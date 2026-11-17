"""文本转语音接口：把讲解文本合成为 mp3 音频流，供播放与演示使用。"""
from collections.abc import Iterator
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.models.user import User
from app.security import get_current_user
from app.services import tts_service

router = APIRouter(prefix="/api/v1/media", tags=["语音合成"])
STREAM_CHUNK_SIZE = 64 * 1024


class TTSRequest(BaseModel):
    """语音合成请求：文本必填，语音可选（非法值由服务回落到默认语音）。"""

    text: str = Field(description="待合成的中文文本")
    voice: str | None = Field(default=None, description="语音名称，需在白名单内")


def _stream(path: Path) -> Iterator[bytes]:
    """按块读取音频文件，避免整段 mp3 一次性载入内存。"""
    with path.open("rb") as audio:
        while chunk := audio.read(STREAM_CHUNK_SIZE):
            yield chunk


@router.post("/tts")
async def text_to_speech(data: TTSRequest, _: User = Depends(get_current_user)) -> StreamingResponse:
    """需要登录的文本转语音接口，返回 audio/mpeg 流并标记缓存命中情况。"""
    try:
        path, cache_status = await tts_service.synthesize(data.text, data.voice)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except tts_service.TTSSynthesisError as exc:
        raise HTTPException(status_code=503, detail="语音合成服务暂不可用") from exc
    headers = {
        "X-TTS-Cache": cache_status,
        "Content-Disposition": 'inline; filename="tts.mp3"',
    }
    return StreamingResponse(_stream(path), media_type="audio/mpeg", headers=headers)
