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
- **Local Development**:
  ```bash
  make dev               # Start server in development mode
  ```

## Configuration for Cloud Code

To use this MCP server in Cloud Code, add the following configuration to your `mcpServers` setting:

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

## Contributing

Unit tests are located in `src/tests`. Please ensure all tests pass before submitting changes.
