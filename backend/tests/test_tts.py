"""文本转语音服务的单测：缓存命中、参数校验、语音回落与上游失败清理。"""
import asyncio
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from test_env import configure_test_environment

configure_test_environment()

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402
from app.services import tts_service  # noqa: E402

FAKE_MP3 = b"ID3\x04\x00\x00\x00\x00\x00\x00fake-mp3-payload"


class FakeCommunicate:
    """模拟 edge_tts.Communicate：记录调用；fail=True 时先写半成品再抛错。"""

    instances: list = []
    fail = False

    def __init__(self, text: str, voice: str):
        self.text = text
        self.voice = voice
        FakeCommunicate.instances.append(self)

    async def save(self, path: str) -> None:
        target = Path(path)
        if FakeCommunicate.fail:
            target.write_bytes(b"partial-audio")
            raise ConnectionError("upstream unreachable")
        target.write_bytes(FAKE_MP3)


class _IsolatedTTSTestCase(unittest.TestCase):
    """为每个用例准备独立缓存目录，并用假实现替换真实上游。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.storage = Path(self._tmp.name)
        storage_patch = patch.object(settings, "TTS_STORAGE_DIR", str(self.storage))
        storage_patch.start()
        self.addCleanup(storage_patch.stop)
        FakeCommunicate.instances = []
        FakeCommunicate.fail = False
        communicate_patch = patch.object(tts_service.edge_tts, "Communicate", FakeCommunicate)
        communicate_patch.start()
        self.addCleanup(communicate_patch.stop)


class TTSServiceTests(_IsolatedTTSTestCase):
    def test_cache_hit_skips_repeated_synthesis(self):
        first_path, first_state = asyncio.run(tts_service.synthesize("欢迎来到思政情景工坊。"))
        second_path, second_state = asyncio.run(tts_service.synthesize("欢迎来到思政情景工坊。"))
        self.assertEqual(first_state, "miss")
        self.assertEqual(second_state, "hit")
        self.assertEqual(first_path, second_path)
        self.assertEqual(len(FakeCommunicate.instances), 1)
        self.assertEqual(first_path.read_bytes(), FAKE_MP3)

    def test_empty_and_overlong_text_raise_value_error(self):
        with self.assertRaises(ValueError):
            asyncio.run(tts_service.synthesize("   "))
        with self.assertRaises(ValueError):
            asyncio.run(tts_service.synthesize("啊" * (settings.TTS_MAX_CHARS + 1)))
        self.assertEqual(FakeCommunicate.instances, [])

    def test_unknown_voice_falls_back_to_default(self):
        asyncio.run(tts_service.synthesize("请用默认语音朗读。", "en-US-EmmaMultilingualNeural"))
        self.assertEqual(FakeCommunicate.instances[0].voice, settings.TTS_DEFAULT_VOICE)

    def test_upstream_failure_leaves_no_partial_file(self):
        FakeCommunicate.fail = True
        with self.assertRaises(tts_service.TTSSynthesisError):
            asyncio.run(tts_service.synthesize("上游中断的朗读文本。"))
        self.assertEqual(list(self.storage.rglob("*")), [])
        FakeCommunicate.fail = False
        path, cache_state = asyncio.run(tts_service.synthesize("上游中断的朗读文本。"))
        self.assertEqual(cache_state, "miss")
        self.assertEqual(path.read_bytes(), FAKE_MP3)


class TTSEndpointTests(_IsolatedTTSTestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = TestClient(app)
        cls.client = cls.context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)

    def _auth_headers(self) -> dict:
        phone = f"139{uuid.uuid4().int % 100_000_000:08d}"
        registered = self.client.post("/api/v1/auth/register", json={"phone": phone, "password": "test-password"})
        self.assertEqual(registered.status_code, 201)
        return {"Authorization": f"Bearer {registered.json()['data']['token']}"}

    def test_endpoint_streams_mp3_with_cache_header(self):
        headers = self._auth_headers()
        body = {"text": "欢迎收听思政情景讲解。", "voice": "zh-CN-YunxiNeural"}
        first = self.client.post("/api/v1/media/tts", headers=headers, json=body)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.headers["content-type"], "audio/mpeg")
        self.assertEqual(first.headers["x-tts-cache"], "miss")
        self.assertEqual(first.content, FAKE_MP3)
        second = self.client.post("/api/v1/media/tts", headers=headers, json=body)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.headers["x-tts-cache"], "hit")
        self.assertEqual(len(FakeCommunicate.instances), 1)

    def test_endpoint_rejects_overlong_text(self):
        headers = self._auth_headers()
        response = self.client.post(
            "/api/v1/media/tts",
            headers=headers,
            json={"text": "啊" * (settings.TTS_MAX_CHARS + 1)},
        )
        self.assertEqual(response.status_code, 400)

    def test_endpoint_returns_503_when_upstream_unavailable(self):
        headers = self._auth_headers()
        FakeCommunicate.fail = True
        response = self.client.post(
            "/api/v1/media/tts",
            headers=headers,
            json={"text": "网络断开时的朗读请求。"},
        )
        self.assertEqual(response.status_code, 503)
        self.assertIn("语音合成服务暂不可用", response.json()["detail"])
        self.assertEqual(list(self.storage.rglob("*")), [])


if __name__ == "__main__":
    unittest.main()
