# Resources Reference

MCP resources are **static, URI-addressable documents** that an AI client can read to gain context before calling tools. They are defined in [`src/resources/resources.py`](../src/resources/resources.py) and the reference strings in [`src/resources/references.py`](../src/resources/references.py).

Resources are registered with `@mcp.resource("helm-unittest://…")` and accessed by their URI.

---

## Available Resources

| URI | Handler | Description |
|---|---|---|
| `helm-unittest://schema` | `schema_resource` | Official JSON schema for `helm-unittest` test suites |
| `helm-unittest://reference/assertions` | `assertions_reference_resource` | Assertion type reference guide |
| `helm-unittest://reference/mocking` | `mocking_reference_resource` | Mocking (capabilities, release, lookup, post-renderer) guide |
| `helm-unittest://snapshots/{chart_path}` | `snapshots_resource` | JSON listing of all snapshot entries for a chart |

---

## `helm-unittest://schema`

Returns the full **JSON schema** for `helm-unittest` test suite YAML files.

The schema is loaded from the bundled file:
```
src/resources/schemas/helm-testsuite.json
```

This is the same schema used by [`validate_tests`](./tools.md#validate_tests) as an offline fallback when the upstream GitHub URL is unreachable.

---

## `helm-unittest://reference/assertions`

Returns the **Assertions Reference Guide** as a Markdown string.

Covers all assertion types supported by `helm-unittest`:

| Assertion | Description |
|---|---|
| `equal` / `notEqual` | Compare a JSONPath value to an expected value |
| `matchRegex` / `notMatchRegex` | Regex match on a string value |
| `contains` / `notContains` | Array/string membership check |
| `containsSubPath` / `notContainsSubPath` | Object within array has specific sub-path values |
| `isNull` / `isNotNull` | Path existence check |
| `isEmpty` / `isNotEmpty` | Empty/non-empty array, map, or string |
| `isKind` | Document `kind` assertion |
| `isAPIVersion` | Document `apiVersion` assertion |
| `hasDocuments` | Count of rendered documents |
| `lengthEqual` | Array or object length |
| `matchSnapshot` / `matchSnapshotRaw` | Compare against stored snapshot |
| `failedTemplate` | Assert template rendering fails with an error |

Also documents **document selection** via `documentIndex` and `documentSelector`.

---

## `helm-unittest://reference/mocking`

Returns the **Mocking Reference Guide** as a Markdown string.

Covers all mocking capabilities:

| Topic | Description |
|---|---|
| Capabilities mocking | Override `.Capabilities` (Kubernetes version, API versions) |
| Release mocking | Simulate `.Release` variables (name, namespace, revision, upgrade) |
| Kubernetes provider mocking | Mock `lookup` function results via `kubernetesProvider` |
| PostRenderer mocking | Apply post-render transformations before assertions |
| Subchart / values mocking | Override subchart values and individual value keys |

---

## `helm-unittest://snapshots/{chart_path}`

Returns a **JSON array** of all snapshot files discovered under `chart_path`.

### Response shape

```json
[
  {
    "file_path": "tests/deployment/__snapshot__/deployment_test.yaml.snap",
    "test_file_path": "tests/deployment/deployment_test.yaml",
    "is_orphaned": false,
    "entries": [
      {
        "name": "my suite should render deployment 0",
        "content": "apiVersion: apps/v1\nkind: Deployment\n..."
      }
    ]
  }
]
```

`is_orphaned: true` means the associated test YAML no longer exists.

On error, returns `{"error": "<message>"}`.

---

_Next: [Configuration & Setup →](./setup.md)_
