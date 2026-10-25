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
