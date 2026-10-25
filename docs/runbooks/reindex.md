# Runbook: rebuild the index

Index versions are side by side: building `v2` never touches `v1`, which keeps serving.

1. Ingest new judgments (idempotent by sha256; failures land in `dead_letter`):
   `uv run python -m helperinlaw.ingest path/to/folder`
2. Build the new version (embeddings need Ollama running with `nomic-embed-text`):
   `uv run python -m helperinlaw.index build --version v2`
   Interrupted? Run the same command again; embedding resumes where it stopped.
3. Evaluate against the new version before switching:
   `HIL_INDEX_VERSION=v2 uv run python eval/run_eval.py --dense`
4. Switch: set `HIL_INDEX_VERSION=v2` in `.env` and restart the API / MCP server.
5. Roll back: set `HIL_INDEX_VERSION=v1` and restart.

BM25-only build (no Ollama): add `--no-dense`.
