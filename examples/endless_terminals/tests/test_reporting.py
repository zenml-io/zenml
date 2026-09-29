"""Behavior checks for deterministic evaluation reporting."""

from copy import deepcopy
from typing import Any

import pytest
from reporting import (
    render_evaluation_report,
    summarize_evaluation,
)


def evaluation() -> dict[str, Any]:
    """Return a small recorded evaluation for reporting checks.

    Returns:
        Example evaluation with one passing task.
    """
    return {
        "model": {"name": "small-model", "revision": "revision-1"},
        "mode": "model",
        "dataset_revision": "dataset-1",
        "protocol": {"max_actions": 16},
        "task_hashes": {"task-a": "hash-a"},
        "status": "completed",
        "cleanup": {"complete": True},
        "episodes": [
            {
                "task_id": "task-a",
                "exit_reason": "done",
                "turns": [
                    {
                        "action": {"type": "invalid"},
                        "usage": {"total_tokens": 10},
                    },
                    {
                        "action": {"type": "command"},
                        "usage": {"total_tokens": 20},
                    },
                    {"action": {"type": "done"}, "usage": {"total_tokens": 5}},
                ],
                "grading": {"raw_reward": 1, "audited_valid": True},
                "elapsed_seconds": 2.5,
                "cleanup_complete": True,
                "transcript": [],
            }
        ],
    }


def test_counts_and_format_validity() -> None:
    """Derive totals from recorded responses and audited outcomes."""
    result = summarize_evaluation(evaluation())
    assert result["passes"] == result["attempts"] == 1
    assert result["responses"] == 3
    assert result["format_errors"] == 1
    assert result["valid_response_percent"] == pytest.approx(200 / 3)
    assert result["total_tokens"] == 35
    assert result["elapsed_seconds"] == 2.5


def test_infrastructure_errors_are_not_task_failures() -> None:
    """Do not classify an unavailable verifier as an ordinary wrong answer."""
    data = evaluation()
    base = data["episodes"][0]
    failure = deepcopy(base)
    failure["grading"] = {"raw_reward": 0, "audited_valid": False}
    error = deepcopy(base)
    error["grading"] = {"raw_reward": 0, "infrastructure_error": "Docker lost"}
    incomplete = deepcopy(base)
    incomplete["grading"] = None
    data["episodes"] += [failure, error, incomplete]
    result = summarize_evaluation(data)
    assert result["attempts"] == 4
    assert result["passes"] == result["failures"] == 1
    assert result["infrastructure_errors"] == result["incomplete"] == 1


def test_escaped_untrusted_content() -> None:
    """Escape task labels, model names, transcript text, and verifier output."""
    data = evaluation()
    attack = '<script>alert("x")</script><img src=x onerror=alert(1)>'
    data["model"]["name"] = attack
    data["episodes"][0]["task_id"] = attack
    data["episodes"][0]["grading"]["verifier_output"] = attack
    data["episodes"][0]["transcript"] = [
        {"role": "assistant", "content": attack}
    ]
    report = render_evaluation_report(data)
    assert "<script>" not in report
    assert "<img" not in report
    assert "&lt;script&gt;" in report
    assert report == render_evaluation_report(data)


def test_zero_episodes_and_fixture_badge() -> None:
    """An empty fixture run has no score or response validity denominator."""
    data = evaluation()
    data["episodes"] = []
    data["mode"] = "fixture"
    result = summarize_evaluation(data)
    assert result["attempts"] == result["passes"] == 0
    assert result["valid_response_percent"] is None
    report = render_evaluation_report(data)
    assert "FIXTURE CHECK: NOT A MODEL SCORE" in report
    assert "N/A (no responses)" in report
    assert "No episodes recorded" in report


@pytest.mark.parametrize(
    "key", ["dataset_revision", "protocol", "task_hashes", "mode"]
)
def test_comparison_rejects_mismatched_identity(key: str) -> None:
    """Only identically configured evaluations may be paired.

    Args:
        key: Identity field changed in the baseline.
    """
    current = evaluation()
    baseline = deepcopy(current)
    baseline[key] = "different"
    with pytest.raises(ValueError, match=key):
        render_evaluation_report(current, baseline)


def test_comparison_rejects_different_tasks() -> None:
    """Equal attempt counts do not imply equal evaluation tasks."""
    current = evaluation()
    baseline = deepcopy(current)
    baseline["episodes"][0]["task_id"] = "task-b"
    with pytest.raises(ValueError, match="task sets"):
        render_evaluation_report(current, baseline)


def test_comparison_accepts_changed_model() -> None:
    """Model identity may differ when the evaluation contract matches."""
    current = evaluation()
    baseline = deepcopy(current)
    baseline["model"] = {
        "name": "earlier-model",
        "revision": "earlier-revision",
    }
    baseline["episodes"][0]["grading"] = {
        "raw_reward": 0,
        "audited_valid": False,
    }
    report = render_evaluation_report(current, baseline)
    assert "0/1 baseline; 1/1 current" in report
    assert "earlier-model" in report


def test_unverified_endpoint_cannot_be_compared() -> None:
    """A claimed endpoint revision is insufficient for checkpoint comparison."""
    current = evaluation()
    current["model"]["revision_verified"] = False
    with pytest.raises(ValueError, match="unverified"):
        render_evaluation_report(current, deepcopy(current))


def test_verifier_setup_error_is_infrastructure_failure() -> None:
    """Keep broken verifier setup separate from a failed task assertion."""
    current = evaluation()
    current["episodes"][0]["grading"] = {
        "raw_reward": 0,
        "audited_valid": False,
        "test_counts": {"error": 1},
    }
    summary = summarize_evaluation(current)
    assert summary["infrastructure_errors"] == 1
    assert summary["failures"] == 0


def test_comparison_pairs_repeated_attempts_by_index() -> None:
    """Pair outcomes by attempt identity even when episode order differs."""
    current = evaluation()
    current["episodes"][0]["attempt_index"] = 1
    second = deepcopy(current["episodes"][0])
    second["attempt_index"] = 2
    second["grading"] = {"raw_reward": 0, "audited_valid": False}
    current["episodes"].append(second)
    baseline = deepcopy(current)
    baseline["episodes"].reverse()
    report = render_evaluation_report(current, baseline)
    assert "1/2 baseline; 1/2 current" in report
    assert "task-a (attempt 1)</td><td>Passed</td><td>Passed</td>" in report
    assert "task-a (attempt 2)</td><td>Failed</td><td>Failed</td>" in report


@pytest.mark.parametrize("index", [1, 3])
def test_comparison_rejects_duplicate_or_mismatched_attempts(
    index: int,
) -> None:
    """Reject ambiguous duplicates and missing paired attempt identities.

    Args:
        index: Duplicate or mismatched attempt index.
    """
    current = evaluation()
    current["episodes"][0]["attempt_index"] = 1
    current["episodes"].append({**current["episodes"][0], "attempt_index": 2})
    baseline = deepcopy(current)
    baseline["episodes"][1]["attempt_index"] = index
    with pytest.raises(ValueError, match="task sets"):
        render_evaluation_report(current, baseline)
