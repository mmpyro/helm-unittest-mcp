import pytest
from unittest.mock import patch, MagicMock, call
from tools.run_tests_parallel import (
    _group_tests_by_suite,
    _merge_summaries,
    _run_suite,
    run_tests_parallel,
)
from utils.dtos import TestFile, TestResultSummary, TestCaseResult


# --- _group_tests_by_suite tests ---


class TestGroupTestsBySuite:
    def test_single_suite(self):
        files = [
            TestFile(
                suite="Suite A", tests=["t1"], release={}, file_path="/a/test1.yaml"
            ),
            TestFile(
                suite="Suite A", tests=["t2"], release={}, file_path="/a/test2.yaml"
            ),
        ]
        result = _group_tests_by_suite(files)

        assert len(result) == 1
        assert "Suite A" in result
        assert len(result["Suite A"]) == 2

    def test_multiple_suites(self):
        files = [
            TestFile(
                suite="Suite A", tests=["t1"], release={}, file_path="/a/test1.yaml"
            ),
            TestFile(
                suite="Suite B", tests=["t2"], release={}, file_path="/b/test2.yaml"
            ),
            TestFile(
                suite="Suite A", tests=["t3"], release={}, file_path="/a/test3.yaml"
            ),
            TestFile(
                suite="Suite C", tests=["t4"], release={}, file_path="/c/test4.yaml"
            ),
        ]
        result = _group_tests_by_suite(files)

        assert len(result) == 3
        assert len(result["Suite A"]) == 2
        assert len(result["Suite B"]) == 1
        assert len(result["Suite C"]) == 1

    def test_empty_list(self):
        result = _group_tests_by_suite([])
        assert result == {}

    def test_preserves_order_within_suite(self):
        files = [
            TestFile(
                suite="Suite A", tests=["t1"], release={}, file_path="/a/first.yaml"
            ),
            TestFile(
                suite="Suite A", tests=["t2"], release={}, file_path="/a/second.yaml"
            ),
            TestFile(
                suite="Suite A", tests=["t3"], release={}, file_path="/a/third.yaml"
            ),
        ]
        result = _group_tests_by_suite(files)

        paths = [f.file_path for f in result["Suite A"]]
        assert paths == ["/a/first.yaml", "/a/second.yaml", "/a/third.yaml"]


# --- _merge_summaries tests ---


class TestMergeSummaries:
    def test_merge_two_summaries(self):
        s1 = TestResultSummary(
            total=3,
            passed=2,
            failed=1,
            skipped=0,
            errors=0,
            time=1.5,
            test_cases=[
                TestCaseResult(name="t1", suite="S1", result="Pass", time=0.5),
                TestCaseResult(name="t2", suite="S1", result="Pass", time=0.5),
                TestCaseResult(
                    name="t3", suite="S1", result="Fail", time=0.5, message="err"
                ),
            ],
        )
        s2 = TestResultSummary(
            total=2,
            passed=1,
            failed=0,
            skipped=1,
            errors=0,
            time=0.8,
            test_cases=[
                TestCaseResult(name="t4", suite="S2", result="Pass", time=0.4),
                TestCaseResult(name="t5", suite="S2", result="Skip", time=0.4),
            ],
        )

        merged = _merge_summaries([s1, s2], elapsed_time=1.234)

        assert merged.total == 5
        assert merged.passed == 3
        assert merged.failed == 1
        assert merged.skipped == 1
        assert merged.errors == 0
        assert merged.time == pytest.approx(2.3)
        assert merged.elapsed_time == 1.234
        assert len(merged.test_cases) == 5

    def test_merge_empty_list(self):

        merged = _merge_summaries([])

        assert merged.total == 0
        assert merged.passed == 0
        assert merged.failed == 0
        assert merged.skipped == 0
        assert merged.errors == 0
        assert merged.time == 0.0
        assert merged.test_cases == []

    def test_merge_single_summary(self):
        s = TestResultSummary(
            total=1,
            passed=1,
            failed=0,
            skipped=0,
            errors=0,
            time=0.1,
            test_cases=[TestCaseResult(name="t1", suite="S", result="Pass", time=0.1)],
        )
        merged = _merge_summaries([s])

        assert merged.total == 1
        assert merged.passed == 1
        assert len(merged.test_cases) == 1

    def test_merge_aggregates_errors(self):
        s1 = TestResultSummary(
            total=1,
            passed=0,
            failed=0,
            skipped=0,
            errors=1,
            time=0.1,
            test_cases=[],
        )
        s2 = TestResultSummary(
            total=1,
            passed=0,
            failed=0,
            skipped=0,
            errors=1,
            time=0.2,
            test_cases=[],
        )
        merged = _merge_summaries([s1, s2])

        assert merged.errors == 2
        assert merged.total == 2


