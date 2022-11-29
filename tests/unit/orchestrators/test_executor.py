from uuid import UUID

import pytest

from zenml.artifacts.data_artifact import DataArtifact
from zenml.artifacts.model_artifact import ModelArtifact
from zenml.orchestrators.executor import register_output_artifacts


def test_register_output_artifacts(clean_client):
    """Test that `register_output_artifacts()` registers new artifacts."""
    artifact_1 = DataArtifact(
        uri="some/uri/abc/",
        materializer="some_materializer",
        data_type="np.ndarray",
    )
    artifact_2 = DataArtifact(
        uri="some/uri/def/",
        materializer="some_other_materializer",
        data_type="some data type",
    )
    artifact_3 = ModelArtifact(
        uri="some/uri/ghi/",
        materializer="some_model_materializer",
        data_type="some model type",
    )
    assert len(clean_client.zen_store.list_artifacts()) == 0
    return_val = register_output_artifacts({"output": artifact_1})
    assert len(clean_client.zen_store.list_artifacts()) == 1
    assert isinstance(return_val, dict)
    assert len(return_val) == 1
    assert isinstance(return_val["output"], UUID)
    return_val = register_output_artifacts({})
    assert len(clean_client.zen_store.list_artifacts()) == 1
    assert return_val == {}
    return_val = register_output_artifacts(
        {
            "arias_data": artifact_2,
            "arias_model": artifact_3,
        }
    )
    assert len(clean_client.zen_store.list_artifacts()) == 3
    assert isinstance(return_val, dict)
    assert len(return_val) == 2
    assert isinstance(return_val["arias_data"], UUID)
    assert isinstance(return_val["arias_model"], UUID)


def test_register_output_artifacts_with_incomplete_artifacts(clean_client):
    """Test that an error is raised if materializer or data type are missing."""

    # data type missing
    incomplete_artifact = DataArtifact(
        uri="some/uri/abc/",
        materializer="some_materializer",
    )
    with pytest.raises(ValueError):
        register_output_artifacts({"output": incomplete_artifact})

    # materializer missing
    incomplete_artifact = DataArtifact(
        uri="some/uri/abc/",
        data_type="some_data_type",
    )
    with pytest.raises(ValueError):
        register_output_artifacts({"output": incomplete_artifact})
