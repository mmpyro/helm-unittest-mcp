import subprocess
import tempfile
import os
import time
from typing import Optional, cast
from utils.mcp import Server, tool
from utils.parser import TestResultParser, TestFormat
from utils.dtos import TestResultSummary


mcp = Server().mcp


def _run_unittest_internal(
    test_suite_files: str,
    chart_path: str,
    values_path: list[str] = [],
    output_type: str = "xunit",
    output_file: Optional[str] = None,
    update_snapshot: bool = False,
    include_test_cases: str = "failed_only",
    max_message_length: Optional[int] = 1000,
    strict: bool = False,
    fail_fast: bool = False,
    with_subchart: Optional[bool] = None,
    skip_schema_validation: bool = False,
    chart_tests_path: Optional[str] = None,
    debug: bool = False,
) -> TestResultSummary:
    start_time = time.perf_counter()
    is_temp = False
    if not output_file:
        # Create a temporary file to store the XML report
        fd, output_file = tempfile.mkstemp(suffix=".xml")
        os.close(fd)
        is_temp = True

    cmd = [
        "helm",
        "unittest",
        "-f",
        test_suite_files,
        chart_path,
        "-t",
        output_type,
        "-o",
        output_file,
    ]
    if update_snapshot:
        cmd.append("-u")

    if strict:
        cmd.append("--strict")

    if fail_fast:
        cmd.append("--failfast")

    if with_subchart is not None:
        cmd.append(f"--with-subchart={str(with_subchart).lower()}")

    if skip_schema_validation:
        cmd.append("--skip-schema-validation")

    if chart_tests_path:
        cmd.extend(["--chart-tests-path", chart_tests_path])

    if debug:
        cmd.append("--debugPlugin")

    for v in values_path:
        cmd.append("-v")
        cmd.append(v)

    # Run the tests
    subprocess.run(cmd, text=True, capture_output=True, check=False)

    try:
        parser = TestResultParser(cast(TestFormat, output_type.lower()))
        summary = parser.parse(output_file)

        # Filter test cases and truncate messages
        filtered_cases = []
        for tc in summary.test_cases:
            if include_test_cases == "none":
                continue
            elif include_test_cases == "failed_only":
                if tc.result.lower() in ("pass", "passed"):
                    continue

            message = tc.message
            if (
                message
                and max_message_length is not None
                and max_message_length >= 0
                and len(message) > max_message_length
            ):
                overflow = len(message) - max_message_length
                message = (
                    message[:max_message_length] + f"\n... [truncated {overflow} chars]"
                )

            tc.message = message
            filtered_cases.append(tc)

        summary.test_cases = filtered_cases
        summary.elapsed_time = round(time.perf_counter() - start_time, 4)
        return summary

    finally:
        # Cleanup temporary file if we created one
        if is_temp and os.path.exists(output_file):
            try:
                os.remove(output_file)
            except Exception:
                pass


@tool()
def run_unittest(
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
) -> TestResultSummary:
    """Run helm unit tests sequentially for a specific test file or glob pattern.

    Use this tool for targeted, single-file test execution. For running all tests
    in a directory, prefer `run_tests_parallel` which discovers tests automatically,
    groups them by suite, and executes suites in parallel for faster results.

    Args:
        test_suite_files (str): Glob pattern for test suite files (e.g. "tests/*_test.yaml")
        chart_path (str): Path to the Helm chart to test
        values_path (list[str]): Optional list of paths to values files
        output_type (str): Format of the test report ("xunit", "junit", "nunit", or "sonar")
        output_file (str, optional): Path where to save the test report.
                                     If not provided, a temporary file will be used.
        include_test_cases (str): Which test cases to include in test_cases list:
                                  "failed_only" (default), "all", or "none".
        max_message_length (int, optional): Maximum character length for failure messages.
                                            Set to None or negative to disable truncation.
        strict (bool): Strictly parse the test suites (fail on unknown fields).
        fail_fast (bool): Quit testing immediately on the first failed test.
        with_subchart (bool, optional): Include tests of subcharts in charts folder.
        skip_schema_validation (bool): Skip values schema validation when rendering chart.
        chart_tests_path (str, optional): Folder location relative to chart where test suites are located.
        debug (bool): Enable verbose debug output from helm-unittest plugin.

    Returns:
        TestResultSummary: A summary of the test execution, including total counts and individual test cases.
    """
    return _run_unittest_internal(
        test_suite_files,
        chart_path,
        values_path,
        output_type,
        output_file,
        update_snapshot=False,
        include_test_cases=include_test_cases,
        max_message_length=max_message_length,
        strict=strict,
        fail_fast=fail_fast,
        with_subchart=with_subchart,
        skip_schema_validation=skip_schema_validation,
        chart_tests_path=chart_tests_path,
        debug=debug,
    )


@tool(destructive=True)
def update_snapshot(
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
) -> TestResultSummary:
    """Update snapshots for helm unit tests and return a summary of the results.

    Args:
        test_suite_files (str): Glob pattern for test suite files (e.g. "tests/*_test.yaml")
        chart_path (str): Path to the Helm chart to test
        values_path (list[str]): Optional list of paths to values files
        output_type (str): Format of the test report ("xunit", "junit", "nunit", or "sonar")
        output_file (str, optional): Path where to save the test report.
                                     If not provided, a temporary file will be used.
        include_test_cases (str): Which test cases to include in test_cases list:
                                  "failed_only" (default), "all", or "none".
        max_message_length (int, optional): Maximum character length for failure messages.
                                            Set to None or negative to disable truncation.
        strict (bool): Strictly parse the test suites.
        fail_fast (bool): Quit testing immediately on the first failed test.
        with_subchart (bool, optional): Include tests of subcharts in charts folder.
        skip_schema_validation (bool): Skip values schema validation when rendering chart.
        chart_tests_path (str, optional): Folder location relative to chart where test suites are located.
        debug (bool): Enable verbose debug output from helm-unittest plugin.

    Returns:
        TestResultSummary: A summary of the test execution, including total counts and individual test cases.
    """
    return _run_unittest_internal(
        test_suite_files,
        chart_path,
        values_path,
        output_type,
        output_file,
        update_snapshot=True,
        include_test_cases=include_test_cases,
        max_message_length=max_message_length,
        strict=strict,
        fail_fast=fail_fast,
        with_subchart=with_subchart,
        skip_schema_validation=skip_schema_validation,
        chart_tests_path=chart_tests_path,
        debug=debug,
    )
