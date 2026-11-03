"""Genera la locución consistente de Jordi con una voz española autorizada.

Configuración requerida (local o en GitHub Actions):
  JORDI_TTS_API_KEY       clave del proveedor de voz
  JORDI_TTS_VOICE_ID      voz española masculina licenciada o creada con consentimiento

La voz se mantiene idéntica entre Reels, pero nunca se clona ni imita a una
persona real sin autorización verificable.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def synthesize(text: str, output: Path) -> None:
    api_key = os.environ.get("JORDI_TTS_API_KEY", "")
    voice_id = os.environ.get("JORDI_TTS_VOICE_ID", "")
    if not api_key or not voice_id:
        raise RuntimeError("Faltan JORDI_TTS_API_KEY o JORDI_TTS_VOICE_ID")

    request = urllib.request.Request(
        "https://api.elevenlabs.io/v1/text-to-speech/"
        + urllib.parse.quote(voice_id, safe="")
        + "?output_format=mp3_44100_128",
        data=json.dumps(
            {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "language_code": "es",
                "voice_settings": {
                    "stability": 0.48,
                    "similarity_boost": 0.78,
                    "style": 0.05,
                    "use_speaker_boost": True,
                },
            }
        ).encode("utf-8"),
        method="POST",
        headers={"xi-api-key": api_key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            audio = response.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"El proveedor de voz rechazó la generación (HTTP {exc.code})") from exc
    if len(audio) < 4_000:
        raise RuntimeError("El proveedor devolvió audio incompleto")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(audio)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    synthesize(args.text, args.out)
    print(args.out)


if __name__ == "__main__":
    main()
