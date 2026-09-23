# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""One target and a confirmation protect against accidental archiving."""

from unittest.mock import Mock
from uuid import uuid4

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


def test_failed_attempts_fail_the_command(monkeypatch):
    """Scripts can detect that some runs were not archived."""
    archive = Mock(return_value=ArchiveResponse(archived=1, failed=1))
    monkeypatch.setattr(Client, "archive_runs", archive)

    result = CliRunner().invoke(
        retention, ["archive", "--run-id", RUN_ID, "--yes"]
    )

    assert result.exit_code != 0
    assert "Archived 1" in result.output


@pytest.mark.parametrize("dry_run", [False, True])
def test_archive_automatically_traverses_batches(monkeypatch, dry_run):
    """One command visits every page, including preview pages with no writes."""
    cursors = [uuid4(), uuid4()]
    archive = Mock(
        side_effect=[
            ArchiveResponse(
                dry_run=dry_run, pending=True, next_after_run_id=cursors[0]
            ),
            ArchiveResponse(
                dry_run=dry_run, pending=True, next_after_run_id=cursors[1]
            ),
            ArchiveResponse(dry_run=dry_run),
        ]
    )
    monkeypatch.setattr(Client, "archive_runs", archive)
    args = [
        "archive",
        "--project",
        "demo",
        "--dry-run" if dry_run else "--yes",
    ]
    result = CliRunner().invoke(retention, args)
    assert result.exit_code == 0, result.output
    assert [
        call.kwargs["after_run_id"] for call in archive.call_args_list
    ] == [None, *cursors]
    assert all(
        call.kwargs["dry_run"] == dry_run for call in archive.call_args_list
    )


def test_archive_stops_after_failed_batch(monkeypatch):
    """Do not advance past a failed page and report the full scan as success."""
    archive = Mock(
        return_value=ArchiveResponse(
            failed=1, pending=True, next_after_run_id=uuid4()
        )
    )
    monkeypatch.setattr(Client, "archive_runs", archive)
    result = CliRunner().invoke(
        retention, ["archive", "--project", "demo", "--yes"]
    )
    assert result.exit_code != 0
    assert archive.call_count == 1
