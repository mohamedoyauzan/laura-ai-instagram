"""Prepara las cuatro fotos y dos historias naturales de Jordi."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parent
GENERATED = Path.home() / ".codex" / "generated_images" / "01a159d0-01be-7f80-b411-3e09778e854e"
OUT = ROOT / "posts" / "jordi" / "2026-10-23-round2"

FEED = [
    ("exec-5d2bd943-abdb-4a57-87d1-e55cfd420972.png", "01-remo-espalda.jpg"),
    ("exec-fb461549-5b65-422f-ab6e-b9f604ef0a36.png", "02-magnesio-peso-muerto.jpg"),
    ("exec-83511c0e-91b8-4ff5-9d63-8ddd08765833.png", "03-elevaciones-laterales.jpg"),
    ("exec-d323171e-efa6-4aa7-acbe-d8dade6cb76c.png", "04-farmers-carry.jpg"),
]

STORIES = [
    (
        "exec-c80e76de-9575-4f5e-aeee-bb7f06ad2d01.png",
        "story-piscina.jpg",
        "RECUPERAR TAMBIEN\nES ENTRENAR",
    ),
    (
        "exec-11dc5411-084a-4145-a93a-83f8408a9f06.png",
        "story-mancuernas.jpg",
        "ULTIMA SERIE.\nTRABAJO HECHO.",
    ),
]


def finish(image: Image.Image) -> Image.Image:
    image = ImageEnhance.Color(image).enhance(0.94)
    image = ImageEnhance.Contrast(image).enhance(1.04)
    return image


def add_story_text(image: Image.Image, text: str) -> Image.Image:
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = ImageFont.truetype("C:/Windows/Fonts/impact.ttf", 76)
    lines = text.split("\n")
    spacing = 10
    boxes = [draw.textbbox((0, 0), line, font=font, stroke_width=2) for line in lines]
    heights = [box[3] - box[1] for box in boxes]
    total_h = sum(heights) + spacing * (len(lines) - 1)
    y = 1540 - total_h / 2
    draw.rounded_rectangle((70, y - 42, 1010, y + total_h + 44), radius=28, fill=(0, 0, 0, 112))
    for line, box, height in zip(lines, boxes, heights):
        width = box[2] - box[0]
        draw.text(
            ((1080 - width) / 2, y),
            line,
            font=font,
            fill=(255, 255, 255, 255),
            stroke_width=4,
            stroke_fill=(0, 0, 0, 230),
        )
        y += height + spacing
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for source_name, output_name in FEED:
        source = Image.open(GENERATED / source_name).convert("RGB")
        image = ImageOps.fit(source, (1080, 1350), method=Image.Resampling.LANCZOS)
        finish(image).save(OUT / output_name, quality=93, optimize=True)

    for source_name, output_name, text in STORIES:
        source = Image.open(GENERATED / source_name).convert("RGB")
        image = ImageOps.fit(source, (1080, 1920), method=Image.Resampling.LANCZOS)
        image = finish(image)
        add_story_text(image, text).save(OUT / output_name, quality=93, optimize=True)

    print(OUT)


if __name__ == "__main__":
    main()
