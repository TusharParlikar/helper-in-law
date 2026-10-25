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
5. [Project status and roadmap](#project-status-and-roadmap)
6. [Quick start](#quick-start)
7. [Use it](#use-it) (UI, REST API, MCP)
8. [Personalised answers](#personalised-answers)
9. [Project structure](#project-structure)
10. [Configuration](#configuration)
11. [Evaluation](#evaluation)
12. [Development](#development)
13. [Data, licensing and privacy](#data-licensing-and-privacy)
14. [Contributing](#contributing)
15. [License](#license)

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
| Indian Supreme Court Judgments (AWS Open Data, Dattam Labs) | Supreme Court judgments applying key fundamental-rights articles (default: 150 from 2014-2024) | CC-BY-4.0 |

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

## Project status and roadmap

| Phase | Goal | Status |
|---|---|---|
| **1. Build it for real** | Full pipeline, grounded answers, adaptive style, API + UI + **MCP**. **No auth** (single-user, localhost) | 🚧 In progress |
| **2. Production-ready** | Auth (OAuth 2.1), scale, observability, automated data refresh, compliance, deployment | ⏳ Planned |
| **3. Intensive testing** | Red-team, hallucination campaign, expert review, MCP conformance, load/chaos, pen-test | ⏳ Planned |

Phase 1 checklist:

- [x] M1 Foundations (uv, ruff, mypy, pytest, pre-commit, Makefile, CI, licence log)
- [x] M2 Ingestion (quality gate, cleaner, idempotent, dead-letter queue)
- [x] M3 Parsing and structure (metadata, paragraphs, sections, statutes + aliases, citation treatment)
- [x] M4 Indexing (paragraph-bounded chunks, FTS5, Ollama embeddings, versioned)
- [x] M5 Retrieval (understand, alias rewrite, hybrid RRF, rerank, evidence gate)
- [x] M6 Grounded generation and verification (claims by source id, verification suite, extractive fallback)
- [x] M7 Adaptive presentation (profiles, overrides, presenter, final guard, translation)
- [x] M8 API + UI
- [x] M9 MCP server (stdio + Streamable HTTP, localhost)
- [x] M10 Tests, fault injection, evaluation report ([`eval/reports/latest.md`](eval/reports/latest.md))

Phase 1 runs on a **fictional sample corpus** (`data/sample/`, 8 judgments written for testing). Swapping in a real corpus needs a licensed source; see [`docs/licence-log.md`](docs/licence-log.md). Deliberate Phase 1 substitutions (SQLite for Postgres/Qdrant, Ollama for hosted models) are listed in [`docs/architecture.md`](docs/architecture.md).

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
ollama pull nomic-embed-text

# 4. Configure (optional; defaults work)
cp .env.example .env

# 5. Ingest the sample corpus, then build the index
uv run python -m helperinlaw.ingest --constitution --sci 2014-2024 --limit 150
uv run python -m helperinlaw.index build

# 6. Run
uv run python -m helperinlaw.api        # REST API on 127.0.0.1:8000
uv run streamlit run ui/app.py          # Web UI
uv run python -m helperinlaw.mcp_server # MCP (stdio)
```

Without Ollama the system still works: retrieval falls back to BM25 and answers to verbatim extractive quotes (`HIL_USE_LLM=false`, `HIL_USE_DENSE=false`).

---

## Use it

### Web UI

Open the Streamlit URL, ask a question, and click any citation to see the highlighted paragraph in the source judgment.

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
| `HIL_EMBED_MODEL` | Embeddings | `nomic-embed-text` |
| `HIL_USE_LLM` / `HIL_USE_DENSE` | Turn the LLM / embeddings off (extractive, BM25) | `true` |
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

```bash
uv run python eval/run_eval.py              # offline gates
uv run python eval/run_eval.py --llm --dense  # with Ollama
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
