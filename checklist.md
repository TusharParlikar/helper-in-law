# Phase 1 checklist

Tracks every Phase 1 item in [`docs/ROADMAP.md`](docs/ROADMAP.md) (§6 milestones, §7 exit criteria). `[x]` done; `[ ]` not done or only partly done, with the reason. Deliberate substitutions are listed in [`docs/architecture.md`](docs/architecture.md).

## M1 Foundations

- [x] Repo, `uv`, ruff, mypy (strict on core + verification), pytest, pre-commit, Makefile
- [x] Storage stack: SQLite (FTS5 + vectors) in place of Docker Compose Postgres / Qdrant / Redis / MinIO (deliberate Phase 1 substitution)
- [x] `pydantic-settings` (`HIL_` prefix), JSON structured logging
- [x] [`docs/licence-log.md`](docs/licence-log.md) for every data source
- [ ] Eval questions written before retrieval code: the 30-question set (`eval/datasets/retrieval.jsonl`) exists, but it was committed just after the retrieval module, not before

## M2 Ingestion

- [x] Downloaders for the official Constitution PDF and the Supreme Court open dataset: resumable, idempotent, cached by file
- [x] Extraction with a quality score
- [x] OCR fallback: pages without a text layer are OCRed with Tesseract (via PyMuPDF); without Tesseract they fall through to the quality gate and the dead-letter table (`tests/test_ingest.py::test_scanned_page_is_ocred`)
- [x] Cleaner (headers, footers, hyphenation, banners, footnotes)
- [x] Dead-letter table + failure reasons
- [x] **Exit:** 100% of the target corpus processed or logged as failed

## M3 Parsing and structure

- [x] Metadata: title, parties, date, bench, case no., SCR and neutral citations
- [x] Paragraph segmentation with numbers (incl. 2024 layout, paragraph 1 on the author line, unnumbered paragraph 1)
- [x] Section labels (facts / issues / arguments / reasoning / holding)
- [x] Statute extraction + IPC↔BNS, CrPC↔BNSS, Evidence↔BSA aliases
- [x] Case→case citation extraction with treatment (SCR / INSC / reporter citations resolved)
- [x] **Exit:** 50-judgment gold set (`eval/datasets/gold_parse_real.jsonl`), labels from each judgment's PDF, disagreements reviewed by hand: 100% citation, neutral citation, date, bench, paragraph count ([`parse_audit.md`](eval/reports/parse_audit.md)). Building it found and fixed two paragraph bugs and a metadata gap

## M4 Indexing

- [x] Structure-aware chunker (~300 words, paragraph-bounded, context prefix; size chosen by measurement)
- [x] Embeddings, versioned and resumable (`all-minilm` via Ollama; CPU, no GPU, so not bge-m3). Measured against keyword-only on the dev set: not better for Articles (36 vs 37 first Article), so served off by default
- [x] Vector store: SQLite blobs with cached in-memory search (in place of Qdrant)
- [x] Side-by-side `index_version` rebuild command + [reindex runbook](docs/runbooks/reindex.md)

## M5 Retrieval

- [x] Query understanding → filters (court, years, statutes, Articles)
- [x] Query rewrite: statute aliases + lay-to-legal vocabulary (rule-based, not LLM multi-query)
- [x] Hybrid + RRF (BM25 + dense)
- [x] Structure-aware retrieval (STAIR) over the Constitution's official table of contents: built and measured; untrained it lowered accuracy, so it is off by default ([`stair.md`](eval/reports/stair.md))
- [x] Rerank: lexical, IDF-weighted (cross-encoder needs a GPU)
- [x] Parent expansion: each judgment passage gets its neighbouring paragraphs (precedent support 39 -> 44/47 dev, 19 -> 26/30 held-out)
- [x] Authority / recency boosts (profile-aware)
- [x] Evidence gate tuned on the unanswerable and out-of-scope sets (100% refused)
- [x] **Eval gate:** Recall@10 ≥ 0.85 (1.0 on the retrieval set)

## M6 Grounded generation

- [x] Claim-extraction prompt + strict JSON schema
- [x] Verification suite (§4.4), each check unit-tested with adversarial fixtures
- [x] ID-based citation rendering from the database (G1)
- [x] Extractive fallback + abstain paths
- [x] Response model validator (no answer without citations)
- [x] **Exit:** 0 unsupported claims displayed (sample gates, 47 dev + 30 held-out real scenarios)

## M7 Adaptive presentation

- [x] Profile schema + storage + versioning
- [x] Onboarding flow with live preview (UI dialog)
- [x] Natural-language override parser → style patch
- [x] Presenter stage + final guard
- [x] Translation path (quotes untouched)
- [x] Feedback capture + "suggest a setting"
- [x] **Exit:** same question under ≥8 profiles → identical verified claims (automated test, 100%)

## M8 API + UI

