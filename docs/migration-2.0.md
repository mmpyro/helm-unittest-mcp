# Migrating to 2.0

2.0 rewrites the tool surface to cost less context. Twelve tools became eight, several defaults flipped to
the cheap setting, and results are no longer sent twice.

Measured against the bundled `example/` chart:

| | 1.0.1 | 2.0.0 |
|---|---|---|
| `tools/list` payload, paid every session | 27,049 chars (~6,760 tokens) | **5,975 chars (~1,490 tokens)** |
| `get_rendered_debug_output` response | 77,465 chars | **3,998 chars** |
| `get_test_coverage` response | 2,777 chars | **213 chars** |
| `validate_tests` response | 1,586 chars | **103 chars** |

---

## Renamed and merged tools

| 1.0.1 | 2.0.0 |
|---|---|
| `run_unittest(test_suite_files, chart_path, …)` | `run_tests(chart_path, path, …)` |
| `update_snapshot(test_suite_files, chart_path, …)` | `run_tests(chart_path, path, update_snapshot=True, …)` |
| `run_tests_parallel(dir_path, chart_path, …)` | `run_tests(chart_path, path=<a directory>, …)` |
| `get_test_from_file(test_file_path)` | `get_tests(dir_path=<a file>)` — returns a one-element list |
| `validate_schema(test_file_path)` | `validate_tests(dir_path=<a file>)` |

`run_tests` picks its execution path from `path`: a directory is discovered and its suites run in parallel,
a file or glob runs sequentially. `path` defaults to `"tests"` and is resolved against `chart_path`.

The removed names remain importable as plain Python functions (`tools.run_tests._run_unittest_internal`,
`tools.run_tests_parallel.run_parallel`, `tools.get_tests.get_test_from_file`,
`tools.schema_validator.validate_schema`); they are simply no longer registered as MCP tools.

## Changed defaults

| Tool | Parameter | 1.0.1 | 2.0.0 |
|---|---|---|---|
| `get_rendered_debug_output` | `include_raw_log` | always on | `False` |
| `get_snapshots` | `names_only` | n/a (always full) | `True` |
| `get_test_coverage` | `untested_only` | n/a (always full) | `True` |
| `validate_tests` | `return_summary` | `False` | `True` |
| `run_tests` | `max_test_cases` | n/a (unbounded) | `50` |

Each has an explicit opt-out: pass `include_raw_log=True`, `names_only=False`, `untested_only=False`,
`return_summary=False`, or raise `max_test_cases`.

## Removed parameters

- `debug` on the test-running tools. It appended `--debugPlugin`, whose output was captured and discarded,
  so the flag never had an observable effect. Use `get_rendered_debug_output` instead.
- `output_file` is still available on `run_tests`, but the parallel path ignores it.

## Result format

Tools now return a single compact JSON text block. Previously each result was sent twice — once as a
pretty-printed (`indent=2`) text block and again as `structuredContent` — and every tool advertised an
`outputSchema`. Clients that read `structuredContent` must read the text content instead.

The data itself is unchanged: the same DTOs, the same field names.

## Snapshot diffing

`diff_snapshot` now matches each snapshot entry to the rendered manifest it came from, by `kind` and
`metadata.name`, and diffs against that one manifest.

In 1.0.1 every entry was diffed against the concatenation of *all* rendered templates, so a chart that
rendered more than one template reported `has_diff: true` even when its snapshots were up to date, and the
returned diff repeated near-complete output once per entry. Existing callers that worked around that
behavior can drop the workaround. Entries that cannot be matched still fall back to the whole-render diff
and are now named in `message`.
