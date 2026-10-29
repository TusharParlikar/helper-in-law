"""STAIR-style retrieval (Kumar et al., "STAIR: STructure Aware Information Retriever", 2026):
the model reads the Constitution's official table of contents (Parts, chapters, group headings,
Article titles) and names the Articles that govern a situation. Decoding is constrained to the
Article numbers in the table, so it cannot name one that does not exist.

ponytail: untrained (prompted) STAIR on the local model. The paper's gains come from fine-tuning
on query -> section pairs; do that on a GPU before expecting more than a ranking hint.
"""

from functools import lru_cache
from typing import Any

from helperinlaw.core import ollama
from helperinlaw.core.config import Settings
from helperinlaw.core.store import Store
from helperinlaw.core.types import TocEntry

TOP = 3
CONTEXT = 12288  # the outline is ~7k tokens; the default 4096 would cut it
INSTRUCTION = (
    "You find the Articles of the Constitution of India that govern a situation described by a lawyer.\n"
    "Pick the best Articles from the table of contents below. Only answer with Article numbers from "
    "the table, most relevant first, at most 3. Do not explain.\n\n### Table of Contents\n"
)


def outline(toc: list[TocEntry]) -> str:
    """Indented table of contents: Part, chapter, group heading, then "14. Equality before law"."""
    lines: list[str] = []
    part = chapter = group = None
    for e in toc:
        if e.part != part:
            part, chapter, group = e.part, None, None
            lines.append(e.part)
        if e.chapter and e.chapter != chapter:
            chapter, group = e.chapter, None
            lines.append(f" {e.chapter}")
        if e.group and e.group != group:
            group = e.group
            lines.append(f"  {e.group}")
        lines.append(f"   {e.number}. {e.title}")
    return "\n".join(lines)


@lru_cache(maxsize=512)  # one model call per distinct situation; errors are not cached
def _pick(model: str, system: str, question: str, numbers: tuple[str, ...]) -> tuple[str, ...]:
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "articles": {
                "type": "array",
                "items": {"type": "string", "enum": list(numbers)},
                "minItems": 1,
                "maxItems": TOP,
            }
        },
        "required": ["articles"],
    }
    out = ollama.chat_json(
        model, system, f"### Situation\n{question}\n\n### Articles", schema,
        options={"num_ctx": CONTEXT, "num_predict": 48},
        timeout=900,  # the first call reads the whole outline (minutes on a laptop CPU)
    )
    valid = set(numbers)
    return tuple(dict.fromkeys(a for a in out.get("articles", []) if a in valid))[:TOP]


def stair_articles(store: Store, cfg: Settings, question: str) -> list[str]:
    """Up to 3 Article numbers, most relevant first; [] when off, without a table, or offline."""
    if not cfg.use_stair or not (toc := store.toc()):
        return []
    # The system message is the same for every question, so the server reuses its processed
    # prefix and only the situation is new work on each call.
    try:
        return list(_pick(cfg.llm_model, INSTRUCTION + outline(toc), question, tuple(e.number for e in toc)))
    except ollama.OllamaError:
        return []  # STAIR is a ranking hint; keyword search alone still answers
