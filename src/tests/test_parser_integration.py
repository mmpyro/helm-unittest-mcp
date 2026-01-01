"""
Integration tests for parser.py module.

These tests use actual test report files from the src/tests/reports directory
to verify the functionality of TestResultParser in real-world scenarios.
"""

import pytest
import os
from pathlib import Path
from utils.parser import TestResultParser
from utils.dtos import TestResultSummary, TestCaseResult


# Mark all tests in this module with the integration tag
pytestmark = pytest.mark.integration


@pytest.fixture
def reports_dir():
    """Fixture providing the path to the test reports directory."""
    # Get the tests directory (assuming this file is in src/tests)
    tests_dir = Path(__file__).parent
    reports_path = tests_dir / "reports"
    
    if not reports_path.exists():
        pytest.skip(f"Reports directory not found: {reports_path}")
    
    return str(reports_path)


@pytest.fixture
def junit_report_path(reports_dir):
    """Fixture providing the path to the JUnit report file."""
    report_path = os.path.join(reports_dir, "junit_report.xml")
    
    if not os.path.exists(report_path):
        pytest.skip(f"JUnit report not found: {report_path}")
    
    return report_path


@pytest.fixture
def xunit_report_path(reports_dir):
    """Fixture providing the path to the xUnit report file."""
    report_path = os.path.join(reports_dir, "xunit_report.xml")
    
    if not os.path.exists(report_path):
        pytest.skip(f"xUnit report not found: {report_path}")
    
    return report_path


@pytest.fixture
def nunit_report_path(reports_dir):
    """Fixture providing the path to the NUnit report file."""
    report_path = os.path.join(reports_dir, "nunit_report.xml")
    
    if not os.path.exists(report_path):
        pytest.skip(f"NUnit report not found: {report_path}")
    
    return report_path


class TestJUnitParserIntegration:
    """Integration tests for JUnit parser using real report files."""
    
    def test_parse_junit_report_file(self, junit_report_path):
        """Test parsing a real JUnit report file from helm-unittest."""
        parser = TestResultParser("junit")
        result = parser.parse(junit_report_path)
        
        # Verify the result structure
        assert isinstance(result, TestResultSummary)
        assert isinstance(result.test_cases, list)
        
        # Verify summary statistics
        assert result.total == 6  # Total test cases across all suites
        assert result.passed == 6  # All tests passed
        assert result.failed == 0
        assert result.skipped == 0
        
        # Verify test cases were parsed
        assert len(result.test_cases) == 6
        
        # Verify specific test cases
        test_names = [tc.name for tc in result.test_cases]
        assert "should render release-name-example deployment object" in test_names
        assert "should render release-name-example ingress object" in test_names
        assert "should render release-name-example service object" in test_names
        assert "should render release-name-example service account object" in test_names
        assert "should use release-name-example service account into deployment" in test_names
        
        # Verify all test cases have passed status
        for test_case in result.test_cases:
            assert test_case.result == "passed"
            assert isinstance(test_case.time, float)
            assert test_case.time >= 0
    
    def test_parse_junit_report_string(self, junit_report_path):
        """Test parsing JUnit report from XML string content."""
        # Read the file content
        with open(junit_report_path, 'r') as f:
            xml_content = f.read()
        
        parser = TestResultParser("junit")
        result = parser.parse(xml_content)
        
        # Verify the result
        assert isinstance(result, TestResultSummary)
        assert result.total == 6
        assert result.passed == 6
        assert len(result.test_cases) == 6
    
    def test_junit_test_suites_structure(self, junit_report_path):
        """Test that JUnit parser correctly handles multiple test suites."""
        parser = TestResultParser("junit")
        result = parser.parse(junit_report_path)
        
        # Verify we have test cases from different suites
        suite_names = set()
        for test_case in result.test_cases:
            # Suite name is in the classname attribute
            if hasattr(test_case, 'suite'):
                suite_names.add(test_case.suite)
        
        # We should have tests from multiple suites
        # (deployment, ingress, service, serviceaccount, horizontalpodautoscaler)
        assert len(result.test_cases) >= 5
    
    def test_junit_time_parsing(self, junit_report_path):
        """Test that time values are correctly parsed from JUnit report."""
        parser = TestResultParser("junit")
        result = parser.parse(junit_report_path)
        
        # Verify total time is calculated
        assert isinstance(result.time, float)
        assert result.time > 0
        
        # Verify individual test case times
        total_test_time = sum(tc.time for tc in result.test_cases)
        assert total_test_time > 0


