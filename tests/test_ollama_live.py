"""Live tests against local Ollama. Skipped when Ollama or the models aren't available."""

import pytest

from helperinlaw.core import ollama
from helperinlaw.core.config import Settings
from helperinlaw.core.store import Store
from helperinlaw.index.build import build
from helperinlaw.service import Service

pytestmark = pytest.mark.skipif(not ollama.available(), reason="Ollama not running")


@pytest.fixture(scope="module")
def live(store: Store) -> Service:
    cfg = Settings(use_llm=True, use_dense=True, db_path=":memory:", index_version="live")
    try:
        build(store, "live", dense=True)
    except ollama.OllamaError as e:
        pytest.skip(f"embedding model unavailable: {e}")
    return Service(store, cfg)


def test_llm_answer_is_fully_grounded(live: Service) -> None:
    r = live.ask("What are the grounds for refusing bail under Section 439 CrPC?")
    assert r.confidence != "not_found"
    assert all(b.citation_ids for b in r.answer_blocks)
    for c in r.citations:
        para = live.get_paragraphs(c.case_id, int(c.para))[0]["text"]
        assert c.quote.strip(" .").lower() in para.lower() or c.quote in para


def test_llm_path_still_abstains(live: Service) -> None:
    r = live.ask("What is the punishment for sedition under Section 124A IPC?")
    assert r.confidence == "not_found"
