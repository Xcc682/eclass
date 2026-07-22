"""Prepare generated immersive storyboards for the H5 and API media trees.

Each ``*-sheet.png`` is a generated 3 x 2 storyboard.  The script removes the
thin panel gutters, converts each panel to a 16:10 WebP scene, and mirrors the
result into the frontend bundle and backend static directory.

When a storyboard is still being regenerated, the script can derive six
distinct camera crops from the generated per-book fallback artwork.  That keeps
the reader functional without introducing third-party or placeholder imagery.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter


ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "backend" / "app" / "static" / "immersive" / "storyboards"
BACKEND_OUTPUT = ROOT / "backend" / "app" / "static" / "immersive" / "images"
FRONTEND_OUTPUT = ROOT / "frontend" / "src" / "assets" / "immersive"

BOOK_IDS = [*(f"history-{i}" for i in range(1, 6)), *(f"tour-{i}" for i in range(1, 6))]
# Curated focus regions for the generated historical-river master artwork.
# Values are (horizontal center, base width); they deliberately avoid visually
# unrelated sections while a dedicated six-panel storyboard is being retried.
FALLBACK_FOCUS = {
    "history-3": (0.77, 0.46),  # Tiananmen and the gathered crowd
    "history-4": (0.84, 0.34),  # modernising city horizon
    "history-5": (0.78, 0.43),  # contemporary city and public life
    "tour-1": (0.46, 0.42),     # mountain terrain and the travelling column
    "tour-2": (0.49, 0.44),     # mountain route, no modern skyline
    "tour-3": (0.75, 0.48),     # square and broad public landscape
    "tour-4": (0.20, 0.36),     # old settlement, water and rural textures
    "tour-5": (0.46, 0.42),
}


def _fit_16_by_10(image: Image.Image, size: tuple[int, int] = (1200, 750)) -> Image.Image:
    target_ratio = size[0] / size[1]
    ratio = image.width / image.height
    if ratio > target_ratio:
        width = round(image.height * target_ratio)
        left = (image.width - width) // 2
        image = image.crop((left, 0, left + width, image.height))
    else:
        height = round(image.width / target_ratio)
        top = (image.height - height) // 2
        image = image.crop((0, top, image.width, top + height))
    return image.resize(size, Image.Resampling.LANCZOS)


def _storyboard_panels(sheet: Image.Image) -> list[Image.Image]:
    panels: list[Image.Image] = []
    for row in range(2):
        for column in range(3):
            left = round(sheet.width * column / 3) + (2 if column else 0)
            right = round(sheet.width * (column + 1) / 3) - (2 if column < 2 else 0)
            top = round(sheet.height * row / 2) + (2 if row else 0)
            bottom = round(sheet.height * (row + 1) / 2) - (2 if row == 0 else 0)
            panels.append(_fit_16_by_10(sheet.crop((left, top, right, bottom))))
    return panels


def _fallback_panels(image: Image.Image, book_id: str) -> list[Image.Image]:
    panels: list[Image.Image] = []
    center, base_width = FALLBACK_FOCUS.get(book_id, (0.5, 0.62))
    offsets = (-0.035, 0.02, -0.015, 0.03, 0.0, 0.045)
    zooms = (1.0, 0.92, 0.82, 0.88, 0.76, 0.94)
    verticals = ((0.02, 0.98), (0.0, 0.9), (0.08, 1.0), (0.0, 0.86), (0.12, 0.98), (0.05, 0.94))
    for index, (offset, zoom, vertical) in enumerate(zip(offsets, zooms, verticals)):
        width = base_width * zoom
        left = max(0.0, min(1.0 - width, center + offset - width / 2))
        right = left + width
        top, bottom = vertical
        panel = image.crop((
            round(image.width * left), round(image.height * top),
            round(image.width * right), round(image.height * bottom),
        ))
        panel = _fit_16_by_10(panel)
        # Tiny cinematic variations prevent adjacent pages from appearing frozen.
        panel = ImageEnhance.Brightness(panel).enhance(0.92 + index * 0.025)
        panel = ImageEnhance.Color(panel).enhance(0.84 + (index % 3) * 0.07)
        if index in {1, 4}:
            panel = panel.filter(ImageFilter.GaussianBlur(radius=0.25))
        panels.append(panel)
    return panels


def prepare(book_id: str) -> tuple[str, str]:
    scene_dir = SOURCE_DIR / book_id
    sheet_path = SOURCE_DIR / f"{book_id}-sheet.png"
    fallback_path = BACKEND_OUTPUT / f"{book_id}.png"
    scene_paths = [scene_dir / f"{index:02d}.png" for index in range(1, 7)]
    if all(path.exists() for path in scene_paths):
        panels = []
        for path in scene_paths:
            with Image.open(path) as source:
                panels.append(_fit_16_by_10(source.convert("RGB")))
        source = "independent scenes"
    else:
        source_path = sheet_path if sheet_path.exists() else fallback_path
        if not source_path.exists():
            raise FileNotFoundError(f"No generated source artwork for {book_id}")
        with Image.open(source_path) as opened:
            opened = opened.convert("RGB")
            panels = _storyboard_panels(opened) if sheet_path.exists() else _fallback_panels(opened, book_id)
        source = "storyboard" if sheet_path.exists() else "generated fallback"

    BACKEND_OUTPUT.mkdir(parents=True, exist_ok=True)
    FRONTEND_OUTPUT.mkdir(parents=True, exist_ok=True)
    for index, panel in enumerate(panels, start=1):
        filename = f"{book_id}-{index:02d}.webp"
        for directory in (BACKEND_OUTPUT, FRONTEND_OUTPUT):
            panel.save(directory / filename, "WEBP", quality=84, method=6)
    return book_id, source


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("book_ids", nargs="*", default=BOOK_IDS)
    args = parser.parse_args()
    for book_id in args.book_ids:
        name, source = prepare(book_id)
        print(f"{name}: six scenes from {source}")


if __name__ == "__main__":
    main()
