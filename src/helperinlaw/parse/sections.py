"""Rhetorical-role labels for paragraphs: facts, arguments, issues, holding, reasoning.

ponytail: keyword heuristic. Swap for a trained classifier when the gold set shows it
misses (measure with eval/datasets/gold_parse.jsonl).
"""

import re

RULES = [
    ("arguments", re.compile(r"\b(learned counsel|contended|submitted|argued)\b", re.I)),
    ("issues", re.compile(r"\b(the question|the issue|questions? that arises?|for determination)\b", re.I)),
    ("holding", re.compile(
        r"\b(we hold|it is held|appeal is (allowed|dismissed)|petition is (allowed|dismissed)"
        r"|application is (allowed|dismissed)|overruled|reference is answered)\b", re.I)),
    ("facts", re.compile(r"\b(FIR|was arrested|was convicted|was married|was charged|facts)\b")),
]


def label(text: str, n: int) -> str:
    for name, rx in RULES:
        if rx.search(text):
            return name
    return "facts" if n == 1 else "reasoning"
