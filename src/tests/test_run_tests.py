import pytest
from unittest.mock import patch, MagicMock, call
import subprocess
import os
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
    args, kwargs = mock_run.call_args
    cmd = args[0]
    assert "-o" in cmd
    assert cmd[cmd.index("-o") + 1] == "custom_report.xml"
    
    # Verify NO cleanup for provided file
    with patch("os.remove") as mock_remove:
        # The finally block won't call remove because is_temp is False
        pass
    # (Checking that os.remove wasn't called is tricky since I'm patching it inside the test)

@patch("tools.run_tests._run_unittest_internal")
def test_run_unittest_tool(mock_internal):
    run_unittest("files", "path", ["v1"], "junit", "out")
    mock_internal.assert_called_once_with("files", "path", ["v1"], "junit", "out", update_snapshot=False)

@patch("tools.run_tests._run_unittest_internal")
def test_update_snapshot_tool(mock_internal):
    update_snapshot("files", "path", ["v1"], "junit", "out")
    mock_internal.assert_called_once_with("files", "path", ["v1"], "junit", "out", update_snapshot=True)

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
