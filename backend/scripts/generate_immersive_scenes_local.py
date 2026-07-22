"""Generate independent immersive scenes locally with SDXL Turbo.

The script creates original artwork only; it never downloads reference photos.
Outputs are deterministic PNG source files consumed by
``prepare_immersive_storyboards.py``.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import torch
from diffusers import AutoPipelineForText2Image


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = ROOT / "backend" / "app" / "static" / "immersive" / "storyboards"
MODEL_ID = "stabilityai/sdxl-turbo"

STYLE = (
    "museum-grade photorealistic Chinese historical documentary cinema, "
    "natural human proportions and expressions, authentic architecture, clothing, tools and weather, "
    "first-person witness atmosphere, layered depth, subtle 35mm film grain, restrained color grading, "
    "wide landscape composition, no text, no letters, no numbers, no caption, no logo, no watermark, "
    "no exact famous-person likeness, no heroic propaganda pose, no modern object unless explicitly contemporary"
)

SCENES: dict[str, list[str]] = {
    "history-3": [
        "Beijing at dawn on 1 October 1949, old hutong, ordinary citizens in late-1940s coats walking and cycling toward Tiananmen, cool autumn air",
        "Tiananmen Square filling with workers, students and families in historically accurate 1949 clothing, crowd-level viewpoint, clear autumn sky",
        "distant view toward Tiananmen rostrum and period architecture from inside the crowd, dignitaries only tiny silhouettes, solemn anticipation",
        "close view of an ordinary listener's weathered hands holding a small plain red paper flag, surrounding faces natural and emotionally restrained",
        "broad ceremonial formation crossing the square, historically plausible 1949 vehicles far behind, orderly crowd and vast public space",
        "warm evening lantern light in old Beijing, families returning through a stone gateway after the ceremony, quiet sense of a new beginning",
    ],
    "history-4": [
        "winter Beijing street in December 1978, streams of bicycles, blue-grey cotton coats, low-rise period buildings, crisp morning light",
        "modest late-1970s office desk with newspapers turned face-down, notebooks, fountain pen, enamel mug and production figures without readable text",
        "serious collective conference discussion in a plain 1978 meeting room, long table, participants viewed from side and behind, documentary realism",
        "rural Chinese household in the late 1970s listening to a wooden radio beside farm tools and an account notebook, warm lamplight",
        "early factory workshop restarting machinery, workers in period uniforms checking equipment, shafts of winter sunlight and suspended dust",
        "spring landscape suggesting reform beginning: train beside fields, small market activity and distant southern construction cranes, hopeful dawn",
    ],
    "history-5": [
        "contemporary Chinese mountain village at sunrise around 2021, paved road, renovated homes, green hills, ordinary residents beginning the day",
        "bright rural classroom with teacher and children, modern but modest facilities, books and sunlight, no readable writing",
        "community health clinic with doctor speaking to an elderly resident, clean practical interior, humane documentary mood",
        "small modern workshop and local logistics station, workers packing agricultural products, digital equipment present but no visible screen text",
        "family outside a new home reviewing household changes with a village worker, road, water and public-service infrastructure visible",
        "wide contemporary panorama connecting village, railway, city skyline and cultivated land at golden hour, ordinary builders and families in foreground",
    ],
    "tour-1": [
        "present-day Jinggangshan forested mountain visitor path after rain, stone steps, red-earth slope, dense bamboo and mist, no people posing",
        "historical window into autumn 1927, a small travelling column entering a misty Jinggangshan trail, seen from behind, simple cloth uniforms",
        "old mountain residence and narrow path integrated into steep terrain, first-person visitor discovering architecture and geography",
        "ordinary local villagers and early base-area members carrying supplies together on a forest path, respectful group story, no named hero",
        "close environmental evidence: straw sandals, oil lamp, simple farming tool and hand-drawn map without readable marks on a wooden table",
        "Jinggangshan ridgeline above clouds at sunrise, winding trail connecting old settlement and present-day memorial landscape without signage",
    ],
    "tour-2": [
        "present-day Yan'an loess plateau, preserved cave dwellings and visitor path under clear northern light, no signage or tourist crowd",
        "historical transition to a 1930s Yan'an cave-dwelling courtyard at dusk, oil lamp beginning to glow, wind moving across loess hills",
        "plain cave room with wooden desk, books without readable titles, map and kerosene lamp, austere learning environment",
        "group study in a cave classroom, young men and women in period plain clothing listening and taking notes, no exact famous likeness",
        "collective production scene beside loess fields, spinning wheel, farm tools and people working, documentary group narrative",
        "Yan'an valley before dawn, scattered cave lights across hills, path leading toward the horizon, quiet endurance and shared purpose",
    ],
    "tour-3": [
        "present-day Xibaipo northern Chinese village courtyard, low stone houses, trees and preserved simple buildings, calm visitor viewpoint",
        "historical window to winter 1948, same modest village with staff moving between courtyards carrying document folders without readable text",
        "small operations room with large unlabelled wall map, wooden table, oil lamps and telegraph equipment, workers viewed from behind",
        "telegraph operator receiving messages at a simple desk, paper strips without legible marks, concentrated atmosphere",
        "village residents and staff sharing water and supplies in a courtyard, ordinary people sustaining intensive work",
        "early 1949 dawn road leaving Xibaipo toward distant plains, simple convoy and walkers, restrained 'setting out for an examination' metaphor",
    ],
    "tour-4": [
        "present-day Shaoshan rural landscape, green rice fields, pond, wooded hills and preserved earthen residence exterior, soft morning rain",
        "late Qing era Hunan farmhouse courtyard, agricultural tools, water buffalo far away and family life suggested without famous-person portrait",
        "simple historic study corner with wooden desk, brush, oil lamp and closed books without readable writing, window facing fields",
        "young rural students and family members working in rice fields and discussing daily concerns, group perspective, no identifiable leader",
        "a young traveller seen from behind leaving the village along a field path with a cloth bundle, mountains beyond, dawn light",
        "contemporary Shaoshan landscape at sunset linking old residence, fields and village paths, visitors small in the distance, reflective mood",
    ],
    "tour-5": [
        "present-day Zunyi Conference site courtyard, grey-brick two-storey residence, wet stone paving, quiet visitor viewpoint, no signage",
        "historical transition from the present courtyard into January 1935 winter rain, period sentry silhouettes and warm windows",
        "interior meeting-room reconstruction seen as a visitor, long wooden table, enamel mugs, lamps and maps, no exact famous-person likeness",
        "close-up of architecture and evidence: wooden window lattice, worn stair rail, oil lamp and unlabelled route map",
        "contemporary visitor notebook in hand while looking from the corridor toward the courtyard, reflective travel-study perspective",
        "Zunyi old-town rooflines and surrounding mountains after rain at dawn, historic site nested in the city, renewed clarity",
    ],
}


def stable_seed(book_id: str, index: int) -> int:
    digest = hashlib.sha256(f"eclass:{book_id}:{index}:v3".encode()).digest()
    return int.from_bytes(digest[:4], "big")


def load_pipeline():
    torch.backends.cuda.matmul.allow_tf32 = True
    pipe = AutoPipelineForText2Image.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.float16,
        variant="fp16",
        use_safetensors=True,
    )
    pipe.enable_model_cpu_offload()
    pipe.enable_vae_tiling()
    pipe.set_progress_bar_config(disable=True)
    return pipe


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("book_ids", nargs="*", choices=sorted(SCENES), default=sorted(SCENES))
    parser.add_argument("--steps", type=int, default=2, choices=(1, 2, 3, 4))
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="Generate only the first N scenes per book (smoke test).")
    args = parser.parse_args()

    pipe = load_pipeline()
    for book_id in args.book_ids:
        output_dir = OUTPUT_ROOT / book_id
        output_dir.mkdir(parents=True, exist_ok=True)
        scenes = SCENES[book_id][: args.limit or None]
        for index, scene in enumerate(scenes, start=1):
            output = output_dir / f"{index:02d}.png"
            if output.exists() and not args.overwrite:
                print(f"skip {book_id}-{index:02d}")
                continue
            prompt = f"{scene}. {STYLE}."
            generator = torch.Generator(device="cuda").manual_seed(stable_seed(book_id, index))
            image = pipe(
                prompt=prompt,
                width=768,
                height=512,
                num_inference_steps=args.steps,
                guidance_scale=0.0,
                generator=generator,
            ).images[0]
            image.save(output, optimize=True)
            print(f"generated {book_id}-{index:02d}: {output}")


if __name__ == "__main__":
    main()
