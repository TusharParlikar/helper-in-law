.PHONY: install lint format type test eval eval-llm ingest index api mcp inspector ui

install:
	uv sync --extra pdf --extra ui

lint:
	uv run ruff check .

format:
	uv run ruff format .

type:
	uv run mypy src

test:
	uv run pytest -q

eval:
	uv run python eval/run_eval.py

eval-llm:
	uv run python eval/run_eval.py --llm --dense

ingest:
	uv run python -m helperinlaw.ingest data/sample

index:
	uv run python -m helperinlaw.index build

api:
	uv run python -m helperinlaw.api

mcp:
	uv run python -m helperinlaw.mcp_server

# Official MCP Inspector (Node.js): opens a browser UI connected to the stdio server.
inspector:
	npx @modelcontextprotocol/inspector uv run python -m helperinlaw.mcp_server

ui:
	uv run streamlit run ui/app.py --server.address 127.0.0.1
