"""python -m helperinlaw.mcp_server [--http] [--port 8765]

stdio by default. --http serves Streamable HTTP on HIL_BIND_HOST (127.0.0.1) only."""

import argparse

from helperinlaw.core.config import settings
from helperinlaw.core.logging import setup_logging
from helperinlaw.mcp_server.server import mcp

setup_logging("WARNING")
ap = argparse.ArgumentParser()
ap.add_argument("--http", action="store_true")
ap.add_argument("--port", type=int, default=8765)
args = ap.parse_args()
if args.http:
    mcp.run("streamable-http", host=settings.bind_host, port=args.port)
else:
    mcp.run("stdio")
