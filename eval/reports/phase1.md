# Phase 1 evaluation report

Scope: everything Phase 1 of [`docs/ROADMAP.md`](../../docs/ROADMAP.md) asks for, measured locally. No CI, no deployment, no authentication (Phase 2). Item-by-item status: [`checklist.md`](../../checklist.md).

## Build measured

| Part | State |
|---|---|
| Constitution of India | 471 Articles in force (all listed in the official Arrangement of Articles), official PDF (Legislative Department, as on 1 May 2024), each linked to its page; the Arrangement parsed into a table of contents |
| Supreme Court judgments | 384, 2014-2024, CC-BY-4.0 open dataset; only the Court's own numbered paragraphs |
| Index | v1, 8,946 passages of ~300 words on paragraph boundaries, SQLite FTS5 (BM25); parent expansion adds neighbouring paragraphs at answer time |
| Interfaces | Streamlit UI (research, Constitution lookup, onboarding, PDF report), REST API, MCP server (stdio + Streamable HTTP) |
| Tests | 103 passing |

## Accuracy

| Measure | Dev (47, tuned on) | Held-out (30, never tuned on) | Held-out, first run |
|---|---|---|---|
| First Article correct | 77% (36/47) | 50% (15/30) | 47% (14/30) |
| Correct Article shown | 91% (43/47) | 57% (17/30) | 53% (16/30) |
| Precision of Articles shown | 63% (43/68) | 50% (18/36) | 44% (16/36) |
| Cited judgment applies that Article | 94% (44/47) | 87% (26/30) | 63% (19/30) |
| Answered (not abstained) | 100% (47/47) | 90% (27/30) | 90% (27/30) |
| Out-of-scope refused | 8/8 | 8/8 | 8/8 |

Details: [`scenarios.md`](scenarios.md), [`scenarios_heldout.md`](scenarios_heldout.md).

Every change after the first held-out run was chosen on the dev set (parent expansion, parser fixes, the recovered Articles); the held-out set was re-run only to measure them. Recovering the 15 missing Articles left dev unchanged and cost one held-out "shown" (18 -> 17/30). Parent expansion is the main gain: judgment support for the right Article rose from 63% to 87% on held-out. Finding the right Article on new wording is still the weak point (50% first, 57% shown), because the lay-to-legal vocabulary (`retrieve/rewrite.py`) was written while reading dev misses.

Dense retrieval was measured as the fix for that and did not help: `all-minilm` embeddings fused with BM25 scored 36/47 first Article vs 37/47 keyword-only (41 vs 42 shown), at twice the answer time; dense for judgments only scored 35/47. It stays off by default. A stronger embedding model (`nomic-embed-text`, ~3 s per passage on this CPU, ~7 h to embed the corpus) or a GPU is the next thing to try, then a larger judgment corpus.

## Structure-aware retrieval (STAIR)

[`stair.md`](stair.md). STAIR (Kumar et al., IBM, arXiv 2609.03874) retrieves by reading a table of contents and naming the section that answers the query, with decoding constrained to real sections. Built here over the Constitution's official Arrangement of Articles (Parts -> chapters -> group headings -> 471 Article titles, `ingest/official.py:parse_toc`), with the local model (`retrieve/stair.py`).

| Finding the Article (dev, 47) | Recall@1 | Recall@3 |
|---|---|---|
| Keyword search over the Constitution | 18/47 | 32/47 |
| STAIR, untrained `qwen3:1.7b` | 2/47 | 2/47 |

Fused with the precedent vote at boosts 0.2 / 0.4 / 0.6 the full system scored 36 / 35 / 27 first Article (36 without), at ~17 s per question after a 6-minute first call. A two-step walk (choose a Part or group, then an Article) and generating titles instead of numbers were also tried on spot checks and were no better. Adding each Article's table-of-contents path to its indexed text left the full system unchanged (Recall@3 32 -> 31). STAIR is off by default; the paper's own untrained baselines are below BM25 too, and its gains come from fine-tuning, planned on a GPU (Phase 2 W0).

The table of contents still paid off: comparing it with the parsed Articles showed 15 Articles in force missing from the corpus (5, 36, 124C, 131, 132, 239A, 268, 323, 330A, 331-334, 371I, 395). Causes, all fixed and tested: rejected cross-reference matches swallowing the next heading; real headings ("395. Repeals.—", "131. Original jurisdiction...") read as footnotes, dropping the rest of the page; en-dash and ".-" heading endings; "3*[" markers; "371-I" numbers.

## Intensive testing

[`campaign.md`](campaign.md) (`make eval-campaign`, ~20 min). 3,380 responses (77 scenarios and 68 out-of-scope questions under 18 answer styles, plus 5 rewrites and 5 prompt attacks per scenario), each re-checked independently.

| Test | Result |
|---|---|
| Unsupported statements displayed | 0 of 3,380 responses (95% upper bound 0.09%) |
| Citations verbatim at the cited paragraph | 11,403 / 11,403 |
| Determinism across 3 processes with different hash seeds | 137/137 questions identical |
| Style invariance (same evidence per depth; Brief ⊆ Standard ⊆ Detailed) | 145/145 |
| Corrupted claims blocked (10 fault types, real answers) | 3,741 / 3,741 |
| Prompt attacks resisted | 385 / 385 |
| Refused: off-topic / foreign law / non-constitutional Indian law | 37/38 · 15/15 · 9/15 |
| Hostile REST requests / MCP calls | 0 server errors / 0 crashes |

