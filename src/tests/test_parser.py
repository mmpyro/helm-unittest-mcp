from typing import cast
import pytest
from unittest.mock import patch, MagicMock
import xml.etree.ElementTree as ET
from utils.parser import TestResultParser, TestFormat
from utils.dtos import TestResultSummary

# Sample XML contents
JUNIT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites time="1.5">
    <testsuite name="Suite 1" time="1.0">
        <testcase name="Test 1" time="0.6" />
        <testcase name="Test 2" time="0.4">
            <failure message="Assertion failed">Details</failure>
        </testcase>
    </testsuite>
    <testsuite name="Suite 2" time="0.5">
        <testcase name="Test 3" time="0.5">
            <skipped message="Ignored" />
        </testcase>
    </testsuite>
</testsuites>
"""

XUNIT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<assemblies>
    <assembly name="Asm 1" total="2" passed="1" failed="1" skipped="0" errors="0" time="1.2">
        <collection name="Coll 1">
            <test name="Test 1" result="Pass" time="0.7" />
            <test name="Test 2" result="Fail" time="0.5">
                <failure message="Error found" />
            </test>
        </collection>
    </assembly>
</assemblies>
"""

NUNIT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<test-results total="3" failures="1" errors="0" skipped="1" time="2.0">
    <test-suite name="Suite 1" time="1.0">
        <results>
            <test-case name="Test 1" result="Success" time="0.5" />
            <test-case name="Test 2" result="Failure" time="0.5">
                <failure>
                    <message>Fail Message</message>
                </failure>
            </test-case>
        </results>
    </test-suite>
    <test-suite name="Suite 2" time="1.0">
        <results>
            <test-case name="Test 3" result="Ignored" time="0.0" />
        </results>
    </test-suite>
</test-results>
"""


def test_parser_unsupported_type():
    with pytest.raises(ValueError, match="Unsupported report type"):
        parser = TestResultParser(cast(TestFormat, "invalid"))
        parser.parse("<xml/>")


def test_parse_junit_string():
    parser = TestResultParser("junit")
    result = parser.parse(JUNIT_XML)

    assert isinstance(result, TestResultSummary)
    assert result.total == 3
    assert result.passed == 1
    assert result.failed == 1
    assert result.skipped == 1
    assert result.time == 1.5
    assert len(result.test_cases) == 3

    assert result.test_cases[0].name == "Test 1"
    assert result.test_cases[0].result == "passed"
    assert result.test_cases[1].result == "failed"
    assert result.test_cases[1].message is not None
    assert "Assertion failed" in result.test_cases[1].message


@patch("pathlib.Path.exists")
@patch("pathlib.Path.is_file")
@patch("xml.etree.ElementTree.parse")
def test_parse_junit_file(mock_et_parse, mock_is_file, mock_exists):
    mock_exists.return_value = True
    mock_is_file.return_value = True

    # Setup mock tree and root
    mock_root = ET.fromstring(JUNIT_XML)
    mock_tree = MagicMock()
    mock_tree.getroot.return_value = mock_root
    mock_et_parse.return_value = mock_tree

    parser = TestResultParser("junit")
    result = parser.parse("fake_report.xml")

    assert result.total == 3
    mock_et_parse.assert_called_once_with("fake_report.xml")


def test_parse_xunit_string():
    parser = TestResultParser("xunit")
    result = parser.parse(XUNIT_XML)

    assert result.total == 2
    assert result.passed == 1
    assert result.failed == 1
    assert result.time == 1.2
    assert result.test_cases[1].result == "failed"


def test_parse_nunit_string():
    parser = TestResultParser("nunit")
    result = parser.parse(NUNIT_XML)

    assert result.total == 3
    assert result.passed == 1
    assert result.failed == 1
    assert result.skipped == 1
    assert result.time == 2.0
    assert result.test_cases[0].result == "passed"
    assert result.test_cases[1].result == "failed"
    assert result.test_cases[1].message == "Fail Message"


def test_parse_invalid_xml():
    parser = TestResultParser("junit")
    with pytest.raises(ET.ParseError):
        parser.parse("Not even XML")
