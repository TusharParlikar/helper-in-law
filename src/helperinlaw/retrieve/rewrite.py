"""Multi-query rewrite. Deterministic: expand statute references to their old/new-code
counterpart so a BNS question also finds IPC-era judgments (and vice versa).

ponytail: no LLM paraphrase rewrite; add one when the eval shows vocabulary-mismatch misses.
"""

from helperinlaw.parse.statutes import ACT_NAMES, aliases
from helperinlaw.retrieve.understand import Query


def rewrite(q: Query) -> list[str]:
    queries = [q.text]
    for act, section in q.statutes:
        for a, s in aliases(act, section):
            name = ACT_NAMES.get(a, [a])[0]
            queries.append(f"Section {s} {a} {name}")
    return list(dict.fromkeys(queries))
