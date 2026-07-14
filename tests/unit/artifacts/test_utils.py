#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
import os
import shutil
import tempfile
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from pydantic import BaseModel

import zenml.artifacts.utils as au
from zenml.artifacts.utils import (
    _load_artifact_from_uri,
    _strip_timestamp_from_multiline_string,
    load_artifact_from_response,
    load_model_from_metadata,
    save_model_metadata,
    should_use_artifact_store_cache,
    verify_artifact_data_availability,
)
from zenml.client import Client
from zenml.constants import MODEL_METADATA_YAML_FILE_NAME
from zenml.enums import ArtifactVersionAvailability
from zenml.materializers.pydantic_materializer import DEFAULT_FILENAME
from zenml.models import ArtifactVersionResponse


@pytest.fixture
def model_artifact(mocker, clean_client: "Client"):
    return mocker.Mock(
        spec=ArtifactVersionResponse,
        id="123",
        created="2023-01-01T00:00:00Z",
        updated="2023-01-01T00:00:00Z",
        project="project-name",
        name="model-name",
        type="type",
        uri="gs://my-bucket/model.joblib",
        data_type="path/to/model/class",
        materializer="path/to/materializer/class",
        artifact_store_id=clean_client.active_stack.artifact_store.id,
        availability=ArtifactVersionAvailability.AVAILABLE,
    )


def test_save_model_metadata(model_artifact):
    """Test the save_model_metadata function."""
    file_path = save_model_metadata(model_artifact)

    # Ensure that the file exists
    assert os.path.exists(file_path)

    # Read the contents of the file
    with open(file_path, "r") as f:
        file_contents = f.read()
        assert "datatype" in file_contents
        assert model_artifact.data_type in file_contents
        assert "materializer" in file_contents
        assert model_artifact.materializer in file_contents


@pytest.fixture
def model_metadata_dir(model_artifact, clean_client: "Client"):
    # Save the model metadata to a temporary file
    file_path = save_model_metadata(model_artifact)

    # Move the file to a temporary directory
    temp_dir = tempfile.mkdtemp(
        dir=clean_client.active_stack.artifact_store.path
    )
    shutil.move(
        file_path, os.path.join(temp_dir, MODEL_METADATA_YAML_FILE_NAME)
    )

    # Yield the temporary directory
    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


def test_load_model_from_metadata(mocker, model_metadata_dir):
    """Test the load_model_from_metadata function."""
    mocked_model = mocker.MagicMock()

    # Mock the _load_artifact function
    mocker_load_artifact = mocker.patch(
        "zenml.artifacts.utils._load_artifact_from_uri",
        return_value=mocked_model,
    )

    # Load the model from the metadata file
    model = load_model_from_metadata(model_metadata_dir)

    # Ensure that the model object is returned
    mocker_load_artifact.assert_called_once()
    assert model is not None
    assert isinstance(model, mocker.MagicMock)
    assert model == mocked_model


def test_load_artifact_from_response(mocker, model_artifact):
    """Test the test_load_artifact_from_response function."""
    # Mock the model object
    model = mocker.MagicMock()

    # Mock the _load_artifact_from_uri function
    mocker_load_artifact = mocker.patch(
        "zenml.artifacts.utils._load_artifact_from_uri", return_value=model
    )

    load_artifact_from_response(model_artifact)

    # Ensure the _load_artifact_from_uri function is called
    mocker_load_artifact.assert_called_once()


class TempClass(BaseModel):
    """Temp class for testing purposes."""

    temp_value: int = 1


@pytest.fixture
def builtin_type_file_uri(clean_client: "Client"):
    # Create a temporary file to save an integer
    temp_dir = tempfile.mkdtemp(
        dir=clean_client.active_stack.artifact_store.path
    )
    filepath = os.path.join(temp_dir, DEFAULT_FILENAME)

    # Save the integer to the temporary file
    from zenml.utils.yaml_utils import write_json

    write_json(filepath, TempClass().model_dump(mode="json"))

    # Yield the temporary directory
    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


