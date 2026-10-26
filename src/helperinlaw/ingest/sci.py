"""Real Supreme Court of India judgments from the Indian Supreme Court Judgments open dataset
(AWS Open Data, maintained by Dattam Labs, CC-BY-4.0; judgments as published by the Supreme
Court in e-SCR). Only judgments whose headnotes apply selected constitutional articles are
fetched, and only the Court's own paragraphs are indexed (not the editorial headnotes).
"""

import html
import io
import json
import re
import tarfile
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from helperinlaw.core.logging import get_logger
from helperinlaw.core.store import Store
from helperinlaw.core.types import Case, Paragraph
from helperinlaw.ingest.clean import clean
from helperinlaw.ingest.extract import extract_text, quality, sha256
from helperinlaw.parse.paragraphs import split_paragraphs
from helperinlaw.parse.sections import label
from helperinlaw.parse.statutes import extract_statutes

log = get_logger(__name__)
BUCKET = "https://indian-supreme-court-judgments.s3.amazonaws.com"
RAW = Path("data/raw/sci")
# Fundamental rights and writ articles a scenario most often turns on.
KEY_ARTICLES = re.compile(
    r"\bArt(?:icle|s?\.)\s*(14|15|16|19|20|21|21A|22|25|32|226|300A|311)\b", re.I
)
FIRST_PARA = re.compile(r"(\b(?:CJI|J)\.?\s*:?)\s+(1\.\s+[A-Z])")
NEW_LAYOUT = re.compile(r"Judgment\s*/\s*Order of the Supreme Court\s*\n\s*(?:Judgment|Order)\s*\n")  # 2024
JURISDICTION = re.compile(r"\b(?:CIVIL|CRIMINAL)?\s*(?:APPELLATE|ORIGINAL|ADVISORY)\s+JURISDICTION\b")
DELIVERED = re.compile(r"(?:The\s+)?Judgments?\s+of\s+the\s+Court\s+(?:was|were)\s+delivered\s+by", re.I)
SPACED = re.compile(r"^\s*J\s*U\s*D\s*G\s*M\s*E\s*N\s*T\s*$|^\s*JUDGMENT\s*$", re.M)


def judgment_start(text: str) -> int:
    """Where the Court's own text begins, after the editorial headnote. Older reports put an
    "APPELLATE JURISDICTION" heading just before it; anything before that heading is headnote."""
    if m := NEW_LAYOUT.search(text):
        return m.end()
    heads = list(JURISDICTION.finditer(text))
    after = heads[-1].end() if heads else 0
    for rx in (DELIVERED, SPACED):
        if m := rx.search(text, after):
            return m.end()
    return after


AUTHOR_LINE = re.compile(r"^\s*[A-Z][A-Za-z.\s]{2,60},\s*(?:CJI|J)\.?\s*:?\s*$", re.M)
NUMBERED = re.compile(r"^\s*(\d{1,4})\.\s", re.M)


@dataclass
class Meta:
    path: str
    title: str
    citation: str
    neutral: str
    coram: list[str]
    date: str
    case_no: str
    headnote: str = ""
    extra: dict[str, str] = field(default_factory=dict)

    @property
    def pdf_url(self) -> str:
        return f"{BUCKET}/data/pdf/year={self.date[:4]}/english/{self.path}_EN.pdf"


def _get(url: str, dest: Path) -> Path:
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(urllib.request.Request(url), timeout=180) as r:
        dest.write_bytes(r.read())
    return dest


