# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Readable and confirmation-safe execution retention commands."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID

import pytest
from click import unstyle
from click.testing import CliRunner

from zenml.cli.pipeline import runs
from zenml.cli.project import project
from zenml.client import Client
from zenml.enums import RestoreOutcome, RetentionOutcome
from zenml.models.v2.misc.retention import (
    RestoreResponse,
    RetentionPassResponse,
    RetentionSettings,
    RetentionStatusResponse,
)


@pytest.fixture
def submit(monkeypatch: pytest.MonkeyPatch) -> Mock:
    """Replace archive submission with an accepted response."""
    accepted = Mock(
        return_value=RetentionPassResponse(outcome=RetentionOutcome.ACCEPTED)
    )
    monkeypatch.setattr(Client, "archive_project", accepted)
    return accepted


def output(result) -> str:
    """Return command output without styling or line wrapping."""
    return " ".join(unstyle(result.output).split())


def saved_policy(monkeypatch: pytest.MonkeyPatch, days) -> None:
    """Answer project reads with a policy that archives after `days`."""
    monkeypatch.setattr(
        Client,
        "get_project",
        Mock(
            return_value=SimpleNamespace(
                retention=RetentionSettings(archive_after_days=days)
            )
        ),
    )


def test_archive_confirms_then_submits(monkeypatch, submit) -> None:
    """The prompt names the saved policy; --yes submits and names status."""
    saved_policy(monkeypatch, 90)
    runner = CliRunner()

    canceled = runner.invoke(
        project, ["retention", "archive", "demo"], input="n\n"
    )
    assert canceled.exit_code == 0, canceled.output
    assert "finished more than 90 days ago" in output(canceled)
    assert "Execution retention canceled" in canceled.output
    submit.assert_not_called()

    accepted = runner.invoke(
        project, ["retention", "archive", "demo", "--yes"]
    )
    assert accepted.exit_code == 0, accepted.output
    assert "zenml project retention status demo" in output(accepted)
    submit.assert_called_once()


def test_archive_without_a_policy_submits_nothing(monkeypatch, submit) -> None:
    """A project with no saved policy is told how to set one."""
    saved_policy(monkeypatch, None)

    result = CliRunner().invoke(
        project, ["retention", "archive", "demo", "--yes"]
    )

    assert result.exit_code == 0, result.output
    assert "zenml project retention set --archive-after-days" in output(result)
    submit.assert_not_called()


def test_set_merges_the_saved_policy(monkeypatch) -> None:
    """Set keeps unspecified values, and --disable cannot carry values."""
    saved = RetentionSettings(archive_after_days=90, restored_grace_days=5)
    monkeypatch.setattr(
        Client,
        "get_project",
        Mock(return_value=SimpleNamespace(retention=saved)),
    )
    update_project = Mock()
    monkeypatch.setattr(Client, "update_project", update_project)
    runner = CliRunner()

    result = runner.invoke(
        project, ["retention", "set", "demo", "--max-runs", "50"]
    )

    assert result.exit_code == 0, result.output
    assert update_project.call_args.kwargs["retention"] == RetentionSettings(
        archive_after_days=90, restored_grace_days=5, max_runs_per_pass=50
    )
    invalid = runner.invoke(
        project,
        ["retention", "set", "--disable", "--archive-after-days", "90"],
    )
    assert invalid.exit_code == 2
    assert "cannot be combined" in invalid.output


def test_status_and_restore_print_plain_results(monkeypatch) -> None:
    """Status shows its counts; restore reports the restored run."""
    monkeypatch.setattr(
        Client,
        "get_retention_status",
        Mock(
            return_value=RetentionStatusResponse(
                outcome=RetentionOutcome.SUCCEEDED,
                finished_at=datetime(2026, 1, 2, 3, 4, 5),
                archived=4,
                oversized=1,
            )
        ),
    )
    status = CliRunner().invoke(project, ["retention", "status", "demo"])
    assert status.exit_code == 0, status.output
    assert "2026-01-02T03:04:05" in status.output
    assert "archived │ 4" in output(status) or "archived 4" in output(status)

    for outcome, message in (
        (RestoreOutcome.RESTORED, "Restored run"),
        (RestoreOutcome.NOOP, "is not archived"),
    ):
        monkeypatch.setattr(
            Client,
            "restore_pipeline_run",
            Mock(
                return_value=RestoreResponse(
                    run_id=UUID(int=1), outcome=outcome
                )
            ),
        )
        restore = CliRunner().invoke(runs, ["restore", "run-123"])
        assert restore.exit_code == 0, restore.output
        assert message in output(restore)
