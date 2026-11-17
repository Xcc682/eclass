# ruff: noqa: E402
# 说明：必须先调用 configure_test_environment()，再导入读取环境变量的 app 模块。
import unittest
import uuid
from unittest.mock import AsyncMock, patch

from test_env import configure_test_environment

configure_test_environment()

from fastapi.testclient import TestClient

from app.immersive_branch_content import BRANCH_STORIES
from app.main import app

STAGES = ("route", "evidence", "judgment")


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
        registered = self.client.post(
            "/api/v1/auth/register",
            json={"phone": phone, "password": "test-password"},
        )
        self.assertEqual(registered.status_code, 201)
        return {"Authorization": f"Bearer {registered.json()['data']['token']}"}

    def detail(self, book_id: str, headers: dict[str, str]) -> dict:
        response = self.client.get(f"/api/v1/immersive/books/{book_id}", headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["data"]

    def advance(self, book_id: str, spread_id: str, headers: dict[str, str]) -> dict:
        response = self.client.post(
            f"/api/v1/immersive/books/{book_id}/advance",
            headers=headers,
            json={"from_spread_id": spread_id, "direction": "next"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["data"]

    def discover_all(self, book_id: str, spread: dict, headers: dict[str, str]) -> None:
        for hotspot in spread["scene"].get("hotspots", []):
            response = self.client.patch(
                f"/api/v1/immersive/books/{book_id}/progress",
                headers=headers,
                json={"discovered_hotspot": hotspot["id"]},
            )
            self.assertEqual(response.status_code, 200, response.text)

    def option_ids(self, book_id: str, stage_index: int) -> tuple[str, str]:
        options = BRANCH_STORIES[book_id][stage_index]["options"]
        correct = next(index for index, option in enumerate(options, 1) if option["correct"])
        wrong = next(index for index, option in enumerate(options, 1) if not option["correct"])
        stage = STAGES[stage_index]
        return f"{stage}-option-{correct}", f"{stage}-option-{wrong}"

    def walk_to_ending(self, book_id: str, headers: dict[str, str], *, take_wrong_route: bool = False) -> dict:
        detail = self.detail(book_id, headers)
        spreads = {spread["id"]: spread for spread in detail["spreads"]}
        current = spreads[detail["progress"]["current_spread_id"]]
        stage_index = 0

        while current["type"] != "ending":
            if current["type"] == "exploration":
                self.discover_all(book_id, current, headers)
            if current["type"] == "decision":
                correct_id, wrong_id = self.option_ids(book_id, stage_index)
                if take_wrong_route and stage_index == 0:
                    submission_id = f"wrong-{uuid.uuid4()}"
                    wrong = self.client.post(
                        f"/api/v1/immersive/books/{book_id}/choices",
                        headers=headers,
                        json={
                            "decision_spread_id": current["id"],
                            "option_id": wrong_id,
                            "submission_id": submission_id,
                        },
                    )
                    self.assertEqual(wrong.status_code, 200, wrong.text)
                    wrong_data = wrong.json()["data"]
                    self.assertEqual(wrong_data["result"], "detour")
                    self.assertEqual(wrong_data["spread"]["type"], "detour")
                    duplicate = self.client.post(
                        f"/api/v1/immersive/books/{book_id}/choices",
                        headers=headers,
                        json={
                            "decision_spread_id": current["id"],
                            "option_id": wrong_id,
                            "submission_id": submission_id,
                        },
                    )
                    self.assertEqual(duplicate.status_code, 200, duplicate.text)
                    self.assertEqual(
                        duplicate.json()["data"]["progress"]["route"]["attempts"][current["id"]],
                        1,
                    )
                    current = self.advance(book_id, wrong_data["spread"]["id"], headers)["spread"]
                    self.assertEqual(current["type"], "decision")
                chosen = self.client.post(
                    f"/api/v1/immersive/books/{book_id}/choices",
                    headers=headers,
                    json={
                        "decision_spread_id": current["id"],
                        "option_id": correct_id,
                        "submission_id": f"correct-{uuid.uuid4()}",
                    },
                )
                self.assertEqual(chosen.status_code, 200, chosen.text)
                self.assertEqual(chosen.json()["data"]["result"], "correct")
                current = chosen.json()["data"]["spread"]
                stage_index += 1
                continue
            current = self.advance(book_id, current["id"], headers)["spread"]
        return self.detail(book_id, headers)

    def test_all_books_have_three_private_branch_decisions(self):
        headers = self.login()
        summaries = []
        for module in ("history", "tour"):
            response = self.client.get("/api/v1/immersive/books", params={"module": module}, headers=headers)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(len(response.json()["data"]), 5)
            summaries.extend(response.json()["data"])

        branch_images = set()
        for summary in summaries:
            detail = self.detail(summary["id"], headers)
            self.assertEqual(detail["version"], 5)
            decisions = [spread for spread in detail["spreads"] if spread["type"] == "decision"]
            detours = [spread for spread in detail["spreads"] if spread["type"] == "detour"]
            self.assertEqual(len(decisions), 3)
            self.assertEqual(len(detours), 6)
            self.assertEqual(detail["progress"]["route"]["required_count"], 3)
            for decision in decisions:
                self.assertEqual(len(decision["scene"]["options"]), 3)
                self.assertTrue(decision["scene"].get("required_clues"))
                for option in decision["scene"]["options"]:
                    self.assertEqual(set(option), {"id", "label"})
            for detour in detours:
                self.assertNotIn(detour["image_url"], branch_images)
                branch_images.add(detour["image_url"])
                self.assertTrue(detour["image_url"].endswith(".webp"))
                self.assertTrue(detour["scene"].get("detour_body"))
                self.assertTrue(detour["sources"])
        self.assertEqual(len(branch_images), 60)

    def test_wrong_route_backtracks_and_completion_is_idempotent(self):
        headers = self.login()
        before = self.client.get("/api/v1/users/profile", headers=headers).json()["data"]["total_points"]
        detail = self.walk_to_ending("history-1", headers, take_wrong_route=True)
        route = detail["progress"]["route"]
        self.assertEqual(route["solved_count"], 3)
        self.assertEqual(len(route["wrong_routes"]), 1)
        first = self.client.post("/api/v1/immersive/books/history-1/complete", headers=headers)
        second = self.client.post("/api/v1/immersive/books/history-1/complete", headers=headers)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertFalse(first.json()["data"]["already_completed"])
        self.assertTrue(second.json()["data"]["already_completed"])
        after = self.client.get("/api/v1/users/profile", headers=headers).json()["data"]["total_points"]
        self.assertEqual(after - before, 2)

    def test_tour_report_failure_preserves_route_and_awards_once(self):
        headers = self.login()
        before = self.client.get("/api/v1/users/profile", headers=headers).json()["data"]["total_points"]
        detail = self.walk_to_ending("tour-1", headers)
        saved = self.client.patch(
            "/api/v1/immersive/books/tour-1/progress",
            headers=headers,
            json={"note": "我从地形、组织网络和群众支持之间，看到了根据地建设的现实基础。"},
        )
        self.assertEqual(saved.status_code, 200, saved.text)
        with patch("app.routers.immersive.ai_service.tour_report", new=AsyncMock(side_effect=RuntimeError("offline"))):
            failed = self.client.post("/api/v1/immersive/books/tour-1/complete", headers=headers)
        self.assertEqual(failed.status_code, 503, failed.text)
        progress = self.detail("tour-1", headers)["progress"]
        self.assertFalse(progress["completed"])
        self.assertEqual(progress["route"]["solved_count"], 3)
        self.assertEqual(progress["current_spread_id"], detail["progress"]["current_spread_id"])
        with patch("app.routers.immersive.ai_service.tour_report", new=AsyncMock(return_value="研学报告内容完整。")):
            first = self.client.post("/api/v1/immersive/books/tour-1/complete", headers=headers)
            second = self.client.post("/api/v1/immersive/books/tour-1/complete", headers=headers)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertTrue(first.json()["data"]["report"])
        self.assertTrue(second.json()["data"]["already_completed"])
        after = self.client.get("/api/v1/users/profile", headers=headers).json()["data"]["total_points"]
        self.assertEqual(after - before, 3)


if __name__ == "__main__":
    unittest.main()