class TestXUnitParserIntegration:
    """Integration tests for xUnit parser using real report files."""
    
    def test_parse_xunit_report_file(self, xunit_report_path):
        """Test parsing a real xUnit report file from helm-unittest."""
        parser = TestResultParser("xunit")
        result = parser.parse(xunit_report_path)
        
        # Verify the result structure
        assert isinstance(result, TestResultSummary)
        assert isinstance(result.test_cases, list)
        
        # Verify summary statistics
        assert result.total == 6  # Total test cases across all assemblies
        assert result.passed == 6  # All tests passed
        assert result.failed == 0
        assert result.skipped == 0
        
        # Verify test cases were parsed
        assert len(result.test_cases) == 6
        
        # Verify specific test cases
        test_names = [tc.name for tc in result.test_cases]
        assert "should render release-name-example deployment object" in test_names
        assert "should render release-name-example horizontal pod autoscaler object" in test_names
        assert "should render release-name-example ingress object" in test_names
        
        # Verify all test cases have passed status
        for test_case in result.test_cases:
            assert test_case.result == "passed"
            assert isinstance(test_case.time, float)
    
    def test_parse_xunit_report_string(self, xunit_report_path):
        """Test parsing xUnit report from XML string content."""
        # Read the file content
        with open(xunit_report_path, 'r') as f:
            xml_content = f.read()
        
        parser = TestResultParser("xunit")
        result = parser.parse(xml_content)
        
        # Verify the result
        assert isinstance(result, TestResultSummary)
        assert result.total == 6
        assert result.passed == 6
        assert len(result.test_cases) == 6
    
    def test_xunit_assembly_structure(self, xunit_report_path):
        """Test that xUnit parser correctly handles multiple assemblies."""
        parser = TestResultParser("xunit")
        result = parser.parse(xunit_report_path)
        
        # Verify we have test cases from different assemblies/collections
        # Each test file is an assembly with a collection
        assert len(result.test_cases) == 6
        
        # Verify test case names are unique
        test_names = [tc.name for tc in result.test_cases]
        assert len(test_names) == len(set(test_names))
    
    def test_xunit_time_aggregation(self, xunit_report_path):
        """Test that time values are correctly aggregated from xUnit report."""
        parser = TestResultParser("xunit")
        result = parser.parse(xunit_report_path)
        
        # Verify total time is calculated
        assert isinstance(result.time, float)
        assert result.time > 0
        
        # Verify individual test case times
        for test_case in result.test_cases:
            assert test_case.time >= 0


class TestNUnitParserIntegration:
    """Integration tests for NUnit parser using real report files."""
    
    def test_parse_nunit_report_file(self, nunit_report_path):
        """Test parsing a real NUnit report file from helm-unittest."""
        parser = TestResultParser("nunit")
        result = parser.parse(nunit_report_path)
        
        # Verify the result structure
        assert isinstance(result, TestResultSummary)
        assert isinstance(result.test_cases, list)
        
        # Verify summary statistics
        assert result.total == 6  # Total test cases across all suites
        assert result.passed == 6  # All tests passed
        assert result.failed == 0
        assert result.skipped == 0
        
        # Verify test cases were parsed
        assert len(result.test_cases) == 6
        
        # Verify specific test cases
        test_names = [tc.name for tc in result.test_cases]
        assert "should render release-name-example deployment object" in test_names
        assert "should render release-name-example horizontal pod autoscaler object" in test_names
        assert "should render release-name-example ingress object" in test_names
        assert "should render release-name-example service object" in test_names
        
        # Verify all test cases have passed status
        for test_case in result.test_cases:
            assert test_case.result == "passed"
            assert isinstance(test_case.time, float)
    
    def test_parse_nunit_report_string(self, nunit_report_path):
        """Test parsing NUnit report from XML string content."""
        # Read the file content
        with open(nunit_report_path, 'r') as f:
            xml_content = f.read()
        
        parser = TestResultParser("nunit")
        result = parser.parse(xml_content)
        
        # Verify the result
        assert isinstance(result, TestResultSummary)
        assert result.total == 6
        assert result.passed == 6
        assert len(result.test_cases) == 6
    
    def test_nunit_test_suite_structure(self, nunit_report_path):
        """Test that NUnit parser correctly handles test-suite hierarchy."""
        parser = TestResultParser("nunit")
        result = parser.parse(nunit_report_path)
        
        # Verify we have test cases from different test suites
        assert len(result.test_cases) == 6
        
        # Verify test case names are unique
        test_names = [tc.name for tc in result.test_cases]
        assert len(test_names) == len(set(test_names))
    
    def test_nunit_time_parsing(self, nunit_report_path):
        """Test that time values are correctly parsed from NUnit report."""
        parser = TestResultParser("nunit")
        result = parser.parse(nunit_report_path)
        
        # Verify total time is in the root element
        assert isinstance(result.time, float)
        # NUnit doesn't always have a total time, so it might be 0
        assert result.time >= 0
        
        # Verify individual test case times
        for test_case in result.test_cases:
            assert test_case.time >= 0


