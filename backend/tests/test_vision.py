# ruff: noqa: E402
# 说明：必须先调用 configure_test_environment()，再导入读取环境变量的 app 模块。
import unittest
import uuid

from test_env import configure_test_environment

configure_test_environment()

from app.config import settings
from app.services import vision

PNG_DATA_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


class VisionInputTests(unittest.TestCase):
    def test_accepts_png_data_url(self):
        self.assertEqual(vision.sanitize_images([PNG_DATA_URL]), [PNG_DATA_URL])

    def test_ignores_empty_entries(self):
        self.assertEqual(vision.sanitize_images(["", "  "]), [])

    def test_rejects_remote_url_and_plain_text(self):
        for bad in ("https://example.com/a.png", "image/png;base64,AAAA", "data:text/plain;base64,AAAA"):
            with self.assertRaises(vision.ImageInputError):
                vision.sanitize_images([bad])

    def test_rejects_invalid_base64(self):
        with self.assertRaises(vision.ImageInputError):
            vision.sanitize_images(["data:image/png;base64,@@@not-base64@@@"])

    def test_rejects_too_many_images(self):
        limit = settings.VISION_MAX_IMAGES
        with self.assertRaises(vision.ImageInputError):
            vision.sanitize_images([PNG_DATA_URL] * (limit + 1))

    def test_rejects_oversized_image(self):
        original = settings.VISION_MAX_IMAGE_CHARS
        settings.VISION_MAX_IMAGE_CHARS = 16
        try:
            with self.assertRaises(vision.ImageInputError):
                vision.sanitize_images([PNG_DATA_URL])
        finally:
            settings.VISION_MAX_IMAGE_CHARS = original

    def test_with_images_builds_multimodal_parts(self):
        self.assertEqual(vision.with_images("你好", None), "你好")
        parts = vision.with_images("看图回答", [PNG_DATA_URL])
        self.assertEqual(parts[0], {"type": "text", "text": "看图回答"})
        self.assertEqual(parts[1]["type"], "image_url")
        self.assertEqual(parts[1]["image_url"]["url"], PNG_DATA_URL)


class VisionApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient

        from app.main import app

        cls.context = TestClient(app)
        cls.client = cls.context.__enter__()
        phone = f"135{uuid.uuid4().int % 100_000_000:08d}"
        registered = cls.client.post("/api/v1/auth/register", json={"phone": phone, "password": "test-password"})
        cls.headers = {"Authorization": f"Bearer {registered.json()['data']['token']}"}

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)

    def test_knowledge_ask_rejects_invalid_image_before_ai(self):
        response = self.client.post("/api/v1/knowledge/ask", headers=self.headers, json={
            "question": "这张图片里的内容是什么？",
            "images": ["https://example.com/a.png"],
            "submission_id": f"img-{uuid.uuid4()}",
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("图片", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
