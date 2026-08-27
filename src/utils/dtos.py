from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class TestFile:
    __test__ = False
    suite: str
    tests: list[str]
    file_path: str
    release: Optional[dict[str, Any]] = None


@dataclass
class ValidationResult:
    """Result of schema validation operation.

    Attributes:
        success (bool): True if validation passed, False otherwise
        message (str): Human-readable message describing the result
        errors (list[str] | None): List of validation error messages
                                   if validation passed, None otherwise
    """

    success: bool
    message: str
    errors: list[str] | None = None


@dataclass
class BatchValidationSummary:
    """Summary of batch schema validation operation.

    Attributes:
        total_files (int): Total number of files processed
        valid_files (int): Number of valid test files
        invalid_files (int): Number of invalid test files
        failures (list[ValidationResult]): Validation results for failed files only
    """

    total_files: int
    valid_files: int
    invalid_files: int
    failures: list[ValidationResult]


@dataclass
class TestCaseResult:
    __test__ = False
    """Individual test case result.

    Attributes:
        name (str): Name of the test case
        suite (str): Test suite/collection name
        result (str): Test result (Pass, Fail, Skip)
        time (float): Execution time in seconds
        message (str | None): Error message if test failed
    """
    name: str
    suite: str
    result: str
    time: float
    message: str | None = None


@dataclass
class TestResultSummary:
    __test__ = False
    """Summary of test execution results.

    Attributes:
        total (int): Total number of tests
        passed (int): Number of passed tests
        failed (int): Number of failed tests
        skipped (int): Number of skipped tests
        errors (int): Number of tests with errors
        time (float): Total execution time in seconds (sum of suite execution times)
        test_cases (list[TestCaseResult]): List of individual test case results
        elapsed_time (float | None): Actual wall-clock elapsed time in seconds
    """
    total: int
    passed: int
    failed: int
    skipped: int
    errors: int
    time: float
    test_cases: list[TestCaseResult]
    elapsed_time: Optional[float] = None


@dataclass
class SnapshotEntry:
    """Individual snapshot entry within a snapshot file."""

    name: str
    content: str


@dataclass
class SnapshotFile:
    """Represents a snapshot file (.snap) and its entries.

    Attributes:
        file_path (str): Absolute or relative path to the snapshot file
        test_file_path (str): Path to the corresponding test YAML file
        snapshots (list[SnapshotEntry]): List of parsed snapshot entries
        is_orphaned (bool): True if the associated test file no longer exists
    """

    file_path: str
    test_file_path: str
    snapshots: list[SnapshotEntry]
    is_orphaned: bool = False


@dataclass
class SnapshotDiffResult:
    """Result of snapshot diffing operation.

    Attributes:
        test_file (str): Path to the test file
        test_it (Optional[str]): Name of the test case if specific
        exists (bool): Whether the snapshot file exists
        has_diff (bool): Whether differences were found
        diff (Optional[str]): Unified diff output if differences exist
        message (str): Human-readable status message
    """

    test_file: str
    test_it: Optional[str]
    exists: bool
    has_diff: bool
    diff: Optional[str]
    message: str


@dataclass
class SnapshotCleanResult:
    """Summary of snapshot cleaning/pruning operation.

    Attributes:
        cleaned_files (list[str]): List of snapshot file paths deleted
        cleaned_entries (list[str]): List of snapshot entry keys removed
        dry_run (bool): Whether this was a dry run without actual file modification
        message (str): Summary description
    """

    cleaned_files: list[str]
    cleaned_entries: list[str]
    dry_run: bool
    message: str


@dataclass
class TemplateCoverage:
    """Coverage details for a single template file.

    Attributes:
        template_path (str): Path to the template file relative to chart root
        tested (bool): Whether the template is covered by at least one test suite
        test_files (list[str]): Test files targeting this template
        test_suites (list[str]): Test suite names targeting this template
    """

    template_path: str
    tested: bool
    test_files: list[str]
    test_suites: list[str]


@dataclass
class CoverageReport:
    """Overall test coverage report for a Helm chart.

    Attributes:
        chart_path (str): Path to the Helm chart
        total_templates (int): Total number of renderable template files
        tested_templates (int): Number of templates covered by tests
        untested_templates (int): Number of templates not covered by any tests
        coverage_percentage (float): Percentage of covered templates (0.0 to 100.0)
        template_details (list[TemplateCoverage]): Per-template coverage information
        untested_template_paths (list[str]): List of template paths lacking test coverage
    """

    chart_path: str
    total_templates: int
    tested_templates: int
    untested_templates: int
    coverage_percentage: float
    template_details: list[TemplateCoverage]
    untested_template_paths: list[str]
