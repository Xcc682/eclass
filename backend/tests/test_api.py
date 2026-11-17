import asyncio
import json
import unittest
import uuid
from unittest.mock import AsyncMock, patch

from test_env import configure_test_environment

configure_test_environment()

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models.user import User
from app.services.ai_service import (
    AIResponseValidationError, AIService, validate_debate_feedback, validate_debate_turn,
    validate_interview_report, validate_interview_turn,
)


class ApiAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client_context = TestClient(app)
        cls.client = cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_context.__exit__(None, None, None)

    def login_headers(self, phone: str) -> dict[str, str]:
        registered = self.client.post("/api/v1/auth/register", json={"phone": phone, "password": "test-password"})
        self.assertIn(registered.status_code, (201, 409))
        if registered.status_code == 201:
            return {"Authorization": f"Bearer {registered.json()['data']['token']}"}
        login = self.client.post("/api/v1/auth/login", json={"phone": phone, "password": "test-password"})
        self.assertEqual(login.status_code, 200)
        return {"Authorization": f"Bearer {login.json()['data']['token']}"}

    def test_01_health_and_public_catalogs(self):
        self.assertEqual(self.client.get("/health").json(), {"status": "healthy"})
        self.assertGreaterEqual(len(self.client.get("/api/v1/interviews/scenarios").json()["data"]), 4)
        headers = self.login_headers(f"135{uuid.uuid4().int % 100_000_000:08d}")
        self.assertGreaterEqual(len(self.client.get("/api/v1/history/scenarios", headers=headers).json()["data"]), 5)
        self.assertGreaterEqual(len(self.client.get("/api/v1/knowledge/documents").json()["data"]), 3)

    def test_02_auth_profile_and_role_guard(self):
        self.assertEqual(self.client.get("/api/v1/users/profile").status_code, 401)
        unknown_phone = f"137{uuid.uuid4().int % 100_000_000:08d}"
        unknown_login = self.client.post("/api/v1/auth/login", json={"phone": unknown_phone, "password": "test-password"})
        self.assertEqual(unknown_login.status_code, 404)
        self.assertEqual(unknown_login.json()["detail"], "账号不存在，请先注册")
        register_phone = f"138{uuid.uuid4().int % 100_000_000:08d}"
        registered = self.client.post("/api/v1/auth/register", json={"phone": register_phone, "password": "register-password"})
        self.assertEqual(registered.status_code, 201, registered.text)
        self.assertTrue(registered.json()["data"]["token"])
        self.assertEqual(registered.json()["data"]["user"]["nickname"], f"同学{register_phone[-4:]}")
        duplicate = self.client.post("/api/v1/auth/register", json={"phone": register_phone, "password": "register-password"})
        self.assertEqual(duplicate.status_code, 409)
        registered_login = self.client.post("/api/v1/auth/login", json={"phone": register_phone, "password": "register-password"})
        self.assertEqual(registered_login.status_code, 200)
        phone = f"139{uuid.uuid4().int % 100_000_000:08d}"
        headers = self.login_headers(phone)
        profile = self.client.get("/api/v1/users/profile", headers=headers)
        self.assertEqual(profile.status_code, 200)
        self.assertTrue(profile.json()["data"]["features"]["notifications_available"])
        self.assertFalse(profile.json()["data"]["features"]["yiban_binding_available"])
        updated = self.client.put("/api/v1/users/profile", headers=headers, json={"nickname": "验收同学", "school": "测试大学"})
        self.assertEqual(updated.json()["data"]["nickname"], "验收同学")
        wrong = self.client.post("/api/v1/auth/login", json={"phone": phone, "password": "wrong-password"})
        self.assertEqual(wrong.status_code, 401)
        forbidden = self.client.post("/api/v1/community/tasks", headers=headers, json={"title": "教师任务", "description": "test"})
        self.assertEqual(forbidden.status_code, 403)

    def test_03_community_persistence_and_reply(self):
        headers = self.login_headers("13900000012")
        created = self.client.post("/api/v1/community/posts", headers=headers, json={
            "title": "自动化验收帖子", "content": "该内容用于验证社区持久化。", "category": "测试", "is_question": False,
        })
        self.assertEqual(created.status_code, 200)
        post_id = created.json()["data"]["id"]
        reply = self.client.post(f"/api/v1/community/posts/{post_id}/replies", headers=headers, json={"content": "验收回复"})
        self.assertEqual(reply.status_code, 200)
        detail = self.client.get(f"/api/v1/community/posts/{post_id}").json()["data"]
        self.assertEqual(detail["title"], "自动化验收帖子")
        self.assertEqual(detail["reply_list"][0]["content"], "验收回复")

    def test_04_history_completion_is_idempotent(self):
        phone = f"139{uuid.uuid4().int % 100_000_000:08d}"
        headers = self.login_headers(phone)
        before = self.client.get("/api/v1/users/profile", headers=headers).json()["data"]["total_points"]
        self.assertEqual(self.client.post("/api/v1/history/scenarios/1/choice", headers=headers, json={"option_index": 1}).status_code, 200)
        self.assertEqual(self.client.post("/api/v1/history/scenarios/1/complete", headers=headers).status_code, 200)
        self.assertEqual(self.client.post("/api/v1/history/scenarios/1/complete", headers=headers).status_code, 200)
        after = self.client.get("/api/v1/users/profile", headers=headers).json()["data"]["total_points"]
        self.assertEqual(after - before, 2)
        points = self.client.get("/api/v1/users/points", headers=headers).json()["data"]
        self.assertEqual(points["by_module"]["history"], 2)
        self.assertEqual(len([row for row in points["recent_transactions"] if row["module"] == "history"]), 1)
        self.assertTrue(points["is_reconciled"])
        growth = self.client.get("/api/v1/users/growth", headers=headers).json()["data"]
        history_growth = next(row for row in growth["module_growth"] if row["key"] == "history")
        self.assertEqual(history_growth["completed_count"], 1)
        self.assertEqual(history_growth["points"], 2)
        self.assertEqual(len(growth["ability_dimensions"]), 4)
        self.assertGreaterEqual(growth["streak_days"], 1)

    def test_05_ai_failure_is_explicit_and_does_not_create_practice(self):
        headers = self.login_headers("13900000014")
        with patch("app.routers.interviews.ai_service.interview_start", new=AsyncMock(side_effect=RuntimeError("provider unavailable"))):
            response = self.client.post("/api/v1/interviews/practice/start", headers=headers, json={"scenario_id": "1"})
        self.assertEqual(response.status_code, 503)
        history = self.client.get("/api/v1/interviews/history", headers=headers).json()["data"]
        self.assertEqual(history, [])

    def test_06_interview_end_to_end_with_mocked_ai(self):
        headers = self.login_headers(f"138{uuid.uuid4().int % 100_000_000:08d}")
        report = {"overall_score": 88, "grade": "优秀", "dimension_scores": {
                  "思想认识": 88, "表达逻辑": 86, "入党动机": 90, "理论掌握": 84, "应变能力": 87},
                  "dimension_analysis": [{"name": "思想认识", "score": 88, "suggestion": "保持"}],
                  "strengths": ["表达清晰"], "weaknesses": [], "suggestion": "继续学习", "total_rounds": 2}
        turn = {"question": "请继续", "comment": "回答具体", "finished": False, "phase": "模型随意返回的错误阶段",
                "observations": {"表达逻辑": {"observed": True, "score": 86, "confidence": 0.8, "evidence": "表达清晰"}}}
        with patch("app.routers.interviews.ai_service.interview_start", new=AsyncMock(return_value={"question": "请介绍自己"})), \
             patch("app.routers.interviews.ai_service.interview_respond", new=AsyncMock(return_value=turn)), \
             patch("app.routers.interviews.ai_service.interview_report", new=AsyncMock(return_value=report)):
            started = self.client.post("/api/v1/interviews/practice/start", headers=headers, json={"scenario_id": "1"})
            self.assertEqual(started.status_code, 200)
            practice_id = started.json()["data"]["id"]
            phases = []
            early_end = self.client.post(f"/api/v1/interviews/practice/{practice_id}/end", headers=headers)
            self.assertEqual(early_end.status_code, 400)
            for index, answer in enumerate(("我是一名大学生", "我希望为同学服务", "我重视理论学习", "我会结合实践理解", "我会辨析信息来源", "我会坚持原则并沟通")):
                submission_id = f"interview-turn-{index + 1}"
                response = self.client.post(f"/api/v1/interviews/practice/{practice_id}/respond", headers=headers, json={"content": answer, "submission_id": submission_id})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["data"]["answered_count"], index + 1)
                self.assertEqual(response.json()["data"]["user_message"]["round_number"], index + 1)
                self.assertEqual(response.json()["data"]["ai_message"]["round_number"], index + 1)
                if index == 0:
                    duplicate = self.client.post(f"/api/v1/interviews/practice/{practice_id}/respond", headers=headers, json={"content": answer, "submission_id": submission_id})
                    self.assertEqual(duplicate.status_code, 200)
                    self.assertEqual(duplicate.json()["data"]["user_message"]["id"], response.json()["data"]["user_message"]["id"])
                phases.append(response.json()["data"]["phase"])
                live_score = response.json()["data"]["live_evaluation"]["dimensions"]["表达逻辑"]["score"]
                if index == 0:
                    self.assertIsNone(live_score)
                if index == 1:
                    self.assertEqual(live_score, 86)
            self.assertEqual(phases, ["自我认知", "入党动机", "理论考察", "理论考察", "情景假设", "情景假设"])
            self.assertEqual(response.json()["data"]["status"], "awaiting_report")
            self.assertIsNone(response.json()["data"]["current_question_number"])
            self.assertEqual(response.json()["data"]["live_evaluation"]["dimensions"]["表达逻辑"]["score"], 86)
            ended = self.client.post(f"/api/v1/interviews/practice/{practice_id}/end", headers=headers)
            self.assertEqual(ended.json()["data"]["overall_score"], 87)
            self.assertEqual(self.client.get(f"/api/v1/interviews/practice/{practice_id}/report", headers=headers).status_code, 200)

    def test_07_debate_tour_and_template_report_persistence(self):
        headers = self.login_headers(f"137{uuid.uuid4().int % 100_000_000:08d}")
        feedback = {"overall_score": 82, "dimension_scores": {
                    "逻辑严谨性": 82, "知识运用": 80, "思辨深度": 83, "语言表达": 81, "临场反应": 84},
                    "strengths": ["论点清晰"], "weaknesses": [], "suggestion": "补充论据"}
        debate = self.client.post("/api/v1/debates/practice/start", headers=headers, json={"topic_id": "1", "stance": "pro"})
        session_id = debate.json()["data"]["id"]
        with patch("app.routers.debates.ai_service.debate_argue", new=AsyncMock(return_value="这是反方回应")), \
             patch("app.routers.debates.ai_service.debate_feedback", new=AsyncMock(return_value=feedback)):
            for index, argument in enumerate(("我的核心观点", "针对对方论据的质询", "回应质询并补充论据", "总结我方立场并回应辩题")):
                response = self.client.post(f"/api/v1/debates/practice/{session_id}/argue", headers=headers, json={"argument": argument, "submission_id": f"quick-turn-{index + 1}"})
                self.assertEqual(response.status_code, 200)
                if index == 0:
                    duplicate = self.client.post(f"/api/v1/debates/practice/{session_id}/argue", headers=headers, json={"argument": argument, "submission_id": "quick-turn-1"})
                    self.assertEqual(duplicate.json()["data"]["user_message_id"], response.json()["data"]["user_message_id"])
            self.assertEqual(response.json()["data"]["status"], "awaiting_feedback")
            first_end = self.client.post(f"/api/v1/debates/practice/{session_id}/end", headers=headers)
            self.assertEqual(first_end.json()["data"]["overall_score"], 82)
            points_after_first = self.client.get("/api/v1/users/profile", headers=headers).json()["data"]["total_points"]
            second_end = self.client.post(f"/api/v1/debates/practice/{session_id}/end", headers=headers)
            points_after_second = self.client.get("/api/v1/users/profile", headers=headers).json()["data"]["total_points"]
            self.assertEqual(second_end.json()["data"], first_end.json()["data"])
            self.assertEqual(points_after_second, points_after_first)
        with patch("app.routers.tours.ai_service.tour_report", new=AsyncMock(return_value="研学心得正文")):
            points_before_tour = self.client.get("/api/v1/users/profile", headers=headers).json()["data"]["total_points"]
            tour = self.client.post("/api/v1/tours/generate-report", headers=headers, json={"site_id": "1", "qa_history": ["问答记录"]})
            self.assertEqual(tour.json()["data"]["report"], "研学心得正文")
            repeated_tour = self.client.post("/api/v1/tours/generate-report", headers=headers, json={"site_id": "1", "qa_history": ["重复请求"]})
            self.assertEqual(repeated_tour.json()["data"]["id"], tour.json()["data"]["id"])
            points_after_tour = self.client.get("/api/v1/users/profile", headers=headers).json()["data"]["total_points"]
            self.assertEqual(points_after_tour - points_before_tour, 3)
            point_rows = self.client.get("/api/v1/users/points", headers=headers).json()["data"]
            self.assertEqual(point_rows["by_module"]["tour"], 3)
        with patch("app.routers.knowledge.ai_service.generate_template", new=AsyncMock(return_value="思想汇报正文")):
            template = self.client.post("/api/v1/knowledge/templates/generate", headers=headers, json={"template_id": "2", "requirements": "结合学习经历"})
            self.assertEqual(template.json()["data"]["content"], "思想汇报正文")
        reports = self.client.get("/api/v1/users/reports", headers=headers).json()["data"]
        self.assertEqual({row["type"] for row in reports}, {"debate", "tour"})
        self.assertTrue(all(row["source_record_id"] for row in reports))
        template_history = self.client.get("/api/v1/knowledge/templates/history", headers=headers).json()["data"]
        self.assertEqual(len(template_history), 1)
        growth = self.client.get("/api/v1/users/growth", headers=headers).json()["data"]
        self.assertEqual(growth["current_reports"], len(reports))
        practices = self.client.get("/api/v1/users/practices", headers=headers).json()["data"]
        self.assertTrue({"debate", "tour"}.issubset({row["module"] for row in practices["items"]}))
        self.assertEqual(practices["summary"]["completed"], 2)
        self.assertEqual(practices["summary"]["legacy"], 0)

    def test_08_ai_payload_validation_rejects_fake_scores(self):
        with self.assertRaises(AIResponseValidationError):
            validate_interview_report({"overall_score": 175})
        with self.assertRaises(AIResponseValidationError):
            validate_debate_feedback({"overall_score": 78, "dimension_scores": {}})
        interview_turn = validate_interview_turn({
            "question": "继续", "observations": {
                "表达逻辑": {"observed": True, "score": 88, "confidence": .8, "evidence": ""},
            },
        })
        self.assertFalse(interview_turn["observations"]["表达逻辑"]["observed"])
        debate_turn = validate_debate_turn({
            "argument": "回应", "argument_map": {"claims": "不应按字符拆分", "gaps": ["缺少数据"]},
        })
        self.assertEqual(debate_turn["argument_map"]["claims"], [])

    def test_09_community_like_and_task_workflow(self):
        student = self.login_headers(f"133{uuid.uuid4().int % 100_000_000:08d}")
        teacher_phone = f"132{uuid.uuid4().int % 100_000_000:08d}"
        teacher = self.login_headers(teacher_phone)
        with SessionLocal() as db:
            user = db.query(User).filter(User.phone == teacher_phone).one()
            user.role = "teacher"
            db.commit()
        teacher = self.login_headers(teacher_phone)
        post = self.client.post("/api/v1/community/posts", headers=student, json={"title": "幂等点赞测试", "content": "同一用户重复点赞不应重复计数", "category": "测试", "is_question": True}).json()["data"]
        first = self.client.post(f"/api/v1/community/posts/{post['id']}/like", headers=student).json()["data"]
        second = self.client.post(f"/api/v1/community/posts/{post['id']}/like", headers=student).json()["data"]
        self.assertEqual(first["likes"], second["likes"])
        task = self.client.post("/api/v1/community/tasks", headers=teacher, json={"title": "学习任务", "description": "提交真实心得", "deadline": "2026-12-31"}).json()["data"]
        submitted = self.client.post(f"/api/v1/community/tasks/{task['id']}/submissions", headers=student, json={"content": "这是我的学习心得"})
        self.assertEqual(submitted.status_code, 200)
        rows = self.client.get(f"/api/v1/community/tasks/{task['id']}/submissions", headers=teacher).json()["data"]
        reviewed = self.client.put(f"/api/v1/community/tasks/submissions/{rows[0]['id']}/review", headers=teacher, json={"score": 90, "feedback": "观点清晰"})
        self.assertEqual(reviewed.json()["data"]["score"], 90)

    def test_10_full_debate_step_machine_and_resume(self):
        headers = self.login_headers(f"136{uuid.uuid4().int % 100_000_000:08d}")
        started = self.client.post("/api/v1/debates/practice/start", headers=headers, json={"topic_id": "1", "stance": "con", "mode": "full"})
        self.assertEqual(started.status_code, 200)
        session_id = started.json()["data"]["id"]
        mock_turn = AsyncMock(return_value={
            "argument": "AI回应", "coach_feedback": {"stage_fit": "匹配", "strength": "观点清楚", "next_action": "补充依据"},
            "argument_map": {"claims": ["主张"], "evidence": [], "reasoning": ["推理"], "gaps": ["缺少事实"]},
        })
        expected_steps = ["user_opening", "user_question", "user_counter_answer", "user_rebuttal", "user_defense", "user_closing"]
        with patch("app.routers.debates.ai_service.debate_argue", new=mock_turn):
            for index, step in enumerate(expected_steps):
                response = self.client.post(f"/api/v1/debates/practice/{session_id}/argue", headers=headers, json={"argument": f"第{index + 1}步陈词", "submission_id": f"full-turn-{index + 1}"})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["data"]["step"], step)
        self.assertEqual(response.json()["data"]["next_stage"], "finished")
        self.assertEqual(response.json()["data"]["status"], "awaiting_feedback")
        resumed = self.client.post("/api/v1/debates/practice/start", headers=headers, json={"topic_id": "1", "stance": "con", "mode": "full"})
        self.assertTrue(resumed.json()["data"]["resumed"])
        self.assertEqual(resumed.json()["data"]["status"], "awaiting_feedback")
        called_steps = [call.kwargs["step"] for call in mock_turn.await_args_list]
        self.assertEqual(called_steps, expected_steps)

    def test_11_debate_prompt_context_is_bounded_for_long_sessions(self):
        service = AIService()
        conversation = [
            {"stance": "pro" if index % 2 == 0 else "con", "content": f"第{index}轮：" + "历史内容" * 700}
            for index in range(20)
        ]
        response = {
            "argument": "反方回应",
            "coach_feedback": {"stage_fit": "符合", "strength": "清晰", "next_action": "补充例证"},
            "argument_map": {"claims": ["主张"], "evidence": [], "reasoning": [], "gaps": []},
        }
        with patch.object(service, "_call_api", new=AsyncMock(return_value=json.dumps(response))) as call:
            result = asyncio.run(service.debate_argue(
                topic="基层选举的规范", stance="pro", argument="当前陈词" + "论述" * 4000,
                conversation=conversation,
                evidence=[{"document_title": "资料" + "标题" * 100, "excerpt": "引用" * 2000}] * 8,
            ))
        prompt = call.await_args.args[0][1]["content"]
        self.assertIn("最近辩论交锋", prompt)
        self.assertIn("[内容过长，以下已截断]", prompt)
        self.assertLessEqual(len(prompt), 23000)
        self.assertEqual(call.await_args.kwargs["timeout"], 60.0)
        self.assertTrue(call.await_args.kwargs["disable_thinking"])
        self.assertTrue(call.await_args.kwargs["json_mode"])
        self.assertEqual(result["argument"], "反方回应")

    def test_12_debate_accepts_plain_ai_reply_when_json_is_invalid(self):
        service = AIService()
        plain_reply = "对方的论据仍缺少可核验的事实支撑，应当补充具体制度依据。"
        with patch.object(service, "_call_api", new=AsyncMock(return_value=plain_reply)):
            result = asyncio.run(service.debate_argue(
                topic="基层选举的规范", stance="pro", argument="我方观点", conversation=[],
            ))
        self.assertEqual(result["argument"], plain_reply)
        with self.assertRaisesRegex(AIResponseValidationError, "不是有效 JSON"):
            service._parse_json("这不是 JSON")

    def test_13_debate_feedback_retries_once_after_invalid_json(self):
        service = AIService()
        feedback = {
            "overall_score": 82,
            "dimension_scores": {"逻辑严谨性": 82, "知识运用": 80, "思辨深度": 83, "语言表达": 81, "临场反应": 84},
            "strengths": ["论点清晰"], "weaknesses": ["可补充事实"], "suggestion": "补充论据",
        }
        with patch.object(service, "_call_api", new=AsyncMock(side_effect=["非 JSON 内容", json.dumps(feedback)])) as call:
            result = asyncio.run(service.debate_feedback("基层选举的规范", [], user_stance="pro"))
        self.assertEqual(call.await_count, 2)
        self.assertTrue(call.await_args.kwargs["disable_thinking"])
        self.assertTrue(call.await_args.kwargs["json_mode"])
        self.assertEqual(result["overall_score"], 82)


if __name__ == "__main__":
    unittest.main()
