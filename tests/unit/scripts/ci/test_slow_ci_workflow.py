"""Tests for slow-CI workflow guardrails."""

from __future__ import annotations

from pathlib import Path

import yaml


def _load_slow_workflow() -> dict:
    return yaml.load(
        Path(".github/workflows/ci-slow-develop.yml").read_text(),
        Loader=yaml.BaseLoader,
    )


def test_slow_ci_resolve_ref_does_not_interpolate_pr_context() -> None:
    """Reusable slow CI must work for schedule, manual, and workflow_call."""
    workflow_text = Path(".github/workflows/ci-slow-develop.yml").read_text()

    assert "github.event.pull_request.number" not in workflow_text
    assert "Get PR labels" not in workflow_text
    assert "Resolve qualification inputs" in workflow_text


def test_slow_ci_has_single_develop_qualification_publisher() -> None:
    """The develop qualification publisher should have only one needs list."""
    jobs = _load_slow_workflow()["jobs"]

    assert "publish-qualification" in jobs
    assert "publish-qualification-success" not in jobs
    assert "publish-qualification-failure" not in jobs

    publisher = jobs["publish-qualification"]
    assert (
        publisher["if"]
        == "always() && needs.resolve-ref.outputs.qualification-target == 'develop'"
    )
    assert "resolve-ref" in publisher["needs"]

    run_blocks = "\n".join(step.get("run", "") for step in publisher["steps"])
    assert "scripts/ci/slow_qualification_result.py" in run_blocks
    assert '--conclusion "$QUALIFICATION_CONCLUSION"' in run_blocks


def test_slow_ci_write_permissions_are_publish_job_scoped() -> None:
    """Slow-CI test jobs should not all inherit GitHub write permissions."""
    workflow = _load_slow_workflow()
    publisher = workflow["jobs"]["publish-qualification"]

    assert workflow["permissions"] == {"contents": "read"}
    assert publisher["permissions"] == {
        "contents": "read",
        "checks": "write",
        "issues": "write",
    }
