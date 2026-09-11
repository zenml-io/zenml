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
from zenml.enums import RetentionOutcome
from zenml.models.v2.misc.retention import (
    RetentionDryRunResponse,
    RetentionOperationResponse,
    RetentionPassResponse,
    RetentionSettings,
    RetentionStatusResponse,
    RetentionTreeEstimate,
)


@pytest.fixture
def preview() -> RetentionDryRunResponse:
    """Return a compact preview with stable totals for CLI assertions."""
    return RetentionDryRunResponse(
        eligible_tree_count=2,
        examined_tree_count=3,
        truncated=False,
        trees=[
            RetentionTreeEstimate(root_run_id=UUID(int=1), rows=3),
            RetentionTreeEstimate(root_run_id=UUID(int=2), rows=4),
            RetentionTreeEstimate(
                root_run_id=UUID(int=3),
                rows=1,
                exclusion_reason="not_old",
            ),
        ],
        estimated_bytes=1536 * 1024,
        retained_details={},
        effective_policy=RetentionSettings(archive_after_days=90),
    )


def test_archive_previews_before_dry_run_or_submission(
    monkeypatch: pytest.MonkeyPatch, preview: RetentionDryRunResponse
) -> None:
    """Dry-run stops after preview and accepted submission prints no null table.

    Args:
        monkeypatch: Isolate client calls.
        preview: Stable inventory response.
    """
    inventory = Mock(return_value=preview)
    submit = Mock(
        return_value=RetentionPassResponse(outcome=RetentionOutcome.ACCEPTED)
    )
    monkeypatch.setattr(Client, "retention_dry_run", inventory)
    monkeypatch.setattr(Client, "archive_project", submit)
    runner = CliRunner()

    dry_run = runner.invoke(
        project, ["retention", "archive", "demo", "--dry-run"]
    )
    assert dry_run.exit_code == 0, dry_run.output
    assert "2 eligible tree(s), about 1.5 MiB across 7 rows" in unstyle(
        dry_run.output
    )
    assert "no data was changed" in dry_run.output
    submit.assert_not_called()

    accepted = runner.invoke(
        project, ["retention", "archive", "demo", "--yes"]
    )
    assert accepted.exit_code == 0, accepted.output
    assert "zenml project retention status demo" in " ".join(
        unstyle(accepted.output).split()
    )
    assert "None" not in accepted.output
    assert submit.call_count == 1


def test_archive_confirmation_can_cancel(
    monkeypatch: pytest.MonkeyPatch, preview: RetentionDryRunResponse
) -> None:
    """A rejected confirmation performs no archive submission.

    Args:
        monkeypatch: Isolate client calls.
        preview: Stable inventory response.
    """
    submit = Mock()
    monkeypatch.setattr(
        Client, "retention_dry_run", Mock(return_value=preview)
    )
    monkeypatch.setattr(Client, "archive_project", submit)

    result = CliRunner().invoke(
        project, ["retention", "archive", "demo"], input="n\n"
    )
    assert result.exit_code == 0, result.output
    assert "Execution retention canceled" in result.output
    submit.assert_not_called()


def test_set_and_show_merge_policy_and_reject_ambiguous_disable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Set preserves unspecified values, show renders them, and disable is explicit."""
    saved = RetentionSettings(archive_after_days=90, max_trees=7)
    get_project = Mock(return_value=SimpleNamespace(retention=saved))
    update_project = Mock()
    monkeypatch.setattr(Client, "get_project", get_project)
    monkeypatch.setattr(Client, "update_project", update_project)
    runner = CliRunner()

    result = runner.invoke(
        project,
        ["retention", "set", "demo", "--max-rows", "1234"],
    )
    assert result.exit_code == 0, result.output
    policy = update_project.call_args.kwargs["retention"]
    assert (policy.archive_after_days, policy.max_trees, policy.max_rows) == (
        90,
        7,
        1234,
    )
    shown = runner.invoke(project, ["retention", "show", "demo"])
    assert shown.exit_code == 0
    assert "Retention policy" in shown.output and "90" in shown.output

    invalid = runner.invoke(
        project,
        ["retention", "set", "--disable", "--archive-after-days", "90"],
    )
    assert invalid.exit_code == 2
    assert "cannot be combined" in invalid.output


def test_status_and_restore_acceptance_are_scalar_and_actionable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Status uses ISO scalars and accepted restore names its follow-up command.

    Args:
        monkeypatch: Isolate client calls.
    """
    monkeypatch.setattr(
        Client,
        "get_retention_status",
        Mock(
            return_value=RetentionStatusResponse(
                outcome=RetentionOutcome.SUCCEEDED,
                archive_enabled=True,
                archive_configured=True,
                archive_after_days=90,
                finished_at=datetime(2026, 1, 2, 3, 4, 5),
            )
        ),
    )
    status = CliRunner().invoke(project, ["retention", "status", "demo"])
    assert status.exit_code == 0, status.output
    assert "2026-01-02T03:04:05" in status.output
    assert "succeeded" in status.output
    assert "{" not in status.output

    monkeypatch.setattr(
        Client,
        "restore_pipeline_run",
        Mock(
            return_value=RetentionOperationResponse(
                outcome=RetentionOutcome.ACCEPTED
            )
        ),
    )
    restore = CliRunner().invoke(runs, ["restore", "run-123"])
    assert restore.exit_code == 0, restore.output
    assert "zenml pipeline runs restore-status run-123" in " ".join(
        unstyle(restore.output).split()
    )
    assert "None" not in restore.output
