"""Protected storage for community uploads, with local and S3-compatible backends."""

from __future__ import annotations

import io
import uuid
from pathlib import Path

from app.config import settings


def local_root() -> Path:
    root = Path(settings.COMMUNITY_STORAGE_DIR)
    if not root.is_absolute():
        root = Path(__file__).resolve().parents[2] / root
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def use_s3() -> bool:
    return bool(settings.S3_ENDPOINT and settings.S3_ACCESS_KEY and settings.S3_SECRET_KEY)


def storage_key(suffix: str) -> str:
    safe_suffix = suffix.lower().replace(".", "")[:12] or "bin"
    return f"community/{uuid.uuid4().hex}.{safe_suffix}"


def _s3_client():
    import boto3
    return boto3.client(
        "s3", endpoint_url=settings.S3_ENDPOINT,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.S3_REGION,
    )


def save_bytes(key: str, content: bytes, mime_type: str) -> str:
    if use_s3():
        client = _s3_client()
        try:
            client.head_bucket(Bucket=settings.S3_BUCKET)
        except Exception:
            client.create_bucket(Bucket=settings.S3_BUCKET)
        client.put_object(Bucket=settings.S3_BUCKET, Key=key, Body=content, ContentType=mime_type)
        return "s3"
    path = (local_root() / key.removeprefix("community/")).resolve()
    if local_root() not in path.parents:
        raise ValueError("非法存储路径")
    path.write_bytes(content)
    return "local"


def read_file(key: str, backend: str) -> tuple[io.BytesIO | Path, int | None]:
    if backend == "s3":
        body = _s3_client().get_object(Bucket=settings.S3_BUCKET, Key=key)["Body"].read()
        return io.BytesIO(body), len(body)
    path = (local_root() / key.removeprefix("community/")).resolve()
    if local_root() not in path.parents or not path.is_file():
        raise FileNotFoundError(key)
    return path, path.stat().st_size


def delete_file(key: str, backend: str) -> None:
    if backend == "s3":
        _s3_client().delete_object(Bucket=settings.S3_BUCKET, Key=key)
        return
    path = (local_root() / key.removeprefix("community/")).resolve()
    if local_root() in path.parents and path.is_file():
        path.unlink()
