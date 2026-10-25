# Helper in Law — Roadmap v3 (3 Phases)

**Supersedes:** `Legal_RAG_Roadmap_Phase1_Phase2.md` and `Legal_RAG_Build_Blueprint.md`.
**Product:** Research over Indian court judgments. Every statement shown to the user is traceable to verbatim source text. Output adapts to how each user likes answers.
**Tags:** ✅ decided · 🔍 verify first · ⚠️ risk

---

## 0. What changed in v3

| Change | Where |
|---|---|
| **MCP moved into Phase 1** (local + HTTP, API-key auth) | §6 M9 |
| **Phase 2 = production hardening** (OAuth, scale, ops, compliance) | §9 |
| **Phase 3 = intensive testing** (red-team, conformance, load, expert review) | §10 |
| **Citations on every response**, enforced in code, not by prompt | §4 |
| **Hallucination-proof design ("grounding contract")** | §4 |
| **Adaptive answers** from a user preference profile | §5 |

---

## 1. Read this first: the honest hallucination promise

"No window for hallucination" cannot be guaranteed by any LLM system if you promise it as "the model never errs." What you **can** build and prove is a narrower, testable guarantee:

> **Grounding guarantee:** every claim, quote, case name, citation, date, and statute section shown to the user is traceable to a specific passage in the indexed corpus, and was machine-verified against that passage before display. If it can't be verified, it isn't shown.

What this does **not** guarantee (and the UI must say so):
- **Completeness:** retrieval may miss a relevant case.
- **Currency:** a cited case may have been overruled after the corpus date. (Mitigated by a citation-treatment graph + "as of" date.)
- **Legal correctness of interpretation:** a faithful paraphrase of a passage can still be a wrong reading of the law.

So the design target is **zero unsupported claims displayed**, measured and gated in tests, plus honest disclosure of the three limits above.

---

## 2. Product definition

**Capabilities (v1):**
1. **Ask** — Q&A with pinpoint citations
2. **Search** — keyword + semantic + filters (court, year, bench, statute)
3. **Read** — open a judgment, jump to a paragraph
4. **Chat with a judgment** — scoped to one case
5. **Statute lookup** — IPC↔BNS aware
6. **Trace** — who cites this case, and how (followed / distinguished / overruled) 🔍
7. **Personalise** — answers shaped by the user's style profile (§5)

**Non-goals:** live case status, cause lists, party "risk scores" on individuals (⚠️ privacy), drafting petitions, legal advice.

---

## 3. Architecture

```
Sources → Ingest → Parse → Chunk → Embed → Index (Qdrant) + Postgres (cases, paras, graph)

Question
  │
  ▼
[1] Understand (filters, statutes, case names)  ← user profile (jurisdiction focus etc.)
  ▼
[2] Hybrid retrieve (dense + BM25 → RRF) → [3] Rerank → [4] Evidence gate
  │                                                        │ weak evidence
  │                                                        └──► ABSTAIN ("not found") + nearest sources
  ▼
[5] Claim extraction (LLM → structured claims, each with source IDs + verbatim quote)
  ▼
[6] Verification suite (deterministic + entailment)   ← failures dropped
  ▼
[7] Verified Claim Set (style-independent, cached)
  ▼
[8] Presenter (applies user profile; may only use verified claims)
  ▼
[9] Final guard (no new facts, citations rendered from DB) → Response
```

**Core principle:** two separate stages.
- **Stage A — content** (steps 1–7): decide *what is true and supported*. Style-independent.
- **Stage B — presentation** (steps 8–9): decide *how to say it* for this user. Cannot add facts.

This is what lets answers be fully adaptive without ever loosening grounding.

**Adapters over one core:** REST, MCP, and UI all call `service.py`. No logic lives in handlers.

---

## 4. The grounding contract (anti-hallucination design)

### 4.1 Rules the code enforces

