# Helper in Law

> Citation-first research over Indian court judgments. Every claim shown is verified against the source text, and answers adapt to how you like to read them.

![status](https://img.shields.io/badge/status-Phase%201%20in%20development-orange)
![python](https://img.shields.io/badge/python-3.12-blue)
![license](https://img.shields.io/badge/license-MIT-green)

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

**Helper in Law** is a retrieval-augmented generation (RAG) system for Indian court judgments. You ask a legal research question; it finds the relevant judgments, and answers **only** from what it found, with a pinpoint citation (case, court, date, paragraph) and the exact quote behind every statement.

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

- [ ] M1 Foundations (repo, Docker Compose, CI basics)
- [ ] M2 Ingestion
- [ ] M3 Parsing and structure
- [ ] M4 Indexing
- [ ] M5 Retrieval
- [ ] M6 Grounded generation and verification
- [ ] M7 Adaptive presentation
- [ ] M8 API + UI
- [ ] M9 MCP server
- [ ] M10 Hardening and evaluation report

Full plan: [`docs/ROADMAP.md`](docs/ROADMAP.md).

> **Phase 1 has no authentication.** It is designed to run on your own machine and binds to `127.0.0.1` by default. **Do not expose it to the internet.**

---

## Quick start

> The commands below describe the intended Phase 1 layout. They will work as milestones land; the checklist above shows what exists today.

**Prerequisites:** Python 3.12, [`uv`](https://docs.astral.sh/uv/), Docker, an Anthropic API key. A GPU is strongly recommended for bulk embedding and reranking.

```bash
# 1. Clone
git clone https://github.com/<your-username>/helper-in-law.git
cd helper-in-law

# 2. Install dependencies
uv sync

# 3. Configure
cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY

# 4. Start backing services (Postgres, Qdrant, Redis, MinIO)
docker compose up -d

# 5. Create the database schema
uv run alembic upgrade head

# 6. Ingest a small sample, then build the index
uv run python -m helperinlaw.ingest --court SC --limit 200
uv run python -m helperinlaw.index build

# 7. Run
uv run uvicorn helperinlaw.api.main:app --host 127.0.0.1 --port 8000   # REST API
uv run streamlit run ui/app.py                                      # Web UI
```

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
| `get_profile` / `set_style` | Read or override answer style |

**Claude Code (stdio):**

```bash
claude mcp add helper-in-law -- uv run --directory /path/to/helper-in-law python -m helperinlaw.mcp_server
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
├── docs/                 # architecture, runbooks, ROADMAP.md, licence-log.md
├── migrations/           # Alembic database migrations
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
├── docker-compose.yml
└── .env.example
```

---

## Configuration

Set in `.env` (see `.env.example`):

| Variable | Purpose | Default |
|---|---|---|
| `ANTHROPIC_API_KEY` | LLM for claim extraction and presentation | required |
| `DATABASE_URL` | Postgres connection | local compose |
| `QDRANT_URL` | Vector index | `http://localhost:6333` |
| `REDIS_URL` | Cache and queue | local compose |
| `S3_ENDPOINT` | Raw PDFs (MinIO locally) | local compose |
| `EMBED_MODEL` | Embedding model | `BAAI/bge-m3` |
| `RERANK_MODEL` | Cross-encoder | `BAAI/bge-reranker-v2-m3` |
| `JUDGE_MODEL` | Entailment checker (must differ from the answer model) | set explicitly |
| `EVIDENCE_MIN_SCORE` | Below this, the system abstains | tuned on eval set |
| `BIND_HOST` | Server bind address | `127.0.0.1` |

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
uv run python eval/run_eval.py --suite all
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
- **No data leaves your machine** in Phase 1 except calls to the LLM API for generation and verification.

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

Inspired by the product category of Indian legal-tech case search. Built on open tooling: FastAPI, Qdrant, PostgreSQL, Streamlit, the Model Context Protocol, and open embedding and reranking models from BAAI.
