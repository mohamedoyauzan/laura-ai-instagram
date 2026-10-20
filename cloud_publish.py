"""Publica el lote diario desde un runner de GitHub Actions.

Los medios deben existir en un repositorio público para que Instagram pueda
descargarlos. Las credenciales se reciben exclusivamente mediante secretos del
runner; nunca se escriben en el repositorio.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from instagram_publish import InstagramAPIError, publish_media, verify_account


ROOT = Path(__file__).resolve().parent
SCHEDULE_PATH = ROOT / "cloud_schedule.json"
TIMEZONE = ZoneInfo("Europe/Madrid")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def load_schedule() -> list[dict]:
    return json.loads(SCHEDULE_PATH.read_text(encoding="utf-8"))


def save_schedule(schedule: list[dict]) -> None:
    SCHEDULE_PATH.write_text(
        json.dumps(schedule, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def media_base_url() -> str:
    explicit = os.environ.get("MEDIA_BASE_URL", "").rstrip("/")
    if explicit:
        return explicit
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    ref_name = os.environ.get("GITHUB_REF_NAME", "main")
    if not repository:
        raise RuntimeError("Falta MEDIA_BASE_URL o GITHUB_REPOSITORY")
    return f"https://raw.githubusercontent.com/{repository}/{ref_name}/posts/cloud"


def public_url(base_url: str, relative_name: str) -> str:
    return f"{base_url}/{urllib.parse.quote(relative_name, safe='/')}"


def assert_public(url: str) -> None:
    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status != 200:
                raise RuntimeError(f"El medio devolvió HTTP {response.status}: {url}")
    except OSError as exc:
        raise RuntimeError(f"Instagram no podrá descargar el medio: {url}: {exc}") from exc


def publish_due(today: str | None = None) -> dict:
    verify_account()
    schedule = load_schedule()
    local_today = today or datetime.now(TIMEZONE).date().isoformat()
    due = [
        item
        for item in schedule
        if item["publish_date"] <= local_today and item.get("status") != "published"
    ]
    if not due:
        return {"published": False, "reason": "nothing_due", "date": local_today}

    # Publica solo el lote más antiguo para impedir ráfagas si GitHub se retrasa.
    item = sorted(due, key=lambda row: row["publish_date"])[0]
    base_url = media_base_url()

    if item.get("reel_status") != "published":
        reel_url = public_url(base_url, item["reel_file"])
        assert_public(reel_url)
        result = publish_media(reel_url, item["caption"], "reel")
        item["reel_status"] = "published"
        item["reel_media_id"] = result.get("id")
        save_schedule(schedule)

    if item.get("story_status") != "published":
        story_url = public_url(base_url, item["story_file"])
        assert_public(story_url)
        result = publish_media(story_url, "", "story")
        item["story_status"] = "published"
        item["story_media_id"] = result.get("id")
        save_schedule(schedule)

    item["status"] = "published"
    item["published_at"] = datetime.now(TIMEZONE).isoformat()
    save_schedule(schedule)
    return {
        "published": True,
        "id": item["id"],
        "publish_date": item["publish_date"],
        "reel_media_id": item.get("reel_media_id"),
        "story_media_id": item.get("story_media_id"),
    }


if __name__ == "__main__":
    try:
        print(json.dumps(publish_due(), ensure_ascii=False))
    except (InstagramAPIError, RuntimeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1)
