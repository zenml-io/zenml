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


def test_archive_reports_refusals(monkeypatch):
    """Refused runs are listed with their reason, not silently counted."""
    monkeypatch.setattr(
        Client,
        "archive_runs",
        Mock(
            return_value=ArchiveResponse(
                skipped=1,
                refusals=[{"run_id": RUN_ID, "reason": "resumable_failed"}],
                pending=True,
            )
        ),
    )
    result = CliRunner().invoke(
        retention, ["archive", "--run-id", RUN_ID, "--yes"]
    )
    assert result.exit_code == 0, result.output
    assert "resumable_failed" in result.output
    assert "repeat the command" in result.output
