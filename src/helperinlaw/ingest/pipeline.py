"""Ingest: extract -> quality gate -> clean -> parse -> store. Idempotent by sha256;
failures go to the dead-letter table, never silently skipped."""

from dataclasses import dataclass, field
from pathlib import Path

from helperinlaw.core.logging import get_logger
from helperinlaw.core.store import Store
from helperinlaw.core.types import Paragraph
from helperinlaw.ingest.clean import clean
from helperinlaw.ingest.extract import extract_text, quality, sha256
from helperinlaw.parse.citations import extract_citations
from helperinlaw.parse.metadata import parse_metadata
from helperinlaw.parse.paragraphs import split_paragraphs
from helperinlaw.parse.sections import label
from helperinlaw.parse.statutes import extract_statutes

log = get_logger(__name__)
MIN_QUALITY = 0.6


@dataclass
class Report:
    ingested: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)


def ingest_file(store: Store, path: Path) -> str:
    """Returns 'ingested' or 'skipped'. Raises ValueError with the reason on failure."""
    sha = sha256(path)
    if store.has_sha(sha):
        return "skipped"
    raw = extract_text(path)
    if quality(raw) < MIN_QUALITY:
        raise ValueError(f"extraction quality {quality(raw):.2f} < {MIN_QUALITY}")
    header, paras = split_paragraphs(clean(raw))
    if not paras:
        raise ValueError("no numbered paragraphs found")
    case = parse_metadata(header, case_id=path.stem, sha=sha)
    if not case.title or not case.date:
        raise ValueError("missing title or date")
    store.add_case(
        case, [Paragraph(case_id=case.id, n=n, text=t, section=label(t, n)) for n, t in paras]
    )
    store.add_statutes(case.id, extract_statutes(header + "\n" + "\n".join(t for _, t in paras)))
    return "ingested"


def link_citations(store: Store) -> int:
    """Resolve case->case citations once every case is stored (cited cases may arrive later)."""
    edges = 0
    for case in store.list_cases():
        paras = [(p.n, p.text) for p in store.get_paragraphs(case.id)]
        # one edge per cited case: the same judgment cited by its SCR and its INSC citation
        # counts once, with the strongest treatment seen
        rank = {"overruled": 3, "distinguished": 2, "followed": 1, "unknown": 0}
        best: dict[str, tuple[str, int]] = {}
        for cit, treatment, n in extract_citations(paras):
            target = store.resolve_citation(cit)
            if target and target != case.id and (
                target not in best or rank[treatment] > rank[best[target][0]]
            ):
                best[target] = (treatment, n)
        resolved = [(t, tr, n) for t, (tr, n) in best.items()]
        store.add_citations(case.id, resolved)
        edges += len(resolved)
    return edges


def ingest_dir(store: Store, folder: Path, limit: int | None = None) -> Report:
    report = Report()
    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in {".txt", ".pdf"})
    for path in files[:limit]:
        try:
            status = ingest_file(store, path)
            (report.ingested if status == "ingested" else report.skipped).append(path.name)
        except Exception as e:  # anything unexpected is a dead letter, not a crash
            report.failed[path.name] = str(e)
            store.dead_letter(str(path), str(e))
            log.warning("ingest failed", extra={"extra_fields": {"path": str(path), "err": str(e)}})
    link_citations(store)
    return report
