"""Judgment metadata from the header block: title, court, date, bench, case no., citations."""

import re
from datetime import datetime

from helperinlaw.core.types import Case

TITLE = re.compile(r"^(?P<t>[A-Z][^\n]{2,150}?\s+v(?:s)?\.?\s+[A-Z][^\n]{2,150})$", re.M)
COURT = re.compile(r"^IN THE (?P<c>(SUPREME COURT OF INDIA|HIGH COURT OF [A-Z .]+))$", re.M | re.I)
DATE = re.compile(r"Date of (?:Judgment|Decision)\s*:\s*(?P<d>\d{1,2}[-./]\d{1,2}[-./]\d{4})", re.I)
BENCH = re.compile(r"^(?:Bench|Coram)\s*:\s*(?P<b>.+)$", re.M | re.I)
CASE_NO = re.compile(
    r"^(?P<n>(?:CRIMINAL|CIVIL|WRIT)\s[A-Z ]*?NO\.\s*\d+\s+OF\s+\d{4})$", re.M | re.I
)
REPORTER = re.compile(r"\(\d{4}\)\s+\d+\s+[A-Z]{2,6}\s+\d+")
NEUTRAL = re.compile(r"Neutral Citation\s*:\s*(?P<n>\d{4}\s+[A-Z]{2,6}\s+\d+)", re.I)
CITATION_LINE = re.compile(r"^Citation\s*:\s*(?P<c>.+)$", re.M | re.I)


def _iso(d: str) -> str:
    day, month, year = re.split(r"[-./]", d)
    return datetime(int(year), int(month), int(day)).date().isoformat()


def short_court(court: str) -> str:
    if "SUPREME" in court.upper():
        return "SC"
    m = re.search(r"HIGH COURT OF (.+)", court, re.I)
    return f"{m.group(1).strip().title()} HC" if m else court


def parse_metadata(header: str, case_id: str, sha: str = "") -> Case:
    def grab(rx: re.Pattern[str], key: str) -> str:
        m = rx.search(header)
        return m.group(key).strip() if m else ""

    court = grab(COURT, "c")
    court = (
        "Supreme Court of India"
        if court.upper().startswith("SUPREME")
        else court.title().replace(" Of ", " of ")
    )
    date = grab(DATE, "d")
    cit_line = grab(CITATION_LINE, "c")
    reporter = REPORTER.search(cit_line)
    return Case(
        id=case_id,
        title=grab(TITLE, "t"),
        court=court,
        date=_iso(date) if date else "",
        bench=[b.strip() for b in grab(BENCH, "b").split(";") if b.strip()],
        case_no=grab(CASE_NO, "n"),
        citation=reporter.group(0) if reporter else "",
        neutral_citation=grab(NEUTRAL, "n"),
        pdf_sha256=sha,
    )
