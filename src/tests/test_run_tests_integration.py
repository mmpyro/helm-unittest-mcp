"""
Integration tests for run_tests.py module.

These tests execute actual 'helm unittest' commands using the example chart
to verify the full execution flow from command generation to result parsing.
"""

import pytest
import os
import shutil
import tempfile
from pathlib import Path
from tools.run_tests import run_unittest, update_snapshot
from utils.dtos import TestResultSummary


# Mark all tests in this module with the integration tag
pytestmark = pytest.mark.integration


@pytest.fixture
def chart_path():
    """Fixture providing the path to the example Helm chart."""
    project_root = Path(__file__).parent.parent.parent
    path = project_root / "example"

    if not path.exists() or not (path / "Chart.yaml").exists():
        pytest.skip(f"Example chart not found at {path}")

    return str(path)


@pytest.fixture
def temp_chart(chart_path):
    """Fixture providing a temporary copy of the example chart to allow modifications."""
    temp_dir = tempfile.mkdtemp()
    target_path = os.path.join(temp_dir, "example")
    shutil.copytree(chart_path, target_path)
    yield target_path
    shutil.rmtree(temp_dir)


class TestRunTestsIntegration:
    """Integration tests for run_unittest and update_snapshot tools."""

    def test_run_unittest_all_tests(self, chart_path):
        """Test running all tests in the example chart."""
        # Using default pattern "tests/*/*.yaml" which matches example/tests structure
        result = run_unittest(
            test_suite_files="tests/*/*.yaml",
            chart_path=chart_path,
            output_type="xunit"
        )

        assert isinstance(result, TestResultSummary)
        assert result.total == 6
        assert result.passed == 6
        assert result.failed == 0
        assert len(result.test_cases) == 6

        # Verify some test names are present
        test_names = [tc.name for tc in result.test_cases]
        assert "should render release-name-example deployment object" in test_names
        assert "should render release-name-example service object" in test_names

    def test_run_unittest_specific_suite(self, chart_path):
        """Test running only a specific test suite."""
        result = run_unittest(
            test_suite_files="tests/ingress/*.yaml",
            chart_path=chart_path,
            output_type="junit"
        )

        assert result.total == 1
        assert result.passed == 1
        assert result.test_cases[0].name == "should render release-name-example ingress object"

    def test_run_unittest_with_values(self, chart_path):
        """Test running tests with an additional values file."""
        # Note: In real scenarios, we'd have a specific test that depends on values.
        # For this integration test, we just verify that passing -v doesn't break anything.
        result = run_unittest(
            test_suite_files="tests/service/*.yaml",
            chart_path=chart_path,
            values_path=["values.yaml"]  # Using the chart's own values.yaml as an extra values file
        )

        assert result.total == 1
        assert result.passed == 1

    def test_run_unittest_different_formats(self, chart_path):
        """Test that different output formats (JUnit, NUnit) are correctly parsed."""
        for fmt in ["junit", "nunit", "xunit"]:
            result = run_unittest(
                test_suite_files="tests/deployment/*.yaml",
                chart_path=chart_path,
                output_type=fmt
            )
            assert result.passed >= 1
            assert len(result.test_cases) >= 1

    def test_update_snapshot_functionality(self, temp_chart):
        """Test update_snapshot tool (using a temporary copy of the chart)."""
        # First, ensure no snapshots exist
        snapshot_dir = Path(temp_chart) / "tests" / "deployment" / "__snapshot__"
        if snapshot_dir.exists():
            shutil.rmtree(snapshot_dir)

        # Run update snapshot
        result = update_snapshot(
            test_suite_files="tests/deployment/*.yaml",
            chart_path=temp_chart
        )

        # TestResultSummary doesn't have success attr normally, but its presence means it ran
        assert result.total >= 1

    def test_run_unittest_nonexistent_chart(self):
        """Test running tests on a nonexistent chart path."""
        # helm unittest creates an empty valid report even when chart is missing
        result = run_unittest(
            test_suite_files="tests/*.yaml",
            chart_path="/nonexistent/path"
        )

        assert isinstance(result, TestResultSummary)
        assert result.total == 0
        assert len(result.test_cases) == 0

    def test_run_unittest_invalid_test_files(self, chart_path):
        """Test running with a glob that matches no files."""
        # helm unittest will fail if it finds no test files
        result = run_unittest(
            test_suite_files="nonexistent/*.yaml",
            chart_path=chart_path
        )

        # It should return a summary with 0 tests
        assert result.total == 0
        assert len(result.test_cases) == 0
