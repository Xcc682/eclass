# ruff: noqa: E402
# 说明：必须先调用 configure_test_environment()，再导入读取环境变量的 app 模块。
import asyncio
import unittest
import uuid
from unittest.mock import AsyncMock, patch

from test_env import configure_test_environment

configure_test_environment()

from fastapi.testclient import TestClient

from app.config import settings
from app.database import SessionLocal
from app.main import app
from app.models.user import User
from app.services import ai_quota, circuit_breaker, grounding, llm_metrics, retrieval_advanced, semantic_cache
from app.services.ai_service import AIService


class FakeLLM:
    """按顺序返回预设回复的假模型，记录每次调用的参数。"""

    def __init__(self, replies):
        self.api_key = "fake-key"
        self.fast_model = "fake-fast"
        self.replies = list(replies)
        self.calls: list[dict] = []

    async def _call_api(self, messages, **kwargs):
        self.calls.append({"messages": messages, **kwargs})
        if not self.replies:
            raise RuntimeError("no reply")
        return self.replies.pop(0)


class MetricsAndBreakerTests(unittest.TestCase):
    def setUp(self):
        llm_metrics.reset()
        circuit_breaker.breaker.reset()

    def tearDown(self):
        circuit_breaker.breaker.reset()
        ai_quota.reset()
        llm_metrics.reset()

    def test_metrics_snapshot_counts_calls_and_tokens(self):
        llm_metrics.record("m", 120, ok=True, prompt_tokens=30, completion_tokens=10)
        llm_metrics.record("m", 80, ok=False, error="ConnectError")
        snapshot = llm_metrics.snapshot()
        self.assertEqual(snapshot["totals"]["calls"], 2)
        self.assertEqual(snapshot["totals"]["success"], 1)
        self.assertEqual(snapshot["totals"]["failed"], 1)
        self.assertEqual(snapshot["totals"]["prompt_tokens"], 30)
        self.assertEqual(snapshot["success_rate"], 0.5)
        self.assertEqual(snapshot["average_latency_ms"], 100)
        self.assertEqual(len(snapshot["recent"]), 2)

    def test_breaker_opens_then_half_opens_after_cooldown(self):
        clock = {"now": 0.0}
        breaker = circuit_breaker.CircuitBreaker(threshold=2, cooldown=30, clock=lambda: clock["now"])
        self.assertTrue(breaker.allow())
        breaker.record_failure()
        self.assertEqual(breaker.state, "closed")
        breaker.record_failure()
        self.assertEqual(breaker.state, "open")
        self.assertFalse(breaker.allow())
        clock["now"] = 31
        self.assertEqual(breaker.state, "half_open")
        self.assertTrue(breaker.allow())
        breaker.record_success()
        self.assertEqual(breaker.describe()["failures"], 0)
        self.assertEqual(breaker.state, "closed")

    def test_quota_blocks_after_budget_and_admins_bypass(self):
        with patch.object(settings, "AI_DAILY_TOKEN_BUDGET", 100):
            ai_quota.consume("u1", 60)
            ai_quota.ensure("u1", "student")
            self.assertEqual(ai_quota.describe("u1")["remaining"], 40)
            ai_quota.consume("u1", 50)
            with self.assertRaises(ai_quota.QuotaExceeded):
                ai_quota.ensure("u1", "student")
            ai_quota.ensure("u1", "admin")
            self.assertEqual(ai_quota.used(None), 0)


