"""Integration tests for `zenml.log_artifact_metadata()`."""

from typing import Tuple

import pytest
from typing_extensions import Annotated

from zenml import log_data_artifact_metadata, pipeline, step


@step
def artifact_metadata_logging_step() -> str:
    """A step that logs artifact metadata."""
    output_metadata = {
        "description": "Aria is great!",
        "metrics": {"accuracy": 0.9},
    }
    log_data_artifact_metadata(**output_metadata)
    return "42"


def test_log_artifact_metadata_single_output(clean_client):
    """Test logging artifact metadata for a single output."""

    @pipeline
    def artifact_metadata_logging_pipeline():
        artifact_metadata_logging_step()

    artifact_metadata_logging_pipeline()
    run_ = artifact_metadata_logging_pipeline.model.last_run
    output = run_.steps["artifact_metadata_logging_step"].output
    assert "description" in output.metadata
    assert output.metadata["description"].value == "Aria is great!"
    assert "metrics" in output.metadata
    assert output.metadata["metrics"].value == {"accuracy": 0.9}


@step
def artifact_multi_output_metadata_logging_step() -> (
    Tuple[Annotated[str, "str_output"], Annotated[int, "int_output"]]
):
    """A step that logs artifact metadata and has multiple outputs."""
    output_metadata = {
        "description": "Blupus is great!",
        "metrics": {"accuracy": 0.9},
    }
    log_data_artifact_metadata(output_name="int_output", **output_metadata)
    return "42", 42


def test_log_artifact_metadata_multi_output(clean_client):
    """Test logging artifact metadata for multiple outputs."""

    @pipeline
    def artifact_metadata_logging_pipeline():
        artifact_multi_output_metadata_logging_step()

    artifact_metadata_logging_pipeline()
    run_ = artifact_metadata_logging_pipeline.model.last_run
    step_ = run_.steps["artifact_multi_output_metadata_logging_step"]
    str_output = step_.outputs["str_output"]
    assert "description" not in str_output.metadata
    assert "metrics" not in str_output.metadata
    int_output = step_.outputs["int_output"]
    assert "description" in int_output.metadata
    assert int_output.metadata["description"].value == "Blupus is great!"
    assert "metrics" in int_output.metadata
    assert int_output.metadata["metrics"].value == {"accuracy": 0.9}


@step
def wrong_artifact_multi_output_metadata_logging_step() -> (
    Tuple[Annotated[str, "str_output"], Annotated[int, "int_output"]]
):
    """A step that logs artifact metadata and has multiple outputs."""
    output_metadata = {
        "description": "Axl is great!",
        "metrics": {"accuracy": 0.9},
    }
    log_data_artifact_metadata(**output_metadata)
    return "42", 42


def test_log_artifact_metadata_raises_error_if_output_name_unclear(
    clean_client,
):
    """Test that `log_artifact_metadata` raises an error if the output name is unclear."""

    @pipeline
    def artifact_metadata_logging_pipeline():
        wrong_artifact_multi_output_metadata_logging_step()

    with pytest.raises(ValueError):
        artifact_metadata_logging_pipeline()
