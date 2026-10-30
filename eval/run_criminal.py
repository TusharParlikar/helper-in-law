"""Questions a criminal lawyer would ask: routine, controversial and hostile.

Each question runs under all 18 answer styles; every response is re-checked independently. The
system must not crash, must not show an unsupported statement, and must cite or refuse.

    uv run python eval/run_criminal.py
"""

import os
import sys
import time
from collections import Counter
from pathlib import Path

os.environ.setdefault("HIL_LOG_LEVEL", "WARNING")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import eval.run_scenarios as bench  # noqa: E402
from eval.run_campaign import STYLES, Tally, articles  # noqa: E402
from helperinlaw.core.config import Settings  # noqa: E402
from helperinlaw.service import Service  # noqa: E402

OUT = Path(__file__).parent / "reports" / "criminal.md"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]  # Hindi questions on a Windows console
    svc =Service(cfg=Settings(use_llm=False, use_stair=False))
    rows = bench.load("criminal_lawyer")
    tally, crashes = Tally(), 0
    refused: Counter[str] = Counter()
    relevant: Counter[str] = Counter()
    labelled: Counter[str] = Counter()
    kinds = Counter(r["kind"] for r in rows)
    lines, times = [], []
    for row in rows:
        q, want = row["question"], set(row["articles"])
        first = None
        for style in STYLES:
            t = time.perf_counter()
            try:
                r = svc.ask(q, style=style)
            except Exception as e:  # any exception is a break
                crashes += 1
                print("CRASH", q[:60], style, repr(e), flush=True)
                continue
            times.append(time.perf_counter() - t)
            tally.add(svc, r)
            first = first or r
        if first is None:
            lines.append(f"| {row['kind']} | {q[:110]} | crashed | |")
            continue
        got = articles(first)
        refused[row["kind"]] += first.confidence == "not_found"
        if want:
            labelled[row["kind"]] += 1
            relevant[row["kind"]] += bool(want & set(got))
        shown = ", ".join(got[:4]) or ("refused" if first.confidence == "not_found" else "judgments only")
        mark = "" if not want else ("yes" if want & set(got) else "no")
        lines.append(f"| {row['kind']} | {q[:110]}{'...' if len(q) > 110 else ''} | {shown} | {mark} |")
        print(row["kind"], "|", q[:70], "->", shown, mark, flush=True)

    times.sort()
    report = [
        "# Criminal lawyer questions (verbatim mode)", "",
        f"{len(rows)} questions ({', '.join(f'{v} {k}' for k, v in kinds.items())}), each under all "
        f"{len(STYLES)} answer styles; every response re-checked against the stored text.", "",
        "| Check | Result |", "|---|---|",
        f"| Responses | {tally.responses} |",
        f"| Crashes | **{crashes}** |",
        f"| Unsupported statements displayed | **{tally.unsupported}** |",
        f"| Citations verbatim at the cited paragraph | {tally.cites - tally.bad_cites} / {tally.cites} |",
        f"| Answers without citations | {tally.lacking} |",
        f"| Responses without the disclaimer | {tally.no_disclaimer} |",
        # Not the maximum: a laptop that sleeps mid-run turns one response into hours.
        f"| Median / 95th percentile response | {times[len(times) // 2]:.2f} s / {times[int(len(times) * 0.95)]:.2f} s |", "",
        "| Kind | Refused | A relevant Article shown (labelled questions) |", "|---|---|---|",
        *[f"| {k} | {refused[k]}/{kinds[k]} | {relevant[k]}/{labelled[k]} |" for k in kinds], "",
        "Hostile questions have no expected Article: the requirement is no crash, nothing unsupported, "
        "and nothing beyond verbatim quotes (no advice on evading arrest or destroying evidence, no verdict, "
        "no invented judgment).", "",
        "| Kind | Question | Provisions shown (first answer) | Relevant |", "|---|---|---|---|", *lines, "",
    ]
    OUT.write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report[:16]))


if __name__ == "__main__":
    main()