def test__load_artifact(builtin_type_file_uri):
    """Test the _load_artifact function."""
    materializer = (
        "random_materializer_class_path.random_materializer_class_name"
    )
    data_type = "random_data_type_class_path.random_data_type_class_name"

    # Test with invalid materializer and ensure that a ModuleNotFoundError is
    # raised
    try:
        _load_artifact_from_uri(materializer, data_type, builtin_type_file_uri)
        assert False, "Expected a ModuleNotFoundError to be raised."
    except ModuleNotFoundError as e:
        assert str(e) == "No module named 'random_materializer_class_path'", (
            "Unexpected error message."
        )

    # Test with invalid data type and ensure that a ModuleNotFoundError is
    # raised
    materializer = (
        "zenml.materializers.pydantic_materializer.PydanticMaterializer"
    )
    try:
        _load_artifact_from_uri(materializer, data_type, builtin_type_file_uri)
        assert False, "Expected a ModuleNotFoundError to be raised."
    except ModuleNotFoundError as e:
        assert str(e) == "No module named 'random_data_type_class_path'", (
            "Unexpected error message."
        )

    # Test with valid materializer and data type and ensure that the artifact
    # is loaded correctly
    from zenml.utils import source_utils

    data_type = source_utils.Source(
        module=TempClass.__module__,
        attribute=TempClass.__name__,
        type=source_utils.SourceType.BUILTIN,
    )
    artifact = _load_artifact_from_uri(
        materializer, data_type, builtin_type_file_uri
    )
    assert artifact is not None
    assert isinstance(artifact, TempClass)


@pytest.mark.parametrize(
    "raw, expected",
    [
        (
            "[2025-05-16 16:20:23 UTC] Using cached version of step XYZ.\n",
            "Using cached version of step XYZ.\n",
        ),
        (
            "[2025-05-16 16:20:23 UTC] Using cached version of step XYZ.\n[2025-05-16 16:20:59 UTC] Log 2.\n",
            "Using cached version of step XYZ.\nLog 2.\n",
        ),
        (
            "Using cached version of step XYZ.\nLog 2.\n",
            "Using cached version of step XYZ.\nLog 2.\n",
        ),
        ("", ""),
        (
            "[2025-05-16 16:20:23 UTC] Using cached version of step XYZ.\nNo timestamp here\n"
            "[2025-05-16 16:20:59 UTC] Log 2.\n",
            "Using cached version of step XYZ.\nNo timestamp here\nLog 2.\n",
        ),
        (
            "[2025-05-16 16:20:23 UTC] Using cached version of step XYZ.\n"
            "Timestamp is in the logs: [2025-05-16 16:20:59 UTC]\n"
            "[2025-05-16 16:20:59 UTC] Log 2.\n",
            "Using cached version of step XYZ.\n"
            "Timestamp is in the logs: [2025-05-16 16:20:59 UTC]\nLog 2.\n",
        ),
    ],
)
def test__strip_timestamp_from_multiline_string(raw: str, expected: str):
    """Test the _strip_timestamp_from_multiline_string function to properly strip the logs."""
    assert _strip_timestamp_from_multiline_string(raw) == expected


def _artifact_store_model():
    """Build a fake component model exposing id, updated and name."""
    return SimpleNamespace(
        id=uuid4(),
        updated=datetime(2024, 1, 1),
        name="artifact-store",
    )


def test_should_use_cache_respects_server_env_and_config(monkeypatch):
    """The gate requires the server env and honors the config toggle."""
    monkeypatch.delenv("ZENML_SERVER", raising=False)
    monkeypatch.delenv(
        "ZENML_SERVER_ARTIFACT_STORE_CACHE_ENABLED", raising=False
    )
    # Outside the server the config is never consulted.
    assert should_use_artifact_store_cache() is False

    monkeypatch.setenv("ZENML_SERVER", "true")
    monkeypatch.setenv("ZENML_SERVER_ARTIFACT_STORE_CACHE_ENABLED", "true")
    assert should_use_artifact_store_cache() is True

    monkeypatch.setenv("ZENML_SERVER_ARTIFACT_STORE_CACHE_ENABLED", "false")
    assert should_use_artifact_store_cache() is False


