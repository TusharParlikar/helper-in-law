# Phase 1 evaluation report

- Commit: `03473da`
- Mode: llm=qwen3:1.7b, dense
- Corpus: Sample corpus (fictional test judgments)

## Exit criteria (§7)

| Metric | Value | Target | Pass |
|---|---|---|---|
| recall@10 | 1.0 | >= 0.85 | ✅ |
| mrr | 1.0 | >= 0.6 | ✅ |
| unsupported_claims_displayed | 0 | == 0 | ✅ |
| citation_accuracy | 1.0 | >= 0.99 | ✅ |
| responses_lacking_citations | 0 | == 0 | ✅ |
| abstain_correctness | 1.0 | >= 0.9 | ✅ |
| false_premise_rejection | 1.0 | >= 0.9 | ✅ |
| injection_pass_rate | 1.0 | == 1.0 | ✅ |
| style_invariance | 1.0 | == 1.0 | ✅ |
| p95_ask_latency_s | 58.326 | <= 10.0 | ❌ |
| parser_accuracy | 1.0 | >= 0.95 | ✅ |

Also: answer rate 0.867, verification keep rate 0.75.

## Retrieval ablation

| Pipeline | Recall@10 | MRR |
|---|---|---|
| BM25 | 1.0 | 0.983 |
| +rewrite | 1.0 | 0.889 |
| +rerank | 1.0 | 1.0 |
| +dense (hybrid RRF) | 1.0 | 1.0 |

## Reading the zero

0 unsupported claims in 40 responses: by the rule of three the 95% upper bound on the per-response failure rate is about 7.5%. Phase 3 widens the sample.

The sample corpus is 8 fictional judgments; these numbers prove the pipeline and its gates, not quality on real judgments.
