"""Prepara y publica el contenido diario de Laura de forma repetible."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parent
PLAN_PATH = ROOT / "content_plan.json"
QUEUE_PATH = ROOT / "publication_queue.json"
POSTS_DIR = ROOT / "posts" / "auto"
MASTER_IMAGE = ROOT / "assets" / "lia-cute-v4.png"
FONT_CANDIDATES = [
    Path("C:/Windows/Fonts/segoeuib.ttf"),
    Path("C:/Windows/Fonts/arialbd.ttf"),
]


def load_json(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, value: list[dict]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def next_item() -> dict | None:
    for item in load_json(PLAN_PATH):
        if item.get("status") not in {"published"}:
            return item
    return None


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in FONT_CANDIDATES:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def validate_source(path: Path) -> Image.Image:
    if not path.is_file():
        raise RuntimeError(f"No existe la imagen generada: {path}")
    image = Image.open(path).convert("RGB")
    if image.width < 768 or image.height < 768:
        raise RuntimeError("La imagen es demasiado pequeña para Instagram")
    return image


def make_vertical_frame(source: Image.Image, hook: str, output: Path) -> None:
    canvas_size = (1080, 1920)
    background = ImageOps.fit(source, canvas_size, method=Image.Resampling.LANCZOS)
    background = background.filter(ImageFilter.GaussianBlur(28))
    background = ImageEnhance.Brightness(background).enhance(0.58)

    foreground = ImageOps.contain(source, (1010, 1500), method=Image.Resampling.LANCZOS)
    canvas = background.copy()
    x = (canvas.width - foreground.width) // 2
    y = (canvas.height - foreground.height) // 2
    canvas.paste(foreground, (x, y))

    shade = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    shade_draw = ImageDraw.Draw(shade)
    for row in range(420):
        alpha = int(155 * (row / 420))
        shade_draw.line((0, 1500 + row, 1080, 1500 + row), fill=(0, 0, 0, alpha))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), shade)

    draw = ImageDraw.Draw(canvas)
    title_font = font(58)
    body_font = font(29)
    lines = textwrap.wrap(hook, width=25)
    title = "\n".join(lines[:3])
    bbox = draw.multiline_textbbox((0, 0), title, font=title_font, spacing=10)
    box_width = min(980, bbox[2] - bbox[0] + 70)
    box_height = bbox[3] - bbox[1] + 56
    box_x = (1080 - box_width) // 2
    draw.rounded_rectangle(
        (box_x, 92, box_x + box_width, 92 + box_height),
        radius=28,
        fill=(0, 0, 0, 145),
    )
    draw.multiline_text(
        (540, 120),
        title,
        font=title_font,
        fill="white",
        anchor="ma",
        align="center",
        spacing=10,
        stroke_width=1,
        stroke_fill=(0, 0, 0, 110),
    )
    draw.text(
        (540, 1810),
        "LAURA  •  VIRTUAL CREATOR",
        font=body_font,
        fill=(255, 255, 255, 225),
        anchor="mm",
    )
    canvas.convert("RGB").save(output, quality=94, optimize=True)


def make_reel(frame: Path, output: Path) -> None:
    filter_graph = (
        "zoompan="
        "z='min(zoom+0.00032,1.055)':"
        "x='iw/2-(iw/zoom/2)':"
        "y='ih/2-(ih/zoom/2)':"
        "d=270:s=1080x1920:fps=30,scale=in_range=full:out_range=tv,format=yuv420p"
    )
    command = [
        "ffmpeg", "-y", "-loop", "1", "-i", str(frame),
        "-vf", filter_graph,
        "-t", "9", "-r", "30",
        "-c:v", "libx264", "-profile:v", "high", "-level", "4.1",
        "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", "-an", str(output),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(f"FFmpeg no pudo crear el Reel: {completed.stderr[-1200:]}")


def prepare(image_path: Path) -> dict:
    item = next_item()
    if item is None:
        return {"complete": True, "message": "El plan de 30 días está terminado"}
    if item.get("status") == "prepared":
        return {"prepared": True, "resumed": True, "item": item}

    source = validate_source(image_path)
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    date_slug = datetime.now().astimezone().date().isoformat()
    base = f"{date_slug}-{item['id']}-{item['city'].lower().replace(' ', '-')}"
    photo_path = POSTS_DIR / f"{base}.jpg"
    frame_path = POSTS_DIR / f"{base}-reel-frame.jpg"
    reel_path = POSTS_DIR / f"{base}-reel.mp4"

    source.save(photo_path, quality=91, optimize=True)
    make_vertical_frame(source, item["hook"], frame_path)
    make_reel(frame_path, reel_path)

    batch_id = f"{date_slug}-{item['id']}"
    queue = load_json(QUEUE_PATH)
    queue.extend(
        [
            {
                "file": str(reel_path.relative_to(ROOT)).replace("\\", "/"),
                "caption": item["caption"],
                "type": "reel",
                "batch_id": batch_id,
                "status": "pending",
            },
            {
                "file": str(photo_path.relative_to(ROOT)).replace("\\", "/"),
                "caption": "",
                "type": "story",
                "batch_id": batch_id,
                "status": "pending",
            },
        ]
    )
    save_json(QUEUE_PATH, queue)

    plan = load_json(PLAN_PATH)
    for row in plan:
        if row["id"] == item["id"]:
            row.update(
                {
                    "status": "prepared",
                    "batch_id": batch_id,
                    "prepared_at": datetime.now(timezone.utc).isoformat(),
                    "photo_file": str(photo_path.relative_to(ROOT)).replace("\\", "/"),
                    "reel_file": str(reel_path.relative_to(ROOT)).replace("\\", "/"),
                }
            )
            item = row
            break
    save_json(PLAN_PATH, plan)
    return {"prepared": True, "item": item}


def sync() -> dict:
    plan = load_json(PLAN_PATH)
    queue = load_json(QUEUE_PATH)
    changed = False
    for item in plan:
        batch_id = item.get("batch_id")
        if not batch_id or item.get("status") == "published":
            continue
        entries = [row for row in queue if row.get("batch_id") == batch_id]
        if entries and all(row.get("status") == "published" for row in entries):
            item["status"] = "published"
            item["published_at"] = max(row.get("published_at", "") for row in entries)
            item["media_ids"] = [row.get("media_id") for row in entries]
            changed = True
    if changed:
        save_json(PLAN_PATH, plan)
    current = next_item()
    return {"synced": changed, "next": current}


def publish_current() -> int:
    item = next_item()
    if item is None:
        print(json.dumps({"complete": True}, ensure_ascii=False))
        return 0
    batch_id = item.get("batch_id")
    if not batch_id:
        print(json.dumps({"ok": False, "error": "El contenido todavía no está preparado"}, ensure_ascii=False))
        return 2
    completed = subprocess.run(
        ["python", str(ROOT / "publish_queue.py"), "--batch-id", batch_id],
        cwd=ROOT,
    )
    print(json.dumps(sync(), ensure_ascii=False))
    return completed.returncode


def prompt_for(item: dict) -> str:
    return (
        "Use case: photorealistic-natural\n"
        "Asset type: vertical Instagram travel photo used for a Reel and Story\n"
        f"Primary request: Laura visiting {item['location']} in {item['city']}\n"
        f"Subject: preserve exactly the same fictional adult woman from {MASTER_IMAGE.name}; "
        "about 20 years old, blonde hair, blue eyes, light freckles, cute natural face\n"
        f"Composition/framing: {item['shot']}\n"
        f"Wardrobe: {item['outfit']}\n"
        "Style/medium: highly photorealistic candid smartphone travel photography, natural skin texture, "
        "subtle imperfections, realistic hands and anatomy, real ambient crowds\n"
        "Lighting/mood: natural location-appropriate light, unstaged and believable\n"
        "Constraints: identity-preserve; exact same face, eye color, freckles and blonde hair as the master; "
        "recognizable geographically accurate landmark; adult subject; no text, no logos, no watermark\n"
        "Avoid: plastic skin, glamour studio lighting, impossible architecture, extra fingers, distorted face, "
        "always staring into the camera"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("next")
    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("--image", required=True, type=Path)
    sub.add_parser("publish")
    sub.add_parser("sync")
    args = parser.parse_args()

    if args.command == "next":
        item = next_item()
        payload = {"complete": item is None, "item": item}
        if item is not None:
            payload["image_prompt"] = prompt_for(item)
            payload["master_image"] = str(MASTER_IMAGE)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if args.command == "prepare":
        print(json.dumps(prepare(args.image.resolve()), ensure_ascii=False, indent=2))
        return 0
    if args.command == "sync":
        print(json.dumps(sync(), ensure_ascii=False, indent=2))
        return 0
    return publish_current()


if __name__ == "__main__":
    raise SystemExit(main())
