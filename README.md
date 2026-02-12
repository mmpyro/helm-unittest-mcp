# Helm Unittest MCP Server

This is a Model Context Protocol (MCP) server that provides tools for running and managing [helm-unittest](https://github.com/helm-unittest/helm-unittest). It allows AI assistants to discover, validate, and execute Helm unit tests within a project.

## Features

- **Test Discovery**: Recursively find all YAML test suites in a directory.
- **Schema Validation**: Validate test files against the official `helm-unittest` JSON schema.
- **Test Execution**: Run tests using the `helm unittest` CLI and receive structured results (JUnit/xUnit/NUnit formats).
- **Snapshot Support**: Tools for updating test snapshots.

## Project Structure

The project follows a modular structure optimized for MCP:

- `src/`: Core application source code.
  - `tools/`: MCP tool implementations (test discovery, execution, validation).
  - `prompt/`: MCP prompt templates to guide the LLM in writing or debugging tests.
  - `utils/`: Shared utilities, DTOs, and result parsers.
  - `tests/`: Comprehensive unit tests for the server logic.
- `example/`: A sample Helm chart with accompanying `helm-unittest` YAML files to demonstrate usage.
- `pyproject.toml`: Project configuration and dependency management via `uv`.

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