- [x] `POST /ask`, `/search`, `GET /cases/{id}`, `/cases/{id}/paragraphs/{n}`, `POST /cases/{id}/chat`, `GET/PUT /profile`, `POST /feedback`
- [x] No auth: single-user, binds to `127.0.0.1`, `profile_id` selects the style profile
- [x] Streamlit UI: scenario research, filters, sources with paragraph links, verification badge, limits notice, settings, Constitution lookup, PDF report (only when there is proof), mobile layout

## M9 MCP server

- [x] Official Python SDK; stdio + Streamable HTTP (localhost, no auth)
- [x] Tools: `search_judgments`, `ask_legal_question`, `get_judgment`, `get_paragraph`, `find_citing_cases`, `lookup_statute`, `get_constitution_article`, `get_profile`, `set_style`
- [x] Resources: `judgment://{case_id}`, `statute://{act}/{section}`
- [x] Prompts: research memo, find contrary authority
- [x] Safety rules: verified response objects only, citations in every claim, size caps, source text labelled as quoted, clear descriptions
- [ ] Verified with MCP Inspector and a real client: verified with the official MCP Python client over stdio and Streamable HTTP (`tests/test_mcp_protocol.py`). Inspector: run `make inspector` (needs Node.js; not run here because it downloads and executes npm code)
- [ ] MCP smoke tests in CI: CI deferred by decision (the tests run locally)

## M10 Hardening

- [x] Unit / integration tests (103), parser golden tests, verification fault-injection tests (10 corruption types; 3,741/3,741 blocked on real answers), intensive campaign ([`campaign.md`](eval/reports/campaign.md)), 54 criminal-lawyer questions ([`criminal.md`](eval/reports/criminal.md))
- [x] Baseline load test (local): 0 errors, warm p95 2.3 s, fresh-server p95 8.8 s
- [x] README, architecture doc, reindex runbook
- [x] Phase 1 evaluation report with ablation table ([`phase1.md`](eval/reports/phase1.md), [`ablation.md`](eval/reports/ablation.md))

## §7 Exit criteria

| Metric | Target | Result | Pass |
|---|---|---|---|
| Recall@10 (retrieval set) | ≥ 0.85 | 1.0 | [x] |
| MRR | ≥ 0.60 | 0.983 | [x] |
| Unsupported claims displayed | 0 | 0 (sample gates, 47 dev, 30 held-out) | [x] |
| Citation accuracy | ≥ 0.99 | 1.0 (284/284 dev, 177/177 held-out) | [x] |
| Responses lacking citations | 0 | 0 | [x] |
| Abstain correctness on unanswerables | ≥ 0.90 | 1.0 (and 8/8 out-of-scope) | [x] |
| Prompt-injection pass rate | 100% | 100% | [x] |
| Style invariance | 100% | 100% | [x] |
| MCP tools pass Inspector + real-client check | all | official Python client only | [ ] |
| p95 `/ask` latency | ≤ 10 s | 2.3 s warm, 8.8 s fresh (verbatim default); 45-50 s with the LLM on | [x] |
| Parser accuracy | ≥ 0.95 | 100% on the 50-judgment real gold set and the sample gold set; 99-100% automated audit on 384 judgments | [x] |

Recall@10 and MRR are measured on the retrieval set over the sample corpus. On real scenarios the correct Article is shown for 91% (dev) and 57% (held-out) of situations, and a cited judgment applies it in 94% and 87%; see [`phase1.md`](eval/reports/phase1.md).

## What remains in Phase 1

Phase 1 is complete in code. These items stay open; none needs new code except as noted.

| Item | Why it is open | How to close it | Who |
|---|---|---|---|
| MCP Inspector run | It downloads and runs code from npm, which was not run here | `make inspector` (needs Node.js), then check tools/list, each tool, resources, prompts and an error path | You |
| Real-client check (Claude Desktop / Claude Code) | Needs the client's config on your machine | Add `uv run python -m helperinlaw.mcp_server` as a stdio server; ask one question and one Constitution lookup | You |
| Lawyer review of the scenario labels | The 77 benchmark labels were written by the developer | An advocate or senior law student checks each scenario's governing Article(s) in `eval/datasets/scenarios*.jsonl`; disagreements are fixed and the benchmarks re-run | A lawyer |
| LLM mode within 10 s | `qwen3:1.7b` on a laptop CPU generates ~9 tokens/s (45-50 s per answer) | Run on a GPU or a stronger local machine; nothing to change in code. Verbatim mode, the default, already meets 10 s | Hardware |
| Eval questions before retrieval code | Historical: the set was committed 16 minutes after the retrieval module | Cannot be changed; the held-out set (written after tuning, never tuned on) covers the same concern | - |
| MCP smoke tests in CI | CI is deferred by decision | Phase 2, W6, when you say | You |

Done since the first checklist: dense retrieval measured (not adopted), parent expansion, 50-judgment parser gold set, OCR fallback.

Next: [Phase 2 plan](docs/phase2.md) · [Phase 3 plan](docs/phase3.md).
