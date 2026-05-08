"""Tests for required CI job rollup validation."""

from __future__ import annotations

from scripts.ci.verify_required_jobs import find_failed_jobs


def test_find_failed_jobs_allows_success_and_skipped() -> None:
    """Skipped optional jobs should not fail required rollups."""
    assert (
        find_failed_jobs(
            {
                "passed": {"result": "success"},
                "optional": {"result": "skipped"},
            }
        )
        == []
    )


def test_find_failed_jobs_reports_unexpected_results() -> None:
    """Failures and cancellations should fail required rollups."""
    assert find_failed_jobs(
        {
            "passed": {"result": "success"},
            "failed": {"result": "failure"},
            "cancelled": {"result": "cancelled"},
        }
    ) == ["failed: failure", "cancelled: cancelled"]
