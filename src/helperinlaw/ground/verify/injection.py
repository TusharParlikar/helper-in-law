"""G9: judgment text is data. Claims that carry instruction-like text are dropped."""

import re

INJECTION = re.compile(
    r"ignore (all |any )?(previous|prior|above) instructions|\bAI system\b|system prompt"
    r"|\byou are now\b|\breply PWNED\b|\bPWNED\b|disregard (the|your) (rules|instructions)",
    re.I,
)


def looks_injected(text: str) -> bool:
    return bool(INJECTION.search(text))
