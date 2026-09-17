import concurrent.futures
import os
import time
from typing import Optional
from collections import defaultdict
from utils.dtos import TestFile, TestResultSummary, TestCaseResult
from utils.truncate import cap_test_cases
from tools.run_tests import _run_unittest_internal
from tools.get_tests import get_tests


def _group_tests_by_suite(
    test_files: list[TestFile],
) -> dict[str, list[TestFile]]:
    """Group test files by their suite name.

    Args:
        test_files: List of TestFile objects to group

    Returns:
        Dictionary mapping suite names to lists of TestFile objects
    """
    groups: dict[str, list[TestFile]] = defaultdict(list)
    for test_file in test_files:
        groups[test_file.suite].append(test_file)
    return dict(groups)


def _merge_summaries(
    summaries: list[TestResultSummary],
    elapsed_time: Optional[float] = None,
) -> TestResultSummary:
    """Merge multiple TestResultSummary objects into a single aggregate summary.

    Args:
        summaries: List of TestResultSummary objects to merge
        elapsed_time: Optional wall-clock elapsed time in seconds

    Returns:
        A single TestResultSummary with aggregated totals and
        concatenated test cases
    """
    total = 0
    passed = 0
    failed = 0
    skipped = 0
    errors = 0
    time = 0.0
    test_cases: list[TestCaseResult] = []

    for summary in summaries:
        total += summary.total
        passed += summary.passed
        failed += summary.failed
        skipped += summary.skipped
        errors += summary.errors
        time += summary.time
        test_cases.extend(summary.test_cases)

    return TestResultSummary(
        total=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
        errors=errors,
        time=time,
        test_cases=test_cases,
        elapsed_time=elapsed_time,
    )


def _run_suite(
    suite_files: list[TestFile],
    chart_path: str,
    values_path: list[str],
    output_type: str,
    update_snapshot: bool,
    include_test_cases: str = "failed_only",
    max_message_length: Optional[int] = 1000,
    strict: bool = False,
    fail_fast: bool = False,
    with_subchart: Optional[bool] = None,
    skip_schema_validation: bool = False,
    chart_tests_path: Optional[str] = None,
) -> TestResultSummary:
    """Run all test files for a single suite sequentially.

    Args:
        suite_files: List of TestFile objects belonging to the same suite
        chart_path: Path to the Helm chart to test
        values_path: Optional list of paths to values files
        output_type: Format of the test report
        update_snapshot: Whether to update snapshots
        include_test_cases: Which test cases to include in results ("failed_only", "all", "none")
        max_message_length: Maximum character length for failure messages
        strict: Whether to strictly parse test suites
        fail_fast: Whether to quit immediately on failure
        with_subchart: Whether to include subchart tests
        skip_schema_validation: Whether to skip schema validation
        chart_tests_path: Custom test directory location

    Returns:
        Merged TestResultSummary for the entire suite
    """
    summaries: list[TestResultSummary] = []
    for test_file in suite_files:
        test_path = test_file.file_path
        if os.path.isabs(test_path):
            try:
                rel_path = os.path.relpath(test_path, chart_path)
                if not rel_path.startswith(".."):
                    test_path = rel_path
            except ValueError:
                pass

        summary = _run_unittest_internal(
            test_suite_files=test_path,
            chart_path=chart_path,
            values_path=values_path,
            output_type=output_type,
            update_snapshot=update_snapshot,
            include_test_cases=include_test_cases,
            max_message_length=max_message_length,
            strict=strict,
            fail_fast=fail_fast,
            with_subchart=with_subchart,
            skip_schema_validation=skip_schema_validation,
            chart_tests_path=chart_tests_path,
        )
        summaries.append(summary)

    return _merge_summaries(summaries)


def run_parallel(
    dir_path: str,
    chart_path: str,
    pattern: Optional[str] = "",
    values_path: list[str] = [],
    output_type: str = "xunit",
    max_workers: Optional[int] = None,
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
    """Discover tests under a directory, group them by suite, and run the groups in parallel.

    Files within one suite run sequentially so their ordering guarantees hold.
    """
    start_time = time.perf_counter()
    test_files = get_tests(dir_path, pattern)

    if not test_files:
        elapsed_time = round(time.perf_counter() - start_time, 4)
        return TestResultSummary(
            total=0,
            passed=0,
            failed=0,
            skipped=0,
            errors=0,
            time=0.0,
            test_cases=[],
            elapsed_time=elapsed_time,
        )

    suite_groups = _group_tests_by_suite(test_files)

    suite_summaries: list[TestResultSummary] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_suite = {
            executor.submit(
                _run_suite,
                suite_files,
                chart_path,
                values_path,
                output_type,
                update_snapshot,
                include_test_cases,
                max_message_length,
                strict,
                fail_fast,
                with_subchart,
                skip_schema_validation,
                chart_tests_path,
            ): suite_name
            for suite_name, suite_files in suite_groups.items()
        }

        for future in concurrent.futures.as_completed(future_to_suite):
            suite_name = future_to_suite[future]
            try:
                result = future.result()
                suite_summaries.append(result)
            except Exception as e:
                # Create a failure summary for the suite that errored
                suite_summaries.append(
                    TestResultSummary(
                        total=1,
                        passed=0,
                        failed=1,
                        skipped=0,
                        errors=1,
                        time=0.0,
                        test_cases=[
                            TestCaseResult(
                                name=f"Suite execution: {suite_name}",
                                suite=suite_name,
                                result="Fail",
                                time=0.0,
                                message=str(e),
                            )
                        ],
                    )
                )

    elapsed_time = round(time.perf_counter() - start_time, 4)
    merged = _merge_summaries(suite_summaries, elapsed_time=elapsed_time)
    return cap_test_cases(merged, max_test_cases)
