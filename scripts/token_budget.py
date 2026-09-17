"""Report the wire cost of this server's tool surface.

Run: uv run python scripts/token_budget.py [--calls]

The `tools/list` payload is paid by every client on every session, so it is the
number to watch. `--calls` additionally exercises each tool against `example/`
and reports the per-call response size.
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import server  # noqa: E402

BUDGET_CHARS = 8000
EXAMPLE_CALLS: list[tuple[str, dict]] = [
    ("get_tests", {"dir_path": "example/tests"}),
    ("get_test_coverage", {"chart_path": "example"}),
    ("validate_tests", {"dir_path": "example/tests"}),
    ("get_snapshots", {"chart_path": "example"}),
    (
        "get_rendered_debug_output",
        {"chart_path": "example", "test_suite_files": "tests/*/*_test.yaml"},
    ),
    (
        "run_tests_parallel",
        {"dir_path": "example/tests", "chart_path": "example"},
    ),
]


async def report_tools() -> int:
    tools = await server.mcp.list_tools()
    total_desc = total_in = total_out = 0
    rows = []
    for t in tools:
        desc = len(t.description or "")
        in_schema = len(json.dumps(t.input_schema))
        out_schema = len(json.dumps(t.output_schema)) if t.output_schema else 0
        total_desc += desc
        total_in += in_schema
        total_out += out_schema
        rows.append((desc + in_schema + out_schema, t.name, desc, in_schema, out_schema))

    rows.sort(reverse=True)
    print(f"{'tool':30s} {'desc':>6s} {'in':>6s} {'out':>6s} {'total':>7s}")
    for total, name, desc, in_schema, out_schema in rows:
        print(f"{name:30s} {desc:6d} {in_schema:6d} {out_schema:6d} {total:7d}")

    grand = total_desc + total_in + total_out
    print(
        f"\n{len(tools)} tools  desc={total_desc} in={total_in} out={total_out}"
        f"  TOTAL={grand} chars (~{grand // 4} tokens)"
    )
    status = "OK" if grand < BUDGET_CHARS else "OVER BUDGET"
    print(f"budget {BUDGET_CHARS} chars: {status}")
    return grand


async def report_calls() -> None:
    print("\nper-call response size against example/:")
    for name, args in EXAMPLE_CALLS:
        try:
            result = await server.mcp.call_tool(name, args)
        except Exception as exc:  # pragma: no cover - diagnostic script
            print(f"{name:30s} ERROR {type(exc).__name__}: {str(exc)[:80]}")
            continue
        dumped = result.model_dump(exclude_none=True, by_alias=True)
        content = len(json.dumps(dumped.get("content", []), default=str))
        structured = (
            len(json.dumps(dumped["structuredContent"], default=str))
            if dumped.get("structuredContent")
            else 0
        )
        total = content + structured
        dup = " (DUPLICATED)" if structured else ""
        print(f"{name:30s} {total:8d} chars (~{total // 4:6d} tokens){dup}")


async def main() -> None:
    grand = await report_tools()
    if "--calls" in sys.argv:
        await report_calls()
    sys.exit(0 if grand < BUDGET_CHARS else 1)


if __name__ == "__main__":
    asyncio.run(main())
