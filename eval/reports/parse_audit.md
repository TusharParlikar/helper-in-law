# Parser audit (real Supreme Court judgments)

384 judgments in the corpus.

## Gold set (50 judgments)

Labels taken from each judgment's own PDF (first page: citation, neutral citation, date, bench; paragraph count after checking that no later paragraph number is left inside the last paragraph). Every disagreement with the parser was reviewed by hand against the PDF; the sample is drawn with a fixed seed. Paragraphs are re-parsed from the PDF on every run. Building it found two parser bugs (paragraph numbers after a stray bullet or margin letter, and paragraphs joined onto the previous line) and one metadata gap (neutral citation missing from the record but printed in the PDF): before those fixes the parser scored 48/50 on paragraphs and 49/50 on neutral citations.

| Field | Correct |
|---|---|
| citation | 50/50 (100%) |
| neutral citation | 50/50 (100%) |
| date | 50/50 (100%) |
| judges | 50/50 (100%) |
| paragraphs | 50/50 (100%) |

## Whole corpus (automated consistency checks)

| Check | Result |
|---|---|
| Metadata complete (title, date, bench, SCR citation, neutral citation) | 381/384 (99%) |
| Paragraphs numbered 1..N with no gaps, at least 3 | 384/384 (100%) |
| Editorial headnote text leaking into the first paragraphs | 3/384 |
| Share of the judgment's text captured in numbered paragraphs (median) | 99% |
| Judgments with under 60% captured (likely concurring opinions or annexures dropped) | 1/384 |

Metadata comes from the Supreme Court's own e-SCR records. Paragraph numbering and coverage come from the parser. Concurring and dissenting opinions restart their numbering and are not yet captured; that is the main source of low coverage.
