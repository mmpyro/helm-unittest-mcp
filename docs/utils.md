# Utils & DTOs Reference

The `utils/` package contains shared infrastructure used by all tools, prompts, and resources.

---

## Module Overview

| Module | Purpose |
|---|---|
| [`utils/mcp.py`](#mcppy) | MCP server singleton |
| [`utils/dtos.py`](#dtospy) | All data-transfer objects (Python dataclasses) |
| [`utils/parser.py`](#parserpy) | XML test-result parser supporting four report formats |

---

## `mcp.py`

Exports a `Server` class that wraps `FastMCP` and implements the **singleton pattern** so that all modules share the same MCP application instance.

```python
from utils.mcp import Server

mcp = Server().mcp   # FastMCP instance shared across the whole server
```

Every `@mcp.tool()`, `@mcp.prompt()`, and `@mcp.resource()` decorator registers on this single instance, which is then started by `server.py`.

---

## `dtos.py`

All public data-transfer objects are plain Python `dataclass`es. They are serialised automatically by the MCP framework when returned from a tool.

---

### `TestFile`

Represents a parsed `helm-unittest` test suite file.

```python
@dataclass
class TestFile:
    suite: str                       # Suite name (from the `suite:` field)
    tests: list[str]                 # List of test case descriptions (`it:` values)
    file_path: str                   # Absolute or relative path to the YAML file
    release: Optional[dict] = None   # Release block (only when include_release=True)
```

---

### `ValidationResult`

Result of a schema-validation check for a single file.

```python
@dataclass
class ValidationResult:
    success: bool           # True if the file passed validation
    message: str            # Human-readable status message
    errors: list[str] | None = None  # Validation error details (None on success)
```

---

### `BatchValidationSummary`

Aggregate result when validating an entire directory with `return_summary=True`.

```python
@dataclass
class BatchValidationSummary:
    total_files: int            # Files evaluated
    valid_files: int            # Files that passed
    invalid_files: int          # Files that failed
    failures: list[ValidationResult]  # Details for each failure
```

---

### `TestCaseResult`

Result for a single test case within a suite execution.

```python
@dataclass
class TestCaseResult:
    name: str           # Test case name / description
    suite: str          # Parent suite name
    result: str         # "Pass", "Fail", or "Skip"
    time: float         # Execution time in seconds
    message: str | None = None  # Failure message (truncated if max_message_length set)
```

---

### `TestResultSummary`

Aggregate result of a `run_tests` call.

```python
@dataclass
class TestResultSummary:
    total: int                       # Total test cases run
    passed: int
    failed: int
    skipped: int
    errors: int
    time: float                      # Sum of individual suite times
    test_cases: list[TestCaseResult] # Filtered list (see include_test_cases)
    elapsed_time: Optional[float] = None  # Wall-clock time (parallel runner only)
```

> **Note**: `time` is the sum of all suite times and may exceed `elapsed_time` when running in parallel.

---

### `SnapshotEntry`

A single named entry inside a `.snap` file.

```python
@dataclass
class SnapshotEntry:
    name: str     # Entry key (usually "<suite> <test-it> <index>")
    content: str  # Rendered YAML string
```

---

### `SnapshotFile`

Represents a `.snap` file and its parsed entries.

```python
@dataclass
class SnapshotFile:
    file_path: str              # Path to the .snap file
    test_file_path: str         # Corresponding test YAML path
    snapshots: list[SnapshotEntry]
    is_orphaned: bool = False   # True if test_file_path no longer exists
```

---

### `SnapshotDiffResult`

Result of a `diff_snapshot` call.

```python
@dataclass
class SnapshotDiffResult:
    test_file: str
    test_it: Optional[str]   # Scoped test case, if provided
    exists: bool             # Whether the snapshot file exists
    has_diff: bool           # Whether differences were detected
    diff: Optional[str]      # Unified diff string (None when no diff)
    message: str             # Human-readable summary
```

---

### `SnapshotCleanResult`

Result of a `clean_snapshots` call.

```python
@dataclass
class SnapshotCleanResult:
    cleaned_files: list[str]    # Snapshot files deleted (or would be)
    cleaned_entries: list[str]  # "<file> -> <key>" strings for removed entries
    dry_run: bool
    message: str                # Summary, e.g. "Dry run: Found 2 orphaned file(s)…"
```

---

### `TemplateCoverage`

Per-template coverage detail inside a `CoverageReport`.

```python
@dataclass
class TemplateCoverage:
    template_path: str       # Relative path from templates/
    tested: bool             # Covered by at least one test suite
    test_files: list[str]    # Test files referencing this template
    test_suites: list[str]   # Suite names referencing this template
```

---

### `CoverageReport`

Overall coverage report returned by `get_test_coverage`.

```python
@dataclass
class CoverageReport:
    chart_path: str
    total_templates: int
    tested_templates: int
    untested_templates: int
    coverage_percentage: float           # 0.0 – 100.0
    template_details: list[TemplateCoverage]
    untested_template_paths: list[str]   # Shortcut list of uncovered paths
```

---

## `parser.py`

The `TestResultParser` class converts XML test reports produced by `helm unittest` into [`TestResultSummary`](./utils.md#testresultsummary) objects.

```python
from utils.parser import TestResultParser, TestFormat

parser = TestResultParser("xunit")
summary = parser.parse("/tmp/result.xml")
```

### Supported Formats

| `TestFormat` | Helm flag | Notes |
|---|---|---|
| `"xunit"` | `-t xunit` | **Default** — xUnit-style XML |
| `"junit"` | `-t junit` | Standard JUnit XML (used by most CI tools) |
| `"nunit"` | `-t nunit` | NUnit XML format |
| `"sonar"` | `-t sonar` | SonarQube generic test execution format |

The `parse()` method accepts either a **file path** or an **XML string** directly. It falls back to XML-string parsing if the path does not resolve to a file.

---

_Next: [Resources Reference →](./resources.md)_