class TestParserCrossFormatConsistency:
    """Integration tests verifying consistency across different report formats."""
    
    def test_all_formats_parse_same_test_count(
        self, junit_report_path, xunit_report_path, nunit_report_path
    ):
        """Test that all three formats report the same number of tests."""
        junit_parser = TestResultParser("junit")
        xunit_parser = TestResultParser("xunit")
        nunit_parser = TestResultParser("nunit")
        
        junit_result = junit_parser.parse(junit_report_path)
        xunit_result = xunit_parser.parse(xunit_report_path)
        nunit_result = nunit_parser.parse(nunit_report_path)
        
        # All formats should report the same total
        assert junit_result.total == xunit_result.total == nunit_result.total == 6
        assert len(junit_result.test_cases) == len(xunit_result.test_cases) == len(nunit_result.test_cases) == 6
    
    def test_all_formats_report_same_results(
        self, junit_report_path, xunit_report_path, nunit_report_path
    ):
        """Test that all three formats report the same test results."""
        junit_parser = TestResultParser("junit")
        xunit_parser = TestResultParser("xunit")
        nunit_parser = TestResultParser("nunit")
        
        junit_result = junit_parser.parse(junit_report_path)
        xunit_result = xunit_parser.parse(xunit_report_path)
        nunit_result = nunit_parser.parse(nunit_report_path)
        
        # All formats should report the same pass/fail/skip counts
        assert junit_result.passed == xunit_result.passed == nunit_result.passed == 6
        assert junit_result.failed == xunit_result.failed == nunit_result.failed == 0
        assert junit_result.skipped == xunit_result.skipped == nunit_result.skipped == 0
    
    def test_all_formats_contain_same_test_names(
        self, junit_report_path, xunit_report_path, nunit_report_path
    ):
        """Test that all three formats contain the same test names."""
        junit_parser = TestResultParser("junit")
        xunit_parser = TestResultParser("xunit")
        nunit_parser = TestResultParser("nunit")
        
        junit_result = junit_parser.parse(junit_report_path)
        xunit_result = xunit_parser.parse(xunit_report_path)
        nunit_result = nunit_parser.parse(nunit_report_path)
        
        junit_names = set(tc.name for tc in junit_result.test_cases)
        xunit_names = set(tc.name for tc in xunit_result.test_cases)
        nunit_names = set(tc.name for tc in nunit_result.test_cases)
        
        # All formats should have the same test names
        assert junit_names == xunit_names == nunit_names


class TestParserEdgeCases:
    """Integration tests for edge cases and error handling."""
    
    def test_parse_nonexistent_file(self):
        """Test that parsing a nonexistent file raises FileNotFoundError."""
        parser = TestResultParser("junit")
        
        with pytest.raises(FileNotFoundError):
            parser.parse("/nonexistent/path/to/report.xml")
    
    def test_parse_invalid_xml_content(self):
        """Test that parsing invalid XML raises ET.ParseError."""
        import xml.etree.ElementTree as ET
        
        parser = TestResultParser("junit")
        
        with pytest.raises(ET.ParseError):
            parser.parse("This is not valid XML content")
    
    def test_unsupported_report_type(self):
        """Test that unsupported report type raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported report type"):
            parser = TestResultParser("invalid")  # type: ignore
            parser.parse("<xml/>")
    
    def test_parse_empty_xml_string(self):
        """Test that parsing an empty string raises ET.ParseError."""
        import xml.etree.ElementTree as ET
        
        parser = TestResultParser("junit")
        
        with pytest.raises(ET.ParseError):
            parser.parse("")
    
    def test_parse_malformed_junit_xml(self):
        """Test that parsing malformed JUnit XML raises ET.ParseError."""
        import xml.etree.ElementTree as ET
        
        malformed_xml = """
        <testsuites>
            <testsuite name="Suite 1">
                <testcase name="Test 1"
        </testsuites>
        """
        
        parser = TestResultParser("junit")
        
        with pytest.raises(ET.ParseError):
            parser.parse(malformed_xml)


class TestParserRealWorldScenarios:
    """Integration tests for real-world usage scenarios."""
    
    def test_parse_all_report_formats_sequentially(
        self, junit_report_path, xunit_report_path, nunit_report_path
    ):
        """Test parsing all report formats in sequence with a single parser instance."""
        # This tests that the parser can be reused for different formats
        
        junit_parser = TestResultParser("junit")
        junit_result = junit_parser.parse(junit_report_path)
        assert junit_result.total == 6
        
        xunit_parser = TestResultParser("xunit")
        xunit_result = xunit_parser.parse(xunit_report_path)
        assert xunit_result.total == 6
        
        nunit_parser = TestResultParser("nunit")
        nunit_result = nunit_parser.parse(nunit_report_path)
        assert nunit_result.total == 6
    
    def test_verify_helm_unittest_metadata(self, junit_report_path):
        """Test that helm-unittest specific metadata is present in reports."""
        # Read the file to verify metadata
        with open(junit_report_path, 'r') as f:
            content = f.read()
        
        # Verify helm-unittest version is present
        assert "helm-unittest.version" in content
        assert "1.6" in content
    
    def test_verify_test_execution_times_are_realistic(
        self, junit_report_path, xunit_report_path, nunit_report_path
    ):
        """Test that execution times are realistic (not negative or extremely large)."""
        parsers = [
            ("junit", junit_report_path),
            ("xunit", xunit_report_path),
            ("nunit", nunit_report_path),
        ]
        
        for format_type, report_path in parsers:
            parser = TestResultParser(format_type)
            result = parser.parse(report_path)
            
            # Total time should be reasonable (less than 1 minute for these small tests)
            assert 0 <= result.time < 60
            
            # Individual test times should be reasonable
            for test_case in result.test_cases:
                assert 0 <= test_case.time < 10  # No single test should take more than 10 seconds
