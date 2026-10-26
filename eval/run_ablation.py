"""Ablation on the live corpus: switch one component off at a time and re-run the 47-scenario
benchmark, to show what each part contributes.

uv run python eval/run_ablation.py
"""

import contextlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

import eval.run_scenarios as bench  # noqa: E402
import helperinlaw.ground.claim_extract as claim_extract  # noqa: E402
import helperinlaw.ground.pipeline as pipeline  # noqa: E402
import helperinlaw.retrieve.evidence_gate as gate  # noqa: E402
import helperinlaw.retrieve.rerank as rerank  # noqa: E402
import helperinlaw.retrieve.rewrite as rewrite  # noqa: E402


@contextlib.contextmanager
def patched(obj: object, name: str, value: object):  # type: ignore[no-untyped-def]
    old = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, old)


def run() -> dict:  # type: ignore[type-arg]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        bench.main()
    return json.loads(buf.getvalue().strip().splitlines()[-1])


def no_idf(store, index_version):  # type: ignore[no-untyped-def]
    return {}


CONFIGS = [
    ("Full system", []),
    ("- lay-to-legal vocabulary", [(rewrite, "LEGAL_TERMS", {}), (rerank, "LEGAL_TERMS", {}), (gate, "LEGAL", gate.LEGAL_WORDS)]),
    ("- precedent vote for Articles", [(pipeline, "PRECEDENT_BOOST", 0.0)]),
    ("- IDF weighting in reranker", [(rerank, "idf_table", no_idf)]),
    ("- runner-up rule (always 2 Articles)", [(claim_extract, "RUNNER_UP", 0.0)]),
    ("- legal-vocabulary gate", [(gate, "legal_question", lambda q: True)]),
]


def main() -> None:
    rows = []
    for name, patches in CONFIGS:
        with contextlib.ExitStack() as stack:
            for obj, attr, value in patches:
                stack.enter_context(patched(obj, attr, value))
            m = run()
        rows.append((name, m))
        print(name, json.dumps({k: m[k] for k in ("top_provision_correct", "correct_provision_shown",
                                                     "provisions_on_point", "provisions_shown",
                                                     "judgment_applies_it", "out_of_scope_abstained")}), flush=True)
    n = rows[0][1]["scenarios"]
    lines = ["# Ablation (live corpus, 47 scenarios + 8 out-of-scope)", "",
             "Each row switches one component off; everything else stays as in the full system.", "",
             "| Configuration | Top Article correct | Correct Article shown | Precision of Articles shown "
             "| Precedent applies it | Out-of-scope refused | Unsupported shown |", "|---|---|---|---|---|---|---|"]
    for name, m in rows:
        prec = m["provisions_on_point"] / m["provisions_shown"] if m["provisions_shown"] else 0
        lines.append(f"| {name} | {m['top_provision_correct']}/{n} | {m['correct_provision_shown']}/{n} | {prec:.0%} "
                     f"| {m['judgment_applies_it']}/{n} | {m['out_of_scope_abstained']}/{m['out_of_scope']} "
                     f"| {m['unsupported_claims_displayed']} |")
    report = "\n".join(lines) + "\n"
    (ROOT / "eval" / "reports" / "ablation.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
