"""Verify scoring keeps the selected training run's registered model identity."""

import sys
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID

import pytest
import run as demo_cli

from zenml.enums import ExecutionStatus
from zenml.models import (
    ModelResponse,
    ModelResponseMetadata,
    ModelVersionResponse,
    ModelVersionResponseBody,
    ModelVersionResponseMetadata,
    ModelVersionResponseResources,
)


def test_scoring_cli_reuses_registered_model_version_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An existing version UUID must not become a newly created version name.

    Args:
        monkeypatch: Fixture for replacing client and pipeline boundaries.
    """
    version_id = UUID("12345678-1234-4234-8234-123456789abc")
    training_id = UUID("87654321-4321-4321-8321-cba987654321")
    project = SimpleNamespace(id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"))
    registered_model = ModelResponse.model_construct(
        name="bike-demand", metadata=ModelResponseMetadata.model_construct()
    )
    registered_version = ModelVersionResponse.model_construct(
        id=version_id,
        name="weather-aware",
        body=ModelVersionResponseBody.model_construct(model=registered_model),
        metadata=ModelVersionResponseMetadata.model_construct(),
        resources=ModelVersionResponseResources.model_construct(tags=[]),
    )
    training_run = SimpleNamespace(
        project=project,
        pipeline=SimpleNamespace(name="bike_demand_training"),
        status=ExecutionStatus.COMPLETED,
        model_version=registered_version,
    )
    client = SimpleNamespace(
        active_project=project,
        get_pipeline_run=Mock(return_value=training_run),
    )
    scoring = Mock()
    scoring.with_options.return_value.return_value = SimpleNamespace(
        id="new-scoring-run", status=ExecutionStatus.COMPLETED
    )
    monkeypatch.setattr(demo_cli, "Client", lambda: client)
    monkeypatch.setattr(demo_cli, "bike_demand_scoring", scoring)
    monkeypatch.setattr(
        sys,
        "argv",
        ["run.py", "score-bikes", "--training-run-id", str(training_id)],
    )

    demo_cli.main()

    selected_model = scoring.with_options.call_args.kwargs["model"]
    assert selected_model.model_version_id == version_id
    assert selected_model.version == "weather-aware"
    client.get_pipeline_run.assert_called_once_with(
        training_id, project=project.id
    )
    assert scoring.with_options.return_value.call_args.kwargs[
        "training_run_id"
    ] == str(training_id)
