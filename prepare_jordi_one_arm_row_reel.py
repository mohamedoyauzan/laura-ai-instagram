"""Monta un Reel educativo de remo a una mano con cuatro tomas distintas."""

from __future__ import annotations

import shutil
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageFilter


ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets" / "jordi" / "row-one-arm-v2"
OUT = ROOT / "posts" / "jordi" / "reels" / "drafts" / "remo-mancuerna-v2"
WORK = ROOT / "temp" / "remo-mancuerna-v2"
MUSIC = ROOT / "assets" / "music" / "gym-phonk-dopestuff.mp3"
VIDEO = OUT / "jordi-remo-mancuerna-educativo-v2.mp4"
CAPTION = OUT / "caption.txt"

W, H = 1080, 1920
FONT_BOLD = Path("C:/Windows/Fonts/segoeuib.ttf")
FONT = Path("C:/Windows/Fonts/segoeui.ttf")

SCENES = [
    ("setup.png", "¿TU REMO NO TE DA ESPALDA?", "1 · APOYO ESTABLE", "Rodilla y palma firmes", 4.6),
    ("pull.png", "EL PESO EMPIEZA AQUÍ", "2 · CODO A LA CADERA", "No tires hacia el pecho", 4.8),
    ("brace.png", "NO GIRES EL TORSO", "3 · DORSAL ACTIVO", "El brazo solo acompaña", 4.8),
    ("finish.png", "BAJA LENTO. PROGRESA MÁS.", "GUÁRDALO", "Sígueme para más técnica", 4.8),
]


def run(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(result.stderr[-2000:])


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size=size)


def cover(path: Path) -> Image.Image:
    image = Image.open(path).convert("RGB")
    scale = max(W / image.width, H / image.height)
    resized = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS)
    left = (resized.width - W) // 2
    top = (resized.height - H) // 2
    return resized.crop((left, top, left + W, top + H))


def make_card(source: Path, heading: str, step: str, cue: str, destination: Path) -> None:
    base = ImageEnhance.Contrast(cover(source)).enhance(1.04).convert("RGBA")
    base = ImageEnhance.Color(base).enhance(0.84)
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(shade)
    draw.rectangle((0, 0, W, 330), fill=(1, 4, 10, 185))
    draw.rectangle((0, 1450, W, H), fill=(0, 0, 0, 185))
    draw.rounded_rectangle((48, 54, 540, 125), radius=30, fill=(15, 99, 183, 230))
    draw.text((78, 70), "TÉCNICA · ESPALDA", font=font(FONT_BOLD, 30), fill="white")
    heading_lines = textwrap.wrap(heading, width=28)[:2]
    heading_y = 155
    for line in heading_lines:
        draw.text((52, heading_y), line, font=font(FONT_BOLD, 53), fill="white", stroke_width=2, stroke_fill=(0, 0, 0))
        heading_y += 60
    draw.rounded_rectangle((48, 1490, 1032, 1650), radius=30, fill=(2, 8, 16, 235), outline=(58, 154, 240, 230), width=3)
    draw.text((78, 1522), step, font=font(FONT_BOLD, 35), fill=(104, 190, 255))
    draw.text((78, 1575), cue, font=font(FONT_BOLD, 48), fill="white")
    base.alpha_composite(shade.filter(ImageFilter.GaussianBlur(0.35)))
    destination.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(destination, quality=94)


def build_video(cards: list[Path]) -> None:
    inputs: list[str] = []
    for card, scene in zip(cards, SCENES):
        # One still frame per card; zoompan creates exactly the requested
        # duration. Looping the input for the full scene would multiply that
        # duration and make the first card consume the complete Reel.
        inputs += ["-loop", "1", "-t", "0.04", "-i", str(card)]
    visual_filters = []
    for index in range(len(cards)):
        # Each source has a deliberately subtle, different camera drift. The
        # image never pretends to be a generated exercise video.
        drift = "x='iw/2-(iw/zoom/2)+sin(on/18)*5'" if index % 2 == 0 else "y='ih/2-(ih/zoom/2)+sin(on/19)*5'"
        visual_filters.append(
            f"[{index}:v]zoompan=z='min(zoom+0.00032,1.045)':{drift}:d={round(SCENES[index][-1] * 30)}:s=1080x1920:fps=30,format=yuv420p[v{index}]"
        )
    joins = "".join(f"[v{i}]" for i in range(len(cards)))
    visual_filters.append(f"{joins}concat=n={len(cards)}:v=1:a=0[v]")
    music_index = len(cards)
    filter_graph = ";".join(visual_filters) + ";" + (
        f"[{music_index}:a]volume=0.11,afade=t=in:st=0:d=0.8,loudnorm=I=-14:LRA=6:TP=-1.5[a]"
    )
    command = ["ffmpeg", "-y", *inputs, "-stream_loop", "-1", "-ss", "24", "-i", str(MUSIC),
               "-filter_complex", filter_graph, "-map", "[v]", "-map", "[a]", "-shortest",
               "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
               "-movflags", "+faststart", str(VIDEO)]
    run(command)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    cards: list[Path] = []
    for index, scene in enumerate(SCENES, start=1):
        target = WORK / f"card-{index}.jpg"
        make_card(ASSETS / scene[0], *scene[1:-1], target)
        cards.append(target)
    build_video(cards)
    CAPTION.write_text(
        "El remo con mancuerna no va de levantar la pesa como sea. Apoyo firme, torso quieto, codo hacia la cadera y bajada controlada.\n\n"
        "Guárdalo para tu próximo día de espalda.\n\n#Espalda #RemoConMancuerna #TecnicaGym #PullDay #JordiFitt",
        encoding="utf-8",
    )
    print(VIDEO)


if __name__ == "__main__":
    main()