def _text(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def title_case(name: str) -> str:
    """"D.Y. CHANDRACHUD" -> "D.Y. Chandrachud"; small words stay lower-case mid-name."""
    small = {"of", "and", "the", "&", "for", "in", "on"}
    words = name.lower().split()
    return " ".join(w if i and w in small else w.title() for i, w in enumerate(words))


def party(side: str) -> str:
    # Some records repeat the cause title after an SCR page number: "STATE OF KERALA 561 INDIAN ..."
    return re.sub(r"\s+\d{2,4}\s+.*$", "", _text(side))


def parse_meta(raw: str, path: str, neutral: str) -> Meta | None:
    m = re.search(r"<strong>(.*?)<span class='fst-italic'>\s*versus\s*</span>(.*?)</strong>", raw, re.S)
    date = re.search(r"Decision Date :</span><font[^>]*>\s*([\d-]+)", raw)
    if not m or not date:
        return None
    coram = re.search(r"Coram :(.*?)</strong>", raw, re.S)
    head = re.search(r"Coram :.*?</strong><br>(.*?)<br><strong class='caseDetailsTD'", raw, re.S)
    escr = re.search(r"class='escrText'>([^<]+)<", raw)
    case_no = re.search(r"Case No :</span><font[^>]*>([^<]+)<", raw)
    d, mo, y = date.group(1).split("-")
    nc = re.sub(r"(\d{4})(INSC)(\d+)", r"\1 \2 \3", neutral or "")
    return Meta(
        path=path,
        title=f"{title_case(party(m.group(1)))} v. {title_case(party(m.group(2)))}",
        citation=_text(escr.group(1)) if escr else "",
        neutral=nc,
        coram=[title_case(c.strip()) for c in re.sub(r"<sup.*?</sup>", "", coram.group(1) if coram else "").split(",") if c.strip()],
        date=datetime(int(y), int(mo), int(d)).date().isoformat(),
        case_no=_text(case_no.group(1)) if case_no else "",
        headnote=_text(head.group(1)) if head else "",
    )


def year_metadata(year: int) -> list[Meta]:
    tar = _get(f"{BUCKET}/metadata/tar/year={year}/metadata.tar", RAW / f"metadata_{year}.tar")
    out = []
    with tarfile.open(tar) as t:
        for member in t.getmembers():
            if not member.name.endswith(".json"):
                continue
            f = t.extractfile(member)
            if f is None:
                continue
            d = json.load(io.TextIOWrapper(f, encoding="utf-8"))
            if meta := parse_meta(d.get("raw_html", ""), d.get("path", ""), d.get("nc_display", "")):
                out.append(meta)
    return out


def judgment_paragraphs(text: str) -> list[tuple[int, str]]:
    """The Court's own numbered paragraphs, after the editorial headnote."""
    body = text[judgment_start(text):]
    # Paragraph 1 often shares a line with the author: "R. K. AGRAWAL, J. 1. The jurisdiction..."
    body = FIRST_PARA.sub(r"\1\n\2", body, count=1)
    # Many judgments leave paragraph 1 unnumbered ("Leave granted.") and print numbers from 2.
    first = NUMBERED.search(body)
    if first and first.group(1) == "2":
        lead = AUTHOR_LINE.sub("", body[: first.start()]).strip()
        if lead:
            body = f"1. {lead}\n{body[first.start():]}"
    _, paras = split_paragraphs(body)
    return paras


def ingest_judgment(store: Store, meta: Meta) -> str:
    case_id = f"sc-{meta.neutral.replace(' ', '-').lower() or meta.path}"
    if store.get_case(case_id):
        return "skipped"
    pdf = _get(meta.pdf_url, RAW / f"{meta.path}.pdf")
    raw = extract_text(pdf)
    if quality(raw) < 0.6:
        raise ValueError(f"extraction quality {quality(raw):.2f}")
    paras = judgment_paragraphs(clean(raw))
    if len(paras) < 3:
        raise ValueError("no numbered judgment paragraphs")
    case = Case(id=case_id, title=meta.title, court="Supreme Court of India", date=meta.date,
                bench=meta.coram, case_no=meta.case_no, citation=meta.citation,
                neutral_citation=meta.neutral, url=meta.pdf_url, pdf_sha256=sha256(pdf))
    store.add_case(case, [Paragraph(case_id=case_id, n=n, text=t, section=label(t, n)) for n, t in paras])
    store.add_statutes(case_id, extract_statutes(" ".join(t for _, t in paras)))
    return "ingested"


def reparse(store: Store) -> dict[str, int]:
    """Re-run paragraph parsing on already-ingested judgments from their cached PDFs (after a
    parser fix). Updates paragraphs and statutes in place; metadata is unchanged."""
    changed = unchanged = 0
    for case in store.list_cases():
        if not case.id.startswith("sc-"):
            continue
        pdf = RAW / f"{Path(case.url).stem.removesuffix('_EN')}.pdf"
        if not pdf.exists():
            continue
        paras = judgment_paragraphs(clean(extract_text(pdf)))
        old = [(p.n, p.text) for p in store.get_paragraphs(case.id)]
        if len(paras) < 3 or paras == old:
            unchanged += 1
            continue
        store.add_case(case, [Paragraph(case_id=case.id, n=n, text=t, section=label(t, n)) for n, t in paras])
        store.add_statutes(case.id, extract_statutes(" ".join(t for _, t in paras)))
        changed += 1
    return {"reparsed": changed, "unchanged": unchanged}


def ingest_sci(store: Store, years: range, limit: int, pattern: re.Pattern[str] = KEY_ARTICLES) -> dict[str, int]:
    """Fetch up to `limit` judgments (newest years first) whose headnotes cite `pattern`."""
    done = failed = 0
    for year in sorted(years, reverse=True):
        for meta in year_metadata(year):
            if done >= limit:
                return {"ingested": done, "failed": failed}
            if not pattern.search(meta.headnote):
                continue
            try:
                done += ingest_judgment(store, meta) == "ingested"
            except Exception as e:  # one bad PDF must not stop the batch
                failed += 1
                store.dead_letter(meta.pdf_url, str(e))
                log.warning("sci ingest failed", extra={"extra_fields": {"path": meta.path, "err": str(e)}})
    return {"ingested": done, "failed": failed}
