"""python -m helperinlaw.api  (binds to HIL_BIND_HOST, default 127.0.0.1)"""

import uvicorn

from helperinlaw.core.config import settings
from helperinlaw.core.logging import setup_logging

setup_logging()
uvicorn.run("helperinlaw.api.main:app", host=settings.bind_host, port=8000)
