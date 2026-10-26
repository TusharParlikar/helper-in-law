"""Scenario benchmark on the live corpus (official Constitution + indexed Supreme Court judgments).

uv run python eval/run_scenarios.py          # verbatim mode (no LLM), as the app runs by default
uv run python eval/run_scenarios.py --llm    # with the local LLM drafting claims
uv run python eval/run_scenarios.py --heldout  # the held-out set, written before any tuning on it

Each scenario is labelled with the Article(s) that govern it (eval/datasets/scenarios.jsonl).
Labels are standard constitutional law, written by the developer; have a lawyer review them.
"""

import json
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from eval.run_eval import audit  # noqa: E402
from helperinlaw.core.config import Settings  # noqa: E402
from helperinlaw.ingest.official import PREFIX  # noqa: E402
from helperinlaw.service import Service  # noqa: E402

DATA = ROOT / "eval" / "datasets"


def load(name: str) -> list[dict]:  # type: ignore[type-arg]
    return [json.loads(x) for x in (DATA / f"{name}.jsonl").read_text("utf-8").splitlines() if x.strip()]


def pct(n: int, d: int) -> str:
    return f"{100 * n / d:.0f}% ({n}/{d})" if d else "n/a"


def main() -> None:
    use_llm = "--llm" in sys.argv
    heldout = "--heldout" in sys.argv
    svc = Service(cfg=Settings(use_llm=use_llm))
    scenarios, oos = load("scenarios_heldout" if heldout else "scenarios"), load("out_of_scope")
    rows, latencies = [], []
    unsupported = n_cites = bad_cites = lacking = 0
    for s in scenarios:
        t = time.perf_counter()
        r = svc.ask(s["scenario"])
        latencies.append(time.perf_counter() - t)
        u, n, b = audit(svc, r)
        unsupported, n_cites, bad_cites = unsupported + u, n_cites + n, bad_cites + b
        lacking += r.confidence != "not_found" and not r.citations
        shown = list(dict.fromkeys(c.case_id.removeprefix(PREFIX) for c in r.citations if c.kind == "provision"))
        want = set(s["articles"])
        applies = any(f"CONST {a}" in c.statutes for c in r.citations if c.kind == "judgment" for a in want)
        rows.append({**s, "shown": shown, "top": shown[0] if shown else None, "answered": r.confidence != "not_found",
                     "hit1": bool(shown) and shown[0] in want, "hit": bool(want & set(shown)), "applies": applies})
    abstained = 0
    for q in oos:
        t = time.perf_counter()
        abstained += svc.ask(q["question"]).confidence == "not_found"
        latencies.append(time.perf_counter() - t)

    n = len(rows)
    m = {
        "scenarios": n,
        "answered": sum(r["answered"] for r in rows),
        "top_provision_correct": sum(r["hit1"] for r in rows),
        "correct_provision_shown": sum(r["hit"] for r in rows),
        "provisions_shown": sum(len(r["shown"]) for r in rows),
        "provisions_on_point": sum(len(set(r["shown"]) & set(r["articles"])) for r in rows),
        "judgment_applies_it": sum(r["applies"] for r in rows),
        "out_of_scope": len(oos),
        "out_of_scope_abstained": abstained,
        "unsupported_claims_displayed": unsupported,
        "citations_checked": n_cites,
        "citation_accuracy": round(1 - bad_cites / n_cites, 4) if n_cites else 1.0,
        "answers_without_citations": lacking,
        "p50_s": round(statistics.median(latencies), 2),
        "p95_s": round(statistics.quantiles(latencies, n=20)[18], 2),
    }
    by_area: dict[str, list[dict]] = defaultdict(list)  # type: ignore[type-arg]
    for r in rows:
        by_area[r["area"]].append(r)

    cov = svc.coverage()
    lines = [
        "# Scenario benchmark" + (" (held-out set)" if heldout else ""), "",
        f"- Mode: {'local LLM drafts, then verified' if use_llm else 'verbatim passages (no LLM)'}; "
        f"search: {'keyword + semantic' if svc.cfg.use_dense else 'keyword'}",
        f"- Corpus: {cov.corpus}",
        f"- {n} lawyer-style scenarios labelled with the governing Article(s), plus {len(oos)} out-of-scope questions.",
        "- Labels are standard constitutional law written by the developer, not yet reviewed by a lawyer.", "",
        "## Results", "",
        "| Measure | Result |", "|---|---|",
        f"| Correct Article is the top provision shown | {pct(m['top_provision_correct'], n)} |",
        f"| Correct Article among the provisions shown | {pct(m['correct_provision_shown'], n)} |",
        f"| Provisions shown that are on point (precision) | {pct(m['provisions_on_point'], m['provisions_shown'])} |",
        f"| A cited judgment applies that Article | {pct(m['judgment_applies_it'], n)} |",
        f"| Scenarios answered (not abstained) | {pct(m['answered'], n)} |",
        f"| Out-of-scope questions correctly refused | {pct(abstained, len(oos))} |",
        f"| Unsupported statements displayed | **{unsupported}** |",
        f"| Quotes found verbatim at their cited paragraph | {pct(n_cites - bad_cites, n_cites)} |",
        f"| Answers without citations | **{lacking}** |",
        f"| Latency p50 / p95 | {m['p50_s']} s / {m['p95_s']} s |", "",
        "## By area", "", "| Area | Scenarios | Top Article correct | Correct Article shown |", "|---|---|---|---|",
    ]
    for area, rs in sorted(by_area.items()):
        lines.append(f"| {area} | {len(rs)} | {pct(sum(r['hit1'] for r in rs), len(rs))} | "
                     f"{pct(sum(r['hit'] for r in rs), len(rs))} |")
    misses = [r for r in rows if not r["hit"]]
    lines += ["", f"## Misses ({len(misses)})", "", "| Scenario | Expected | Shown |", "|---|---|---|"]
    lines += [f"| {r['scenario'][:90]} | Art. {', '.join(r['articles'])} | "
              f"{', '.join('Art. ' + a for a in r['shown']) or 'none'} |" for r in misses]
    report = "\n".join(lines) + "\n"
    name = "scenarios_heldout" if heldout else "scenarios"
    out = ROOT / "eval" / "reports" / f"{name}{'_llm' if use_llm else ''}.md"
    out.write_text(report, encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(report)
    print(json.dumps(m))


if __name__ == "__main__":
    main()
