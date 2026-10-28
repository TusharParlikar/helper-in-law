# Phase 3 plan: intensive testing

Purpose: try to break the system before users do, and produce evidence for every claim it makes. Nothing ships publicly until the release gates below pass.

Source of truth for scope: [`ROADMAP.md`](ROADMAP.md) §10. This document turns it into a plan starting from the evidence Phase 1 already has and the stack Phase 2 delivers ([`phase2.md`](phase2.md)).

**Guide:** 3-5 weeks of testing, plus time to recruit reviewers and a red-teamer. Runs on the Phase 2 staging stack, not on a laptop.

## Starting point: evidence from Phase 1

| Evidence | Phase 1 | Phase 3 needs |
|---|---|---|
| Unsupported statements displayed | 0 in 77 real scenarios + 40 sample-gate responses (95% upper bound ~4%) | 0 in >= 1,000 trials (upper bound < 0.3%) |
| Verbatim quotes at the cited paragraph | 100% (463/463) | 100% on the full campaign |
| Fault injection | 10 corruption types, 100% caught | The roadmap's full list, >= 99% per type, 100% for fabricated names and citations |
| Unanswerable / out-of-scope | 10 unanswerable, 8 out-of-scope, 10 false premise: all correct | 200 unanswerable, 100 false premise, 100 non-existent names |
| Prompt injection | 10 adversarial cases, 100% | Planted poisoned documents, MCP attacks, external red team |
| Style invariance | 100% (automated, >= 8 profiles) | All combinations of key settings, >= 5 profiles per campaign question |
| Expert review | None (labels written by the developer) | >= 2 blind legal reviewers, >= 300 answers, Cohen's kappa |
| MCP conformance | Official Python client, stdio + Streamable HTTP | Inspector full run, client matrix, OAuth flows, fuzzing |
| Load | Local, 8 concurrent, p95 9.5 s uncached | 10x expected traffic, 24-72 h soak, chaos |
| Security | No auth (localhost) | External pen-test against OWASP Top 10 and OWASP LLM Top 10 |

## 1. Verifier mutation testing

Extend `eval/faults/generate.py` to the roadmap's full list.

