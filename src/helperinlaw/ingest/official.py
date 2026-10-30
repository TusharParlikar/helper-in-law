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
from helperinlaw.core.types import Case, Paragraph, TocEntry
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


def is_article(case_id: str) -> bool:
    """An Article, not the Preamble or a Schedule."""
    return is_provision(case_id) and case_id[len(PREFIX) : len(PREFIX) + 1].isdigit()

FOOTNOTE = re.compile(
    # Footnote numbers restart on every page, so they stay small; "131. Original jurisdiction..."
    # and "395. Repeals.—" are Article headings, not notes.
    r"^\s*(?:[1-9]|[12]\d)\.\s+(Subs|Ins|Rep\.|Added|Omitted|The words|The brackets|Cl\.|Art\.|"
    r"Arts\.|Clause|Original (?:Part|art|cl)|Renumbered|Sub-clause|Now see|Certain words|Vide|See |"
    r"Brought into force)",
)
PAGE_HEADER = re.compile(r"^\s*(THE CONSTITUTION OF INDIA|\(Part [^)]*\)|\d{1,3})\s*$")
HEADING = re.compile(
    # "2[21A." / "3*[239A." carry a footnote marker; the digits before "[" are never the number.
    # "371-I." is Article 371I. Headings end ".—", occasionally ".––" (124C) or ".-" (330A).
    r"(?:^|\s)(?:\d*\*?\[)?(?P<num>\d{1,3}[A-Z]{0,3}(?:-[A-Z]{1,2})?)\s?\.\s+(?:\d+\[)?"
    r"(?P<title>[A-Z][^—–\n]{2,160}?)\]?(?:\.?\s*(?:—|––?)|\.-)",
)
NUMERIC = re.compile(r"\d+")
ORDINALS = "FIRST SECOND THIRD FOURTH FIFTH SIXTH SEVENTH EIGHTH NINTH TENTH ELEVENTH TWELFTH".split()
SCHEDULE = re.compile(rf"^\s*\d*\[?({'|'.join(ORDINALS)}) SCHEDULE\s*$")
PARA_WORDS = 120  # a Schedule is split into passages of about this size, so a citation is precise


def document_key(name: str) -> str:
    """"Article 21" -> "21", "preamble" -> "preamble", "Seventh Schedule" / "Schedule 7" -> "schedule-7"."""
    n = " ".join(name.lower().split()).removeprefix("article").strip()
    if n == "preamble":
        return n
    if m := re.fullmatch(r"(?:the )?(\w+) schedule|schedule (\w+)", n):
        word = (m.group(1) or m.group(2)).upper()
        roman = "I II III IV V VI VII VIII IX X XI XII".split()
        k = (ORDINALS.index(word) + 1 if word in ORDINALS else roman.index(word) + 1 if word in roman
             else int(word) if word.isdigit() else 0)
        return f"schedule-{k}" if 1 <= k <= len(ORDINALS) else n
    return n.upper()


# An omitted Article's stub: "380. [Provision as to President.].—Omitted by the Constitution
# (Seventh Amendment) Act, 1956, s. 29 and Sch. (w.e.f. 1-11-1956)." Not enacted text.
OMITTED = re.compile(
    r"(?:\s\d{1,5}[A-Z]{0,2}\.)?\s*\.?\s*\[[^\[\]]{3,200}\]\s*\.?\s*[—–-]?\s*Omitted by .*?"
    r"\(w\.e\.f\.\s*[\d\- ]+\)\.?"
)
GLUED_NOTE = re.compile(r"(?<=[a-z])\d{1,2}(?:,\d{1,2})*(?=[\s;,.:)\]]|$)")  # "rules1", "notification6,5"


def tidy(text: str) -> str:
    """Drop editorial footnote markers ("1[", "3***", "order1"), page headers and omitted-Article
    stubs; rejoin words split at a line end ("twenty- one"); keep the enacted words."""
    text = " ".join(text.split())  # also folds the PDF's non-breaking spaces
    text = re.sub(r"THE CONSTITUTION OF INDIA(\s*\(Part [^)]*\))?(\s+\d{1,3}\b)?", " ", text)
    text = re.sub(r"\((?:\w+ )?Schedule\)", " ", text)  # a Schedule's running header
    text = re.sub(r"\d+\[", "[", text)
    text = re.sub(r"\d*(?:\*\s*){3,}", "", text)  # "3***" and the spaced "* * * * *"
    text = OMITTED.sub("", text)
    text = GLUED_NOTE.sub("", text)
    text = re.sub(r"(?<=[a-z])- (?=[a-z])", "-", text)
    text = re.sub(r"\s+(?=[,;:])", "", text)  # "article 32 , every" -> "article 32, every"
    return " ".join(text.split())


