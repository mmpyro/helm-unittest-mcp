# Tools Reference

All MCP tools are registered in [`src/tools/`](../src/tools/) and re-exported by [`src/tools/__init__.py`](../src/tools/__init__.py).

---

## Tools Summary

| Tool | Module | Purpose |
|---|---|---|
| [`get_tests`](#get_tests) | `get_tests.py` | Recursively discover test files in a directory |
| [`get_test_from_file`](#get_test_from_file) | `get_tests.py` | Parse a single test YAML file |
| [`run_unittest`](#run_unittest) | `run_tests.py` | Run tests sequentially, return structured summary |
| [`update_snapshot`](#update_snapshot) | `run_tests.py` | Run tests with snapshot update (`-u` flag) |
| [`run_tests_parallel`](#run_tests_parallel) | `run_tests_parallel.py` | Discover + run tests in parallel, grouped by suite |
| [`validate_schema`](#validate_schema) | `schema_validator.py` | Validate a single test file against the official JSON schema |
| [`validate_tests`](#validate_tests) | `schema_validator.py` | Batch-validate every test file in a directory |
| [`get_test_coverage`](#get_test_coverage) | `coverage.py` | Analyse template coverage for a Helm chart |
| [`get_rendered_debug_output`](#get_rendered_debug_output) | `debug.py` | Run tests in debug mode and extract rendered manifests |
| [`get_snapshots`](#get_snapshots) | `snapshots.py` | List and parse all snapshot files in a chart |
| [`diff_snapshot`](#diff_snapshot) | `snapshots.py` | Compare stored snapshot against live rendered output |
| [`clean_snapshots`](#clean_snapshots) | `snapshots.py` | Remove orphaned or obsolete snapshot entries |

---

## `get_tests`

```python
get_tests(
    dir_path: str,
    pattern: Optional[str] = "",
    include_release: bool = False,
    suite_pattern: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> list[TestFile]
```

Recursively walks `dir_path`, parses every matching YAML file as a `helm-unittest` test suite, and returns a list of [`TestFile`](./utils.md#testfile) objects.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `dir_path` | `str` | — | Root directory to scan |
| `pattern` | `str` | `""` | Regex to filter file **names** (empty = all `.yaml`) |
| `include_release` | `bool` | `false` | Include the `release:` block in results |
| `suite_pattern` | `str` | `null` | Regex to filter by **suite name** |
| `limit` | `int` | `null` | Max results to return |
| `offset` | `int` | `0` | Skip the first N results (pagination) |

### Returns

`list[TestFile]` — see [TestFile DTO](./utils.md#testfile).

### Notes

- Uses a custom YAML loader that tolerates duplicate anchors common in `helm-unittest` files.
- Files that fail to parse are skipped with a warning; they do not raise an error.

---

## `get_test_from_file`

```python
get_test_from_file(
    test_file_path: str,
    include_release: bool = False,
) -> TestFile
```

Parses a single `helm-unittest` YAML file and returns a [`TestFile`](./utils.md#testfile).

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `test_file_path` | `str` | — | Absolute or relative path to the YAML test file |
| `include_release` | `bool` | `false` | Include the `release:` block |

### Raises

`FileNotFoundError`, `PermissionError`, `yaml.YAMLError`, `KeyError` (missing `suite`/`tests`), `TypeError`, `ValueError`.

---

## `run_unittest`

```python
run_unittest(
    test_suite_files: str,
    chart_path: str,
    values_path: list[str] = [],
    output_type: str = "xunit",
    output_file: Optional[str] = None,
    include_test_cases: str = "failed_only",
    max_message_length: Optional[int] = 1000,
    strict: bool = False,
    fail_fast: bool = False,
    with_subchart: Optional[bool] = None,
    skip_schema_validation: bool = False,
    chart_tests_path: Optional[str] = None,
    debug: bool = False,
) -> TestResultSummary
```

Runs `helm unittest` **sequentially** for the given glob pattern and returns a [`TestResultSummary`](./utils.md#testresultsummary).

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `test_suite_files` | `str` | — | Glob pattern, e.g. `tests/*_test.yaml` |
| `chart_path` | `str` | — | Path to the Helm chart root |
| `values_path` | `list[str]` | `[]` | Extra `-v values.yaml` overrides |
| `output_type` | `str` | `"xunit"` | `"xunit"`, `"junit"`, `"nunit"`, or `"sonar"` |
| `output_file` | `str` | `null` | Persist the XML report; temp file used otherwise |
| `include_test_cases` | `str` | `"failed_only"` | `"failed_only"`, `"all"`, or `"none"` |
| `max_message_length` | `int` | `1000` | Truncate failure messages beyond this length |
| `strict` | `bool` | `false` | Fail on unknown fields in test files |
| `fail_fast` | `bool` | `false` | Stop on first failure |
| `with_subchart` | `bool` | `null` | Include subchart tests |
| `skip_schema_validation` | `bool` | `false` | Skip Helm values schema validation |
| `chart_tests_path` | `str` | `null` | Custom tests directory inside the chart |
| `debug` | `bool` | `false` | Enable `--debugPlugin` output |

---

## `update_snapshot`

Same signature as [`run_unittest`](#run_unittest). Internally passes `-u` to `helm unittest`, which regenerates all `__snapshot__/*.snap` files.

---

## `run_tests_parallel`

```python
run_tests_parallel(
    dir_path: str,
    chart_path: str,
    pattern: Optional[str] = "",
    values_path: list[str] = [],
    output_type: str = "xunit",
    max_workers: Optional[int] = None,
    include_test_cases: str = "failed_only",
    max_message_length: Optional[int] = 1000,
    strict: bool = False,
    fail_fast: bool = False,
    with_subchart: Optional[bool] = None,
    skip_schema_validation: bool = False,
    chart_tests_path: Optional[str] = None,
    debug: bool = False,
) -> TestResultSummary
```

**Recommended default** for running tests. Discovers all test files via `get_tests`, groups them by suite name, and runs each suite group concurrently using `ThreadPoolExecutor`. Tests within a single suite run sequentially.

### Additional Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `dir_path` | `str` | — | Directory to scan for test files |
| `max_workers` | `int` | `null` | Thread pool size (defaults to Python's `ThreadPoolExecutor` heuristic) |

Returns an **aggregate** [`TestResultSummary`](./utils.md#testresultsummary) (`elapsed_time` reflects real wall-clock time).

---

## `validate_schema`

```python
validate_schema(test_file_path: str) -> ValidationResult
```

Validates a single `helm-unittest` YAML file against the [official JSON schema](https://github.com/helm-unittest/helm-unittest/blob/main/schema/helm-testsuite.json). Falls back to the bundled offline schema when the network is unavailable.

### Returns

[`ValidationResult`](./utils.md#validationresult) with `success`, `message`, and `errors`.

---

## `validate_tests`

```python
validate_tests(
    dir_path: str,
    pattern: Optional[str] = "",
    only_failures: bool = False,
    return_summary: bool = False,
) -> list[ValidationResult] | BatchValidationSummary
```

Batch-validates every matching YAML file under `dir_path`.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `only_failures` | `bool` | `false` | Return only files that failed validation |
| `return_summary` | `bool` | `false` | Return a [`BatchValidationSummary`](./utils.md#batchvalidationsummary) instead of a list |

---

## `get_test_coverage`

```python
get_test_coverage(
    chart_path: str,
    tests_dir: str = "tests",
    pattern: Optional[str] = "",
    with_subcharts: bool = False,
) -> CoverageReport
```

Scans `<chart_path>/templates/` for renderable manifest files (`.yaml`, `.yml`, `.tpl`) and cross-references them with every discovered test suite to calculate coverage.

### Returns

[`CoverageReport`](./utils.md#coveragereport) containing per-template detail and an overall `coverage_percentage`.

### What counts as "covered"?

A template is considered covered if it appears in at least one test suite's `templates:` list or in an individual test's `template:` field.

---

## `get_rendered_debug_output`

```python
get_rendered_debug_output(
    chart_path: str,
    test_suite_files: str = "tests/*_test.yaml",
    values_path: list[str] = [],
) -> dict[str, str]
```

Runs `helm unittest -d` (debug mode) and returns a dictionary:

- Keys are **template file paths** relative to the chart.
- Values are the **rendered YAML** for each template.
- A special `__raw_debug_log__` key contains the full combined stdout+stderr.

Also reads any files written to `<chart_path>/.debug/` by the plugin.

Useful for troubleshooting assertion failures by inspecting the exact manifests produced by Helm.

---

## `get_snapshots`

```python
get_snapshots(
    chart_path: str,
    test_file_path: Optional[str] = None,
) -> list[SnapshotFile]
```

Walks the chart directory for `__snapshot__/*.snap` files, parses them, and returns a list of [`SnapshotFile`](./utils.md#snapshotfile) objects. Each `SnapshotFile` reports whether its associated test YAML still exists (`is_orphaned`).

Pass `test_file_path` to retrieve snapshots for a **specific** test file only.

---

## `diff_snapshot`

```python
diff_snapshot(
    chart_path: str,
    test_file_path: str,
    test_it: Optional[str] = None,
) -> SnapshotDiffResult
```

Compares the stored `.snap` content against the live rendered output (via `get_rendered_debug_output`) and returns a unified diff. Set `test_it` to scope the diff to a single test case.

### Returns

[`SnapshotDiffResult`](./utils.md#snapshotdiffresult) — `has_diff`, the unified `diff` string, and a human-readable `message`.

---

## `clean_snapshots`

```python
clean_snapshots(
    chart_path: str,
    dry_run: bool = True,
) -> SnapshotCleanResult
```

Detects and optionally removes:

1. **Orphaned snapshot files** — `.snap` files whose test YAML no longer exists.
2. **Obsolete snapshot entries** — entries within a `.snap` that no longer correspond to an active `it:` block.

By default `dry_run=True` — no files are modified.

### Returns

[`SnapshotCleanResult`](./utils.md#snapshotcleanresult) with lists of what was (or would be) cleaned.

---

_Next: [Prompts Reference →](./prompts.md)_
