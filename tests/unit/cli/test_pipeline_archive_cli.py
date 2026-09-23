# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Pipeline CLI archive discovery and restore feedback."""

from unittest.mock import Mock
from uuid import uuid4

import pytest
from click.testing import CliRunner

from zenml.cli import utils as cli_utils
from zenml.cli.pipeline import pipeline
from zenml.client import Client
from zenml.enums import RestoreOutcome
from zenml.models.v2.core.pipeline_run import PipelineRunArchiveDescriptor
from zenml.models.v2.misc.retention import RestoreResponse


def test_pipeline_run_row_marks_archived_runs(sample_pipeline_run) -> None:
    """The default run table can show archive state without hydration."""
    sample_pipeline_run.get_body().archive = PipelineRunArchiveDescriptor(
        bundle_id=uuid4(),
        restore_run_id=sample_pipeline_run.id,
    )

    row = cli_utils.generate_pipeline_run_row(sample_pipeline_run, "json")

    assert row["archived"] is True


def test_unarchive_explains_which_detail_is_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Successful restore output names the newly available operations."""
    run_id = uuid4()
    monkeypatch.setattr(
        Client,
        "restore_pipeline_run",
        Mock(
            return_value=RestoreResponse(
                run_id=run_id, outcome=RestoreOutcome.RESTORED
            )
        ),
    )

    result = CliRunner().invoke(pipeline, ["runs", "unarchive", str(run_id)])

    assert result.exit_code == 0, result.output
    assert "Configuration, DAG" in result.output
    assert "inspection, and replay" in result.output