# --- _run_suite tests ---


class TestRunSuite:
    @patch("tools.run_tests_parallel._run_unittest_internal")
    def test_runs_files_sequentially(self, mock_internal):
        files = [
            TestFile(
                suite="Suite A", tests=["t1"], release={}, file_path="/a/test1.yaml"
            ),
            TestFile(
                suite="Suite A", tests=["t2"], release={}, file_path="/a/test2.yaml"
            ),
        ]
        mock_internal.side_effect = [
            TestResultSummary(
                total=1,
                passed=1,
                failed=0,
                skipped=0,
                errors=0,
                time=0.5,
                test_cases=[
                    TestCaseResult(name="t1", suite="Suite A", result="Pass", time=0.5)
                ],
            ),
            TestResultSummary(
                total=1,
                passed=1,
                failed=0,
                skipped=0,
                errors=0,
                time=0.3,
                test_cases=[
                    TestCaseResult(name="t2", suite="Suite A", result="Pass", time=0.3)
                ],
            ),
        ]

        result = _run_suite(files, "./chart", ["values.yaml"], "xunit", False)

        assert mock_internal.call_count == 2
        mock_internal.assert_any_call(
            test_suite_files="/a/test1.yaml",
            chart_path="./chart",
            values_path=["values.yaml"],
            output_type="xunit",
            update_snapshot=False,
            include_test_cases="failed_only",
            max_message_length=1000,
        )
        mock_internal.assert_any_call(
            test_suite_files="/a/test2.yaml",
            chart_path="./chart",
            values_path=["values.yaml"],
            output_type="xunit",
            update_snapshot=False,
            include_test_cases="failed_only",
            max_message_length=1000,
        )

        assert result.total == 2
        assert result.passed == 2
        assert result.time == pytest.approx(0.8)
        assert len(result.test_cases) == 2

    @patch("tools.run_tests_parallel._run_unittest_internal")
    def test_single_file_suite(self, mock_internal):
        files = [
            TestFile(suite="Solo", tests=["t1"], release={}, file_path="/a/test.yaml"),
        ]
        mock_internal.return_value = TestResultSummary(
            total=1,
            passed=1,
            failed=0,
            skipped=0,
            errors=0,
            time=0.2,
            test_cases=[
                TestCaseResult(name="t1", suite="Solo", result="Pass", time=0.2)
            ],
        )

        result = _run_suite(files, "./chart", [], "junit", True)

        mock_internal.assert_called_once_with(
            test_suite_files="/a/test.yaml",
            chart_path="./chart",
            values_path=[],
            output_type="junit",
            update_snapshot=True,
            include_test_cases="failed_only",
            max_message_length=1000,
        )
        assert result.total == 1

    @patch("tools.run_tests_parallel._run_unittest_internal")
    def test_converts_abs_path_to_rel_path(self, mock_internal):
        files = [
            TestFile(
                suite="Rel",
                tests=["t1"],
                release={},
                file_path="/chart/tests/sub/test.yaml",
            ),
        ]
        mock_internal.return_value = TestResultSummary(
            total=1,
            passed=1,
            failed=0,
            skipped=0,
            errors=0,
            time=0.2,
            test_cases=[
                TestCaseResult(name="t1", suite="Rel", result="Pass", time=0.2)
            ],
        )

        _run_suite(files, "/chart", [], "xunit", False)

        mock_internal.assert_called_once_with(
            test_suite_files="tests/sub/test.yaml",
            chart_path="/chart",
            values_path=[],
            output_type="xunit",
            update_snapshot=False,
            include_test_cases="failed_only",
            max_message_length=1000,
        )


