# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""CLI opt-in and confirmation protect against accidental archive passes."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from click.testing import CliRunner

from zenml.cli.project import project
from zenml.client import Client
from zenml.models.v2.misc.retention import (
    RetentionPassResponse,
    RetentionSettings,
)


@pytest.mark.parametrize(
    "days,confirmed,submits",
    [(90, False, False), (None, True, False), (90, True, True)],
)
def test_archive_requires_policy_and_confirmation(
    monkeypatch, days, confirmed, submits
):
    """Only an enabled policy and confirmation permit submission."""
    monkeypatch.setattr(
        Client,
        "get_project",
        lambda *a, **k: SimpleNamespace(
            retention=RetentionSettings(archive_after_days=days)
        ),
    )
    submit = Mock(return_value=RetentionPassResponse(outcome="accepted"))
    monkeypatch.setattr(Client, "archive_project", submit)
    args = ["retention", "archive", "demo"] + (["--yes"] if confirmed else [])
    result = CliRunner().invoke(project, args, input="n\n")
    assert result.exit_code == 0, result.output
    assert submit.call_count == int(submits)
