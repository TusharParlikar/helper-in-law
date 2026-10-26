# Phase 1 evaluation report

Scope: everything Phase 1 of [`docs/ROADMAP.md`](../../docs/ROADMAP.md) asks for, measured locally. No CI, no deployment, no authentication (Phase 2).

## Build measured

| Part | State |
|---|---|
| Constitution of India | 461 articles, official PDF (Legislative Department, as on 1 May 2024), each linked to its page |
| Supreme Court judgments | 384, 2014-2024, CC-BY-4.0 open dataset; only the Court's own numbered paragraphs |
| Index | v1, 8,814 passages of ~300 words on paragraph boundaries, SQLite FTS5 (BM25); dense embeddings not built |
| Interfaces | Streamlit UI (research, Constitution lookup, onboarding, PDF report), REST API, MCP server (stdio + Streamable HTTP) |
| Tests | 82 passing |

## Accuracy

| Measure | Dev (47, tuned on) | Held-out (30, run once) |
|---|---|---|
| First Article correct | 79% (37/47) | 47% (14/30) |
| Correct Article shown | 89% (42/47) | 53% (16/30) |
| Precision of Articles shown | 63% (42/67) | 44% (16/36) |
| Cited judgment applies that Article | 83% (39/47) | 63% (19/30) |
| Answered (not abstained) | 100% (47/47) | 90% (27/30) |
| Out-of-scope refused | 8/8 | 8/8 |

Details: [`scenarios.md`](scenarios.md), [`scenarios_heldout.md`](scenarios_heldout.md).

The dev-to-held-out drop is the main finding. The lay-to-legal vocabulary (`retrieve/rewrite.py`) was written while reading dev misses; new phrasings fall outside it. The held-out set was not used for any change. Next lever, in order of expected gain: dense embeddings for vocabulary-independent recall (built in `index/build.py`, needs an embedding model), then a larger judgment corpus.

## Grounding

| Measure | Result |
|---|---|
| Unsupported statements displayed | 0 (dev and held-out) |
| Quotes verbatim at the cited paragraph | 240/240 dev, 142/142 held-out |
| Answers without citations | 0 |
| Fault injection blocked | 100%, 10 corruption types |
| Phase 1 gates | 11/11 ([`latest.md`](latest.md)) |

## Component ablation (dev set)

See [`ablation.md`](ablation.md). Every component earns its place: the precedent vote and the lay-to-legal vocabulary are each worth about 17-19 first-Article hits; IDF weighting 5; the runner-up rule costs nothing in recall and adds 18 points of precision; the legal-vocabulary gate is what refuses 3 of the 8 off-topic questions.

## Parsing

[`parse_audit.md`](parse_audit.md), 384 judgments: metadata complete 99%, paragraphs numbered 1..N 100%, headnote leaks 3, median text captured 99%, 1 judgment under 60% (separate opinions restart numbering and are not yet captured). OCR was not needed: every PDF had a text layer; unreadable files go to the dead-letter table.

## Performance (local only)

`eval/load_test.py`, 120 requests, 8 concurrent, verbatim mode:

| Run | Errors | Throughput | p50 | p95 |
|---|---|---|---|---|
| Warm server | 0 | 4.2 req/s | 1.9 s | 2.3 s |
| Fresh server | 0 | 1.8 req/s | 2.2 s | 8.8 s |

Two bugs found and fixed: concurrent requests on one SQLite connection returned HTTP 500 (now one connection per thread, WAL); concurrent first requests each rebuilt the IDF table, giving a 106 s cold start (now built once under a lock, at API startup).

## MCP

Verified end to end with the official MCP Python client over stdio and Streamable HTTP (`tests/test_mcp_protocol.py`): tool listing, calls, and error results.

## Not met in Phase 1

| Item | Status |
|---|---|
| Answer time <= 10 s with the LLM on | Not met: about 60 s with `qwen3:1.7b` on CPU. Default verbatim mode meets it |
| Lawyer review of benchmark labels | Not done; labels written by the developer |
| Dense / hybrid retrieval | Code present, embeddings not built (no GPU); keyword only in all numbers above |
| Held-out accuracy | 47% first Article; below the dev figure, see above |
| CI | Deferred by decision |
