import subprocess
import tempfile
import os
import time
from typing import Optional, cast
from utils.parser import TestResultParser, TestFormat
from utils.dtos import TestResultSummary
from utils.truncate import filter_test_cases


def _run_unittest_internal(
    test_suite_files: str,
    chart_path: str,
    values_path: list[str] = [],
    output_type: str = "xunit",
    output_file: Optional[str] = None,
    update_snapshot: bool = False,
    include_test_cases: str = "failed_only",
    max_message_length: Optional[int] = 1000,
    max_test_cases: Optional[int] = None,
    strict: bool = False,
    fail_fast: bool = False,
    with_subchart: Optional[bool] = None,
    skip_schema_validation: bool = False,
    chart_tests_path: Optional[str] = None,
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

    for v in values_path:
        cmd.append("-v")
        cmd.append(v)

    # Run the tests
    subprocess.run(cmd, text=True, capture_output=True, check=False)

    try:
        parser = TestResultParser(cast(TestFormat, output_type.lower()))
        summary = parser.parse(output_file)

        summary.test_cases = filter_test_cases(
            summary.test_cases,
            include_test_cases=include_test_cases,
            max_message_length=max_message_length,
            max_test_cases=max_test_cases,
        )
        summary.elapsed_time = round(time.perf_counter() - start_time, 4)
        return summary

    finally:
        # Cleanup temporary file if we created one
        if is_temp and os.path.exists(output_file):
            try:
                os.remove(output_file)
            except Exception:
                pass
