import os
from unittest.mock import patch

from tools.run import run_tests
from utils.dtos import TestFile


def _test_file(path):
    return TestFile(suite="S", tests=["t"], release={}, file_path=path)


@patch("tools.run.get_tests")
@patch("tools.run._run_unittest_internal")
def test_directory_path_runs_in_parallel(mock_internal, mock_get_tests):
    mock_get_tests.return_value = [
        _test_file("example/tests/a_test.yaml"),
        _test_file(os.path.abspath("example/tests/b/b_test.yaml")),
    ]

    run_tests(chart_path="example", path="tests", max_workers=4)

    mock_get_tests.assert_called_once_with("example/tests")
    kwargs = mock_internal.call_args.kwargs
    assert kwargs["test_suite_files"] == ["tests/a_test.yaml", "tests/b/b_test.yaml"]
    assert kwargs["chart_path"] == "example"
    assert kwargs["parallel"] is True
    assert kwargs["max_workers"] == 4


@patch("tools.run.get_tests")
@patch("tools.run._run_unittest_internal")
def test_empty_directory_does_not_run_helm(mock_internal, mock_get_tests):
    mock_get_tests.return_value = []

    result = run_tests(chart_path="example", path="tests")

    mock_internal.assert_not_called()
    assert result.total == 0
    assert result.test_cases == []


@patch("tools.run.get_tests")
@patch("tools.run._run_unittest_internal")
def test_test_files_outside_chart_keep_their_path(
    mock_internal, mock_get_tests, tmp_path
):
    outside = str(tmp_path / "x_test.yaml")
    mock_get_tests.return_value = [_test_file(outside)]

    run_tests(chart_path="example", path=str(tmp_path))

    assert mock_internal.call_args.kwargs["test_suite_files"] == [outside]


@patch("tools.run._run_unittest_internal")
def test_glob_path_runs_sequentially(mock_internal):
    run_tests(chart_path="example", path="tests/deployment/*_test.yaml")

    mock_internal.assert_called_once()
    assert mock_internal.call_args.kwargs["test_suite_files"] == (
        "tests/deployment/*_test.yaml"
    )
    assert mock_internal.call_args.kwargs["parallel"] is False


@patch("tools.run.get_tests")
@patch("tools.run._run_unittest_internal")
def test_absolute_directory_is_not_joined_to_chart_path(mock_internal, mock_get_tests):
    mock_get_tests.return_value = [_test_file("example/tests/a_test.yaml")]

    run_tests(chart_path="example", path="example/tests")

    mock_get_tests.assert_called_once_with("example/tests")


@patch("tools.run._run_unittest_internal")
def test_update_snapshot_is_forwarded(mock_internal):
    run_tests(chart_path="example", path="tests/x_test.yaml", update_snapshot=True)

    assert mock_internal.call_args.kwargs["update_snapshot"] is True
