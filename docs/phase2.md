# Phase 2 plan: production-ready

Phase 1 proved the pipeline on one machine for one user. Phase 2 makes it safe to run for other people: accounts and auth, a storage stack that scales, a refreshing corpus, monitoring, compliance, and deployment. It also carries forward the quality work Phase 1's measurements pointed to.

Source of truth for scope: [`ROADMAP.md`](ROADMAP.md) §8. This document turns it into an ordered plan starting from where Phase 1 actually ended ([`checklist.md`](../checklist.md), [`eval/reports/phase1.md`](../eval/reports/phase1.md)).

**Guide:** ~10-14 weeks part-time. Milestones are gates, not dates.

## Starting point

| Area | End of Phase 1 | Phase 2 target |
|---|---|---|
| Users | One, on localhost, no auth | Accounts, orgs, roles; OAuth 2.1 for MCP |
| Storage | SQLite (FTS5 + vectors as blobs) | Postgres 16, Qdrant, Redis, object storage for PDFs |
| Concurrency | One Python process; 8 uncached questions at once -> p95 9.5 s (CPU-bound, shared interpreter) | Several stateless API/MCP workers; p95 within SLO at expected load |
| Models | Ollama `qwen3:1.7b` on a laptop CPU, ~9 tokens/s; LLM mode 45-50 s; verbatim mode default | Ollama on a GPU host (or a hosted model, if chosen); LLM mode <= 10 s |
| Retrieval quality | Held-out: right Article first 50%, shown 60%; precedent 87% | Measurably better on a fresh held-out set (target set after W0 baseline) |
| Corpus | 384 SC judgments (2014-2024), Constitution; manual ingest | Scheduled incremental ingest, more years, chosen High Courts |
| Observability | JSON logs | Traces through every stage, dashboards, alerts |
| Release | Local tests and eval scripts; no CI | Evals and verification regressions in CI, blocking merges |
| Compliance | Licence log; no personal-data policy | DPDP review, redaction and takedown policy, privacy policy and ToS |

## Decisions needed before starting

| Decision | Options | Why it matters |
|---|---|---|
| Hosting | One VPS with a GPU; a cloud provider; on-premise | Drives W1, W3 and W9; a GPU is what fixes LLM latency and makes stronger embeddings practical |
| Model provider | Ollama on a GPU host (current choice); a hosted API | Latency, cost per answer, data leaving the machine |
| Corpus scope | More SC years; which High Courts | Corpus size drives storage, ingest time and licence review |
| Who uses it | Private beta (named users) or public | Public serving needs W7 compliance done first |
| Budget | Monthly ceiling for hosting and models | Sets W8 limits |
| CI | When to turn it on | W6 depends on it; nothing is set up until you say so |

## Workstreams, in order

### W0: Quality carry-over from Phase 1 (first, because it changes what gets scaled)

What Phase 1 measured and could not finish on a laptop CPU.

- [ ] Fresh held-out set (30+ new scenarios, written before any W0 change, never tuned on); the current held-out set has now been seen
- [ ] Stronger embeddings on a GPU: `nomic-embed-text` (~7 h on the laptop CPU, minutes on a GPU), `bge-m3`, InLegalBERT; keep one only if it beats keyword-only on dev, then check on held-out
- [ ] Cross-encoder reranker (`bge-reranker-v2-m3`) in place of the lexical reranker, same rule
- [ ] Capture concurrent and dissenting opinions (they restart their numbering and are dropped today; main source of low text coverage)
- [ ] Remove the 3 remaining headnote leaks
- [ ] Larger corpus (more SC years, then chosen High Courts), re-measuring after each step
- [ ] LLM mode on a GPU within 10 s; compare a stronger local model against `qwen3:1.7b` on the verification keep rate

**Done when:** each change has a dev and fresh held-out number in `eval/reports/`, and only the ones that help are on.

### W1: Storage and scale

- [ ] Postgres 16 for cases, paragraphs, profiles, feedback, answers (with migrations)
- [ ] Qdrant for vectors, with payload indexes for court, year, statute
- [ ] Redis for embeddings, retrieval results and Verified Claim Sets (restyle without re-verifying)
- [ ] Object storage for PDFs, keyed by `pdf_sha256`
- [ ] Stateless API and MCP workers (several processes, so CPU-bound answering no longer shares one interpreter)
- [ ] GPU inference service for embedding and reranking, with batching
- [ ] Blue/green index swaps through `index_version`
- [ ] Backups: Postgres point-in-time recovery, Qdrant snapshots; one restore drill

**Done when:** the Phase 1 benchmarks give the same numbers on the new stack, and a load test at expected traffic stays within SLO.

### W2: Accounts and security

- [ ] Users, orgs, roles, scopes; API keys for integrations
- [ ] IDOR protection on case, chat, profile and answer IDs
- [ ] Secrets manager; no secrets in the repo or environment files on servers
- [ ] SSRF-safe fetchers (the ingest downloaders and statute lookups)
- [ ] Input validation and size limits on every endpoint
- [ ] Dependency and container scanning, SBOM
- [ ] Pen-test checklist prepared for Phase 3

