import os
from typing import Annotated, Optional

from pydantic import Field

from utils.mcp import tool
from utils.dtos import TestResultSummary
from utils.types import IncludeCases, OutputType
from tools.run_tests import _run_unittest_internal
from tools.run_tests_parallel import run_parallel


@tool()
def run_tests(
    chart_path: str,
    path: Annotated[
        str,
        Field(
            description="Test file, glob, or directory relative to the chart. "
            "A directory is discovered and its suites run in parallel."
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
    max_workers: Optional[int] = None,
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

    if os.path.isdir(resolved):
        return run_parallel(
            dir_path=resolved,
            chart_path=chart_path,
            values_path=values_path,
            output_type=output_type,
            max_workers=max_workers,
            update_snapshot=update_snapshot,
            include_test_cases=include_test_cases,
            max_message_length=max_message_length,
            max_test_cases=max_test_cases,
            strict=strict,
            fail_fast=fail_fast,
            with_subchart=with_subchart,
            skip_schema_validation=skip_schema_validation,
            chart_tests_path=chart_tests_path,
        )

    return _run_unittest_internal(
        test_suite_files=path,
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
    )
