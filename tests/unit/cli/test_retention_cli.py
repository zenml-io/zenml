# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""One target and a confirmation protect against accidental archiving."""

from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from click.testing import CliRunner

from zenml.cli.server import retention
from zenml.client import Client
from zenml.models.v2.misc.retention import ArchiveResponse

RUN_ID = str(uuid4())


@pytest.mark.parametrize(
    "args,confirmed,archives",
    [
        (["--run-id", RUN_ID], False, False),
        (["--run-id", RUN_ID], True, True),
        (["--pipeline", "demo"], True, True),
        (["--pipeline", "demo", "--project", "demo"], True, False),
        ([], True, False),
    ],
)
def test_archive_requires_one_target_and_confirmation(
    monkeypatch, args, confirmed, archives
):
    """Exactly one target plus confirmation permits archiving."""
    archive = Mock(return_value=ArchiveResponse(archived=1))
    monkeypatch.setattr(Client, "archive_runs", archive)
    result = CliRunner().invoke(
        retention,
        ["archive", *args] + (["--yes"] if confirmed else []),
        input="n\n",
    )
    assert archive.call_count == int(archives), result.output


def test_archive_reports_refusals(monkeypatch):
    """Refused runs are listed with their reason, not silently counted."""
    archive = Mock(
        return_value=ArchiveResponse(
            skipped=1,
            refusals=[{"run_id": RUN_ID, "reason": "resumable_failed"}],
            pending=True,
            next_after_run_id=RUN_ID,
        )
    )
    monkeypatch.setattr(Client, "archive_runs", archive)
    result = CliRunner().invoke(
        retention, ["archive", "--project", "demo", "--yes"]
    )
    assert result.exit_code == 0, result.output
    assert "resumable_failed" in result.output
    assert "repeat the command" in result.output
    assert "--after-run-id" in result.output
    assert RUN_ID in result.output

    continued = CliRunner().invoke(
        retention,
        [
            "archive",
            "--project",
            "demo",
            "--after-run-id",
            RUN_ID,
            "--yes",
        ],
    )
    assert continued.exit_code == 0, continued.output
    assert archive.call_args.kwargs["after_run_id"] == UUID(RUN_ID)


def test_force_confirmation_names_every_policy_override(monkeypatch):
    """An interactive force request states which protections it bypasses."""
    archive = Mock(return_value=ArchiveResponse(archived=1))
    monkeypatch.setattr(Client, "archive_runs", archive)

    result = CliRunner().invoke(
        retention,
        ["archive", "--run-id", RUN_ID, "--force"],
        input="y\n",
    )

    assert result.exit_code == 0, result.output
    assert "minimum age" in result.output
    assert "model-version protection" in result.output
    assert "restore grace" in result.output
    assert "active and resumable" in result.output
    assert archive.call_args.kwargs["force"] is True


def test_dry_run_needs_no_confirmation_and_reports_eligibility(monkeypatch):
    """A side-effect-free preview is immediate and clearly labeled."""
    archive = Mock(
        return_value=ArchiveResponse(
            dry_run=True,
            eligible=2,
            skipped=1,
            refusals=[{"run_id": RUN_ID, "reason": "not_old"}],
        )
    )
    monkeypatch.setattr(Client, "archive_runs", archive)

    result = CliRunner().invoke(
        retention, ["archive", "--run-id", RUN_ID, "--dry-run"]
    )

    assert result.exit_code == 0, result.output
    assert "Dry run: eligible 2" in result.output
    assert "Nothing moved" not in result.output
    assert archive.call_args.kwargs["dry_run"] is True
