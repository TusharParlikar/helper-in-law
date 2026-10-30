.PHONY: eval-criminal install lint format type test eval eval-llm eval-stair eval-campaign ingest index api mcp inspector ui

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

# STAIR (table-of-contents retrieval) alone and fused; needs Ollama, ~25 min on a laptop CPU.
eval-stair:
	uv run python eval/run_stair.py

# Intensive test campaign: 3,000+ responses re-checked, attacks, fault injection, fuzzing (~20 min).
eval-criminal:
	uv run python eval/run_criminal.py

eval-campaign:
	uv run python eval/run_campaign.py

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
