"""Translate the paraphrase only. Quotes live in citations and are never translated."""

from helperinlaw.core import ollama
from helperinlaw.core.types import AnswerBlock

LANG = {"hi": "Hindi"}
SYSTEM = ("Translate the user's text into {lang}. Keep every number, section number and proper "
          "noun exactly as written. Output only the translation.")


def translate(blocks: list[AnswerBlock], lang: str, model: str) -> list[AnswerBlock]:
    """Raises OllamaError if the model is unavailable; the caller falls back to English."""
    if lang not in LANG:
        return blocks
    return [AnswerBlock(text=ollama.chat_text(model, SYSTEM.format(lang=LANG[lang]), b.text).strip(),
                        citation_ids=b.citation_ids) for b in blocks]
