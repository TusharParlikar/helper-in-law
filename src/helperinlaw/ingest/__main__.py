"""Build the corpus.

python -m helperinlaw.ingest --constitution              # official Constitution of India
python -m helperinlaw.ingest --sci 2014-2024 --limit 150 # real Supreme Court judgments
python -m helperinlaw.ingest data/sample                 # a folder of .txt/.pdf judgments
"""

import argparse
import json
from pathlib import Path

from helperinlaw.core.config import settings
from helperinlaw.core.logging import setup_logging
from helperinlaw.core.store import Store
from helperinlaw.ingest.official import ingest_constitution
from helperinlaw.ingest.pipeline import ingest_dir, link_citations
from helperinlaw.ingest.sci import ingest_sci

setup_logging()
ap = argparse.ArgumentParser(description="Ingest the Constitution, Supreme Court judgments or a folder")
ap.add_argument("folder", nargs="?")
ap.add_argument("--constitution", action="store_true", help="official Constitution of India (2024)")
ap.add_argument("--sci", metavar="FROM-TO", help="Supreme Court judgments for these years, e.g. 2014-2024")
ap.add_argument("--limit", type=int, default=150)
args = ap.parse_args()
store = Store(settings.db_path)
out: dict[str, object] = {}
if args.constitution:
    out["constitution_articles"] = ingest_constitution(store)
if args.sci:
    a, _, b = args.sci.partition("-")
    out["supreme_court"] = ingest_sci(store, range(int(a), int(b or a) + 1), args.limit)
if args.folder:
    r = ingest_dir(store, Path(args.folder), args.limit)
    out["folder"] = {"ingested": len(r.ingested), "skipped": len(r.skipped), "failed": r.failed}
if not out:
    ap.error("nothing to ingest: pass --constitution, --sci or a folder")
link_citations(store)
print(json.dumps(out, indent=2))
