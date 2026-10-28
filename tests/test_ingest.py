from pathlib import Path

from helperinlaw.core.store import Store
from helperinlaw.ingest.clean import clean
from helperinlaw.ingest.extract import quality
from helperinlaw.ingest.pipeline import ingest_dir


def test_cleaner_drops_page_numbers_and_running_headers() -> None:
    text = (
        "HEADER LINE\n1. First para con-\ntinues here.\nPage 1 of 3\nHEADER LINE\n"
        "2. Second.\n- 2 -\nHEADER LINE\n"
    )
    out = clean(text)
    assert "Page 1" not in out and "HEADER LINE" not in out and "- 2 -" not in out
    assert "continues here" in out


def test_quality_flags_garbage() -> None:
    assert quality("The court held that bail is the rule. " * 20) > 0.7
    assert quality("@#$%^ 1234 ~~ ;;; " * 30) < 0.3


def test_ingest_is_idempotent_and_dead_letters_bad_files(tmp_path: Path, store: Store) -> None:
    (tmp_path / "bad.txt").write_text("@@@ ### " * 100)
    (tmp_path / "nopara.txt").write_text("Just some text without numbered paragraphs. " * 20)
    s = Store(":memory:")
    first = ingest_dir(s, tmp_path)
    assert set(first.failed) == {"bad.txt", "nopara.txt"}
    assert len(s.dead_letters()) == 2

    sample = Path(__file__).parent.parent / "data" / "sample"
    r1 = ingest_dir(s, sample)
    r2 = ingest_dir(s, sample)
    assert len(r1.ingested) == 8 and len(r2.skipped) == 8 and not r2.ingested


def test_scanned_page_is_ocred(tmp_path: Path) -> None:
    import pytest

    fitz = pytest.importorskip("fitz")
    from helperinlaw.ingest.extract import extract_text, tessdata

    if not tessdata():
        pytest.skip("Tesseract not installed")
    # Render a text page to an image and build a PDF from the image alone: no text layer.
    src = fitz.open()
    src.new_page().insert_text((72, 100), "The appeal is allowed and the detention is quashed.", fontsize=16)
    pix = src[0].get_pixmap(dpi=200)
    scan = fitz.open()
    scan.new_page().insert_image(scan[0].rect, pixmap=pix)
    path = tmp_path / "scan.pdf"
    scan.save(path)
    assert fitz.open(path)[0].get_text().strip() == ""
    assert "detention is quashed" in extract_text(path)