def clean_markers(text: str) -> str:
    """tidy(), then cut what trails an Article: the next Part's or Chapter's title ("CHAPTER
    II.—PARLIAMENT General"), a group heading ("The Attorney-General for India"), or the number
    of an omitted Article ("[2A")."""
    text = tidy(text)
    text = re.sub(r"\s+\[?PART [IVXLC]+[A-Z]?\b.*$", "", text)  # the next Part's title
    text = re.sub(r"\s*\S*CHAPTER [IVXL]+\s?\.\s*[—–-].*$", "", text)  # "1(4)CHAPTER IV.—THE UNION JUDICIARY"
    text = re.sub(r"\s+\[\d{1,3}[A-Z]{1,2}\]?$", "", text)
    text = re.sub(r"(?<=[.;:\])])\s+\[?[A-Z][A-Za-z ,-]{3,80}\]?$", "", text)  # a trailing group heading
    return text.rstrip(" [").strip(" ]")


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
    with pymupdf.open(pdf) as doc:  # type: ignore[no-untyped-call]  # pymupdf ships no type hints
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
            if SCHEDULE.match(line):  # "1[FIRST SCHEDULE": the Articles end here
                break
            body.append((page, line))
    text, pages = "", []
    for page, line in body:
        pages.append((len(text), page))
        text += " " + line.strip()

    def page_at(pos: int) -> int:
        return max((p for start, p in pages if start <= pos), default=pages[0][1] if pages else 1)

    heads = []
    last = pos = 0
    while m := HEADING.search(text, pos):
        n = int(NUMERIC.match(m.group("num")).group(0))  # type: ignore[union-attr]
        # Repealed blocks (e.g. 379-391) leave gaps; a cross-reference never has the "Title.—" form.
        if last <= n <= last + 20 and n <= 395:
            heads.append(m)
            last, pos = n, m.end()
        else:
            # A rejected match ("...article 368. PART II CITIZENSHIP 5. Citizenship...—") can
            # span a real heading: search again just after its start, not after its end.
            pos = m.start() + 1
    articles = []
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body_text = clean_markers(text[m.end() : end])
        articles.append(Article(m.group("num").replace("-", ""), " ".join(m.group("title").split()), body_text,
                                page_at(m.start())))
    # One entry per number: a later duplicate is a repeated heading, not a new article.
    seen: dict[str, Article] = {}
    for a in articles:
        seen.setdefault(a.number, a)
    return list(seen.values())


@dataclass
class Document:
    """The Preamble or a Schedule: stored like an Article, as `coi-preamble`, `coi-schedule-7`."""

    key: str
    title: str
    subtitle: str
    paragraphs: list[str]
    page: int


def parse_preamble(lines: list[tuple[int, str]]) -> Document | None:
    start = next((i for i, (_, line) in enumerate(lines) if line.strip() == "PREAMBLE"), None)
    if start is None:
        return None
    body = []
    for _, line in lines[start + 1 :]:
        if re.match(r"^\s*PART I\s*$", line):
            break
        body.append(line)
    return Document("preamble", "Preamble", "", [tidy(" ".join(body))], lines[start][0])


def parse_schedules(lines: list[tuple[int, str]]) -> list[Document]:
    """The twelve Schedules, between Article 395 and "APPENDIX I" (amending Acts, not the
    Constitution). Each Schedule's text is split at its numbered entries into ~PARA_WORDS passages."""
    first = next((i for i, (_, line) in enumerate(lines) if "Name and territory of the Union" in line), 0)
    docs: list[Document] = []
    current: tuple[int, int, list[str]] | None = None  # (ordinal, page, lines)

    def close() -> None:
        if current:
            k, page, body = current
            subtitle = body[0].strip() if body and re.match(r"^\s*[\[(]Articles?", body[0]) else ""
            text = tidy(" ".join(body[1 if subtitle else 0 :]))
            # Numbered entries first; an entry still too long is split at its sentences.
            units = [x for e in re.split(r"\s(?=\d{1,3}[A-Z]?\.\s)", text)
                     for x in (re.split(r"(?<=[.;:])\s+|(?<=[.;:][”\"])\s+", e) if len(e.split()) > PARA_WORDS else [e])]
            # A table row with no sentence end (the First Schedule's territories): cut by length.
            units = [" ".join(w[i : i + PARA_WORDS]) for u in units
                     for w in [u.split()] for i in range(0, len(w), PARA_WORDS)]
            paras: list[str] = []
            for u in units:
                if paras and len(paras[-1].split()) + len(u.split()) <= PARA_WORDS:
                    paras[-1] += " " + u
                else:
                    paras.append(u)
            docs.append(Document(f"schedule-{k}", f"{ORDINALS[k - 1].title()} Schedule",
                                 re.sub(r"^[\[(](.*)[\])]$", r"\1", tidy(subtitle)), [p for p in paras if p.strip()], page))

    for page, line in lines[first:]:
        if line.strip() == "APPENDIX I":
            break
        if m := SCHEDULE.match(line):
            close()
            current = (ORDINALS.index(m.group(1)) + 1, page, [])
        elif current:
            current[2].append(line)
    close()
    return docs


