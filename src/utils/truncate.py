"""Output-size caps shared by the tools.

Every tool result is copied verbatim into the client's context window, so the
tools that can emit arbitrarily large payloads (rendered manifests, snapshot
bodies, diffs, failure messages) cap them here rather than each inventing its
own rule.
"""

from typing import Optional

from utils.dtos import TestCaseResult, TestResultSummary


def truncate_text(text: Optional[str], max_chars: Optional[int]) -> Optional[str]:
    """Cut ``text`` to ``max_chars``, appending a note about what was dropped.

    A ``max_chars`` of ``None`` or a negative value disables truncation.
    """
    if text is None or max_chars is None or max_chars < 0 or len(text) <= max_chars:
        return text
    overflow = len(text) - max_chars
    return text[:max_chars] + f"\n... [truncated {overflow} chars]"


def filter_test_cases(
    test_cases: list[TestCaseResult],
    include_test_cases: str,
    max_message_length: Optional[int],
    max_test_cases: Optional[int] = None,
) -> list[TestCaseResult]:
    """Apply the include/truncate/cap rules to a list of test case results."""
    if include_test_cases == "none":
        return []

    kept: list[TestCaseResult] = []
    for case in test_cases:
        if include_test_cases == "failed_only" and case.result.lower() in ("pass", "passed"):
            continue
        case.message = truncate_text(case.message, max_message_length)
        kept.append(case)

    if max_test_cases is not None and max_test_cases >= 0 and len(kept) > max_test_cases:
        dropped = len(kept) - max_test_cases
        kept = kept[:max_test_cases]
        kept.append(
            TestCaseResult(
                name=f"... {dropped} more test cases omitted",
                suite="",
                result="Omitted",
                time=0.0,
                message="Raise max_test_cases to see them.",
            )
        )
    return kept


def cap_test_cases(
    summary: TestResultSummary, max_test_cases: Optional[int]
) -> TestResultSummary:
    """Cap an already-merged summary's ``test_cases`` list in place."""
    summary.test_cases = filter_test_cases(
        summary.test_cases,
        include_test_cases="all",
        max_message_length=None,
        max_test_cases=max_test_cases,
    )
    return summary
