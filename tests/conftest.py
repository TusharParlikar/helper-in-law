from pathlib import Path

import pytest

from helperinlaw.core.config import Settings
from helperinlaw.core.store import Store
from helperinlaw.index.build import build
from helperinlaw.ingest.pipeline import ingest_dir
from helperinlaw.service import Service

SAMPLE = Path(__file__).parent.parent / "data" / "sample"


@pytest.fixture(scope="session")
def cfg() -> Settings:
    # Offline and deterministic: BM25 + extractive claims + lexical judge. Live Ollama tests
    # live in test_ollama_live.py and skip when Ollama isn't running.
    return Settings(use_llm=False, use_dense=False, db_path=":memory:")


@pytest.fixture(scope="session")
def store(cfg: Settings) -> Store:
    s = Store(":memory:")
    ingest_dir(s, SAMPLE)
    build(s, cfg.index_version, dense=False)
    return s


@pytest.fixture()
def service(store: Store, cfg: Settings) -> Service:
    return Service(store, cfg)
