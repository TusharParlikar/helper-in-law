"""python -m helperinlaw.api  (binds to HIL_BIND_HOST, default 127.0.0.1)"""

import uvicorn

from helperinlaw.api.main import svc
from helperinlaw.core.config import settings
from helperinlaw.core.logging import setup_logging
from helperinlaw.retrieve.rerank import idf_table

setup_logging()
idf_table(svc().store, settings.index_version)  # build before serving, so no first request waits for it
uvicorn.run("helperinlaw.api.main:app", host=settings.bind_host, port=8000)