class GatewayTests(unittest.TestCase):
    def setUp(self):
        llm_metrics.reset()
        circuit_breaker.breaker.reset()
        ai_quota.reset()

    def tearDown(self):
        circuit_breaker.breaker.reset()
        ai_quota.reset()
        llm_metrics.reset()
        ai_quota.bind(None)

    def test_call_api_records_metrics_and_consumes_quota(self):
        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "choices": [{"message": {"content": "回答"}}],
                    "usage": {"prompt_tokens": 12, "completion_tokens": 8},
                }

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def post(self, *args, **kwargs):
                return FakeResponse()

        ai_quota.bind("user-1")
        service = AIService()
        with patch("app.services.ai_service.httpx.AsyncClient", return_value=FakeClient()):
            content = asyncio.run(service._call_api([{"role": "user", "content": "你好"}]))

        self.assertEqual(content, "回答")
        snapshot = llm_metrics.snapshot()
        self.assertEqual(snapshot["totals"]["calls"], 1)
        self.assertEqual(snapshot["totals"]["prompt_tokens"], 12)
        self.assertEqual(snapshot["totals"]["completion_tokens"], 8)
        self.assertEqual(ai_quota.used("user-1"), 20)
        self.assertEqual(circuit_breaker.breaker.state, "closed")

    def test_gateway_opens_breaker_after_repeated_failures(self):
        calls = {"count": 0}

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def post(self, *args, **kwargs):
                calls["count"] += 1
                raise RuntimeError("upstream down")

        service = AIService()
        with patch("app.services.ai_service.httpx.AsyncClient", return_value=FakeClient()):
            for _ in range(settings.LLM_CIRCUIT_FAIL_THRESHOLD):
                with self.assertRaises(RuntimeError):
                    asyncio.run(service._call_api([{"role": "user", "content": "hi"}]))
            self.assertEqual(circuit_breaker.breaker.state, "open")
            with self.assertRaises(circuit_breaker.CircuitOpenError):
                asyncio.run(service._call_api([{"role": "user", "content": "hi"}]))
        self.assertEqual(calls["count"], settings.LLM_CIRCUIT_FAIL_THRESHOLD)
        # 每次上游失败一条，熔断后快速失败再记一条 circuit_open
        self.assertEqual(llm_metrics.snapshot()["totals"]["failed"], settings.LLM_CIRCUIT_FAIL_THRESHOLD + 1)

    def test_call_api_passes_model_routing(self):
        service = AIService()
        with patch.object(service, "_post_chat", new=AsyncMock(return_value={"choices": [{"message": {"content": "ok"}}]})) as post:
            asyncio.run(service._call_api([{"role": "user", "content": "hi"}], model="fast-x"))
        payload = post.await_args.args[0]
        self.assertEqual(payload["model"], "fast-x")


