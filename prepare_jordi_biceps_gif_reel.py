"""Create a beginner-friendly animated biceps-curl GIF and narrated Reel draft."""

from __future__ import annotations

import math
import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np
import soundfile as sf
from kokoro import KPipeline
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent
ASSET_DIR = ROOT / "assets" / "jordi" / "infographic"
BOTTOM_PATH = ASSET_DIR / "biceps-curl-bottom-v2.png"
MIDDLE_PATH = ASSET_DIR / "biceps-curl-manikin-v1.png"
TOP_PATH = ASSET_DIR / "biceps-curl-top-v2.png"
PORTRAIT_PATH = ASSET_DIR / "jordi-presenter-v2.png"
MUSIC_PATH = ROOT / "assets" / "music" / "infernal-dark-phonk-markjuly.mp3"

OUT_DIR = ROOT / "posts" / "jordi" / "reels" / "drafts"
TEMP_DIR = ROOT / "temp" / "jordi-biceps-gif-v8"
OUTPUT = OUT_DIR / "jordi-curl-principiantes-v10-follow.mp4"
GIF_OUTPUT = OUT_DIR / "jordi-curl-principiantes-v10-follow.gif"
CAPTION_OUTPUT = OUT_DIR / "jordi-curl-principiantes-v10-follow-caption.txt"
VOICE_OUTPUT = TEMP_DIR / "voice.wav"
EXTERNAL_VOICE = TEMP_DIR / "voice-alvaro-neural.mp3"
VISUAL_OUTPUT = TEMP_DIR / "visual.mp4"

W, H, FPS = 720, 1280, 30
POSE_W, POSE_H = 520, 780
POSE_X, POSE_Y = 100, 275

BG = (4, 7, 14, 255)
WHITE = (247, 249, 252, 255)
MUTED = (164, 179, 199, 255)
BLUE = (61, 151, 255, 255)
ORANGE = (255, 170, 54, 255)
RED = (250, 71, 82, 255)
GREEN = (63, 221, 157, 255)

SENTENCES = [
    "Mira este brazo.",
    "Empieza abajo, sin balancearte.",
    "En la mitad es donde más cuesta.",
    "Sube sin mover el codo.",
    "Arriba, aprieta un segundo.",
    "Y ahora baja despacio.",
    "Así haces una repetición limpia.",
]

EXTERNAL_TIMINGS = [
    (0.0, 2.0, SENTENCES[0]),
    (2.0, 5.0, SENTENCES[1]),
    (5.0, 8.0, SENTENCES[2]),
    (8.0, 10.0, SENTENCES[3]),
    (10.0, 13.0, SENTENCES[4]),
    (13.0, 15.0, SENTENCES[5]),
    (15.0, 18.15, SENTENCES[6]),
]


def font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    filename = "segoeuib.ttf" if weight == "bold" else "segoeui.ttf"
    return ImageFont.truetype(f"C:/Windows/Fonts/{filename}", size=size)


F18 = font("bold", 18)
F23 = font("regular", 23)
F25 = font("bold", 25)
F30 = font("bold", 30)
F36 = font("bold", 36)
F45 = font("bold", 45)
F54 = font("bold", 54)


