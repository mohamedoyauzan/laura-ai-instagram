"""Publica las entradas pendientes de publication_queue.json.

Durante la ejecución abre un servidor local y un túnel HTTPS temporal para que
Instagram pueda descargar las imágenes. El túnel se cierra al terminar.
"""

from __future__ import annotations

import argparse
import functools
import json
import re
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from instagram_publish import InstagramAPIError, publish_media, verify_account
from token_manager import refresh_if_due


ROOT = Path(__file__).resolve().parent
POSTS_DIR = ROOT / "posts"
QUEUE_PATH = ROOT / "publication_queue.json"
LOCAL_PORT = 8010
TUNNEL_PATTERN = re.compile(r"https://[a-z0-9-]+\.lhr\.life")


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


def read_queue() -> list[dict]:
    return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))


def write_queue(entries: list[dict]) -> None:
    QUEUE_PATH.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def start_file_server() -> ThreadingHTTPServer:
    handler = functools.partial(QuietHandler, directory=str(POSTS_DIR))
    server = ThreadingHTTPServer(("127.0.0.1", LOCAL_PORT), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def start_tunnel(timeout: int = 45) -> tuple[subprocess.Popen[str], str]:
    command = [
        "ssh",
        "-T",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-o",
        "ExitOnForwardFailure=yes",
        "-o",
        "ServerAliveInterval=30",
        "-R",
        f"80:127.0.0.1:{LOCAL_PORT}",
        "nokey@localhost.run",
        "--",
        "--output",
        "text",
    ]
    for attempt in range(3):
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        deadline = time.monotonic() + timeout
        assert process.stdout is not None
        while time.monotonic() < deadline:
            line = process.stdout.readline()
            if line:
                match = TUNNEL_PATTERN.search(line)
                if match:
                    return process, match.group(0)
            elif process.poll() is not None:
                break
            else:
                time.sleep(0.1)
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
        if attempt < 2:
            time.sleep(2)
    raise RuntimeError("El túnel HTTPS no creó una URL después de 3 intentos")


def wait_for_public_file(url: str, timeout: int = 30) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(1)
    raise RuntimeError("La imagen no quedó accesible mediante el túnel")


def public_file_url(public_base: str, local_file: Path) -> str:
    try:
        relative = local_file.resolve().relative_to(POSTS_DIR.resolve()).as_posix()
    except ValueError as exc:
        raise RuntimeError(f"El archivo debe estar dentro de {POSTS_DIR}") from exc
    return f"{public_base}/{urllib.parse.quote(relative, safe='/')}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit", type=int, default=0, help="Máximo de entradas a publicar (0 = todas)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Muestra las pendientes sin publicarlas"
    )
    parser.add_argument("--batch-id", default="", help="Publica solo este lote")
    args = parser.parse_args()

    try:
        refresh_if_due()
    except RuntimeError as exc:
        print(json.dumps({"warning": "token_refresh_failed", "detail": str(exc)}, ensure_ascii=False))
    account = verify_account()
    entries = read_queue()
    pending = [entry for entry in entries if entry.get("status") != "published"]
    if args.batch_id:
        pending = [entry for entry in pending if entry.get("batch_id") == args.batch_id]
    if args.limit > 0:
        pending = pending[: args.limit]

    print(
        json.dumps(
            {
                "account": account.get("username"),
                "pending": len(pending),
                "files": [entry["file"] for entry in pending],
            },
            ensure_ascii=False,
        )
    )
    if args.dry_run or not pending:
        return 0

    server = start_file_server()
    tunnel: subprocess.Popen[str] | None = None
    try:
        tunnel, public_base = start_tunnel()
        first_local_file = ROOT / pending[0]["file"]
        first_url = public_file_url(public_base, first_local_file)
        wait_for_public_file(first_url)
        time.sleep(3)

        for entry in pending:
            local_file = ROOT / entry["file"]
            if not local_file.is_file():
                raise RuntimeError(f"No existe {local_file}")
            image_url = public_file_url(public_base, local_file)
            for attempt in range(1, 4):
                try:
                    media_kind = entry.get("type", "photo")
                    result = publish_media(
                        image_url,
                        entry.get("caption", ""),
                        media_kind,
                    )
                    break
                except InstagramAPIError as exc:
                    if attempt == 3:
                        raise
                    print(
                        json.dumps(
                            {
                                "retry": entry["file"],
                                "attempt": attempt + 1,
                                "reason": str(exc),
                            },
                            ensure_ascii=False,
                        )
                    )
                    time.sleep(5 * attempt)
            entry["status"] = "published"
            entry["media_id"] = result.get("id")
            entry["published_at"] = datetime.now(timezone.utc).isoformat()
            write_queue(entries)
            print(
                json.dumps(
                    {"published": entry["file"], "media_id": result.get("id")},
                    ensure_ascii=False,
                )
            )
        return 0
    except (InstagramAPIError, OSError, RuntimeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    finally:
        if tunnel is not None and tunnel.poll() is None:
            tunnel.terminate()
            try:
                tunnel.wait(timeout=5)
            except subprocess.TimeoutExpired:
                tunnel.kill()
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
