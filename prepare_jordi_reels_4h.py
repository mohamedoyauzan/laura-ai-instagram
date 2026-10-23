"""Prepara dos Reels de Jordi para publicar cuatro horas después."""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MEDIA = ROOT / "posts" / "jordi" / "2026-10-23-round2"
OUT = ROOT / "posts" / "jordi" / "reels" / "scheduled"
MUSIC = ROOT / "assets" / "music" / "gym-phonk-dopestuff.mp3"
FONT = "C\\:/Windows/Fonts/impact.ttf"


REELS = [
    {
        "output": "jordi-espalda-hombros-v1.mp4",
        "music_start": 28,
        "images": [
            "01-remo-espalda.jpg",
            "03-elevaciones-laterales.jpg",
            "01-remo-espalda.jpg",
            "03-elevaciones-laterales.jpg",
        ],
        "texts": ["ESPALDA FUERTE", "REMO CONTROLADO", "HOMBROS SIN IMPULSO", "TECNICA > EGO"],
    },
    {
        "output": "jordi-entreno-recuperacion-v1.mp4",
        "music_start": 46,
        "images": [
            "02-magnesio-peso-muerto.jpg",
            "04-farmers-carry.jpg",
            "story-mancuernas.jpg",
            "story-piscina.jpg",
        ],
        "texts": ["ENTRENA DURO", "RECUPERA MEJOR", "AGUA + COMIDA + SUENO", "VUELVE MAS FUERTE"],
    },
]


def make_reel(spec: dict) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    inputs: list[str] = []
    chains: list[str] = []
    for index, name in enumerate(spec["images"]):
        inputs.extend(["-i", str(MEDIA / name)])
        zoom = "0.00045" if index % 2 else "0.00058"
        chains.append(
            f"[{index}:v]scale=1200:2134:force_original_aspect_ratio=increase,"
            "crop=1080:1920,setsar=1,"
            f"zoompan=z='min(zoom+{zoom},1.075)':"
            "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=120:s=1080x1920:fps=30,"
            "eq=contrast=1.10:saturation=0.88:brightness=-0.055,"
            "fade=t=in:st=0:d=0.12,fade=t=out:st=3.78:d=0.22,"
            "format=yuv420p,setpts=PTS-STARTPTS"
            f"[v{index}]"
        )

    concat = "".join(f"[v{i}]" for i in range(4))
    text = ["drawbox=x=60:y=690:w=960:h=420:color=black@0.38:t=fill"]
    for index, label in enumerate(spec["texts"]):
        color = "0xE7FF19" if index in {0, 3} else "white"
        start = index * 4 + 0.20
        end = index * 4 + 3.80
        text.append(
            f"drawtext=fontfile='{FONT}':text='{label}':fontcolor={color}:"
            "fontsize=91:borderw=6:bordercolor=black@0.95:"
            f"x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,{start:.2f},{end:.2f})'"
        )

    graph = ";".join(chains) + ";" + concat + "concat=n=4:v=1:a=0[base];[base]" + ",".join(text) + "[video]"
    output = OUT / spec["output"]
    command = [
        "ffmpeg", "-y", *inputs,
        "-ss", str(spec["music_start"]), "-t", "16", "-i", str(MUSIC),
        "-filter_complex", graph,
        "-map", "[video]", "-map", "4:a",
        "-c:v", "libx264", "-profile:v", "high", "-level", "4.1",
        "-preset", "medium", "-crf", "19", "-r", "30", "-g", "60",
        "-pix_fmt", "yuv420p", "-color_range", "tv", "-colorspace", "bt709",
        "-color_primaries", "bt709", "-color_trc", "bt709",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-af", "afade=t=in:st=0:d=0.15,afade=t=out:st=15.25:d=0.75,volume=0.96",
        "-movflags", "+faststart", "-shortest", str(output),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    if completed.returncode:
        raise RuntimeError(completed.stderr[-5000:])
    return output


def main() -> None:
    for reel in REELS:
        print(make_reel(reel))


if __name__ == "__main__":
    main()