def run(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(result.stderr[-5000:])


def duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return float(result.stdout.strip())


def load_pose(path: Path) -> np.ndarray:
    image = Image.open(path).convert("RGBA").resize((POSE_W, POSE_H), Image.Resampling.LANCZOS)
    return np.asarray(image, dtype=np.uint8)


POSES = [load_pose(BOTTOM_PATH), load_pose(MIDDLE_PATH), load_pose(TOP_PATH)]


def gray_for_flow(image: np.ndarray) -> np.ndarray:
    rgb = image[..., :3]
    alpha = image[..., 3:4].astype(np.float32) / 255.0
    composite = (rgb.astype(np.float32) * alpha).astype(np.uint8)
    return cv2.cvtColor(composite, cv2.COLOR_RGB2GRAY)


def flow_pair(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ga, gb = gray_for_flow(a), gray_for_flow(b)
    fwd = cv2.calcOpticalFlowFarneback(ga, gb, None, 0.5, 4, 25, 4, 7, 1.5, 0)
    back = cv2.calcOpticalFlowFarneback(gb, ga, None, 0.5, 4, 25, 4, 7, 1.5, 0)
    return fwd, back


FLOWS = [flow_pair(POSES[0], POSES[1]), flow_pair(POSES[1], POSES[2])]
GRID_X, GRID_Y = np.meshgrid(np.arange(POSE_W, dtype=np.float32), np.arange(POSE_H, dtype=np.float32))


def smoothstep(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3.0 - 2.0 * x)


def morph(a: np.ndarray, b: np.ndarray, flows: tuple[np.ndarray, np.ndarray], amount: float) -> Image.Image:
    amount = smoothstep(amount)
    fwd, back = flows
    map_ax = GRID_X - fwd[..., 0] * amount
    map_ay = GRID_Y - fwd[..., 1] * amount
    map_bx = GRID_X - back[..., 0] * (1.0 - amount)
    map_by = GRID_Y - back[..., 1] * (1.0 - amount)
    wa = cv2.remap(a, map_ax, map_ay, cv2.INTER_LINEAR, borderMode=cv2.BORDER_TRANSPARENT)
    wb = cv2.remap(b, map_bx, map_by, cv2.INTER_LINEAR, borderMode=cv2.BORDER_TRANSPARENT)
    mixed = cv2.addWeighted(wa, 1.0 - amount, wb, amount, 0.0)
    return Image.fromarray(mixed, mode="RGBA")


def pose_for_phase(phase: float) -> tuple[Image.Image, tuple[float, float], tuple[float, float], int]:
    """Return the animated pose plus precise elbow/hand anchors in source coordinates."""
    # A deliberately clean GIF-style repetition: bottom -> middle -> top ->
    # middle -> bottom.  We use distinct anatomically verified keyframes rather
    # than dissolving them, because a dissolve creates ghost hands and weights.
    anchors = [
        ((414.0, 535.0), (526.0, 778.0)),
        ((409.0, 548.0), (670.0, 546.0)),
        ((449.0, 527.0), (588.0, 298.0)),
    ]
    if phase < 0.16:
        index = 0
    elif phase < 0.36:
        index = 1
    elif phase < 0.64:
        index = 2
    elif phase < 0.84:
        index = 1
    else:
        index = 0
    return Image.fromarray(POSES[index]), anchors[index][0], anchors[index][1], index


def point_to_canvas(point: tuple[float, float]) -> tuple[int, int]:
    return (
        round(POSE_X + point[0] / 1024.0 * POSE_W),
        round(POSE_Y + point[1] / 1536.0 * POSE_H),
    )


def circle_portrait(size: int = 112) -> Image.Image:
    source = Image.open(PORTRAIT_PATH).convert("RGB")
    side = min(source.size)
    left = (source.width - side) // 2
    top = max(0, (source.height - side) // 2 - side // 14)
    crop = source.crop((left, top, left + side, top + side)).resize((size, size), Image.Resampling.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((2, 2, size - 3, size - 3), fill=255)
    result = Image.new("RGBA", (size + 12, size + 12), (0, 0, 0, 0))
    ImageDraw.Draw(result).ellipse((0, 0, size + 11, size + 11), fill=BLUE)
    result.paste(crop, (6, 6), mask)
    return result


PORTRAIT = circle_portrait()


def alpha_paste(base: Image.Image, overlay: Image.Image, xy: tuple[int, int], opacity: float = 1.0) -> None:
    layer = overlay
    if opacity < 0.999:
        layer = overlay.copy()
        layer.putalpha(layer.getchannel("A").point(lambda a: round(a * opacity)))
    base.alpha_composite(layer, xy)


def draw_background() -> Image.Image:
    image = Image.new("RGBA", (W, H), BG)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((-150, 130, 850, 1160), fill=(18, 61, 115, 74))
    glow = glow.filter(ImageFilter.GaussianBlur(145))
    image.alpha_composite(glow)
    draw = ImageDraw.Draw(image)
    for y in range(840, H, 56):
        draw.line((0, y, W, y), fill=(25, 43, 67, 85), width=1)
    for x in range(-200, W + 250, 78):
        draw.line((360, 840, x, H), fill=(25, 43, 67, 65), width=1)
    return image


def wrap_text(draw: ImageDraw.ImageDraw, text: str, y: int, font_obj: ImageFont.FreeTypeFont, fill: tuple[int, ...], max_width: int) -> int:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textbbox((0, 0), trial, font=font_obj)[2] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    for line in lines:
        draw.text((W // 2, y), line, font=font_obj, fill=fill, anchor="ma", stroke_width=2, stroke_fill=(0, 0, 0, 240))
        y += font_obj.size + 8
    return y


def render_frame(t: float, total: float, timings: list[tuple[float, float, str]]) -> Image.Image:
    image = draw_background()
    draw = ImageDraw.Draw(image)

    # Synchronize the visible pose with the sentence being spoken.  A beginner
    # should never hear "abajo" while looking at the top position.
    if t < timings[1][1]:
        phase = 0.05  # bottom
    elif t < timings[2][1]:
        phase = 0.25  # horizontal / hardest point
    elif t < timings[4][1]:
        phase = 0.50  # top
    elif t < timings[5][1]:
        phase = 0.70  # returning through the middle
    else:
        phase = 0.95  # back at the bottom
    pose, elbow_src, hand_src, stage = pose_for_phase(phase)
    alpha_paste(image, pose, (POSE_X, POSE_Y), 0.98)

    # The small presenter portrait has a restrained GIF-like breathing motion.
    bob = round(3.0 * math.sin(t * 2.1))
    alpha_paste(image, PORTRAIT, (30, 30 + bob))
    draw.rounded_rectangle((166, 38, 687, 160), radius=22, fill=(4, 9, 19, 230), outline=(55, 76, 103), width=2)
    draw.text((193, 58), "JORDI EXPLICA", font=F18, fill=BLUE)
    draw.text((193, 88), "CURL PARA PRINCIPIANTES", font=F30, fill=WHITE)
    draw.text((193, 128), "MIRA SOLO EL BRAZO", font=F23, fill=MUTED)

    labels = [
        ("1 · ABAJO", "Empieza sin balancearte", ORANGE),
        ("2 · MITAD", "Aquí es donde más cuesta", RED),
        ("3 · ARRIBA", "Aprieta y baja despacio", GREEN),
    ]
    title, subtitle, color = labels[stage]
    draw.rounded_rectangle((95, 190, 625, 306), radius=25, fill=(2, 7, 15, 235), outline=color, width=3)
    draw.text((360, 211), title, font=F45, fill=color, anchor="ma")
    draw.text((360, 267), subtitle, font=F25, fill=WHITE, anchor="ma")

    elbow = point_to_canvas(elbow_src)
    hand = point_to_canvas(hand_src)
    # Every marker follows the same anatomical anchors used for the moving frame.
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.line((elbow, hand), fill=(61, 151, 255, 72), width=11)
    pulse = 18 + round(3 * math.sin(t * 6.0))
    od.ellipse((elbow[0] - pulse, elbow[1] - pulse, elbow[0] + pulse, elbow[1] + pulse), outline=BLUE, width=6)
    od.ellipse((elbow[0] - 6, elbow[1] - 6, elbow[0] + 6, elbow[1] + 6), fill=BLUE)
    od.rounded_rectangle((36, elbow[1] - 28, 180, elbow[1] + 24), radius=16, fill=(10, 67, 137, 235))
    od.text((108, elbow[1] - 14), "CODO FIJO", font=F18, fill=WHITE, anchor="ma")
    od.line((180, elbow[1] - 2, elbow[0] - pulse, elbow[1]), fill=BLUE, width=4)
    image.alpha_composite(overlay)

    spoken = SENTENCES[-1]
    for start, end, sentence in timings:
        if start <= t < end:
            spoken = sentence
            break
    box_top = 1090
    draw.rounded_rectangle((30, box_top, 690, 1250), radius=24, fill=(0, 0, 0, 225), outline=(65, 84, 108), width=2)
    wrap_text(draw, spoken, box_top + 30, F30, WHITE, 590)

    # A concise final call to action, after the spoken explanation has ended.
    if t >= timings[-1][1]:
        shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shade)
        sd.rounded_rectangle((70, 458, 650, 806), radius=36, fill=(2, 8, 19, 238), outline=GREEN, width=4)
        sd.text((360, 552), "¿TE SIRVIÓ?", font=F30, fill=MUTED, anchor="ma")
        sd.text((360, 624), "SÍGUEME", font=F54, fill=GREEN, anchor="ma")
        sd.text((360, 688), "PARA MÁS", font=F45, fill=WHITE, anchor="ma")
        sd.text((360, 750), "técnica clara para progresar", font=F23, fill=MUTED, anchor="ma")
        image.alpha_composite(shade)
    return image.convert("RGB")


def make_voice() -> list[tuple[float, float, str]]:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    if EXTERNAL_VOICE.is_file():
        # This is a higher-quality Spanish neural render generated for this
        # project.  Preserve it unchanged instead of passing it through a
        # second TTS engine.
        shutil.copy2(EXTERNAL_VOICE, VOICE_OUTPUT)
        return EXTERNAL_TIMINGS
    pipeline = KPipeline(lang_code="e", repo_id="hexgrad/Kokoro-82M", device="cpu")
    pieces: list[Path] = []
    timings: list[tuple[float, float, str]] = []
    cursor = 0.0
    for index, sentence in enumerate(SENTENCES):
        chunks = list(pipeline(sentence, voice="em_alex", speed=0.97))
        audio_parts = []
        for chunk in chunks:
            audio = chunk.audio.cpu().numpy() if hasattr(chunk.audio, "cpu") else np.asarray(chunk.audio)
            audio_parts.append(audio)
        audio = np.concatenate(audio_parts)
        # Short silence between thoughts prevents the synthetic rushed cadence.
        silence = np.zeros(round(0.24 * 24000), dtype=np.float32)
        audio = np.concatenate((audio.astype(np.float32), silence))
        wav_path = TEMP_DIR / f"voice-{index:02d}.wav"
        sf.write(wav_path, audio, 24000)
        piece_duration = len(audio) / 24000.0
        timings.append((cursor, cursor + piece_duration, sentence))
        cursor += piece_duration
        pieces.append(wav_path)
    concat = TEMP_DIR / "voice-concat.txt"
    concat.write_text("".join(f"file '{p.as_posix()}'\n" for p in pieces), encoding="utf-8")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c:a", "pcm_s16le", str(VOICE_OUTPUT)])
    return timings


def render_visual(total: float, timings: list[tuple[float, float, str]]) -> None:
    command = [
        "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-vf", "scale=1080:1920:flags=lanczos,format=yuv420p", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-movflags", "+faststart", str(VISUAL_OUTPUT),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    assert process.stdin is not None
    for frame_index in range(math.ceil(total * FPS)):
        process.stdin.write(render_frame(frame_index / FPS, total, timings).tobytes())
    process.stdin.close()
    stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
    if process.wait():
        raise RuntimeError(stderr[-5000:])


def make_gif(total: float, timings: list[tuple[float, float, str]]) -> None:
    frames: list[Image.Image] = []
    sample_fps = 10
    for frame_index in range(math.ceil(total * sample_fps)):
        frame = render_frame(frame_index / sample_fps, total, timings).resize((540, 960), Image.Resampling.LANCZOS)
        frames.append(frame.convert("P", palette=Image.Palette.ADAPTIVE, colors=128))
    frames[0].save(GIF_OUTPUT, save_all=True, append_images=frames[1:], duration=100, loop=0, optimize=False, disposal=2)


def mux(total: float) -> None:
    fade_out = max(0.1, total - 1.3)
    run([
        "ffmpeg", "-y", "-i", str(VISUAL_OUTPUT), "-i", str(VOICE_OUTPUT), "-stream_loop", "-1", "-ss", "41", "-i", str(MUSIC_PATH),
        "-filter_complex",
        f"[1:a]volume=1.18,highpass=f=70,lowpass=f=11500,acompressor=threshold=-20dB:ratio=2.2:attack=15:release=160[voice];"
        f"[2:a]volume=0.038,afade=t=in:st=0:d=0.8,afade=t=out:st={fade_out:.2f}:d=1.2[music];"
        "[voice][music]amix=inputs=2:duration=longest:normalize=0,loudnorm=I=-14:LRA=6:TP=-1.4[a]",
        "-map", "0:v", "-map", "[a]", "-t", f"{total:.3f}", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", str(OUTPUT),
    ])


def write_caption() -> None:
    CAPTION_OUTPUT.write_text(
        "Si estás empezando, piensa solo en esto: codo quieto y antebrazo en movimiento.\n\n"
        "Sube sin balancearte, aprieta arriba y baja despacio. Una repetición limpia vale más que mover más peso sin control.\n\n"
        "Guárdalo para tu próximo día de brazos.\n\n"
        "#Bíceps #CurlDeBíceps #GymPrincipiantes #TécnicaGym #JordiFitt\n",
        encoding="utf-8",
    )


def main() -> int:
    for path in (BOTTOM_PATH, MIDDLE_PATH, TOP_PATH, PORTRAIT_PATH, MUSIC_PATH):
        if not path.is_file():
            raise FileNotFoundError(path)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    timings = make_voice()
    total = max(20.2, timings[-1][1] + 2.0)
    render_visual(total, timings)
    make_gif(total, timings)
    mux(total)
    write_caption()
    print(OUTPUT)
    print(GIF_OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
