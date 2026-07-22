"""Audit immersive scene assets for missing, duplicate and near-duplicate images."""
from __future__ import annotations

import argparse
import hashlib
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MEDIA_DIR = ROOT / "frontend" / "src" / "assets" / "immersive"
BOOK_IDS = [*(f"history-{i}" for i in range(1, 6)), *(f"tour-{i}" for i in range(1, 6))]


@dataclass(frozen=True)
class SceneFingerprint:
    path: Path
    sha256: str
    average_bits: int
    difference_bits: int

    @property
    def book_id(self) -> str:
        return self.path.stem.rsplit("-", 1)[0]


def perceptual_hashes(path: Path, hash_size: int = 16) -> tuple[int, int]:
    """Return average and difference hashes to avoid sky/landscape false positives."""
    with Image.open(path) as image:
        average_image = ImageOps.grayscale(image).resize(
            (hash_size, hash_size), Image.Resampling.LANCZOS
        )
        difference_image = ImageOps.grayscale(image).resize(
            (hash_size + 1, hash_size), Image.Resampling.LANCZOS
        )
        average_pixels = list(average_image.get_flattened_data())
        difference_pixels = list(difference_image.get_flattened_data())

    average = sum(average_pixels) / len(average_pixels)
    average_bits = 0
    for pixel in average_pixels:
        average_bits = (average_bits << 1) | int(pixel >= average)

    difference_bits = 0
    row_width = hash_size + 1
    for row in range(hash_size):
        offset = row * row_width
        for column in range(hash_size):
            difference_bits = (difference_bits << 1) | int(
                difference_pixels[offset + column] >= difference_pixels[offset + column + 1]
            )
    return average_bits, difference_bits


def similarity(left: int, right: int, hash_size: int = 16) -> float:
    distance = (left ^ right).bit_count()
    return 1.0 - distance / (hash_size * hash_size)


def fingerprint(path: Path) -> SceneFingerprint:
    average_bits, difference_bits = perceptual_hashes(path)
    return SceneFingerprint(
        path=path,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        average_bits=average_bits,
        difference_bits=difference_bits,
    )


def expected_paths(media_dir: Path) -> list[Path]:
    return [
        media_dir / f"{book_id}-{scene:02d}.webp"
        for book_id in BOOK_IDS
        for scene in range(1, 7)
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--media-dir", type=Path, default=DEFAULT_MEDIA_DIR)
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.90,
        help="Report cross-book perceptual similarity at or above this value.",
    )
    args = parser.parse_args()

    paths = expected_paths(args.media_dir)
    missing = [path for path in paths if not path.exists()]
    if missing:
        print(f"FAIL: {len(missing)} expected scene files are missing")
        for path in missing:
            print(f"  missing: {path.name}")
        return 1

    fingerprints = [fingerprint(path) for path in paths]
    exact_pairs: list[tuple[SceneFingerprint, SceneFingerprint]] = []
    same_book_near_pairs: list[tuple[SceneFingerprint, SceneFingerprint, float]] = []
    cross_book_near_pairs: list[tuple[SceneFingerprint, SceneFingerprint, float]] = []

    for left, right in combinations(fingerprints, 2):
        if left.sha256 == right.sha256:
            exact_pairs.append((left, right))
            continue
        average_score = similarity(left.average_bits, right.average_bits)
        difference_score = similarity(left.difference_bits, right.difference_bits)
        if average_score < args.threshold or difference_score < args.threshold:
            continue
        score = (average_score + difference_score) / 2
        target = same_book_near_pairs if left.book_id == right.book_id else cross_book_near_pairs
        target.append((left, right, score))

    print(f"Audited {len(fingerprints)} scenes across {len(BOOK_IDS)} books")
    print(f"Exact duplicate pairs: {len(exact_pairs)}")
    print(f"Same-book near-duplicate pairs >= {args.threshold:.0%}: {len(same_book_near_pairs)}")
    print(f"Cross-book near-duplicate pairs >= {args.threshold:.0%}: {len(cross_book_near_pairs)}")

    for label, pairs in (
        ("exact", [(left, right, 1.0) for left, right in exact_pairs]),
        ("same-book", same_book_near_pairs),
        ("cross-book", cross_book_near_pairs),
    ):
        for left, right, score in sorted(pairs, key=lambda pair: pair[2], reverse=True):
            print(f"  {label}: {left.path.name} <-> {right.path.name} ({score:.1%})")

    return 1 if exact_pairs or same_book_near_pairs or cross_book_near_pairs else 0


if __name__ == "__main__":
    raise SystemExit(main())
