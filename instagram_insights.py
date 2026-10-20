"""Recoge métricas de las publicaciones y conserva un historial local."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from instagram_publish import InstagramAPIError, api_request, credentials

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parent
ANALYTICS_DIR = ROOT / "analytics"
METRICS = ["views", "reach", "likes", "comments", "saved", "shares", "total_interactions"]


def media_list(limit: int) -> list[dict]:
    user_id, token = credentials()
    response = api_request(
        f"{user_id}/media",
        params={
            "fields": "id,caption,media_type,media_product_type,permalink,timestamp,like_count,comments_count",
            "limit": str(limit),
            "access_token": token,
        },
    )
    return response.get("data", [])


def media_metrics(media_id: str, token: str) -> dict[str, object]:
    result: dict[str, object] = {}
    for metric in METRICS:
        try:
            response = api_request(
                f"{media_id}/insights",
                params={"metric": metric, "access_token": token},
            )
            rows = response.get("data", [])
            if rows:
                values = rows[0].get("values", [])
                result[metric] = values[-1].get("value") if values else rows[0].get("value")
        except InstagramAPIError:
            continue
    return result


def collect(limit: int = 25) -> dict:
    _, token = credentials()
    items = media_list(limit)
    for item in items:
        item["insights"] = media_metrics(str(item["id"]), token)
    snapshot = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "media": items,
    }
    ANALYTICS_DIR.mkdir(exist_ok=True)
    (ANALYTICS_DIR / "latest.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (ANALYTICS_DIR / "history.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(snapshot, ensure_ascii=False) + "\n")
    return snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()
    try:
        print(json.dumps(collect(args.limit), ensure_ascii=False, indent=2))
        return 0
    except InstagramAPIError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
