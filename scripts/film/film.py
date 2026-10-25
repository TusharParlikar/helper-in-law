"""Render the product video: the problem (0-15 s, in the dark), the turn at 15 s, then how it
works, shown in the real app with zooms and highlights, narrated by a local neural voice.

uv run --no-project --with pillow --with numpy --with imageio-ffmpeg --with piper-tts \
    python scripts/film/film.py REC_DIR VOICE_MODEL.onnx OUT.mp4
REC_DIR holds screen.webm + marks.json from record.py.
"""

import json
import sys
import wave
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from motion import (
    BLACK, FPS, GREY_D, H, INK, SR, W, WHITE, bloom, day_counter, encoder, ease, env, font, framed, icon,
    compress, finish, motes, music_bed, mux, put, scales, screen_frames, wall, words, write_wav,
)
from PIL import Image

TURN = 15.0


@dataclass
class Scene:
    vo: str
    render: Callable[[float, float], Image.Image] | None = None
    ui: tuple[str, str, str, float] | None = None  # (start mark, end mark, focus mark, zoom lead)
    caption: str = ""
    min_dur: float = 3.0


def s_story(t: float, d: float) -> Image.Image:
    im = wall(t, speed=10, strength=0.10, blur=3.0)
    words(im, "Every case begins with a story.", font("serif", 92), H / 2, WHITE, t, 0.4, d)
    return im


def s_pages(t: float, d: float) -> Image.Image:
    im = wall(t + 4, speed=30, strength=0.30)
    words(im, "Thousands of pages of judgments.", font("serif", 88), H / 2 - 80, WHITE, t, 0.5, d)
    words(im, "Somewhere in them, the law that decides it.", font("serif", 60), H / 2 + 70, GREY_D, t, 2.0, d)
    return im


def s_days(t: float, d: float) -> Image.Image:
    im = Image.new("RGB", (W, H), BLACK)
    split = d * 0.55
    if t < split:
        day_counter(im, t, 0.2, split)
    else:
        a, r = env(t, split, d, 0.5, 0.6)
        put(im, "Missing it can cost everything.", font("serif", 84), H / 2, (190, 190, 195), a, r)
    return im


def s_title(t: float, d: float) -> Image.Image:
    im = bloom(Image.new("RGB", (W, H), BLACK), 0.55 * ease(t / 2.2))
    motes(im, t, ease(t / 2.5) * env(t, 0, d, 0.1, 0.7)[0])
    scales(im, W / 2, H / 2 - 150, 170, ease(t / 1.8), env(t, 0, d, 0.1, 0.6)[0])
    a, r = env(t, 1.3, d, 0.9, 0.6)
    put(im, "Helper in Law", font("serifb", 140), H / 2 + 70, WHITE, a, r)
    a, r = env(t, 2.2, d, 0.9, 0.6)
    put(im, "Constitutional research, grounded in precedent.", font("reg", 44), H / 2 + 190, WHITE, a, r, gold=True)
    return im


PILLARS = [("check", "Verified.", "Every statement checked against its source."),
           ("quote", "Cited.", "Every quote, to the exact paragraph."),
           ("clock", "In minutes.", "Not days.")]


