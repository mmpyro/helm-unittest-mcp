# Helm Unittest MCP — Documentation

Welcome to the full documentation for the **Helm Unittest MCP Server** (`helm-unittest-mcp`).

This server implements the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) to expose Helm unit-testing capabilities — discovery, validation, execution, snapshot management, coverage reporting, and debugging — to AI assistants and other MCP clients.

---

## Contents

| Document | Description |
|---|---|
| [Architecture Overview](./architecture.md) | High-level design, request lifecycle, and module map |
| [Tools Reference](./tools.md) | Every MCP tool: signature, parameters, return types, examples |
| [Prompts Reference](./prompts.md) | MCP prompt templates and when to use each |
| [Utils & DTOs](./utils.md) | Shared utilities, data-transfer objects, and the test-result parser |
| [Resources Reference](./resources.md) | MCP static resources (schema, assertions guide, mocking guide) |
| [Configuration & Setup](./setup.md) | Prerequisites, installation, and MCP client configuration |
| [Development Guide](./development.md) | Running tests, linting, type-checking, and contributing |
| [Example Chart](./example.md) | Walkthrough of the bundled sample Helm chart |
| [Migrating to 2.0](./migration-2.0.md) | Renamed tools, changed defaults, and the new result format |

---

## Quick Links

- [README](../README.md)
- [uvx install](./setup.md#uvx)
- [All MCP Tools at a Glance](./tools.md#tools-summary)
