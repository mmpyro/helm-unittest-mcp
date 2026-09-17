from utils.mcp import Server


mcp = Server().mcp


@mcp.prompt()
def helm_unittest_assistant(test_directory: str, pattern: str = "") -> str:
    """Create a prompt to assist with analyzing Helm unittest files.

    This prompt helps users work with Helm unittest test files by providing
    context and guidance on how to use the get_tests tool to analyze test suites.

    Args:
        test_directory: Path to the directory containing Helm unittest files
        pattern: Optional regex pattern to filter test files. If empty,
                matches all .yaml files

    Returns:
        A formatted prompt string to guide the assistant in analyzing Helm tests
    """

    pattern_info = f"using pattern: '{pattern}'" if pattern else "for all .yaml files"

    return f"""You are a Helm unittest expert assistant. Your task is to help analyze and work with Helm unittest test files.

**Context:**
- Test directory: {test_directory}
- File filter: {pattern_info}

**Available Tools:**
1. `get_tests(dir_path, pattern, include_release=False, suite_pattern=None, limit=None, offset=0)` - \
Finds and parses test files. `dir_path` takes a directory or a single test file. Supports regex filtering by \
filename (`pattern`) or suite name (`suite_pattern`), pagination (`offset`/`limit`), and optional `release` \
dictionary inclusion (`include_release=False` by default to reduce output).

**Your Responsibilities:**
- Help users discover and analyze Helm unittest test files
- Explain the structure of test suites (suite name, tests, release configuration)
- Identify patterns and commonalities across test files
- Suggest improvements or identify potential issues in test definitions
- Provide insights about test coverage and organization

**Test File Structure:**
Each test file contains:
- `suite`: The name of the test suite
- `tests`: A list of test cases (each with an 'it' field describing the test)
- `release`: Optional release configuration (Helm values, etc., included only when `include_release=True` is passed)
- `file_path`: The path to the test file

Please start by analyzing the test files in the specified directory and provide a comprehensive overview of the test suites found."""


@mcp.prompt()
def validate_helm_tests(test_directory: str, pattern: str = "") -> str:
    """Create a prompt to assist with validating Helm unittest schema.

    This prompt helps users ensure their Helm unittest test files follow the official
    JSON schema by providing context and guidance on using the validation tools.

    Args:
        test_directory: Path to the directory containing Helm unittest files
        pattern: Optional regex pattern to filter test files

    Returns:
        A formatted prompt string for the assistant to validate Helm tests schema
    """

    pattern_info = f"using pattern: '{pattern}'" if pattern else "for all .yaml files"

    return f"""You are a Helm unittest validation assistant. Your goal is to ensure that Helm unittest test files are correctly structured according to the official JSON schema.

**Context:**
- Validation directory: {test_directory}
- File filter: {pattern_info}

**Validation Tools:**
1. `validate_tests(dir_path, pattern, only_failures=False, return_summary=True)` - \
Validates test files against the official JSON schema. `dir_path` takes a directory or a single test file. \
Returns counts plus the failures by default; pass `return_summary=False` for one result per file, or \
`only_failures=True` to list just the failures.

**Your Workflow:**
- Call `validate_tests` to check the quality and schema compliance of all test files in the specified directory.
- For each file that fails validation, provide a detailed report of the schema errors (e.g., missing required fields, incorrect data types).
- Pass a single file path as `dir_path` if the user wants to focus on one file.
- Explain the validation errors to the user in a helpful manner and suggest how to fix them to match the official `helm-unittest` schema.

**Common Schema Issues to Watch For:**
- Missing `suite` or `it` fields.
- Incorrect structure of `release` or `capabilities` blocks.
- Using unsupported keys in assertions or test configurations.

Please begin by validating the test files in the directory and report your findings on their schema compliance."""