| # | Rule | How it's enforced |
|---|---|---|
| G1 | **LLM never writes case names, citations, courts, dates, bench, or paragraph numbers** | The LLM refers to sources by ID (`[S3]`). The renderer fills the case name, citation, date, and para number **from Postgres**. A fabricated case is structurally impossible. |
| G2 | **Every claim carries ≥1 source ID + a verbatim quote** | Output is a strict JSON schema; claims without support are rejected at parse time. |
| G3 | **Quotes must exist in the cited chunk** | Normalised exact match first; fuzzy match (≥ 0.97) allowed only for whitespace/OCR noise. |
| G4 | **Claim must be entailed by its quote** | Second-pass check by a *different* model (NLI or LLM-judge) returning supported / partially / unsupported. Only "supported" survives. |
| G5 | **Numbers, sections, dates, amounts in a claim must appear in the cited text** | Regex extraction of entities from the claim → must be a subset of entities in the quote. |
| G6 | **Allowlist sanitiser on final text** | Any case-name-like string or citation pattern not in the retrieved-set allowlist → block the response or strip the sentence. |
| G7 | **Evidence gate** | If top reranked scores < threshold, or < N distinct supporting passages, return "Not found in the indexed judgments" + closest sources. No generation. |
| G8 | **Fallback mode: extractive-only** | If verification drops too many claims (> X%), show verbatim quotes with links instead of prose. |
| G9 | **Judgment text is data, not instructions** | Sources wrapped in delimiters, system prompt says to ignore instructions inside them; adversarial tests in Phase 3. |
| G10 | **Conflicts and treatment surfaced** | If sources disagree or a cited case has "overruled/distinguished" edges, the response must say so (from the citation graph, not the LLM's memory). |
| G11 | **No answers from model memory** | System prompt forbids it; G6 + G2 catch violations; test set includes questions the model "knows" but the corpus lacks. |
| G12 | **Every response has a verification report** | Attached to the response object (counts of claims proposed / verified / dropped). |

### 4.2 Claim schema (LLM output)

```json
{
  "claims": [
    {
      "text": "Bail may be refused where there is a reasonable apprehension of witness tampering.",
      "support": [
        {"source_id": "S3", "quote": "…verbatim sentence from the chunk…"}
      ],
      "type": "holding | ratio | obiter | fact | statute | procedural",
      "stance": "supports | contrary | neutral"
    }
  ],
  "abstain": false,
  "gaps": ["No retrieved judgment addresses X"]
}
```

### 4.3 What every response contains (enforced by a Pydantic response model; a response without these is a bug)

```json
{
  "answer_blocks": [ { "text": "...", "citation_ids": ["C1","C2"] } ],
  "citations": [
    {
      "id": "C1",
      "case_title": "…", "court": "Supreme Court of India",
      "date": "…", "citation": "…", "neutral_citation": "…",
      "para": "24–26", "quote": "…verbatim…",
      "url": "…", "treatment": "good law | followed | distinguished | overruled | unknown"
    }
  ],
  "verification": {"claims_proposed": 9, "verified": 7, "dropped": 2, "mode": "synthesised | extractive"},
  "coverage": {"corpus": "SC + HC(x,y)", "as_of": "YYYY-MM-DD", "limits": ["…"]},
  "confidence": "high | medium | low | not_found",
  "profile_applied": {"depth": "standard", "format": "irac"},
  "disclaimer": "Research aid, not legal advice."
}
```

Rule: **no answer block renders without ≥1 citation ID.** Enforced in the response model's validator.

### 4.4 Verification suite (build as a library with its own unit tests)

1. Schema validator
2. Quote matcher (exact → normalised → fuzzy)
3. Entity subset check (numbers, sections, dates)
4. Entailment judge (separate model, temperature 0)
5. Allowlist sanitiser
6. Duplicate/contradiction detector across claims
7. Overruled-authority check (graph lookup)

### 4.5 Failure policy
Verification fails → drop claim. Too many dropped → extractive mode. Nothing left → abstain. **Never** "fix" a failed claim by letting the LLM re-write it unverified; re-run the full chain on any rewrite.

---

## 5. Adaptive answers (user preference profile)

### 5.1 "How do you like your answers?" — onboarding + settings

Short onboarding (60 seconds, skippable, editable anytime). Plain choices, with a live preview of the same answer in the chosen style.

| Setting | Options |
|---|---|
| **Who you are** | Advocate · Law student · Researcher · In-house counsel · General reader |
| **Depth** | Quick (3–5 lines) · Standard · Deep (full analysis) |
| **Structure** | Bullets · Short paragraphs · IRAC · Research memo · Table of cases |
| **Tone / language level** | Technical legal · Plain English · Explain like I'm new |
| **Answer language** | English · Hindi · (others later). Quotes stay in original, translation shown alongside |
| **Citation style** | Case name + SCC/AIR · Neutral citation · Para-level inline · Footnotes |
| **Quotes** | Always show quotes · Show on hover · Only on request |
| **Contrary authority** | Always include · Only if found · Never |
| **Ratio vs obiter** | Highlight · Hide obiter · Don't distinguish |
| **Jurisdiction focus** | SC only · A specific High Court · All |
| **Recency preference** | Newest first · Landmark first · Balanced |
| **Length cap** | words or "fit one screen" |
| **Follow-ups** | Suggest next questions: on/off |
| **Save my history** | On / Off (privacy) |

### 5.2 Three ways preferences get set
1. **Explicit settings** (above) — source of truth.
2. **Natural-language overrides per request:** "shorter", "as a table", "explain simply", "only SC after 2015". Parsed into a one-off style patch.
3. **Learned suggestions** from feedback (👍/👎, "too long" button, edits). The system **suggests** a settings change ("You often shorten answers — switch default to Quick?"). It never silently changes settings.

### 5.3 Profile schema

```json
{
  "user_id": "…",
  "role": "advocate",
  "depth": "standard",
  "structure": "irac",
  "tone": "technical",
  "answer_language": "en",
  "citation_style": "case_name_scc",
  "quotes": "always",
  "contrary_authority": "always",
  "obiter": "highlight",
  "jurisdiction": ["SC", "Gujarat HC"],
  "recency": "balanced",
  "max_words": null,
  "suggest_followups": true,
  "history_opt_in": true,
  "version": 3
}
```

### 5.4 Hard boundary: what preferences may NOT change
Preferences affect **presentation only**. These are not user-configurable:
- Citations required
- Verification on
- Abstain on weak evidence
- Disclaimer shown
- Coverage/as-of notice shown

"Quick" mode shortens prose, but still shows citation IDs and the verification badge.

### 5.5 How Stage B stays safe
- Presenter receives **only** the Verified Claim Set + profile (not the raw sources, not the original question's unverified reasoning).
- Output uses claim IDs per sentence (`{c3}`); renderer attaches citations.
- A light final guard checks: every sentence maps to ≥1 verified claim ID; no new entities/numbers; translation keeps quotes untouched.
- Translations: translate the paraphrase; **never** translate or alter quoted text. Show original quote.
- The Verified Claim Set is cached per (question, filters, index_version); restyling is then cheap and doesn't re-run retrieval.

### 5.6 MCP and API honour the same profile
Phase 1 (no auth): profile resolved from a local `profile_id` (default `default`). Phase 2: from the authenticated user. Per-call `style` override accepted as a typed parameter.

---

# PHASE 1 — Build it for real (incl. MCP)

**Guide:** ~10–12 weeks part-time. Milestones are gates, not dates.

## 6. Phase 1 milestones

### M1 — Foundations (wk 1)
- [ ] Repo, `uv`, ruff, mypy (strict on core + verification), pytest, pre-commit, Makefile
- [ ] Docker Compose: Postgres, Qdrant, Redis, MinIO
- [ ] `pydantic-settings`, JSON structured logging
- [ ] `docs/licence-log.md` for every data source
- [ ] **Write 30 eval questions before any retrieval code**

### M2 — Ingestion (wk 1–2)
- [ ] Per-source downloader (ToS-respecting, resumable, idempotent by `pdf_sha256`)
- [ ] Extraction with quality score; OCR fallback
- [ ] Cleaner (headers/footers, hyphenation, banners)
- [ ] Dead-letter queue + failure report
- [ ] **Exit:** 100% of target corpus processed or explicitly logged as failed

### M3 — Parsing & structure (wk 2–3)
- [ ] Metadata: title, parties, date, bench, case no., citations
- [ ] Paragraph segmentation with numbers
- [ ] Section labels (facts/issues/arguments/reasoning/holding)
- [ ] Statute extraction + IPC↔BNS, CrPC↔BNSS, Evidence↔BSA alias table
- [ ] Case→case citation extraction, with treatment tagging 🔍
- [ ] **Exit:** 50-judgment gold set: ≥95% title/date/bench, ≥90% para numbering

### M4 — Indexing (wk 3–4)
- [ ] Structure-aware chunker (300–600 tokens, para-bounded, context prefix)
- [ ] GPU batch embedding (bge-m3 dense + sparse), versioned, resumable
- [ ] Qdrant collections + payload indexes
- [ ] Side-by-side `index_version` rebuild command

### M5 — Retrieval (wk 4–5)
- [ ] Query understanding → filters
- [ ] Multi-query rewrite
- [ ] Hybrid + RRF
- [ ] Cross-encoder rerank
- [ ] Parent expansion
- [ ] Authority/recency boosts (profile-aware)
- [ ] **Evidence gate** thresholds tuned on the unanswerable set
- [ ] **Eval gate:** Recall@10 ≥ 0.85

### M6 — Grounded generation (wk 5–7) ← the heart
- [ ] Claim-extraction prompt + strict JSON schema
- [ ] **Verification suite** (§4.4), each check unit-tested with adversarial fixtures
- [ ] ID-based citation rendering from DB (G1)
- [ ] Extractive fallback + abstain paths
- [ ] Response model validator (no answer without citations)
- [ ] **Exit:** on the answer set, 0 unsupported claims displayed (§7)

### M7 — Adaptive presentation (wk 7–8)
- [ ] Profile schema + storage + versioning
- [ ] Onboarding flow with live preview
- [ ] Natural-language override parser → style patch
- [ ] Presenter stage + final guard
- [ ] Translation path (quotes untouched)
- [ ] Feedback capture + "suggest a setting" logic
- [ ] **Exit:** same question rendered under ≥8 profiles → identical verified claims, differing only in style (automated test)

### M8 — API + UI (wk 8–9)
- [ ] `POST /ask`, `/search`, `GET /cases/{id}`, `/cases/{id}/paragraphs/{n}`, `POST /cases/{id}/chat`, `GET/PUT /profile`, `POST /feedback`
- [ ] **No auth in Phase 1:** single-user local mode, bind to `127.0.0.1` by default, never expose publicly. A `profile_id` parameter selects the style profile (default: `default`). Auth is introduced in Phase 2.
- [ ] Streamlit UI: ask, filters, source panel with highlighted paragraph, verification badge, "limits" notice, profile settings

### M9 — MCP server (wk 9–10) ← now in Phase 1
- [ ] Official Python SDK (FastMCP); **stdio** (local) + **Streamable HTTP** (localhost only, no auth in Phase 1)
- [ ] Tools (all read-only; thin wrappers over `service.py`):

| Tool | Notes |
|---|---|
| `search_judgments` | filters; max 20 results; returns case IDs + snippets + para refs |
| `ask_legal_question` | returns the full response object (answer blocks + citations + verification + coverage) |
| `get_judgment` | metadata + structured sections |
| `get_paragraph` | exact text, max 10 paras |
| `find_citing_cases` | with treatment |
| `lookup_statute` | IPC↔BNS mapping + top cases |
| `get_profile` / `set_style` | read the user's style; apply a per-call override (profile writes limited to style fields) |

- [ ] Resources: `judgment://{case_id}`, `statute://{act}/{section}`
- [ ] Prompts: "research memo on {issue}", "find contrary authority"
- [ ] **MCP safety rules:**
  - Tool results are always the **verified response object**, never raw LLM text
  - Citations included in every tool result that makes a claim
  - Size caps on every result
  - Source text labelled as quoted material (injection hygiene — G9)
  - Clear tool descriptions (they are part of the client's prompt surface)
- [ ] Verified with **MCP Inspector** and a real client (Claude Desktop / Claude Code)
- [ ] MCP smoke tests in CI

### M10 — Hardening (wk 10–12)
- [ ] Unit/integration tests; parser golden tests; verification-suite mutation tests (§10.2)
- [ ] Baseline load test
- [ ] README, architecture doc, reindex runbook
- [ ] Written Phase 1 evaluation report with ablation table (dense → +BM25 → +rerank → +rewrite → +verification)

---

## 7. Phase 1 exit criteria

| Metric | Target |
|---|---|
| Recall@10 (retrieval set) | ≥ 0.85 |
| MRR | ≥ 0.60 |
| **Unsupported claims displayed** (answer + adversarial sets) | **0** |
| Citation accuracy (quote exists at cited para) | ≥ 0.99 |
| Responses lacking citations | **0** |
| Abstain correctness on unanswerables | ≥ 0.90 |
| Prompt-injection pass rate (adversarial set) | 100% |
| Style-invariance test (same claims across profiles) | 100% |
| MCP tools pass Inspector + real-client check | all |
| p95 `/ask` latency | ≤ 10 s non-streaming |
| Parser accuracy | ≥ 0.95 |

Interpretation note: "0 displayed" is measured on your test sets. Phase 3 widens the sample so the claim is statistically defensible (§10.3).

---

# PHASE 2 — Production-ready

## 8. Phase 2 workstreams (MCP already exists; now it gets hardened)

### W1 — MCP hardening
- **OAuth 2.1** per the current MCP authorization spec 🔍 (spec has evolved; check the current revision): discovery metadata, token validation, scopes per tool
- Per-tool rate limits, per-token quotas, response size budgets
- Versioned tool schemas + deprecation policy
- Remote deployment behind TLS/WAF; keep stdio build for self-host

### W2 — Security
- **Introduce AuthN/Z** (none exists in Phase 1): orgs, roles, scopes, secrets manager, IDOR protection on case/chat IDs
- SSRF-safe fetchers, input validation, dependency + container scanning, SBOM
- Pen-test checklist

### W3 — Reliability & scale
- Stateless API/MCP pods; GPU inference service (batching) for embed/rerank
- Redis caching: embeddings, retrieval, **Verified Claim Sets** (restyle without re-verify)
- Timeouts/retries/circuit breaker on LLM provider; retrieval-only fallback
- Qdrant replicas + snapshots; Postgres PITR
- Blue/green index swaps via `index_version`

### W4 — Automated data pipeline
- Scheduled incremental ingest, backfills, source health checks (layout-change detection)
- Data quality dashboard (coverage by court/year, parse failures)
- Provenance: every answer → `pdf_sha256` + `index_version`

### W5 — Observability
- OpenTelemetry traces through every pipeline stage; Langfuse/Phoenix for LLM traces + prompt versions
- Dashboards: latency, errors, cache hit, cost/query, abstain rate, **verification-drop rate**
- Alerts: unsupported-claim detector firing in prod, drift in abstain rate, ingestion failures, cost anomalies

### W6 — Release process
- Evals + verification regression suite in CI; **block merges on regression**
- Versioned prompts, models, chunker, index; changelog; rollback runbook
- Shadow/canary for new index or model versions

### W7 — Compliance ⚠️
- **DPDP Act** 🔍 get qualified advice: personal data in judgments (minors, victims, sexual-offence and matrimonial matters). Policy for redaction, takedown, retention
- Source licence review before any public serving
- Query-log retention limits; profile data: export + delete; "history off" truly stores nothing
- Privacy policy, ToS, disclaimers

### W8 — Cost control
- Small model for rewrite/classify, stronger model for claim extraction; separate judge model for G4
- Context caps, caching, batching, per-user budgets
- **Cost per verified answer** as a tracked metric

### W9 — Deployment
- IaC (Terraform), dev/staging/prod, containers (non-root, multi-stage)
- CI/CD: build → test → eval → scan → staging → MCP smoke → promote

**Phase 2 exit:** OAuth flow works for a fresh user · backup restore drill done · alerts tested · security review clean of criticals · compliance review done · eval gates running in CI.

---

# PHASE 3 — Intensive testing

**Purpose:** try to break it before users do, and produce evidence for the claims you make.
**Guide:** 3–5 weeks. Nothing ships publicly until the release gates (§10.8) pass.

## 10. Phase 3 test programme

### 10.1 Test layers

| Layer | What |
|---|---|
| Unit | parsers, chunker, each verifier check, response validator, profile logic |
| Integration | ingest→index→retrieve→verify→present, with real services |
| E2E | UI flows, REST, MCP via real clients |
| Non-functional | load, soak, chaos, cost |
| Safety/quality | hallucination, injection, bias/fairness, privacy |
| Human | expert blind review, usability |

### 10.2 Verification-suite mutation testing (does the safety net actually catch things?)
Create **fault injections**: take known-good verified answers, then corrupt them programmatically, and confirm the verifier blocks each:
- swap a case name / citation / year
- alter a number or section (e.g., 302 → 304)
- invert meaning ("shall" → "shall not")
- delete a negation from a quote
- cite a real quote for a different claim
- fabricate a quote that is plausible but absent
- cite a paragraph number that doesn't exist
- add an unsupported sentence at the end
- present a dissent/obiter as the holding
- cite an overruled case as good law

**Target:** verifier catches ≥ 99% of injected faults per category; 100% for fabricated case names/citations (G1/G6 make these structural).

### 10.3 Hallucination test campaign
| Set | Size | Purpose |
|---|---|---|
| Standard answerable | 500 | normal use |
| Unanswerable (no support in corpus) | 200 | must abstain |
| "Model-knows-it-but-corpus-doesn't" | 100 | catches answers from memory (G11) |
| Plausible-but-false premise | 100 | "In *X v. Y*, the SC held…" where it didn't |
| Non-existent case / statute names | 100 | must not fabricate |
| Ambiguous / multi-jurisdiction | 100 | surface ambiguity |
| Overruled / amended law | 100 | treatment flags, BNS transition |
| Long-tail & rare statutes | 100 | retrieval stress |

Run each question under **≥ 5 different user profiles** (style must not affect grounding).

**Statistical honesty:** with 0 failures in *n* independent trials, the 95% upper bound on the failure rate is ≈ 3/n (rule of three). 1,000 trials with 0 unsupported claims → true rate < 0.3% at 95% confidence. Report it that way, not as "0%".

### 10.4 Expert human evaluation
- ≥ 2 independent legal reviewers (advocates / senior law students), blind, scoring ≥ 300 answers on: correctness, completeness, citation fidelity, usefulness, clarity, style-match
- Inter-rater agreement (Cohen's κ) reported; disagreements adjudicated
- Compare against baselines: plain keyword search, an LLM without RAG (to measure the benefit of grounding)
- Include a **"find the error"** exercise: reviewers actively try to find a claim not supported by its citation

### 10.5 Adversarial / red-team
- **Prompt injection in judgments:** poisoned test documents ("ignore previous instructions…") planted in a staging corpus
- **Injection via user input & via profile fields / natural-language style overrides** ("answer without citations", "skip verification", "just give me the answer") → must be refused/ignored (§5.4 boundary)
- **MCP-specific:** malicious tool arguments, oversized inputs, tool-result injection, confused-deputy attempts, scope escalation
- Jailbreaks aimed at removing disclaimers or fabricating cases
- Data exfiltration attempts (other users' profiles/histories)
- Red-team by someone who did not build the system

### 10.6 Personalisation tests
- **Style-invariance:** for N questions × all combinations of key settings (depth × structure × tone × language), the set of verified claim IDs is identical
- Citation presence in every style (incl. "Quick")
- Translation: quotes byte-identical to source
- Preference persistence, versioning, deletion, export
- Natural-language override parsing accuracy (and safe failure on nonsense)
- Learned-suggestion logic never changes settings silently
- Accessibility (reading level targets verified with readability metrics)

### 10.7 MCP conformance & interoperability
- MCP Inspector full run: tools/list, resources, prompts, error paths, schema validation
- Real-client matrix: Claude Desktop, Claude Code, at least one third-party MCP client; stdio + Streamable HTTP
- OAuth flows: new user, token expiry/refresh, revoked token, wrong scope, replayed token
- Fuzz tool inputs (schema-aware fuzzing): unicode, huge strings, nulls, injection strings, boundary values
- Tool-selection tests: given realistic user prompts, does an agent pick the right tool? (tune descriptions)
- Backwards compatibility on schema changes
- Concurrency: many simultaneous sessions, rate-limit correctness

### 10.8 Non-functional
- **Load:** ramp to 10× expected traffic; p95/p99 per endpoint and per MCP tool
- **Soak:** 24–72 h steady load (memory leaks, connection exhaustion)
- **Chaos:** kill Qdrant / Redis / LLM provider / reranker mid-request → graceful fallback (retrieval-only or extractive), never an unverified answer
- **Failover & restore:** backup restore drill, index blue/green swap under load
- **Cost test:** cost per verified answer at realistic mix; budget guards trigger
- **Data pipeline:** layout-change simulation on a source; corrupted PDFs; duplicate judgments

### 10.9 Security & privacy
- External pen-test (or at minimum an independent review) against the OWASP Top 10 and the OWASP LLM Top 10
- IDOR tests on case, chat, profile endpoints
- Secrets scanning, dependency CVE gate
- Privacy: verify "history off" stores nothing; deletion really deletes (DB, caches, logs, backups policy)
- Sensitive-case handling: anonymised judgments stay anonymised; no re-identification via search

### 10.10 Release gates (all must pass)

| Gate | Threshold |
|---|---|
| Unsupported claims displayed (hallucination campaign, ≥ 1,000 trials) | **0**, reported with 95% upper bound |
| Responses without citations | **0** |
| Verifier fault-injection catch rate | ≥ 99% overall; 100% fabricated names/citations |
| Abstain correctness (unanswerable + false premise) | ≥ 95% |
| Expert review: citation fidelity | ≥ 98% of sampled claims judged supported |
| Expert review: overall correctness | ≥ target set after baseline (suggest ≥ 90%) |
| Style-invariance | 100% |
| Injection / red-team: critical findings open | **0** |
| MCP Inspector + client matrix | all pass |
| Load/soak/chaos | within SLO, no unverified output under failure |
| Pen-test: critical/high open | **0** |
| Compliance sign-off | done |

Any gate fails → fix → **re-run the whole campaign** (not just the failing test), because fixes can regress other areas.

### 10.11 Ongoing after launch
- Sample 1–2% of production answers for automatic re-verification and weekly human spot checks
- Every user "this is wrong" report becomes a regression test
- Re-run the full hallucination campaign on every model, prompt, or index change

---

## 11. Data model (additions to earlier schema)

```
cases, paragraphs, chunks, statutes, case_statutes, citations(treatment)   -- as before
users, orgs, api_keys, oauth_clients, tokens                               -- Phase 2 only (Phase 1 has no auth)
user_profiles(user_id, profile_json, version, updated_at)
answers(id, user_id?, question, filters, index_version, claim_set_json,
        verification_report_json, mode, confidence, created_at)            -- store only if history on
feedback(answer_id, rating, reason, style_flags)
eval_runs(id, git_sha, dataset, metrics_json)
audit_log(…)
```

---

## 12. Repo layout

```
helper-in-law/
├── infra/  migrations/  docs/ (architecture, runbooks, ADRs, licence-log)
├── src/helperinlaw/
│   ├── core/            # config, logging, types
│   ├── ingest/ parse/ index/
│   ├── retrieve/        # understand, rewrite, hybrid, rerank, evidence_gate
│   ├── ground/          # claim_extract, verify/ (quote, entities, entail, allowlist, graph), render
│   ├── present/         # profile, overrides, presenter, final_guard, translate
│   ├── service.py       # THE core API
│   ├── api/             # FastAPI adapter
│   ├── mcp_server/      # tools, resources, prompts, auth
│   └── workers/
├── ui/
├── eval/
│   ├── datasets/        # retrieval, answers, unanswerable, false_premise, adversarial, gold_parse
│   ├── faults/          # fault-injection generators for verifier tests
│   ├── run_eval.py
│   └── reports/
├── tests/               # unit, integration, e2e, mcp, security, load
└── .github/workflows/
```

---

## 13. Stack (unchanged highlights)
Python 3.12 · FastAPI · Postgres 16 · Qdrant · Redis · MinIO/S3 · PyMuPDF + OCR · `bge-m3` · `bge-reranker-v2-m3` · Claude (extraction/presentation) + a *different* model for the entailment judge · MCP Python SDK · OTel + Langfuse · GitHub Actions · Terraform (P2).

🔍 Benchmark embedding alternatives (multilingual-e5, InLegalBERT) on your own eval set.
🔍 GPU needed for bulk embedding and reranking.

---

## 14. Top risks

1. ⚠️ Misleading-but-faithful paraphrase (entailment passes, interpretation wrong) → show quote next to every claim; expert review in Phase 3
2. ⚠️ Retrieval misses the key case → recall metrics, "coverage" disclosure, "search more" affordance
3. ⚠️ Outdated/overruled law → treatment graph, as-of date
4. ⚠️ Data licensing and DPDP → resolve before public launch
5. ⚠️ Prompt injection via judgments / MCP results
6. ⚠️ Users pressuring the system to drop safeguards via "preferences" → §5.4 boundary + tests
7. Parsing quality, cost, GPU availability
8. Scope creep

---

## 15. Week-1 checklist

- [ ] Fix Phase 1 court scope (SC + which HCs)
- [ ] Locate bulk data source; read terms; fill licence log
- [ ] Recruit 1–2 legal reviewers now (you'll need them in Phases 1 and 3)
- [ ] Write the 30 starter eval questions + 10 unanswerable + 10 false-premise
- [ ] Repo skeleton + Docker Compose
- [ ] Download 200 judgments, eyeball extraction quality
- [ ] Decide GPU plan
- [ ] Draft the response schema (§4.3) and claim schema (§4.2) **first** — everything else hangs off them

---

*Gate rule: P1 ships on §7. P2 ships on its exit list. Public launch only after every §10.10 gate passes.*
