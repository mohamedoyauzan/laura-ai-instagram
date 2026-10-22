"""Prepara las diez fotos iniciales de Jordi y una hoja de revisión visual."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = Path.home() / ".codex" / "generated_images" / "01a159d0-01be-7f80-b411-3e09778e854e"
OUTPUT_DIR = ROOT / "posts" / "jordi"
ASSET_DIR = ROOT / "assets" / "jordi" / "launch"

SOURCES = [
    (ROOT / "assets" / "jordi" / "jordi-master-v1.png", "01-presentacion"),
    (SOURCE_ROOT / "exec-2ae99dc8-5446-4e6a-bb33-c8f582827d85.png", "02-sentadilla"),
    (SOURCE_ROOT / "exec-2c1c8e81-1e8d-4e69-9aff-104bb29a3b23.png", "03-dominadas"),
    (SOURCE_ROOT / "exec-58bbc0f2-7cb8-4417-aa4c-9dcb9de945fe.png", "04-press-inclinado"),
    (SOURCE_ROOT / "exec-718eb8df-17ac-4751-a790-297de430be53.png", "05-peso-muerto-rumano"),
    (SOURCE_ROOT / "exec-ca599daf-398d-4a60-86e0-360b93ca9288.png", "06-jalon-espalda"),
    (SOURCE_ROOT / "exec-8518918c-db0b-4fbe-bf22-08e8b0903498.png", "07-press-hombro"),
    (SOURCE_ROOT / "exec-a2684188-b0d2-496c-ac5f-a7b0a5a54610.png", "08-camino-pesas"),
    (SOURCE_ROOT / "exec-f8cd5386-8eed-4de6-9946-c637c7ed235a.png", "09-post-entreno"),
    (SOURCE_ROOT / "exec-8db7c46f-ee72-4f23-8e64-7acdf60670ef.png", "10-antes-de-empezar"),
]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    thumbs: list[tuple[Image.Image, str]] = []
    for source, stem in SOURCES:
        if not source.is_file():
            raise FileNotFoundError(source)
        image = Image.open(source).convert("RGB")
        source_copy = ASSET_DIR / f"{stem}.png"
        image.save(source_copy, optimize=True)
        post = ImageOps.fit(image, (1080, 1350), method=Image.Resampling.LANCZOS)
        post.save(OUTPUT_DIR / f"{stem}.jpg", quality=94, optimize=True)
        thumbs.append((ImageOps.fit(post, (324, 405), method=Image.Resampling.LANCZOS), stem))

    sheet = Image.new("RGB", (1080, 1995), "#171717")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 26)
    for index, (thumb, stem) in enumerate(thumbs):
        row, col = divmod(index, 3)
        x = 27 + col * 351
        y = 30 + row * 480
        sheet.paste(thumb, (x, y))
        draw.text((x, y + 414), stem, fill="white", font=font)
    sheet.save(ROOT / "jordi-launch-contact-sheet.jpg", quality=92, optimize=True)
    print(f"prepared={len(thumbs)}")


if __name__ == "__main__":
    main()
