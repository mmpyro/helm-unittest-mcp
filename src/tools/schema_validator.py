import os
import re
import yaml
import requests
from jsonschema import validate, ValidationError
from pathlib import Path
from typing import Optional
from utils.mcp import Server
from utils.dtos import ValidationResult

from functools import lru_cache


mcp = Server().mcp
schema_url = "https://raw.githubusercontent.com/helm-unittest/helm-unittest/refs/heads/main/schema/helm-testsuite.json"


@lru_cache(maxsize=1)
def _get_schema(url: str) -> dict:
    """Fetch and parse the JSON schema from the provided URL with caching."""
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


@mcp.tool()
def validate_schema(test_file_path: str) -> ValidationResult:
    """
    Validate a helm-unittest YAML test file against the official JSON schema.

    This function fetches the helm-unittest JSON schema from the official repository
    and validates the provided YAML test file against it. It ensures that the test
    file conforms to the expected structure and contains all required fields.

    Args:
        test_file_path (str): Path to the YAML test file to validate. Can be either
                             an absolute path or a relative path.

    Returns:
        ValidationResult: A dataclass containing validation results with the following attributes:
            - success (bool): True if validation passed, False otherwise
            - message (str): Human-readable message describing the result
            - errors (list[str] | None): List of validation error messages if validation passed, None otherwise

    Raises:
        FileNotFoundError: If the test file does not exist at the specified path
        yaml.YAMLError: If the test file contains invalid YAML syntax
        requests.RequestException: If the schema cannot be fetched from the URL

    Example:
        >>> result = validate_schema("tests/my-test_test.yaml")
        >>> if result["success"]:
        ...     print("Validation passed!")
        ... else:
        ...     print(f"Validation failed: {result['errors']}")
    """
    try:
        # Fetch the JSON schema (cached)
        schema = _get_schema(schema_url)

        # Load the YAML test file
        test_file = Path(test_file_path)
        if not test_file.exists():
            raise FileNotFoundError(f"Test file not found: {test_file_path}")

        with open(test_file, 'r', encoding='utf-8') as f:
            test_data = yaml.safe_load(f)

        # Validate the test data against the schema
        validate(instance=test_data, schema=schema)

        return ValidationResult(
            success=True,
            message=f"Validation successful for {test_file_path}"
        )

    except FileNotFoundError as e:
        return ValidationResult(
            success=False,
            message=str(e),
            errors=[str(e)]
        )

    except yaml.YAMLError as e:
        return ValidationResult(
            success=False,
            message=f"Invalid YAML syntax in {test_file_path}",
            errors=[f"YAML parsing error: {str(e)}"]
        )

    except requests.RequestException as e:
        return ValidationResult(
            success=False,
            message=f"Failed to fetch schema from {schema_url}",
            errors=[f"Network error: {str(e)}"]
        )

    except ValidationError as e:
        return ValidationResult(
            success=False,
            message=f"Schema validation failed for {test_file_path}",
            errors=[
                f"Validation error at {'.'.join(str(p) for p in e.path)}: {e.message}"
            ]
        )

    except Exception as e:
        return ValidationResult(
            success=False,
            message="Unexpected error during validation",
            errors=[f"Error: {str(e)}"]
        )


@mcp.tool()
def validate_tests(dir_path: str, pattern: Optional[str] = "") -> list[ValidationResult]:
    """Recursively validate all test files from a directory and its subdirectories.

    This function walks through the specified directory and validates each matching
    test file against the helm-unittest JSON schema. It follows the same pattern
    as get_tests but returns validation results instead of parsed test data.

    Args:
        dir_path (str): Path to the directory to search for test files
        pattern (Optional[str]): Optional regex pattern to filter files. If empty or None,
                                matches all .yaml files. Otherwise, uses the provided regex pattern.

    Returns:
        list[ValidationResult]: List of ValidationResult objects, one for each file that was
                                attempted to be validated. Files that match the pattern but fail
                                to validate will have success=False in their result.

    Raises:
        ValueError: If dir_path is empty, not a string, or pattern is invalid regex
        FileNotFoundError: If the directory doesn't exist
        NotADirectoryError: If dir_path is not a directory

    Example:
        >>> results = validate_tests("tests/", pattern=r".*_test\\.yaml$")
        >>> for result in results:
        ...     if not result.success:
        ...         print(f"Failed: {result.message}")
        ...         print(f"Errors: {result.errors}")
    """
    # Validate input
    if not dir_path:
        raise ValueError("dir_path cannot be empty")

    if not isinstance(dir_path, str):
        raise TypeError(f"dir_path must be a string, got {type(dir_path).__name__}")

    # Check if directory exists
    if not os.path.exists(dir_path):
        raise FileNotFoundError(f"Directory not found: {dir_path}")

    if not os.path.isdir(dir_path):
        raise NotADirectoryError(f"Path is not a directory: {dir_path}")

    # Determine the pattern to use
    if pattern is None or pattern.strip() == "":
        # Default pattern: match all .yaml files
        file_pattern = re.compile(r".*\.yaml$", re.IGNORECASE)
    else:
        # Use the provided regex pattern
        try:
            file_pattern = re.compile(pattern)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern '{pattern}': {e}")

    validation_results = []

    # Recursively walk through directory
    for root, dirs, files in os.walk(dir_path):
        for filename in files:
            # Check if filename matches the pattern
            if file_pattern.match(filename):
                file_path = os.path.join(root, filename)

                # Validate the file
                try:
                    result = validate_schema(file_path)
                    validation_results.append(result)
                except Exception as e:
                    # If validate_schema raises an exception (shouldn't happen as it catches all),
                    # create a failed validation result
                    validation_results.append(
                        ValidationResult(
                            success=False,
                            message=f"Unexpected error validating {file_path}",
                            errors=[f"Error: {str(e)}"]
                        )
                    )

    return validation_results
