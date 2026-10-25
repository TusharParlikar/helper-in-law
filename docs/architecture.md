# Architecture (Phase 1)

One core (`src/helperinlaw/service.py`), three thin adapters: REST (`api/`), MCP (`mcp_server/`), Streamlit (`ui/`). No logic lives in handlers.

```
data/sample/*.txt|pdf
  -> ingest/  extract (quality score) -> clean -> parse/ (metadata, paragraphs, sections, statutes, citations)
  -> core/store.py  SQLite: cases, paragraphs, statutes, citation graph
  -> index/   paragraph-bounded chunks + FTS5 (BM25) + Ollama embeddings (nomic-embed-text)

question
  -> retrieve/understand   filters, statutes, case names
  -> retrieve/rewrite      IPC<->BNS / CrPC<->BNSS / IEA<->BSA alias queries
  -> retrieve/hybrid       BM25 + dense, RRF fusion, metadata filters
  -> retrieve/rerank       term coverage + statute match + profile boosts
  -> retrieve/evidence_gate  weak evidence -> abstain (G7)
  -> ground/claim_extract  Ollama (qwen3:1.7b) structured claims by source id + verbatim quote
                           (extractive fallback: verbatim sentences)
  -> ground/verify         schema, quote match, entities, entailment, allowlist, injection,
                           role check, duplicates, conflicts, overruled graph
  -> Verified Claim Set    (Stage A: style-independent, cached)
  -> present/presenter     profile: depth, structure, tone, citation style (Stage B)
  -> present/final_guard   no uncited block, no new numbers, no unknown case names
  -> Response              answer blocks + DB-rendered citations + verification report + coverage
```

## Grounding contract, where each rule lives

| Rule | Code |
|---|---|
| G1 LLM never writes case names/citations | `ground/claim_extract.render_sources` (model sees only ids), `ground/render.py` |
| G2 every claim has source id + quote | `core/types.Claim` (`support` min length 1) |
| G3 quote exists in cited chunk | `ground/verify/quote.py` (exact, then word-aligned fuzzy) |
| G4 claim entailed by quote | `ground/verify/entail.py` (lexical judge; optional separate Ollama judge) |
| G5 numbers/sections in the quote | `ground/verify/entities.py` |
| G6 allowlist sanitiser | `ground/verify/allowlist.py`, `present/final_guard.py` |
| G7 evidence gate | `retrieve/evidence_gate.py` |
| G8 extractive fallback | `ground/pipeline.py` (`max_drop_ratio`) |
| G9 source text is data | system prompt + `ground/verify/injection.py` |
| G10 conflicts / overruled | `ground/verify/graph.py`, `verify.conflicts` |
| G11 no answers from memory | G2 + G3 + G6 together |
| G12 verification report | `core/types.VerificationReport` on every `Response` |

## Phase 1 substitutions (deliberate)

| Roadmap | Phase 1 | Upgrade when |
|---|---|---|
| Postgres + Qdrant + Redis + MinIO | SQLite (FTS5 + vectors as blobs), in-process cache, local files | corpus > ~100k chunks or multi-user (Phase 2) |
| Claude + separate judge | Ollama `qwen3:1.7b`; lexical judge by default, `HIL_JUDGE_MODEL` for an LLM judge | a stronger local or hosted model is available |
| bge-m3 + bge-reranker | `nomic-embed-text` via Ollama + lexical reranker | GPU available |
| LLM multi-query rewrite | statute-alias rewrite | eval shows vocabulary misses |
| OCR fallback | low-quality extraction goes to dead letters | scanned judgments enter the corpus |
