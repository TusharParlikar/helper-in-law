"""Research report (PDF) of the proofs behind an answer: governing provisions, analysis,
supporting judgments and a table of authorities. Only answers with verified citations get a
report; there is nothing to report without proof.

Needs the "ui" extra (fpdf2) and a serif + sans TrueType font (Georgia/Segoe UI on Windows,
DejaVu on Linux).
"""

from datetime import datetime
from hashlib import sha1
from pathlib import Path

from helperinlaw.core.store import Store
from helperinlaw.core.types import Citation, Response

NAVY, INK, MUTED, GOLD, RULE = (31, 58, 95), (28, 31, 35), (95, 107, 122), (176, 141, 87), (220, 223, 228)
FONT_SETS = [  # (serif regular, serif bold, serif italic, sans regular, sans bold)
    ("C:/Windows/Fonts/georgia.ttf", "C:/Windows/Fonts/georgiab.ttf", "C:/Windows/Fonts/georgiai.ttf",
     "C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
]


class NoProof(ValueError):
    """Raised when an answer has no verified citations: there is nothing to report."""


def has_proof(r: Response) -> bool:
    return r.confidence != "not_found" and bool(r.citations) and bool(r.answer_blocks)


def build_report(r: Response, situation: str, store: Store) -> bytes:
    if not has_proof(r):
        raise NoProof("no verified proof to report")
    from fpdf import FPDF

    fonts = next((f for f in FONT_SETS if all(Path(p).exists() for p in f)), None)
    if fonts is None:
        raise RuntimeError("no suitable TrueType fonts found for the report")
    now = datetime.now()
    ref = "HIL-" + sha1(f"{situation}{now.isoformat()}".encode()).hexdigest()[:8].upper()

    class Report(FPDF):
        def footer(self) -> None:
            self.set_y(-14)
            self.set_draw_color(*RULE)
            self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
            self.set_font("sans", "", 7.5)
            self.set_text_color(*MUTED)
            self.cell(0, 8, f"Helper in Law  ·  {ref}  ·  Research aid, not legal advice", align="L")
            self.cell(0, 8, f"Page {self.page_no()} of {{nb}}", align="R")

    pdf = Report(format="A4")
    pdf.set_margins(20, 18, 20)
    pdf.set_auto_page_break(True, margin=20)
    for style, path in zip(("", "B", "I"), fonts[:3], strict=True):
        pdf.add_font("serif", style, path)
    pdf.add_font("sans", "", fonts[3])
    pdf.add_font("sans", "B", fonts[4])
    pdf.alias_nb_pages()
    pdf.add_page()
    width = pdf.w - pdf.l_margin - pdf.r_margin

    def text(s: str, size: float = 10.5, font: str = "sans", style: str = "", color: tuple[int, int, int] = INK,
             h: float = 5.6, indent: float = 0.0) -> None:
        pdf.set_font(font, style, size)
        pdf.set_text_color(*color)
        pdf.set_x(pdf.l_margin + indent)
        pdf.multi_cell(width - indent, h, s, new_x="LMARGIN", new_y="NEXT")

    def heading(n: int, title: str) -> None:
        if pdf.get_y() > pdf.h - 45:
            pdf.add_page()
        pdf.ln(5)
        text(f"{n}.  {title.upper()}", 9, "sans", "B", NAVY, 5)
        pdf.set_draw_color(*GOLD)
        pdf.set_line_width(0.5)
        pdf.line(pdf.l_margin, pdf.get_y() + 1, pdf.l_margin + 18, pdf.get_y() + 1)
        pdf.set_line_width(0.2)
        pdf.ln(4)

    def quote(s: str, label: str) -> None:
        page, y0 = pdf.page_no(), pdf.get_y()
        text(label, 8, "sans", "B", MUTED, 4.5, indent=5)
        text(f"“{s}”", 10.5, "serif", "I", INK, 5.6, indent=5)
        pdf.set_draw_color(*GOLD)
        top = y0 if pdf.page_no() == page else pdf.t_margin  # a quote that broke across pages
        pdf.line(pdf.l_margin + 1.5, top + 0.5, pdf.l_margin + 1.5, pdf.get_y() - 0.5)
        pdf.ln(2.5)

    def link(label: str, url: str) -> None:
        pdf.set_x(pdf.l_margin + 5)
        pdf.set_font("sans", "", 8.5)
        pdf.set_text_color(*NAVY)
        pdf.write(4.6, label, link=url)
        pdf.ln(5.5)

    provisions = [c for c in r.citations if c.kind == "provision"]
    judgments = [c for c in r.citations if c.kind == "judgment"]
    order = {c.id: i + 1 for i, c in enumerate(provisions + judgments)}

    # cover block
    text("HELPER IN LAW", 9, "sans", "B", GOLD, 5)
    text("Research Report", 24, "serif", "B", INK, 11)
    text(f"Prepared {now:%d %B %Y, %H:%M}   ·   Reference {ref}", 9, "sans", "", MUTED, 5)
    pdf.ln(3)
    pdf.set_fill_color(247, 248, 250)
    pdf.set_draw_color(*RULE)
    pdf.set_font("sans", "", 8.5)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(width, 4.8, "This report sets out the constitutional provisions and judgments retrieved for the "
                   "situation below. Every quotation was checked word for word against the official source before "
                   "inclusion. It is a research aid, not legal advice.", border=1, fill=True,
                   padding=3, new_x="LMARGIN", new_y="NEXT")

    heading(1, "The situation")
    text(situation, 11, "serif", "", INK, 6)

    heading(2, "Summary")
    v = r.verification
    conf = {"high": "High", "medium": "Moderate", "low": "Review carefully"}.get(r.confidence, r.confidence)
    mode = {"synthesised": "Drafted by the local model, then verified",
            "extractive": "Verbatim passages from the sources"}.get(v.mode, v.mode)
    for k, val in [("Confidence", conf),
                   ("Statements verified", f"{v.verified} of {v.claims_proposed} proposed"),
                   ("Method", mode),
                   ("Authorities cited", f"{len({c.case_id for c in provisions})} constitutional provision(s), "
                                         f"{len({c.case_id for c in judgments})} judgment(s)")]:
        pdf.set_font("sans", "B", 9.5)
        pdf.set_text_color(*MUTED)
        pdf.cell(42, 6, k)
        pdf.set_font("sans", "", 9.5)
        pdf.set_text_color(*INK)
        pdf.cell(0, 6, val, new_x="LMARGIN", new_y="NEXT")

    section = 3
    if provisions:
        heading(section, "Governing constitutional provisions")
        section += 1
        for group in by_document(provisions):
            c = group[0]
            text(c.case_title, 12, "serif", "B", INK, 6.5)
            text(c.neutral_citation, 9, "sans", "", MUTED, 5)
            pdf.ln(1.5)
            for q in group:
                quote(q.quote, f"[{order[q.id]}]")
            link("Official text, exact page", c.url)
            text(f"Source: {c.source}", 8, "sans", "", MUTED, 4.5, indent=5)
            pdf.ln(3)

    heading(section, "Analysis")
    section += 1
    for i, b in enumerate(r.answer_blocks, 1):
        refs = " ".join(f"[{order[x]}]" for x in b.citation_ids if x in order)
        if pdf.get_y() > pdf.h - 40:
            pdf.add_page()  # never strand a number at the foot of a page
        y = pdf.get_y()
        pdf.set_font("serif", "B", 10.5)
        pdf.set_text_color(*GOLD)
        pdf.cell(7, 5.8, f"{i}.")
        pdf.set_y(y)
        text(f"{b.text.removeprefix('- ')}  {refs}", 10.5, "serif", "", INK, 5.8, indent=7)
        pdf.ln(1.5)

    if judgments:
        heading(section, "Supporting judgments")
        section += 1
        for group in by_document(judgments):
            c = group[0]
            text(c.case_title, 12, "serif", "B", INK, 6.5)
            cites = " · ".join(x for x in (c.court, c.date, c.citation, c.neutral_citation) if x)
            text(cites, 9, "sans", "", MUTED, 5)
            if c.treatment == "overruled":
                text("Treatment: overruled; do not rely on this authority without checking.", 9, "sans", "B",
                     (163, 58, 31), 5)
            arts = ", ".join(x.replace("CONST ", "Art. ") for x in c.statutes if x.startswith("CONST"))
            if arts:
                text(f"Applies: {arts}", 9, "sans", "", MUTED, 5)
            pdf.ln(1.5)
            for q in group:
                quote(q.quote, f"[{order[q.id]}]  Paragraph {q.para}")
            link(f"Read the judgment at paragraph {c.para}", c.url)
            case = store.get_case(c.case_id)
            if case and case.url:
                link("Original judgment (PDF)", case.url)
            text(f"Source: {c.source}", 8, "sans", "", MUTED, 4.5, indent=5)
            pdf.ln(3)

    notes = [n for n in r.notices if not n.startswith("Not found")]
    if notes:
        heading(section, "Notices")
        section += 1
        for n in notes:
            text(f"•  {n}", 9.5, "sans", "", INK, 5.2)

    heading(section, "Table of authorities")
    section += 1
    rows: dict[tuple[str, str], list[Citation]] = {}
    for c in provisions + judgments:
        rows.setdefault((c.case_id, c.para), []).append(c)
    for group in rows.values():
        c, nums = group[0], [order[x.id] for x in group]
        tag = f"[{nums[0]}]" if len(nums) == 1 else f"[{nums[0]}]-[{nums[-1]}]"
        where = f"para {c.para}" if c.kind == "judgment" else "official text"
        text(f"{tag}  {c.case_title}, {where}", 9, "sans", "B", INK, 4.8)
        text(c.url, 7.5, "sans", "", MUTED, 4.2, indent=6)
        pdf.ln(0.8)

    heading(section, "Limits of this research")
    cov = r.coverage
    for line in [f"Indexed sources: {cov.corpus}; as of {cov.as_of}.", *cov.limits,
                 "Verify every authority against the official record before relying on it in court.",
                 r.disclaimer]:
        text(f"•  {line}", 9, "sans", "", MUTED, 5)
    return bytes(pdf.output())


def by_document(cs: list[Citation]) -> list[list[Citation]]:
    grouped: dict[str, list[Citation]] = {}
    for c in cs:
        grouped.setdefault(c.case_id, []).append(c)
    return list(grouped.values())
