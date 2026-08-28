# Configuration & Setup

---

## Prerequisites

### 1. Python ≥ 3.13

Verify with:

```bash
python3 --version
```

### 2. `uv` package manager

[`uv`](https://docs.astral.sh/uv/) is used for dependency management:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. Helm

Install from [helm.sh](https://helm.sh/docs/intro/install/).

```bash
brew install helm        # macOS
choco install kubernetes-helm  # Windows
```

### 4. `helm-unittest` plugin

```bash
helm plugin install https://github.com/helm-unittest/helm-unittest.git
```

Verify:

```bash
helm unittest --version
```

---

## Installation

### Option A — Local checkout

Clone the repository and install dependencies:

```bash
git clone https://github.com/mmpyro/helm-unittest-mcp.git
cd helm-unittest-mcp

# Install runtime dependencies into the system Python interpreter used by your MCP client
uv pip install --system -r pyproject.toml
```

### Option B — `uvx` (recommended)

[`uvx`](https://docs.astral.sh/uv/guides/tools/) creates an isolated, cached environment automatically:

```bash
# No installation step needed — uvx handles it at runtime
uvx git+https://github.com/mmpyro/helm-unittest-mcp.git
```

---

## MCP Client Configuration

### Local path

Add to your MCP client's `mcpServers` configuration:

```json
{
  "mcpServers": {
    "helmunittest": {
      "type": "stdio",
      "command": "python",
      "args": [
        "/path/to/helm-unittest-mcp/src/server.py"
      ],
      "env": {}
    }
  }
}
```

> **Important**: Run `uv pip install --system -r pyproject.toml` first so that dependencies are available to the interpreter.

### `uvx` — latest release

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

### `uvx` — specific branch or commit

```json
{
  "mcpServers": {
    "helm-unittest": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "git+https://github.com/mmpyro/helm-unittest-mcp.git@<branch-or-sha>"
      ]
    }
  }
}
```

### `uvx` — pinned version tag

```json
{
  "mcpServers": {
    "helm-unittest": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "git+https://github.com/mmpyro/helm-unittest-mcp.git@v1.0.0"
      ]
    }
  }
}
```

---

## Environment Variables

The server itself does not require any environment variables. It relies on `helm` being available on `PATH`.

---

_Next: [Development Guide →](./development.md)_
