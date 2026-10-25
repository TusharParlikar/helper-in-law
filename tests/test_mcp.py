"""MCP smoke tests: tool listing, calls through the server, resources and prompts."""

import asyncio
import json
from typing import Any

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from helperinlaw.mcp_server.server import mcp, set_service
from helperinlaw.service import Service

TOOLS = {
    "search_judgments",
    "ask_legal_question",
    "get_judgment",
    "get_paragraph",
    "find_citing_cases",
    "lookup_statute",
    "get_profile",
    "set_style",
}


@pytest.fixture(autouse=True)
def wire(service: Service) -> None:
    set_service(service)


def call(name: str, args: dict[str, Any]) -> Any:
    result = asyncio.run(mcp.call_tool(name, args))
    assert not result.is_error, result
    return result.structured_content


def test_tools_listed_with_descriptions_and_read_only_hints() -> None:
    tools = {t.name: t for t in asyncio.run(mcp.list_tools())}
    assert set(tools) == TOOLS
    assert all(t.description for t in tools.values())
    assert all(tools[n].annotations.read_only_hint for n in TOOLS - {"set_style"})


def test_ask_returns_verified_response_object() -> None:
    out = call(
        "ask_legal_question", {"question": "Is a 65B certificate mandatory?", "depth": "quick"}
    )
    assert out["citations"] and out["verification"]["verified"] >= 1
    assert all(b["citation_ids"] for b in out["answer_blocks"])
    assert "notice" in out


def test_other_tools() -> None:
    assert len(call("search_judgments", {"query": "bail", "limit": 50})["results"]) <= 20
    assert (
        call("get_judgment", {"case_id": "fs_2020_joshi"})["title"]
        == "Neha Joshi v. Union of India"
    )
    assert (
        len(
            call("get_paragraph", {"case_id": "fs_2015_mehta", "start": 1, "end": 30})["paragraphs"]
        )
        <= 10
    )
    assert (
        call("find_citing_cases", {"case_id": "fs_2016_verma"})["citing"][0]["treatment"]
        == "overruled"
    )
    assert call("lookup_statute", {"act": "IPC", "section": "302"})["cases"]
    assert call("set_style", {"changes": {"depth": "deep"}, "profile_id": "mcp"})["depth"] == "deep"
    assert call("get_profile", {"profile_id": "mcp"})["depth"] == "deep"


def test_bad_input_is_a_tool_error_not_a_crash() -> None:
    # ToolError becomes an isError result for the client; anything else would be a crash.
    with pytest.raises(ToolError, match="not found"):
        asyncio.run(mcp.call_tool("get_judgment", {"case_id": "nope"}))
    with pytest.raises(ToolError, match="not a style setting"):
        asyncio.run(mcp.call_tool("set_style", {"changes": {"verification": False}}))


def test_resources_and_prompts() -> None:
    contents = list(asyncio.run(mcp.read_resource("judgment://fs_2015_mehta")))
    assert "[7] Bail may be refused" in contents[0].content
    statute = list(asyncio.run(mcp.read_resource("statute://BNS/103")))
    assert json.loads(statute[0].content)["cases"]
    prompt = asyncio.run(mcp.get_prompt("research_memo", {"issue": "bail"}))
    assert "ask_legal_question" in str(prompt)
