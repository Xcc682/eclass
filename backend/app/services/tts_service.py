"""文本转语音服务：调用微软 Edge 神经语音把中文文本合成为 mp3，并做内容寻址缓存。

缓存键是 sha256(文本 + 语音)，同一段讲解重复请求时无需再次访问上游；合成先写入
进程内唯一的临时文件，成功后才原子替换进缓存，避免残缺文件被后续请求命中。
"""
import hashlib
import logging
import os
import uuid
from pathlib import Path

import edge_tts

from app.config import settings

ALLOWED_VOICES = frozenset({
    "zh-CN-XiaoxiaoNeural",
    "zh-CN-YunxiNeural",
    "zh-CN-YunyangNeural",
})
DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"
CACHE_HIT = "hit"
CACHE_MISS = "miss"
AUDIO_SUFFIX = ".mp3"
logger = logging.getLogger("app.tts")


class TTSSynthesisError(RuntimeError):
    """上游语音合成服务不可用，或返回了空音频。"""


def resolve_voice(voice: str | None) -> str:
    """返回白名单内的语音；未知语音回落到配置的默认值。"""
    if voice in ALLOWED_VOICES:
        return voice
    configured = settings.TTS_DEFAULT_VOICE
    return configured if configured in ALLOWED_VOICES else DEFAULT_VOICE


def _cache_path(text: str, voice: str) -> Path:
    """按 sha256(文本 + 语音) 计算缓存文件路径。"""
    digest = hashlib.sha256(f"{text}{voice}".encode()).hexdigest()
    return Path(settings.TTS_STORAGE_DIR) / f"{digest}{AUDIO_SUFFIX}"


async def synthesize(text: str, voice: str | None = None) -> tuple[Path, str]:
    """把中文文本合成为 mp3，返回 (音频路径, "hit" 或 "miss")。

    文本为空或超过 TTS_MAX_CHARS 时抛 ValueError；上游失败时清理临时文件并抛
    TTSSynthesisError，确保残缺音频不会进入缓存。
    """
    clean = (text or "").strip()
    if not clean:
        raise ValueError("待合成文本不能为空")
    if len(clean) > settings.TTS_MAX_CHARS:
        raise ValueError(f"待合成文本不能超过 {settings.TTS_MAX_CHARS} 字")

    resolved = resolve_voice(voice)
    cache_path = _cache_path(clean, resolved)
    if cache_path.is_file() and cache_path.stat().st_size > 0:
        logger.info("TTS cache hit voice=%s chars=%s", resolved, len(clean))
        return cache_path, CACHE_HIT

    storage = cache_path.parent
    storage.mkdir(parents=True, exist_ok=True)
    temp_path = storage / f".{cache_path.stem}.{os.getpid()}.{uuid.uuid4().hex}.part"
    try:
        await edge_tts.Communicate(clean, resolved).save(str(temp_path))
    except Exception as exc:
        temp_path.unlink(missing_ok=True)
        logger.warning("TTS synthesis failed voice=%s chars=%s: %s", resolved, len(clean), exc)
        raise TTSSynthesisError("语音合成服务暂不可用") from exc
    if not temp_path.is_file() or temp_path.stat().st_size == 0:
        temp_path.unlink(missing_ok=True)
        logger.warning("TTS upstream returned empty audio voice=%s chars=%s", resolved, len(clean))
        raise TTSSynthesisError("语音合成服务返回了空音频")
    os.replace(temp_path, cache_path)
    logger.info("TTS synthesized voice=%s chars=%s", resolved, len(clean))
    return cache_path, CACHE_MISS
