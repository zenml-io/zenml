"""Verify readable reports preserve raw evidence and honest qualification states."""

import copy
import html
import json
from typing import Any

from sandbox_pipeline import report_sandbox_results


def evidence() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Build three distinct qualification phases with expected binary outcomes.

    Returns:
        Initial readiness, solved fixture, and untouched fixture evidence.
    """
    grade: dict[str, Any] = {
        "raw_reward": 1,
        "audited_valid": True,
        "test_counts": {"total": 3, "failure": 0, "error": 0, "skipped": 0},
        "verifier_output": "3 passed",
    }
    initial: dict[str, Any] = {
        "task": {"task_id": "task-one", "dataset_revision": "a" * 40},
        "grading": copy.deepcopy(grade),
        "cleanup_complete": True,
    }
    reference: dict[str, Any] = {
        "grading": copy.deepcopy(grade),
        "exit_reason": "done",
        "cleanup_complete": True,
    }
    noop = copy.deepcopy(reference)
    noop["grading"].update(raw_reward=0, audited_valid=False)
    noop["grading"]["test_counts"]["failure"] = 2
    noop["grading"]["verifier_output"] = "1 passed, 2 failed"
    return initial, reference, noop


def test_report_explains_expected_failure_and_keeps_full_evidence() -> None:
    """Show reference and no-op differences without converting fixtures to scores."""
    phases = evidence()
    original = copy.deepcopy(phases)
    results, report = report_sandbox_results.entrypoint(*phases)
    assert phases == original
    assert results == {
        "status": "passed",
        "scope": "CPU Kubernetes sandbox qualification; no model inference or training",
        **dict(zip(("initial", "reference", "noop"), phases)),
    }
    assert "Sandbox qualification passed" in report
    assert "Initial environment ready" in report
    assert "3 passed · 0 failed" in report
    assert "1 passed · 2 failed" in report
    assert "An untouched-task failure is the expected result" in report
    assert report.count('class="badge">As expected') == 2
    assert html.escape(json.dumps(results, indent=2), quote=True) in report
    assert "<details>" in report
    assert "No model inference or training" in report
    assert "<script" not in report
    assert "<link" not in report


def test_report_surfaces_runtime_failure_even_with_expected_reward() -> None:
    """A nominal pass cannot conceal broken cleanup or infrastructure."""
    initial, reference, noop = evidence()
    reference["cleanup_complete"] = False
    noop["grading"]["infrastructure_error"] = "Verifier unavailable"
    results, report = report_sandbox_results.entrypoint(
        initial, reference, noop
    )
    assert results["status"] == "failed"
    assert "Qualification needs attention" in report
    assert "Cleanup needs review" in report
    assert "Reference: unconfirmed" in report
    assert "Verifier unavailable" in report
    assert 'class="badge">As expected' not in report


def test_report_distinguishes_initial_failure_from_unrun_fixtures() -> None:
    """Missing qualification does not appear as an expected untouched-task fail."""
    initial, _, _ = evidence()
    initial["grading"] = None
    skipped = {
        "skipped": "initial qualification failed",
        "cleanup_complete": True,
    }
    results, report = report_sandbox_results.entrypoint(
        initial, skipped, skipped
    )
    assert results["status"] == "failed"
    assert "Initial environment not qualified" in report
    assert report.count('<div class="value">Not run</div>') == 2
    assert "Test counts unavailable" in report


def test_report_escapes_task_logs_and_error_content() -> None:
    """Untrusted task strings remain text in summaries and collapsed evidence."""
    initial, reference, noop = evidence()
    payload = '<script>alert("bad")</script><img src=x onerror=alert(1)>'
    initial["task"]["task_id"] = payload
    reference["grading"]["verifier_output"] = payload
    noop["error"] = payload
    _, report = report_sandbox_results.entrypoint(initial, reference, noop)
    assert payload not in report
    assert html.escape(payload, quote=True) in report
    assert "<script" not in report
    assert "<img" not in report
