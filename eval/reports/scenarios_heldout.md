# Scenario benchmark (held-out set)

- Mode: verbatim passages (no LLM); search: keyword
- Corpus: Constitution of India, 471 articles (official text as on 1 May 2024); 384 judgments (2014-2024)
- 30 lawyer-style scenarios labelled with the governing Article(s), plus 8 out-of-scope questions.
- Labels are standard constitutional law written by the developer, not yet reviewed by a lawyer.

## Results

| Measure | Result |
|---|---|
| Correct Article is the top provision shown | 50% (15/30) |
| Correct Article among the provisions shown | 57% (17/30) |
| Provisions shown that are on point (precision) | 50% (18/36) |
| A cited judgment applies that Article | 87% (26/30) |
| Scenarios answered (not abstained) | 90% (27/30) |
| Out-of-scope questions correctly refused | 100% (8/8) |
| Unsupported statements displayed | **0** |
| Quotes found verbatim at their cited paragraph | 100% (178/178) |
| Answers without citations | **0** |
| Latency p50 / p95 | 0.62 s / 1.4 s |

## By area

| Area | Scenarios | Top Article correct | Correct Article shown |
|---|---|---|---|
| arrest and detention | 2 | 100% (2/2) | 100% (2/2) |
| criminal process | 3 | 33% (1/3) | 67% (2/3) |
| discrimination | 2 | 50% (1/2) | 50% (1/2) |
| education | 1 | 0% (0/1) | 0% (0/1) |
| equality | 3 | 67% (2/3) | 100% (3/3) |
| exploitation | 2 | 0% (0/2) | 0% (0/2) |
| life and personal liberty | 5 | 40% (2/5) | 40% (2/5) |
| minority rights | 1 | 100% (1/1) | 100% (1/1) |
| property | 1 | 0% (0/1) | 0% (0/1) |
| public employment | 2 | 50% (1/2) | 50% (1/2) |
| religion | 2 | 50% (1/2) | 50% (1/2) |
| service law | 1 | 100% (1/1) | 100% (1/1) |
| speech and expression | 3 | 33% (1/3) | 33% (1/3) |
| trade and occupation | 1 | 100% (1/1) | 100% (1/1) |
| writs | 1 | 100% (1/1) | 100% (1/1) |

## Misses (13)

| Scenario | Expected | Shown |
|---|---|---|
| The state government is forcibly evicting pavement dwellers in the city without offering a | Art. 21 | Art. 14 |
| A prisoner sentenced to death has been waiting for over ten years for his mercy petition t | Art. 21 | Art. 72 |
| The government is collecting citizens' biometric data and sharing it with private companie | Art. 21 | Art. 32, Art. 19 |
| A new law increases the punishment for an offence and the prosecution wants to apply it to | Art. 20 | Art. 19, Art. 14 |
| A university suspended a student for posting a satirical cartoon about the vice-chancellor | Art. 19 | none |
| Lawyers in a district have been forbidden from forming an association. | Art. 19 | Art. 17 |
| A housing society refuses to sell flats to people of a particular religion. | Art. 15 | Art. 19 |
| Women officers were denied permanent commission in the armed forces while men in the same  | Art. 14, 15, 16 | Art. 33 |
| Migrant workers at a construction site are paid less than the minimum wage and cannot leav | Art. 23 | none |
| Children are working in a glass factory where they handle furnaces. | Art. 24 | Art. 39 |
| The police stopped a community from performing a religious procession that they had perfor | Art. 25, 19 | none |
| A state has not set up enough schools for children in tribal areas and many children are o | Art. 21A | Art. 15, Art. 51A |
| The municipality demolished my client's shop and took over the land without any acquisitio | Art. 300A | Art. 31A, Art. 323B |
