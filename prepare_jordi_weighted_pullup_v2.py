"""Reel de dominada lastrada: texto en zona segura, sin zoom ni cajas."""

from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets" / "jordi" / "weighted-pullup-v2"
WORK = ROOT / "temp" / "weighted-pullup-v2"
OUT = ROOT / "posts" / "jordi" / "reels" / "drafts" / "dominada-lastrada-v2"
MUSIC = ROOT / "assets" / "music" / "infernal-dark-phonk-markjuly.mp3"
VIDEO = OUT / "jordi-dominada-lastrada-educativo-v2.mp4"
CAPTION = OUT / "caption.txt"
W, H = 1080, 1920
FB = Path("C:/Windows/Fonts/segoeuib.ttf")
FR = Path("C:/Windows/Fonts/segoeui.ttf")

SCENES = [
    ("start.png", "DOMINADA LASTRADA", "Empieza sin encoger los hombros", "01 · CUELGA ACTIVO", 4.5),
    ("hang.png", "PRIMERO: HOMBROS ABAJO", "Antes de doblar el codo", "02 · FIJA ESCÁPULAS", 4.5),
    ("top.png", "TIRA LOS CODOS HACIA ABAJO", "No busques solo la barbilla", "03 · DORSAL + CODO", 4.5),
    ("pull.png", "PAUSA. BAJA. REPITE.", "Controla también la bajada", "GUÁRDALO PARA PULL DAY", 4.5),
]


def run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(result.stderr[-2000:])


def fit(path: Path) -> Image.Image:
    source = Image.open(path).convert("RGB")
    scale = max(W / source.width, H / source.height)
    resized = source.resize((round(source.width * scale), round(source.height * scale)), Image.Resampling.LANCZOS)
    return resized.crop(((resized.width - W) // 2, (resized.height - H) // 2, (resized.width - W) // 2 + W, (resized.height - H) // 2 + H))


def lines(text: str, width: int) -> list[str]:
    return textwrap.wrap(text, width=width)[:3]


def card(source: Path, title: str, cue: str, label: str, destination: Path) -> None:
    base = ImageEnhance.Contrast(fit(source)).enhance(1.03).convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    # Safe area: headline begins below the profile/avatar region and the cue
    # ends above the caption/share controls. No framed panels touch screen edges.
    draw.rectangle((0, 285, W, 600), fill=(0, 0, 0, 105))
    draw.rectangle((0, 1110, W, 1410), fill=(0, 0, 0, 100))
    y = 350
    for line in lines(title, 25):
        draw.text((W // 2, y), line, anchor="ma", font=ImageFont.truetype(str(FB), 64), fill="white", stroke_width=3, stroke_fill=(0, 0, 0))
        y += 73
    draw.text((W // 2, 1160), label, anchor="ma", font=ImageFont.truetype(str(FB), 31), fill=(255, 190, 75), stroke_width=2, stroke_fill=(0, 0, 0))
    y = 1220
    for line in lines(cue, 31):
        draw.text((W // 2, y), line, anchor="ma", font=ImageFont.truetype(str(FB), 48), fill="white", stroke_width=2, stroke_fill=(0, 0, 0))
        y += 58
    base.alpha_composite(overlay)
    destination.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(destination, quality=94)


def main() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    cards: list[Path] = []
    command = ["ffmpeg", "-y"]
    for index, scene in enumerate(SCENES):
        target = WORK / f"scene-{index + 1}.jpg"
        card(ASSETS / scene[0], *scene[1:-1], target)
        cards.append(target)
        command += ["-loop", "1", "-t", str(scene[-1]), "-i", str(target)]
    for index in range(len(cards)):
        command += []
    command += ["-stream_loop", "-1", "-ss", "48", "-i", str(MUSIC)]
    inputs = "".join(f"[{i}:v]scale=1080:1920,setsar=1[v{i}];" for i in range(len(cards)))
    joined = "".join(f"[v{i}]" for i in range(len(cards)))
    graph = inputs + f"{joined}concat=n={len(cards)}:v=1:a=0[v];[{len(cards)}:a]volume=0.11,afade=t=in:st=0:d=0.7,loudnorm=I=-14:LRA=6:TP=-1.5[a]"
    command += ["-filter_complex", graph, "-map", "[v]", "-map", "[a]", "-shortest", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(VIDEO)]
    run(command)
    CAPTION.write_text(
        "La dominada lastrada no empieza tirando fuerte: empieza colocando las escápulas. Hombros abajo, codos hacia las costillas y bajada bajo control.\n\n"
        "Guárdalo para tu próximo Pull Day.\n\n#DominadaLastrada #Espalda #PullDay #TecnicaGym #JordiFitt",
        encoding="utf-8",
    )
    print(VIDEO)


if __name__ == "__main__":
    main()
