"""Build an index version: chunk every case, load FTS, embed (resumable)."""

from helperinlaw.core import ollama
from helperinlaw.core.logging import get_logger
from helperinlaw.core.store import Store
from helperinlaw.index.chunker import MAX_WORDS, chunk_case

log = get_logger(__name__)
BATCH = 32


def build(store: Store, index_version: str, dense: bool, max_words: int = MAX_WORDS) -> dict[str, int]:
    """Side-by-side rebuild: a new index_version never touches the one being served."""
    chunks = [
        c
        for case in store.list_cases()
        for c in chunk_case(case, store.get_paragraphs(case.id), max_words)
    ]
    store.replace_chunks(index_version, chunks)
    embedded = 0
    if dense:
        done = store.embedded_ids(index_version)
        todo = [c for c in chunks if c.id not in done]
        for i in range(0, len(todo), BATCH):
            batch = todo[i : i + BATCH]
            vecs = ollama.embed([c.prefix + "\n" + c.text for c in batch])
            store.put_embeddings(
                index_version, [(c.id, v) for c, v in zip(batch, vecs, strict=True)]
            )
            embedded += len(batch)
    log.info(
        "index built", extra={"extra_fields": {"version": index_version, "chunks": len(chunks)}}
    )
    return {"chunks": len(chunks), "embedded": embedded}
