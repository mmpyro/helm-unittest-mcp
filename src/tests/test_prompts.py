from prompt.prompts import (
    helm_unittest_assistant,
    validate_helm_tests,
    run_helm_tests,
    update_helm_snapshots,
)


def test_helm_unittest_assistant_prompt():
    prompt_str = helm_unittest_assistant("/path/to/tests", pattern=".*test\\.yaml")
    assert "/path/to/tests" in prompt_str
    assert "pattern: '.*test\\.yaml'" in prompt_str
    assert "include_release=False" in prompt_str
    assert "suite_pattern=None" in prompt_str


def test_validate_helm_tests_prompt():
    prompt_str = validate_helm_tests("/path/to/tests")
    assert "/path/to/tests" in prompt_str
    assert "only_failures=False" in prompt_str
    assert "return_summary=False" in prompt_str


def test_run_helm_tests_prompt():
    prompt_str = run_helm_tests("/path/to/chart", test_directory="my_tests")
    assert "/path/to/chart" in prompt_str
    assert "my_tests" in prompt_str
    assert 'include_test_cases="failed_only"' in prompt_str
    assert "max_message_length=1000" in prompt_str


def test_update_helm_snapshots_prompt():
    prompt_str = update_helm_snapshots("/path/to/chart")
    assert "/path/to/chart" in prompt_str
    assert 'include_test_cases="failed_only"' in prompt_str
