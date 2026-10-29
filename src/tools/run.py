import os
from typing import Annotated, Optional

from pydantic import Field

from utils.mcp import tool
from utils.dtos import TestResultSummary
from utils.types import IncludeCases, OutputType
from tools.get_tests import get_tests
from tools.run_tests import _chart_relative, _run_unittest_internal


@tool()
def run_tests(
    chart_path: str,
    path: Annotated[
        str,
        Field(
            description="Test file, glob, or directory relative to the chart. "
            "A directory is discovered and its suites run with helm unittest --parallel."
        ),
    ] = "tests",
    update_snapshot: Annotated[
        bool, Field(description="Rewrite stored snapshots to match the current render")
    ] = False,
    values_path: list[str] = [],
    include_test_cases: IncludeCases = "failed_only",
    max_message_length: Annotated[
        Optional[int], Field(description="Per-message cap; null disables truncation")
    ] = 1000,
    max_test_cases: Annotated[
        int, Field(description="Cap on how many test cases come back")
    ] = 50,
    max_workers: Annotated[
        Optional[int],
        Field(description="--max-workers for directory runs; null means one per CPU core"),
    ] = None,
    output_type: OutputType = "xunit",
    output_file: Annotated[
        Optional[str], Field(description="Persist the report here instead of a temp file")
    ] = None,
    strict: bool = False,
    fail_fast: bool = False,
    with_subchart: Optional[bool] = None,
    skip_schema_validation: bool = False,
    chart_tests_path: Optional[str] = None,
) -> TestResultSummary:
    """Run a Helm chart's unit tests and summarize the results.

    Returns totals plus, by default, only the failing cases.
    """
    resolved = path if os.path.isdir(path) else os.path.join(chart_path, path)

    test_suite_files: str | list[str] = path
    parallel = os.path.isdir(resolved)
    if parallel:
        test_suite_files = [
            _chart_relative(t.file_path, chart_path) for t in get_tests(resolved)
        ]
        # With no -f, helm unittest would fall back to its own tests/*_test.yaml default.
        if not test_suite_files:
            return TestResultSummary(
                total=0, passed=0, failed=0, skipped=0, errors=0, time=0.0, test_cases=[]
            )

    return _run_unittest_internal(
        test_suite_files=test_suite_files,
        chart_path=chart_path,
        values_path=values_path,
        output_type=output_type,
        output_file=output_file,
        update_snapshot=update_snapshot,
        include_test_cases=include_test_cases,
        max_message_length=max_message_length,
        max_test_cases=max_test_cases,
        strict=strict,
        fail_fast=fail_fast,
        with_subchart=with_subchart,
        skip_schema_validation=skip_schema_validation,
        chart_tests_path=chart_tests_path,
        parallel=parallel,
        max_workers=max_workers,
    )
