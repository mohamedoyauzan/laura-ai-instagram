"""Build a vertical travel Reel from licensed real footage at zero API cost."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import textwrap
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parent
WORK = ROOT / "temp" / "free-vlog"
VOICE_DIR = WORK / "voices"
VOICE_BASE = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
    "es/es_ES/sharvard/medium/es_ES-sharvard-medium"
)
FONT_CANDIDATES = [
    Path("C:/Windows/Fonts/segoeuib.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
]


def run(command: list[str]) -> None:
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    if completed.returncode:
        raise RuntimeError(completed.stderr[-3000:])


def download(url: str, destination: Path) -> Path:
    if destination.is_file() and destination.stat().st_size > 0:
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "LauraContentBot/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)
    return destination


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in FONT_CANDIDATES:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def make_card(source_path: Path, text: str, output: Path, *, bottom: bool = False) -> None:
    source = Image.open(source_path).convert("RGB")
    canvas = ImageOps.fit(source, (1080, 1920), method=Image.Resampling.LANCZOS)
    canvas = ImageEnhance.Contrast(canvas).enhance(0.94).convert("RGBA")
    shade = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shade_draw = ImageDraw.Draw(shade)
    start = 1210 if bottom else 0
    end = 1920 if bottom else 720
    for y in range(start, end):
        progress = (y - start) / max(1, end - start)
        alpha = int(185 * (1 - progress if bottom else progress))
        shade_draw.line((0, y, 1080, y), fill=(0, 0, 0, alpha))
    canvas = Image.alpha_composite(canvas, shade)
    draw = ImageDraw.Draw(canvas)
    title_font = font(68 if not bottom else 58)
    lines = "\n".join(textwrap.wrap(text, width=22)[:4])
    y = 1450 if bottom else 130
    draw.multiline_text(
        (540, y), lines, font=title_font, fill="white", anchor="ma",
        align="center", spacing=14, stroke_width=3, stroke_fill=(0, 0, 0, 180),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output, quality=94)


def make_still_segment(image: Path, duration: float, output: Path) -> None:
    run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(image), "-t", str(duration),
        "-vf", "scale=1080:1920,format=yuv420p", "-r", "30", "-an",
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", str(output),
    ])


def make_video_segment(source: Path, start: float, duration: float, output: Path) -> None:
    filter_graph = (
        "[0:v]split=2[bg][fg];"
        "[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        "gblur=sigma=32,eq=brightness=-0.25:saturation=0.8[bg2];"
        "[fg]scale=1080:-2[fg2];"
        "[bg2][fg2]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]"
    )
    run([
        "ffmpeg", "-y", "-ss", str(start), "-i", str(source), "-t", str(duration),
        "-filter_complex", filter_graph, "-map", "[v]", "-r", "30", "-an",
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", str(output),
    ])


def ensure_voice() -> tuple[Path, Path]:
    model = download(f"{VOICE_BASE}.onnx", VOICE_DIR / "es_ES-sharvard-medium.onnx")
    config = download(f"{VOICE_BASE}.onnx.json", VOICE_DIR / "es_ES-sharvard-medium.onnx.json")
    return model, config


def make_voice(text: str, output: Path) -> None:
    model, config = ensure_voice()
    completed = subprocess.run(
        [
            "piper", "-m", str(model), "-c", str(config), "-s", "1",
            "--length-scale", "0.92", "--sentence-silence", "0.2", "-f", str(output),
        ],
        input=text, text=True, capture_output=True, encoding="utf-8",
    )
    if completed.returncode:
        raise RuntimeError(completed.stderr[-2000:])


def build(manifest_path: Path) -> Path:
    spec = json.loads(manifest_path.read_text(encoding="utf-8"))
    WORK.mkdir(parents=True, exist_ok=True)
    slug = spec["id"]
    render_dir = WORK / slug
    render_dir.mkdir(parents=True, exist_ok=True)
    source = download(spec["video_url"], render_dir / "source.webm")
    image = ROOT / spec["image"]
    intro = render_dir / "intro.jpg"
    outro = render_dir / "outro.jpg"
    make_card(image, spec["hook"], intro)
    make_card(image, spec["outro"], outro, bottom=True)

    parts: list[Path] = []
    intro_mp4 = render_dir / "part-00.mp4"
    make_still_segment(intro, float(spec.get("intro_duration", 1.6)), intro_mp4)
    parts.append(intro_mp4)
    for index, segment in enumerate(spec["segments"], start=1):
        path = render_dir / f"part-{index:02d}.mp4"
        make_video_segment(source, float(segment["start"]), float(segment["duration"]), path)
        parts.append(path)
    outro_mp4 = render_dir / f"part-{len(parts):02d}.mp4"
    make_still_segment(outro, float(spec.get("outro_duration", 2.3)), outro_mp4)
    parts.append(outro_mp4)

    concat_file = render_dir / "concat.txt"
    concat_file.write_text(
        "".join(f"file '{path.as_posix()}'\n" for path in parts), encoding="utf-8"
    )
    silent = render_dir / "silent.mp4"
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c", "copy", str(silent),
    ])
    voice = render_dir / "voice.wav"
    make_voice(spec["voiceover"], voice)
    output = ROOT / spec["output"]
    output.parent.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg", "-y", "-i", str(silent), "-i", str(voice),
        "-filter_complex", "[1:a]volume=1.25,apad=pad_dur=2[a]",
        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
        "-shortest", "-movflags", "+faststart", str(output),
    ])
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    print(build(args.manifest.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
