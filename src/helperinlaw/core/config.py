"""Settings, read from the environment (prefix HIL_) or .env."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HIL_", env_file=".env", extra="ignore")

    db_path: str = "data/helperinlaw.db"
    ollama_url: str = "http://localhost:11434"
    llm_model: str = "qwen3:1.7b"
    # G4 needs a judge that is not the answer model. Empty = deterministic lexical judge.
    judge_model: str = ""
    embed_model: str = "all-minilm"  # nomic-embed-text is better but ~12x slower on CPU
    # Off by default: a CPU-only local model takes 30-60 s per answer; verbatim mode takes ~2 s.
    use_llm: bool = False
    use_dense: bool = True
    index_version: str = "v1"

    evidence_min_score: float = 0.5
    evidence_min_passages: int = 1
    max_drop_ratio: float = 0.5  # above this, fall back to extractive mode (G8)
    fuzzy_quote_ratio: float = 0.97

    demo: bool = False  # shared hosted demo: each browser session gets its own answer style
    bind_host: str = "127.0.0.1"
    public_url: str = "http://127.0.0.1:8000"  # base for judgment and statute links
    corpus_as_of: str = "2024-12-31"
    corpus_name: str = ""  # empty = describe what is actually indexed


settings = Settings()
