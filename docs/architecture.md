# Architecture (Phase 1)

One core (`src/helperinlaw/service.py`), three thin adapters: REST (`api/`), MCP (`mcp_server/`), Streamlit (`ui/`). No logic lives in handlers.

## Corpus

| Source | Ingest | Stored as |
|---|---|---|
| The Constitution of India [As on 1st May, 2024], Legislative Department (official PDF) | `ingest/official.py`: English pages only, footnotes and running headers removed, one record per Article | `coi-<article>` documents, one paragraph each, linked to the exact PDF page |
| Supreme Court judgments, Indian Supreme Court Judgments open dataset (CC-BY-4.0) | `ingest/sci.py`: per-year metadata tar, headnotes filtered for key Articles, PDF fetched, only the Court's own numbered paragraphs kept (editorial headnotes dropped) | `sc-<neutral citation>` documents with paragraphs, statutes and the citation graph |
| Fictional sample judgments | `ingest/pipeline.py` | Used by the test suite only |

Every ingest is idempotent and resumable; a document that cannot be parsed goes to the `dead_letter` table with its reason, never silently.

## Answering a question

```
situation / question
  -> retrieve/understand     filters, statutes, Articles, case names
  -> retrieve/evidence_gate  no legal vocabulary at all -> "not found" (off-topic questions)
  -> retrieve/rewrite        statute aliases (IPC<->BNS ...) + lay-to-legal terms
                             ("not told why" -> "informed of the grounds", "lawyer" -> "legal practitioner")
  -> retrieve/hybrid         BM25 (SQLite FTS5) [+ dense if embeddings exist], RRF fusion,
                             run separately for Constitution articles and for judgments
  -> retrieve/rerank         IDF-weighted coverage of the situation's most informative words,
                             synonym groups, statute match, profile boosts
  -> ground/pipeline         judgments (max 2 passages each) vote for the Articles they apply;
                             evidence gate; parent expansion (each judgment passage + its
                             neighbouring paragraphs)
  -> ground/claim_extract    the governing Article's best clause + verbatim judgment sentences
                             (or, with the LLM on, structured claims citing sources by id)
  -> ground/verify           quote exists (exact, then word-aligned fuzzy), numbers/sections in the
                             quote, entailment + negation scope, allowlist, injection, role check,
                             duplicates, conflicts, overruled graph
  -> Verified Claim Set      (Stage A: style-independent, cached)
  -> present/presenter       depth, structure, tone, citation style (Stage B)
  -> present/final_guard     no uncited block, no new numbers, no unknown case names
  -> Response                answer + DB-rendered citations + verification report + laws + coverage
  -> report.py               optional PDF research report; refused when there is no proof
```

## Grounding contract, where each rule lives

| Rule | Code |
|---|---|
| G1 LLM never writes case names/citations | `ground/claim_extract.render_sources` (model sees only ids and the source kind), `ground/render.py` |
| G2 every claim has source id + quote | `core/types.Claim` (`support` min length 1) |
| G3 quote exists in cited chunk | `ground/verify/quote.py`; paragraph markers `⟦n⟧` so report citations like "[1993] 2 SCR 581" are never read as paragraph numbers |
| G4 claim entailed by quote | `ground/verify/entail.py` (lexical judge with negation scope; optional separate Ollama judge) |
| G5 numbers/sections in the quote | `ground/verify/entities.py` |
| G6 allowlist sanitiser | `ground/verify/allowlist.py`, `present/final_guard.py` |
| G7 evidence gate | `retrieve/evidence_gate.py` |
| G8 extractive fallback | `ground/pipeline.py` (`max_drop_ratio`) |
| G9 source text is data | system prompt + `ground/verify/injection.py` |
| G10 conflicts / overruled | `ground/verify/graph.py` over the citation graph (SCR / INSC / reporter citations resolved at ingest) |
| G11 no answers from memory | G2 + G3 + G6 together |
| G12 verification report | `core/types.VerificationReport` on every `Response` |

