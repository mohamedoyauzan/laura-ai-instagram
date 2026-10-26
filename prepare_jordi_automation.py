"""Prepara siete días de contenido validado para la automatización de Jordi."""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import subprocess
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps, ImageStat


ROOT = Path(__file__).resolve().parent
PLAN_PATH = ROOT / "jordi_automation_plan.json"
SCHEDULE_PATH = ROOT / "jordi_automation_schedule.json"
OUT = ROOT / "posts" / "jordi" / "automation"
TZ = ZoneInfo("Europe/Madrid")
MUSIC = [
    ROOT / "assets" / "music" / "infernal-dark-phonk-markjuly.mp3",
    ROOT / "assets" / "music" / "gym-phonk-dopestuff.mp3",
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default(size=size)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def technical_image_review(path: Path) -> dict:
    with Image.open(path) as source:
        rgb = ImageOps.exif_transpose(source).convert("RGB")
        grey = rgb.convert("L")
        stat = ImageStat.Stat(grey)
        edge = grey.filter(ImageFilter.FIND_EDGES)
        edge_std = ImageStat.Stat(edge).stddev[0]
        mean = stat.mean[0]
        contrast = stat.stddev[0]
        histogram = grey.histogram()
        pixels = max(1, rgb.width * rgb.height)
        clipped_dark = sum(histogram[:6]) / pixels
        clipped_light = sum(histogram[250:]) / pixels
        reasons: list[str] = []
        # Instagram vuelve a muestrear los originales. 900 px en el lado corto
        # conserva detalle suficiente para el máster vertical generado.
        if min(rgb.size) < 900:
            reasons.append("resolution_below_900px")
        if not 35 <= mean <= 220:
            reasons.append("exposure_out_of_range")
        if contrast < 28:
            reasons.append("contrast_too_low")
        # Las escenas nocturnas tienen menos microcontraste de forma natural.
        if edge_std < 15:
            reasons.append("image_too_soft")
        if clipped_dark > 0.38 or clipped_light > 0.25:
            reasons.append("excessive_clipping")
        return {
            "approved": not reasons,
            "width": rgb.width,
            "height": rgb.height,
            "mean_luma": round(mean, 2),
            "contrast": round(contrast, 2),
            "edge_std": round(edge_std, 2),
            "clipped_dark": round(clipped_dark, 4),
            "clipped_light": round(clipped_light, 4),
            "reasons": reasons,
        }


def fit_with_mild_grade(source: Path, size: tuple[int, int], darken: float = 0.96) -> Image.Image:
    with Image.open(source) as image:
        rgb = ImageOps.exif_transpose(image).convert("RGB")
    fitted = ImageOps.fit(rgb, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    fitted = ImageEnhance.Contrast(fitted).enhance(1.04)
    fitted = ImageEnhance.Color(fitted).enhance(0.94)
    return ImageEnhance.Brightness(fitted).enhance(darken)


def save_feed(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    image = fit_with_mild_grade(source, (1080, 1350), 0.97)
    image.save(destination, "JPEG", quality=92, optimize=True, progressive=True)


def multiline_center(draw: ImageDraw.ImageDraw, text: str, y: int, *, face: ImageFont.FreeTypeFont, fill: str, spacing: int = 14) -> None:
    box = draw.multiline_textbbox((0, 0), text, font=face, spacing=spacing, align="center", stroke_width=2)
    width = box[2] - box[0]
    draw.multiline_text(((1080 - width) / 2, y), text, font=face, fill=fill, spacing=spacing, align="center", stroke_width=2, stroke_fill="#090909")


def save_story(source: Path, destination: Path, text: str, accent: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    image = fit_with_mild_grade(source, (1080, 1920), 0.82)
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle((65, 1320, 1015, 1710), radius=34, fill=(0, 0, 0, 155), outline=(255, 255, 255, 32), width=2)
    draw.text((92, 1355), "JORDI FITT", font=font(34, True), fill=accent)
    lines = text.split("\n", 1)
    draw.text((92, 1435), lines[0], font=font(74, True), fill="white", stroke_width=3, stroke_fill="#080808")
    if len(lines) > 1:
        draw.text((94, 1535), lines[1], font=font(48), fill="#E8E8E8", stroke_width=2, stroke_fill="#080808")
    draw.text((92, 1650), "creador fitness virtual", font=font(26), fill="#B7B7B7")
    Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB").save(destination, "JPEG", quality=91, optimize=True, progressive=True)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, face: ImageFont.FreeTypeFont, max_width: int) -> str:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=face)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return "\n".join(lines)


def save_reel_frame(source: Path, destination: Path, kicker: str, message: str, accent: str, index: int) -> None:
    image = fit_with_mild_grade(source, (1080, 1920), 0.60).convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle((0, 0, 1080, 1920), fill=(0, 0, 0, 65))
    draw.rounded_rectangle((62, 570, 1018, 1335), radius=38, fill=(0, 0, 0, 178), outline=(255, 255, 255, 28), width=2)
    draw.text((90, 615), f"{index:02d}  {kicker}", font=font(32, True), fill=accent)
    body_font = font(72 if len(message) < 36 else 62, True)
    wrapped = wrap_text(draw, message, body_font, 860)
    body_box = draw.multiline_textbbox((0, 0), wrapped, font=body_font, spacing=20, align="center", stroke_width=3)
    body_h = body_box[3] - body_box[1]
    multiline_center(draw, wrapped, 865 - body_h / 2, face=body_font, fill="white", spacing=20)
    draw.text((90, 1260), "GUÁRDALO · JORDI FITT", font=font(28, True), fill="#C8C8C8")
    Image.alpha_composite(image, overlay).convert("RGB").save(destination, "JPEG", quality=91, optimize=True, progressive=True)


def make_reel(frame_paths: list[Path], destination: Path, music: Path, music_start: float) -> None:
    if not music.is_file():
        raise RuntimeError(f"Falta la pista con licencia: {music}")
    inputs: list[str] = []
    filters: list[str] = []
    duration = 3.8
    frames = 30 * duration
    for index, path in enumerate(frame_paths):
        inputs += ["-loop", "1", "-t", f"{duration:.1f}", "-i", str(path)]
        zoom = "0.00034" if index % 2 else "0.00046"
        filters.append(
            f"[{index}:v]scale=1200:2134:force_original_aspect_ratio=increase,crop=1080:1920,"
            f"zoompan=z='min(zoom+{zoom},1.055)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={int(frames)}:s=1080x1920:fps=30,fade=t=in:st=0:d=0.12,"
            f"fade=t=out:st={duration - 0.22:.2f}:d=0.22,format=yuv420p,setpts=PTS-STARTPTS[v{index}]"
        )
    concat = "".join(f"[v{i}]" for i in range(len(frame_paths)))
    graph = ";".join(filters) + f";{concat}concat=n={len(frame_paths)}:v=1:a=0[video]"
    total = duration * len(frame_paths)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg no está instalado")
    filter_script = destination.with_suffix(".filter.txt")
    filter_script.write_text(graph, encoding="utf-8")
    command = [
        ffmpeg, "-y", *inputs, "-ss", str(music_start), "-t", f"{total:.1f}", "-i", str(music),
        "-filter_complex_script", str(filter_script), "-map", "[video]", "-map", f"{len(frame_paths)}:a",
        "-c:v", "libx264", "-profile:v", "high", "-level", "4.1", "-preset", "medium", "-crf", "20",
        "-r", "30", "-g", "60", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
        "-af", f"afade=t=in:st=0:d=0.20,afade=t=out:st={total - 0.8:.2f}:d=0.8,volume=0.90",
        "-movflags", "+faststart", "-shortest", str(destination),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
        # Algunas compilaciones de FFmpeg para Windows devuelven un código de
        # excepción después de cerrar un MP4 válido. Verificamos el artefacto
        # final con ffprobe antes de considerarlo un fallo real.
        probe = subprocess.run(
            [
                shutil.which("ffprobe") or "ffprobe", "-v", "error",
                "-show_entries", "format=duration:stream=codec_name,width,height",
                "-of", "json", str(destination),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        valid = False
        if probe.returncode == 0:
            try:
                metadata = json.loads(probe.stdout)
                streams = metadata.get("streams", [])
                video = next(stream for stream in streams if stream.get("codec_name") == "h264")
                audio = next(stream for stream in streams if stream.get("codec_name") == "aac")
                duration_probe = float(metadata.get("format", {}).get("duration", 0))
                valid = video.get("width") == 1080 and video.get("height") == 1920 and bool(audio) and 15 <= duration_probe <= 30
            except (StopIteration, TypeError, ValueError, json.JSONDecodeError):
                valid = False
        if result.returncode and not valid:
            detail = (result.stderr or result.stdout or f"FFmpeg terminó con {result.returncode}")[-5000:]
            raise RuntimeError(detail)
        if not valid:
            raise RuntimeError(f"El Reel generado no supera ffprobe: {probe.stderr[-2000:]}")
    finally:
        filter_script.unlink(missing_ok=True)


def main() -> None:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    start = date.fromisoformat(plan["start_date"])
    times = {key: time.fromisoformat(value) for key, value in plan["times"].items()}
    sources = [ROOT / item["source"] for item in plan["days"]]
    for source in sources:
        if not source.is_file():
            raise FileNotFoundError(source)

    schedule: dict = {
        "version": 1,
        "timezone": plan["timezone"],
        "account_username": plan["account_username"],
        "generated_at": datetime.now(TZ).isoformat(),
        "items": [],
    }
    accents = ["#E8FF36", "#FF6B35", "#46D3FF", "#F6C945", "#9CFF57", "#FF4F73", "#D1B3FF"]

    for day_index, item in enumerate(plan["days"]):
        day_date = start + timedelta(days=day_index)
        source = sources[day_index]
        review = technical_image_review(source)
        if not review["approved"]:
            raise RuntimeError(f"{source} no supera el filtro técnico: {review['reasons']}")
        day_dir = OUT / day_date.isoformat()
        frames_dir = day_dir / "frames"
        day_dir.mkdir(parents=True, exist_ok=True)
        frames_dir.mkdir(parents=True, exist_ok=True)
        accent = accents[day_index]

        post = day_dir / "post.jpg"
        story_1 = day_dir / "story-13h.jpg"
        story_2 = day_dir / "story-15h.jpg"
        reel = day_dir / "reel.mp4"
        save_feed(source, post)
        save_story(source, story_1, item["story_1"], accent)
        save_story(sources[(day_index + 1) % len(sources)], story_2, item["story_2"], accent)

        frame_paths: list[Path] = []
        for frame_index, line in enumerate(item["reel_lines"], 1):
            frame_source = sources[(day_index + frame_index - 1) % len(sources)]
            frame_path = frames_dir / f"{frame_index:02d}.jpg"
            save_reel_frame(frame_source, frame_path, item["reel_title"], line, accent, frame_index)
            frame_paths.append(frame_path)
        music = MUSIC[day_index % len(MUSIC)]
        make_reel(frame_paths, reel, music, music_start=8 + (day_index * 11) % 45)

        quality = {
            "status": "approved",
            "source_sha256": sha256(source),
            "technical": review,
            "visual_review": item["review"],
        }
        rows = [
            ("post", times["post"], post, item["post_caption"]),
            ("reel", times["reel"], reel, item["reel_caption"]),
            ("story", times["story_1"], story_1, ""),
            ("story", times["story_2"], story_2, ""),
        ]
        for slot, publish_time, path, caption in rows:
            published_at = datetime.combine(day_date, publish_time, tzinfo=TZ)
            schedule["items"].append({
                "id": f"{item['id']}-{slot}-{publish_time.strftime('%H%M')}",
                "publish_at": published_at.isoformat(),
                "kind": slot,
                "file": path.relative_to(ROOT).as_posix(),
                "caption": caption,
                "quality": quality if slot == "post" else {"status": "derived_from_approved_source", "source_sha256": quality["source_sha256"]},
                "status": "pending",
            })

    SCHEDULE_PATH.write_text(json.dumps(schedule, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"prepared": len(schedule["items"]), "days": len(plan["days"]), "schedule": str(SCHEDULE_PATH)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
