# Development Guide

---

## Getting Started

```bash
git clone https://github.com/mmpyro/helm-unittest-mcp.git
cd helm-unittest-mcp

# Install all dependencies including dev extras
make sync-dev
```

---

## Project Layout

```
helm-unittest-mcp/
├── src/
│   ├── server.py         # Entry point
│   ├── tools/            # MCP tool implementations
│   ├── prompt/           # MCP prompt templates
│   ├── resources/        # MCP resources (schema, reference docs)
│   └── utils/            # Shared helpers and DTOs
├── example/              # Sample Helm chart for manual testing
├── docs/                 # This documentation
├── Makefile              # Common development commands
├── pyproject.toml        # Project metadata and dependencies
└── uv.lock               # Locked dependency tree
```

---

## Makefile Commands

### Dependency Management

```bash
make sync        # Install production dependencies only
make sync-dev    # Install production + dev dependencies
```

### Running Tests

```bash
make unittest          # Unit tests only (excludes integration-marked tests)
make test-integration  # Integration tests only (requires helm + helm-unittest)
make test-all          # Run the full test suite
```

Test results are written to `test-results.xml` (xUnit format) and coverage to `coverage.xml`.

### Quality Checks

```bash
make lint        # flake8 linting
make typecheck   # mypy static type checking
make check       # Both lint and typecheck
```

### Local Development Server

```bash
make dev         # Start the MCP server in development mode (stdio)
```

---

## Test Suite Layout

Tests live in `src/tests/`. The naming convention is:

| File pattern | Type | Notes |
|---|---|---|
| `test_*.py` (no `integration` suffix) | **Unit** | No external tools required |
| `test_*_integration.py` | **Integration** | Requires `helm` + `helm-unittest` on PATH |

Integration tests are marked with `@pytest.mark.integration` and are excluded from the default `make unittest` run via `-m "not integration"`.

---

## Code Quality Standards

| Tool | Config file | Purpose |
|---|---|---|
| `flake8` | `.flake8` | PEP 8 style enforcement |
| `mypy` | `pyproject.toml [tool.mypy]` | Static type checking (Python 3.13, strict) |

Key mypy settings:
- `check_untyped_defs = true`
- `warn_unused_ignores = true`
- `ignore_missing_imports = true`

---

## Adding a New Tool

1. Create `src/tools/my_tool.py`:

```python
from utils.mcp import Server

mcp = Server().mcp

@mcp.tool()
def my_tool(param: str) -> dict:
    """Docstring shown to the LLM."""
    ...
```

2. Export it from `src/tools/__init__.py`:

```python
from tools.my_tool import my_tool

__all__ = [..., "my_tool"]
```

3. Add unit tests in `src/tests/test_my_tool.py`.

4. Run `make check && make test-all` before submitting a PR.

---

## Adding a New Prompt

1. Add a function to `src/prompt/prompts.py` decorated with `@mcp.prompt()`.
2. Add unit tests in `src/tests/test_prompts.py`.

---

## Contributing

- All tests must pass (`make test-all`).
- No new type errors (`make typecheck`).
- No new lint violations (`make lint`).
- Docstrings are required for all public tool and prompt functions — the MCP framework exposes them to the LLM.
- Include unit tests for new tools. Integration tests are welcome but optional for PRs.

---

_Back to [Documentation Index →](./index.md)_
