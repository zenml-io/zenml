from uuid import uuid4

import pytest
from mock import MagicMock

from zenml.models import (
    ArtifactVersionIdentifier,
    ModelVersionIdentifier,
    PipelineRunIdentifier,
    RunMetadataResource,
    StepRunIdentifier,
)
from zenml.utils import metadata_utils
from zenml.utils.metadata_utils import bulk_log_metadata


def test_bulk_log_metadata_validations(monkeypatch):
    def boom():
        raise RuntimeError("boom!")

    # invalid step context with infer options triggers value error

    with monkeypatch.context() as m:
        m.setattr(metadata_utils, "get_step_context", boom)

        with pytest.raises(ValueError):
            bulk_log_metadata(metadata={"x": 1}, infer_models=True)

    with monkeypatch.context() as m:
        m.setattr(metadata_utils, "get_step_context", boom)

        with pytest.raises(ValueError):
            bulk_log_metadata(metadata={"x": 1}, infer_artifacts=True)

    # empty metadata triggers value error

    with pytest.raises(ValueError):
        bulk_log_metadata(
            metadata={},
            model_versions=[ModelVersionIdentifier(id=uuid4())],
        )

    # no entities provided triggers value error

    with pytest.raises(ValueError):
        bulk_log_metadata(
            metadata={"x": 1},
        )


def test_bulk_log_metadata_explicit(monkeypatch):
    mock_client = MagicMock()

    mock_client.get_pipeline_run.return_value = MagicMock(
        id=uuid4(), steps={"step": MagicMock(id=uuid4())}
    )
    mock_client.get_artifact_version.return_value = MagicMock(id=uuid4())
    mock_client.get_model_version.return_value = MagicMock(id=uuid4())

    mock_client.create_run_metadata = MagicMock()

    with monkeypatch.context() as m:
        m.setattr(metadata_utils, "Client", lambda: mock_client)

        bulk_log_metadata(
            metadata={"x": 1},
            step_runs=[
                StepRunIdentifier(
                    name="step",
                    run=PipelineRunIdentifier(id=uuid4()),
                )
            ],
            pipeline_runs=[
                PipelineRunIdentifier(id=uuid4()),
                PipelineRunIdentifier(name="test"),
            ],
            artifact_versions=[
                ArtifactVersionIdentifier(id=uuid4()),
                ArtifactVersionIdentifier(name="artifact", version="1"),
            ],
            model_versions=[
                ModelVersionIdentifier(name="model", version="1"),
                ModelVersionIdentifier(id=uuid4()),
            ],
            infer_models=False,
            infer_artifacts=False,
        )

    assert mock_client.get_pipeline_run.call_count == 2
    mock_client.get_artifact_version.assert_called_once()
    mock_client.get_model_version.assert_called_once()

    assert mock_client.create_run_metadata.call_args.kwargs["metadata"] == {
        "x": 1
    }
    assert (
        len(mock_client.create_run_metadata.call_args.kwargs["resources"]) == 7
    )

    assert all(
        isinstance(r, RunMetadataResource)
        for r in mock_client.create_run_metadata.call_args.kwargs["resources"]
    )


def test_bulk_log_metadata_infer_artifacts(monkeypatch):
    mock_step_context = MagicMock(
        _outputs={"a": MagicMock(id=uuid4()), "b": MagicMock(id=uuid4())}
    )

    mock_step_context.add_output_metadata = MagicMock()

    mock_client = MagicMock()
    mock_client.create_run_metadata = MagicMock()

    with monkeypatch.context() as m:
        m.setattr(metadata_utils, "Client", lambda: mock_client)
        m.setattr(
            metadata_utils, "get_step_context", lambda: mock_step_context
        )

        bulk_log_metadata(metadata={"x": 1}, infer_artifacts=True)

    assert mock_client.create_run_metadata.call_count == 0
    assert mock_step_context.add_output_metadata.call_count == 2


def test_bulk_log_metadata_infer_model(monkeypatch):
    mock_step_context = MagicMock(
        model_version=MagicMock(id=uuid4()),
    )

    mock_client = MagicMock()
    mock_client.create_run_metadata = MagicMock()

    with monkeypatch.context() as m:
        m.setattr(metadata_utils, "Client", lambda: mock_client)
        m.setattr(
            metadata_utils, "get_step_context", lambda: mock_step_context
        )

        bulk_log_metadata(metadata={"x": 1}, infer_models=True)

    assert mock_client.create_run_metadata.call_count == 1

    assert mock_client.create_run_metadata.call_args.kwargs["metadata"] == {
        "x": 1
    }
    assert (
        len(mock_client.create_run_metadata.call_args.kwargs["resources"]) == 1
    )


def test_combined_infer_with_explicit_options(monkeypatch):
    mock_step_context = MagicMock(
        model_version=MagicMock(id=uuid4()),
        _outputs={"a": MagicMock(id=uuid4()), "b": MagicMock(id=uuid4())},
    )

    mock_client = MagicMock()
    mock_client.create_run_metadata = MagicMock()

    with monkeypatch.context() as m:
        m.setattr(metadata_utils, "Client", lambda: mock_client)
        m.setattr(
            metadata_utils, "get_step_context", lambda: mock_step_context
        )

        bulk_log_metadata(
            metadata={"x": 1},
            infer_models=True,
            infer_artifacts=True,
            model_versions=[ModelVersionIdentifier(id=uuid4())],
            artifact_versions=[ArtifactVersionIdentifier(id=uuid4())],
        )

        assert mock_client.create_run_metadata.call_count == 1

        assert mock_client.create_run_metadata.call_args.kwargs[
            "metadata"
        ] == {"x": 1}
        assert (
            len(mock_client.create_run_metadata.call_args.kwargs["resources"])
            == 3
        )
        assert mock_step_context.add_output_metadata.call_count == 2