def s_pillars(t: float, d: float) -> Image.Image:
    seg = d / 3
    i = min(2, int(t // seg))
    lt = t - i * seg
    kind, head, sub = PILLARS[i]
    im = Image.new("RGB", (W, H), WHITE)
    icon(im, kind, W / 2, H / 2 - 170, 120, lt / 1.0)
    a, r = env(lt, 0.2, seg, 0.55, 0.4)
    put(im, head, font("serifb", 130), H / 2 + 30, INK, a, r)
    a, r = env(lt, 0.5, seg, 0.6, 0.4)
    put(im, sub, font("reg", 42), H / 2 + 160, (90, 90, 95), a, r)
    return im


def s_end(t: float, d: float) -> Image.Image:
    im = bloom(Image.new("RGB", (W, H), BLACK), 0.18 * env(t, 0, d, 1.5, 1.5)[0])
    scales(im, W / 2, H / 2 - 190, 110, ease(t / 1.4), env(t, 0, d, 0.2, 1.2)[0])
    a, r = env(t, 0.6, d, 1.0, 1.2)
    put(im, "Helper in Law", font("serifb", 130), H / 2 - 10, WHITE, a, r)
    a, r = env(t, 1.4, d, 1.0, 1.2)
    put(im, "Every claim. Verified.", font("reg", 52), H / 2 + 110, WHITE, a, r, gold=True)
    a, _ = env(t, 2.2, d, 1.0, 1.2)
    put(im, "A research aid, not legal advice.", font("reg", 26), H - 120, (120, 120, 125), a)
    put(im, "Judgment text: Supreme Court of India, via the Indian Supreme Court Judgments dataset (CC BY 4.0).",
        font("reg", 20), H - 80, (85, 85, 90), a)
    return im


HOPELESS = [
    Scene("Every case begins with a story.", s_story),
    Scene("And somewhere, in thousands of pages of judgments, is the law that decides it.", s_pages),
    Scene("Finding it can take days. Missing it can cost everything.", s_days),
]
HOPEFUL = [
    Scene("Introducing Helper in Law.", s_title, min_dur=4.6),
    Scene("Just describe your client's situation, in your own words.",
          ui=("home", "typed", "typed", 7.0), caption="Describe the situation."),
    Scene("Helper in Law finds the Article of the Constitution that governs it.",
          ui=("typed", "provisions", "provisions", 2.4), caption="The Article that governs it."),
    Scene("Every statement is checked against the source, before you ever see it.",
          ui=("provisions", "analysis", "analysis", 2.6), caption="Every statement, checked."),
    Scene("With the Supreme Court judgments that apply it, quoted at the exact paragraph.",
          ui=("analysis", "judgments", "judgments", 2.6), caption="The judgments that apply it."),
    Scene("Look up any Article, in its official words.",
          ui=("lookup", "article", "article", 2.2), caption="Any Article, in its official words."),
    Scene("And when the law is silent, it tells you. It never guesses.",
          ui=("article", "notfound", "notfound", 2.6), caption="When the law is silent, it says so."),
    Scene("Verified. Cited. In minutes, not days.", s_pillars, min_dur=6.9),
    Scene("Helper in Law. Every claim, verified.", s_end, min_dur=6.0),
]


def voice(model: Path, scenes: list[Scene], work: Path) -> list[np.ndarray]:
    from piper import PiperVoice, SynthesisConfig

    v = PiperVoice.load(str(model))
    cfg = SynthesisConfig(length_scale=1.1, noise_scale=0.55, noise_w_scale=0.7)
    clips = []
    for i, sc in enumerate(scenes):
        path = work / f"vo_{i:02d}.wav"
        with wave.open(str(path), "wb") as wf:
            v.synthesize_wav(sc.vo, wf, syn_config=cfg)
        with wave.open(str(path), "rb") as wf:
            sr = wf.getframerate()
            pcm = np.frombuffer(wf.readframes(wf.getnframes()), dtype="<i2").astype(np.float32) / 32768
        clips.append(np.interp(np.arange(int(len(pcm) * SR / sr)) / SR, np.arange(len(pcm)) / sr, pcm))
    return clips


def main(rec: Path, model: Path, out: Path, audio_only: bool = False) -> None:
    marks = json.loads((rec / "marks.json").read_text())
    work = out.parent / "film_work"
    work.mkdir(parents=True, exist_ok=True)
    scenes = HOPELESS + HOPEFUL
    clips = voice(model, scenes, work)
    lens = [len(c) / SR for c in clips]
    # the problem takes exactly TURN seconds, so picture and music turn together
    raw = [max(sc.min_dur, n + 1.0) for sc, n in zip(HOPELESS, lens[: len(HOPELESS)], strict=True)]
    durs = [d * TURN / sum(raw) for d in raw]
    for sc, n in zip(HOPEFUL, lens[len(HOPELESS):], strict=True):
        d = max(sc.min_dur, n + 1.2)
        if sc.ui:
            d = max(d, (marks[sc.ui[1]]["t"] - marks[sc.ui[0]]["t"]) / 1.9)
        durs.append(d)
    starts = [sum(durs[:i]) for i in range(len(durs))]
    total = sum(durs)

    silent = work / "film.silent.mp4"
    if not (audio_only and silent.exists()):
        render(scenes, durs, marks, rec, silent)

    # Grief until the turn, then Morning Mood from its first note: its sunrise peaks near the end.
    music = compress(music_bed(total, TURN, dawn_from=0.0))
    vo = np.zeros(len(music))
    for st, clip in zip(starts, clips, strict=True):
        i = int((st + 0.45) * SR)
        j = min(len(vo), i + len(clip))
        vo[i:j] += clip[: j - i]
    speech = np.abs(vo) > 0.01
    music *= 0.30 * np.sqrt(np.mean(vo[speech] ** 2)) / np.sqrt(np.mean(music**2))
    win = int(0.3 * SR)
    duck = 1 - 0.45 * np.clip(np.convolve(speech.astype(float), np.ones(win) / win, "same") * 3, 0, 1)
    wav = work / "film.wav"
    write_wav(wav, finish(vo[:, None] + music * duck[:, None]))
    mux(silent, wav, out)
    print(f"wrote {out} ({total:.1f}s; turn at {TURN}s)")


def render(scenes: list[Scene], durs: list[float], marks: dict, rec: Path, silent: Path) -> None:  # type: ignore[type-arg]
    enc = encoder(silent)
    assert enc.stdin
    for sc, dur in zip(scenes, durs, strict=True):
        n = int(round(dur * FPS))
        if sc.ui:
            a, b, focus, lead = sc.ui
            t0, t1, box = marks[a]["t"], marks[b]["t"], marks[focus]["box"]
            for k, (fr, src_t) in enumerate(screen_frames(rec / "screen.webm", t0, t1, n)):
                zk = ease((src_t - (t1 - lead)) / 1.1)
                gk = ease((src_t - (t1 - lead) - 1.0) / 0.6)
                enc.stdin.write(framed(fr, k / FPS, dur, sc.caption, box, zk, gk).tobytes())
        else:
            assert sc.render
            for k in range(n):
                enc.stdin.write(sc.render(k / FPS, dur).tobytes())
    enc.stdin.close()
    enc.wait()


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), "--audio-only" in sys.argv)
