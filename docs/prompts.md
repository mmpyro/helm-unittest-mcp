# Prompts Reference

MCP prompts are reusable **prompt templates** that an AI client can invoke to start a guided workflow. They are defined in [`src/prompt/prompts.py`](../src/prompt/prompts.py) and registered via `@mcp.prompt()`.

Unlike tools, prompts return a **formatted string** that becomes the system or user message, providing the LLM with context, available tools, and a recommended workflow.

---

## Available Prompts

| Prompt name | Function | Typical use-case |
|---|---|---|
| `helm_unittest_assistant` | [`helm_unittest_assistant`](#helm_unittest_assistant) | Explore and analyse existing test suites |
| `validate_helm_tests` | [`validate_helm_tests`](#validate_helm_tests) | Check schema compliance of test files |
| `run_helm_tests` | [`run_helm_tests`](#run_helm_tests) | Execute all tests and review results |
| `update_helm_snapshots` | [`update_helm_snapshots`](#update_helm_snapshots) | Regenerate snapshot files after template changes |

---

## `helm_unittest_assistant`

```python
helm_unittest_assistant(
    test_directory: str,
    pattern: str = "",
) -> str
```

Generates a prompt that instructs the LLM to act as a **Helm unittest expert** and analyse test files in the given directory.

### Workflow the LLM follows

1. Call `get_tests(dir_path=test_directory, pattern=pattern)`.
2. Provide an overview of the discovered test suites.
3. Identify patterns, commonalities, coverage gaps, and potential issues.

### When to use

- You want the LLM to give you an overview of your test organisation.
- You need help understanding what is covered or how tests are structured.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `test_directory` | `str` | — | Path to the directory containing test YAML files |
| `pattern` | `str` | `""` | Optional regex to filter test files |

---

## `validate_helm_tests`

```python
validate_helm_tests(
    test_directory: str,
    pattern: str = "",
) -> str
```

Instructs the LLM to **validate** all test files in a directory against the official `helm-unittest` JSON schema and report any errors.

### Workflow the LLM follows

1. Call `validate_tests(dir_path=test_directory, pattern=pattern)`.
2. Report schema violations with error details.
3. Explain how to fix each issue.

### When to use

- Before committing test changes to CI.
- After upgrading `helm-unittest` to check for breaking schema changes.
- When a test file fails with a cryptic parse error.

### Common issues the prompt guards against

- Missing `suite` or `it` fields.
- Incorrect `release` or `capabilities` block structure.
- Unsupported assertion keys.

---

## `run_helm_tests`

```python
run_helm_tests(
    chart_path: str,
    test_directory: str = "tests",
    test_pattern: str = "",
    test_suite_files: str = "tests/*_test.yaml",
) -> str
```

Instructs the LLM to **run all unit tests** for a Helm chart and present a clear summary.

### Workflow the LLM follows

1. Call `run_tests(chart_path=chart_path, path=test_directory)`.
2. Parse the returned [`TestResultSummary`](./utils.md#testresultsummary).
3. Present: total / passed / failed / skipped counts, wall-clock time.
4. List each failed test case with suite name and (truncated) error message.
5. Offer to investigate failures.

> A directory `path` runs suites in parallel; pass a file or glob to run one suite sequentially.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `chart_path` | `str` | — | Path to the Helm chart |
| `test_directory` | `str` | `"tests"` | Relative path to the tests folder |
| `test_pattern` | `str` | `""` | Regex filter for test file names |
| `test_suite_files` | `str` | `"tests/*_test.yaml"` | Glob for single-file runs |

---

## `update_helm_snapshots`

```python
update_helm_snapshots(
    chart_path: str,
    test_suite_files: str = "tests/*_test.yaml",
) -> str
```

Instructs the LLM to **regenerate snapshot files** after intentional template changes.

### Workflow the LLM follows

1. Inform the user which snapshots will be updated.
2. Call `run_tests(chart_path=…, path=…, update_snapshot=True)`.
3. Report the execution summary.
4. Remind the user to review changes in `__snapshot__/` directories.

### When to use

- After modifying a template that has existing snapshot assertions (`matchSnapshot`).
- When `helm unittest` fails with "snapshot mismatch" due to an intentional change.

> **Warning**: Always review the generated diff before committing updated snapshots to version control.

---

_Next: [Utils & DTOs →](./utils.md)_
