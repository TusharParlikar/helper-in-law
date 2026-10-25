"""Structure-aware chunker: paragraph-bounded chunks with a context prefix."""

from helperinlaw.core.types import Case, Chunk, Paragraph

MAX_WORDS = 300  # ~400 tokens; a single longer paragraph stays whole rather than being cut


def prefix(case: Case, a: int, b: int) -> str:
    paras = f"para {a}" if a == b else f"paras {a}-{b}"
    return f"{case.title} | {case.court} | {case.date} | {paras}"


def chunk_case(case: Case, paras: list[Paragraph], max_words: int = MAX_WORDS) -> list[Chunk]:
    chunks: list[Chunk] = []
    group: list[Paragraph] = []

    def flush() -> None:
        if group:
            a, b = group[0].n, group[-1].n
            chunks.append(
                Chunk(
                    id=f"{case.id}:{a}-{b}",
                    case_id=case.id,
                    para_from=a,
                    para_to=b,
                    text="\n".join(f"[{p.n}] {p.text}" for p in group),
                    prefix=prefix(case, a, b),
                )
            )
            group.clear()

    words = 0
    for p in paras:
        n = len(p.text.split())
        if group and words + n > max_words:
            flush()
            words = 0
        group.append(p)
        words += n
    flush()
    return chunks
