"""Prepara un Reel educativo breve de remo con apoyo de pecho."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "assets" / "jordi" / "row-education"
OUT = ROOT / "posts" / "jordi" / "reels" / "ready" / "row-chest-supported-v1"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "arialbd.ttf" if bold else "arial.ttf"
    return ImageFont.truetype(name, size)


def make_frame(source: Path, destination: Path, title: str, cue: str, accent: str) -> None:
    image = Image.open(source).convert("RGB").resize((1080, 1920), Image.Resampling.LANCZOS)
    shade = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(shade)
    draw.rounded_rectangle((58, 72, 1022, 244), radius=30, fill=(0, 0, 0, 150))
    draw.rounded_rectangle((58, 1538, 1022, 1808), radius=30, fill=(5, 8, 8, 190))
    draw.rectangle((90, 111, 104, 202), fill=accent)
    draw.text((132, 100), title, font=font(44, True), fill="white")
    draw.text((92, 1583), cue, font=font(52, True), fill="white", spacing=8)
    draw.text((92, 1740), "REMO CON APOYO DE PECHO", font=font(26, True), fill=accent)
    Image.alpha_composite(image.convert("RGBA"), shade).convert("RGB").save(destination, "JPEG", quality=93)


def make_story(source: Path, destination: Path, eyebrow: str, message: str, accent: str) -> None:
    image = Image.open(source).convert("RGB").resize((1080, 1920), Image.Resampling.LANCZOS)
    shade = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(shade)
    draw.rounded_rectangle((56, 92, 1024, 350), radius=32, fill=(0, 0, 0, 165))
    draw.text((90, 132), eyebrow, font=font(30, True), fill=accent)
    draw.text((90, 190), message, font=font(50, True), fill="white", spacing=8)
    draw.text((90, 1805), "JORDI FITT", font=font(28, True), fill="white")
    Image.alpha_composite(image.convert("RGBA"), shade).convert("RGB").save(destination, "JPEG", quality=93)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    bottom = SOURCE / "row-bottom-v1.png"
    top = SOURCE / "row-top-v1.png"
    frames = [
        (bottom, "¿NO NOTAS LA ESPALDA?", "NO TIRES CON EL CUELLO", "#D5FF44"),
        (bottom, "1 · BASE ESTABLE", "PECHO PEGADO AL BANCO", "#52C7FF"),
        (top, "2 · EL TIRÓN", "CODOS HACIA LA CADERA", "#FF9952"),
        (bottom, "3 · LA VUELTA", "BAJA LENTO · 2 SEGUNDOS", "#D5FF44"),
        (top, "PULL DAY", "GUÁRDALO PARA TU PRÓXIMA SESIÓN", "#52C7FF"),
    ]
    for index, (source, title, cue, accent) in enumerate(frames, 1):
        make_frame(source, OUT / f"frame-{index:02d}.jpg", title, cue, accent)
    make_story(bottom, OUT / "story-rem-row.jpg", "PULL DAY", "REMAR SIN IMPULSO\nCAMBIA TODO", "#D5FF44")
    make_story(SOURCE / "story-post-workout-v1.png", OUT / "story-exit.jpg", "POST ENTRENO", "HOY: TÉCNICA\nANTES QUE PESO", "#52C7FF")
    (OUT / "caption.txt").write_text(
        "El remo con apoyo de pecho te quita impulso y te obliga a mover con la espalda. "
        "Pecho estable, codos hacia la cadera y vuelta lenta.\n\n"
        "#Espalda #PullDay #TecnicaGym #JordiFitt",
        encoding="utf-8",
    )
    print(OUT)


if __name__ == "__main__":
    main()
