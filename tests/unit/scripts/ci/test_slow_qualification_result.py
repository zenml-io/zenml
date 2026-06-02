"""Tests for slow-CI qualification result derivation."""

from __future__ import annotations

from scripts.ci.slow_qualification_result import qualification_result


def test_qualification_result_success_when_all_dependencies_pass() -> None:
    """All successful dependencies publish a successful qualification."""
    conclusion, failed_jobs = qualification_result(
        {
            "resolve-ref": {"result": "success"},
            "ubuntu-unit-test": {"result": "success"},
        }
    )

    assert conclusion == "success"
    assert failed_jobs == []


def test_qualification_result_failure_when_dependency_fails() -> None:
    """Any non-success dependency publishes a failed qualification."""
    conclusion, failed_jobs = qualification_result(
        {
            "resolve-ref": {"result": "success"},
            "ubuntu-unit-test": {"result": "failure"},
        }
    )

    assert conclusion == "failure"
    assert failed_jobs == ["ubuntu-unit-test: failure"]


def test_qualification_result_failure_when_dependency_list_is_empty() -> None:
    """An empty needs context is not a successful qualification."""
    conclusion, failed_jobs = qualification_result({})

    assert conclusion == "failure"
    assert failed_jobs == ["<no required jobs found>: missing"]
