"""Parser audit on the real Supreme Court judgments: automated consistency checks over the whole
corpus, plus a 50-judgment gold set (eval/datasets/gold_parse_real.jsonl) re-parsed from the PDFs.

uv run python eval/run_parse_audit.py
"""

import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from helperinlaw.core.config import Settings  # noqa: E402
from helperinlaw.core.store import Store  # noqa: E402
from helperinlaw.ingest.clean import clean  # noqa: E402
from helperinlaw.ingest.extract import extract_text  # noqa: E402
from helperinlaw.ingest.sci import RAW, judgment_paragraphs, judgment_start  # noqa: E402

GOLD = ROOT / "eval" / "datasets" / "gold_parse_real.jsonl"
HEADNOTE = re.compile(r"\bHeld\s*:|\bHEADNOTE|\[Paras? \d+", re.I)


def gold(store: Store) -> dict[str, tuple[int, int]]:
    """Field -> (correct, total) on the gold set. Paragraphs are re-parsed from the PDF."""
    rows = [json.loads(x) for x in GOLD.read_text("utf-8").splitlines() if x.strip()]
    score = {k: [0, 0] for k in ("citation", "neutral_citation", "date", "judges", "paragraphs")}
    for g in rows:
        c = store.get_case(g["case_id"])
        if c is None:
            continue
        paras = judgment_paragraphs(clean(extract_text(RAW / f"{Path(c.url).stem.removesuffix('_EN')}.pdf")))
        got = {"citation": c.citation, "neutral_citation": c.neutral_citation, "date": c.date,
               "judges": [j.split()[-1] for j in c.bench], "paragraphs": len(paras)}
        for k in score:
            score[k][0] += got[k] == g[k]
            score[k][1] += 1
    return {k: (a, b) for k, (a, b) in score.items()}


def main() -> None:
    store = Store(Settings().db_path)
    cases = [c for c in store.list_cases() if c.id.startswith("sc-")]
    meta_ok = numbering_ok = leaks = 0
    coverage: list[float] = []
    for c in cases:
        meta_ok += all([c.title, c.date, c.bench, c.citation, c.neutral_citation])
        paras = store.get_paragraphs(c.id)
        numbering_ok += [p.n for p in paras] == list(range(1, len(paras) + 1)) and len(paras) >= 3
        leaks += any(HEADNOTE.search(p.text) for p in paras[:2])
        pdf = RAW / f"{Path(c.url).stem.removesuffix('_EN')}.pdf"
        if pdf.exists():
            text = clean(extract_text(pdf))
            body_words = len(text[judgment_start(text):].split())
            coverage.append(min(1.0, sum(len(p.text.split()) for p in paras) / max(1, body_words)))
    n = len(cases)
    low = sum(x < 0.6 for x in coverage)
    g = gold(store)
    lines = [
        "# Parser audit (real Supreme Court judgments)", "",
        f"{n} judgments in the corpus.", "",
        "## Gold set (50 judgments)", "",
        "Labels taken from each judgment's own PDF (first page: citation, neutral citation, date, bench; "
        "paragraph count after checking that no later paragraph number is left inside the last paragraph). "
        "Every disagreement with the parser was reviewed by hand against the PDF; the sample is drawn with a "
        "fixed seed. Paragraphs are re-parsed from the PDF on every run. Building it found two parser bugs "
        "(paragraph numbers after a stray bullet or margin letter, and paragraphs joined onto the previous "
        "line) and one metadata gap (neutral citation missing from the record but printed in the PDF): "
        "before those fixes the parser scored 48/50 on paragraphs and 49/50 on neutral citations.", "",
        "| Field | Correct |", "|---|---|",
        *[f"| {k.replace('_', ' ')} | {a}/{b} ({100 * a / b:.0f}%) |" for k, (a, b) in g.items()],
        "", "## Whole corpus (automated consistency checks)", "",
        "| Check | Result |", "|---|---|",
        f"| Metadata complete (title, date, bench, SCR citation, neutral citation) | {meta_ok}/{n} ({100 * meta_ok / n:.0f}%) |",
        f"| Paragraphs numbered 1..N with no gaps, at least 3 | {numbering_ok}/{n} ({100 * numbering_ok / n:.0f}%) |",
        f"| Editorial headnote text leaking into the first paragraphs | {leaks}/{n} |",
        f"| Share of the judgment's text captured in numbered paragraphs (median) | {statistics.median(coverage):.0%} |",
        f"| Judgments with under 60% captured (likely concurring opinions or annexures dropped) | {low}/{len(coverage)} |",
        "", "Metadata comes from the Supreme Court's own e-SCR records. Paragraph numbering and coverage come from "
        "the parser. Concurring and dissenting opinions restart their numbering and are not yet captured; "
        "that is the main source of low coverage.",
    ]
    report = "\n".join(lines) + "\n"
    (ROOT / "eval" / "reports" / "parse_audit.md").write_text(report, encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
