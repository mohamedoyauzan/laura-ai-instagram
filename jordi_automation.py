"""Publicador programado y reanudable de Jordi para GitHub Actions."""

from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image

from instagram_publish import InstagramAPIError, publish_media, verify_account


ROOT = Path(__file__).resolve().parent
SCHEDULE_PATH = ROOT / "jordi_automation_schedule.json"
TZ = ZoneInfo("Europe/Madrid")
MAX_LATE = timedelta(hours=3)


def load_schedule() -> dict:
    return json.loads(SCHEDULE_PATH.read_text(encoding="utf-8"))


def save_schedule(schedule: dict) -> None:
    SCHEDULE_PATH.write_text(json.dumps(schedule, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def media_base_url() -> str:
    explicit = os.environ.get("MEDIA_BASE_URL", "").rstrip("/")
    if explicit:
        return explicit
    repository = os.environ.get("GITHUB_REPOSITORY", "mohamedoyauzan/laura-ai-instagram")
    ref_name = os.environ.get("GITHUB_REF_NAME", "main")
    return f"https://raw.githubusercontent.com/{repository}/{ref_name}"


def public_url(relative_path: str) -> str:
    return f"{media_base_url()}/{urllib.parse.quote(relative_path, safe='/')}"


def assert_public(url: str) -> None:
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "JordiPublisher/1.0"})
    with urllib.request.urlopen(request, timeout=45) as response:
        if response.status != 200:
            raise RuntimeError(f"El medio devolvió HTTP {response.status}")


def validate_local(item: dict) -> None:
    if item.get("quality", {}).get("status") not in {"approved", "derived_from_approved_source"}:
        raise RuntimeError(f"{item['id']} no tiene aprobación visual")
    path = ROOT / item["file"]
    if not path.is_file() or path.stat().st_size < 30_000:
        raise RuntimeError(f"Medio ausente o incompleto: {path}")
    if item["kind"] in {"post", "story"}:
        with Image.open(path) as image:
            expected = (1080, 1350) if item["kind"] == "post" else (1080, 1920)
            if image.size != expected:
                raise RuntimeError(f"Dimensiones incorrectas en {path}: {image.size}, esperado {expected}")
    elif item["kind"] != "reel":
        raise RuntimeError(f"Tipo no compatible: {item['kind']}")


def expire_old(schedule: dict, now: datetime) -> int:
    changed = 0
    for item in schedule["items"]:
        if item.get("status") != "pending":
            continue
        due = datetime.fromisoformat(item["publish_at"])
        if due.date() < now.date() or now - due > MAX_LATE:
            item["status"] = "expired"
            item["expired_at"] = now.isoformat()
            changed += 1
    return changed


def select_due(schedule: dict, now: datetime, slot_id: str = "") -> dict | None:
    pending = [item for item in schedule["items"] if item.get("status") == "pending"]
    if slot_id:
        return next((item for item in pending if item["id"] == slot_id), None)
    due = [item for item in pending if datetime.fromisoformat(item["publish_at"]) <= now]
    return min(due, key=lambda item: item["publish_at"], default=None)


def run(*, now: datetime | None = None, dry_run: bool = False, slot_id: str = "") -> dict:
    schedule = load_schedule()
    current = now or datetime.now(TZ)
    expired = expire_old(schedule, current)
    item = select_due(schedule, current, slot_id)
    if not item:
        if expired:
            save_schedule(schedule)
        return {"published": False, "reason": "nothing_due", "expired": expired, "now": current.isoformat()}

    validate_local(item)
    url = public_url(item["file"])
    result = {"published": False, "dry_run": dry_run, "item": item["id"], "kind": item["kind"], "url": url, "expired": expired}
    if dry_run:
        return result

    account = verify_account()
    if account.get("username") != schedule["account_username"]:
        raise RuntimeError(f"Cuenta inesperada: {account.get('username')}; se esperaba {schedule['account_username']}")
    assert_public(url)
    media = publish_media(url, item.get("caption", ""), item["kind"])
    item["status"] = "published"
    item["media_id"] = media.get("id")
    item["published_at"] = datetime.now(TZ).isoformat()
    save_schedule(schedule)
    result.update({"published": True, "media_id": media.get("id")})
    return result


def status() -> dict:
    schedule = load_schedule()
    counts: dict[str, int] = {}
    for item in schedule["items"]:
        state = item.get("status", "pending")
        counts[state] = counts.get(state, 0) + 1
    next_item = next((item for item in schedule["items"] if item.get("status") == "pending"), None)
    return {"account": schedule["account_username"], "counts": counts, "next": next_item}


def verify_expected_account() -> dict:
    schedule = load_schedule()
    account = verify_account()
    actual = account.get("username")
    expected = schedule["account_username"]
    if actual != expected:
        raise RuntimeError(f"Cuenta inesperada: {actual}; se esperaba {expected}")
    return {
        "connected": True,
        "username": actual,
        "account_type": account.get("account_type"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    due = sub.add_parser("due")
    due.add_argument("--dry-run", action="store_true")
    due.add_argument("--slot", default="")
    due.add_argument("--now", default="", help="Fecha ISO para pruebas")
    sub.add_parser("status")
    sub.add_parser("verify")
    args = parser.parse_args()
    try:
        if args.command == "status":
            output = status()
        elif args.command == "verify":
            output = verify_expected_account()
        else:
            test_now = datetime.fromisoformat(args.now) if args.now else None
            output = run(now=test_now, dry_run=args.dry_run, slot_id=args.slot)
        print(json.dumps(output, ensure_ascii=False))
        return 0
    except (InstagramAPIError, OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
