"""Shared motion graphics and score for the trailer and the product film. Everything is drawn
here (no stock footage, no third-party music) and rendered on this machine."""

import math
import random
import subprocess
from collections.abc import Iterator
from functools import cache
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS, SR = 1920, 1080, 30, 44100
FF = imageio_ffmpeg.get_ffmpeg_exe()
FONTS = Path("C:/Windows/Fonts")
BLACK, WHITE, INK = (0, 0, 0), (255, 255, 255), (29, 29, 31)
GREY_D, GREY_L, PAPER = (134, 134, 139), (110, 110, 115), (245, 245, 247)
GOLD_A, GOLD_B = (232, 199, 132), (190, 146, 82)
REC_W, REC_H = 1600, 1000


@cache
def font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    name = {"bold": "segoeuib.ttf", "semi": "seguisb.ttf", "reg": "segoeui.ttf", "light": "segoeuil.ttf",
            "serif": "georgia.ttf", "serifb": "georgiab.ttf", "mono": "consola.ttf"}[weight]
    return ImageFont.truetype(str(FONTS / name), size)


def ease(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 4


def ease_io(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def env(t: float, start: float, dur: float, fin: float = 0.9, fout: float = 0.6) -> tuple[float, float]:
    """(alpha, rise) for a fade-up entrance at `start` and a fade-out at the end of `dur`."""
    k = ease((t - start) / fin)
    return min(k, ease((dur - t) / fout)), 18 * (1 - k)


@cache
def gold_fill() -> Image.Image:
    ramp = np.linspace(0, 1, W)[None, :, None]
    a, b = np.array(GOLD_A), np.array(GOLD_B)
    return Image.fromarray(np.broadcast_to(a + (b - a) * ramp, (H, W, 3)).astype("uint8"))


def put(im: Image.Image, s: str, f: ImageFont.FreeTypeFont, cy: float, color: tuple[int, int, int],
        alpha: float, rise: float = 0.0, gold: bool = False, cx: float = W / 2) -> None:
    if alpha <= 0.003 or not s:
        return
    box = f.getbbox(s)
    x = cx - (box[2] - box[0]) / 2 - box[0]
    y = cy - (box[3] - box[1]) / 2 - box[1] + rise
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).text((x, y), s, font=f, fill=int(255 * alpha))
    im.paste(gold_fill() if gold else Image.new("RGB", im.size, color), (0, 0), mask)


def words(im: Image.Image, s: str, f: ImageFont.FreeTypeFont, cy: float, color: tuple[int, int, int],
          t: float, start: float, dur: float, gap: float = 0.16, gold: bool = False) -> None:
    """Kinetic type: each word rises into place in turn."""
    parts = s.split(" ")
    widths = [f.getlength(p + " ") for p in parts]
    x = W / 2 - sum(widths) / 2
    for i, (p, w) in enumerate(zip(parts, widths, strict=True)):
        a, r = env(t, start + i * gap, dur, 0.7, 0.6)
        put(im, p, f, cy, color, a, r * 1.6, gold, cx=x + f.getlength(p) / 2)
        x += w


# --- backgrounds and graphics ----------------------------------------------------------------


@cache
def text_wall() -> Image.Image:
    """A tall sheet of real judgment and Constitution text, set small and grey."""
    import json
    import sqlite3

    paras: list[str] = []
    db = Path("data/helperinlaw.db")
    if db.exists():
        rows = sqlite3.connect(db).execute("SELECT text FROM paragraphs ORDER BY random() LIMIT 900")
        paras = [r[0] for r in rows]
    if not paras:
        paras = [a["text"] for a in json.loads(Path("tests/fixtures/coi_articles.json").read_text("utf-8"))] * 40
    f = font("serif", 22)
    im = Image.new("L", (W + 400, H * 4), 0)
    d = ImageDraw.Draw(im)
    y, col_w = 0, 520
    rnd = random.Random(3)
    line, x = "", 40 + rnd.randint(0, 60)
    for word in " ".join(paras).split():
        if f.getlength(line + word) > col_w:
            d.text((x, y), line, font=f, fill=rnd.randint(70, 150))
            line, y = "", y + 34
            if y > im.height - 40:
                y, x = rnd.randint(0, 30), x + col_w + 60
                if x > im.width - col_w:
                    break
        line += word + " "
    return im


def wall(t: float, speed: float = 22, strength: float = 0.28, blur: float = 1.2) -> Image.Image:
    """Endless drifting text, softly out of focus, fading at the edges."""
    sheet = text_wall()
    y = int(t * speed) % (sheet.height - H)
    x = int(120 + 60 * math.sin(t * 0.15))
    crop = sheet.crop((x, y, x + W, y + H)).filter(ImageFilter.GaussianBlur(blur))
    vign = vignette()
    arr = np.asarray(crop, dtype=np.float32) * strength * vign
    return Image.fromarray(np.dstack([arr] * 3).clip(0, 255).astype("uint8"))


@cache
def vignette() -> np.ndarray:
    yy, xx = np.mgrid[-1:1:complex(0, H), -1:1:complex(0, W)]
    return np.clip(1.15 - (xx**2 * 0.8 + yy**2), 0, 1).astype(np.float32)


def bloom(im: Image.Image, k: float, warm: bool = True) -> Image.Image:
    """Light opening up from the centre: the turn from hopeless to hopeful."""
    if k <= 0:
        return im
    yy, xx = np.mgrid[-1:1:complex(0, H // 4), -1.78:1.78:complex(0, W // 4)]
    r = np.sqrt(xx**2 + yy**2)
    glow = np.exp(-(r / (0.25 + 1.4 * k)) ** 2) * k
    tint = np.array((255, 214, 150) if warm else (255, 255, 255), dtype=np.float32)
    layer = Image.fromarray((glow[..., None] * tint).clip(0, 255).astype("uint8")).resize((W, H), Image.BILINEAR)
    return Image.fromarray(np.minimum(255, np.asarray(im, np.int16) + np.asarray(layer, np.int16)).astype("uint8"))


PARTICLES = [(random.Random(i).random(), random.Random(i * 7).random(), random.Random(i * 13).uniform(0.4, 1.4))
             for i in range(90)]


def motes(im: Image.Image, t: float, k: float) -> None:
    """Small warm lights drifting upward."""
    if k <= 0:
        return
    d = ImageDraw.Draw(im, "RGBA")
    for px, py, sp in PARTICLES:
        y = (py * H - t * 40 * sp) % H
        x = px * W + 18 * math.sin(t * sp + px * 9)
        r = 1.5 + 2.2 * sp
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 220, 160, int(150 * k * (0.4 + 0.6 * sp))))


SCALES = [  # scales of justice as strokes, in a 120x110 box (drawn in order)
    [(60, 10), (60, 92)], [(36, 98), (84, 98)], [(14, 28), (106, 28)],
    [(22, 28), (8, 60), (36, 60), (22, 28)], [(98, 28), (84, 60), (112, 60), (98, 28)],
]


def scales(im: Image.Image, cx: float, cy: float, size: float, progress: float, alpha: float = 1.0) -> None:
    """Draw the scales stroke by stroke (progress 0..1) in gold, with a soft glow."""
    if progress <= 0 or alpha <= 0:
        return
    s = size / 120
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    total = len(SCALES)
    for i, stroke in enumerate(SCALES):
        p = min(1.0, max(0.0, progress * total - i))
        if p <= 0:
            break
        pts = [(cx + (x - 60) * s, cy + (y - 55) * s) for x, y in stroke]
        seglens = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
        todo, out = sum(seglens) * p, [pts[0]]
        for (a, b), L in zip(zip(pts, pts[1:]), seglens):
            if todo <= 0:
                break
            f = min(1.0, todo / L)
            out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
            todo -= L
        d.line(out, fill=(*GOLD_A, int(255 * alpha)), width=max(2, int(5 * s)), joint="curve")
    if progress >= 0.95:
        r = 7 * s
        d.ellipse((cx - r, cy - 27 * s - r, cx + r, cy - 27 * s + r), fill=(*GOLD_B, int(255 * alpha)))
    glow = layer.filter(ImageFilter.GaussianBlur(10))
    im.paste(glow, (0, 0), glow)
    im.paste(layer, (0, 0), layer)


def day_counter(im: Image.Image, t: float, start: float, dur: float, days: int = 5) -> None:
    """'Day 1, Day 2...' flipping by, with a thin progress line that never completes."""
    a, _ = env(t, start, dur, 0.5, 0.6)
    lt = max(0.0, t - start)
    n = min(days, 1 + int(lt / ((dur - start) / days)))
    frac = (lt / ((dur - start) / days)) % 1
    put(im, f"Day {n}", font("light", 120), H / 2 - 40, (200, 200, 205), a * (1 - 0.6 * ease_io(frac)))
    d = ImageDraw.Draw(im)
    w = 520
    x0 = W / 2 - w / 2
    d.line((x0, H / 2 + 70, x0 + w, H / 2 + 70), fill=(50, 50, 55), width=2)
    d.line((x0, H / 2 + 70, x0 + w * min(0.92, lt / (dur - start) * 0.92), H / 2 + 70),
           fill=(int(120 * a), int(120 * a), int(125 * a)), width=2)


def icon(im: Image.Image, kind: str, cx: float, cy: float, size: float, progress: float) -> None:
    """Line icons that draw themselves: check (verified), quote (cited), clock (minutes)."""
    d = ImageDraw.Draw(im)
    p = ease(progress)
    col, w = GOLD_A, max(3, int(size / 14))
    if kind == "check":
        pts = [(cx - size * 0.38, cy), (cx - size * 0.1, cy + size * 0.28), (cx + size * 0.42, cy - size * 0.3)]
        d.ellipse((cx - size / 2, cy - size / 2, cx + size / 2, cy + size / 2), outline=(60, 60, 64), width=2)
        d.arc((cx - size / 2, cy - size / 2, cx + size / 2, cy + size / 2), -90, -90 + 360 * p, fill=col, width=w)
        if p > 0.5:
            q = (p - 0.5) * 2
            mid = (pts[0][0] + (pts[1][0] - pts[0][0]) * min(1, q * 2), pts[0][1] + (pts[1][1] - pts[0][1]) * min(1, q * 2))
            line = [pts[0], mid] if q < 0.5 else [pts[0], pts[1], (pts[1][0] + (pts[2][0] - pts[1][0]) * (q - 0.5) * 2,
                                                                     pts[1][1] + (pts[2][1] - pts[1][1]) * (q - 0.5) * 2)]
            d.line(line, fill=col, width=w, joint="curve")
    elif kind == "quote":
        for dx in (-0.2, 0.18):
            x = cx + dx * size
            d.arc((x - size * 0.16, cy - size * 0.2, x + size * 0.16, cy + size * 0.12), 90, 90 + 300 * p, fill=col, width=w)
        d.line((cx - size * 0.42, cy + size * 0.36, cx - size * 0.42 + size * 0.84 * p, cy + size * 0.36), fill=col, width=2)
    elif kind == "clock":
        d.ellipse((cx - size / 2, cy - size / 2, cx + size / 2, cy + size / 2), outline=col, width=w)
        ang = -math.pi / 2 + p * 2 * math.pi * 2.75  # the hand races round
        d.line((cx, cy, cx + math.cos(ang) * size * 0.36, cy + math.sin(ang) * size * 0.36), fill=col, width=w)
        d.line((cx, cy, cx, cy - size * 0.22), fill=col, width=w)


# --- the real app, framed and zoomed -------------------------------------------------------------

WIN_W, WIN_H, BAR = 1520, 950, 40


@cache
def window_assets(dark: bool) -> tuple[Image.Image, Image.Image, Image.Image]:
    m = 90
    shadow = Image.new("RGBA", (WIN_W + 2 * m, WIN_H + BAR + 2 * m), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((m, m + 28, m + WIN_W, m + WIN_H + BAR + 28), 24,
                                             fill=(0, 0, 0, 120 if dark else 55))
    shadow = shadow.filter(ImageFilter.GaussianBlur(42))
    bar = Image.new("RGB", (WIN_W, BAR), (242, 242, 245))
    d = ImageDraw.Draw(bar)
    for i in range(3):
        d.ellipse((20 + i * 22, 14, 31 + i * 22, 25), fill=(208, 208, 212))
    mask = Image.new("L", (WIN_W, WIN_H + BAR), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, WIN_W - 1, WIN_H + BAR - 1), 24, fill=255)
    return shadow, bar, mask


def focus_rect(box: list[int] | None, k: float) -> tuple[float, float, float, float]:
    """Crop of the 1600x1000 recording, easing from the full frame to the box of interest."""
    full = (0.0, 0.0, float(REC_W), float(REC_H))
    if not box or k <= 0:
        return full
    x, y, w, h = box
    pad = 70
    tw = max(860.0, w + 2 * pad)
    th = tw * REC_H / REC_W
    if h + 2 * pad > th:
        th = h + 2 * pad
        tw = th * REC_W / REC_H
    cx, cy = x + w / 2, y + h / 2
    tx = min(max(0.0, cx - tw / 2), REC_W - tw)
    ty = min(max(0.0, cy - th / 2), REC_H - th)
    return tuple(a + (b - a) * k for a, b in zip(full, (tx, ty, tx + tw, ty + th)))  # type: ignore[return-value]


def framed(frame: Image.Image, t: float, dur: float, caption: str, box: list[int] | None,
           zoom_k: float, glow_k: float, dark: bool = False) -> Image.Image:
    """The app in a clean window on a soft backdrop, pushing in to the part that matters, with a
    gold highlight drawing around it."""
    bg = Image.new("RGB", (W, H), (12, 12, 14) if dark else PAPER)
    shadow, bar, mask = window_assets(dark)
    rect = focus_rect(box, zoom_k)
    view = frame.crop(tuple(int(v) for v in rect)).resize((WIN_W, WIN_H), Image.BILINEAR)
    if box and glow_k > 0:
        sx, sy = WIN_W / (rect[2] - rect[0]), WIN_H / (rect[3] - rect[1])
        x, y, w, h = box
        bx0, by0 = (x - rect[0]) * sx - 10, (y - rect[1]) * sy - 10
        bx1, by1 = bx0 + w * sx + 20, by0 + h * sy + 20
        hl = Image.new("RGBA", view.size, (0, 0, 0, 0))
        hd = ImageDraw.Draw(hl)
        pulse = 0.75 + 0.25 * math.sin(t * 3.2)
        hd.rounded_rectangle((bx0, by0, bx1, by1), 18, outline=(*GOLD_B, int(235 * glow_k * pulse)), width=4)
        g = hl.filter(ImageFilter.GaussianBlur(8))
        view.paste(g, (0, 0), g)
        view.paste(hl, (0, 0), hl)
    win = Image.new("RGB", (WIN_W, WIN_H + BAR), WHITE)
    win.paste(bar, (0, 0))
    win.paste(view, (0, BAR))
    s = 0.95 + 0.025 * ease_io(t / dur)  # slow push-in of the whole window
    ww, wh = int(WIN_W * s), int((WIN_H + BAR) * s)
    win_z, mask_z = win.resize((ww, wh), Image.BILINEAR), mask.resize((ww, wh), Image.BILINEAR)
    x, y = (W - ww) // 2, 120 + (H - 120 - wh) // 2
    sh = shadow.resize((int(shadow.width * s), int(shadow.height * s)))
    bg.paste(sh, (x - int(90 * s), y - int(90 * s)), sh)
    bg.paste(win_z, (x, y), mask_z)
    a, r = env(t, 0.1, dur, 0.7, 0.5)
    put(bg, caption, font("semi", 42), 62, WHITE if dark else INK, a, r * 0.5)
    return bg


def screen_frames(rec: Path, start: float, end: float, n_out: int) -> Iterator[tuple[Image.Image, float]]:
    """n_out frames spanning the recording from start to end, re-timed to fit; yields (frame,
    source time) so zooms can follow what the recording is showing."""
    span = max(0.1, end - start)
    proc = subprocess.Popen(
        [FF, "-loglevel", "error", "-ss", f"{start:.2f}", "-t", f"{span:.2f}", "-i", str(rec),
         "-vf", f"fps={FPS},scale={REC_W}:{REC_H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        stdout=subprocess.PIPE,
    )
    assert proc.stdout
    size = REC_W * REC_H * 3
    n_src = max(1, int(span * FPS))
    last, idx = None, -1
    for k in range(n_out):
        want = min(n_src - 1, int(k * n_src / n_out))
        while idx < want:
            buf = proc.stdout.read(size)
            if len(buf) < size:
                break
            last = Image.frombytes("RGB", (REC_W, REC_H), buf)
            idx += 1
        yield (last if last is not None else Image.new("RGB", (REC_W, REC_H), WHITE)), start + want / FPS
    proc.stdout.close()
    proc.wait()


# --- music: public-domain recordings, hopeless then hopeful ---------------------------------------

MUSIC_DIR = Path("data/music")
# Both: Edvard Grieg, Peer Gynt Suite No. 1, Musopen Symphony. Wikimedia Commons, Public domain.
SORROW = ("death_of_aase.flac", "https://upload.wikimedia.org/wikipedia/commons/3/35/"
          "Grieg_-_Peer_Gynt_Suite_No._1%2C_Op._46_-_II._The_Death_of_Aase_%28Musopen_Symphony%29.flac")
DAWN = ("morning_mood.flac", "https://upload.wikimedia.org/wikipedia/commons/c/c2/"
        "Grieg_-_Peer_Gynt_Suite_No._1%2C_Op._46_-_I._Morning_Mood_%28Musopen_Symphony%29.flac")


def load(track: tuple[str, str]) -> np.ndarray:
    """Stereo float samples at SR, downloading the public-domain file once."""
    import urllib.request

    path = MUSIC_DIR / track[0]
    if not path.exists():
        MUSIC_DIR.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(track[1], headers={"User-Agent": "helper-in-law-film/1.0"})
        path.write_bytes(urllib.request.urlopen(req, timeout=300).read())
    raw = subprocess.run([FF, "-loglevel", "error", "-i", str(path), "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype="<f4").reshape(-1, 2).astype(np.float64)


def rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(x**2)) + 1e-9)


def music_bed(total: float, turn: float, dawn_from: float, xfade: float = 1.8) -> np.ndarray:
    """Grief until `turn` (The Death of Aase, from its opening), then dawn (Morning Mood from
    `dawn_from` s), crossfaded across the turn. The grief sits ~4 dB under the dawn."""
    n, n_turn, nx = int(total * SR), int(turn * SR), int(xfade * SR)
    sorrow = load(SORROW)[: n_turn + nx]
    dawn = load(DAWN)[int(dawn_from * SR):][: n - n_turn + nx]
    dawn = np.pad(dawn, ((0, max(0, n - n_turn + nx - len(dawn))), (0, 0)))
    sorrow *= (0.7 * rms(dawn[: 10 * SR])) / rms(sorrow)  # just under the first light, not the climax
    out = np.zeros((n + nx, 2))
    out[: len(sorrow)] += sorrow * np.clip((len(sorrow) - np.arange(len(sorrow)))[:, None] / nx, 0, 1)
    fade_in = np.clip(np.arange(len(dawn))[:, None] / nx, 0, 1)
    out[n_turn - nx // 2 : n_turn - nx // 2 + len(dawn)] += (dawn * fade_in)[: n + nx - (n_turn - nx // 2)]
    return out[:n]


def compress(sig: np.ndarray, threshold_db: float = -24.0, ratio: float = 3.0) -> np.ndarray:
    """Gentle broadcast-style compression so quiet passages stay audible next to the climax."""
    mono = np.abs(sig).mean(axis=1) if sig.ndim == 2 else np.abs(sig)
    win = int(0.08 * SR)
    level = np.sqrt(np.convolve(mono**2, np.ones(win) / win, "same")) + 1e-9
    thr = 10 ** (threshold_db / 20) * mono.max()
    gain = np.where(level > thr, (thr / level) ** (1 - 1 / ratio), 1.0)
    gain = np.convolve(gain, np.ones(win) / win, "same")  # smooth: no pumping clicks
    return sig * (gain[:, None] if sig.ndim == 2 else gain)


def finish(sig: np.ndarray, peak: float = 0.89) -> np.ndarray:
    """Compress, fade in/out and normalise. No saturation: these are real recordings."""
    sig = compress(sig)
    n = len(sig)
    fade = np.clip(np.arange(n) / (0.5 * SR), 0, 1) * np.clip((n - np.arange(n)) / (3.0 * SR), 0, 1)
    sig = sig * (fade[:, None] if sig.ndim == 2 else fade)
    return sig / max(1e-6, np.abs(sig).max()) * peak


def write_wav(path: Path, sig: np.ndarray) -> None:
    import wave

    stereo = sig if sig.ndim == 2 else np.stack([sig, sig], axis=1)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes((np.clip(stereo, -1, 1) * 32767).astype("<i2").tobytes())


def encoder(path: Path) -> subprocess.Popen:  # type: ignore[type-arg]
    return subprocess.Popen(
        [FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
         "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(path)],
        stdin=subprocess.PIPE,
    )


def mux(video: Path, wav: Path, out: Path) -> None:
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(video), "-i", str(wav), "-c:v", "copy", "-c:a",
                    "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", str(out)], check=True)
