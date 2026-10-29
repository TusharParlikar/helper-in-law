# STAIR on the dev set (47 scenarios)

STAIR: the local model (`qwen3:1.7b`, untrained) reads the Constitution's official table of contents and names up to 3 Articles; decoding is constrained to real Article numbers.

## Retrieving the Article alone

| Retriever | Recall@1 | Recall@3 |
|---|---|---|
| Keyword search over the Constitution (BM25 + rewrite + rerank) | 18/47 | 32/47 |
| STAIR (table of contents, untrained) | 2/47 | 2/47 |

STAIR time per question: first 361 s (reads the whole outline), then median 17 s.

## Full system

| Configuration | First Article correct | Correct Article shown | Precision | Precedent applies it | Out-of-scope refused | Unsupported shown |
|---|---|---|---|---|---|---|
| Full system, no STAIR | 36/47 | 43/47 | 63% | 44/47 | 8/8 | 0 |
| Full system + STAIR (boost 0.2) | 36/47 | 42/47 | 63% | 44/47 | 8/8 | 0 |
| Full system + STAIR (boost 0.4) | 35/47 | 41/47 | 60% | 44/47 | 8/8 | 0 |
| Full system + STAIR (boost 0.6) | 27/47 | 33/47 | 51% | 44/47 | 8/8 | 0 |
