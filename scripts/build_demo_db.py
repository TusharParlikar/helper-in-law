"""Build the read-only database shipped with the Streamlit demo (deploy/helperinlaw.db.gz).

uv run python scripts/build_demo_db.py

Keeps the served index version only and drops local state (profiles, feedback, answers,
eval runs, the dead-letter table, unused index versions and embeddings).
"""

import gzip
import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from helperinlaw.core.config import settings  # noqa: E402

OUT = ROOT / "deploy" / "helperinlaw.db.gz"


def main() -> None:
    tmp = ROOT / "deploy" / "helperinlaw.db"
    tmp.unlink(missing_ok=True)
    src = sqlite3.connect(settings.db_path)
    dst = sqlite3.connect(tmp)
    src.backup(dst)  # consistent copy, including anything still in the WAL
    src.close()
    v = settings.index_version
    with dst:
        dst.execute("DELETE FROM chunks WHERE index_version != ?", (v,))
        dst.execute("DELETE FROM chunks_fts WHERE index_version != ?", (v,))
        for table in ("embeddings", "user_profiles", "feedback", "answers", "eval_runs", "dead_letter"):
            dst.execute(f"DELETE FROM {table}")
    dst.isolation_level = None  # VACUUM cannot run inside a transaction
    dst.execute("INSERT INTO chunks_fts(chunks_fts) VALUES ('optimize')")
    dst.execute("PRAGMA journal_mode=DELETE")
    dst.execute("VACUUM")
    dst.close()
    with tmp.open("rb") as f, gzip.open(OUT, "wb", compresslevel=9) as g:
        shutil.copyfileobj(f, g)
    print(f"{tmp.stat().st_size / 1e6:.0f} MB -> {OUT.name} {OUT.stat().st_size / 1e6:.0f} MB")
    tmp.unlink()


if __name__ == "__main__":
    main()
