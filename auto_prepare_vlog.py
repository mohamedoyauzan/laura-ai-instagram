"""Prepare the next due Reel with reusable Creative Commons location footage."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from free_vlog import build


ROOT = Path(__file__).resolve().parent
SCHEDULE = ROOT / "cloud_schedule.json"
PLAN = ROOT / "content_plan.json"
VLOGS = ROOT / "vlogs"
TIMEZONE = ZoneInfo("Europe/Madrid")
API = "https://commons.wikimedia.org/w/api.php"
ALLOWED_LICENSES = ("CC BY", "CC0", "PUBLIC DOMAIN")


def request_json(params: dict[str, str | int]) -> dict:
    url = f"{API}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": "LauraContentBot/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def plain(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return " ".join(html.unescape(value).split())


def find_video(query: str) -> dict:
    data = request_json(
        {
            "action": "query",
            "generator": "search",
            "gsrsearch": f"{query} filetype:video",
            "gsrnamespace": 6,
            "gsrlimit": 15,
            "prop": "videoinfo|imageinfo",
            "viprop": "url|size|mediatype|derivatives",
            "iiprop": "extmetadata",
            "format": "json",
            "formatversion": 2,
        }
    )
    candidates: list[tuple[int, dict]] = []
    for page in data.get("query", {}).get("pages", []):
        video = (page.get("videoinfo") or [{}])[0]
        meta = ((page.get("imageinfo") or [{}])[0]).get("extmetadata", {})
        duration = float(video.get("duration") or 0)
        width = int(video.get("width") or 0)
        license_name = plain(meta.get("LicenseShortName", {}).get("value", ""))
        if duration < 15 or width < 640:
            continue
        if not any(name in license_name.upper() for name in ALLOWED_LICENSES):
            continue
        derivatives = video.get("derivatives") or []
        preferred = next(
            (row for row in derivatives if row.get("transcodekey") == "480p.vp9.webm"),
            None,
        )
        if preferred is None and int(video.get("size") or 0) <= 220_000_000:
            preferred = {"src": video.get("url"), "width": width}
        if not preferred or not preferred.get("src"):
            continue
        title = page.get("title", "").removeprefix("File:")
        author = plain(
            meta.get("Attribution", {}).get("value")
            or meta.get("Artist", {}).get("value", "Autor de Wikimedia Commons")
        )
        score = min(width, 1920) + (500 if query.lower().split(",")[0] in title.lower() else 0)
        candidates.append(
            (
                score,
                {
                    "title": title,
                    "url": preferred["src"],
                    "duration": duration,
                    "author": author[:140],
                    "license": license_name,
                    "source_page": video.get("descriptionurl", ""),
                },
            )
        )
    if not candidates:
        raise RuntimeError(f"No se encontró vídeo reutilizable para {query}")
    return max(candidates, key=lambda row: row[0])[1]


def prepare(today: str | None = None, force: bool = False) -> dict:
    schedule = json.loads(SCHEDULE.read_text(encoding="utf-8"))
    plan = {row["id"]: row for row in json.loads(PLAN.read_text(encoding="utf-8"))}
    local_today = today or datetime.now(TIMEZONE).date().isoformat()
    due = sorted(
        (
            row
            for row in schedule
            if row["publish_date"] <= local_today and row.get("status") != "published"
        ),
        key=lambda row: row["publish_date"],
    )
    if not due:
        return {"prepared": False, "reason": "nothing_due", "date": local_today}
    item = due[0]
    if item.get("vlog_generated") and not force:
        return {"prepared": False, "reason": "already_prepared", "id": item["id"]}

    manifest = VLOGS / f"{item['id']}.json"
    if not manifest.is_file():
        content = plan[item["id"]]
        found = find_video(content["location"])
        duration = found["duration"]
        starts = [max(0, duration * ratio - 1.5) for ratio in (0.18, 0.52, 0.82)]
        spec = {
            "id": f"{item['id']}-{item['city'].lower()}",
            "image": f"posts/cloud/{item['story_file']}",
            "video_url": found["url"],
            "source_page": found["source_page"],
            "author": found["author"],
            "license": found["license"],
            "hook": f"Tres detalles de {item['city']} que casi nadie mira",
            "outro": f"¿Qué rincón de {item['city']} vemos después?",
            "voiceover": (
                f"Hoy exploramos {content['location']}. Mira estos tres detalles que suelen pasar "
                f"desapercibidos. ¿Qué rincón de {item['city']} vemos después?"
            ),
            "intro_duration": 1.6,
            "outro_duration": 2.3,
            "segments": [{"start": round(value, 1), "duration": 3.0} for value in starts],
            "output": f"posts/cloud/{item['reel_file']}",
        }
        VLOGS.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        spec = json.loads(manifest.read_text(encoding="utf-8"))

    output = build(manifest)
    item["vlog_generated"] = True
    item["vlog_source"] = spec["source_page"]
    item["vlog_license"] = spec["license"]
    if "Wikimedia Commons" not in item["caption"]:
        clean_caption = item["caption"].replace("#VirtualCreator", "").replace("#AIGirl", "")
        item["caption"] = (
            clean_caption.rstrip()
            + f"\n\n🎥 {spec.get('author', 'Wikimedia Commons')} — {spec['license']} "
            f"(recortado y editado), Wikimedia Commons."
        )
    SCHEDULE.write_text(json.dumps(schedule, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"prepared": True, "id": item["id"], "output": str(output), "source": spec["source_page"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--today")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.today, args.force), ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"prepared": False, "warning": str(exc)}, ensure_ascii=False))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