# --- run_tests_parallel tests ---


class TestRunTestsParallel:
    @patch("tools.run_tests_parallel.get_tests")
    @patch("tools.run_tests_parallel._run_unittest_internal")
    def test_parallel_execution_multiple_suites(self, mock_internal, mock_get_tests):
        mock_get_tests.return_value = [
            TestFile(
                suite="Suite A", tests=["t1"], release={}, file_path="/a/test1.yaml"
            ),
            TestFile(
                suite="Suite B", tests=["t2"], release={}, file_path="/b/test2.yaml"
            ),
            TestFile(
                suite="Suite A", tests=["t3"], release={}, file_path="/a/test3.yaml"
            ),
        ]
        mock_internal.side_effect = [
            TestResultSummary(
                total=1,
                passed=1,
                failed=0,
                skipped=0,
                errors=0,
                time=0.5,
                test_cases=[
                    TestCaseResult(name="t1", suite="Suite A", result="Pass", time=0.5)
                ],
            ),
            TestResultSummary(
                total=1,
                passed=1,
                failed=0,
                skipped=0,
                errors=0,
                time=0.3,
                test_cases=[
                    TestCaseResult(name="t3", suite="Suite A", result="Pass", time=0.3)
                ],
            ),
            TestResultSummary(
                total=1,
                passed=0,
                failed=1,
                skipped=0,
                errors=0,
                time=0.4,
                test_cases=[
                    TestCaseResult(
                        name="t2",
                        suite="Suite B",
                        result="Fail",
                        time=0.4,
                        message="err",
                    )
                ],
            ),
        ]

        result = run_tests_parallel("/tests", "./chart")

        mock_get_tests.assert_called_once_with("/tests", "")
        assert result.total == 3
        assert result.passed == 2
        assert result.failed == 1
        assert result.elapsed_time is not None
        assert result.elapsed_time >= 0
        assert len(result.test_cases) == 3



    @patch("tools.run_tests_parallel.get_tests")
    def test_empty_test_files(self, mock_get_tests):
        mock_get_tests.return_value = []

        result = run_tests_parallel("/tests", "./chart")

        assert result.total == 0
        assert result.passed == 0
        assert result.test_cases == []

    @patch("tools.run_tests_parallel.get_tests")
    @patch("tools.run_tests_parallel._run_unittest_internal")
    def test_passes_pattern_to_get_tests(self, mock_internal, mock_get_tests):
        mock_get_tests.return_value = [
            TestFile(suite="S", tests=["t1"], release={}, file_path="/a/test.yaml"),
        ]
        mock_internal.return_value = TestResultSummary(
            total=1,
            passed=1,
            failed=0,
            skipped=0,
            errors=0,
            time=0.1,
            test_cases=[TestCaseResult(name="t1", suite="S", result="Pass", time=0.1)],
        )

        run_tests_parallel("/tests", "./chart", pattern=".*special.*")

        mock_get_tests.assert_called_once_with("/tests", ".*special.*")

    @patch("tools.run_tests_parallel.get_tests")
    @patch("tools.run_tests_parallel._run_unittest_internal")
    def test_suite_error_creates_failure_summary(self, mock_internal, mock_get_tests):
        mock_get_tests.return_value = [
            TestFile(suite="Good", tests=["t1"], release={}, file_path="/a/good.yaml"),
            TestFile(suite="Bad", tests=["t2"], release={}, file_path="/b/bad.yaml"),
        ]
        mock_internal.side_effect = [
            TestResultSummary(
                total=1,
                passed=1,
                failed=0,
                skipped=0,
                errors=0,
                time=0.2,
                test_cases=[
                    TestCaseResult(name="t1", suite="Good", result="Pass", time=0.2)
                ],
            ),
            Exception("Helm crashed"),
        ]

        result = run_tests_parallel("/tests", "./chart")

        assert result.total == 2
        assert result.passed == 1
        assert result.failed == 1
        assert result.errors == 1
        # The error message should be captured
        failed_cases = [tc for tc in result.test_cases if tc.result == "Fail"]
        assert len(failed_cases) == 1
        assert "Helm crashed" in (failed_cases[0].message or "")

    @patch("tools.run_tests_parallel.get_tests")
    @patch("tools.run_tests_parallel._run_unittest_internal")
    def test_single_suite_no_parallelism_overhead(self, mock_internal, mock_get_tests):
        mock_get_tests.return_value = [
            TestFile(suite="Only", tests=["t1"], release={}, file_path="/a/test1.yaml"),
            TestFile(suite="Only", tests=["t2"], release={}, file_path="/a/test2.yaml"),
        ]
        mock_internal.side_effect = [
            TestResultSummary(
                total=1,
                passed=1,
                failed=0,
                skipped=0,
                errors=0,
                time=0.3,
                test_cases=[
                    TestCaseResult(name="t1", suite="Only", result="Pass", time=0.3)
                ],
            ),
            TestResultSummary(
                total=1,
                passed=1,
                failed=0,
                skipped=0,
                errors=0,
                time=0.2,
                test_cases=[
                    TestCaseResult(name="t2", suite="Only", result="Pass", time=0.2)
                ],
            ),
        ]

        result = run_tests_parallel("/tests", "./chart")

        assert result.total == 2
        assert result.passed == 2
        assert mock_internal.call_count == 2

    @patch("tools.run_tests_parallel.get_tests")
    @patch("tools.run_tests_parallel._run_unittest_internal")
    def test_passes_values_and_output_type(self, mock_internal, mock_get_tests):
        mock_get_tests.return_value = [
            TestFile(suite="S", tests=["t1"], release={}, file_path="/a/test.yaml"),
        ]
        mock_internal.return_value = TestResultSummary(
            total=1,
            passed=1,
            failed=0,
            skipped=0,
            errors=0,
            time=0.1,
            test_cases=[TestCaseResult(name="t1", suite="S", result="Pass", time=0.1)],
        )

        run_tests_parallel(
            "/tests",
            "./chart",
            values_path=["v1.yaml", "v2.yaml"],
            output_type="junit",
        )

        mock_internal.assert_called_once_with(
            test_suite_files="/a/test.yaml",
            chart_path="./chart",
            values_path=["v1.yaml", "v2.yaml"],
            output_type="junit",
            update_snapshot=False,
            include_test_cases="failed_only",
            max_message_length=1000,
        )

    @patch("tools.run_tests_parallel.get_tests")
    @patch("tools.run_tests_parallel._run_unittest_internal")
    def test_passes_include_test_cases_and_max_message_length(
        self, mock_internal, mock_get_tests
    ):
        mock_get_tests.return_value = [
            TestFile(suite="S", tests=["t1"], release={}, file_path="/a/test.yaml"),
        ]
        mock_internal.return_value = TestResultSummary(
            total=1,
            passed=1,
            failed=0,
            skipped=0,
            errors=0,
            time=0.1,
            test_cases=[],
        )

        run_tests_parallel(
            "/tests",
            "./chart",
            include_test_cases="all",
            max_message_length=500,
        )

        mock_internal.assert_called_once_with(
            test_suite_files="/a/test.yaml",
            chart_path="./chart",
            values_path=[],
            output_type="xunit",
            update_snapshot=False,
            include_test_cases="all",
            max_message_length=500,
        )


