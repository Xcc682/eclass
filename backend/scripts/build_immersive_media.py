"""Pre-generate narration and optionally publish it to S3-compatible storage.

Usage:
    python scripts/build_immersive_media.py
    python scripts/build_immersive_media.py --upload

The command is deliberately offline from the user request path: failed TTS or
object storage never prevents a reader from opening a book.
"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import boto3
import edge_tts
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models.immersive import ImmersiveSpread


VOICE = "zh-CN-YunxiNeural"


async def render(spread: ImmersiveSpread, output: Path) -> None:
    if not spread.narration.strip():
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    await edge_tts.Communicate(spread.narration, VOICE, rate="-8%").save(str(output))


def s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.S3_REGION,
    )


async def main(upload: bool) -> None:
    root = Path(settings.IMMERSIVE_MEDIA_DIR) / "audio"
    with SessionLocal() as db:
        rows = list(db.scalars(select(ImmersiveSpread).order_by(ImmersiveSpread.book_id, ImmersiveSpread.order_index)).all())
        for spread in rows:
            if not spread.narration.strip():
                continue
            destination = root / f"{spread.id}.mp3"
            if not destination.exists():
                print(f"[tts] {spread.id}")
                await render(spread, destination)
            if upload:
                if not settings.S3_ENDPOINT:
                    raise RuntimeError("S3_ENDPOINT is required with --upload")
                client = s3_client()
                try:
                    client.head_bucket(Bucket=settings.S3_BUCKET)
                except Exception:
                    client.create_bucket(Bucket=settings.S3_BUCKET)
                key = f"audio/{destination.name}"
                client.upload_file(str(destination), settings.S3_BUCKET, key, ExtraArgs={"ContentType": "audio/mpeg"})
                spread.audio_url = f"{settings.MEDIA_BASE_URL.rstrip('/')}/{key}"
            else:
                spread.audio_url = f"/media/immersive/audio/{destination.name}"
        db.commit()
    print(f"[ok] processed {len(rows)} spreads")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--upload", action="store_true", help="upload generated MP3 files and persist public URLs")
    args = parser.parse_args()
    asyncio.run(main(args.upload))
