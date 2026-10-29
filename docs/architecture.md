# Architecture (Phase 1)

One core (`src/helperinlaw/service.py`), three thin adapters: REST (`api/`), MCP (`mcp_server/`), Streamlit (`ui/`). No logic lives in handlers.

## Corpus

| Source | Ingest | Stored as |
|---|---|---|
| The Constitution of India [As on 1st May, 2024], Legislative Department (official PDF) | `ingest/official.py`: English pages only, footnotes and running headers removed, one record per Article in force (the 471 listed in the official Arrangement of Articles); the Arrangement itself parsed into a table of contents (Part, chapter, group heading, title) | `coi-<article>` documents, one paragraph each, linked to the exact PDF page; `toc` table |
| Supreme Court judgments, Indian Supreme Court Judgments open dataset (CC-BY-4.0) | `ingest/sci.py`: per-year metadata tar, headnotes filtered for key Articles, PDF fetched, only the Court's own numbered paragraphs kept (editorial headnotes dropped) | `sc-<neutral citation>` documents with paragraphs, statutes and the citation graph |
| Fictional sample judgments | `ingest/pipeline.py` | Used by the test suite only |

Every ingest is idempotent and resumable; a document that cannot be parsed goes to the `dead_letter` table with its reason, never silently.

## Answering a question

```
situation / question
  -> retrieve/understand     filters, statutes, Articles, case names
  -> retrieve/evidence_gate  a foreign jurisdiction ("in California", "English law") -> declined,
                             Indian law only; no legal word and fewer than two lay words ->
                             "not found" (off-topic questions)
  -> retrieve/rewrite        statute aliases (IPC<->BNS ...) + lay-to-legal terms
                             ("not told why" -> "informed of the grounds", "lawyer" -> "legal practitioner")
  -> retrieve/hybrid         BM25 (SQLite FTS5) [+ dense if embeddings exist], RRF fusion,
                             run separately for Constitution articles and for judgments
  -> retrieve/rerank         IDF-weighted coverage of the situation's most informative words,
                             synonym groups, statute match, profile boosts
  -> ground/pipeline         judgments (max 2 passages each) vote for the Articles they apply;
                             [retrieve/stair, opt-in: the local model reads the Constitution's
                             table of contents and votes for up to 3 Articles, decoding
                             constrained to real Article numbers];
                             evidence gate; parent expansion (each judgment passage + its
                             neighbouring paragraphs)
  -> ground/claim_extract    the governing Article's best clause + verbatim judgment sentences
                             (or, with the LLM on, structured claims citing sources by id)
  -> ground/verify           quote exists (exact, then word-aligned fuzzy), numbers/sections/dates/
                             docket numbers in the quote in the same order, entailment + negation scope, allowlist, injection, role check,
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

SQLite (`core/store.py`): one connection per thread, WAL mode and a busy timeout, so the API's thread pool, the UI and a running ingest can share the database. FTS5 provides BM25; vectors are stored as blobs and searched by brute-force cosine. The `toc` table holds the Constitution's table of contents in official order, used by STAIR.

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
| STAIR (table-of-contents retrieval) off by default | 47-scenario benchmark, [`eval/reports/stair.md`](../eval/reports/stair.md) | Untrained `qwen3:1.7b` reading the official table of contents named the right Article first 2/47 times (keyword search: 18/47); fused into the ranking it cost Articles (boost 0.2 / 0.4 / 0.6: 36 / 35 / 27 vs 36 first Article) and ~17 s per question. Matches the paper: untrained models fall below BM25. Kept behind `HIL_USE_STAIR` for a fine-tuned model |
| Article search text without the table-of-contents path | same | Adding "PART III — FUNDAMENTAL RIGHTS › Right to Freedom" to each Article's indexed text: full system unchanged (36/47), keyword-only Recall@3 32 -> 31. Not adopted |
| Article headings: resume after a rejected match; footnotes only with footnote-sized numbers | The official Arrangement of Articles | 15 Articles in force were missing (5, 36, 131, 132, 323, 331-334, 371I, 395...); now 471/471 present, omitted stubs dropped |
| Claim numbers matched in order, compound number words ("twenty-four" = 24), docket identifiers counted | Intensive campaign, fault injection on real answers | Altered dates and clause numbers had passed (sets let "27" match elsewhere in the quote); blocked faults 4,017/4,047 -> 3,736/3,744 on claims that pass as they are |
| Precedent vote iterates judgments in rank order | Same 137 questions in processes with different hash seeds | A set's order made tied Articles swap between runs; now identical |
| Conversational words are stop words | Scenarios wrapped in chat | "query", "kindly", "urgent" have higher IDF than "custody" and took the reranker's slots: 25 -> 49/77 first Article correct wrapped; dev unchanged |
| Gate: one legal word or two lay words; foreign jurisdictions declined | 60 new out-of-scope questions | Off-topic 34 -> 37/38, foreign law 3 -> 14/15 refused; none of the 77 scenarios refused |

## Phase 1 substitutions (deliberate)

| Roadmap | Phase 1 | Upgrade when |
|---|---|---|
| Postgres + Qdrant + Redis + MinIO | SQLite (FTS5 + vectors as blobs), in-process cache, local files | corpus > ~100k chunks or multi-user (Phase 2) |
| Claude + separate judge | Ollama `qwen3:1.7b`; lexical judge by default, `HIL_JUDGE_MODEL` for an LLM judge | a stronger local or hosted model is available |
| bge-m3 + bge-reranker | keyword retrieval + lexical reranker; dense (`all-minilm` via Ollama) measured and not adopted | GPU available |
| LLM multi-query rewrite | statute-alias + lay-to-legal rewrite | eval shows vocabulary misses |
| OCR fallback (Tesseract via PyMuPDF) | built and tested; no judgment in the current corpus needed it | - |
