"""Tests for required CI job rollup validation."""

from __future__ import annotations

from scripts.ci.verify_required_jobs import (
    find_failed_jobs,
    parse_allowed_skips,
)


def test_find_failed_jobs_allows_success() -> None:
    """Successful jobs should not fail required rollups."""
    assert find_failed_jobs({"passed": {"result": "success"}}) == []


def test_find_failed_jobs_reports_skipped_by_default() -> None:
    """Skipped jobs should fail unless they are explicitly allowed."""
    assert find_failed_jobs(
        {
            "passed": {"result": "success"},
            "optional": {"result": "skipped"},
        }
    ) == ["optional: skipped"]


def test_find_failed_jobs_allows_named_skipped_jobs() -> None:
    """Named skipped jobs should not fail required rollups."""
    assert find_failed_jobs(
        {
            "passed": {"result": "success"},
            "optional": {"result": "skipped"},
            "other-skipped": {"result": "skipped"},
        },
        allowed_skipped_jobs={"optional"},
    ) == ["other-skipped: skipped"]


def test_parse_allowed_skips_accepts_repeated_or_comma_separated_values() -> (
    None
):
    """The CLI accepts repeated flags and comma-separated job names."""
    assert parse_allowed_skips(["first, second", "third"]) == {
        "first",
        "second",
        "third",
    }


def test_find_failed_jobs_reports_unexpected_results() -> None:
    """Failures and cancellations should fail required rollups."""
    assert find_failed_jobs(
        {
            "passed": {"result": "success"},
            "failed": {"result": "failure"},
            "cancelled": {"result": "cancelled"},
        }
    ) == ["failed: failure", "cancelled: cancelled"]
