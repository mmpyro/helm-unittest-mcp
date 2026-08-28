# Architecture Overview

This document describes the high-level architecture of the **Helm Unittest MCP Server**, how requests flow through it, and how the source tree is organised.

---

## What is it?

`helm-unittest-mcp` is a **stdio-based MCP server** written in Python 3.13. It wraps the `helm unittest` CLI plugin and exposes its features to any MCP-compatible client (Claude Desktop, Cloud Code, Cursor, etc.) as:

- **Tools** — callable functions the LLM invokes to execute actions.
- **Prompts** — reusable prompt templates that guide the LLM in common workflows.
- **Resources** — static data the LLM can read (schema, assertion reference, etc.).

---

## Request Lifecycle

```
MCP Client (e.g. Claude Desktop)
        │  stdio transport
        ▼
  src/server.py   ← entry point, assembles the MCP app from all modules
        │
        ├── tools/        ← tool handlers (run tests, discover files, snapshot ops …)
        ├── prompt/       ← prompt template handlers
        └── resources/    ← static resource handlers
              │
              └── utils/  ← shared helpers (DTOs, result parser, MCP singleton)
```

The server singleton (`utils/mcp.py → Server`) is shared across all modules via a module-level import so that `@mcp.tool()`, `@mcp.prompt()`, and `@mcp.resource()` decorators are all registered on the same `FastMCP` instance.

---

## Source Tree

```
src/
├── server.py              # Entry point – starts the MCP stdio server
├── tools/                 # MCP tool implementations
│   ├── __init__.py        # Re-exports every public tool symbol
│   ├── get_tests.py       # get_tests, get_test_from_file
│   ├── run_tests.py       # run_unittest, update_snapshot
│   ├── run_tests_parallel.py  # run_tests_parallel
│   ├── schema_validator.py    # validate_schema, validate_tests
│   ├── coverage.py        # get_test_coverage
│   ├── debug.py           # get_rendered_debug_output
│   └── snapshots.py       # get_snapshots, diff_snapshot, clean_snapshots
├── prompt/                # MCP prompt templates
│   ├── __init__.py
│   └── prompts.py         # 4 prompt handlers
├── resources/             # MCP resource providers
│   ├── __init__.py
│   ├── references.py      # Assertion & mocking reference strings
│   ├── resources.py       # schema / assertions / mocking / snapshots resources
│   └── schemas/
│       └── helm-testsuite.json   # Bundled official schema (offline fallback)
└── utils/                 # Shared internals
    ├── mcp.py             # MCP server singleton
    ├── dtos.py            # All data-transfer objects (dataclasses)
    └── parser.py          # TestResultParser: JUnit / xUnit / NUnit / Sonar XML
```

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **Singleton MCP server** | All modules import the same `Server()` instance so decorators land on one `FastMCP` app. |
| **Parallel test runner** | Tests are grouped by suite and run with `ThreadPoolExecutor`; within a suite they run sequentially to preserve ordering. |
| **Offline schema fallback** | `schema_validator.py` tries to fetch the official schema from GitHub; on failure it falls back to the bundled `helm-testsuite.json`. |
| **Temporary XML files** | `run_unittest` writes output to a `tempfile` and cleans it up after parsing so no artefacts are left on disk. |
| **Duplicate-anchor YAML loader** | `get_tests.py` ships a custom `SafeLoader` that silently overwrites duplicate anchors — a pattern common in `helm-unittest` files. |

---

## Data Flow — Running Tests

```
run_tests_parallel(dir_path, chart_path)
  └─ get_tests(dir_path)            → list[TestFile]
       └─ _group_tests_by_suite()   → dict[suite → [TestFile]]
            └─ ThreadPoolExecutor
                 └─ _run_suite()
                      └─ _run_unittest_internal()
                           ├─ subprocess: helm unittest -f … -t xunit -o /tmp/…
                           └─ TestResultParser.parse(/tmp/…) → TestResultSummary
  └─ _merge_summaries()             → TestResultSummary (aggregate)
```

---

_Next: [Tools Reference →](./tools.md)_
