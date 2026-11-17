# ruff: noqa: E402
# 说明：必须先调用 configure_test_environment()，再导入读取环境变量的 app 模块。
import asyncio
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

from test_env import configure_test_environment

configure_test_environment()

from fastapi.testclient import TestClient
from sqlalchemy import bindparam, delete, select, text

from app.database import SessionLocal
from app.main import app
from app.models.knowledge import (
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeFavorite,
    KnowledgeIngestionJob,
    KnowledgeMessage,
    KnowledgeView,
)
from app.models.user import User
from app.routers.knowledge import _normalize_answer
from app.services.ai_service import AIResponseValidationError, AIService
from app.services.knowledge_service import _vector_engine, chunk_text, parse_document


class KnowledgeUnitTests(unittest.TestCase):
    def test_chunk_overlap_and_text_parser(self):
        content = "第一段。" * 180
        chunks = chunk_text(content, size=120, overlap=20)
        self.assertGreater(len(chunks), 2)
        self.assertTrue(set(chunks[0][-20:]).intersection(set(chunks[1][:20])))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.txt"
            path.write_text("标题\n\n正文内容", encoding="utf-8")
            self.assertEqual(parse_document(path), "标题\n\n正文内容")

    def test_structured_answer_rewrites_and_validates_citations(self):
        citations = [
            {"index": 1, "document_id": "d1", "document_title": "资料一", "chunk_id": "c1"},
            {"index": 2, "document_id": "d2", "document_title": "资料二", "chunk_id": "c2"},
        ]
        result = _normalize_answer({
            "blocks": [
                {"type": "paragraph", "text": "结论一[2][2]", "citations": [2, 2, 9]},
                {"type": "paragraph", "text": "没有依据的结论", "citations": []},
            ],
            "follow_up_suggestions": ["它的历史背景是什么？"],
        }, citations, "核心内涵是什么？", [{"content": "结论一只说明核心内涵。"}])
        self.assertEqual(result["used_citation_indexes"], [1])
        self.assertEqual(len(result["citations"]), 1)
        self.assertEqual(result["citations"][0]["document_id"], "d2")
        self.assertNotIn("[2][2]", result["answer"])
        self.assertNotIn("没有依据的结论", result["answer"])
        self.assertEqual(result["follow_up_suggestions"], [])

    def test_citations_are_renumbered_after_document_grouping(self):
        citations = [
            {"index": 1, "document_id": "document-b", "chunk_id": "b1"},
            {"index": 2, "document_id": "document-c", "chunk_id": "c1"},
            {"index": 3, "document_id": "document-b", "chunk_id": "b2"},
            {"index": 4, "document_id": "document-a", "chunk_id": "a1"},
            {"index": 5, "document_id": "document-b", "chunk_id": "b3"},
        ]
        result = _normalize_answer({
            "blocks": [
                {"type": "paragraph", "text": "A", "citations": [4]},
                {"type": "paragraph", "text": "B", "citations": [1, 3, 5]},
                {"type": "paragraph", "text": "C", "citations": [2]},
            ],
        }, citations)

        self.assertEqual(
            [item["document_id"] for item in result["citations"]],
            ["document-a", "document-b", "document-b", "document-b", "document-c"],
        )
        self.assertEqual([item["index"] for item in result["citations"]], [1, 2, 3, 4, 5])
        self.assertEqual(
            [block["citations"] for block in result["answer_blocks"]],
            [[1], [2, 3, 4], [5]],
        )

    def test_truncated_json_answer_recovers_complete_blocks(self):
        citations = [{"index": 1, "document_id": "document-a", "chunk_id": "a1"}]
        truncated = '''{
          "blocks": [
            {"type":"heading","text":"Rules","citations":[]},
            {"type":"paragraph","text":"Complete fact","citations":**[1]**},
            {"type":"paragraph","text":"unfinished
        '''
        result = _normalize_answer(truncated, citations)

        self.assertEqual([block["text"] for block in result["answer_blocks"]], ["Rules", "Complete fact"])
        self.assertEqual(result["answer_blocks"][1]["citations"], [1])
        self.assertNotIn('"blocks"', result["answer"])

    def test_citations_are_sorted_and_deduplicated_inside_each_block(self):
        citations = [
            {"index": 1, "document_id": "document-a", "chunk_id": "a1"},
            {"index": 2, "document_id": "document-b", "chunk_id": "b1"},
        ]
        result = _normalize_answer({
            "blocks": [{"type": "paragraph", "text": "同一结论", "citations": [2, 1, 2]}],
        }, citations)

        self.assertEqual(result["answer_blocks"][0]["citations"], [1, 2])
        self.assertTrue(result["answer"].endswith("[1][2]"))

    def test_tool_selector_accepts_one_valid_call_and_rejects_direct_answers(self):
        service = AIService()
        valid_message = {
            "tool_calls": [{
                "id": "call-1",
                "type": "function",
                "function": {"name": "describe_assistant", "arguments": '{"topic":"identity"}'},
            }],
        }
        with patch.object(service, "_call_tool_api", new=AsyncMock(return_value=valid_message)):
            selected = asyncio.run(service.select_knowledge_tool("你是谁"))
        self.assertEqual(selected["name"], "describe_assistant")
        self.assertEqual(selected["arguments"], {"topic": "identity"})

        repeated_same_tool = {
            "tool_calls": [
                valid_message["tool_calls"][0],
                {
                    "id": "call-2",
                    "type": "function",
                    "function": {"name": "describe_assistant", "arguments": '{"topic":"capabilities"}'},
                },
            ],
        }
        with patch.object(service, "_call_tool_api", new=AsyncMock(return_value=repeated_same_tool)):
            selected = asyncio.run(service.select_knowledge_tool("你是谁"))
        self.assertEqual(selected["arguments"], {"topic": "identity"})

        with (
            patch.object(service, "_call_tool_api", new=AsyncMock(return_value={"content": "我是助手"})),
            self.assertRaises(AIResponseValidationError),
        ):
            asyncio.run(service.select_knowledge_tool("你是谁"))


class KnowledgeApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = TestClient(app)
        cls.client = cls.context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)

    def setUp(self):
        async def choose_search(question: str, _history=None):
            return {
                "name": "search_knowledge",
                "arguments": {"query": question},
                "tool_call_id": f"test-{uuid.uuid4().hex}",
            }

        self.tool_selector = AsyncMock(side_effect=choose_search)
        self.tool_patcher = patch(
            "app.routers.knowledge.ai_service.select_knowledge_tool",
            new=self.tool_selector,
        )
        self.tool_patcher.start()

    def tearDown(self):
        self.tool_patcher.stop()
        with SessionLocal() as db:
            documents = db.scalars(select(KnowledgeDocument).where(KnowledgeDocument.source == "测试权威来源")).all()
            ids = [item.id for item in documents]
            paths = [Path(item.file_path) for item in documents if item.file_path]
            if ids:
                db.execute(delete(KnowledgeView).where(KnowledgeView.document_id.in_(ids)))
                db.execute(delete(KnowledgeFavorite).where(KnowledgeFavorite.document_id.in_(ids)))
                db.execute(delete(KnowledgeIngestionJob).where(KnowledgeIngestionJob.document_id.in_(ids)))
                db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id.in_(ids)))
                db.execute(delete(KnowledgeDocument).where(KnowledgeDocument.id.in_(ids)))
                try:
                    for document_id in ids:
                        db.execute(text("DELETE FROM knowledge_chunks_fts WHERE document_id = :id"), {"id": document_id})
                except Exception:
                    pass
                db.commit()
            storage = (Path(__file__).resolve().parents[1] / "storage" / "knowledge").resolve()
            for path in paths:
                resolved = path.resolve()
                if storage in resolved.parents and resolved.is_file():
                    resolved.unlink()
            vector_engine = _vector_engine()
            if vector_engine is not None and ids:
                with vector_engine.begin() as connection:
                    connection.execute(
                        text("DELETE FROM knowledge_vectors WHERE document_id IN :document_ids")
                        .bindparams(bindparam("document_ids", expanding=True)),
                        {"document_ids": ids},
                    )

    def test_assistant_intro_skips_retrieval_and_is_restored_from_history(self):
        headers = self.login(f"130{uuid.uuid4().int % 100_000_000:08d}")
        submission = uuid.uuid4().hex
        self.tool_selector.side_effect = None
        self.tool_selector.return_value = {
            "name": "describe_assistant",
            "arguments": {"topic": "identity"},
            "tool_call_id": "intro-call",
        }
        with patch("app.routers.knowledge.retrieve_async", new=AsyncMock()) as retrieve_mock, patch(
            "app.routers.knowledge.ai_service.knowledge_answer", new=AsyncMock()
        ) as answer_mock:
            response = self.client.post(
                "/api/v1/knowledge/ask",
                headers=headers,
                json={"question": "你是谁", "submission_id": submission},
            )
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["response_kind"], "assistant_intro")
        self.assertEqual(data["selected_tool"], "describe_assistant")
        self.assertEqual(data["citations"], [])
        self.assertIn("知识库助手", data["answer"])
        retrieve_mock.assert_not_awaited()
        answer_mock.assert_not_awaited()

        detail = self.client.get(
            f"/api/v1/knowledge/sessions/{data['session_id']}", headers=headers,
        ).json()["data"]
        assistant = next(item for item in detail["messages"] if item["role"] == "assistant")
        self.assertEqual(assistant["response_kind"], "assistant_intro")
        self.assertEqual(assistant["selected_tool"], "describe_assistant")

        cached = self.client.post(
            "/api/v1/knowledge/ask",
            headers=headers,
            json={
                "question": "你是谁",
                "session_id": data["session_id"],
                "submission_id": submission,
            },
        ).json()["data"]
        self.assertTrue(cached["cached"])
        self.assertEqual(self.tool_selector.await_count, 1)
        self.assertEqual(
            self.client.delete(f"/api/v1/knowledge/sessions/{data['session_id']}", headers=headers).status_code,
            200,
        )

    def test_invalid_tool_selection_falls_back_to_strict_knowledge_search(self):
        headers = self.login(f"139{uuid.uuid4().int % 100_000_000:08d}")
        self.tool_selector.side_effect = AIResponseValidationError("invalid tool")
        retrieve_mock = AsyncMock(return_value=[])
        with patch("app.routers.knowledge.retrieve_async", new=retrieve_mock), patch(
            "app.routers.knowledge.ai_service.knowledge_answer", new=AsyncMock()
        ) as answer_mock:
            response = self.client.post(
                "/api/v1/knowledge/ask",
                headers=headers,
                json={"question": "一个无法检索的问题", "submission_id": uuid.uuid4().hex},
            )
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["selected_tool"], "search_knowledge")
        self.assertEqual(data["response_kind"], "no_evidence")
        self.assertTrue(data["degraded"])
        retrieve_mock.assert_awaited_once()
        answer_mock.assert_not_awaited()
        self.assertEqual(
            self.client.delete(f"/api/v1/knowledge/sessions/{data['session_id']}", headers=headers).status_code,
            200,
        )

    def login(self, phone: str, role: str = "student") -> dict[str, str]:
        registered = self.client.post("/api/v1/auth/register", json={"phone": phone, "password": "test-password"})
        self.assertEqual(registered.status_code, 201)
        response = registered
        user_id = registered.json()["data"]["user"]["id"]
        if role != "student":
            with SessionLocal() as db:
                user = db.get(User, user_id)
                user.role = role
                db.commit()
            response = self.client.post("/api/v1/auth/login", json={"phone": phone, "password": "test-password"})
        return {"Authorization": f"Bearer {response.json()['data']['token']}"}

    def test_upload_permission_limits_and_complete_flow(self):
        random_part = uuid.uuid4().hex[:8]
        student = self.login(f"136{uuid.uuid4().int % 100_000_000:08d}")
        teacher = self.login(f"137{uuid.uuid4().int % 100_000_000:08d}", "teacher")
        fields = {"title": f"测试权威资料{random_part}", "category": "测试分类", "source": "测试权威来源", "source_url": "https://example.edu/source", "version": "1"}
        file_bytes = f"{random_part}是本资料的检索标识。\n\n这是经过审核后才能用于回答的正文内容。".encode()

        forbidden = self.client.post("/api/v1/knowledge/documents/upload", headers=student, data=fields, files={"file": ("sample.txt", file_bytes, "text/plain")})
        self.assertEqual(forbidden.status_code, 403)
        invalid = self.client.post("/api/v1/knowledge/documents/upload", headers=teacher, data=fields, files={"file": ("sample.exe", b"bad", "application/octet-stream")})
        self.assertEqual(invalid.status_code, 415)

        uploaded = self.client.post("/api/v1/knowledge/documents/upload", headers=teacher, data=fields, files={"file": ("sample.txt", file_bytes, "text/plain")})
        self.assertEqual(uploaded.status_code, 202, uploaded.text)
        data = uploaded.json()["data"]
        document_id, job_id = data["document"]["id"], data["job_id"]
        job = self.client.get(f"/api/v1/knowledge/ingestion-jobs/{job_id}", headers=teacher)
        self.assertEqual(job.json()["data"]["status"], "completed")

        duplicate = self.client.post(
            "/api/v1/knowledge/documents/upload",
            headers=teacher,
            data=fields,
            files={"file": ("renamed-sample.txt", file_bytes, "text/plain")},
        )
        self.assertEqual(duplicate.status_code, 409)
        duplicate_detail = duplicate.json()["detail"]
        self.assertEqual(duplicate_detail["code"], "DUPLICATE_DOCUMENT")
        self.assertEqual(duplicate_detail["document"]["id"], document_id)

        corrected_fields = {
            "title": f"修正后的资料标题{random_part}",
            "category": "修正分类",
            "source": "修正后的权威来源",
            "source_url": "https://example.edu/corrected",
            "summary": "用于验证资料信息编辑功能。",
            "version": 2,
        }
        corrected = self.client.put(f"/api/v1/knowledge/documents/{document_id}", headers=teacher, json=corrected_fields)
        self.assertEqual(corrected.status_code, 200, corrected.text)
        self.assertEqual(corrected.json()["data"]["title"], corrected_fields["title"])
        self.assertEqual(corrected.json()["data"]["version"], 2)

        before = self.client.post("/api/v1/knowledge/search", headers=student, json={"query": random_part})
        self.assertEqual(before.json()["data"], [])
        published = self.client.post(f"/api/v1/knowledge/documents/{document_id}/publish", headers=teacher)
        self.assertEqual(published.status_code, 200)

        with SessionLocal() as db:
            active_job = KnowledgeIngestionJob(document_id=document_id, status="queued", progress=0)
            db.add(active_job)
            db.commit()
            active_job_id = active_job.id
        conflict = self.client.post(f"/api/v1/knowledge/documents/{document_id}/reindex", headers=teacher)
        self.assertEqual(conflict.status_code, 409)
        edit_conflict = self.client.put(f"/api/v1/knowledge/documents/{document_id}", headers=teacher, json=corrected_fields)
        self.assertEqual(edit_conflict.status_code, 409)
        delete_conflict = self.client.delete(f"/api/v1/knowledge/documents/{document_id}", headers=teacher)
        self.assertEqual(delete_conflict.status_code, 409)
        with SessionLocal() as db:
            db.get(KnowledgeIngestionJob, active_job_id).status = "completed"
            db.commit()

        reindexed = self.client.post(f"/api/v1/knowledge/documents/{document_id}/reindex", headers=teacher)
        self.assertEqual(reindexed.status_code, 202)
        reindex_job = self.client.get(
            f"/api/v1/knowledge/ingestion-jobs/{reindexed.json()['data']['job_id']}",
            headers=teacher,
        ).json()["data"]
        self.assertEqual(reindex_job["status"], "completed")
        self.assertEqual(reindex_job["document_status"], "published")
        with SessionLocal() as db:
            self.assertEqual(db.get(KnowledgeDocument, document_id).status, "published")

        with patch("app.services.knowledge_service.parse_document", side_effect=ValueError("reindex failed")):
            failed_reindex = self.client.post(f"/api/v1/knowledge/documents/{document_id}/reindex", headers=teacher)
        failed_job = self.client.get(
            f"/api/v1/knowledge/ingestion-jobs/{failed_reindex.json()['data']['job_id']}",
            headers=teacher,
        ).json()["data"]
        self.assertEqual(failed_job["status"], "failed")
        self.assertEqual(failed_job["document_status"], "published")

        rejected = self.client.post(
            f"/api/v1/knowledge/documents/{document_id}/reject",
            headers=teacher,
            json={"reason": "标题仍需调整"},
        )
        self.assertEqual(rejected.status_code, 200)
        corrected_fields["title"] = f"最终资料标题{random_part}"
        self.assertEqual(
            self.client.put(f"/api/v1/knowledge/documents/{document_id}", headers=teacher, json=corrected_fields).status_code,
            200,
        )
        resubmitted = self.client.post(f"/api/v1/knowledge/documents/{document_id}/resubmit", headers=teacher)
        self.assertEqual(resubmitted.status_code, 200)
        self.assertEqual(resubmitted.json()["data"]["status"], "pending_review")
        self.assertEqual(self.client.post(f"/api/v1/knowledge/documents/{document_id}/publish", headers=teacher).status_code, 200)

        after = self.client.post("/api/v1/knowledge/search", headers=student, json={"query": random_part})
        self.assertEqual(after.json()["data"][0]["id"], document_id)

        with patch("app.routers.knowledge.ai_service.knowledge_answer", new=AsyncMock(return_value="根据资料，结论有明确依据。[1]")):
            answered = self.client.post("/api/v1/knowledge/ask", headers=student, json={"question": random_part})
        self.assertEqual(answered.status_code, 200)
        answer_data = answered.json()["data"]
        self.assertEqual(answer_data["citations"][0]["document_id"], document_id)
        self.assertTrue(answer_data["session_id"])

        # Natural-language question words must not make keyword fallback miss
        # an indexed document while the embedding model is still warming up.
        with patch("app.routers.knowledge.ai_service.knowledge_answer", new=AsyncMock(return_value="自然语言检索命中资料。[1]")):
            natural_answer = self.client.post(
                "/api/v1/knowledge/ask",
                headers=student,
                json={"question": f"请问资料中的{random_part}主要说明了什么？"},
            )
        self.assertEqual(natural_answer.status_code, 200, natural_answer.text)
        self.assertEqual(natural_answer.json()["data"]["citations"][0]["document_id"], document_id)

        self.assertEqual(self.client.post(f"/api/v1/knowledge/favorites/{document_id}", headers=student).status_code, 200)
        favorites = self.client.get("/api/v1/knowledge/favorites", headers=student).json()["data"]
        self.assertIn(document_id, [item["id"] for item in favorites])
        self.assertEqual(self.client.get(f"/api/v1/knowledge/documents/{document_id}", headers=student).status_code, 200)
        recent = self.client.get("/api/v1/knowledge/recent", headers=student).json()["data"]
        self.assertIn(document_id, [item["id"] for item in recent])

        with SessionLocal() as db:
            stored_path = db.get(KnowledgeDocument, document_id).file_path
        deleted = self.client.delete(f"/api/v1/knowledge/documents/{document_id}", headers=teacher)
        self.assertEqual(deleted.status_code, 200, deleted.text)
        self.assertTrue(deleted.json()["data"]["deleted"])
        self.assertFalse(Path(stored_path).exists())
        self.assertEqual(self.client.get(f"/api/v1/knowledge/documents/{document_id}", headers=teacher).status_code, 404)
        self.assertEqual(self.client.post("/api/v1/knowledge/search", headers=student, json={"query": random_part}).json()["data"], [])

        uploaded_again = self.client.post(
            "/api/v1/knowledge/documents/upload",
            headers=teacher,
            data=fields,
            files={"file": ("sample-again.txt", file_bytes, "text/plain")},
        )
        self.assertEqual(uploaded_again.status_code, 202, uploaded_again.text)

    def test_no_evidence_refuses_without_calling_ai(self):
        headers = self.login(f"135{uuid.uuid4().int % 100_000_000:08d}")
        with patch("app.routers.knowledge.retrieve_async", new=AsyncMock(return_value=[])), patch(
            "app.routers.knowledge.ai_service.knowledge_answer", new=AsyncMock()
        ) as mocked:
            response = self.client.post("/api/v1/knowledge/ask", headers=headers, json={"question": f"不存在的证据{uuid.uuid4().hex}"})
        self.assertTrue(response.json()["data"]["answer"].startswith("当前知识库没有足够依据"))
        session_id = response.json()["data"]["session_id"]
        other_headers = self.login(f"133{uuid.uuid4().int % 100_000_000:08d}")
        self.assertEqual(self.client.delete(f"/api/v1/knowledge/sessions/{session_id}", headers=other_headers).status_code, 404)
        deleted = self.client.delete(f"/api/v1/knowledge/sessions/{session_id}", headers=headers)
        self.assertEqual(deleted.status_code, 200)
        self.assertTrue(deleted.json()["data"]["deleted"])
        self.assertEqual(self.client.get(f"/api/v1/knowledge/sessions/{session_id}", headers=headers).status_code, 404)
        with SessionLocal() as db:
            self.assertEqual(len(db.scalars(select(KnowledgeMessage).where(KnowledgeMessage.session_id == session_id)).all()), 0)
        mocked.assert_not_awaited()

    def test_vector_timeout_falls_back_to_keyword_retrieval(self):
        headers = self.login(f"134{uuid.uuid4().int % 100_000_000:08d}")
        fallback_context = [{
            "document_id": "doc-timeout-fallback",
            "title": "测试资料",
            "source": "测试来源",
            "source_url": "",
            "chunk_id": "chunk-timeout-fallback",
            "chunk_index": 0,
            "content": "用于验证向量检索超时后仍可使用关键词检索回答。",
        }]
        retrieve_mock = AsyncMock(side_effect=[TimeoutError(), fallback_context])
        with patch("app.routers.knowledge.retrieve_async", new=retrieve_mock), patch(
            "app.routers.knowledge.ai_service.knowledge_answer", new=AsyncMock(return_value="已使用降级检索回答。[1]")
        ) as answer_mock:
            response = self.client.post("/api/v1/knowledge/ask", headers=headers, json={"question": "验证降级检索"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["data"]["citations"][0]["document_id"], "doc-timeout-fallback")
        self.assertEqual(retrieve_mock.await_count, 2)
        answer_mock.assert_awaited_once()

    def test_conversation_context_idempotency_session_edit_and_feedback(self):
        headers = self.login(f"132{uuid.uuid4().int % 100_000_000:08d}")
        context = [{
            "document_id": "doc-context", "title": "上下文资料", "source": "官方来源", "source_url": "",
            "chunk_id": "chunk-context", "chunk_index": 0, "content": "第一项规定与第二项规定适用范围不同。", "score": 1.0,
        }]
        answer_value = {"blocks": [{"type": "paragraph", "text": "第一项规定适用于基层组织。", "citations": [1]}], "follow_up_suggestions": ["第二项规定是什么？"]}
        retrieve_mock = AsyncMock(return_value=context)
        answer_mock = AsyncMock(return_value=answer_value)
        submission = uuid.uuid4().hex
        with patch("app.routers.knowledge.retrieve_async", new=retrieve_mock), patch(
            "app.routers.knowledge.ai_service.knowledge_answer", new=answer_mock
        ):
            first = self.client.post("/api/v1/knowledge/ask", headers=headers, json={"question": "第一项规定是什么？", "submission_id": submission})
            self.assertEqual(first.status_code, 200, first.text)
            first_data = first.json()["data"]
            cached = self.client.post("/api/v1/knowledge/ask", headers=headers, json={
                "question": "第一项规定是什么？", "session_id": first_data["session_id"], "submission_id": submission,
            })
            self.assertTrue(cached.json()["data"]["cached"])
            follow = self.client.post("/api/v1/knowledge/ask", headers=headers, json={
                "question": "它和上一个规定有什么区别？", "session_id": first_data["session_id"], "submission_id": uuid.uuid4().hex,
            })
            self.assertEqual(follow.status_code, 200, follow.text)

        self.assertEqual(answer_mock.await_count, 2)
        self.assertIn("第一项规定是什么", retrieve_mock.await_args_list[1].args[0])
        message_id = first_data["message_id"]
        feedback = self.client.post(f"/api/v1/knowledge/messages/{message_id}/feedback", headers=headers, json={"helpful": True, "reason": "引用清楚"})
        self.assertEqual(feedback.json()["data"]["feedback"], "helpful")
        renamed = self.client.patch(f"/api/v1/knowledge/sessions/{first_data['session_id']}", headers=headers, json={"title": "规定比较"})
        self.assertEqual(renamed.json()["data"]["title"], "规定比较")
        detail = self.client.get(f"/api/v1/knowledge/sessions/{first_data['session_id']}", headers=headers).json()["data"]
        self.assertEqual(len([item for item in detail["messages"] if item["role"] == "user"]), 2)
        self.assertEqual(self.client.delete(f"/api/v1/knowledge/sessions/{first_data['session_id']}", headers=headers).status_code, 200)

    def test_failed_question_is_persisted_and_can_retry(self):
        headers = self.login(f"131{uuid.uuid4().int % 100_000_000:08d}")
        submission = uuid.uuid4().hex
        context = [{
            "document_id": "doc-retry", "title": "重试资料", "source": "官方来源", "source_url": "",
            "chunk_id": "chunk-retry", "chunk_index": 0, "content": "用于验证失败重试。", "score": 1.0,
        }]
        with patch("app.routers.knowledge.retrieve_async", new=AsyncMock(return_value=context)), patch(
            "app.routers.knowledge.ai_service.knowledge_answer", new=AsyncMock(side_effect=RuntimeError("offline"))
        ):
            failed = self.client.post("/api/v1/knowledge/ask", headers=headers, json={"question": "如何重试？", "submission_id": submission})
        self.assertEqual(failed.status_code, 503)
        sessions = self.client.get("/api/v1/knowledge/sessions", headers=headers).json()["data"]
        session_id = sessions[0]["id"]
        detail = self.client.get(f"/api/v1/knowledge/sessions/{session_id}", headers=headers).json()["data"]
        self.assertEqual(detail["messages"][0]["status"], "failed")
        with patch("app.routers.knowledge.retrieve_async", new=AsyncMock(return_value=context)), patch(
            "app.routers.knowledge.ai_service.knowledge_answer", new=AsyncMock(return_value={
                "blocks": [{"type": "paragraph", "text": "现在可以重试。", "citations": [1]}], "follow_up_suggestions": []
            })
        ):
            retried = self.client.post("/api/v1/knowledge/ask", headers=headers, json={
                "question": "如何重试？", "session_id": session_id, "submission_id": submission,
            })
        self.assertEqual(retried.status_code, 200, retried.text)
        self.assertEqual(self.client.delete(f"/api/v1/knowledge/sessions/{session_id}", headers=headers).status_code, 200)


if __name__ == "__main__":
    unittest.main()