**Done when:** a fresh user can sign up and use the UI and API; another user's data is unreachable by ID guessing.

### W3: MCP hardening

- [ ] OAuth 2.1 per the current MCP authorization spec (discovery metadata, token validation, scopes per tool); check the spec revision before building
- [ ] Per-tool rate limits, per-token quotas, response size budgets
- [ ] Versioned tool schemas and a deprecation policy
- [ ] Remote Streamable HTTP behind TLS; stdio build kept for self-hosting

**Done when:** a real MCP client completes the OAuth flow as a new user and calls every tool within its scope.

### W4: Automated data pipeline

- [ ] Scheduled incremental ingest of new judgments; backfills by year
- [ ] Source health checks (layout-change detection: parse failure rate, coverage, headnote leaks per batch)
- [ ] The parser gold set run on every ingest change (`eval/run_parse_audit.py`)
- [ ] Data-quality dashboard: coverage by court and year, dead-letter reasons
- [ ] Provenance on every answer: `pdf_sha256` and `index_version`

**Done when:** a new month of judgments arrives, is parsed, audited and indexed without manual steps, and a broken batch is caught before it is served.

### W5: Observability

- [ ] OpenTelemetry traces through every stage (understand, rewrite, search, rerank, verify, present)
- [ ] LLM traces with prompt versions
- [ ] Dashboards: latency, errors, cache hits, cost per query, abstain rate, verification-drop rate
- [ ] Alerts: unsupported-claim detector firing, abstain-rate drift, ingest failures, cost anomalies

**Done when:** each alert has been triggered once on purpose and reached a person.

### W6: Release process (only when you approve CI)

- [ ] CI: tests, ruff, mypy, the sample eval gates, the scenario benchmarks, the parser gold set
- [ ] Block merges on any regression in grounding (unsupported statements, citation accuracy) and on agreed accuracy drops
- [ ] Versioned prompts, models, chunker and index; changelog; rollback runbook
- [ ] Shadow or canary runs for a new index or model

**Done when:** a deliberately regressing change is blocked by CI.

### W7: Compliance

- [ ] Qualified advice on the DPDP Act: personal data in judgments (minors, victims, sexual-offence and matrimonial matters)
- [ ] Redaction, takedown and retention policy
- [ ] Source licence review before any public serving (the SC dataset is CC-BY-4.0; each new source logged in [`licence-log.md`](licence-log.md))
- [ ] Query-log retention limits; profile export and delete; "history off" stores nothing
- [ ] Privacy policy, terms of service, "not legal advice" disclaimers

**Done when:** written sign-off from the adviser, and the delete and history-off paths are tested.

### W8: Cost control

- [ ] Cost per verified answer as a tracked metric
- [ ] Small model for rewrite and classification, stronger model for claim extraction, a different model as the entailment judge
- [ ] Context caps, caching, batching, per-user budgets

**Done when:** cost per verified answer is on a dashboard and a budget limit has been hit in a test.

### W9: Deployment

- [ ] Containers (non-root, multi-stage) for API, MCP, UI, workers
- [ ] Infrastructure as code; dev, staging and production environments
- [ ] Pipeline: build -> test -> eval -> scan -> staging -> MCP smoke -> promote (after W6 approval)

**Done when:** staging is rebuilt from scratch by one command and passes the MCP smoke test.

## Suggested sequence

| Weeks | Work |
|---|---|
| 1-3 | Decisions; W0 baseline on a fresh held-out set; W1 storage migration with benchmark parity |
| 4-6 | W0 model and corpus experiments on the GPU host; W2 accounts; W4 scheduled ingest |
| 7-9 | W3 OAuth for MCP; W5 tracing and dashboards; W8 cost metric |
| 10-12 | W7 compliance review; W9 staging deployment; W6 CI once approved |
| 13-14 | Restore drill, alert tests, security review, Phase 2 exit check |

## Phase 2 exit criteria

From [`ROADMAP.md`](ROADMAP.md), plus the carry-over:

- [ ] OAuth flow works for a fresh user (UI, API and MCP)
- [ ] Backup restore drill done
- [ ] Alerts tested
- [ ] Security review with no open criticals
- [ ] Compliance review done
- [ ] Eval and grounding gates running in CI (when approved)
- [ ] Grounding unchanged: 0 unsupported statements, 100% verbatim quotes, on dev and the fresh held-out set
- [ ] LLM mode p95 <= 10 s on the production host

## Risks

| Risk | Mitigation |
|---|---|
| Migration changes answers | Benchmark parity check before switching; keep SQLite as the reference until parity holds |
| Better models still miss on new wording | Fresh held-out set per experiment; adopt only measured gains |
| Personal data in judgments | W7 before any public access; private beta until then |
| GPU cost | W8 budgets; verbatim mode stays the free default |
| Scope creep | Workstreams are gates; anything not here waits for Phase 3 or later |
