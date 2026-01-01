import subprocess
import tempfile
import os
from typing import Optional, cast
from utils.mcp import Server
from utils.parser import TestResultParser, TestFormat
from utils.dtos import TestResultSummary


mcp = Server().mcp


def _run_unittest_internal(
    test_suite_files: str,
    chart_path: str,
    values_path: list[str] = [],
    output_type: str = "xunit",
    output_file: Optional[str] = None,
    update_snapshot: bool = False
) -> TestResultSummary:
    is_temp = False
    if not output_file:
        # Create a temporary file to store the XML report
        fd, output_file = tempfile.mkstemp(suffix=".xml")
        os.close(fd)
        is_temp = True

    cmd = ["helm", "unittest", "-f", test_suite_files, chart_path, "-t", output_type, "-o", output_file]
    if update_snapshot:
        cmd.append("-u")

    for v in values_path:
        cmd.append("-v")
        cmd.append(v)

    # Run the tests
    subprocess.run(cmd, text=True, capture_output=True, check=False)

    try:
        parser = TestResultParser(cast(TestFormat, output_type))
        return parser.parse(output_file)
    finally:
        # Cleanup temporary file if we created one
        if is_temp and os.path.exists(output_file):
            try:
                os.remove(output_file)
            except Exception:
                pass


@mcp.tool()
def run_unittest(
    test_suite_files: str,
    chart_path: str,
    values_path: list[str] = [],
    output_type: str = "xunit",
    output_file: Optional[str] = None
) -> TestResultSummary:
    """Run helm unit tests and return a summary of the results.

    Args:
        test_suite_files (str): Glob pattern for test suite files (e.g. "tests/*_test.yaml")
        chart_path (str): Path to the Helm chart to test
        values_path (list[str]): Optional list of paths to values files
        output_type (str): Format of the test report ("xunit", "junit", or "nunit")
        output_file (str, optional): Path where to save the test report.
                                     If not provided, a temporary file will be used.

    Returns:
        TestResultSummary: A summary of the test execution, including total counts and individual test cases.
    """
    return _run_unittest_internal(
        test_suite_files,
        chart_path,
        values_path,
        output_type,
        output_file,
        update_snapshot=False
    )


@mcp.tool()
def update_snapshot(
    test_suite_files: str,
    chart_path: str,
    values_path: list[str] = [],
    output_type: str = "xunit",
    output_file: Optional[str] = None
) -> TestResultSummary:
    """Update snapshots for helm unit tests and return a summary of the results.

    Args:
        test_suite_files (str): Glob pattern for test suite files (e.g. "tests/*_test.yaml")
        chart_path (str): Path to the Helm chart to test
        values_path (list[str]): Optional list of paths to values files
        output_type (str): Format of the test report ("xunit", "junit", or "nunit")
        output_file (str, optional): Path where to save the test report.
                                     If not provided, a temporary file will be used.

    Returns:
        TestResultSummary: A summary of the test execution, including total counts and individual test cases.
    """
    return _run_unittest_internal(
        test_suite_files,
        chart_path,
        values_path,
        output_type,
        output_file,
        update_snapshot=True
    )
