"""Renueva de forma segura el token de Instagram antes de que caduque."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"
REFRESH_AFTER = timedelta(days=7)


def read_env() -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#") and "=" in line:
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


def _parse_time(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def refresh_if_due(force: bool = False) -> dict[str, object]:
    config = read_env()
    token = config.get("INSTAGRAM_ACCESS_TOKEN", "")
    if not token:
        raise RuntimeError("Falta INSTAGRAM_ACCESS_TOKEN en .env")

    now = datetime.now(timezone.utc)
    last_refresh = _parse_time(config.get("INSTAGRAM_TOKEN_REFRESHED_AT", ""))
    if not force and last_refresh and now - last_refresh < REFRESH_AFTER:
        return {"refreshed": False, "reason": "not_due", "last_refresh": last_refresh.isoformat()}

    url = "https://graph.instagram.com/refresh_access_token?" + urllib.parse.urlencode(
        {"grant_type": "ig_refresh_token", "access_token": token}
    )
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Instagram no pudo renovar el token (HTTP {exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"No se pudo contactar con Instagram: {exc.reason}") from exc

    new_token = payload.get("access_token")
    if not new_token:
        raise RuntimeError("Instagram no devolvió un token renovado")
    update_env(
        {
            "INSTAGRAM_ACCESS_TOKEN": str(new_token),
            "INSTAGRAM_TOKEN_REFRESHED_AT": now.isoformat(),
        }
    )
    return {
        "refreshed": True,
        "expires_in": payload.get("expires_in"),
        "refreshed_at": now.isoformat(),
    }


if __name__ == "__main__":
    try:
        print(json.dumps(refresh_if_due(), ensure_ascii=False))
    except RuntimeError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1)
