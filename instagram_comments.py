"""Lee y responde comentarios mediante los permisos oficiales de Instagram."""

from __future__ import annotations

import argparse
import json
import sys

from instagram_publish import InstagramAPIError, api_request, credentials

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def scan(media_limit: int = 10) -> list[dict]:
    user_id, token = credentials()
    media = api_request(
        f"{user_id}/media",
        params={"fields": "id,permalink,timestamp", "limit": str(media_limit), "access_token": token},
    ).get("data", [])
    output: list[dict] = []
    for item in media:
        comments = api_request(
            f"{item['id']}/comments",
            params={"fields": "id,text,username,timestamp,replies", "access_token": token},
        ).get("data", [])
        for comment in comments:
            comment["media_id"] = item["id"]
            comment["permalink"] = item.get("permalink")
            output.append(comment)
    return output


def reply(comment_id: str, message: str) -> dict:
    _, token = credentials()
    return api_request(
        f"{comment_id}/replies",
        method="POST",
        params={"message": message, "access_token": token},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    scan_parser = sub.add_parser("scan")
    scan_parser.add_argument("--media-limit", type=int, default=10)
    reply_parser = sub.add_parser("reply")
    reply_parser.add_argument("comment_id")
    reply_parser.add_argument("--message", required=True)
    args = parser.parse_args()
    try:
        result = scan(args.media_limit) if args.command == "scan" else reply(args.comment_id, args.message)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except InstagramAPIError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
