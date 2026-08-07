import concurrent.futures
import os
from typing import Optional
from collections import defaultdict
from utils.mcp import Server
from utils.dtos import TestFile, TestResultSummary, TestCaseResult
from tools.run_tests import _run_unittest_internal
from tools.get_tests import get_tests


mcp = Server().mcp


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


def _merge_summaries(summaries: list[TestResultSummary]) -> TestResultSummary:
    """Merge multiple TestResultSummary objects into a single aggregate summary.

    Args:
        summaries: List of TestResultSummary objects to merge

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
    )


def _run_suite(
    suite_files: list[TestFile],
    chart_path: str,
    values_path: list[str],
    output_type: str,
    update_snapshot: bool,
) -> TestResultSummary:
    """Run all test files for a single suite sequentially.

    Args:
        suite_files: List of TestFile objects belonging to the same suite
        chart_path: Path to the Helm chart to test
        values_path: Optional list of paths to values files
        output_type: Format of the test report
        update_snapshot: Whether to update snapshots

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
        )
        summaries.append(summary)

    return _merge_summaries(summaries)


@mcp.tool()
def run_tests_parallel(
    dir_path: str,
    chart_path: str,
    pattern: Optional[str] = "",
    values_path: list[str] = [],
    output_type: str = "xunit",
    max_workers: Optional[int] = None,
) -> TestResultSummary:
    """Run helm unit tests in parallel, grouped by suite.

    Discovers test files using get_tests, groups them by suite name,
    then executes each suite group in parallel using a thread pool.
    Tests within the same suite are executed sequentially to maintain
    ordering guarantees.

    Args:
        dir_path: Path to the directory containing test files
        chart_path: Path to the Helm chart to test
        pattern: Optional regex pattern to filter test files.
                 If empty or None, matches all .yaml files.
        values_path: Optional list of paths to values files
        output_type: Format of the test report ("xunit", "junit", or "nunit")
        max_workers: Maximum number of parallel workers. If None, defaults
                     to ThreadPoolExecutor's default.

    Returns:
        TestResultSummary: An aggregate summary of all test executions
    """
    test_files = get_tests(dir_path, pattern)

    if not test_files:
        return TestResultSummary(
            total=0,
            passed=0,
            failed=0,
            skipped=0,
            errors=0,
            time=0.0,
            test_cases=[],
        )

    suite_groups = _group_tests_by_suite(test_files)

    suite_summaries: list[TestResultSummary] = []

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=max_workers
    ) as executor:
        future_to_suite = {
            executor.submit(
                _run_suite,
                suite_files,
                chart_path,
                values_path,
                output_type,
                False,
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

    return _merge_summaries(suite_summaries)
