import unittest
import uuid
from unittest.mock import AsyncMock, patch

from test_env import configure_test_environment

configure_test_environment()

from fastapi.testclient import TestClient

from app.main import app


class ImmersiveBookApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = TestClient(app)
        cls.client = cls.context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)

    def login(self) -> dict[str, str]:
        phone = f"136{uuid.uuid4().int % 100_000_000:08d}"
        response = self.client.post("/api/v1/auth/login", json={"phone": phone, "password": "test-password"})
        return {"Authorization": f"Bearer {response.json()['data']['token']}"}

    def test_ten_books_have_complete_spreads_and_sources(self):
        headers = self.login()
        history = self.client.get("/api/v1/immersive/books", params={"module": "history"}, headers=headers)
        tour = self.client.get("/api/v1/immersive/books", params={"module": "tour"}, headers=headers)
        self.assertEqual(history.status_code, 200)
        self.assertEqual(len(history.json()["data"]), 5)
        self.assertEqual(len(tour.json()["data"]), 5)
        book = self.client.get("/api/v1/immersive/books/history-1", headers=headers).json()["data"]
        self.assertEqual(len(book["spreads"]), 8)
        self.assertEqual([row["order_index"] for row in book["spreads"]], list(range(8)))
        self.assertTrue(all(row["scene"].get("reconstruction") for row in book["spreads"]))
        scene_urls = {row["image_url"] for row in book["spreads"]}
        self.assertEqual(len(scene_urls), 6)
        self.assertTrue(all(url.endswith(".webp") for url in scene_urls))
        self.assertEqual(book["version"], 2)
        self.assertTrue(book["spreads"][6]["sources"][0]["url"].startswith("https://"))

    def test_history_progress_validation_and_completion_are_idempotent(self):
        headers = self.login()
        before = self.client.get("/api/v1/users/profile", headers=headers).json()["data"]["total_points"]
        invalid = self.client.patch("/api/v1/immersive/books/history-1/progress", headers=headers, json={"discovered_hotspot": "not-real"})
        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(self.client.patch("/api/v1/immersive/books/history-1/progress", headers=headers, json={"discovered_hotspot": "clue-1"}).status_code, 200)
        self.assertEqual(self.client.patch("/api/v1/immersive/books/history-1/progress", headers=headers, json={
            "choice_spread_id": "history-1-05", "choice_option_id": "choice-1", "current_spread": 7,
        }).status_code, 200)
        first = self.client.post("/api/v1/immersive/books/history-1/complete", headers=headers)
        second = self.client.post("/api/v1/immersive/books/history-1/complete", headers=headers)
        self.assertEqual(first.status_code, 200)
        self.assertFalse(first.json()["data"]["already_completed"])
        self.assertTrue(second.json()["data"]["already_completed"])
        after = self.client.get("/api/v1/users/profile", headers=headers).json()["data"]["total_points"]
        self.assertEqual(after - before, 2)

    def test_tour_ai_failure_preserves_progress_and_success_awards_once(self):
        headers = self.login()
        before = self.client.get("/api/v1/users/profile", headers=headers).json()["data"]["total_points"]
        self.client.patch("/api/v1/immersive/books/tour-1/progress", headers=headers, json={
            "discovered_hotspot": "clue-1", "note": "我注意到地形、群众基础和组织建设之间存在紧密联系。", "current_spread": 7,
        })
        with patch("app.routers.immersive.ai_service.tour_report", new=AsyncMock(side_effect=RuntimeError("offline"))):
            failed = self.client.post("/api/v1/immersive/books/tour-1/complete", headers=headers)
        self.assertEqual(failed.status_code, 503)
        after_failure = self.client.get("/api/v1/users/profile", headers=headers).json()["data"]["total_points"]
        self.assertEqual(after_failure, before)
        progress = self.client.get("/api/v1/immersive/books/tour-1", headers=headers).json()["data"]["progress"]
        self.assertFalse(progress["completed"])
        self.assertGreaterEqual(len(progress["note"]), 20)
        with patch("app.routers.immersive.ai_service.tour_report", new=AsyncMock(return_value="这是一份由现场线索和研学手记生成的研学报告。")):
            first = self.client.post("/api/v1/immersive/books/tour-1/complete", headers=headers)
            second = self.client.post("/api/v1/immersive/books/tour-1/complete", headers=headers)
        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.json()["data"]["report"])
        self.assertTrue(second.json()["data"]["already_completed"])
        after = self.client.get("/api/v1/users/profile", headers=headers).json()["data"]["total_points"]
        self.assertEqual(after - before, 3)


if __name__ == "__main__":
    unittest.main()
