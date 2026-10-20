"""Convierte una imagen aprobada en los medios del calendario cloud."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from daily_manager import make_reel, make_vertical_frame, validate_source


ROOT = Path(__file__).resolve().parent
PLAN_PATH = ROOT / "content_plan.json"
CLOUD_DIR = ROOT / "posts" / "cloud"
SOURCE_DIR = ROOT / "assets" / "daily-sources"


def prepare(item_id: str, image_path: Path) -> dict:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    item = next((row for row in plan if row["id"] == item_id), None)
    if item is None:
        raise RuntimeError(f"No existe {item_id} en content_plan.json")
    source = validate_source(image_path)
    CLOUD_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)

    source_path = SOURCE_DIR / f"{item_id}-{item['city'].lower().replace(' ', '-')}.png"
    if image_path.resolve() != source_path.resolve():
        shutil.copy2(image_path, source_path)
    story_path = CLOUD_DIR / f"{item_id}-story.jpg"
    frame_path = CLOUD_DIR / f"{item_id}-frame.jpg"
    reel_path = CLOUD_DIR / f"{item_id}-reel.mp4"
    source.save(story_path, quality=91, optimize=True)
    make_vertical_frame(source, item["hook"], frame_path)
    make_reel(frame_path, reel_path)
    return {
        "id": item_id,
        "source": str(source_path.relative_to(ROOT)).replace("\\", "/"),
        "story": str(story_path.relative_to(ROOT)).replace("\\", "/"),
        "reel": str(reel_path.relative_to(ROOT)).replace("\\", "/"),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True)
    parser.add_argument("--image", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.id, args.image.resolve()), ensure_ascii=False))
    except RuntimeError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1)