class RetrievalAdvancedTests(unittest.TestCase):
    def test_merge_rrf_boosts_chunks_hit_by_multiple_queries(self):
        groups = [
            [{"chunk_id": "a", "title": "A"}, {"chunk_id": "b", "title": "B"}],
            [{"chunk_id": "b", "title": "B"}, {"chunk_id": "c", "title": "C"}],
        ]
        merged = retrieval_advanced.merge_rrf(groups, limit=3)
        self.assertEqual([item["chunk_id"] for item in merged], ["b", "a", "c"])
        self.assertEqual(merged[0]["matched_queries"], 2)
        self.assertGreater(merged[0]["score"], merged[1]["score"])

    def test_expand_queries_dedupes_and_caps(self):
        service = FakeLLM(['["入党流程是什么", "入党流程是什么", "入党需要哪些步骤", "预备党员如何转正"]'])
        with patch.object(settings, "RETRIEVAL_MULTI_QUERY_COUNT", 2):
            queries = asyncio.run(retrieval_advanced.expand_queries(service, "入党流程是什么"))
        self.assertEqual(len(queries), 2)
        self.assertNotIn("入党流程是什么", queries)
        self.assertEqual(service.calls[0]["model"], "fake-fast")

    def test_expand_queries_degrades_on_bad_output(self):
        service = FakeLLM(["不是 JSON"])
        self.assertEqual(asyncio.run(retrieval_advanced.expand_queries(service, "问题")), [])
        self.assertEqual(asyncio.run(retrieval_advanced.expand_queries(object(), "问题")), [])

    def test_rerank_applies_full_permutation(self):
        service = FakeLLM(["[2,3,1]"])
        candidates = [{"chunk_id": "a", "content": "A"}, {"chunk_id": "b", "content": "B"}, {"chunk_id": "c", "content": "C"}]
        ranked = asyncio.run(retrieval_advanced.rerank(service, "问题", candidates))
        self.assertEqual([item["chunk_id"] for item in ranked], ["b", "c", "a"])
        self.assertTrue(all(item["reranked"] for item in ranked))
        self.assertGreater(ranked[0]["score"], ranked[-1]["score"])

    def test_rerank_pads_partial_permutation_with_original_order(self):
        # 模型只回相关编号时按序前置，未提及的候选保持原序续接
        service = FakeLLM(["[3,1]"])
        candidates = [{"chunk_id": "a", "content": "A"}, {"chunk_id": "b", "content": "B"}, {"chunk_id": "c", "content": "C"}]
        ranked = asyncio.run(retrieval_advanced.rerank(service, "问题", candidates))
        self.assertEqual([item["chunk_id"] for item in ranked], ["c", "a", "b"])

    def test_rerank_returns_candidates_when_order_unchanged(self):
        service = FakeLLM(["[1,2]"])
        candidates = [{"chunk_id": "a", "content": "A"}, {"chunk_id": "b", "content": "B"}]
        self.assertIs(asyncio.run(retrieval_advanced.rerank(service, "问题", candidates)), candidates)

    def test_merge_rrf_limits_chunks_per_document(self):
        groups = [[
            {"chunk_id": "d1:0", "document_id": "d1"},
            {"chunk_id": "d1:1", "document_id": "d1"},
            {"chunk_id": "d1:2", "document_id": "d1"},
            {"chunk_id": "d2:0", "document_id": "d2"},
        ]]
        merged = retrieval_advanced.merge_rrf(groups, limit=4, max_per_document=2)
        self.assertEqual([item["chunk_id"] for item in merged], ["d1:0", "d1:1", "d2:0"])

    def test_rerank_falls_back_on_invalid_reply(self):
        service = FakeLLM(["[9]"])
        candidates = [{"chunk_id": "a", "content": "A"}, {"chunk_id": "b", "content": "B"}]
        self.assertIs(asyncio.run(retrieval_advanced.rerank(service, "问题", candidates)), candidates)

    def test_search_fuses_queries_and_reranks(self):
        service = FakeLLM(['["入党流程要求", "入党步骤"]', "[2,1]"])
        fetch = AsyncMock(side_effect=[
            [{"chunk_id": "a", "score": 0.03}],
            [{"chunk_id": "b", "score": 0.02}],
            [{"chunk_id": "a", "score": 0.02}],
        ])
        with patch.object(settings, "RETRIEVAL_MULTI_QUERY_ENABLED", True), \
                patch.object(settings, "RETRIEVAL_RERANK_ENABLED", True):
            results, trace = asyncio.run(retrieval_advanced.search(fetch, service, "入党流程"))
        self.assertEqual(trace["queries"], 3)
        self.assertEqual(trace["expanded"], 2)
        self.assertEqual(trace["reranked"], True)
        self.assertEqual(fetch.await_count, 3)
        self.assertEqual([item["chunk_id"] for item in results], ["b", "a"])

    def test_search_degrades_to_single_query_when_expansion_fails(self):
        service = FakeLLM(['["变体一"]', "[1]"])

        async def fetch(query, category=None, **kwargs):
            if query != "原始问题":
                raise RuntimeError("query failed")
            return [{"chunk_id": "a"}]

        with patch.object(settings, "RETRIEVAL_MULTI_QUERY_ENABLED", True), \
                patch.object(settings, "RETRIEVAL_RERANK_ENABLED", False):
            results, trace = asyncio.run(retrieval_advanced.search(fetch, service, "原始问题"))
        self.assertTrue(trace["degraded"])
        self.assertEqual([item["chunk_id"] for item in results], ["a"])

    def test_search_without_llm_uses_original_query(self):
        fetch = AsyncMock(return_value=[{"chunk_id": "a"}])
        results, trace = asyncio.run(retrieval_advanced.search(fetch, object(), "问题"))
        self.assertEqual(trace["queries"], 1)
        self.assertEqual(len(results), 1)
        self.assertEqual(fetch.await_count, 1)


