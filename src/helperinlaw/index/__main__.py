"""python -m helperinlaw.index build [--version v2] [--no-dense]"""

import argparse
import json

from helperinlaw.core.config import settings
from helperinlaw.core.logging import setup_logging
from helperinlaw.core.store import Store
from helperinlaw.index.build import build

setup_logging()
ap = argparse.ArgumentParser(description="Build a search index version")
ap.add_argument("command", choices=["build"])
ap.add_argument("--version", default=settings.index_version)
ap.add_argument("--no-dense", action="store_true", help="skip Ollama embeddings (BM25 only)")
args = ap.parse_args()
dense = settings.use_dense and not args.no_dense
print(json.dumps(build(Store(settings.db_path), args.version, dense)))