def test_instantiate_artifact_store_uses_cache_when_active(monkeypatch):
    """With the cache active, the store is served from the server cache."""
    monkeypatch.setattr(au, "should_use_artifact_store_cache", lambda: True)
    store = MagicMock()
    cache = MagicMock()
    cache.get_or_create.return_value = store
    monkeypatch.setattr(
        "zenml.zen_server.utils.artifact_store_cache", lambda: cache
    )

    model = _artifact_store_model()
    assert au.instantiate_artifact_store(model) is store
    cache.get_or_create.assert_called_once_with(model)


def test_instantiate_artifact_store_builds_when_disabled(monkeypatch):
    """With the cache off, a fresh store is built."""
    monkeypatch.setattr(au, "should_use_artifact_store_cache", lambda: False)
    store = MagicMock()
    monkeypatch.setattr(
        "zenml.stack.StackComponent.from_model", lambda model: store
    )

    assert au.instantiate_artifact_store(_artifact_store_model()) is store


def _with_availability(artifact_version, availability):
    body = artifact_version.get_body().model_copy(
        update={"availability": availability}
    )
    return artifact_version.model_copy(update={"body": body})


def test_verify_artifact_data_availability_for_available_artifact(
    sample_artifact_version_model,
):
    """An available artifact passes without any server calls."""
    verify_artifact_data_availability(
        artifact=sample_artifact_version_model, wait=False
    )


def test_verify_artifact_data_availability_for_unmaterialized_artifact(
    sample_artifact_version_model,
):
    """An unmaterialized artifact fails immediately."""
    artifact = _with_availability(
        sample_artifact_version_model,
        ArtifactVersionAvailability.UNMATERIALIZED,
    )
    with pytest.raises(RuntimeError, match="materialization disabled"):
        verify_artifact_data_availability(artifact=artifact, wait=False)


def test_verify_artifact_data_availability_refreshes_pending_artifact(
    mocker, sample_artifact_version_model
):
    """A stale pending artifact is refreshed before failing."""
    pending = _with_availability(
        sample_artifact_version_model, ArtifactVersionAvailability.PENDING
    )
    mock_client = MagicMock()
    mock_client.zen_store.get_artifact_version.return_value = (
        sample_artifact_version_model
    )
    mocker.patch("zenml.artifacts.utils.Client", return_value=mock_client)

    verify_artifact_data_availability(artifact=pending, wait=False)
    mock_client.zen_store.get_artifact_version.assert_called_once()


def test_verify_artifact_data_availability_for_failed_upload(
    mocker, sample_artifact_version_model
):
    """An artifact with a failed data upload fails."""
    failed = _with_availability(
        sample_artifact_version_model,
        ArtifactVersionAvailability.UPLOAD_FAILED,
    )
    mock_client = MagicMock()
    mock_client.zen_store.get_artifact_version.return_value = failed
    mocker.patch("zenml.artifacts.utils.Client", return_value=mock_client)

    with pytest.raises(RuntimeError, match="upload failed"):
        verify_artifact_data_availability(artifact=failed, wait=False)


def test_verify_artifact_data_availability_for_pending_artifact_without_wait(
    mocker, sample_artifact_version_model
):
    """A pending artifact fails without waiting when wait is disabled."""
    pending = _with_availability(
        sample_artifact_version_model, ArtifactVersionAvailability.PENDING
    )
    mock_client = MagicMock()
    mock_client.zen_store.get_artifact_version.return_value = pending
    mocker.patch("zenml.artifacts.utils.Client", return_value=mock_client)

    with pytest.raises(RuntimeError, match="still in progress"):
        verify_artifact_data_availability(artifact=pending, wait=False)
