"""Sincroniza el acceso vigente de Jordi con los secretos de GitHub Actions.

No imprime tokens ni los guarda en archivos del repositorio.
"""

from __future__ import annotations

import base64
import json
import subprocess
import urllib.request
from pathlib import Path

from nacl.public import PublicKey, SealedBox


ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env.jordi"
REPOSITORY = "mohamedoyauzan/laura-ai-instagram"


def env_values() -> dict[str, str]:
    result: dict[str, str] = {}
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


def github_token() -> str:
    response = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        capture_output=True,
        text=True,
        check=True,
    )
    values = dict(line.split("=", 1) for line in response.stdout.splitlines() if "=" in line)
    token = values.get("password", "")
    if not token:
        raise RuntimeError("No hay una sesión de GitHub disponible en este equipo")
    return token


def request(url: str, token: str, payload: dict | None = None, method: str = "GET") -> dict:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    call = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "Jordi-Automation-Setup",
        },
    )
    with urllib.request.urlopen(call, timeout=30) as response:
        content = response.read().decode("utf-8")
        return json.loads(content) if content else {"status": response.status}


def main() -> None:
    values = env_values()
    access_token = values.get("INSTAGRAM_ACCESS_TOKEN", "")
    user_id = values.get("INSTAGRAM_USER_ID", "")
    if not access_token or not user_id:
        raise RuntimeError("Faltan credenciales renovadas de Jordi")
    token = github_token()
    key = request(f"https://api.github.com/repos/{REPOSITORY}/actions/secrets/public-key", token)
    box = SealedBox(PublicKey(base64.b64decode(key["key"])))
    updated: list[str] = []
    for name, value in {
        "JORDI_INSTAGRAM_ACCESS_TOKEN": access_token,
        "JORDI_INSTAGRAM_USER_ID": user_id,
    }.items():
        encrypted = base64.b64encode(box.encrypt(value.encode("utf-8"))).decode("ascii")
        request(
            f"https://api.github.com/repos/{REPOSITORY}/actions/secrets/{name}",
            token,
            {"encrypted_value": encrypted, "key_id": key["key_id"]},
            "PUT",
        )
        updated.append(name)
    print(json.dumps({"updated": updated, "repository": REPOSITORY}))


if __name__ == "__main__":
    main()
