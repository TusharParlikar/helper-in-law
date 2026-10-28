# Ablation (live corpus, 47 scenarios + 8 out-of-scope)

Each row switches one component off; everything else stays as in the full system.

| Configuration | Top Article correct | Correct Article shown | Precision of Articles shown | Precedent applies it | Out-of-scope refused | Unsupported shown |
|---|---|---|---|---|---|---|
| Full system | 36/47 | 43/47 | 63% | 44/47 | 8/8 | 0 |
| - lay-to-legal vocabulary | 20/47 | 23/47 | 43% | 38/47 | 8/8 | 0 |
| - precedent vote for Articles | 18/47 | 21/47 | 30% | 44/47 | 8/8 | 0 |
| - IDF weighting in reranker | 32/47 | 38/47 | 55% | 44/47 | 8/8 | 0 |
| - runner-up rule (always 2 Articles) | 36/47 | 43/47 | 46% | 44/47 | 8/8 | 0 |
| - legal-vocabulary gate | 36/47 | 43/47 | 63% | 44/47 | 5/8 | 0 |
| - parent expansion (matched paragraphs only) | 36/47 | 43/47 | 63% | 39/47 | 8/8 | 0 |
