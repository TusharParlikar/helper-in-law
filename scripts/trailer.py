"""Render the trailer (docs/trailer.mp4): the problem in the dark (0-15 s), the turn to light at
15 s, then what the product does, shown in the real app. No voiceover; music and type carry it.

uv run --no-project --with pillow --with numpy --with imageio-ffmpeg python scripts/trailer.py REC_DIR
REC_DIR holds screen.webm + marks.json from scripts/film/record.py.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "film"))
from motion import (  # noqa: E402
    BLACK,
    FPS,
    GREY_D,
    INK,
    WHITE,
    H,
    W,
    bloom,
    day_counter,
    ease,
    encoder,
    env,
    finish,
    font,
    framed,
    icon,
    motes,
    music_bed,
    mux,
    put,
    scales,
    screen_frames,
    wall,
    words,
    write_wav,
)
from PIL import Image  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "trailer.mp4"
TURN = 15.0  # the moment the light comes in, in picture and in music


def s_wall(t: float, dur: float) -> Image.Image:
    im = wall(t, speed=26, strength=0.30)
    words(im, "Thousands of judgments.", font("serif", 96), H / 2 - 85, WHITE, t, 0.6, dur)
    words(im, "Millions of words.", font("serif", 96), H / 2 + 85, GREY_D, t, 2.4, dur)
    return im


def s_client(t: float, dur: float) -> Image.Image:
    im = wall(t + 5, speed=12, strength=0.14, blur=2.4)
    words(im, "One client.", font("serif", 100), H / 2 - 85, WHITE, t, 0.3, dur)
    words(im, "One question.", font("serif", 100), H / 2 + 85, GREY_D, t, 1.4, dur)
    return im


def s_days(t: float, dur: float) -> Image.Image:
    im = Image.new("RGB", (W, H), BLACK)
    put(im, "Searching", font("reg", 34), H / 2 - 190, (95, 95, 100), env(t, 0.2, dur, 0.6, 0.5)[0])
    if t < dur - 1.9:
        day_counter(im, t, 0.2, dur - 1.9)
    else:
        a, r = env(t, dur - 1.8, dur, 0.5, 0.5)
        put(im, "Still no answer.", font("serif", 92), H / 2, (190, 190, 195), a, r)
    return im


def s_title(t: float, dur: float) -> Image.Image:
    im = bloom(Image.new("RGB", (W, H), BLACK), 0.55 * ease(t / 2.2))
    motes(im, t, ease(t / 2.5) * env(t, 0, dur, 0.1, 0.7)[0])
    scales(im, W / 2, H / 2 - 150, 170, ease(t / 1.8), env(t, 0, dur, 0.1, 0.6)[0])
    a, r = env(t, 1.4, dur, 0.9, 0.6)
    put(im, "Helper in Law", font("serifb", 140), H / 2 + 70, WHITE, a, r)
    a, r = env(t, 2.3, dur, 0.9, 0.6)
    put(
        im,
        "Describe the situation. Get the law.",
        font("reg", 46),
        H / 2 + 190,
        WHITE,
        a,
        r,
        gold=True,
    )
    return im


UI = [  # (caption, start mark, end mark, zoom box mark, zoom starts how long before the segment ends)
    ("Describe your client's situation.", "home", "typed", "typed", 7.0),
    ("Get the Article that governs it.", "typed", "provisions", "provisions", 2.4),
    ("Backed by Supreme Court judgments.", "analysis", "judgments", "judgments", 2.6),
]


def s_pillar(t: float, dur: float, kind: str, head: str, sub: str) -> Image.Image:
    im = Image.new("RGB", (W, H), WHITE)
    icon(im, kind, W / 2, H / 2 - 170, 120, t / 1.0)
    a, r = env(t, 0.25, dur, 0.55, 0.4)
    put(im, head, font("serifb", 130), H / 2 + 30, INK, a, r)
    a, r = env(t, 0.55, dur, 0.6, 0.4)
    put(im, sub, font("reg", 42), H / 2 + 160, (90, 90, 95), a, r)
    return im


def s_end(t: float, dur: float) -> Image.Image:
    im = bloom(Image.new("RGB", (W, H), BLACK), 0.18 * env(t, 0, dur, 1.5, 1.5)[0])
    scales(im, W / 2, H / 2 - 190, 110, ease(t / 1.4), env(t, 0, dur, 0.2, 1.2)[0])
    a, r = env(t, 0.6, dur, 1.0, 1.2)
    put(im, "Helper in Law", font("serifb", 130), H / 2 - 10, WHITE, a, r)
    a, r = env(t, 1.4, dur, 1.0, 1.2)
    put(im, "Every claim. Verified.", font("reg", 52), H / 2 + 110, WHITE, a, r, gold=True)
    a, _ = env(t, 2.2, dur, 1.0, 1.2)
    put(im, "A research aid, not legal advice.", font("reg", 26), H - 120, (120, 120, 125), a)
    put(
        im,
        "Judgment text: Supreme Court of India, via the Indian Supreme Court Judgments dataset (CC BY 4.0).",
        font("reg", 20),
        H - 80,
        (85, 85, 90),
        a,
    )
    return im


UI_DUR, PILLAR_DUR, END_DUR = 5.6, 2.2, 5.6
OUTRO = TURN + 4.6 + len(UI) * UI_DUR + 3 * PILLAR_DUR
TOTAL = OUTRO + END_DUR


def audio(silent: Path, work: Path) -> None:
    wav = work / "trailer.wav"
    write_wav(wav, finish(music_bed(TOTAL, TURN)))
    mux(silent, wav, OUT)


def main(rec: Path, audio_only: bool = False) -> None:
    marks = json.loads((rec / "marks.json").read_text())
    work = OUT.parent / "film_work"
    work.mkdir(exist_ok=True)
    silent = work / "trailer.silent.mp4"
    if audio_only and silent.exists():
        audio(silent, work)
        print(f"re-scored {OUT}")
        return
    enc = encoder(silent)
    assert enc.stdin
    clock = 0.0

    def card(render, dur: float) -> None:  # type: ignore[no-untyped-def]
        nonlocal clock
        for k in range(int(round(dur * FPS))):
            enc.stdin.write(render(k / FPS, dur).tobytes())  # type: ignore[union-attr]
        clock += dur

    card(s_wall, 5.0)
    card(s_client, 4.5)
    card(s_days, TURN - 9.5)
    card(s_title, 4.6)
    for caption, a, b, focus, lead in UI:
        dur = UI_DUR
        t0, t1 = marks[a]["t"], marks[b]["t"]
        box = marks[focus]["box"]
        for k, (fr, src_t) in enumerate(screen_frames(rec / "screen.webm", t0, t1, int(dur * FPS))):
            zk = ease((src_t - (t1 - lead)) / 1.1)
            gk = ease((src_t - (t1 - lead) - 1.0) / 0.6)
            enc.stdin.write(framed(fr, k / FPS, dur, caption, box, zk, gk).tobytes())
        clock += dur
    for kind, head, sub in [
        ("check", "Verified.", "Every statement checked against its source."),
        ("quote", "Cited.", "Every quote, to the exact paragraph."),
        ("clock", "In minutes.", "Not days."),
    ]:
        card(lambda t, d, k=kind, h=head, s=sub: s_pillar(t, d, k, h, s), PILLAR_DUR)
    outro = clock
    card(s_end, END_DUR)
    enc.stdin.close()
    enc.wait()
    assert abs(clock - TOTAL) < 0.05 and abs(outro - OUTRO) < 0.05
    audio(silent, work)
    print(f"wrote {OUT} ({clock:.1f}s)")


if __name__ == "__main__":
    main(Path(sys.argv[1]), "--audio-only" in sys.argv)