@mcp.prompt()
def run_helm_tests(
    chart_path: str,
    test_directory: str = "tests",
    test_pattern: str = "",
    test_suite_files: str = "tests/*_test.yaml",
) -> str:
    """Create a prompt to assist with running Helm unittests and analyzing results.

    This prompt guides the assistant in executing Helm unittests and providing a
    clear, structured summary of the test outcomes.

    Args:
        chart_path: Path to the Helm chart to be tested
        test_directory: Path to the directory containing test files
        test_pattern: Optional regex pattern to filter test files
        test_suite_files: Glob pattern for test suite files (used for single-file runs)

    Returns:
        A formatted prompt string for the assistant to run and analyze Helm tests
    """

    pattern_info = (
        f"using pattern: '{test_pattern}'" if test_pattern else "for all .yaml files"
    )

    return f"""You are a Helm unittest execution assistant. Your goal is to run Helm unittests and provide a clear summary of the results.

**Context:**
- Chart Path: {chart_path}
- Test Directory: {test_directory}
- File Filter: {pattern_info}
- Test Suite Pattern (single-file runs): {test_suite_files}

**Available Tools:**
1. `run_tests(chart_path, path, update_snapshot=False, values_path, include_test_cases="failed_only", \
max_message_length=1000, max_test_cases=50, max_workers=None, output_type="xunit")` - \
Runs Helm unittests. A directory `path` is discovered and its suites run in parallel; a file or glob `path` runs \
sequentially. By default only failed test cases are returned (`include_test_cases="failed_only"`), capped at \
`max_test_cases`.

**Your Workflow:**
1. Call `run_tests` with `chart_path="{chart_path}"` and `path="{test_directory}"` to run all tests.
2. Analyze the `TestResultSummary` returned by the tool.
3. Present the results to the user in a clear, summarized format:
    - Overview: Total tests, Passed, Failed, Skipped, aggregate Execution Time (`time`), and wall-clock Elapsed Time (`elapsed_time`).
    - Note that passing test cases are excluded from `test_cases` list by default \
(`include_test_cases="failed_only"`), but count towards totals (`passed`, `total`). \
Set `include_test_cases="all"` if all individual passing test cases are needed, and raise `max_test_cases` \
if the list is truncated.
    - If there are failures: List each failed test case, including its suite name and error message (truncated to `max_message_length` if very long).
    - If all tests pass: Congratulate the user and highlight the successful execution.
4. If there are failures, offer to help investigate specific test files or explain the error messages based on your knowledge of Helm and the `helm-unittest` plugin.

Please start by running the tests for the specified chart and provide the execution summary."""


@mcp.prompt()
def update_helm_snapshots(
    chart_path: str, test_suite_files: str = "tests/*_test.yaml"
) -> str:
    """Create a prompt to assist with updating Helm unittest snapshots.

    This prompt guides the assistant in updating snapshots for Helm unittests using
    run_tests with update_snapshot=True, and providing a clear summary of the results.

    Args:
        chart_path: Path to the Helm chart
        test_suite_files: Glob pattern for test suite files

    Returns:
        A formatted prompt string for the assistant to update Helm snapshots
    """

    return f"""You are a Helm unittest snapshot management assistant. Your goal is to update the snapshot caches for your Helm unit tests when template changes are intentional.

**Context:**
- Chart Path: {chart_path}
- Test Suite Pattern: {test_suite_files}

**Available Tools:**
1. `run_tests(chart_path, path, update_snapshot=True, values_path, output_type, include_test_cases="failed_only", max_message_length=1000)` - \
With `update_snapshot=True`, rewrites snapshot files and returns a summary (`include_test_cases="failed_only"` by default).
2. `diff_snapshot(chart_path, test_file_path, test_it=None)` - Shows what would change before you commit to it.

**Your Workflow:**
1. Inform the user that you are about to update the snapshots for the tests matching `{test_suite_files}` in `{chart_path}`.
2. Call `run_tests` with `update_snapshot=True` and the provided parameters.
3. Analyze the `TestResultSummary` returned by the tool.
4. Present the results to the user:
    - Overview of the updated snapshots and test execution results.
    - If there are failures during the update (e.g., non-snapshot related failures): List each failed test case.
    - Confirm which snapshots were updated or created.
5. Remind the user to review the changes in the `__snapshot__` directories to ensure they match their expectations.

Please proceed with updating the snapshots for the specified chart."""
