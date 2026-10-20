"""Autorización local para Instagram API with Instagram Login.

Inicia un servidor en http://localhost:8787/callback, intercambia el código
de autorización por un token de larga duración y lo guarda en .env sin
imprimir credenciales en la consola.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"
# Instagram exige HTTPS para la URI registrada. El servidor local escucha por
# HTTP para que el usuario pueda reenviar manualmente el código cuando el
# navegador integrado no admite el certificado autofirmado.
REDIRECT_URI = "https://localhost:8787/callback"
HOST = "127.0.0.1"
PORT = 8787


def read_env() -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def update_env(updates: dict[str, str]) -> None:
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    pending = dict(updates)
    output: list[str] = []
    for line in lines:
        if "=" in line and not line.lstrip().startswith("#"):
            key = line.split("=", 1)[0].strip()
            if key in pending:
                output.append(f"{key}={pending.pop(key)}")
                continue
        output.append(line)
    output.extend(f"{key}={value}" for key, value in pending.items())
    ENV_PATH.write_text("\n".join(output) + "\n", encoding="utf-8")


def post_form(url: str, values: dict[str, str]) -> dict:
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(values).encode("utf-8"),
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def get_json(url: str, params: dict[str, str]) -> dict:
    request_url = f"{url}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(request_url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def exchange_code(code: str) -> tuple[str, str]:
    config = read_env()
    app_id = config.get("META_APP_ID", "")
    app_secret = config.get("META_APP_SECRET", "")
    if not app_id or not app_secret:
        raise RuntimeError("Faltan META_APP_ID o META_APP_SECRET en .env")

    short = post_form(
        "https://api.instagram.com/oauth/access_token",
        {
            "client_id": app_id,
            "client_secret": app_secret,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
            "code": code,
        },
    )
    short_token = short["access_token"]
    user_id = str(short.get("user_id", ""))

    long_lived = get_json(
        "https://graph.instagram.com/access_token",
        {
            "grant_type": "ig_exchange_token",
            "client_secret": app_secret,
            "access_token": short_token,
        },
    )
    token = long_lived["access_token"]

    if not user_id:
        profile = get_json(
            "https://graph.instagram.com/me",
            {"fields": "id", "access_token": token},
        )
        user_id = str(profile["id"])

    update_env(
        {
            "INSTAGRAM_ACCESS_TOKEN": token,
            "INSTAGRAM_USER_ID": user_id,
            "INSTAGRAM_TOKEN_REFRESHED_AT": datetime.now(timezone.utc).isoformat(),
        }
    )
    return token, user_id


class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/callback":
            self.send_error(404)
            return

        params = urllib.parse.parse_qs(parsed.query)
        if "error" in params:
            detail = params.get("error_description", params["error"])[0]
            self.respond(400, f"Instagram rechazó la autorización: {detail}")
            return

        code = params.get("code", [""])[0].split("#", 1)[0]
        if not code:
            self.respond(400, "No se recibió el código de autorización.")
            return

        try:
            _, user_id = exchange_code(code)
        except (KeyError, RuntimeError, urllib.error.URLError) as exc:
            self.respond(500, f"No se pudo completar la autorización: {exc}")
            return

        self.respond(
            200,
            f"Instagram conectado correctamente (ID {user_id}). Ya puedes cerrar esta pestaña.",
        )
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def respond(self, status: int, message: str) -> None:
        body = (
            "<!doctype html><meta charset='utf-8'>"
            "<title>Instagram conectado</title>"
            "<style>body{font:18px system-ui;max-width:720px;margin:80px auto;padding:24px}"
            "h1{color:#16784b}</style>"
            f"<h1>{message}</h1>"
        ).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def authorization_url() -> str:
    app_id = read_env().get("META_APP_ID", "")
    query = urllib.parse.urlencode(
        {
            "client_id": app_id,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": (
                "instagram_business_basic,"
                "instagram_business_content_publish,"
                "instagram_business_manage_insights,"
                "instagram_business_manage_comments"
            ),
            "force_reauth": "true",
        }
    )
    return f"https://www.instagram.com/oauth/authorize?{query}"


if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), OAuthHandler)
    print("Receptor local preparado en http://localhost:8787/callback")
    print("Abre esta URL para autorizar Instagram:")
    print(authorization_url())
    server.serve_forever()

