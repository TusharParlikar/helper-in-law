# Helper in Law

> Describe your client's situation. Get the governing provisions of the Constitution of India and the Supreme Court judgments that apply them, with every statement verified against the official text.

![status](https://img.shields.io/badge/status-Phase%201%20in%20development-orange)
![python](https://img.shields.io/badge/python-3.12-blue)
![llm](https://img.shields.io/badge/LLM-Ollama%20(local)-black)
![license](https://img.shields.io/badge/license-MIT-green)

🎬 **Watch:** [trailer](docs/trailer.mp4) (49 s) · [product walkthrough](docs/product_video.mp4) (62 s, narrated)

> ⚠️ **Not legal advice.** This is a research aid. Always read the cited judgment and verify the current state of the law.

---

## Table of contents

1. [What is this?](#what-is-this)
2. [Why it's different: the grounding guarantee](#why-its-different-the-grounding-guarantee)
3. [Features](#features)
4. [How it works](#how-it-works)
5. [Results](#results)
6. [Project status and roadmap](#project-status-and-roadmap)
7. [Quick start](#quick-start)
8. [Use it](#use-it) (UI, REST API, MCP)
9. [Personalised answers](#personalised-answers)
10. [Project structure](#project-structure)
11. [Configuration](#configuration)
12. [Evaluation](#evaluation)
13. [Development](#development)
14. [Data, licensing and privacy](#data-licensing-and-privacy)
15. [Contributing](#contributing)
16. [License](#license)

---

## What is this?

**Helper in Law** is a retrieval-augmented generation (RAG) system for Indian constitutional research. A lawyer describes a scenario in plain words ("my client was detained without being told why"). It finds:

1. **The constitutional provisions** that govern it, quoted from the **official text** published by the Legislative Department, Government of India, with a link to the exact page of the official PDF.
2. **Supreme Court judgments** that apply those provisions, quoted at the paragraph, with a link to the judgment and the original e-SCR PDF.

It answers **only** from those sources. Every statement carries the exact quote it rests on, machine-verified before display.

**Corpus (built by the ingest commands below):**

| Source | What | Licence |
|---|---|---|
| The Constitution of India [As on 1st May, 2024], Legislative Department | All articles, each linked to its page in the official PDF | Official Government publication |
| Indian Supreme Court Judgments (AWS Open Data, Dattam Labs) | Supreme Court judgments applying key fundamental-rights articles (384 from 2014-2024 in the measured build) | CC-BY-4.0 |

It is exposed three ways, all backed by one core service:

| Interface | For |
|---|---|
| Web UI (Streamlit) | Humans |
| REST API (FastAPI) | Integrations |
| **MCP server** | Claude and other AI agents that can call tools |

---

## Why it's different: the grounding guarantee

LLMs can't be trusted to never make things up, so this project doesn't rely on trust. It enforces a narrower guarantee **in code**:

> Every claim, quote, case name, citation, date and statute section shown to the user is traceable to a specific passage in the indexed corpus, and was machine-verified against that passage before display. If it can't be verified, it isn't shown.

How:

- The LLM **never writes** case names, citations, dates or paragraph numbers. It points to sources by ID, and the renderer fills in the details **from the database**.
- Every claim must carry a **verbatim quote**, checked against the cited paragraph.
- A **second, different model** checks that the quote actually supports the claim.
- Numbers, sections and dates in a claim must appear in the cited text.
- Weak evidence → the system says **"not found"** instead of guessing.
- Too many claims fail verification → it falls back to **quotes only**.
- A response with no citations is rejected by the response model itself.

**What this does *not* guarantee** (the UI says so too):

| Limit | Why |
|---|---|
| Completeness | Retrieval can miss a relevant case |
| Currency | A case may have been overruled after the corpus date |
| Interpretation | A faithful paraphrase can still be a wrong reading of the law |

---

## Features

- 🔎 **Hybrid search**: keyword (BM25) + semantic vectors, fused and reranked
- 📌 **Pinpoint citations** on every answer: case, court, date, paragraph, verbatim quote
- ✅ **Verification report** on every response (claims proposed / verified / dropped)
- 🧭 **Abstains** when the corpus doesn't support an answer
- 📄 **Research report**: one click turns the verified proofs into a structured PDF (situation, summary, governing provisions, analysis, supporting judgments, table of authorities, limits). No proof, no report.
- 📖 **Chat with a judgment**: Q&A scoped to a single case
- 📜 **Statute lookup**: IPC↔BNS, CrPC↔BNSS, Evidence Act↔BSA aware
- 🔗 **Citation treatment** (followed / distinguished / overruled) where available
- 🎛️ **Adaptive answers**: depth, structure, tone, language, citation style
- 🤖 **MCP server**: read-only tools for Claude and other agents

---

## How it works

```
Question
  │
  ▼
Understand  →  Hybrid retrieve  →  Rerank  →  Evidence gate ──► "Not found" (weak evidence)
                                                  │
                                                  ▼
                        Claim extraction (claims + source IDs + verbatim quotes)
                                                  │
                                                  ▼
                        Verification (quote match · entities · entailment · allowlist)
                                                  │
                                                  ▼
                        Verified Claim Set  (style-independent, cacheable)
                                                  │
                                                  ▼
                        Presenter (applies YOUR style; cannot add facts)
                                                  │
                                                  ▼
                        Response + citations + verification report
```

Two stages on purpose:

- **Stage A (content):** decide what is true and supported.
- **Stage B (presentation):** decide how to say it for *this* user. It can only use verified claims.

REST, MCP and the UI all call one function layer (`service.py`). No business logic lives in handlers.

---

## Results

Measured on the live corpus: the **Constitution of India** (all 471 Articles in force, official text as on 1 May 2024, with its official table of contents) and **384 Supreme Court judgments** (2014-2024, 8,946 indexed passages). Two benchmarks of lawyer-style scenarios, each labelled with the Article(s) that govern it, plus 8 out-of-scope questions. Default mode: verbatim passages, keyword search, no LLM. Full write-up: [`eval/reports/phase1.md`](eval/reports/phase1.md); item-by-item status: [`checklist.md`](checklist.md).

**Finding the law**

| Measure | Dev set (47, tuned on) | Held-out set (30, never tuned on) |
|---|---|---|
| Correct Article shown for the situation | **91%** (43/47) | **57%** (17/30) |
| Correct Article is the first one shown | **77%** (36/47) | **50%** (15/30) |
| Articles shown that are on point (precision) | **63%** (43/68) | **50%** (18/36) |
| A cited Supreme Court judgment applies that Article | **94%** (44/47) | **87%** (26/30) |
| Out-of-scope questions refused ("not found", no guessing) | **100%** (8/8) | **100%** (8/8) |
| Median / 95th-percentile answer time | 0.8 s / 1.2 s | 0.6 s / 1.4 s |

Every change was chosen on the dev set; the held-out set only measures. Its first run, before parent expansion and the parser fixes, scored 53% / 47% / 44% / 63% on the four rows above. The remaining dev-to-held-out gap is how much the lay-to-legal vocabulary is fitted to the dev wording. It still never shows an unsupported statement. Every miss is listed in [`eval/reports/scenarios.md`](eval/reports/scenarios.md) and [`eval/reports/scenarios_heldout.md`](eval/reports/scenarios_heldout.md).

**Grounding: what is shown is what the record says**

| Measure | Result |
|---|---|
| Unsupported statements displayed | **0** (dev and held-out, 461 quoted passages across 77 answers) |
| Quotes found verbatim at the cited paragraph | **100%** (284/284 dev, 177/177 held-out), checked independently against the stored text |
| Answers without citations | **0** |
| Fault injection: corrupted claims the verifier blocks | **100%** across 10 corruption types (fake case names, altered numbers, flipped meaning, removed negations, fabricated quotes...) |
| Phase 1 gates (retrieval, abstain, false premise, prompt injection, style invariance) | **11/11 pass** ([`eval/reports/latest.md`](eval/reports/latest.md)) |

**What each part contributes** ([`eval/reports/ablation.md`](eval/reports/ablation.md), dev set, one component off at a time)

| Switched off | First Article correct | Precision | Precedent applies it |
|---|---|---|---|
| Nothing (full system) | 36/47 | 63% | 44/47 |
| Precedent vote (judgments voting for the Articles they apply) | 18/47 | 30% | 44/47 |
| Lay-to-legal vocabulary | 20/47 | 43% | 38/47 |
| IDF weighting in the reranker | 32/47 | 55% | 44/47 |
| Runner-up rule (always show 2 Articles) | 36/47 | 46% | 44/47 |
| Parent expansion (matched paragraphs only) | 36/47 | 63% | 39/47 |
| Legal-vocabulary gate | 36/47 | 63%, but only 5/8 out-of-scope refused | 44/47 |

Dense retrieval (`all-minilm` embeddings fused with BM25) was also measured and not adopted: 36 vs 37 first Article, twice the answer time.

**Structure-aware retrieval (STAIR), measured** ([`eval/reports/stair.md`](eval/reports/stair.md))

STAIR (Kumar et al., IBM, 2026) retrieves by reading a document's table of contents and naming the section that answers the query. The Constitution has an official one (the Arrangement of Articles), now parsed into Parts, chapters, group headings and Article titles. The local model reads it and names up to 3 Articles, with decoding constrained to real Article numbers.

| Finding the Article (dev, 47) | Recall@1 | Recall@3 |
|---|---|---|
| Keyword search over the Constitution | 18/47 | 32/47 |
| STAIR, untrained `qwen3:1.7b` on a laptop CPU | 2/47 | 2/47 |

Fused into the full ranking it only took Articles away (boost 0.2 / 0.4 / 0.6: 36 / 35 / 27 vs 36 first Article) and added ~17 s per question, so it is off by default (`HIL_USE_STAIR`). This matches the paper, where models that were not fine-tuned scored below BM25 (Claude Haiku 4.5: 45.6% vs 59.5%); STAIR's gains come from fine-tuning, planned for a GPU in Phase 2. Adding each Article's table-of-contents path to its indexed text did not help either (36/47, Recall@3 32 -> 31). What the table of contents did give: it exposed 15 Articles in force that the parser had missed (5, 36, 131, 132, 323, 331-334, 395...), now recovered, and every Article page shows where it sits ("PART III — FUNDAMENTAL RIGHTS › Right to Freedom").

**Engineering checks**

| Check | Result |
|---|---|
| Parser gold set, 50 judgments checked against their PDFs ([`eval/reports/parse_audit.md`](eval/reports/parse_audit.md)) | 100% citation, neutral citation, date, bench and paragraph count |
| Parser audit, all 384 judgments | 99% complete metadata, 100% paragraphs numbered 1..N, 3 headnote leaks, median 99% of text captured |
| Constitution coverage | 471/471 Articles listed in the official Arrangement of Articles, each with its Part, chapter and group heading |
| OCR | Pages without a text layer are OCRed with Tesseract; tested on a real image-only PDF |
| Local load test, 120 requests, 8 concurrent, fresh server | 0 errors; p50 1.8 s, p95 9.5 s (8 uncached questions share one CPU-bound process); one user at a time: ~2 s |
| MCP server | Verified end to end over stdio and Streamable HTTP with the official MCP Python client (`tests/test_mcp_protocol.py`); `make inspector` opens the MCP Inspector |
| Test suite | 99 passing |

**Intensive testing** ([`eval/reports/campaign.md`](eval/reports/campaign.md), `make eval-campaign`)

Every response below was re-checked independently against the stored text: each displayed statement must be entailed by its quote, and each quote must sit verbatim at its cited paragraph.

| Test | Result |
|---|---|
| Responses checked (77 scenarios + 68 out-of-scope questions x 18 answer styles, plus rewrites and attacks) | **3,380** |
| Unsupported statements displayed | **0** (95% upper bound 0.09% of responses) |
| Citations verbatim at the cited paragraph | **11,403 / 11,403** |
| Same question, same answer (137 questions, 3 processes with different hash seeds) | **identical every time** |
| Style invariance: same evidence for every structure and tone; Brief ⊆ Standard ⊆ Detailed | **145 / 145** |
| Corrupted claims blocked (10 fault types on real answers) | **3,736 / 3,744** (99.8%) |
| Prompt attacks resisted (fake repeal, "no citations", "skip verification", invented precedent, "no disclaimer") | **385 / 385** |
| Off-topic / foreign-law / non-constitutional questions refused | 37/38 · 14/15 · 9/15 |
| Hostile inputs: REST API (41) / MCP tool calls (21) | 0 server errors / 0 crashes |

| The situation rewritten as... | First Article correct (clean text: 51/77) |
|---|---|
| lower case / no punctuation | 51 / 50 |
| with typos (every 7th long word) | 43 |
| wrapped in chat ("Sir, urgent query... Kindly advise") / a second wording | 49 / 50 |

The 8 corrupted claims not blocked: 6 changed footnote markers glued to a word ("Kedar Nath Singh2" -> "Singh4", not a fact of the text), 1 quote swap where the other source holds the same sentence, and 1 added conclusion ("...and the accused must therefore be acquitted") that the lexical judge misses; a model judge is planned (Phase 2). Attacks never put their claim on screen, but they do pull retrieval off course: with "Article 21 has been repealed" or a Kesavananda request appended, the first Article is right 38/77 and 37/77 times (51 clean). Non-constitutional Indian-law questions (stamp duty, GST, gratuity) are often answered with the nearest constitutional provision rather than refused.

The first run of this campaign found real bugs, all fixed and re-measured above:

| Found | Before | After |
|---|---|---|
| Same question gave different Articles in different processes (precedent vote iterated a set) | nondeterministic | identical across seeds |
| Changed dates and clause numbers passed the verifier (numbers compared as sets; "twenty-four" read as 20 and 4) | 273/300 altered numbers blocked | all except glued footnote markers |
| Chatty wrapping crowded out the facts ("query", "kindly" outranked "custody") | 25/77 first Article correct | 49/77 |
| One everyday word ("water", "old") let off-topic questions through | 34/38 refused | 37/38 |
| Foreign-law questions answered with Indian Articles | 3/15 refused | 14/15 |
| A docket number ("S247278") could be altered unnoticed | not checked | checked |

**Read these numbers honestly**

- The scenario labels are standard constitutional law written by the developer and **have not yet been reviewed by a lawyer**.
- The samples are small (47 + 30). With 0 unsupported statements in 77 answers, the 95% upper bound on the true rate is about 4%.
- With the LLM on (Ollama `qwen3:1.7b`, CPU only) an answer takes about 45-50 s once the model is loaded. The prompt carries only the three best-matching sentences per source (2,050 -> 1,277 tokens), but generation runs at about 9 tokens/s on a laptop CPU, so the 10-second target needs a GPU or a hosted model. Verbatim mode, the default everywhere, meets it.
- 384 judgments is a small corpus; a scenario whose leading precedent is not in it can still get the right Article but weaker case support.

Reproduce: `uv run python eval/run_scenarios.py [--heldout]`, `eval/run_ablation.py`, `eval/run_parse_audit.py`, `eval/run_campaign.py`, `eval/run_stair.py`, and `eval/load_test.py` against a local API. Building them found and fixed real bugs: report citations such as "[1993] 2 SCR 581" being misread as paragraph numbers, a slow quote matcher, off-topic questions matching common words, paragraphs merged when a scan put a bullet or margin letter before the number, HTTP 500s from a shared SQLite connection under concurrent requests, and a 106-second cold start from every first request rebuilding the same index statistics.

---

## Project status and roadmap

| Phase | Goal | Status |
|---|---|---|
| **1. Build it for real** | Full pipeline, grounded answers, adaptive style, API + UI + **MCP**. **No auth** (single-user, localhost) | ✅ Complete ([report](eval/reports/phase1.md), [what remains](checklist.md#what-remains-in-phase-1)) |
| **2. Production-ready** | Auth (OAuth 2.1), scale, observability, automated data refresh, compliance, deployment | ⏳ Planned ([plan](docs/phase2.md)) |
| **3. Intensive testing** | Red-team, hallucination campaign, expert review, MCP conformance, load/chaos, pen-test | ⏳ Planned ([plan](docs/phase3.md)) |

Phase 1 checklist:

- [x] M1 Foundations (uv, ruff, mypy, pytest, pre-commit, Makefile, licence log; CI deferred)
- [x] M2 Ingestion (quality gate, cleaner, idempotent, dead-letter queue)
- [x] M3 Parsing and structure (metadata, paragraphs, sections, statutes + aliases, citation treatment)
- [x] M4 Indexing (paragraph-bounded chunks, FTS5, Ollama embeddings, versioned)
- [x] M5 Retrieval (understand, alias rewrite, hybrid RRF, rerank, evidence gate)
- [x] M6 Grounded generation and verification (claims by source id, verification suite, extractive fallback)
- [x] M7 Adaptive presentation (profiles, overrides, presenter, final guard, translation)
- [x] M8 API + UI
- [x] M9 MCP server (stdio + Streamable HTTP, localhost)
- [x] M10 Tests, fault injection, evaluation report ([`eval/reports/latest.md`](eval/reports/latest.md))

Phase 1 runs on real, openly licensed sources: the official Constitution of India and Supreme Court judgments from the CC-BY-4.0 open dataset (see [`docs/licence-log.md`](docs/licence-log.md)). The fictional sample corpus in `data/sample/` is used only by the test suite. Deliberate Phase 1 substitutions (SQLite for Postgres/Qdrant, Ollama for hosted models) are listed in [`docs/architecture.md`](docs/architecture.md).

Full plan: [`docs/ROADMAP.md`](docs/ROADMAP.md).

> **Phase 1 has no authentication.** It is designed to run on your own machine and binds to `127.0.0.1` by default. **Do not expose it to the internet.**

---

## Quick start

**Prerequisites:** Python 3.12, [`uv`](https://docs.astral.sh/uv/), [Ollama](https://ollama.com) running locally. No Docker needed in Phase 1.

```bash
# 1. Clone
git clone https://github.com/TusharParlikar/helper-in-law.git
cd helper-in-law

# 2. Install dependencies (add --extra pdf for PDFs, --extra ui for Streamlit)
uv sync --extra ui

# 3. Pull the local models
ollama pull qwen3:1.7b
ollama pull all-minilm   # embeddings; nomic-embed-text is better but ~12x slower on CPU

# 4. Configure (optional; defaults work)
cp .env.example .env

# 5. Ingest the sample corpus, then build the index
uv run python -m helperinlaw.ingest --constitution --sci 2014-2024 --limit 150
uv run python -m helperinlaw.index build

# 6. Run
uv run python -m helperinlaw.api        # REST API on 127.0.0.1:8000
uv run streamlit run ui/app.py --server.address 127.0.0.1  # Web UI
uv run python -m helperinlaw.mcp_server # MCP (stdio)
```

Without Ollama the system still works: retrieval falls back to BM25 and answers are verbatim extractive quotes (the default). Set `HIL_USE_LLM=true` for model-drafted analysis.

---

## Use it

### Web UI

Open the Streamlit URL, ask a question, and click any citation to see the highlighted paragraph in the source judgment.

**Hosted demo for clients:** deploy the same UI on Streamlit Community Cloud, private to invited emails, with the corpus shipped in the repo. Steps: [`docs/deploy-streamlit.md`](docs/deploy-streamlit.md).

### REST API

```bash
curl -s http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
        "question": "What are the grounds for refusing bail under Section 439 CrPC?",
        "filters": {"court": "SC", "year_from": 2010},
        "style": {"depth": "standard", "structure": "irac"}
      }'
```

| Endpoint | Purpose |
|---|---|
| `POST /ask` | Grounded Q&A with citations |
| `POST /search` | Search judgments |
| `GET /cases/{id}` | Case metadata and structured sections |
| `GET /cases/{id}/paragraphs/{n}` | Exact paragraph text |
| `POST /cases/{id}/chat` | Q&A scoped to one case |
| `GET/PUT /profile` | Read or update your style profile |
| `POST /feedback` | 👍/👎 on an answer |

Every `/ask` response includes `answer_blocks`, `citations`, `verification`, `coverage`, `confidence` and a disclaimer.

### MCP server

Use the tools from Claude Desktop, Claude Code, or any MCP client. All tools are **read-only**, and results are always the verified response object.

| Tool | What it does |
|---|---|
| `search_judgments` | Search with filters; max 20 results |
| `ask_legal_question` | Grounded answer with citations and verification |
| `get_judgment` | Metadata and structured sections |
| `get_paragraph` | Exact paragraph text (max 10) |
| `find_citing_cases` | Cases citing a judgment, with treatment |
| `lookup_statute` | Statute plus IPC↔BNS mapping and top cases |
| `get_constitution_article` | Official text of an Article, its official PDF page, and judgments applying it |
| `get_profile` / `set_style` | Read or override answer style |

**Claude Code (stdio):**

```bash
claude mcp add helper-in-law -- uv run --directory /path/to/helper-in-law python -m helperinlaw.mcp_server
# Streamable HTTP (localhost only): uv run python -m helperinlaw.mcp_server --http --port 8765
```

**Claude Desktop (`claude_desktop_config.json`):**

```json
{
  "mcpServers": {
    "helper-in-law": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/helper-in-law", "python", "-m", "helperinlaw.mcp_server"]
    }
  }
}
```

Test with the [MCP Inspector](https://github.com/modelcontextprotocol/inspector) before connecting a client.

---

## Personalised answers

On first run you're asked **"How do you like your answers?"** (skippable, editable anytime).

| Setting | Options |
|---|---|
| Depth | Quick · Standard · Deep |
| Structure | Bullets · Paragraphs · IRAC · Research memo · Case table |
| Tone | Technical · Plain English · Explain like I'm new |
| Language | English · Hindi (quotes stay in the original) |
| Citation style | Case name + SCC/AIR · Neutral · Inline paragraph · Footnotes |
| Quotes | Always · On hover · On request |
| Contrary authority | Always · If found · Never |
| Jurisdiction focus | SC only · Specific High Court · All |

You can also override per question in plain language: *"shorter"*, *"as a table"*, *"explain simply"*.

**Hard boundary:** preferences change **presentation only**. Citations, verification, abstaining on weak evidence and the disclaimer cannot be switched off. Even "Quick" mode shows citations.

---

## Project structure

```
helper-in-law/
├── data/sample/          # fictional test judgments
├── docs/                 # architecture, runbooks, ROADMAP.md, licence-log.md
├── src/helperinlaw/
│   ├── core/             # config, logging, shared types
│   ├── ingest/           # downloaders, extraction, cleaning
│   ├── parse/            # metadata, structure, statutes, citations
│   ├── index/            # chunking, embeddings, Qdrant
│   ├── retrieve/         # query understanding, hybrid search, rerank, evidence gate
│   ├── ground/           # claim extraction, verification suite, citation rendering
│   ├── present/          # style profiles, presenter, final guard, translation
│   ├── service.py        # the single core API used by REST, MCP and UI
│   ├── api/              # FastAPI adapter
│   ├── mcp_server/       # MCP adapter
│   └── workers/          # background jobs
├── ui/                   # Streamlit app
├── eval/                 # datasets, fault injection, evaluation runner, reports
├── tests/                # unit, integration, e2e, MCP smoke tests
└── .env.example
```

---

## Configuration

Set in `.env` (see `.env.example`). All variables use the `HIL_` prefix.

| Variable | Purpose | Default |
|---|---|---|
| `HIL_DB_PATH` | SQLite database | `data/helperinlaw.db` |
| `HIL_OLLAMA_URL` | Ollama server | `http://localhost:11434` |
| `HIL_LLM_MODEL` | Claim extraction and translation | `qwen3:1.7b` |
| `HIL_JUDGE_MODEL` | Entailment judge (must differ from the answer model); empty = deterministic lexical judge | empty |
| `HIL_EMBED_MODEL` | Embeddings (must match the model the index was built with) | `all-minilm` |
| `HIL_USE_LLM` | Let the local model draft the analysis (every statement still verified) | `false` |
| `HIL_USE_DENSE` | Use embeddings when the index has them (BM25 alone otherwise) | `true` |
| `HIL_USE_STAIR` | STAIR: the local model reads the Constitution's table of contents and votes for Articles ([measured](eval/reports/stair.md); off until a fine-tuned model beats keyword search) | `false` |
| `HIL_INDEX_VERSION` | Index version served | `v1` |
| `HIL_EVIDENCE_MIN_SCORE` | Below this, the system abstains | `0.5` |
| `HIL_BIND_HOST` | Server bind address | `127.0.0.1` |

---

## Evaluation

Quality is measured, not assumed. Datasets live in `eval/datasets/`:

| Set | Purpose |
|---|---|
| Retrieval | Recall@k, MRR |
| Answers | Faithfulness and correctness |
| Unanswerable | Must abstain |
| False-premise | Must not accept wrong premises |
| Adversarial | Prompt-injection and safety |
| Parser gold | Extraction accuracy |
| Scenarios | Lawyer-style situations labelled with the governing Article(s); out-of-scope questions |

```bash
uv run python eval/run_eval.py              # Phase 1 gates on the sample set
uv run python eval/run_eval.py --llm --dense  # the same, with Ollama
uv run python eval/run_scenarios.py         # scenario benchmark on the live corpus (see Results)
```

**Phase 1 exit targets** include: Recall@10 ≥ 0.85, **0 unsupported claims displayed**, **0 responses without citations**, citation accuracy ≥ 0.99, 100% pass on the adversarial set.

Note on "0": it is measured on test sets. With 0 failures in *n* trials, the 95% upper bound on the true failure rate is about 3/*n*, so results are reported with that bound.

---

## Development

```bash
uv run ruff check .          # lint
uv run ruff format .         # format
uv run mypy src              # type-check (strict on core + ground/)
uv run pytest                # tests
```

Code standards:

- Typed, documented code: docstrings on public functions, comments that explain **why**, not what.
- Anything touching the verification suite needs adversarial unit tests.
- No logic in API/MCP handlers; put it in `service.py` or below.
- Prompts, models and chunker settings are versioned; changes must pass the eval suite.

---

## Data, licensing and privacy

- **Source terms:** every data source must be recorded in [`docs/licence-log.md`](docs/licence-log.md) (URL, terms, date accessed). Confirm you are allowed to store and serve the text before any public deployment.
- **Personal data:** judgments can contain sensitive personal data (e.g. minors, victims, matrimonial and sexual-offence matters). Do not attempt to de-anonymise anonymised judgments. Privacy handling for public deployment (Phase 2) must be reviewed against India's DPDP Act with qualified advice.
- **No data leaves your machine** in Phase 1: the LLM and embeddings run locally in Ollama.

---

## Contributing

1. Open an issue before large changes.
2. Branch from `main`; keep PRs small.
3. Run lint, type-check, tests and the relevant eval suite.
4. Any change to retrieval, prompts or verification must include eval results.
5. Found a wrong or unsupported answer? Open an issue with the question and response; it becomes a regression test.

---

## License

MIT (see `LICENSE`). Note: this covers the **code only**. Court judgment data has its own terms; see the data section above.

---

## Acknowledgements

Inspired by the product category of Indian legal-tech case search. Built on open tooling: FastAPI, SQLite FTS5, Ollama, Streamlit and the Model Context Protocol.
