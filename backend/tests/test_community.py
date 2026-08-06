import unittest
import uuid
import shutil
from pathlib import Path

from test_env import configure_test_environment

configure_test_environment()

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.main import app
from app.models.user import User


class CommunityCollaborationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = TestClient(app)
        cls.client = cls.context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)
        shutil.rmtree(Path(__file__).resolve().parent / "_community_storage", ignore_errors=True)

    def login(self, prefix="137"):
        phone = f"{prefix}{uuid.uuid4().int % 100_000_000:08d}"
        registered = self.client.post("/api/v1/auth/register", json={"phone": phone, "password": "test-password"})
        self.assertEqual(registered.status_code, 201)
        return phone, {"Authorization": f"Bearer {registered.json()['data']['token']}"}

    def promote(self, phone, role="teacher"):
        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.phone == phone))
            user.role = role
            db.commit()

    def test_post_idempotency_notifications_favorites_and_moderation(self):
        owner_phone, owner = self.login()
        _, reader = self.login("136")
        submission_id = f"post-{uuid.uuid4()}"
        body = {"title": "如何理解实事求是", "content": "请结合党史资料讨论。", "category": "党史", "is_question": True, "submission_id": submission_id}
        first = self.client.post("/api/v1/community/posts", headers=owner, json=body)
        duplicate = self.client.post("/api/v1/community/posts", headers=owner, json=body)
        self.assertEqual(first.json()["data"]["id"], duplicate.json()["data"]["id"])
        post_id = first.json()["data"]["id"]

        self.assertEqual(self.client.post(f"/api/v1/community/posts/{post_id}/favorite", headers=reader).json()["data"]["favorites"], 1)
        self.assertEqual(self.client.post(f"/api/v1/community/posts/{post_id}/favorite", headers=reader).json()["data"]["favorites"], 1)
        reply_id = self.client.post(f"/api/v1/community/posts/{post_id}/replies", headers=reader, json={"content": "要从具体事实和实践效果出发。", "submission_id": "reply-0001"}).json()["data"]["id"]
        notifications = self.client.get("/api/v1/community/notifications", headers=owner).json()["data"]
        self.assertEqual(notifications["unread"], 1)

        accepted = self.client.post(f"/api/v1/community/posts/{post_id}/resolve/{reply_id}", headers=owner)
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.json()["data"]["points_awarded"], 2)
        again = self.client.post(f"/api/v1/community/posts/{post_id}/resolve/{reply_id}", headers=owner)
        self.assertEqual(again.status_code, 200)
        self.assertEqual(again.json()["data"]["points_awarded"], 0)

        report = self.client.post("/api/v1/community/reports", headers=reader, json={"target_type": "post", "target_id": post_id, "reason": "需要核查", "detail": "测试人工审核流程"})
        self.assertEqual(report.status_code, 200)
        self.promote(owner_phone)
        queue = self.client.get("/api/v1/community/moderation/reports", headers=owner).json()["data"]
        target = next(item for item in queue if item["target_id"] == post_id)
        hidden = self.client.put(f"/api/v1/community/moderation/reports/{target['id']}", headers=owner, json={"action": "hide", "resolution": "暂时隐藏"})
        self.assertEqual(hidden.status_code, 200)
        self.assertEqual(self.client.get(f"/api/v1/community/posts/{post_id}").status_code, 404)

    def test_task_rubric_review_points_and_locked_rubric(self):
        teacher_phone, teacher = self.login()
        self.promote(teacher_phone)
        _, student = self.login("135")
        rubric = [{"title": "准确性", "description": "事实准确", "weight": 60}, {"title": "思考", "description": "联系实际", "weight": 40}]
        created = self.client.post("/api/v1/community/tasks", headers=teacher, json={"title": "社区协作学习任务", "description": "提交学习心得", "status": "published", "rubric": rubric})
        self.assertEqual(created.status_code, 200)
        task_id = created.json()["data"]["id"]
        submitted = self.client.post(f"/api/v1/community/tasks/{task_id}/submission/submit", headers=student, json={"content": "我完成了学习并形成自己的认识。", "attachment_ids": []})
        submission_id = submitted.json()["data"]["id"]
        criteria = created.json()["data"]["rubric"]
        scores = [{"criterion_id": item["id"], "score": 80, "comment": "达到要求"} for item in criteria]
        first = self.client.put(f"/api/v1/community/tasks/submissions/{submission_id}/review", headers=teacher, json={"rubric_scores": scores, "feedback": "完成较好", "next_step": "补充实践例证"})
        second = self.client.put(f"/api/v1/community/tasks/submissions/{submission_id}/review", headers=teacher, json={"rubric_scores": scores, "feedback": "完成较好", "next_step": "补充实践例证"})
        self.assertEqual(first.json()["data"]["points_awarded"], 3)
        self.assertEqual(second.json()["data"]["points_awarded"], 0)
        points = self.client.get("/api/v1/users/points", headers=student).json()["data"]
        self.assertEqual(points["by_module"]["community"], 3)

        changed = [{"title": "内容", "description": "新量规", "weight": 50}, {"title": "表达", "description": "新量规", "weight": 50}]
        response = self.client.put(f"/api/v1/community/tasks/{task_id}", headers=teacher, json={"title": "社区协作学习任务", "description": "仅修改说明", "status": "published", "rubric": changed})
        self.assertEqual(response.status_code, 409)

    def test_attachment_validation_and_protected_task_file(self):
        _, user = self.login()
        invalid = self.client.post("/api/v1/community/attachments/upload", headers=user, data={"purpose": "post_image"}, files={"file": ("fake.png", b"not-an-image", "image/png")})
        self.assertEqual(invalid.status_code, 415)
        uploaded = self.client.post("/api/v1/community/attachments/upload", headers=user, data={"purpose": "task"}, files={"file": ("notes.txt", "学习资料".encode("utf-8"), "text/plain")})
        self.assertEqual(uploaded.status_code, 201)
        attachment_id = uploaded.json()["data"]["id"]
        self.assertEqual(self.client.get(f"/api/v1/community/attachments/{attachment_id}").status_code, 401)
        self.assertEqual(self.client.get(f"/api/v1/community/attachments/{attachment_id}", headers=user).status_code, 200)


if __name__ == "__main__":
    unittest.main()
