"""STAIR (table-of-contents retrieval) on the 47-scenario dev set.

uv run python eval/run_stair.py     # needs Ollama; the first call reads the whole outline

1. STAIR alone, the paper's metric: Recall@1 / Recall@3 of the Articles it names, next to
   keyword search (BM25 + rewrite + rerank) over the Constitution alone.
2. The full system with STAIR fused into the Article ranking, for several boosts, next to the
   full system without it. STAIR's picks are cached, so each boost re-uses the same model calls.
"""

import contextlib
import io
import json
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

import eval.run_scenarios as bench  # noqa: E402
import helperinlaw.ground.pipeline as pipeline  # noqa: E402
from helperinlaw.core.config import Settings  # noqa: E402
from helperinlaw.core.store import Store  # noqa: E402
from helperinlaw.core.types import Profile  # noqa: E402
from helperinlaw.ingest.official import PREFIX  # noqa: E402
from helperinlaw.retrieve.hybrid import search  # noqa: E402
from helperinlaw.retrieve.rerank import rerank  # noqa: E402
from helperinlaw.retrieve.rewrite import rewrite  # noqa: E402
from helperinlaw.retrieve.stair import stair_articles  # noqa: E402
from helperinlaw.retrieve.understand import understand  # noqa: E402

BOOSTS = (0.2, 0.4, 0.6)


def keyword_articles(store: Store, cfg: Settings, question: str) -> list[str]:
    q = understand(question, None)
    hits = search(store, q, rewrite(q), cfg.index_version, False, 60, "provision")
    ranked = rerank(store, q, hits, Profile(), top=10, index_version=cfg.index_version)
    return list(dict.fromkeys(c.case_id.removeprefix(PREFIX) for c, _ in ranked))[:3]


def full(stair: bool, boost: float) -> dict:  # type: ignore[type-arg]
    os.environ["HIL_USE_STAIR"] = "true" if stair else "false"
    pipeline.STAIR_BOOST = boost
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        bench.main()
    return json.loads(buf.getvalue().strip().splitlines()[-1])


def main() -> None:
    cfg = Settings(use_stair=True)
    store = Store(cfg.db_path)
    scenarios = bench.load("scenarios")
    n = len(scenarios)
    s1 = s3 = k1 = k3 = 0
    times: list[float] = []
    for s in scenarios:
        want = set(s["articles"])
        t = time.perf_counter()
        picks = stair_articles(store, cfg, s["scenario"])
        times.append(time.perf_counter() - t)
        kw = keyword_articles(store, cfg, s["scenario"])
        s1 += bool(picks) and picks[0] in want
        s3 += bool(want & set(picks))
        k1 += bool(kw) and kw[0] in want
        k3 += bool(want & set(kw))
        print(f"{times[-1]:6.1f}s STAIR {picks} keyword {kw} want {sorted(want)}", flush=True)
    rows = [("Full system, no STAIR", full(False, 0.0))]
    rows += [(f"Full system + STAIR (boost {b})", full(True, b)) for b in BOOSTS]
    os.environ.pop("HIL_USE_STAIR", None)
    warm = times[1:] or times
    lines = [
        "# STAIR on the dev set (47 scenarios)", "",
        "STAIR: the local model (`qwen3:1.7b`, untrained) reads the Constitution's official table of "
        "contents and names up to 3 Articles; decoding is constrained to real Article numbers.", "",
        "## Retrieving the Article alone", "",
        "| Retriever | Recall@1 | Recall@3 |", "|---|---|---|",
        f"| Keyword search over the Constitution (BM25 + rewrite + rerank) | {k1}/{n} | {k3}/{n} |",
        f"| STAIR (table of contents, untrained) | {s1}/{n} | {s3}/{n} |", "",
        f"STAIR time per question: first {times[0]:.0f} s (reads the whole outline), then median "
        f"{statistics.median(warm):.0f} s.", "",
        "## Full system", "",
        "| Configuration | First Article correct | Correct Article shown | Precision | Precedent applies it "
        "| Out-of-scope refused | Unsupported shown |", "|---|---|---|---|---|---|---|",
    ]
    for name, m in rows:
        prec = m["provisions_on_point"] / m["provisions_shown"] if m["provisions_shown"] else 0
        lines.append(f"| {name} | {m['top_provision_correct']}/{n} | {m['correct_provision_shown']}/{n} | "
                     f"{prec:.0%} | {m['judgment_applies_it']}/{n} | {m['out_of_scope_abstained']}/"
                     f"{m['out_of_scope']} | {m['unsupported_claims_displayed']} |")
    report = "\n".join(lines) + "\n"
    (ROOT / "eval" / "reports" / "stair.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
