# Scenario benchmark

- Mode: verbatim passages (no LLM); search: keyword
- Corpus: Constitution of India, 461 articles (official text as on 1 May 2024); 384 judgments (2014-2024)
- 47 lawyer-style scenarios labelled with the governing Article(s), plus 8 out-of-scope questions.
- Labels are standard constitutional law written by the developer, not yet reviewed by a lawyer.

## Results

| Measure | Result |
|---|---|
| Correct Article is the top provision shown | 79% (37/47) |
| Correct Article among the provisions shown | 89% (42/47) |
| Provisions shown that are on point (precision) | 63% (42/67) |
| A cited judgment applies that Article | 83% (39/47) |
| Scenarios answered (not abstained) | 100% (47/47) |
| Out-of-scope questions correctly refused | 100% (8/8) |
| Unsupported statements displayed | **0** |
| Quotes found verbatim at their cited paragraph | 100% (240/240) |
| Answers without citations | **0** |
| Latency p50 / p95 | 1.41 s / 1.99 s |

## By area

| Area | Scenarios | Top Article correct | Correct Article shown |
|---|---|---|---|
| arrest and detention | 4 | 100% (4/4) | 100% (4/4) |
| criminal process | 3 | 67% (2/3) | 67% (2/3) |
| discrimination | 3 | 67% (2/3) | 100% (3/3) |
| education | 2 | 50% (1/2) | 50% (1/2) |
| equality | 4 | 25% (1/4) | 75% (3/4) |
| exploitation | 2 | 50% (1/2) | 100% (2/2) |
| life and personal liberty | 12 | 92% (11/12) | 92% (11/12) |
| minority rights | 1 | 100% (1/1) | 100% (1/1) |
| property | 1 | 0% (0/1) | 0% (0/1) |
| public employment | 3 | 67% (2/3) | 100% (3/3) |
| religion | 2 | 100% (2/2) | 100% (2/2) |
| service law | 1 | 100% (1/1) | 100% (1/1) |
| speech and expression | 5 | 100% (5/5) | 100% (5/5) |
| trade and occupation | 2 | 100% (2/2) | 100% (2/2) |
| writs | 2 | 100% (2/2) | 100% (2/2) |

## Misses (5)

| Scenario | Expected | Shown |
|---|---|---|
| My client is an 80-year-old widow with no income, abandoned by her children, and the State | Art. 21 | Art. 39 |
| A government order was passed arbitrarily, without reasons and without hearing the people  | Art. 14 | Art. 226 |
| My client is being punished under a law that was made after he committed the act. | Art. 20 | Art. 243ZL, Art. 356 |
| A private school refuses to admit children from poor families under the free seats quota. | Art. 21A | Art. 15, Art. 51A |
| My client's land was taken by the State for a project without any law authorising it and w | Art. 300A | Art. 243ZQ, Art. 366 |
