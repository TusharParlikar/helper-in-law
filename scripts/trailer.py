"""Render the product film (docs/trailer.mp4): minimal launch-keynote style. Frames with
Pillow, a soft synthesized score with numpy, encoded with imageio-ffmpeg's bundled ffmpeg.

uv run --no-project --with pillow --with numpy --with imageio-ffmpeg python scripts/trailer.py
"""

import subprocess
import wave
from collections.abc import Callable
from functools import cache
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1920, 1080, 30
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "trailer.mp4"
FONTS = Path("C:/Windows/Fonts")

BLACK, WHITE = (0, 0, 0), (255, 255, 255)
INK = (29, 29, 31)  # near-black text on white
GREY_D = (134, 134, 139)  # secondary text on black
GREY_L = (110, 110, 115)  # secondary text on white
GRAD = ((255, 196, 87), (255, 122, 69))  # warm gold -> amber, used only on key words
GREEN = (48, 179, 92)


@cache
def font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    name = {
        "bold": "segoeuib.ttf",
        "semi": "seguisb.ttf",
        "reg": "segoeui.ttf",
        "light": "segoeuil.ttf",
        "mono": "consola.ttf",
    }[weight]
    return ImageFont.truetype(str(FONTS / name), size)


def ease(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 4


def env(t: float, start: float, dur: float, fade_in: float = 0.9, fade_out: float = 0.6) -> float:
    """Opacity of an element shown from `start` until the scene ends at `dur`."""
    return min(ease((t - start) / fade_in), ease((dur - t) / fade_out))


def canvas(bg: tuple[int, int, int]) -> Image.Image:
    return Image.new("RGB", (W, H), bg)


def put(
    im: Image.Image,
    s: str,
    f: ImageFont.FreeTypeFont,
    cy: float,
    color: tuple[int, int, int],
    alpha: float,
    rise: float = 0.0,
    gradient: bool = False,
    cx: float = W / 2,
) -> None:
    """Centered text at vertical center `cy`, faded by `alpha`, lifted by `rise` px."""
    if alpha <= 0.002:
        return
    box = f.getbbox(s)
    tw, th = box[2] - box[0], box[3] - box[1]
    x, y = cx - tw / 2 - box[0], cy - th / 2 - box[1] + rise
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).text((x, y), s, font=f, fill=int(255 * alpha))
    if gradient:
        ramp = np.linspace(0, 1, W)[None, :, None]
        a, b = np.array(GRAD[0]), np.array(GRAD[1])
        fill = Image.fromarray(np.broadcast_to(a + (b - a) * ramp, (H, W, 3)).astype("uint8"))
    else:
        fill = Image.new("RGB", im.size, color)
    im.paste(fill, (0, 0), mask)


def reveal(t: float, start: float) -> tuple[float, float]:
    """(alpha, rise) for the standard fade-up entrance."""
    k = ease((t - start) / 0.9)
    return k, 18 * (1 - k)


