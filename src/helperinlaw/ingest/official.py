"""Official text of the Constitution of India, fetched from the Government of India's own
publication (Legislative Department, Ministry of Law and Justice) and parsed into articles.

Every article keeps a link to the exact page of the official PDF, so any quote shown to a user
can be checked against the government text.
"""

import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from helperinlaw.core.store import Store
from helperinlaw.core.types import Case, Paragraph
from helperinlaw.ingest.extract import sha256
from helperinlaw.parse.statutes import extract_statutes

COI_URL = (
    "https://cdnbbsr.s3waas.gov.in/s380537a945c7aaa788ccfcdf1b99b5d8f/uploads/2024/07/"
    "20240716890312078.pdf"
)
COI_EDITION = "The Constitution of India [As on 1st May, 2024], Legislative Department, Ministry of Law and Justice"
COI_DATE = "2024-05-01"
COI_COURT = "Constitution of India"  # provisions are stored as documents with this "court"
LOCAL = Path("data/official/constitution_of_india_2024.pdf")
PREFIX = "coi-"


def is_provision(case_id: str) -> bool:
    return case_id.startswith(PREFIX)

FOOTNOTE = re.compile(
    r"^\s*\d+\.\s+(Subs|Ins|Rep|Added|Omitted|The words|The brackets|Cl\.|Art\.|Arts\.|Clause|"
    r"Original|Renumbered|Sub-clause|Now see|Certain words|Vide|See|Brought into force)",
)
PAGE_HEADER = re.compile(r"^\s*(THE CONSTITUTION OF INDIA|\(Part [^)]*\)|\d{1,3})\s*$")
HEADING = re.compile(
    # "2[21A." carries a footnote marker; the digits before "[" are never the article number.
    r"(?:^|\s)(?:\d+\[|\[)?(?P<num>\d{1,3}[A-Z]{0,3})\.\s+(?:\d+\[)?(?P<title>[A-Z][^—\n]{2,160}?)\]?\.?\s*—",
)
NUMERIC = re.compile(r"\d+")


def clean_markers(text: str) -> str:
    """Drop editorial footnote markers ("1[", "3***") and page rules; keep the enacted words."""
    text = " ".join(text.split())  # also folds the PDF's non-breaking spaces
    text = re.sub(r"THE CONSTITUTION OF INDIA(\s*\(Part [^)]*\))?(\s+\d{1,3}\b)?", " ", text)
    text = re.sub(r"\d+\[", "[", text)
    text = re.sub(r"\d*\*{3}", "", text)
    text = " ".join(text.split())
    text = re.sub(r"\s+PART [IVXLC]+[A-Z]?\b.*$", "", text)  # the next Part's title
    text = re.sub(r"(?<=[.;:\])])\s+[A-Z][A-Za-z ,]{3,60}$", "", text)  # a trailing group heading
    return text.strip(" ]")


@dataclass
class Article:
    number: str
    title: str
    text: str
    page: int


def download(dest: Path = LOCAL, url: str = COI_URL) -> Path:
    """Fetch the official PDF once; later calls reuse the local copy."""
    if dest.exists() and dest.stat().st_size > 100_000:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 helper-in-law"})
    with urllib.request.urlopen(req, timeout=180) as r:
        dest.write_bytes(r.read())
    return dest


def english_lines(pdf: Path) -> list[tuple[int, str]]:
    """(page, line) for English pages only; the diglot edition interleaves Hindi pages."""
    import pymupdf

    out: list[tuple[int, str]] = []
    with pymupdf.open(pdf) as doc:
        for i, page in enumerate(doc):
            text = page.get_text()
            letters = [c for c in text if c.isalpha()]
            if not letters or sum(c.isascii() for c in letters) / len(letters) < 0.9:
                continue
            # Footnotes sit below a "____" rule at the foot of the page; the text continues above it.
            body = re.split(r"\n\s*_{5,}\s*\n", text, maxsplit=1)[0]
            for line in body.splitlines():
                if FOOTNOTE.match(line):
                    break  # footnotes are one block at the bottom: the rest of the page is notes
                if not PAGE_HEADER.match(line):
                    out.append((i + 1, line))
    return out


def parse_articles(lines: list[tuple[int, str]]) -> list[Article]:
    """Article headings look like '21. Protection of life and personal liberty.—'. Accept a
    heading only if its number continues the sequence, so cross-references never split."""
    body = []
    started = False
    for page, line in lines:
        if not started and re.search(r"\b1\.\s+Name and territory of the Union\.\s*—", line):
            started = True
        if started:
            if re.match(r"^\s*(FIRST SCHEDULE|THE FIRST SCHEDULE)\b", line):
                break
            body.append((page, line))
    text, pages = "", []
    for page, line in body:
        pages.append((len(text), page))
        text += " " + line.strip()

    def page_at(pos: int) -> int:
        return max((p for start, p in pages if start <= pos), default=pages[0][1] if pages else 1)

    heads = []
    last = 0
    for m in HEADING.finditer(text):
        n = int(NUMERIC.match(m.group("num")).group(0))  # type: ignore[union-attr]
        # Repealed blocks (e.g. 379-391) leave gaps; a cross-reference never has the "Title.—" form.
        if last <= n <= last + 20 and n <= 395:
            heads.append(m)
            last = n
    articles = []
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body_text = clean_markers(text[m.end() : end])
        articles.append(Article(m.group("num"), " ".join(m.group("title").split()), body_text,
                                page_at(m.start())))
    # One entry per number: a later duplicate is a repeated heading, not a new article.
    seen: dict[str, Article] = {}
    for a in articles:
        seen.setdefault(a.number, a)
    return list(seen.values())


def ingest_constitution(store: Store, pdf: Path | None = None) -> int:
    pdf = pdf or download()
    sha = sha256(pdf)
    count = 0
    for a in parse_articles(english_lines(pdf)):
        if len(a.text) >= 15:
            store_article(store, a, sha)
            count += 1
    return count


def store_article(store: Store, a: Article, sha: str) -> None:
    case = Case(
        id=f"{PREFIX}{a.number}",
        title=f"Article {a.number}, Constitution of India",
        court=COI_COURT,
        date=COI_DATE,
        citation=f"Art. {a.number}",
        neutral_citation=a.title,
        url=f"{COI_URL}#page={a.page}",
        pdf_sha256=f"{sha}:{a.number}",
    )
    text = f"{a.title}. {a.text}"
    store.add_case(case, [Paragraph(case_id=case.id, n=1, text=text, section="provision")])
    store.add_statutes(case.id, [("CONST", a.number), *extract_statutes(a.text)])
