from typing import Literal
import xml.etree.ElementTree as ET
from pathlib import Path
from utils.dtos import TestResultSummary, TestCaseResult


TestFormat = Literal["junit", "xunit", "nunit"]


class TestResultParser(object):
    __test__ = False

    def __init__(self, report_type: TestFormat):
        self.report_type = report_type

    def parse(self, test_result: str) -> TestResultSummary:
        """Parse test results from a file or XML string.

        Args:
            test_result (str): Path to test result file or XML string

        Returns:
            TestResultSummary: Parsed test results
        """
        if self.report_type == "junit":
            return self._parse_junit(test_result)
        elif self.report_type == "xunit":
            return self._parse_xunit(test_result)
        elif self.report_type == "nunit":
            return self._parse_nunit(test_result)
        else:
            raise ValueError(f"Unsupported report type: {self.report_type}")

    def _get_root(self, test_result: str) -> ET.Element:
        """Get the root element from a file path or XML string.

        Args:
            test_result (str): Path to XML file or XML string

        Returns:
            ET.Element: Root element of the XML

        Raises:
            FileNotFoundError: If the test result file doesn't exist and it's not an XML string
            ET.ParseError: If the XML is malformed
        """
        # Try to treat it as a file path first, but only if it's not too long
        # and doesn't look like XML (starts with '<')
        is_file = False
        stripped_result = test_result.strip()

        if not stripped_result.startswith('<'):
            try:
                # Path names have a limit, avoids OSError: [Errno 63] File name too long
                if len(test_result) < 4096:
                    path = Path(test_result)
                    if path.exists() and path.is_file():
                        is_file = True
            except OSError:
                pass

        if is_file:
            tree = ET.parse(test_result)
            return tree.getroot()

        # If it looks like XML, try to parse it from string
        if stripped_result.startswith('<'):
            return ET.fromstring(test_result)

        # If it's not a file and doesn't explicitly look like XML,
        # we need to decide if it's a missing file or an invalid XML string.
        # If it's a single line and looks like a path, assume FileNotFoundError.
        is_likely_path = (
            '\n' not in test_result and
            ('/' in test_result or '\\' in test_result or test_result.lower().endswith('.xml'))
        )
        if is_likely_path:
            raise FileNotFoundError(f"File not found: {test_result}")

        # Otherwise, try to parse it as an XML string (which may raise ET.ParseError)
        return ET.fromstring(test_result)

    def _parse_nunit(self, test_result: str) -> TestResultSummary:
        """Parse NUnit format test results.

        Args:
            test_result (str): Path to NUnit XML file or XML string

        Returns:
            TestResultSummary: Parsed test results with summary and individual test cases

        Raises:
            FileNotFoundError: If the test result file doesn't exist
            ET.ParseError: If the XML is malformed
        """
        root = self._get_root(test_result)

        # Initialize counters
        total_tests = 0
        total_passed = 0
        total_failed = 0
        total_skipped = 0
        total_errors = 0
        total_time = 0.0
        test_cases = []

        # NUnit 2.x style
        if root.tag == 'test-results':
            total_tests = int(root.get('total', 0))
            total_errors = int(root.get('errors', 0))
            total_failed = int(root.get('failures', 0))
            total_skipped = int(root.get('skipped', 0)) + int(root.get('ignored', 0)) + int(root.get('not-run', 0))

            # Handle time - it might be a duration or a timestamp
            time_val = root.get('time', '0')
            try:
                total_time = float(time_val)
            except ValueError:
                # If time is a timestamp (like "20:10:11"), we'll set it to 0 and calculate from suites later if needed
                total_time = 0.0

            total_passed = total_tests - total_failed - total_errors - total_skipped

            # Find all test cases recursively
            suites_sum_time = 0.0
            for suite in root.findall('.//test-suite'):
                suite_name = suite.get('name', 'Unknown')

                # Update total time from top-level suites if root time was invalid
                suite_time_attr = suite.get('time')
                if suite_time_attr:
                    try:
                        suites_sum_time += float(suite_time_attr)
                    except ValueError:
                        pass

                # Check for test-cases inside this suite's results
                results = suite.find('results')
                if results is not None:
                    for tc in results.findall('test-case'):
                        tc_name = tc.get('name', 'Unknown')
                        tc_time = float(tc.get('time', 0.0))
                        tc_result = tc.get('result', 'Unknown')

                        # Normalize result string
                        normalized_result = tc_result.lower()
                        if "success" in normalized_result or "pass" in normalized_result:
                            normalized_result = "passed"
                        elif "fail" in normalized_result:
                            normalized_result = "failed"
                        elif "error" in normalized_result:
                            normalized_result = "error"
                        elif "skip" in normalized_result or "ignore" in normalized_result:
                            normalized_result = "skipped"

                        tc_message = None
                        failure = tc.find('failure')
                        if failure is not None:
                            message_elem = failure.find('message')
                            if message_elem is not None and message_elem.text:
                                tc_message = message_elem.text.strip()
                            else:
                                tc_message = failure.text.strip() if failure.text else None

                        test_cases.append(
                            TestCaseResult(
                                name=tc_name,
                                suite=suite_name,
                                result=normalized_result,
                                time=tc_time,
                                message=tc_message
                            )
                        )

            if total_time == 0.0:
                # Note: NUnit 2.x often has multiple top-level suites or nested ones.
                # Here we just use the sum if the root was clearly a timestamp.
                # However, helm-unittest output seems to have suites for each file.
                # We'll just use the sum of all suite durations as a fallback.
                total_time = suites_sum_time

        return TestResultSummary(
            total=total_tests,
            passed=total_passed,
            failed=total_failed,
            skipped=total_skipped,
            errors=total_errors,
            time=total_time,
            test_cases=test_cases
        )

    def _parse_junit(self, test_result: str) -> TestResultSummary:
        """Parse JUnit format test results.

        Args:
            test_result (str): Path to JUnit XML file or XML string

        Returns:
            TestResultSummary: Parsed test results with summary and individual test cases

        Raises:
            FileNotFoundError: If the test result file doesn't exist
            ET.ParseError: If the XML is malformed
        """
        root = self._get_root(test_result)

        # Initialize counters
        total_tests = 0
        total_passed = 0
        total_failed = 0
        total_skipped = 0
        total_errors = 0
        total_time = 0.0
        test_cases = []

        # JUnit can have <testsuites> as root or <testsuite>
        suites = []
        if root.tag == 'testsuites':
            suites = root.findall('testsuite')
            # Try to get total time from root if available
            root_time = root.get('time')
            if root_time:
                total_time = float(root_time)
        elif root.tag == 'testsuite':
            suites = [root]
        else:
            # Fallback for some non-standard roots that might contain testsuites
            suites = root.findall('.//testsuite')

        for suite in suites:
            suite_name = suite.get('name', 'Unknown')

            # If we don't have total time from root, sum it up from suites
            if root.tag != 'testsuites' or not root.get('time'):
                suite_time = suite.get('time')
                if suite_time:
                    total_time += float(suite_time)

            for tc in suite.findall('.//testcase'):
                tc_name = tc.get('name', 'Unknown')
                tc_time = float(tc.get('time', 0.0))
                tc_result = "passed"
                tc_message = None

                # Check for failure/error/skipped
                failure = tc.find('failure')
                error = tc.find('error')
                skipped = tc.find('skipped')

                if failure is not None:
                    tc_result = "failed"
                    tc_message = failure.get('message') or failure.text
                    total_failed += 1
                elif error is not None:
                    tc_result = "error"
                    tc_message = error.get('message') or error.text
                    total_errors += 1
                elif skipped is not None:
                    tc_result = "skipped"
                    tc_message = skipped.get('message') or skipped.text
                    total_skipped += 1
                else:
                    total_passed += 1

                total_tests += 1

                test_cases.append(
                    TestCaseResult(
                        name=tc_name,
                        suite=suite_name,
                        result=tc_result,
                        time=tc_time,
                        message=tc_message.strip() if tc_message else None
                    )
                )

        return TestResultSummary(
            total=total_tests,
            passed=total_passed,
            failed=total_failed,
            skipped=total_skipped,
            errors=total_errors,
            time=total_time,
            test_cases=test_cases
        )

    def _parse_xunit(self, test_result: str) -> TestResultSummary:
        """Parse xunit format test results.

        Args:
            test_result (str): Path to xunit XML file or XML string

        Returns:
            TestResultSummary: Parsed test results with summary and individual test cases

        Raises:
            FileNotFoundError: If the test result file doesn't exist
            ET.ParseError: If the XML is malformed
        """
        root = self._get_root(test_result)

        # Initialize counters
        total_tests = 0
        total_passed = 0
        total_failed = 0
        total_skipped = 0
        total_errors = 0
        total_time = 0.0
        test_cases = []

        # Parse all assemblies (test suites)
        for assembly in root.findall('.//assembly'):
            # Get assembly-level statistics
            total_tests += int(assembly.get('total', 0))
            total_passed += int(assembly.get('passed', 0))
            total_failed += int(assembly.get('failed', 0))
            total_skipped += int(assembly.get('skipped', 0))
            total_errors += int(assembly.get('errors', 0))
            total_time += float(assembly.get('time', 0.0))

            # Parse collections (test groups within assembly)
            for collection in assembly.findall('.//collection'):
                collection_name = collection.get('name', 'Unknown Collection')

                # Parse individual test cases
                for test in collection.findall('.//test'):
                    test_name = test.get('name', 'Unknown Test')
                    test_result_status = test.get('result', 'Unknown')
                    test_time = float(test.get('time', 0.0))

                    # Normalize result status to lowercase
                    normalized_result = test_result_status.lower()
                    if normalized_result == "pass":
                        normalized_result = "passed"
                    elif normalized_result == "fail":
                        normalized_result = "failed"
                    elif normalized_result == "skip":
                        normalized_result = "skipped"

                    # Check for failure message
                    failure_message = None
                    failure_elem = test.find('.//failure')
                    if failure_elem is not None:
                        message_elem = failure_elem.find('message')
                        if message_elem is not None and message_elem.text:
                            failure_message = message_elem.text.strip()

                    test_cases.append(
                        TestCaseResult(
                            name=test_name,
                            suite=collection_name,
                            result=normalized_result,
                            time=test_time,
                            message=failure_message
                        )
                    )

        return TestResultSummary(
            total=total_tests,
            passed=total_passed,
            failed=total_failed,
            skipped=total_skipped,
            errors=total_errors,
            time=total_time,
            test_cases=test_cases
        )