| Fault | Status |
|---|---|
| Swap a case name / citation / year | Built (name, citation) |
| Alter a number or section (302 -> 304) | Built |
| Invert meaning ("shall" -> "shall not") | Built |
| Delete a negation from a quote | Built |
| Cite a real quote for a different claim | Built |
| Fabricate a plausible but absent quote | Built |
| Cite a paragraph number that does not exist | Partly (non-existent source id); add a real source with a wrong paragraph |
| Add an unsupported sentence at the end | Built |
| Present a dissent or obiter as the holding | Partly (counsel's argument as holding); add real dissent once W0 captures separate opinions |
| Cite an overruled case as good law | To build, on the citation-treatment graph |

**Target:** >= 99% caught per type; 100% for fabricated case names and citations.

## 2. Hallucination campaign

| Set | Size | How it is built |
|---|---|---|
| Standard answerable | 500 | Scenarios written from SC headnotes across areas of law, labels checked by a reviewer |
| Unanswerable (no support in the corpus) | 200 | Questions on law outside the corpus (other courts, foreign law, topics with no indexed judgment) |
| Model knows it, corpus does not | 100 | Well-known cases deliberately left out of the index; catches answers from memory |
| Plausible but false premise | 100 | "In X v. Y the Court held..." where it did not |
| Non-existent case or statute names | 100 | Invented names in realistic form |
| Ambiguous / multi-jurisdiction | 100 | Must surface the ambiguity, not pick silently |
| Overruled or amended law | 100 | Treatment flags; IPC -> BNS transition |
| Long-tail and rare statutes | 100 | Retrieval stress |

Each question runs under >= 5 user profiles. Results are reported with the rule-of-three upper bound, never as "0%".

## 3. Expert human evaluation

- [ ] Recruit >= 2 independent reviewers (advocates or senior law students); brief them on the scoring sheet
- [ ] Blind scoring of >= 300 answers: correctness, completeness, citation fidelity, usefulness, clarity, style match
- [ ] Inter-rater agreement (Cohen's kappa) reported; disagreements adjudicated by a third reviewer
- [ ] Baselines scored the same way: plain keyword search, and an LLM without retrieval (measures what grounding adds)
- [ ] "Find the error" exercise: reviewers try to find a claim its citation does not support
- [ ] The Phase 1 scenario labels reviewed in the same pass (closes the open Phase 1 item)

## 4. Adversarial and red team

- [ ] Poisoned documents ("ignore previous instructions...") planted in a staging corpus
- [ ] Injection through user input, profile fields and style overrides ("answer without citations", "skip verification") must be refused or ignored
- [ ] MCP attacks: malicious arguments, oversized inputs, tool-result injection, confused deputy, scope escalation
- [ ] Jailbreaks aimed at removing disclaimers or fabricating cases
- [ ] Attempts to read other users' profiles and history
- [ ] Run by someone who did not build the system

## 5. Personalisation

- [ ] Style invariance across all combinations of depth x structure x tone x language: identical verified claim ids
- [ ] Citations present in every style, including Brief
- [ ] Translation keeps quotes byte-identical to the source
- [ ] Preference persistence, versioning, export and deletion
- [ ] Natural-language override parsing accuracy, and safe failure on nonsense
- [ ] Suggested settings never change anything silently
- [ ] Reading-level targets checked with readability metrics

## 6. MCP conformance and interoperability

- [ ] MCP Inspector full run: tools/list, resources, prompts, error paths, schema validation
- [ ] Client matrix: Claude Desktop, Claude Code, one third-party client; stdio and Streamable HTTP
- [ ] OAuth: new user, token expiry and refresh, revoked token, wrong scope, replayed token
- [ ] Schema-aware fuzzing: unicode, huge strings, nulls, injection strings, boundary values
- [ ] Tool selection: realistic prompts, does an agent pick the right tool (tune descriptions)
- [ ] Backwards compatibility on schema changes; concurrent sessions and rate limits

## 7. Non-functional

- [ ] Load: ramp to 10x expected traffic; p95 and p99 per endpoint and per MCP tool
- [ ] Soak: 24-72 h steady load (memory, connections)
- [ ] Chaos: kill Qdrant, Redis, the model server and the reranker mid-request; the answer falls back to retrieval-only or verbatim mode, never to unverified text
- [ ] Failover and restore: restore drill; blue/green index swap under load
- [ ] Cost: cost per verified answer at a realistic mix; budget guards trigger
- [ ] Data pipeline: simulated layout change, corrupted PDFs, duplicate judgments, scanned pages (OCR path)

## 8. Security and privacy

- [ ] External pen-test (or an independent review) against the OWASP Top 10 and the OWASP LLM Top 10
- [ ] IDOR tests on case, chat, profile and answer endpoints
- [ ] Secrets scanning; dependency CVE gate
- [ ] "History off" stores nothing; deletion reaches the database, caches and logs (backups by policy)
- [ ] Anonymised judgments stay anonymised; no re-identification through search

## Release gates (all must pass)

| Gate | Threshold | Phase 1 status |
|---|---|---|
| Unsupported claims displayed (campaign, >= 1,000 trials) | 0, with 95% upper bound | 0 in 117 responses |
| Responses without citations | 0 | 0 |
| Verifier fault-injection catch rate | >= 99% overall; 100% fabricated names and citations | 100% on 10 types; 1 type to build, 2 to complete |
| Abstain correctness (unanswerable + false premise) | >= 95% | 100% on 28 |
| Expert review: citation fidelity | >= 98% of sampled claims supported | Not run |
| Expert review: overall correctness | Target set after the baseline (suggest >= 90%) | Not run |
| Style invariance | 100% | 100% |
| Injection and red team: critical findings open | 0 | 10/10 internal cases pass; no external red team yet |
| MCP Inspector + client matrix | All pass | Official Python client only |
| Load, soak, chaos | Within SLO; no unverified output under failure | Local load test only |
| Pen-test: critical or high open | 0 | Not run (no auth in Phase 1) |
| Compliance sign-off | Done | Phase 2 W7 |

If any gate fails: fix it, then re-run the whole campaign, not just the failing test, because a fix can regress another area.

## Suggested sequence

| Weeks | Work |
|---|---|
| Before | Recruit reviewers and a red-teamer; build the campaign datasets; finish the missing fault types |
| 1 | Mutation testing; hallucination campaign, first full run |
| 2 | Expert review starts (runs in parallel); MCP conformance; personalisation |
| 3 | Red team; security and privacy tests; pen-test |
| 4 | Load, soak and chaos on staging; fix findings |
| 5 | Full campaign re-run after fixes; release-gate report |

## After launch

- Re-verify a 1-2% sample of production answers automatically; weekly human spot checks
- Every "this is wrong" report becomes a regression test
- Re-run the full campaign on every model, prompt or index change
