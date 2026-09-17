import pytest
from unittest.mock import patch, mock_open, MagicMock
import yaml
import os
from tools.get_tests import get_tests, get_test_from_file
from utils.dtos import TestFile

# Sample YAML content for testing
VALID_YAML = """
suite: Test Suite
release:
  name: my-release
  namespace: default
tests:
  - it: should render deployment
  - it: should render service
"""

INVALID_YAML = """
suite: Test Suite
  tests:
- it: indent error
"""

MISSING_FIELDS_YAML = """
suite: Test Suite
# missing tests
"""

NOT_A_DICT_YAML = """
- just
- a
- list
"""

DUPLICATE_ANCHOR_YAML = """
suite: Duplicate Anchor Suite
tests:
  - it: test case 1
    asserts:
      - documentIndex: &myDoc 0
        isKind:
          of: Pod
  - it: test case 2
    asserts:
      - documentIndex: &myDoc 0
        isKind:
          of: Deployment
"""


def test_get_test_from_file_success():
    with patch("builtins.open", mock_open(read_data=VALID_YAML)):
        result = get_test_from_file("fake_path.yaml")

        assert isinstance(result, TestFile)
        assert result.suite == "Test Suite"
        assert result.tests == ["should render deployment", "should render service"]
        assert result.release is None
        assert result.file_path == "fake_path.yaml"

    with patch("builtins.open", mock_open(read_data=VALID_YAML)):
        result_with_release = get_test_from_file("fake_path.yaml", include_release=True)

        assert isinstance(result_with_release, TestFile)
        assert result_with_release.release == {
            "name": "my-release",
            "namespace": "default",
        }


def test_get_test_from_file_duplicate_anchors():
    with patch("builtins.open", mock_open(read_data=DUPLICATE_ANCHOR_YAML)):
        result = get_test_from_file("dup_anchor.yaml")

        assert isinstance(result, TestFile)
        assert result.suite == "Duplicate Anchor Suite"
        assert result.tests == ["test case 1", "test case 2"]


def test_get_test_from_file_not_found():
    with patch("builtins.open", side_effect=FileNotFoundError):
        with pytest.raises(FileNotFoundError):
            get_test_from_file("nonexistent.yaml")


def test_get_test_from_file_invalid_yaml():
    with patch("builtins.open", mock_open(read_data=INVALID_YAML)):
        with pytest.raises(yaml.YAMLError):
            get_test_from_file("invalid.yaml")


def test_get_test_from_file_missing_fields():
    with patch("builtins.open", mock_open(read_data=MISSING_FIELDS_YAML)):
        with pytest.raises(KeyError):
            get_test_from_file("missing.yaml")


def test_get_test_from_file_not_a_dict():
    with patch("builtins.open", mock_open(read_data=NOT_A_DICT_YAML)):
        with pytest.raises(TypeError):
            get_test_from_file("not_a_dict.yaml")


def test_get_test_from_file_empty():
    with patch("builtins.open", mock_open(read_data="")):
        with pytest.raises(ValueError):
            get_test_from_file("empty.yaml")


@patch("os.path.exists")
@patch("os.path.isdir")
@patch("os.walk")
@patch("tools.get_tests.get_test_from_file")
def test_get_tests_success(mock_get_test, mock_walk, mock_isdir, mock_exists):
    # Setup mocks
    mock_exists.return_value = True
    mock_isdir.return_value = True
    mock_walk.return_value = [
        ("/root", ["dir1"], ["test1.yaml", "other.txt"]),
        ("/root/dir1", [], ["test2.yaml"]),
    ]

    mock_get_test.side_effect = [
        TestFile(
            suite="Suite 1", tests=["t1"], release=None, file_path="/root/test1.yaml"
        ),
        TestFile(
            suite="Suite 2",
            tests=["t2"],
            release=None,
            file_path="/root/dir1/test2.yaml",
        ),
    ]

    results = get_tests("/root")

    assert len(results) == 2
    assert results[0].suite == "Suite 1"
    assert results[1].suite == "Suite 2"
    assert mock_get_test.call_count == 2


