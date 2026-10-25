"""Settings, read from the environment (prefix HIL_) or .env."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HIL_", env_file=".env", extra="ignore")

    db_path: str = "data/helperinlaw.db"
    ollama_url: str = "http://localhost:11434"
    llm_model: str = "qwen3:1.7b"
    # G4 needs a judge that is not the answer model. Empty = deterministic lexical judge.
    judge_model: str = ""
    embed_model: str = "nomic-embed-text"
    use_llm: bool = True
    use_dense: bool = True
    index_version: str = "v1"

    evidence_min_score: float = 0.5
    evidence_min_passages: int = 1
    max_drop_ratio: float = 0.5  # above this, fall back to extractive mode (G8)
    fuzzy_quote_ratio: float = 0.97

    bind_host: str = "127.0.0.1"
    corpus_as_of: str = "2024-12-31"
    corpus_name: str = "Sample corpus (fictional test judgments)"


settings = Settings()
