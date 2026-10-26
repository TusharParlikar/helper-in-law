"""End-to-end MCP checks over the real protocol: spawn the server as a subprocess and talk to it
with the official MCP Python client, on stdio and on localhost Streamable HTTP. Covers what
MCP Inspector checks: handshake, tools/list (with schemas), tools/call, resources, prompts and
error results."""

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import anyio
import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamable_http_client

from helperinlaw.core.store import Store
from helperinlaw.index.build import build
from helperinlaw.ingest.pipeline import ingest_dir
from tests.conftest import SAMPLE, add_articles

TOOLS = {"search_judgments", "ask_legal_question", "get_judgment", "get_paragraph", "find_citing_cases",
         "lookup_statute", "get_profile", "set_style", "get_constitution_article"}


@pytest.fixture(scope="module")
def env(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    db = tmp_path_factory.mktemp("mcp") / "corpus.db"
    s = Store(db)
    ingest_dir(s, SAMPLE)
    add_articles(s)
    build(s, "v1", dense=False)
    s.db.close()
    return {**os.environ, "HIL_DB_PATH": str(db), "HIL_USE_LLM": "false", "HIL_USE_DENSE": "false"}


async def exercise(session: ClientSession) -> None:
    init = await session.initialize()
    assert init.server_info.name == "helper-in-law"
    tools = {t.name: t for t in (await session.list_tools()).tools}
    assert set(tools) == TOOLS
    for t in tools.values():  # every tool documents itself and declares an input schema
        assert t.description and t.input_schema.get("type") == "object"

    r = await session.call_tool("ask_legal_question", {"question": "Is a 65B certificate mandatory?"})
    assert not r.is_error
    body = r.structured_content or json.loads(r.content[0].text)
    assert body["citations"] and all(b["citation_ids"] for b in body["answer_blocks"])

    r = await session.call_tool("get_constitution_article", {"article": "21"})
    art = r.structured_content or json.loads(r.content[0].text)
    assert art["text"].startswith("Protection of life and personal liberty") and "#page=" in art["official_url"]

    bad = await session.call_tool("get_judgment", {"case_id": "no-such-case"})
    assert bad.is_error  # an expected failure is an error result, not a crashed server

    templates = {t.uri_template for t in (await session.list_resource_templates()).resource_templates}
    assert {"judgment://{case_id}", "statute://{act}/{section}"} <= templates
    res = await session.read_resource("judgment://fs_2015_mehta")
    assert "Bail may be refused" in res.contents[0].text

    prompts = {p.name for p in (await session.list_prompts()).prompts}
    assert prompts == {"research_memo", "find_contrary_authority"}
    got = await session.get_prompt("research_memo", {"issue": "bail"})
    assert "ask_legal_question" in got.messages[0].content.text


def test_stdio(env: dict[str, str]) -> None:
    params = StdioServerParameters(command=sys.executable, args=["-m", "helperinlaw.mcp_server"], env=env,
                                   cwd=str(Path(__file__).parent.parent))

    async def main() -> None:
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await exercise(session)

    anyio.run(main)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def test_streamable_http_on_localhost(env: dict[str, str]) -> None:
    port = free_port()
    proc = subprocess.Popen([sys.executable, "-m", "helperinlaw.mcp_server", "--http", "--port", str(port)],
                            env=env, cwd=str(Path(__file__).parent.parent),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.time() + 30
        while time.time() < deadline:
            with socket.socket() as s:
                if s.connect_ex(("127.0.0.1", port)) == 0:
                    break
            time.sleep(0.3)

        async def main() -> None:
            async with streamable_http_client(f"http://127.0.0.1:{port}/mcp") as streams:
                read, write = streams[0], streams[1]
                async with ClientSession(read, write) as session:
                    await exercise(session)

        anyio.run(main)
    finally:
        proc.terminate()
        proc.wait(timeout=10)
