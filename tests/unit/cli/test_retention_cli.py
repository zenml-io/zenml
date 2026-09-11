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
    RetentionDryRunResponse,
    RetentionPassResponse,
    RetentionRunEstimate,
    RetentionSettings,
    RetentionStatusResponse,
)


def preview(eligible: int, truncated: bool = False) -> RetentionDryRunResponse:
    """Build a preview with `eligible` runs of three rows each."""
    return RetentionDryRunResponse(
        eligible_run_count=eligible,
        examined_run_count=eligible + 1,
        truncated=truncated,
        runs=[
            *(
                RetentionRunEstimate(run_id=UUID(int=index + 1), rows=3)
                for index in range(eligible)
            ),
            RetentionRunEstimate(
                run_id=UUID(int=99), rows=1, exclusion_reason="pinned"
            ),
        ],
        effective_policy=RetentionSettings(archive_after_days=90),
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


def test_archive_previews_then_submits(monkeypatch, submit) -> None:
    """Dry-run stops after the preview; --yes submits and names status."""
    monkeypatch.setattr(
        Client, "retention_dry_run", Mock(return_value=preview(2))
    )
    runner = CliRunner()

    dry_run = runner.invoke(
        project, ["retention", "archive", "demo", "--dry-run"]
    )
    assert dry_run.exit_code == 0, dry_run.output
    assert "2 eligible run(s) covering 6 rows" in output(dry_run)
    submit.assert_not_called()

    accepted = runner.invoke(
        project, ["retention", "archive", "demo", "--yes"]
    )
    assert accepted.exit_code == 0, accepted.output
    assert "zenml project retention status demo" in output(accepted)
    submit.assert_called_once()


def test_archive_confirmation_can_cancel(monkeypatch, submit) -> None:
    """A rejected confirmation submits nothing."""
    monkeypatch.setattr(
        Client, "retention_dry_run", Mock(return_value=preview(2))
    )

    result = CliRunner().invoke(
        project, ["retention", "archive", "demo"], input="n\n"
    )

    assert result.exit_code == 0, result.output
    assert "Execution retention canceled" in result.output
    submit.assert_not_called()


@pytest.mark.parametrize("truncated", [False, True])
def test_empty_preview_submits_only_when_more_runs_follow(
    monkeypatch, submit, truncated
) -> None:
    """A batch without eligible runs still moves a pass past it."""
    monkeypatch.setattr(
        Client,
        "retention_dry_run",
        Mock(return_value=preview(0, truncated=truncated)),
    )

    result = CliRunner().invoke(
        project, ["retention", "archive", "demo", "--yes"]
    )

    assert result.exit_code == 0, result.output
    assert submit.called is truncated
    if not truncated:
        assert "No pipeline runs are currently eligible" in output(result)


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
