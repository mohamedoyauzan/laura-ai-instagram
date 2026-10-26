"""Publica de forma reanudable el lote de gimnasio y cenas semanales de Jordi."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
os.environ.setdefault("INSTAGRAM_ENV_FILE", str(ROOT / ".env.jordi"))

from instagram_publish import InstagramAPIError, publish_media, verify_account  # noqa: E402


STATE_PATH = ROOT / "jordi_weekly_dinners_publish_state.json"
RAW = "https://raw.githubusercontent.com/mohamedoyauzan/laura-ai-instagram/main/"

ITEMS = [
    {
        "id": "feed-bulgarian-split-squat",
        "file": "posts/jordi/2026-10-26-weekly-dinners/01-bulgarian-split-squat.jpg",
        "kind": "photo",
        "caption": (
            "La búlgara no necesita más peso cuando controlas de verdad la bajada. "
            "Rodilla estable, torso firme y cada repetición igual a la anterior. "
            "¿La haces al inicio o al final de pierna?\n\n"
            "#Pierna #SentadillaBulgara #GymTips #FitnessEspaña #JordiFitt"
        ),
    },
    {
        "id": "feed-seated-cable-row",
        "file": "posts/jordi/2026-10-26-weekly-dinners/02-seated-cable-row.jpg",
        "kind": "photo",
        "caption": (
            "En el remo sentado, no tires solo con los brazos: fija el torso, lleva "
            "los codos atrás y controla la vuelta. La espalda también se entrena en "
            "la fase excéntrica.\n\n"
            "#Espalda #RemoSentado #TecnicaGym #FitnessEspaña #JordiFitt"
        ),
    },
    {
        "id": "reel-seven-weekly-dinners",
        "file": "posts/jordi/2026-10-26-weekly-dinners/jordi-7-cenas-semana.mp4",
        "kind": "reel",
        "caption": (
            "7 cenas fitness para organizar toda la semana. Las calorías y la proteína "
            "son aproximadas: ajusta las cantidades a tu objetivo, hambre y gasto diario. "
            "Guarda el menú y compártelo con quien siempre pregunta qué cenar.\n\n"
            "#CenasFitness #MealPrep #NutricionDeportiva #Proteina #FitnessEspaña #JordiFitt"
        ),
    },
    {
        "id": "story-weekly-shopping",
        "file": "posts/jordi/2026-10-26-weekly-dinners/story-01-compra.jpg",
        "kind": "story",
        "caption": "",
    },
    {
        "id": "story-seven-dinners",
        "file": "posts/jordi/2026-10-26-weekly-dinners/story-02-cenas.jpg",
        "kind": "story",
        "caption": "",
    },
]


def load_state() -> dict:
    if STATE_PATH.is_file():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"items": {}}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    try:
        account = verify_account()
        if account.get("username") != "jordi_fitt":
            raise RuntimeError(f"Cuenta inesperada: {account.get('username')}")

        state = load_state()
        for item in ITEMS:
            if state["items"].get(item["id"], {}).get("status") == "published":
                print(json.dumps({"skipped": item["id"]}, ensure_ascii=False))
                continue

            result = publish_media(RAW + item["file"], item["caption"], item["kind"])
            state["items"][item["id"]] = {
                "status": "published",
                "media_id": result.get("id"),
                "published_at": datetime.now(timezone.utc).isoformat(),
                "file": item["file"],
            }
            save_state(state)
            print(json.dumps({"published": item["id"], "media_id": result.get("id")}, ensure_ascii=False))
            time.sleep(3)
        return 0
    except (InstagramAPIError, OSError, RuntimeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
