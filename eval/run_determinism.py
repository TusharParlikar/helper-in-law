"""Fingerprint of every answer to the benchmark questions. Run under different PYTHONHASHSEED
values (eval/run_campaign.py does): identical fingerprints mean the same question always gets
the same answer, whatever the process.

uv run python eval/run_determinism.py
"""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

import eval.run_scenarios as bench  # noqa: E402
from helperinlaw.service import Service  # noqa: E402


def main() -> None:
    svc = Service()
    questions = [s["scenario"] for s in bench.load("scenarios") + bench.load("scenarios_heldout")]
    questions += [q["question"] for q in bench.load("out_of_scope_extra")]
    answers = []
    for q in questions:
        r = svc.ask(q)
        answers.append([r.confidence, [(c.case_id, c.para, c.quote) for c in r.citations],
                        [b.text for b in r.answer_blocks]])
    print(json.dumps({"questions": len(questions),
                      "fingerprint": hashlib.sha256(json.dumps(answers).encode()).hexdigest()[:16]}))


if __name__ == "__main__":
    main()
