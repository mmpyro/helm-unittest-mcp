from unittest.mock import patch

from tools.run import run_tests


@patch("tools.run.run_parallel")
def test_directory_path_runs_in_parallel(mock_parallel):
    run_tests(chart_path="example", path="tests")

    mock_parallel.assert_called_once()
    assert mock_parallel.call_args.kwargs["dir_path"] == "example/tests"
    assert mock_parallel.call_args.kwargs["chart_path"] == "example"


@patch("tools.run._run_unittest_internal")
def test_glob_path_runs_sequentially(mock_internal):
    run_tests(chart_path="example", path="tests/deployment/*_test.yaml")

    mock_internal.assert_called_once()
    assert mock_internal.call_args.kwargs["test_suite_files"] == (
        "tests/deployment/*_test.yaml"
    )


@patch("tools.run.run_parallel")
def test_absolute_directory_is_not_joined_to_chart_path(mock_parallel):
    run_tests(chart_path="example", path="example/tests")

    assert mock_parallel.call_args.kwargs["dir_path"] == "example/tests"


@patch("tools.run._run_unittest_internal")
def test_update_snapshot_is_forwarded(mock_internal):
    run_tests(chart_path="example", path="tests/x_test.yaml", update_snapshot=True)

    assert mock_internal.call_args.kwargs["update_snapshot"] is True
