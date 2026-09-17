# Tools Reference

All MCP tools are registered in [`src/tools/`](../src/tools/) and re-exported by [`src/tools/__init__.py`](../src/tools/__init__.py).

Tools are registered through the `tool()` decorator in [`src/utils/mcp.py`](../src/utils/mcp.py) rather than
`@mcp.tool()` directly. That decorator keeps the wire format small — see
[Token budget](#token-budget) at the bottom of this page.

---

## Tools Summary

| Tool | Module | Purpose |
|---|---|---|
| [`run_tests`](#run_tests) | `run.py` | Run a chart's unit tests, sequentially or in parallel |
| [`get_tests`](#get_tests) | `get_tests.py` | Discover test suites and the tests they define |
| [`validate_tests`](#validate_tests) | `schema_validator.py` | Validate test files against the official JSON schema |
| [`get_test_coverage`](#get_test_coverage) | `coverage.py` | Report which templates no test suite exercises |
| [`get_rendered_debug_output`](#get_rendered_debug_output) | `debug.py` | Render a chart and return the resulting manifests |
| [`get_snapshots`](#get_snapshots) | `snapshots.py` | List snapshot files and their entries |
| [`diff_snapshot`](#diff_snapshot) | `snapshots.py` | Compare stored snapshots against a fresh render |
| [`clean_snapshots`](#clean_snapshots) | `snapshots.py` | Remove snapshots left behind by deleted tests |

---

## `run_tests`

```python
run_tests(
    chart_path: str,
    path: str = "tests",
    update_snapshot: bool = False,
    values_path: list[str] = [],
    include_test_cases: Literal["failed_only", "all", "none"] = "failed_only",
    max_message_length: int | None = 1000,
    max_test_cases: int = 50,
    max_workers: int | None = None,
    output_type: Literal["xunit", "junit", "nunit", "sonar"] = "xunit",
    output_file: str | None = None,
    strict: bool = False,
    fail_fast: bool = False,
    with_subchart: bool | None = None,
    skip_schema_validation: bool = False,
    chart_tests_path: str | None = None,
) -> TestResultSummary
```

Runs a Helm chart's unit tests and summarizes the results.

`path` decides how they run. A **directory** (the default `"tests"`, resolved against `chart_path`) is
discovered, grouped by suite name, and its suite groups run in parallel through a thread pool; files within
one suite stay sequential so their ordering guarantees hold. A **file or glob** runs sequentially.

| Parameter | Notes |
|---|---|
| `path` | Test file, glob, or directory relative to the chart |
| `update_snapshot` | Rewrites stored snapshots to match the current render (`-u`) |
| `include_test_cases` | `failed_only` returns just the failures; `all` returns every case; `none` returns totals only |
| `max_message_length` | Per-message cap, `None` disables truncation |
| `max_test_cases` | Cap on how many cases come back; the overflow is reported as one placeholder entry |
| `max_workers` | Thread pool size for the parallel path; `None` uses the executor default |
| `output_file` | Persists the report instead of using a temp file |

Returns a `TestResultSummary`: totals, aggregate `time`, wall-clock `elapsed_time`, and the `test_cases` that
survived the filters.

---

## `get_tests`

```python
get_tests(
    dir_path: str,
    pattern: str | None = "",
    include_release: bool = False,
    suite_pattern: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[TestFile]
```

Lists the helm-unittest suites under a directory, with the name of every test they define. `dir_path` also
accepts a single test file, in which case the list holds one entry.

Never returns the file body — only `suite`, the `it` descriptions, `file_path`, and (with
`include_release=True`) the suite's `release` block.

---

## `validate_tests`

```python
validate_tests(
    dir_path: str,
    pattern: str | None = "",
    only_failures: bool = False,
    return_summary: bool = True,
) -> list[ValidationResult] | BatchValidationSummary
```

Validates test files against the official helm-unittest JSON schema. `dir_path` accepts a directory or a
single test file.

Returns a `BatchValidationSummary` — counts plus the failures — by default. Pass `return_summary=False` for
one `ValidationResult` per file, optionally narrowed with `only_failures=True`.

The schema is fetched from the helm-unittest repository and cached, falling back to the copy bundled at
`src/resources/schemas/helm-testsuite.json` when the network is unavailable.

---

## `get_test_coverage`

```python
get_test_coverage(
    chart_path: str,
    tests_dir: str = "tests",
    pattern: str | None = "",
    with_subcharts: bool = False,
    untested_only: bool = True,
) -> CoverageReport
```

Reports which of a chart's templates are exercised by a test suite and which are not.

With `untested_only=True` (the default) the report carries totals, the coverage percentage, and
`untested_template_paths`. Pass `untested_only=False` to also get `template_details`: one row per template
with the test files and suites that target it.

Partials (`_helpers.tpl`) and `NOTES.txt` are excluded from the denominator.

---

## `get_rendered_debug_output`

```python
get_rendered_debug_output(
    chart_path: str,
    test_suite_files: str = "tests/*_test.yaml",
    values_path: list[str] = [],
    templates: list[str] | None = None,
    max_chars: int = 20000,
    include_raw_log: bool = False,
) -> dict[str, str]
```

Renders a chart through helm-unittest in debug mode (`-d`) and returns the resulting manifests, keyed by
template path. Use it to see what a failing assertion actually rendered.

| Parameter | Notes |
|---|---|
| `templates` | Return only these templates, matched on full path or basename |
| `max_chars` | Per-template cap; the remainder is replaced with a truncation note |
| `include_raw_log` | Also returns `__raw_debug_log__`, plus any files the plugin left in `<chart>/.debug/` |

`include_raw_log` is off by default because the log restates every rendered template. On the bundled
`example/` chart, turning it on takes the response from ~4 kB to ~40 kB.

---

## `get_snapshots`

```python
get_snapshots(
    chart_path: str,
    test_file_path: str | None = None,
    names_only: bool = True,
    limit: int | None = None,
    offset: int = 0,
) -> list[SnapshotFile]
```

Lists the `.snap` files in a chart and the entries each one stores, flagging files whose test has been
deleted (`is_orphaned`).

With `names_only=True` (the default) each entry's `content` is replaced by its size (`"<1843 chars>"`).
Stored manifests are large, so fetch them with `names_only=False` only when you need to read one.

---

## `diff_snapshot`

```python
diff_snapshot(
    chart_path: str,
    test_file_path: str,
    test_it: str | None = None,
    max_chars: int = 20000,
) -> SnapshotDiffResult
```

Compares a test file's stored snapshots against a fresh render, without touching them.

Each snapshot entry is matched to the rendered manifest it came from, by `kind` and `metadata.name`, and
diffed against that one manifest. Entries that cannot be matched fall back to a diff against the whole
render and are named in `message`.

`test_it` narrows the comparison to entries whose name contains that text.

---

## `clean_snapshots`

```python
clean_snapshots(chart_path: str, dry_run: bool = True) -> SnapshotCleanResult
```

Removes snapshot files and entries left behind by deleted tests. Reports what it would remove without
removing it unless `dry_run=False`.

Returns paths and entry keys only, never snapshot content.

---

## Token budget

Every tool definition is copied into the client's context on every session, and every result is copied into
it on every call. Both are treated as a contract here:

- Tools are registered with `structured_output=False`, so no `outputSchema` is advertised and results are
  not serialized a second time as `structuredContent`.
- Results are compact JSON, not the SDK's `indent=2` pretty-print.
- Generated `title` keys are stripped from the input schemas.
- The tools that can emit unbounded output (`get_rendered_debug_output`, `get_snapshots`, `diff_snapshot`,
  `run_tests`) all cap it, and default to the cheap setting.

`uv run python scripts/token_budget.py --calls` prints both numbers.
`src/tests/test_token_budget.py` fails the build if the tool surface exceeds 8,000 characters.
