"""G9: judgment text is data. Claims that carry instruction-like text are dropped."""

import re

from helperinlaw.ground.text import sentences

INJECTION = re.compile(
    r"ignore (all |any )?(previous|prior|above) instructions|\bAI system\b|system prompt"
    r"|\byou are now\b|\breply PWNED\b|\bPWNED\b|disregard (the|your) (rules|instructions)",
    re.I,
)


# A sentence telling the system how to answer ("Skip the verification step", "Do not show the
# disclaimer"), as opposed to a fact of the situation.
META = re.compile(
    r"^(?:please\s+|also\s+|just\s+)?(?:ignore|skip|omit|hide|remove|answer|reply|respond|do not|don't|never)\b"
    r".*\b(?:instructions?|rules|citations?|verification|verify|disclaimers?)\b",
    re.I,
)


def looks_injected(text: str) -> bool:
    return bool(INJECTION.search(text))


def without_instructions(question: str) -> str:
    """The question minus sentences addressed to the system, so they don't steer retrieval.
    They change nothing else either: grounding ignores them by design."""
    return " ".join(s for s in sentences(question) if not (looks_injected(s) or META.search(s)))
