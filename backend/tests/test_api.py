import unittest
import uuid
from unittest.mock import AsyncMock, patch

from test_env import configure_test_environment

configure_test_environment()

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models.user import User
from app.services.ai_service import AIResponseValidationError, validate_debate_feedback, validate_interview_report


class ApiAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client_context = TestClient(app)
        cls.client = cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_context.__exit__(None, None, None)

    def login_headers(self, phone: str) -> dict[str, str]:
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
        phone = f"139{uuid.uuid4().int % 100_000_000:08d}"
        headers = self.login_headers(phone)
        profile = self.client.get("/api/v1/users/profile", headers=headers)
        self.assertEqual(profile.status_code, 200)
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
        with patch("app.routers.interviews.ai_service.interview_start", new=AsyncMock(return_value={"question": "请介绍自己"})), \
             patch("app.routers.interviews.ai_service.interview_respond", new=AsyncMock(return_value={"question": "请继续", "点评": "回答具体", "结束": False})), \
             patch("app.routers.interviews.ai_service.interview_report", new=AsyncMock(return_value=report)):
            started = self.client.post("/api/v1/interviews/practice/start", headers=headers, json={"scenario_id": "1"})
            self.assertEqual(started.status_code, 200)
            practice_id = started.json()["data"]["id"]
            for answer in ("我是一名大学生", "我希望为同学服务"):
                self.assertEqual(self.client.post(f"/api/v1/interviews/practice/{practice_id}/respond", headers=headers, json={"content": answer}).status_code, 200)
            ended = self.client.post(f"/api/v1/interviews/practice/{practice_id}/end", headers=headers)
            self.assertEqual(ended.json()["data"]["overall_score"], 88)
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
            for argument in ("我的核心观点", "针对对方论据的质询", "回应质询并补充论据"):
                self.assertEqual(self.client.post(f"/api/v1/debates/practice/{session_id}/argue", headers=headers, json={"argument": argument}).status_code, 200)
            self.assertEqual(self.client.post(f"/api/v1/debates/practice/{session_id}/end", headers=headers).json()["data"]["overall_score"], 82)
        with patch("app.routers.tours.ai_service.tour_report", new=AsyncMock(return_value="研学心得正文")):
            tour = self.client.post("/api/v1/tours/generate-report", headers=headers, json={"site_id": "1", "qa_history": ["问答记录"]})
            self.assertEqual(tour.json()["data"]["report"], "研学心得正文")
        with patch("app.routers.knowledge.ai_service.generate_template", new=AsyncMock(return_value="思想汇报正文")):
            template = self.client.post("/api/v1/knowledge/templates/generate", headers=headers, json={"template_id": "2", "requirements": "结合学习经历"})
            self.assertEqual(template.json()["data"]["content"], "思想汇报正文")
        reports = self.client.get("/api/v1/users/reports", headers=headers).json()["data"]
        self.assertGreaterEqual(len(reports), 3)

    def test_08_ai_payload_validation_rejects_fake_scores(self):
        with self.assertRaises(AIResponseValidationError):
            validate_interview_report({"overall_score": 175})
        with self.assertRaises(AIResponseValidationError):
            validate_debate_feedback({"overall_score": 78, "dimension_scores": {}})

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


if __name__ == "__main__":
    unittest.main()
