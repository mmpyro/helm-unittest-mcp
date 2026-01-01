"""
Integration tests for get_tests.py module.

These tests use actual test files from the example/tests directory
to verify the functionality of get_tests and get_test_from_file functions
in a real-world scenario.
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
from tools.get_tests import get_tests, get_test_from_file
from utils.dtos import TestFile


# Mark all tests in this module with the integration tag
pytestmark = pytest.mark.integration


@pytest.fixture
def example_tests_dir():
    """Fixture providing the path to the example tests directory."""
    # Get the project root (assuming tests are in src/tests)
    project_root = Path(__file__).parent.parent.parent
    tests_dir = project_root / "example" / "tests"
    
    if not tests_dir.exists():
        pytest.skip(f"Example tests directory not found: {tests_dir}")
    
    return str(tests_dir)


@pytest.fixture
def ingress_tests_dir(example_tests_dir):
    """Fixture providing the path to the ingress tests directory."""
    ingress_dir = Path(example_tests_dir) / "ingress"
    
    if not ingress_dir.exists():
        pytest.skip(f"Ingress tests directory not found: {ingress_dir}")
    
    return str(ingress_dir)


@pytest.fixture
def temp_test_dir():
    """Fixture providing a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup after test
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestGetTestFromFileIntegration:
    """Integration tests for get_test_from_file function."""
    
    def test_parse_real_ingress_test_file(self, ingress_tests_dir):
        """Test parsing a real ingress test file from the example directory."""
        test_file_path = os.path.join(ingress_tests_dir, "ingress_example_test.yaml")
        
        # Verify file exists
        assert os.path.exists(test_file_path), f"Test file not found: {test_file_path}"
        
        # Parse the file
        result = get_test_from_file(test_file_path)
        
        # Verify the result
        assert isinstance(result, TestFile)
        assert result.suite == "example ingress tests"
        assert isinstance(result.tests, list)
        assert len(result.tests) > 0
        assert "should render release-name-example ingress object" in result.tests
        assert isinstance(result.release, dict)
        assert result.release.get("name") == "release-name"
        assert result.file_path == test_file_path
    
    def test_parse_all_example_test_files(self, example_tests_dir):
        """Test parsing all test files in the example directory."""
        test_files = []
        
        # Find all YAML files in the example tests directory
        for root, dirs, files in os.walk(example_tests_dir):
            for filename in files:
                if filename.endswith(".yaml") or filename.endswith(".yml"):
                    test_files.append(os.path.join(root, filename))
        
        # Should have at least one test file
        assert len(test_files) > 0, "No test files found in example directory"
        
        # Parse each file
        parsed_files = []
        for test_file in test_files:
            try:
                result = get_test_from_file(test_file)
                parsed_files.append(result)
                
                # Verify basic structure
                assert isinstance(result, TestFile)
                assert result.suite
                assert isinstance(result.tests, list)
                assert len(result.tests) > 0
                assert isinstance(result.release, dict)
                assert result.file_path == test_file
            except Exception as e:
                pytest.fail(f"Failed to parse {test_file}: {e}")
        
        # Verify we successfully parsed files
        assert len(parsed_files) > 0
    
    def test_parse_nonexistent_file(self):
        """Test that parsing a nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError) as exc_info:
            get_test_from_file("/nonexistent/path/to/test.yaml")
        
        assert "not found" in str(exc_info.value).lower()
    
    def test_parse_invalid_yaml_file(self, temp_test_dir):
        """Test that parsing an invalid YAML file raises yaml.YAMLError."""
        import yaml
        
        # Create an invalid YAML file
        invalid_file = os.path.join(temp_test_dir, "invalid.yaml")
        with open(invalid_file, "w") as f:
            f.write("suite: Test\n  invalid:\n- indentation\n")
        
        with pytest.raises(yaml.YAMLError):
            get_test_from_file(invalid_file)
    
    def test_parse_file_missing_required_fields(self, temp_test_dir):
        """Test that parsing a file missing required fields raises KeyError."""
        # Create a YAML file missing the 'tests' field
        incomplete_file = os.path.join(temp_test_dir, "incomplete.yaml")
        with open(incomplete_file, "w") as f:
            f.write("suite: Test Suite\nrelease:\n  name: my-release\n")
        
        with pytest.raises(KeyError) as exc_info:
            get_test_from_file(incomplete_file)
        
        assert "tests" in str(exc_info.value).lower()
    
    def test_parse_file_with_empty_suite(self, temp_test_dir):
        """Test that parsing a file with empty suite raises ValueError."""
        empty_suite_file = os.path.join(temp_test_dir, "empty_suite.yaml")
        with open(empty_suite_file, "w") as f:
            f.write("suite: ''\ntests:\n  - it: test case\n")
        
        with pytest.raises(ValueError) as exc_info:
            get_test_from_file(empty_suite_file)
        
        assert "suite" in str(exc_info.value).lower()
        assert "empty" in str(exc_info.value).lower()


class TestGetTestsIntegration:
    """Integration tests for get_tests function."""
    
    def test_get_tests_from_ingress_directory(self, ingress_tests_dir):
        """Test getting all tests from the ingress directory."""
        results = get_tests(ingress_tests_dir)
        
        # Verify we got results
        assert isinstance(results, list)
        assert len(results) > 0
        
        # Verify each result
        for result in results:
            assert isinstance(result, TestFile)
            assert result.suite
            assert isinstance(result.tests, list)
            assert len(result.tests) > 0
            assert isinstance(result.release, dict)
            assert result.file_path.startswith(ingress_tests_dir)
    
    def test_get_tests_from_all_example_directories(self, example_tests_dir):
        """Test getting all tests from the entire example tests directory."""
        results = get_tests(example_tests_dir)
        
        # Verify we got results from multiple subdirectories
        assert isinstance(results, list)
        assert len(results) >= 5  # We know there are at least 5 test files
        
        # Verify we have tests from different suites
        suites = {result.suite for result in results}
        assert len(suites) > 1, "Should have tests from multiple suites"
        
        # Verify all results are valid
        for result in results:
            assert isinstance(result, TestFile)
            assert result.suite
            assert len(result.tests) > 0
            assert result.file_path.startswith(example_tests_dir)
    
    def test_get_tests_with_pattern_matching(self, example_tests_dir):
        """Test getting tests with a specific pattern."""
        # Get only ingress test files
        results = get_tests(example_tests_dir, pattern=".*ingress.*")
        
        # Verify we got results
        assert isinstance(results, list)
        assert len(results) > 0
        
        # Verify all results are from ingress tests
        for result in results:
            assert "ingress" in result.file_path.lower()
    
    def test_get_tests_with_specific_filename_pattern(self, example_tests_dir):
        """Test getting tests with a specific filename pattern."""
        # Get only deployment test files
        results = get_tests(example_tests_dir, pattern="deployment.*\\.yaml$")
        
        # Verify we got results
        assert isinstance(results, list)
        
        # Verify all results match the pattern
        for result in results:
            filename = os.path.basename(result.file_path)
            assert filename.startswith("deployment")
            assert filename.endswith(".yaml")
    
    def test_get_tests_with_no_matching_pattern(self, example_tests_dir):
        """Test getting tests with a pattern that matches nothing."""
        results = get_tests(example_tests_dir, pattern="nonexistent_pattern_xyz")
        
        # Should return empty list
        assert isinstance(results, list)
        assert len(results) == 0
    
    def test_get_tests_default_pattern_matches_all_yaml(self, example_tests_dir):
        """Test that default pattern (empty string) matches all YAML files."""
        results_default = get_tests(example_tests_dir)
        results_none = get_tests(example_tests_dir, pattern=None)
        results_empty = get_tests(example_tests_dir, pattern="")
        
        # All should return the same results
        assert len(results_default) == len(results_none)
        assert len(results_default) == len(results_empty)
        assert len(results_default) > 0
    
    def test_get_tests_nonexistent_directory(self):
        """Test that getting tests from nonexistent directory raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            get_tests("/nonexistent/directory/path")
    
    def test_get_tests_file_instead_of_directory(self, ingress_tests_dir):
        """Test that passing a file path instead of directory raises NotADirectoryError."""
        # Get a file path
        test_file = os.path.join(ingress_tests_dir, "ingress_example_test.yaml")
        
        if not os.path.exists(test_file):
            pytest.skip(f"Test file not found: {test_file}")
        
        with pytest.raises(NotADirectoryError):
            get_tests(test_file)
    
    def test_get_tests_invalid_regex_pattern(self, example_tests_dir):
        """Test that invalid regex pattern raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_tests(example_tests_dir, pattern="[invalid(regex")
        
        assert "invalid regex pattern" in str(exc_info.value).lower()
    
    def test_get_tests_resilience_to_bad_files(self, temp_test_dir):
        """Test that get_tests continues processing even if some files are invalid."""
        # Create a mix of valid and invalid files
        valid_file1 = os.path.join(temp_test_dir, "valid1.yaml")
        with open(valid_file1, "w") as f:
            f.write("suite: Suite 1\ntests:\n  - it: test 1\n")
        
        invalid_file = os.path.join(temp_test_dir, "invalid.yaml")
        with open(invalid_file, "w") as f:
            f.write("suite: Invalid\n  bad:\n- indentation\n")
        
        valid_file2 = os.path.join(temp_test_dir, "valid2.yaml")
        with open(valid_file2, "w") as f:
            f.write("suite: Suite 2\ntests:\n  - it: test 2\n")
        
        # Should get results from valid files only
        results = get_tests(temp_test_dir)
        
        assert isinstance(results, list)
        assert len(results) == 2  # Only the two valid files
        
        suites = {result.suite for result in results}
        assert "Suite 1" in suites
        assert "Suite 2" in suites


class TestGetTestsEdgeCases:
    """Integration tests for edge cases and special scenarios."""
    
    def test_empty_directory(self, temp_test_dir):
        """Test getting tests from an empty directory."""
        results = get_tests(temp_test_dir)
        
        assert isinstance(results, list)
        assert len(results) == 0
    
    def test_directory_with_only_non_yaml_files(self, temp_test_dir):
        """Test getting tests from a directory with no YAML files."""
        # Create some non-YAML files
        with open(os.path.join(temp_test_dir, "readme.txt"), "w") as f:
            f.write("This is a readme")
        
        with open(os.path.join(temp_test_dir, "script.sh"), "w") as f:
            f.write("#!/bin/bash\necho 'hello'\n")
        
        results = get_tests(temp_test_dir)
        
        assert isinstance(results, list)
        assert len(results) == 0
    
    def test_nested_directory_structure(self, temp_test_dir):
        """Test getting tests from deeply nested directory structure."""
        # Create nested directories
        level1 = os.path.join(temp_test_dir, "level1")
        level2 = os.path.join(level1, "level2")
        level3 = os.path.join(level2, "level3")
        os.makedirs(level3)
        
        # Create test files at different levels
        for i, dir_path in enumerate([temp_test_dir, level1, level2, level3], 1):
            test_file = os.path.join(dir_path, f"test{i}.yaml")
            with open(test_file, "w") as f:
                f.write(f"suite: Suite {i}\ntests:\n  - it: test {i}\n")
        
        # Should find all files recursively
        results = get_tests(temp_test_dir)
        
        assert len(results) == 4
        suites = {result.suite for result in results}
        assert suites == {"Suite 1", "Suite 2", "Suite 3", "Suite 4"}
    
    def test_file_with_minimal_valid_structure(self, temp_test_dir):
        """Test parsing a file with minimal valid structure."""
        minimal_file = os.path.join(temp_test_dir, "minimal.yaml")
        with open(minimal_file, "w") as f:
            f.write("suite: Minimal Suite\ntests:\n  - it: single test\n")
        
        result = get_test_from_file(minimal_file)
        
        assert result.suite == "Minimal Suite"
        assert result.tests == ["single test"]
        assert result.release == {}  # Default empty dict
        assert result.file_path == minimal_file
    
    def test_file_with_complex_release_structure(self, temp_test_dir):
        """Test parsing a file with complex release configuration."""
        complex_file = os.path.join(temp_test_dir, "complex.yaml")
        with open(complex_file, "w") as f:
            f.write("""suite: Complex Suite
release:
  name: my-release
  namespace: my-namespace
  values:
    - values/prod.yaml
  set:
    image.tag: v1.2.3
    replicas: 3
tests:
  - it: complex test
""")
        
        result = get_test_from_file(complex_file)
        
        assert result.suite == "Complex Suite"
        assert result.tests == ["complex test"]
        assert isinstance(result.release, dict)
        assert result.release["name"] == "my-release"
        assert result.release["namespace"] == "my-namespace"
        assert "values" in result.release
        assert "set" in result.release
