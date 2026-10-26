# Parser audit (real Supreme Court judgments)

384 judgments in the corpus. Automated consistency checks, not a hand-labelled gold set.

| Check | Result |
|---|---|
| Metadata complete (title, date, bench, SCR citation, neutral citation) | 380/384 (99%) |
| Paragraphs numbered 1..N with no gaps, at least 3 | 384/384 (100%) |
| Editorial headnote text leaking into the first paragraphs | 3/384 |
| Share of the judgment's text captured in numbered paragraphs (median) | 99% |
| Judgments with under 60% captured (likely concurring opinions or annexures dropped) | 1/384 |

Metadata comes from the Supreme Court's own e-SCR records. Paragraph numbering and coverage come from the parser. Concurring and dissenting opinions restart their numbering and are not yet captured; that is the main source of low coverage.
