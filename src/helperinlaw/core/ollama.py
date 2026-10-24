"""Minimal Ollama HTTP client (stdlib only)."""

import json
import urllib.error
import urllib.request
from typing import Any

from helperinlaw.core.config import settings


class OllamaError(RuntimeError):
    pass


def _post(path: str, body: dict[str, Any], timeout: float = 120) -> dict[str, Any]:
    req = urllib.request.Request(
        settings.ollama_url.rstrip("/") + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result: dict[str, Any] = json.loads(resp.read())
            return result
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        raise OllamaError(f"Ollama {path} failed: {e}") from e


def chat_json(model: str, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
    """One chat turn constrained to `schema`. Temperature 0, thinking off."""
    out = _post(
        "/api/chat",
        {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "format": schema,
            "stream": False,
            "think": False,
            "keep_alive": "30m",  # reloading the model costs ~15 s on CPU
            # Capped output keeps latency bounded; truncated JSON fails parsing -> caller falls back.
            "options": {"temperature": 0, "num_predict": 512},
        },
    )
    try:
        parsed: dict[str, Any] = json.loads(out["message"]["content"])
        return parsed
    except (KeyError, json.JSONDecodeError) as e:
        raise OllamaError(f"bad JSON from {model}: {e}") from e


def chat_text(model: str, system: str, user: str) -> str:
    out = _post(
        "/api/chat",
        {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "stream": False,
            "think": False,
            "options": {"temperature": 0},
        },
    )
    return str(out.get("message", {}).get("content", ""))


def embed(texts: list[str]) -> list[list[float]]:
    out = _post("/api/embed", {"model": settings.embed_model, "input": texts}, timeout=600)
    vecs: list[list[float]] = out.get("embeddings", [])
    if len(vecs) != len(texts):
        raise OllamaError("embedding count mismatch")
    return vecs


def available() -> bool:
    try:
        with urllib.request.urlopen(settings.ollama_url.rstrip("/") + "/api/tags", timeout=2):
            return True
    except (urllib.error.URLError, TimeoutError):
        return False
