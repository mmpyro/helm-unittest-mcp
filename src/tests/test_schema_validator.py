import pytest
import requests
from unittest.mock import patch, mock_open, MagicMock
from tools.schema_validator import validate_schema, validate_tests, _get_schema
from utils.dtos import ValidationResult, BatchValidationSummary


# Sample Data
MOCK_SCHEMA = {
    "type": "object",
    "required": ["suite"],
    "properties": {"suite": {"type": "string"}},
}

VALID_YAML = """
suite: Test Suite
"""

INVALID_YAML = """
suite: 123
"""

MALFORMED_YAML = """
suite: [
"""


def test_get_schema_success():
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_SCHEMA
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Clear cache to ensure the mock is called
        _get_schema.cache_clear()

        result = _get_schema("http://example.com/schema.json")
        assert result == MOCK_SCHEMA
        mock_get.assert_called_once()


def test_get_schema_network_failure_fallback():
    with patch("requests.get") as mock_get:
        mock_get.side_effect = requests.RequestException("Network error")
        _get_schema.cache_clear()

        # Should successfully load bundled schema
        result = _get_schema("http://example.com/schema.json")
        assert isinstance(result, dict)


def test_get_schema_total_failure():
    with patch("requests.get") as mock_get:
        mock_get.side_effect = requests.RequestException("Network error")
        with patch("pathlib.Path.exists", return_value=False):
            _get_schema.cache_clear()

            with pytest.raises(requests.RequestException):
                _get_schema("http://example.com/schema.json")


@patch("tools.schema_validator._get_schema")
@patch("pathlib.Path.exists")
@patch("builtins.open", new_callable=mock_open, read_data=VALID_YAML)
def test_validate_schema_success(mock_file, mock_exists, mock_get_schema):
    mock_get_schema.return_value = MOCK_SCHEMA
    mock_exists.return_value = True

    result = validate_schema("test.yaml")

    assert result.success is True
    assert "Validation successful" in result.message
    assert result.errors is None


@patch("tools.schema_validator._get_schema")
@patch("pathlib.Path.exists")
def test_validate_schema_file_not_found(mock_exists, mock_get_schema):
    mock_get_schema.return_value = MOCK_SCHEMA
    mock_exists.return_value = False

    result = validate_schema("nonexistent.yaml")

    assert result.success is False
    assert "Test file not found" in result.message
    assert result.errors == ["Test file not found: nonexistent.yaml"]


@patch("tools.schema_validator._get_schema")
@patch("pathlib.Path.exists")
@patch("builtins.open", new_callable=mock_open, read_data=MALFORMED_YAML)
def test_validate_schema_invalid_yaml(mock_file, mock_exists, mock_get_schema):
    mock_get_schema.return_value = MOCK_SCHEMA
    mock_exists.return_value = True

    result = validate_schema("malformed.yaml")

    assert result.success is False
    assert "Invalid YAML syntax" in result.message
    assert result.errors is not None
    assert any("YAML parsing error" in err for err in result.errors)


@patch("tools.schema_validator._get_schema")
def test_validate_schema_network_error(mock_get_schema):
    mock_get_schema.side_effect = requests.RequestException("Connection failed")

    result = validate_schema("test.yaml")

    assert result.success is False
    assert "Failed to fetch schema" in result.message
    assert result.errors is not None
    assert any("Network error" in err for err in result.errors)


@patch("tools.schema_validator._get_schema")
@patch("pathlib.Path.exists")
@patch("builtins.open", new_callable=mock_open, read_data=INVALID_YAML)
def test_validate_schema_validation_error(mock_file, mock_exists, mock_get_schema):
    mock_get_schema.return_value = MOCK_SCHEMA
    mock_exists.return_value = True

    # jsonschema.validate will be called internally
    result = validate_schema("invalid.yaml")

    assert result.success is False
    assert "Schema validation failed" in result.message
    assert result.errors is not None
    assert any("Validation error" in err for err in result.errors)


@patch("os.path.exists")
@patch("os.path.isdir")
@patch("os.walk")
@patch("tools.schema_validator.validate_schema")
def test_validate_tests_success(mock_validate, mock_walk, mock_isdir, mock_exists):
    mock_exists.return_value = True
    mock_isdir.return_value = True
    mock_walk.return_value = [("/root", [], ["test1.yaml", "test2.yaml", "readme.md"])]

    mock_validate.side_effect = [
        ValidationResult(success=True, message="OK"),
        ValidationResult(success=False, message="Fail", errors=["Err"]),
    ]

    results = validate_tests("/root", return_summary=False)

    assert isinstance(results, list)
    assert len(results) == 2
    assert results[0].success is True
    assert results[1].success is False
    assert mock_validate.call_count == 2


@patch("os.path.exists")
@patch("os.path.isdir")
@patch("os.walk")
@patch("tools.schema_validator.validate_schema")
def test_validate_tests_options(mock_validate, mock_walk, mock_isdir, mock_exists):
    mock_exists.return_value = True
    mock_isdir.return_value = True
    mock_walk.return_value = [("/root", [], ["valid.yaml", "invalid.yaml"])]

    mock_validate.side_effect = [
        ValidationResult(success=True, message="OK"),
        ValidationResult(success=False, message="Fail", errors=["Err"]),
    ]

    # Test only_failures=True
    failed_results = validate_tests("/root", only_failures=True, return_summary=False)
    assert isinstance(failed_results, list)
    assert len(failed_results) == 1
    assert failed_results[0].success is False

    # Reset side_effect
    mock_validate.side_effect = [
        ValidationResult(success=True, message="OK"),
        ValidationResult(success=False, message="Fail", errors=["Err"]),
    ]

    # Test return_summary=True
    summary = validate_tests("/root", return_summary=True)
    assert isinstance(summary, BatchValidationSummary)
    assert summary.total_files == 2
    assert summary.valid_files == 1
    assert summary.invalid_files == 1
    assert len(summary.failures) == 1
    assert summary.failures[0].success is False


@patch("os.path.exists")
@patch("os.path.isdir")
def test_validate_tests_invalid_dir(mock_isdir, mock_exists):
    mock_exists.return_value = False
    with pytest.raises(FileNotFoundError):
        validate_tests("/invalid")

    # A path that is not a directory is now validated as a single file
    mock_exists.return_value = True
    mock_isdir.return_value = False
    with patch("tools.schema_validator.validate_schema") as mock_validate:
        mock_validate.return_value = ValidationResult(success=True, message="OK")
        summary = validate_tests("/not_a_dir")
    mock_validate.assert_called_once_with("/not_a_dir")
    assert isinstance(summary, BatchValidationSummary)
    assert summary.total_files == 1


def test_validate_tests_invalid_pattern():
    with (
        patch("os.path.exists", return_value=True),
        patch("os.path.isdir", return_value=True),
    ):
        with pytest.raises(ValueError, match="Invalid regex pattern"):
            validate_tests("/root", pattern="[invalid")