@cache
def card(w: int, h: int, radius: int, fill: tuple[int, int, int], shadow: bool) -> Image.Image:
    """Rounded card with a soft drop shadow, as RGBA with margin for the shadow."""
    m = 80
    layer = Image.new("RGBA", (w + 2 * m, h + 2 * m), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle(
            (m, m + 24, m + w, m + h + 24), radius, fill=(0, 0, 0, 46)
        )
        layer = Image.alpha_composite(layer, sh.filter(ImageFilter.GaussianBlur(36)))
    ImageDraw.Draw(layer).rounded_rectangle((m, m, m + w, m + h), radius, fill=(*fill, 255))
    return layer


def place(im: Image.Image, layer: Image.Image, cx: float, cy: float, alpha: float) -> None:
    if alpha <= 0.002:
        return
    lay = layer.copy()
    lay.putalpha(lay.getchannel("A").point(lambda v: int(v * alpha)))
    im.paste(lay, (int(cx - lay.width / 2), int(cy - lay.height / 2)), lay)


# --- scenes: each takes local time t and returns a frame -----------------------------


def s_problem(t: float) -> Image.Image:  # 5.0s
    im = canvas(BLACK)
    a, r = reveal(t, 0.4)
    put(im, "Legal research", font("semi", 112), 470, WHITE, a * env(t, 0, 5.0), r)
    a, r = reveal(t, 1.6)
    put(im, "has a trust problem.", font("semi", 112), 610, GREY_D, a * env(t, 0, 5.0), r)
    return im


def s_fabricate(t: float) -> Image.Image:  # 5.0s
    im = canvas(BLACK)
    a, r = reveal(t, 0.3)
    put(im, "AI that sounds certain.", font("semi", 96), 450, WHITE, a * env(t, 0, 5.0), r)
    a, r = reveal(t, 1.7)
    put(im, "Citing cases that don't exist.", font("semi", 96), 590, GREY_D, a * env(t, 0, 5.0), r)
    return im


def s_title(t: float) -> Image.Image:  # 5.5s
    im = canvas(BLACK)
    a, r = reveal(t, 0.5)
    k = env(t, 0, 5.5, 1.2, 0.8)
    put(im, "Helper in Law", font("bold", int(176 + 8 * ease(t / 5.5))), 480, WHITE, a * k, r)
    a, r = reveal(t, 1.8)
    put(im, "Every claim. Verified.", font("semi", 72), 640, WHITE, a * k, r, gradient=True)
    return im


def s_ask(t: float) -> Image.Image:  # 5.0s
    im = canvas(WHITE)
    k = env(t, 0, 5.0)
    a, r = reveal(t, 0.3)
    put(im, "Ask a research question.", font("semi", 84), 330, INK, a * k, r)
    a, _ = reveal(t, 1.1)
    place(im, card(1240, 128, 64, (245, 245, 247), False), W / 2, 560, a * k)
    q = "What are the grounds for refusing bail under Section 439 CrPC?"
    shown = q[: int(max(0.0, t - 1.6) * 34)]
    f = font("reg", 40)
    box = f.getbbox(q)
    x0 = W / 2 - (box[2] - box[0]) / 2
    if shown and a * k > 0.01:
        d = ImageDraw.Draw(im)
        d.text((x0, 560 - 26), shown, font=f, fill=INK)
        if int(t * 2.4) % 2 == 0 or len(shown) < len(q):
            cx = x0 + d.textlength(shown, font=f) + 6
            d.line((cx, 536, cx, 584), fill=(0, 113, 227), width=3)
    return im


def s_answer(t: float) -> Image.Image:  # 7.0s
    im = canvas(WHITE)
    k = env(t, 0, 7.0)
    a, r = reveal(t, 0.2)
    place(im, card(1320, 520, 36, WHITE, True), W / 2, 470 + r, a * k)
    left = W / 2 - 600
    d = ImageDraw.Draw(im)
    body = [
        "Bail may be refused where there is a reasonable apprehension",
        "that the accused will tamper with the evidence or influence",
        "the witnesses.",
    ]
    for i, line in enumerate(body):
        al, rr = reveal(t, 0.6 + i * 0.15)
        if al * k > 0.01:
            put(
                im,
                line,
                font("reg", 44),
                330 + i * 64 + rr,
                INK,
                al * k,
                cx=left + font("reg", 44).getlength(line) / 2,
            )
    al, rr = reveal(t, 1.5)
    if al * k > 0.01:
        cite = "Arjun Mehta v. State of Rajasthan  ·  para 7"
        f = font("semi", 32)
        w = f.getlength(cite) + 56
        chip = card(int(w), 60, 30, (245, 245, 247), False)
        place(im, chip, left + w / 2, 560 + rr, al * k)
        put(im, cite, f, 560 + rr, INK, al * k, cx=left + w / 2)
    al, rr = reveal(t, 2.4)
    if al * k > 0.01:
        f = font("semi", 32)
        label = "Verified against the source"
        w = f.getlength(label) + 100
        place(im, card(int(w), 60, 30, (232, 247, 237), False), left + w / 2, 650 + rr, al * k)
        d.ellipse((left + 26, 650 - 12 + rr, left + 50, 650 + 12 + rr), fill=GREEN)
        put(im, label, f, 650 + rr, GREEN, al * k, cx=left + 64 + f.getlength(label) / 2)
    a, r = reveal(t, 3.4)
    put(
        im,
        "Every sentence is checked against the paragraph it cites.",
        font("reg", 40),
        880,
        GREY_L,
        a * k,
        r,
    )
    return im


def s_abstain(t: float) -> Image.Image:  # 5.5s
    im = canvas(WHITE)
    k = env(t, 0, 5.5)
    a, r = reveal(t, 0.3)
    put(im, "And when the judgments don't say it,", font("semi", 72), 380, INK, a * k, r)
    a, r = reveal(t, 1.5)
    put(im, "neither does Helper in Law.", font("semi", 72), 490, INK, a * k, r, gradient=True)
    a, r = reveal(t, 2.6)
    place(im, card(1000, 110, 55, (245, 245, 247), False), W / 2, 700 + r, a * k)
    put(im, "Not found in the indexed judgments.", font("reg", 40), 700 + r, GREY_L, a * k)
    return im


PILLARS = [
    ("Verified.", "Quotes, numbers and meaning checked before display."),
    ("Cited.", "Case, court and paragraph come from the record."),
    ("Private.", "Runs on your machine with Ollama."),
]


def s_pillars(t: float) -> Image.Image:  # 7.5s (2.5s each)
    im = canvas(BLACK)
    i = min(2, int(t // 2.5))
    lt = t - i * 2.5
    k = env(lt, 0, 2.5, 0.6, 0.45)
    a, r = reveal(lt, 0.0)
    head, sub = PILLARS[i]
    put(im, head, font("bold", 150), 470, WHITE, a * k, r, gradient=(i == 0))
    a, r = reveal(lt, 0.45)
    put(im, sub, font("reg", 44), 630, GREY_D, a * k, r)
    return im


STATS = [("10 of 10", "fault types caught"), ("0", "unsupported claims shown"), ("100%", "local")]


def s_stats(t: float) -> Image.Image:  # 5.5s
    im = canvas(BLACK)
    k = env(t, 0, 5.5)
    col = W / 3
    for i, (big, small) in enumerate(STATS):
        a, r = reveal(t, 0.3 + i * 0.35)
        cx = col / 2 + i * col
        put(im, big, font("bold", 120), 470, WHITE, a * k, r, cx=cx)
        put(im, small, font("reg", 40), 590, GREY_D, a * k, r, cx=cx)
    a, r = reveal(t, 1.9)
    put(
        im,
        "REST API   ·   MCP server for AI agents   ·   Web app",
        font("reg", 36),
        800,
        GREY_D,
        a * k,
        r,
    )
    return im


def s_end(t: float) -> Image.Image:  # 6.0s
    im = canvas(BLACK)
    k = env(t, 0, 6.0, 1.0, 1.2)
    a, r = reveal(t, 0.3)
    put(im, "Helper in Law", font("bold", 150), 450, WHITE, a * k, r)
    a, r = reveal(t, 1.1)
    put(im, "Research over Indian court judgments.", font("reg", 48), 580, GREY_D, a * k, r)
    a, _ = reveal(t, 2.0)
    put(im, "github.com/TusharParlikar/helper-in-law", font("reg", 34), 880, GREY_D, a * k * 0.9)
    put(
        im,
        "A research aid, not legal advice. Demo uses a fictional sample corpus.",
        font("reg", 26),
        940,
        (90, 90, 95),
        a * k,
    )
    return im


SCENES: list[tuple[float, Callable[[float], Image.Image]]] = [
    (5.0, s_problem),
    (5.0, s_fabricate),
    (5.5, s_title),
    (5.0, s_ask),
    (7.0, s_answer),
    (5.5, s_abstain),
    (7.5, s_pillars),
    (5.5, s_stats),
    (6.0, s_end),
]


def score(total: float, marks: list[float], path: Path) -> None:
    """Soft pad (A minor add9), a warm swell into the title, a quiet pulse in the product
    section, gentle chimes on scene changes."""
    sr = 44100
    t = np.arange(int(total * sr)) / sr
    out = np.zeros_like(t)
    chords = [
        (220.0, 261.63, 329.63, 493.88),
        (174.61, 220.0, 261.63, 392.0),
        (196.0, 246.94, 293.66, 440.0),
        (220.0, 277.18, 329.63, 493.88),
    ]
    seg = total / len(chords)
    for i, chord in enumerate(chords):
        m = (t >= i * seg - 1.5) & (t < (i + 1) * seg + 1.5)
        local = t[m] - i * seg
        shape = np.clip((local + 1.5) / 3, 0, 1) * np.clip(((seg + 1.5) - local) / 3, 0, 1)
        for f in chord:
            out[m] += (
                (np.sin(2 * np.pi * f * t[m]) + 0.3 * np.sin(2 * np.pi * f * 2.0 * t[m]))
                * shape
                * 0.05
            )
    bass_on = (t > 15.5) & (t < total - 6)
    beat = (t % 0.75) < 0.12
    out += np.sin(2 * np.pi * 55 * t) * np.exp(-(t % 0.75) * 18) * beat * bass_on * 0.35
    for mk in marks:
        i = int(mk * sr)
        n = min(int(2.5 * sr), len(t) - i)
        tt = np.arange(n) / sr
        out[i : i + n] += np.sin(2 * np.pi * 1318.5 * tt) * np.exp(-tt * 3) * 0.04
    out *= np.clip(t / 2.0, 0, 1) * np.clip((total - t) / 3.0, 0, 1)
    out = np.tanh(out * 1.6) * 0.7
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((out * 32767).astype("<i2").tobytes())


def main() -> None:
    silent, wav = OUT.with_suffix(".silent.mp4"), OUT.with_suffix(".wav")
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    enc = subprocess.Popen(
        [
            ff,
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{W}x{H}",
            "-r",
            str(FPS),
            "-i",
            "-",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "18",
            "-preset",
            "slow",
            "-movflags",
            "+faststart",
            str(silent),
        ],
        stdin=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    assert enc.stdin
    marks, clock = [], 0.0
    for dur, render in SCENES:
        marks.append(clock)
        for i in range(int(dur * FPS)):
            enc.stdin.write(render(i / FPS).tobytes())
        clock += dur
    enc.stdin.close()
    enc.wait()
    score(clock, marks[1:], wav)
    subprocess.run(
        [
            ff,
            "-y",
            "-i",
            str(silent),
            "-i",
            str(wav),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(OUT),
        ],
        check=True,
        stderr=subprocess.DEVNULL,
    )
    silent.unlink()
    wav.unlink()
    print(f"wrote {OUT} ({clock:.1f}s, {OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