@patch("os.path.exists")
@patch("os.path.isdir")
@patch("os.walk")
@patch("tools.get_tests.get_test_from_file")
def test_get_tests_with_pattern(mock_get_test, mock_walk, mock_isdir, mock_exists):
    mock_exists.return_value = True
    mock_isdir.return_value = True
    mock_walk.return_value = [
        ("/root", [], ["test1.yaml", "special_test.yaml", "other.yaml"])
    ]

    mock_get_test.side_effect = [
        TestFile(
            suite="Special Suite",
            tests=["t1"],
            release=None,
            file_path="/root/special_test.yaml",
        )
    ]

    # Only match files containing "special"
    results = get_tests("/root", pattern=".*special.*")

    assert len(results) == 1
    assert results[0].suite == "Special Suite"
    mock_get_test.assert_called_once_with(
        "/root/special_test.yaml", include_release=False
    )


@patch("os.path.exists")
@patch("os.path.isdir")
@patch("os.walk")
@patch("tools.get_tests.get_test_from_file")
def test_get_tests_filtering_and_pagination(
    mock_get_test, mock_walk, mock_isdir, mock_exists
):
    mock_exists.return_value = True
    mock_isdir.return_value = True
    mock_walk.return_value = [("/root", [], ["t1.yaml", "t2.yaml", "t3.yaml"])]

    mock_get_test.side_effect = [
        TestFile(suite="Deployment Suite", tests=["t1"], file_path="/root/t1.yaml"),
        TestFile(suite="Service Suite", tests=["t2"], file_path="/root/t2.yaml"),
        TestFile(
            suite="Deployment Ingress Suite", tests=["t3"], file_path="/root/t3.yaml"
        ),
    ]

    # Filter by suite pattern
    deploy_results = get_tests("/root", suite_pattern="Deployment.*")
    assert len(deploy_results) == 2
    assert deploy_results[0].suite == "Deployment Suite"
    assert deploy_results[1].suite == "Deployment Ingress Suite"

    # Reset mock for pagination test
    mock_get_test.side_effect = [
        TestFile(suite="S1", tests=["t1"], file_path="/root/t1.yaml"),
        TestFile(suite="S2", tests=["t2"], file_path="/root/t2.yaml"),
        TestFile(suite="S3", tests=["t3"], file_path="/root/t3.yaml"),
    ]

    # Pagination: offset=1, limit=1
    paginated = get_tests("/root", offset=1, limit=1)
    assert len(paginated) == 1
    assert paginated[0].suite == "S2"


@patch("os.path.exists")
def test_get_tests_dir_not_found(mock_exists):
    mock_exists.return_value = False
    with pytest.raises(FileNotFoundError):
        get_tests("/nonexistent")


@patch("os.path.exists")
@patch("os.path.isdir")
def test_get_tests_single_file(mock_isdir, mock_exists):
    mock_exists.return_value = True
    mock_isdir.return_value = False
    with patch("tools.get_tests.get_test_from_file") as mock_from_file:
        mock_from_file.return_value = TestFile(
            suite="s", tests=["t"], file_path="/path/to/file"
        )
        result = get_tests("/path/to/file")

    mock_from_file.assert_called_once_with("/path/to/file", include_release=False)
    assert [f.file_path for f in result] == ["/path/to/file"]


@patch("os.path.exists")
@patch("os.path.isdir")
def test_get_tests_invalid_pattern(mock_isdir, mock_exists):
    mock_exists.return_value = True
    mock_isdir.return_value = True
    with pytest.raises(ValueError, match="Invalid regex pattern"):
        get_tests("/root", pattern="[invalid")

    with pytest.raises(ValueError, match="Invalid suite regex pattern"):
        get_tests("/root", suite_pattern="[invalid")


@patch("os.path.exists")
@patch("os.path.isdir")
@patch("os.walk")
@patch("tools.get_tests.get_test_from_file")
def test_get_tests_resilience(mock_get_test, mock_walk, mock_isdir, mock_exists):
    # Test that get_tests continues even if one file fails to parse
    mock_exists.return_value = True
    mock_isdir.return_value = True
    mock_walk.return_value = [
        ("/root", [], ["good.yaml", "bad.yaml", "another_good.yaml"])
    ]

    def side_effect(path, include_release=False):
        if "bad" in path:
            raise ValueError("Bad file")
        return TestFile(
            suite=f"Suite {path}", tests=["t"], release=None, file_path=path
        )

    mock_get_test.side_effect = side_effect

    results = get_tests("/root")

    assert len(results) == 2
    assert results[0].file_path == "/root/good.yaml"
    assert results[1].file_path == "/root/another_good.yaml"
    assert mock_get_test.call_count == 3