The first campaign run found six bugs, fixed and re-measured: answers changing with the process's hash seed (the precedent vote iterated a set); changed dates and clause numbers passing the verifier (numbers compared as a set, "twenty-four" split into 20 and 4); docket numbers not checked; conversational words outranking the facts (25 -> 49/77 first Article correct when a situation is wrapped in chat); a single everyday word letting off-topic questions through (34 -> 37/38 refused); foreign-law questions answered with Indian Articles (3 -> 14/15 refused). A second round fixed the verifier's last misses (glued footnote markers, a two-word claim matching another quote, an added conclusion clause: now 3,741/3,741 blocked), dropped instruction sentences before searching (attack drift gone: 51/77 as clean), and added one-typo spelling correction (typos 43 -> 49/77). Remaining weaknesses: a request to confirm a named case still pulls retrieval toward it (37/77); non-constitutional Indian-law questions are often answered with the nearest constitutional provision. Dev and held-out accuracy were unchanged by the fixes.

**Constitution audit.** Every stored Article was read against the official PDF: the Preamble and all 12 Schedules were missing (glued onto Article 395), omitted-Article stubs sat in 8 Articles, footnote numbers in 10, the next heading trailed 26. All fixed and tested; the corpus is now 471 Articles + the Preamble + 12 Schedules (106 searchable passages). Schedules and Articles 366-367 rank behind governing Articles unless named.

**Criminal lawyer questions** ([`criminal.md`](criminal.md)): 54 routine, controversial and hostile questions x 18 styles = 972 responses, 0 crashes, 0 unsupported, 4,032/4,032 citations verbatim; a relevant Article shown for 24/26 routine and 16/18 controversial questions (the set was also used for fixes, so this is optimistic); requests for help with wrongdoing declined. Not covered: the right of private defence (IPC/BNS) and other statutes, which are not indexed yet.

## Grounding

| Measure | Result |
|---|---|
| Unsupported statements displayed | 0 (dev and held-out) |
| Quotes verbatim at the cited paragraph | 284/284 dev, 177/177 held-out |
| Answers without citations | 0 |
| Fault injection blocked | 100%, 10 corruption types |
| Phase 1 gates | 11/11 ([`latest.md`](latest.md)) |

## Component ablation (dev set)

See [`ablation.md`](ablation.md). Every component earns its place: the precedent vote and the lay-to-legal vocabulary are each worth 16-18 first-Article hits; IDF weighting 4; parent expansion 5 precedent hits; the runner-up rule adds 17 points of precision at no cost in recall; the legal-vocabulary gate is what refuses 3 of the 8 off-topic questions.

## Parsing

[`parse_audit.md`](parse_audit.md).

- **Gold set, 50 judgments** (fixed-seed sample; labels from each judgment's own PDF, disagreements reviewed by hand): 100% citation, neutral citation, date, bench, paragraph count. Building it found two paragraph bugs (numbers after a stray bullet or margin letter; paragraphs joined onto the previous line, 2 of the 50 affected) and one metadata gap (neutral citation printed in the PDF but missing from the record). All three are fixed; re-parsing changed 95 of 384 judgments.
- **Whole corpus, 384 judgments:** metadata complete 99% (3 older reports print no neutral citation), paragraphs numbered 1..N 100%, headnote leaks 3, median text captured 99%.
- **OCR:** pages without a text layer are OCRed with Tesseract through PyMuPDF (`ingest/extract.py`), tested on an image-only PDF. No judgment in the current corpus needed it.

## Performance (local only)

`eval/load_test.py`, 120 requests, 8 concurrent, verbatim mode, fresh server:

| | Errors | Throughput | p50 | p95 |
|---|---|---|---|---|
| Fresh server, uncached questions | 0 | 1.9 req/s | 1.8 s | 9.5 s |
| One user, one question at a time | 0 | - | 1.4-2.2 s | - |

Answering is CPU-bound Python, so 8 simultaneous uncached questions share one interpreter; that, not I/O, sets the concurrent p95. Phase 1 is single-user; scaling out is Phase 2. Bugs found and fixed under load: HTTP 500s from one SQLite connection shared across threads (now one per thread, WAL), and a 106 s cold start from every first request rebuilding the IDF table (now built once, at startup, under a lock).

With the LLM on, `qwen3:1.7b` on this laptop CPU (i5-1335U) generates ~9 tokens/s: 45-50 s per drafted answer even after cutting the prompt to the three best sentences per source (2,050 -> 1,277 tokens) and keeping the model loaded. Verbatim mode is the default for UI, API and MCP.

## MCP

Verified end to end with the official MCP Python client over stdio and Streamable HTTP (`tests/test_mcp_protocol.py`): tool listing, calls, and error results. `make inspector` opens the official MCP Inspector against the stdio server (needs Node.js).

## Not met in Phase 1

| Item | Status |
|---|---|
| MCP Inspector + Claude Desktop check | Ready to run (`make inspector`); not run here |
| Lawyer review of benchmark labels | Not done; labels written by the developer |
| Answer time <= 10 s with the LLM on | 45-50 s on a laptop CPU; needs a GPU or hosted model. Verbatim mode meets it |
| Eval questions written before retrieval code | The set was committed just after the retrieval module |
| CI | Deferred by decision |
