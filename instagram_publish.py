"""Publica fotos, Reels e historias con Instagram API with Instagram Login.

Instagram descarga el archivo desde ``image_url``; por eso la imagen debe estar
disponible mediante una URL HTTPS pública antes de ejecutar este programa.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ENV_PATH = Path(os.environ.get("INSTAGRAM_ENV_FILE", ROOT / ".env"))
if not ENV_PATH.is_absolute():
    ENV_PATH = ROOT / ENV_PATH
GRAPH_URL = "https://graph.instagram.com"


class InstagramAPIError(RuntimeError):
    """Error devuelto por la API de Instagram."""


def read_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_PATH.is_file():
        return values
    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def api_request(
    path: str,
    *,
    method: str = "GET",
    params: dict[str, str] | None = None,
) -> dict:
    values = params or {}
    url = f"{GRAPH_URL}/{path.lstrip('/')}"
    data: bytes | None = None
    if method == "GET":
        url = f"{url}?{urllib.parse.urlencode(values)}"
    else:
        data = urllib.parse.urlencode(values).encode("utf-8")

    request = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8"))
            message = detail.get("error", {}).get("message", "Error desconocido")
        except (json.JSONDecodeError, UnicodeDecodeError):
            message = f"HTTP {exc.code}"
        raise InstagramAPIError(message) from exc
    except urllib.error.URLError as exc:
        raise InstagramAPIError(f"No se pudo contactar con Instagram: {exc.reason}") from exc


def credentials() -> tuple[str, str]:
    config = read_env()
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN") or config.get("INSTAGRAM_ACCESS_TOKEN", "")
    user_id = os.environ.get("INSTAGRAM_USER_ID") or config.get("INSTAGRAM_USER_ID", "")
    if not token or not user_id:
        raise InstagramAPIError(
            "Faltan INSTAGRAM_ACCESS_TOKEN o INSTAGRAM_USER_ID en .env"
        )
    return user_id, token


def verify_account() -> dict:
    _, token = credentials()
    return api_request(
        "me",
        params={
            "fields": "id,username,account_type",
            "access_token": token,
        },
    )


def create_container(
    *,
    user_id: str,
    token: str,
    media_url: str,
    caption: str,
    kind: str,
) -> str:
    values = {"access_token": token, "is_ai_generated": "true"}
    if kind == "photo":
        values["image_url"] = media_url
        if caption:
            values["caption"] = caption
    elif kind == "reel":
        values.update(
            {
                "media_type": "REELS",
                "video_url": media_url,
                "share_to_feed": "true",
            }
        )
        if caption:
            values["caption"] = caption
    elif kind in {"story", "story_video"}:
        values["media_type"] = "STORIES"
        values["video_url" if kind == "story_video" else "image_url"] = media_url
    else:
        raise InstagramAPIError(f"Tipo de publicación no compatible: {kind}")
    result = api_request(f"{user_id}/media", method="POST", params=values)
    return str(result["id"])


def wait_until_ready(container_id: str, token: str, timeout: int = 300) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = api_request(
            container_id,
            params={"fields": "status_code,status", "access_token": token},
        )
        status = result.get("status_code", "")
        if status == "FINISHED":
            return
        if status in {"ERROR", "EXPIRED"}:
            raise InstagramAPIError(result.get("status", status))
        time.sleep(3)
    raise InstagramAPIError("La imagen no terminó de procesarse en 5 minutos")


def publish_media(media_url: str, caption: str = "", kind: str = "photo") -> dict:
    user_id, token = credentials()
    container_id = create_container(
        user_id=user_id,
        token=token,
        media_url=media_url,
        caption=caption,
        kind=kind,
    )
    wait_until_ready(container_id, token)
    return api_request(
        f"{user_id}/media_publish",
        method="POST",
        params={"creation_id": container_id, "access_token": token},
    )


def publish(image_url: str, caption: str, story: bool) -> dict:
    """Compatibilidad con el publicador de fotos original."""
    return publish_media(image_url, caption, "story" if story else "photo")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("verify", help="Comprueba la cuenta conectada")

    photo = subparsers.add_parser("photo", help="Publica una foto en el perfil")
    photo.add_argument("--image-url", required=True, help="URL HTTPS pública de la foto")
    photo.add_argument("--caption", default="", help="Texto de la publicación")

    story = subparsers.add_parser("story", help="Publica una imagen como historia")
    story.add_argument("--image-url", required=True, help="URL HTTPS pública de la imagen")

    story_video = subparsers.add_parser(
        "story-video", help="Publica un vídeo vertical como historia"
    )
    story_video.add_argument("--video-url", required=True, help="URL HTTPS pública del vídeo")

    reel = subparsers.add_parser("reel", help="Publica un vídeo como Reel")
    reel.add_argument("--video-url", required=True, help="URL HTTPS pública del vídeo")
    reel.add_argument("--caption", default="", help="Texto del Reel")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "verify":
            account = verify_account()
            print(
                json.dumps(
                    {
                        "connected": True,
                        "id": account.get("id"),
                        "username": account.get("username"),
                        "account_type": account.get("account_type"),
                    },
                    ensure_ascii=False,
                )
            )
            return 0

        media_url = getattr(args, "image_url", None) or getattr(args, "video_url", "")
        command_kind = {"story-video": "story_video"}.get(args.command, args.command)
        result = publish_media(
            media_url=media_url,
            caption=getattr(args, "caption", ""),
            kind=command_kind,
        )
        print(json.dumps({"published": True, "media_id": result.get("id")}))
        return 0
    except InstagramAPIError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
