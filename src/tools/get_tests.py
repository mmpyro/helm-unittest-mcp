# The mcp instance is injected by server.py before this module is loaded
import os
import re
import yaml
from utils.mcp import Server
from utils.dtos import TestFile
from typing import Optional


mcp = Server().mcp


@mcp.tool()
def get_tests(dir_path: str, pattern: Optional[str] = "") -> list[TestFile]:
    """Recursively get all test files from a directory and its subdirectories.

    Args:
        dir_path: Path to the directory to search for test files
        pattern: Optional regex pattern to filter files. If empty or None,
                matches all .yaml files. Otherwise, uses the provided regex pattern.

    Returns:
        List of TestFile objects parsed from matching files

    Raises:
        ValueError: If dir_path is empty or not a string
        FileNotFoundError: If the directory doesn't exist
        NotADirectoryError: If dir_path is not a directory
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

    test_files = []

    # Recursively walk through directory
    for root, dirs, files in os.walk(dir_path):
        for filename in files:
            # Check if filename matches the pattern
            if file_pattern.match(filename):
                file_path = os.path.join(root, filename)

                # Try to parse the file
                try:
                    test_file = get_test_from_file(file_path)
                    test_files.append(test_file)
                except Exception as e:
                    # Log the error but continue processing other files
                    # This allows the function to be resilient to individual file errors
                    print(f"Warning: Failed to parse {file_path}: {e}")
                    continue

    return test_files


@mcp.tool()
def get_test_from_file(test_file_path: str) -> TestFile:
    """Get the helm unittests from the specified file.

    Args:
        test_file_path: Path to the YAML test file

    Returns:
        TestFile object containing the parsed test data

    Raises:
        FileNotFoundError: If the test file doesn't exist
        PermissionError: If the file cannot be read due to permissions
        yaml.YAMLError: If the file contains invalid YAML
        KeyError: If required fields are missing from the test file
        TypeError: If field values have incorrect types
        ValueError: If field values are invalid
    """
    # Validate input
    if not test_file_path:
        raise ValueError("test_file_path cannot be empty")

    if not isinstance(test_file_path, str):
        raise TypeError(f"test_file_path must be a string, got {type(test_file_path).__name__}")

    # Read and parse the file
    try:
        with open(test_file_path, 'r') as f:
            tests = yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Test file not found: {test_file_path}. "
            "Please verify the file path is correct and the file exists."
        )
    except PermissionError:
        raise PermissionError(
            f"Permission denied when reading test file: {test_file_path}. "
            "Please check file permissions."
        )
    except yaml.YAMLError as e:
        raise yaml.YAMLError(
            f"Invalid YAML syntax in test file {test_file_path}: {e}. "
            "Please ensure the file contains valid YAML."
        )
    except Exception as e:
        raise IOError(
            f"Unexpected error reading test file {test_file_path}: {e}"
        )

    # Validate parsed content
    if tests is None:
        raise ValueError(
            f"Test file {test_file_path} is empty or contains only null values"
        )

    if not isinstance(tests, dict):
        raise TypeError(
            f"Test file {test_file_path} must contain a YAML dictionary/object, "
            f"got {type(tests).__name__}"
        )

    # Validate required fields
    required_fields = ['suite', 'tests']
    missing_fields = [field for field in required_fields if field not in tests]

    if missing_fields:
        raise KeyError(
            f"Missing required field(s) in test file {test_file_path}: {', '.join(missing_fields)}. "
            f"Required fields are: {', '.join(required_fields)}"
        )

    # Validate field types
    suite = tests['suite']
    if not isinstance(suite, str):
        raise TypeError(
            f"Field 'suite' must be a string in {test_file_path}, "
            f"got {type(suite).__name__}"
        )

    if not suite.strip():
        raise ValueError(
            f"Field 'suite' cannot be empty in {test_file_path}"
        )

    test_list = tests['tests']
    if not isinstance(test_list, list):
        raise TypeError(
            f"Field 'tests' must be a list in {test_file_path}, "
            f"got {type(test_list).__name__}"
        )

    if not test_list:
        raise ValueError(
            f"Field 'tests' cannot be an empty list in {test_file_path}"
        )

    # Create and return TestFile object
    try:
        return TestFile(
            suite=suite,
            tests=[x.get('it').strip() for x in test_list],
            release=tests.get('release', {}),
            file_path=test_file_path
        )
    except Exception as e:
        raise ValueError(
            f"Failed to create TestFile object from {test_file_path}: {e}"
        )
