from dataclasses import dataclass
from typing import Any


@dataclass
class TestFile:
    __test__ = False
    suite: str
    tests: list[str]
    release: dict[str, Any]
    file_path: str


@dataclass
class ValidationResult:
    """Result of schema validation operation.
    
    Attributes:
        success (bool): True if validation passed, False otherwise
        message (str): Human-readable message describing the result
        errors (list[str] | None): List of validation error messages if validation failed, None otherwise
    """
    success: bool
    message: str
    errors: list[str] | None = None


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
        time (float): Total execution time in seconds
        test_cases (list[TestCaseResult]): List of individual test case results
    """
    total: int
    passed: int
    failed: int
    skipped: int
    errors: int
    time: float
    test_cases: list[TestCaseResult]