TOC_PAGES = range(3, 31)  # PDF pages 4-31: the official "Arrangement of Articles"
TOC_NOISE = re.compile(r"^(THE CONSTITUTION OF INDIA|CONTENTS|Contents|ARTICLES|PREAMBLE|\([ivxl]+\)|_+)$")
TOC_PART = re.compile(r"^(\[)?PART\s+([IVXLC]+[A-Z]?)\b")
TOC_CHAPTER = re.compile(r"^CHAPTER\s+([IVXLC]+)\.\s*(?:—\s*(.*))?$")
TOC_ENTRY = re.compile(r"^(\[)?(\d{1,3}[A-Z]{0,3})(?:-([A-Z]{1,2}))?\s?\.\s*(.*)$")


def toc_text(pdf: Path) -> str:
    """Raw text of the contents pages. Not english_lines(): that cuts each page at the first
    "____" rule, which on these pages sits under the title and would drop Parts I-II."""
    import pymupdf

    with pymupdf.open(pdf) as doc:  # type: ignore[no-untyped-call]
        return "\n".join(doc[i].get_text() for i in TOC_PAGES if i < len(doc))


def _heading(text: str) -> str:
    return " ".join(re.sub(r"\d+\[|\[|\]|\d*\*{2,}", "", text).split())


def parse_toc(text: str) -> list[TocEntry]:
    """Parts, chapters, group headings ("Right to Equality") and Article titles, in order.
    Omitted Articles ("[2A. ...—Omitted.]") are skipped; parsing stops at the Schedules.
    Numbers can be stacked before their titles ("334." "334A." then both titles), so each title
    line goes to the oldest entry whose title is still open."""
    entries: list[TocEntry] = []
    part = chapter = group = ""
    reading = ""  # which heading the next uppercase / plain lines continue
    queue: list[tuple[TocEntry, list[str], bool]] = []  # (entry, title lines, omitted)

    def done(lines: list[str], omitted: bool) -> bool:
        t = " ".join(lines).strip()
        return t.endswith("]") if omitted else _heading(t).endswith(".")

    def flush() -> None:
        for entry, lines, omitted in queue:
            if not omitted:
                entry.title = _heading(" ".join(lines)).rstrip(".").strip()
                entries.append(entry)
        queue.clear()

    for raw in text.splitlines():
        line = " ".join(raw.split())
        if not line or TOC_NOISE.match(line):
            continue
        if line.startswith("SCHEDULES"):
            break
        if m := TOC_PART.match(line):
            flush()
            part, chapter, group = f"PART {m.group(2)}", "", ""
            reading = "" if m.group(1) else "part"  # "[PART VII.—Omitted]" has no title to read
            continue
        if m := TOC_CHAPTER.match(line):
            flush()
            chapter, group = f"CHAPTER {m.group(1)}", ""
            reading = "chapter"
            if m.group(2):
                chapter += f" — {_heading(m.group(2))}"
                reading = ""
            continue
        if m := TOC_ENTRY.match(line):
            if queue and all(done(ls, o) for _, ls, o in queue):
                flush()
            reading = ""
            number = m.group(2) + (m.group(3) or "")  # "243Z-I." is Article 243ZI
            entry = TocEntry(number=number, title="", part=part, chapter=chapter, group=group)
            queue.append((entry, [m.group(4)] if m.group(4) else [], bool(m.group(1))))
            continue
        if open_ := next(((ls, o) for _, ls, o in queue if not done(ls, o)), None):
            open_[0].append(line)  # the oldest title still being read continues here
            continue
        flush()
        if reading == "part" and line.isupper():
            part += (" " if " — " in part else " — ") + _heading(line)
        elif reading == "chapter" and line.isupper():
            chapter += (" " if " — " in chapter else " — ") + _heading(line)
        elif reading == "group":
            group += " " + _heading(line)  # a heading wrapped onto a second line
        else:
            group, reading = _heading(line), "group"
    flush()
    return entries


def ingest_constitution(store: Store, pdf: Path | None = None) -> int:
    pdf = pdf or download()
    sha = sha256(pdf)
    toc = parse_toc(toc_text(pdf))
    # The official table of contents lists the Articles in force; others are "Omitted by..." stubs.
    listed = {e.number for e in toc}
    lines = english_lines(pdf)
    numbers = set()
    for a in parse_articles(lines):
        if len(a.text) >= 15 and (a.number in listed or not toc):
            store_article(store, a, sha)
            numbers.add(a.number)
    keep = set(numbers)
    for d in [p for p in [parse_preamble(lines)] if p] + parse_schedules(lines):
        store_document(store, d, sha)
        keep.add(d.key)
    for case in store.list_cases():  # stubs stored by an earlier ingest
        if is_provision(case.id) and case.id.removeprefix(PREFIX) not in keep:
            store.delete_case(case.id)
    store.replace_toc([e for e in toc if e.number in numbers])
    return len(numbers)


def store_document(store: Store, d: Document, sha: str) -> None:
    case = Case(
        id=f"{PREFIX}{d.key}",
        title=f"{d.title}, Constitution of India",
        court=COI_COURT,
        date=COI_DATE,
        citation=d.title,
        neutral_citation=d.subtitle,
        url=f"{COI_URL}#page={d.page}",
        pdf_sha256=f"{sha}:{d.key}",
    )
    store.add_case(case, [Paragraph(case_id=case.id, n=i + 1, text=t, section="provision")
                          for i, t in enumerate(d.paragraphs)])


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
