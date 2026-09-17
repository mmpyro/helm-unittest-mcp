import os
import re
import yaml
import requests
from jsonschema import validate, ValidationError
from pathlib import Path
from typing import Annotated, Optional
from functools import lru_cache
from pydantic import Field
from utils.mcp import Server, tool
from utils.dtos import ValidationResult, BatchValidationSummary


mcp = Server().mcp
schema_url = "https://raw.githubusercontent.com/helm-unittest/helm-unittest/refs/heads/main/schema/helm-testsuite.json"


@lru_cache(maxsize=1)
def _get_schema(url: str) -> dict:
    """Fetch and parse the JSON schema from the provided URL with local fallback."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception:
        # Fallback to bundled schema
        bundled_path = Path(__file__).parent.parent / "resources" / "schemas" / "helm-testsuite.json"
        if bundled_path.exists():
            import json
            with open(bundled_path, "r", encoding="utf-8") as f:
                return json.load(f)
        raise


def validate_schema(test_file_path: str) -> ValidationResult:
    """Validate one helm-unittest YAML file against the official JSON schema."""
    try:
        # Fetch the JSON schema (cached)
        schema = _get_schema(schema_url)

        # Load the YAML test file
        test_file = Path(test_file_path)
        if not test_file.exists():
            raise FileNotFoundError(f"Test file not found: {test_file_path}")

        with open(test_file, "r", encoding="utf-8") as f:
            test_data = yaml.safe_load(f)

        # Validate the test data against the schema
        validate(instance=test_data, schema=schema)

        return ValidationResult(
            success=True, message=f"Validation successful for {test_file_path}"
        )

    except FileNotFoundError as e:
        return ValidationResult(success=False, message=str(e), errors=[str(e)])

    except yaml.YAMLError as e:
        return ValidationResult(
            success=False,
            message=f"Invalid YAML syntax in {test_file_path}",
            errors=[f"YAML parsing error: {str(e)}"],
        )

    except requests.RequestException as e:
        return ValidationResult(
            success=False,
            message=f"Failed to fetch schema from {schema_url}",
            errors=[f"Network error: {str(e)}"],
        )

    except ValidationError as e:
        return ValidationResult(
            success=False,
            message=f"Schema validation failed for {test_file_path}",
            errors=[
                f"Validation error at {'.'.join(str(p) for p in e.path)}: {e.message}"
            ],
        )

    except Exception as e:
        return ValidationResult(
            success=False,
            message="Unexpected error during validation",
            errors=[f"Error: {str(e)}"],
        )


@tool(read_only=True, idempotent=True)
def validate_tests(
    dir_path: Annotated[
        str, Field(description="Directory to search, or a single test file")
    ],
    pattern: Annotated[
        Optional[str], Field(description="Regex over filenames; empty matches every .yaml")
    ] = "",
    only_failures: Annotated[
        bool, Field(description="Return only the files that failed validation")
    ] = False,
    return_summary: Annotated[
        bool, Field(description="Return counts plus failures instead of one result per file")
    ] = True,
) -> list[ValidationResult] | BatchValidationSummary:
    """Recursively validate every helm-unittest file in a directory against the official JSON schema."""
    # Validate input
    if not dir_path:
        raise ValueError("dir_path cannot be empty")

    if not isinstance(dir_path, str):
        raise TypeError(f"dir_path must be a string, got {type(dir_path).__name__}")

    # Check if directory exists
    if not os.path.exists(dir_path):
        raise FileNotFoundError(f"Directory not found: {dir_path}")

    if not os.path.isdir(dir_path):
        return _summarize([validate_schema(dir_path)], only_failures, return_summary)

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
                            errors=[f"Error: {str(e)}"],
                        )
                    )

    return _summarize(validation_results, only_failures, return_summary)


def _summarize(
    results: list[ValidationResult],
    only_failures: bool,
    return_summary: bool,
) -> list[ValidationResult] | BatchValidationSummary:
    failures = [r for r in results if not r.success]
    if return_summary:
        return BatchValidationSummary(
            total_files=len(results),
            valid_files=len(results) - len(failures),
            invalid_files=len(failures),
            failures=failures,
        )
    return failures if only_failures else results
