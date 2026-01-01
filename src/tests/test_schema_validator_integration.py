"""
Integration tests for schema_validator.py module.

These tests use actual test files from the example/tests directory
to verify the functionality of schema validation in real-world scenarios.
"""

import pytest
import os
from pathlib import Path
from tools.schema_validator import validate_schema, validate_tests
from utils.dtos import ValidationResult


# Mark all tests in this module with the integration tag
pytestmark = pytest.mark.integration


@pytest.fixture
def example_dir():
    """Fixture providing the path to the example tests directory."""
    # Get the project root directory
    tests_dir = Path(__file__).parent.parent.parent
    example_path = tests_dir / "example" / "tests"
    
    if not example_path.exists():
        pytest.skip(f"Example tests directory not found: {example_path}")
    
    return str(example_path)


@pytest.fixture
def deployment_test_path(example_dir):
    """Fixture providing the path to the deployment example test file."""
    test_path = os.path.join(example_dir, "deployment", "deployment_example_test.yaml")
    
    if not os.path.exists(test_path):
        pytest.skip(f"Deployment example test not found: {test_path}")
    
    return test_path


@pytest.fixture
def ingress_test_path(example_dir):
    """Fixture providing the path to the ingress example test file."""
    test_path = os.path.join(example_dir, "ingress", "ingress_example_test.yaml")
    
    if not os.path.exists(test_path):
        pytest.skip(f"Ingress example test not found: {test_path}")
    
    return test_path


class TestSchemaValidatorIntegration:
    """Integration tests for schema validator using real example files."""
    
    def test_validate_deployment_schema(self, deployment_test_path):
        """Test validating a real deployment test file against the schema."""
        result = validate_schema(deployment_test_path)
        
        # Verify the result
        assert isinstance(result, ValidationResult)
        assert result.success is True
        assert "Validation successful" in result.message
        assert result.errors is None
    
    def test_validate_ingress_schema(self, ingress_test_path):
        """Test validating a real ingress test file against the schema."""
        result = validate_schema(ingress_test_path)
        
        # Verify the result
        assert result.success is True
        assert result.errors is None
    
    def test_validate_all_examples(self, example_dir):
        """Test validating all example files one by one."""
        # Find all .yaml files in the example directory
        example_files = []
        for root, _, files in os.walk(example_dir):
            for file in files:
                if file.endswith(".yaml"):
                    example_files.append(os.path.join(root, file))
        
        assert len(example_files) == 5
        
        for file_path in example_files:
            result = validate_schema(file_path)
            assert result.success is True, f"Validation failed for {file_path}: {result.message}"
    
    def test_validate_tests_recursive(self, example_dir):
        """Test recursive validation of all example test files."""
        results = validate_tests(example_dir)
        
        # We expect 5 files to be validated (one in each subdirectory)
        assert len(results) == 5
        
        # All of them should be successful
        for result in results:
            assert isinstance(result, ValidationResult)
            assert result.success is True
            assert result.errors is None
            
    def test_validate_tests_with_pattern(self, example_dir):
        """Test recursive validation with a pattern."""
        # Only match deployment tests
        results = validate_tests(example_dir, pattern=r".*deployment.*\.yaml$")
        
        assert len(results) == 1
        assert results[0].success is True
        assert "deployment_example_test.yaml" in results[0].message


class TestSchemaValidatorEdgeCases:
    """Integration tests for edge cases and error handling."""
    
    def test_validate_nonexistent_file(self):
        """Test that validating a nonexistent file returns a failure result."""
        result = validate_schema("/nonexistent/path/to/test.yaml")
        
        assert result.success is False
        assert "Test file not found" in result.message
        assert result.errors is not None
        assert any("Test file not found" in err for err in result.errors)
    
    def test_validate_invalid_yaml(self, tmp_path):
        """Test that validating a file with invalid YAML returns a failure result."""
        invalid_yaml = tmp_path / "invalid.yaml"
        invalid_yaml.write_text("suite: [unclosed bracket")
        
        result = validate_schema(str(invalid_yaml))
        
        assert result.success is False
        assert "Invalid YAML syntax" in result.message
        assert result.errors is not None
        assert any("YAML parsing error" in err for err in result.errors)
    
    def test_validate_schema_mismatch(self, tmp_path):
        """Test that validating a file that doesn't match the schema returns a failure result."""
        # 'suite' is a required field in helm-unittest schema
        invalid_schema_yaml = tmp_path / "mismatch.yaml"
        invalid_schema_yaml.write_text("not_a_suite: true")
        
        result = validate_schema(str(invalid_schema_yaml))
        
        assert result.success is False
        assert "Schema validation failed" in result.message
        assert result.errors is not None
        # Should mention missing 'suite' or similar validation error
        assert any("Validation error" in err for err in result.errors)

    def test_validate_tests_invalid_path(self):
        """Test that validate_tests raises FileNotFoundError for nonexistent directory."""
        with pytest.raises(FileNotFoundError):
            validate_tests("/nonexistent/directory")
            
    def test_validate_tests_not_a_directory(self, deployment_test_path):
        """Test that validate_tests raises NotADirectoryError when path is a file."""
        with pytest.raises(NotADirectoryError):
            validate_tests(deployment_test_path)
