# The mcp instance is injected by server.py before this module is loaded
import os
import re
import yaml
from utils.mcp import tool
from utils.dtos import TestFile
from typing import Annotated, Optional
from pydantic import Field


class _DuplicateAnchorSafeLoader(yaml.SafeLoader):
    """A YAML SafeLoader that tolerates duplicate anchor names.

    Helm-unittest test files commonly reuse anchor names (e.g. &podDoc)
    across different test cases within the same document. The standard
    SafeLoader raises a ComposerError for these. This loader silently
    overwrites the previous anchor, matching YAML 1.2 semantics where
    the last definition of an anchor wins.
    """

    pass


_original_compose_node = _DuplicateAnchorSafeLoader.compose_node


def _compose_node_allow_duplicates(
    self: _DuplicateAnchorSafeLoader,
    parent: Optional[yaml.nodes.Node],
    index: int,
) -> Optional[yaml.nodes.Node]:
    if self.check_event(yaml.events.AliasEvent):
        return _original_compose_node(self, parent, index)
    event = self.peek_event()
    if event.anchor is not None and event.anchor in self.anchors:
        del self.anchors[event.anchor]
    return _original_compose_node(self, parent, index)


_DuplicateAnchorSafeLoader.compose_node = _compose_node_allow_duplicates  # type: ignore[assignment]


@tool(read_only=True, idempotent=True)
def get_tests(
    dir_path: Annotated[
        str, Field(description="Directory to search, or a single test file")
    ],
    pattern: Annotated[
        Optional[str], Field(description="Regex over filenames; empty matches every .yaml")
    ] = "",
    include_release: Annotated[
        bool, Field(description="Include each suite's release block")
    ] = False,
    suite_pattern: Annotated[Optional[str], Field(description="Regex over suite names")] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> list[TestFile]:
    """List the helm-unittest suites under a directory, with the name of every test they define.

    Accepts a single test file too, in which case the list holds one entry.
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
        return [get_test_from_file(dir_path, include_release=include_release)]

    # Determine the file pattern to use
    if pattern is None or pattern.strip() == "":
        # Default pattern: match all .yaml files
        file_pattern = re.compile(r".*\.yaml$", re.IGNORECASE)
    else:
        # Use the provided regex pattern
        try:
            file_pattern = re.compile(pattern)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern '{pattern}': {e}")

    # Determine the suite pattern if provided
    compiled_suite_pattern = None
    if suite_pattern is not None and suite_pattern.strip() != "":
        try:
            compiled_suite_pattern = re.compile(suite_pattern)
        except re.error as e:
            raise ValueError(f"Invalid suite regex pattern '{suite_pattern}': {e}")

    test_files = []

    # Recursively walk through directory
    for root, dirs, files in os.walk(dir_path):
        for filename in files:
            # Check if filename matches the pattern
            if file_pattern.match(filename):
                file_path = os.path.join(root, filename)

                # Try to parse the file
                try:
                    test_file = get_test_from_file(
                        file_path, include_release=include_release
                    )
                    # Filter by suite pattern if specified
                    if compiled_suite_pattern and not compiled_suite_pattern.search(
                        test_file.suite
                    ):
                        continue
                    test_files.append(test_file)
                except Exception as e:
                    # Log the error but continue processing other files
                    print(f"Warning: Failed to parse {file_path}: {e}")
                    continue

    # Apply pagination offset and limit
    if offset > 0:
        test_files = test_files[offset:]

    if limit is not None and limit >= 0:
        test_files = test_files[:limit]

    return test_files


def get_test_from_file(test_file_path: str, include_release: bool = False) -> TestFile:
    """Parse one helm-unittest YAML file into a TestFile."""
    # Validate input
    if not test_file_path:
        raise ValueError("test_file_path cannot be empty")

    if not isinstance(test_file_path, str):
        raise TypeError(
            f"test_file_path must be a string, got {type(test_file_path).__name__}"
        )

    # Read and parse the file
    try:
        with open(test_file_path, "r") as f:
            tests = yaml.load(f, Loader=_DuplicateAnchorSafeLoader)
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
        raise IOError(f"Unexpected error reading test file {test_file_path}: {e}")

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
    required_fields = ["suite", "tests"]
    missing_fields = [field for field in required_fields if field not in tests]

    if missing_fields:
        raise KeyError(
            f"Missing required field(s) in test file {test_file_path}: {', '.join(missing_fields)}. "
            f"Required fields are: {', '.join(required_fields)}"
        )

    # Validate field types
    suite = tests["suite"]
    if not isinstance(suite, str):
        raise TypeError(
            f"Field 'suite' must be a string in {test_file_path}, "
            f"got {type(suite).__name__}"
        )

    if not suite.strip():
        raise ValueError(f"Field 'suite' cannot be empty in {test_file_path}")

    test_list = tests["tests"]
    if not isinstance(test_list, list):
        raise TypeError(
            f"Field 'tests' must be a list in {test_file_path}, "
            f"got {type(test_list).__name__}"
        )

    if not test_list:
        raise ValueError(f"Field 'tests' cannot be an empty list in {test_file_path}")

    release = tests.get("release", {}) if include_release else None

    # Create and return TestFile object
    try:
        return TestFile(
            suite=suite,
            tests=[x.get("it").strip() for x in test_list],
            file_path=test_file_path,
            release=release,
        )
    except Exception as e:
        raise ValueError(f"Failed to create TestFile object from {test_file_path}: {e}")
