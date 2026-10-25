"""python -m helperinlaw.ingest [folder] [--limit N]"""

import argparse
import json
from pathlib import Path

from helperinlaw.core.config import settings
from helperinlaw.core.logging import setup_logging
from helperinlaw.core.store import Store
from helperinlaw.ingest.pipeline import ingest_dir

setup_logging()
ap = argparse.ArgumentParser(description="Ingest judgments (.txt/.pdf) from a folder")
ap.add_argument("folder", nargs="?", default="data/sample")
ap.add_argument("--limit", type=int)
args = ap.parse_args()
r = ingest_dir(Store(settings.db_path), Path(args.folder), args.limit)
print(
    json.dumps(
        {"ingested": len(r.ingested), "skipped": len(r.skipped), "failed": r.failed}, indent=2
    )
)
