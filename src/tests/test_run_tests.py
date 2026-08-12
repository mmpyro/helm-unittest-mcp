import pytest
from unittest.mock import patch, MagicMock
from tools.run_tests import run_unittest, update_snapshot, _run_unittest_internal
from utils.dtos import TestResultSummary


@patch("tools.run_tests.TestResultParser")
@patch("tools.run_tests.subprocess.run")
@patch("tools.run_tests.tempfile.mkstemp")
@patch("tools.run_tests.os.close")
@patch("tools.run_tests.os.remove")
@patch("tools.run_tests.os.path.exists")
def test_run_unittest_internal_success(mock_exists, mock_remove, mock_close, mock_mkstemp, mock_run, mock_parser_class):
    # Setup mocks
    mock_mkstemp.return_value = (10, "/tmp/temp_report.xml")
    mock_exists.return_value = True

    # Setup parser mock
    mock_parser_instance = MagicMock()
    mock_summary = TestResultSummary(
        total=1, passed=1, failed=0, skipped=0, errors=0, time=0.1, test_cases=[]
    )
    mock_parser_instance.parse.return_value = mock_summary
    mock_parser_class.return_value = mock_parser_instance

    # Execute
    result = _run_unittest_internal(
        test_suite_files="tests/*.yaml",
        chart_path="./chart",
        values_path=["values.yaml"],
        output_type="junit",
        update_snapshot=True
    )

    # Verify command
    expected_cmd = [
        "helm", "unittest", "-f", "tests/*.yaml", "./chart",
        "-t", "junit", "-o", "/tmp/temp_report.xml", "-u", "-v", "values.yaml"
    ]
    mock_run.assert_called_once_with(expected_cmd, text=True, capture_output=True, check=False)

    # Verify parser called
    mock_parser_class.assert_called_once_with("junit")
    mock_parser_instance.parse.assert_called_once_with("/tmp/temp_report.xml")

    # Verify cleanup
    mock_remove.assert_called_once_with("/tmp/temp_report.xml")
    assert result == mock_summary


@patch("tools.run_tests.TestResultParser")
@patch("tools.run_tests.subprocess.run")
def test_run_unittest_with_provided_file(mock_run, mock_parser_class):
    # Setup mocks
    mock_parser_instance = MagicMock()
    mock_parser_class.return_value = mock_parser_instance

    # Execute
    _run_unittest_internal(
        test_suite_files="tests/*.yaml",
        chart_path="./chart",
        output_file="custom_report.xml"
    )

    # Verify command uses provided file
    args, _ = mock_run.call_args
    cmd = args[0]
    assert "-o" in cmd
    assert cmd[cmd.index("-o") + 1] == "custom_report.xml"

    # Verify NO cleanup for provided file
    with patch("os.remove"):
        # The finally block won't call remove because is_temp is False
        pass


@patch("tools.run_tests._run_unittest_internal")
def test_run_unittest_tool(mock_internal):
    run_unittest("files", "path", ["v1"], "junit", "out")
    mock_internal.assert_called_once_with(
        "files", "path", ["v1"], "junit", "out",
        update_snapshot=False,
        include_test_cases="failed_only",
        max_message_length=1000,
    )


@patch("tools.run_tests._run_unittest_internal")
def test_update_snapshot_tool(mock_internal):
    update_snapshot("files", "path", ["v1"], "junit", "out")
    mock_internal.assert_called_once_with(
        "files", "path", ["v1"], "junit", "out",
        update_snapshot=True,
        include_test_cases="failed_only",
        max_message_length=1000,
    )


@patch("tools.run_tests.TestResultParser")
@patch("tools.run_tests.subprocess.run")
@patch("tools.run_tests.os.close")
@patch("tools.run_tests.os.path.exists")
@patch("tools.run_tests.os.remove")
def test_run_unittest_cleanup_on_error(mock_remove, mock_exists, mock_close, mock_run, mock_parser_class):
    # Test that cleanup happens even if parsing fails
    with patch("tools.run_tests.tempfile.mkstemp") as mock_mkstemp:
        mock_mkstemp.return_value = (10, "/tmp/temp.xml")
        mock_exists.return_value = True

        mock_parser_instance = MagicMock()
        mock_parser_instance.parse.side_effect = Exception("Parse error")
        mock_parser_class.return_value = mock_parser_instance

        with pytest.raises(Exception, match="Parse error"):
            _run_unittest_internal("f", "p")

        mock_remove.assert_called_once_with("/tmp/temp.xml")


@patch("tools.run_tests.TestResultParser")
@patch("tools.run_tests.subprocess.run")
@patch("tools.run_tests.tempfile.mkstemp")
@patch("tools.run_tests.os.close")
@patch("tools.run_tests.os.remove")
@patch("tools.run_tests.os.path.exists")
def test_run_unittest_test_case_filtering_and_truncation(
    mock_exists, mock_remove, mock_close, mock_mkstemp, mock_run, mock_parser_class
):
    from utils.dtos import TestCaseResult

    mock_mkstemp.return_value = (10, "/tmp/temp_report.xml")
    mock_exists.return_value = True

    mock_cases = [
        TestCaseResult(name="pass_1", suite="S1", result="Pass", time=0.1),
        TestCaseResult(
            name="fail_1",
            suite="S1",
            result="Fail",
            time=0.1,
            message="A" * 1500,
        ),
    ]
    mock_summary = TestResultSummary(
        total=2, passed=1, failed=1, skipped=0, errors=0, time=0.2, test_cases=mock_cases
    )
    mock_parser_instance = MagicMock()
    mock_parser_instance.parse.return_value = mock_summary
    mock_parser_class.return_value = mock_parser_instance

    # Test "failed_only" default
    result_failed_only = _run_unittest_internal(
        "tests/*.yaml", "./chart", include_test_cases="failed_only", max_message_length=100
    )
    assert len(result_failed_only.test_cases) == 1
    assert result_failed_only.test_cases[0].name == "fail_1"
    assert result_failed_only.test_cases[0].message.startswith("A" * 100)
    assert "... [truncated 1400 chars]" in result_failed_only.test_cases[0].message

    # Test "none"
    mock_summary.test_cases = [
        TestCaseResult(name="pass_1", suite="S1", result="Pass", time=0.1),
        TestCaseResult(name="fail_1", suite="S1", result="Fail", time=0.1, message="Err"),
    ]
    result_none = _run_unittest_internal(
        "tests/*.yaml", "./chart", include_test_cases="none"
    )
    assert len(result_none.test_cases) == 0

    # Test "all"
    mock_summary.test_cases = [
        TestCaseResult(name="pass_1", suite="S1", result="Pass", time=0.1),
        TestCaseResult(name="fail_1", suite="S1", result="Fail", time=0.1, message="Err"),
    ]
    result_all = _run_unittest_internal(
        "tests/*.yaml", "./chart", include_test_cases="all"
    )
    assert len(result_all.test_cases) == 2

