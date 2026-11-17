"""多模态图片输入的统一校验。

前端把图片读成 data URL 随对话一起提交；这里负责收敛格式、数量与体积，
不合规的输入在进入 AI 之前就被拒绝，避免把任意字符串塞进模型请求。
"""
from __future__ import annotations

import base64
import binascii

from app.config import settings

ALLOWED_PREFIXES = (
    "data:image/png;base64,",
    "data:image/jpeg;base64,",
    "data:image/jpg;base64,",
    "data:image/webp;base64,",
)


class ImageInputError(ValueError):
    """图片输入不合法（数量、格式、体积或编码）。"""


def sanitize_images(images: list[str] | None) -> list[str]:
    """校验并返回可安全下发到模型接口的图片列表。"""
    if not images:
        return []
    limit = int(getattr(settings, "VISION_MAX_IMAGES", 2))
    max_chars = int(getattr(settings, "VISION_MAX_IMAGE_CHARS", 8_000_000))
    if len(images) > limit:
        raise ImageInputError(f"最多附带 {limit} 张图片")
    cleaned: list[str] = []
    for raw in images:
        value = str(raw or "").strip()
        if not value:
            continue
        if not value.startswith(ALLOWED_PREFIXES):
            raise ImageInputError("图片仅支持 PNG/JPEG/WebP 的 base64 data URL")
        payload = value.split(",", 1)[1] if "," in value else ""
        if not payload:
            raise ImageInputError("图片内容为空")
        if len(payload) > max_chars:
            raise ImageInputError(f"单张图片不得超过约 {max_chars * 3 // 4 // (1024 * 1024)} MB")
        try:
            base64.b64decode(payload, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ImageInputError("图片内容不是有效的 base64 编码") from exc
        cleaned.append(value)
    if len(cleaned) > limit:
        raise ImageInputError(f"最多附带 {limit} 张图片")
    return cleaned


def with_images(text: str, images: list[str] | None) -> str | list[dict]:
    """把纯文本消息升级成 OpenAI 兼容的多模态内容块；没有图片时保持原样。"""
    if not images:
        return text
    return [{"type": "text", "text": text}] + [
        {"type": "image_url", "image_url": {"url": url}} for url in images
    ]
