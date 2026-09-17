# Helm Unittest MCP Server

This is a Model Context Protocol (MCP) server that provides tools for running and managing [helm-unittest](https://github.com/helm-unittest/helm-unittest). It allows AI assistants to discover, validate, and execute Helm unit tests within a project.

📖 **[Full Documentation →](docs/index.md)**

## Features

- **Test Discovery**: Recursively find all YAML test suites in a directory.
- **Schema Validation**: Validate test files against the official `helm-unittest` JSON schema.
- **Test Execution**: Run tests using the `helm unittest` CLI and receive structured results (JUnit/xUnit/NUnit/Sonar formats).
- **Parallel Execution**: `run_tests` groups suites and runs them concurrently for faster feedback.
- **Snapshot Management**: Create, diff, update, and clean snapshot files.
- **Coverage Reporting**: Analyse template coverage across a Helm chart.
- **Debug Output**: Inspect rendered manifests to troubleshoot failing assertions.
- **MCP Prompts**: Pre-built prompt templates to guide the LLM through common workflows.
- **MCP Resources**: Built-in assertion and mocking reference guides available to the LLM.
- **Small Context Footprint**: The tool surface costs ~1.5k tokens per session and every tool caps its output (see [Tools Reference](docs/tools.md#token-budget)).

## Project Structure

The project follows a modular structure optimized for MCP:

- `src/`: Core application source code.
  - `tools/`: MCP tool implementations (test discovery, execution, validation, coverage, snapshots, debug).
  - `prompt/`: MCP prompt templates to guide the LLM in writing, running, or debugging tests.
  - `utils/`: Shared utilities, DTOs, and result parsers.
  - `resources/`: MCP resources — JSON schema, assertion reference, mocking guide.
  - `tests/`: Comprehensive unit and integration tests for the server logic.
- `example/`: A sample Helm chart with accompanying `helm-unittest` YAML files to demonstrate usage.
- `docs/`: Full project documentation (see below).
- `pyproject.toml`: Project configuration and dependency management via `uv`.

## Documentation

| Page | Description |
|---|---|
| [Architecture](docs/architecture.md) | High-level design, module map, and data-flow diagrams |
| [Tools Reference](docs/tools.md) | Every MCP tool with full parameter and return-type docs |
| [Prompts Reference](docs/prompts.md) | Prompt templates and when to use each |
| [Utils & DTOs](docs/utils.md) | Shared utilities and all data-transfer objects |
| [Resources Reference](docs/resources.md) | Static MCP resources (schema, assertion guide, mocking guide) |
| [Configuration & Setup](docs/setup.md) | Prerequisites, install options, and MCP client config |
| [Development Guide](docs/development.md) | Running tests, linting, and contributing |
| [Migrating to 2.0](docs/migration-2.0.md) | Renamed tools and changed defaults in 2.0 |
| [Example Chart](docs/example.md) | Walkthrough of the bundled sample chart |


## Prerequisites

To run this MCP server and execute tests, you need the following:

### 1. Python Environment
This project uses `uv` for dependency management. See [Development Commands](#development-commands) for installation.

### 2. Helm
[Helm](https://helm.sh/docs/intro/install/) must be installed on your system.

### 3. Helm Unittest Plugin
The `helm-unittest` plugin must be installed in Helm:
```bash
helm plugin install https://github.com/helm-unittest/helm-unittest.git
```

## Development Commands

For convenience, a `Makefile` is provided with common tasks:

- **Sync dependencies**:
  ```bash
  make sync      # Production only
  make sync-dev  # Include dev dependencies
  ```
- **Running tests**:
  ```bash
  make unittest          # Run unit tests only
  make test-integration  # Run integration tests only
  make test-all          # Run all tests
  ```
- **Quality Checks**:
  ```bash
  make lint              # Run flake8 linting
  make typecheck         # Run mypy type checking
  make check             # Run both linting and type checking
  ```
- **Local Development**:
  ```bash
  make dev               # Start server in development mode
  ```

## Configuration for Cloud Code

To use this MCP server in Cloud Code, add the following configuration to your `mcpServers` setting:

### Local path

**Important**: Before using this MCP server, you need to install the dependencies in the Python interpreter used by Claude. Run this command:
```bash
uv pip install --system -r pyproject.toml
```

Then add the following configuration to your `mcpServers` settings

```json
{
  "mcpServers": {
    "helmunittest": {
      "type": "stdio",
      "command": "python",
      "args": [
        "helm-unittest-mcp/src/server.py"
      ],
      "env": {}
    }
  }
}
```

### uvx

[`uvx`](https://docs.astral.sh/uv/guides/tools/) is a `uv` subcommand for running Python tools in an isolated, cached environment (similar in spirit to `pipx`).
Instead of pointing Cloud Code at a local checkout and manually installing dependencies into the Python interpreter used by the assistant, `uvx` will:

- create an isolated environment automatically,
- install this project (and its dependencies) into that environment,
- cache the environment for fast subsequent runs,
- allow easy pinning to a version/branch/commit via the Git URL.

This is typically better than the **Local path** setup because it avoids “works on my machine” issues, does not require pre-installing dependencies into a shared interpreter, and makes upgrades/pinning straightforward.

Example configuration:
```json
{
  "mcpServers": {
    "helm-unittest": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "git+https://github.com/mmpyro/helm-unittest-mcp.git"
      ]
    }
  }
}
```
Using MCP Server from specific branch
```json
{
  "mcpServers": {
    "helm-unittest": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "git+https://github.com/mmpyro/helm-unittest-mcp.git@<branch-name>"
      ]
    }
  }
}
```

## Contributing

Unit tests are located in `src/tests`. Please ensure all tests pass before submitting changes.