Displayed quotes are always the record's own sentences (`verify/quote.source_span`), never the model's copy.

## Storage

SQLite (`core/store.py`): one connection per thread, WAL mode and a busy timeout, so the API's thread pool, the UI and a running ingest can share the database. FTS5 provides BM25; vectors are stored as blobs and searched by brute-force cosine.

## Measured choices

| Choice | Measured on | Result |
|---|---|---|
| Chunking: paragraph groups of ~300 words | 47-scenario benchmark | Best of 150 / 300 / 450 words and one-paragraph chunks (top Article 81%, precedent 89%) |
| Precedent vote not weighted by Article rarity | same | Rarity weighting lowered accuracy (72% -> 64% at the time); removed |
| Second Article shown only within 85% of the first's score | same | Precision of Articles shown 47% -> 66%, one scenario lost |
| Legal-vocabulary gate | 8 out-of-scope questions | 100% refused, no answerable scenario lost |
| Judgments from 2014 onward only | same, 506 vs 384 judgments | Older (2010-2013) reports have noisier OCR and headnote layouts; dropping them raised top Article 72% -> 79% and precedent 77% -> 83% |
| Forum Articles (32, 136, 142, 226...) still vote | same | Excluding them from the vote changed nothing (33 vs 34/47) |
| Verbatim mode by default, LLM opt-in | Ollama timing counters, i5-1335U laptop CPU | `qwen3:1.7b` generates ~9 tokens/s: 45-50 s per drafted answer vs ~2 s verbatim |
| LLM prompt: 3 best sentences per source | same | Prompt 2,050 -> 1,277 tokens; quotes stay verbatim (sentences are substrings of the chunk) |
| Model kept loaded (`keep_alive` 30 min) | same | Avoids a ~15 s reload per answer |
| IDF table built once, at API start, under a lock | Local load test, 8 concurrent | Fresh-server p95 106 s -> 8.8 s |
| Embeddings: `all-minilm`, not `nomic-embed-text` | Embedding speed on the same CPU | ~0.2 s vs ~3 s per passage: ~35 min vs ~7 h for 8,814 passages |
| Dense search: cached unit vectors, stdlib dot products | 8,814 x 384 vectors | ~0.1 s per query, one query embedding shared by both searches; no numpy dependency |
| Dense retrieval off by default | 47-scenario benchmark, BM25 vs BM25 + `all-minilm` (RRF) | 37 vs 36 first Article, 42 vs 41 shown, 1.4 s vs 3.4 s; dense for judgments only: 35. Not adopted |
| Parent expansion, one paragraph each side | same | Precedent applies the Article 39 -> 44/47 (held-out 19 -> 26/30); two paragraphs: no further gain, slower |
| Paragraph starts tolerate a stray bullet / margin letter, and mid-line starts after a sentence end (not after "Art.", "Sec." ...) | 50-judgment gold set | Paragraph count 48/50 -> 50/50; 95 of 384 judgments re-parsed |

## Phase 1 substitutions (deliberate)

| Roadmap | Phase 1 | Upgrade when |
|---|---|---|
| Postgres + Qdrant + Redis + MinIO | SQLite (FTS5 + vectors as blobs), in-process cache, local files | corpus > ~100k chunks or multi-user (Phase 2) |
| Claude + separate judge | Ollama `qwen3:1.7b`; lexical judge by default, `HIL_JUDGE_MODEL` for an LLM judge | a stronger local or hosted model is available |
| bge-m3 + bge-reranker | keyword retrieval + lexical reranker; dense (`all-minilm` via Ollama) measured and not adopted | GPU available |
| LLM multi-query rewrite | statute-alias + lay-to-legal rewrite | eval shows vocabulary misses |
| OCR fallback (Tesseract via PyMuPDF) | built and tested; no judgment in the current corpus needed it | - |
