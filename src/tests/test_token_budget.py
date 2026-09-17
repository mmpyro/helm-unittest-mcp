"""The tool surface is copied into every client's context, so its size is a
contract, not an implementation detail. These tests fail when it regresses.
"""

import asyncio
import json

import server


BUDGET_CHARS = 8000


def test_tool_surface_stays_within_budget():
    tools = asyncio.run(server.mcp.list_tools())
    total = sum(
        len(t.name) + len(t.description or "") + len(json.dumps(t.input_schema))
        for t in tools
    )
    assert total < BUDGET_CHARS, (
        f"tools/list is {total} chars, over the {BUDGET_CHARS} budget"
    )


def test_no_tool_advertises_an_output_schema():
    tools = asyncio.run(server.mcp.list_tools())
    offenders = [t.name for t in tools if t.output_schema]
    assert offenders == [], (
        "an output schema means the result is also sent again as "
        f"structuredContent: {offenders}"
    )


def test_input_schemas_carry_no_generated_titles():
    tools = asyncio.run(server.mcp.list_tools())
    offenders = [t.name for t in tools if '"title"' in json.dumps(t.input_schema)]
    assert offenders == []


def test_results_are_sent_once_and_compact():
    result = asyncio.run(server.mcp.call_tool("get_tests", {"dir_path": "example/tests"}))
    dumped = result.model_dump(exclude_none=True, by_alias=True)

    assert not dumped.get("structuredContent")
    text = dumped["content"][0]["text"]
    assert "\n  " not in text, "result is pretty-printed rather than compact"