class SemanticCacheTests(unittest.TestCase):
    def setUp(self):
        semantic_cache.reset()

    def tearDown(self):
        semantic_cache.reset()

    def test_exact_match_hit_without_embeddings(self):
        payload = {"normalized": {"answer": "答案"}, "kind": "rag"}
        with patch.object(semantic_cache, "_embedding", return_value=None), \
                patch.object(settings, "SEMANTIC_CACHE_ENABLED", True):
            semantic_cache.store(" 入党流程是什么 ", payload, "|")
            hit = semantic_cache.lookup("入党 流程是什么", "|")
        self.assertIsNotNone(hit)
        self.assertTrue(hit["cached"])
        self.assertEqual(hit["normalized"]["answer"], "答案")

    def test_scope_and_threshold_filter_hits(self):
        with patch.object(settings, "SEMANTIC_CACHE_ENABLED", True), \
                patch.object(settings, "SEMANTIC_CACHE_THRESHOLD", 0.93):
            with patch.object(semantic_cache, "_embedding", side_effect=[[1.0, 0.0], [0.5, 0.5], [0.5, 0.5]]):
                semantic_cache.store("党史学习的方法", {"normalized": {}, "kind": "rag"}, "党史")
                self.assertIsNone(semantic_cache.lookup("党史学习的路径", "党史"))
                self.assertIsNone(semantic_cache.lookup("党史学习的方法", "其他分类"))
            with patch.object(semantic_cache, "_embedding", side_effect=[[1.0, 0.0], [1.0, 0.0]]):
                hit = semantic_cache.lookup("党史学习的路径", "党史")
        self.assertIsNotNone(hit)
        self.assertEqual(hit["similarity"], 1.0)

    def test_expired_entries_are_purged(self):
        clock = {"now": 100.0}
        with patch.object(settings, "SEMANTIC_CACHE_ENABLED", True), \
                patch.object(settings, "SEMANTIC_CACHE_TTL_SECONDS", 60), \
                patch.object(semantic_cache, "_clock", lambda: clock["now"]), \
                patch.object(semantic_cache, "_embedding", return_value=None):
            semantic_cache.store("代理缓存问题", {"normalized": {}, "kind": "rag"})
            clock["now"] = 130.0
            self.assertIsNotNone(semantic_cache.lookup("代理缓存问题"))
            clock["now"] = 400.0
            self.assertIsNone(semantic_cache.lookup("代理缓存问题"))
            self.assertEqual(semantic_cache.stats()["items"], 0)

    def test_disabled_cache_never_hits(self):
        with patch.object(settings, "SEMANTIC_CACHE_ENABLED", False), \
                patch.object(semantic_cache, "_embedding", return_value=None):
            semantic_cache.store("关闭缓存的问题", {"normalized": {}, "kind": "rag"})
            self.assertIsNone(semantic_cache.lookup("关闭缓存的问题"))


class GroundingTests(unittest.TestCase):
    def _answer(self):
        return {
            "answer": "正文[1][2]",
            "answer_blocks": [
                {"type": "heading", "text": "标题", "citations": []},
                {"type": "paragraph", "text": "有据结论", "citations": [1, 2]},
            ],
            "citations": [
                {"index": 1, "document_title": "资料一", "excerpt": "片段一"},
                {"index": 2, "document_title": "资料二", "excerpt": "片段二"},
            ],
            "used_citation_indexes": [1, 2],
            "follow_up_suggestions": [],
        }

    def test_apply_verdicts_drops_unsupported_citations_and_renumbers(self):
        # verdicts 按「送检序号」编号：这里只有段落一个带引用块，序号 1 对应它
        updated, dropped = grounding.apply_verdicts(self._answer(), {1: [2]})
        self.assertEqual(dropped, 1)
        self.assertEqual([item["index"] for item in updated["citations"]], [1])
        self.assertEqual(updated["citations"][0]["document_title"], "资料二")
        self.assertEqual(updated["answer_blocks"][1]["citations"], [1])
        self.assertTrue(updated["answer"].endswith("[1]"))

    def test_apply_verdicts_removes_block_when_all_citations_rejected(self):
        answer = {
            "answer": "有据[1]\n无据[2]",
            "answer_blocks": [
                {"type": "paragraph", "text": "有据", "citations": [1]},
                {"type": "paragraph", "text": "无据", "citations": [2]},
            ],
            "citations": [{"index": 1, "document_title": "资料一"}, {"index": 2, "document_title": "资料二"}],
            "used_citation_indexes": [1, 2],
            "follow_up_suggestions": [],
        }
        updated, dropped = grounding.apply_verdicts(answer, {1: [1], 2: []})
        self.assertEqual([block["text"] for block in updated["answer_blocks"]], ["有据"])
        self.assertEqual(len(updated["citations"]), 1)
        self.assertEqual(dropped, 1)

    def test_verify_skips_when_disabled_or_uncited(self):
        answer = self._answer()
        with patch.object(settings, "GROUNDING_CHECK_ENABLED", False):
            result, report = asyncio.run(grounding.verify(FakeLLM([]), answer, "问题"))
        self.assertIs(result, answer)
        self.assertEqual(report["status"], "disabled")
        with patch.object(settings, "GROUNDING_CHECK_ENABLED", True):
            uncited = {"answer": "x", "answer_blocks": [], "citations": []}
            self.assertEqual(asyncio.run(grounding.verify(FakeLLM([]), uncited))[1]["status"], "skipped")

    def test_verify_applies_supported_verdicts(self):
        service = FakeLLM(['[{"block": 1, "supported": [2]}]'])
        with patch.object(settings, "GROUNDING_CHECK_ENABLED", True):
            updated, report = asyncio.run(grounding.verify(service, self._answer(), "问题"))
        self.assertEqual(report["status"], "verified")
        self.assertEqual(report["dropped"], 1)
        self.assertEqual(len(updated["citations"]), 1)
        self.assertEqual(service.calls[0]["temperature"], 0)

    def test_verify_fails_open_on_bad_output(self):
        answer = self._answer()
        with patch.object(settings, "GROUNDING_CHECK_ENABLED", True):
            result, report = asyncio.run(grounding.verify(FakeLLM(["乱码"]), answer, "问题"))
        self.assertIs(result, answer)
        self.assertEqual(report["status"], "degraded")

    def test_verify_reports_unverified_when_everything_rejected(self):
        answer = self._answer()
        with patch.object(settings, "GROUNDING_CHECK_ENABLED", True):
            result, report = asyncio.run(grounding.verify(FakeLLM(['[{"block": 1, "supported": []}]']), answer, "问题"))
        self.assertIs(result, answer)
        self.assertEqual(report["status"], "unverified")


class ObservabilityApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = TestClient(app)
        cls.client = cls.context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)
        # 本文件注册的账号不占用整套测试共享的登录限流额度
        from app.routers.auth import reset_login_throttle

        reset_login_throttle()

    def setUp(self):
        from app.routers.auth import reset_login_throttle

        reset_login_throttle()
        ai_quota.reset()
        llm_metrics.reset()

    def tearDown(self):
        ai_quota.reset()
        llm_metrics.reset()
        ai_quota.bind(None)

    def login(self) -> tuple[dict[str, str], str]:
        phone = f"139{uuid.uuid4().int % 100_000_000:08d}"
        registered = self.client.post("/api/v1/auth/register", json={"phone": phone, "password": "test-password"})
        self.assertEqual(registered.status_code, 201)
        headers = {"Authorization": f"Bearer {registered.json()['data']['token']}"}
        return headers, registered.json()["data"]["user"]["id"]

    def test_observability_endpoint_reports_gateway_state(self):
        headers, _ = self.login()
        llm_metrics.record("deepseek-v4-flash", 90, ok=True, prompt_tokens=10, completion_tokens=5)
        response = self.client.get("/api/v1/ai/observability", headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["llm"]["totals"]["calls"], 1)
        self.assertIn("state", data["circuit_breaker"])
        self.assertEqual(data["quota"]["used_today"] >= 0, True)
        self.assertIn("hit_rate", data["semantic_cache"])
        self.assertEqual(data["models"]["fast"], settings.LLM_MODEL_FAST)

    def test_quota_exhaustion_returns_429(self):
        headers, user_id = self.login()
        with SessionLocal() as db:
            self.assertIsNotNone(db.get(User, user_id))
        with patch.object(settings, "AI_DAILY_TOKEN_BUDGET", 10):
            ai_quota.consume(user_id, 10)
            response = self.client.post(
                "/api/v1/knowledge/ask",
                headers=headers,
                json={"question": "入党流程是什么", "submission_id": uuid.uuid4().hex},
            )
        self.assertEqual(response.status_code, 429)
        self.assertIn("额度", response.json()["detail"])

    def test_used_tokens_reset_daily(self):
        ai_quota.consume("u-daily", 5)
        self.assertEqual(ai_quota.used("u-daily"), 5)
        with patch("app.services.ai_quota.date") as fake_date:
            fake_date.today.return_value.isoformat.return_value = "2099-01-01"
            self.assertEqual(ai_quota.used("u-daily"), 0)


if __name__ == "__main__":
    unittest.main()
