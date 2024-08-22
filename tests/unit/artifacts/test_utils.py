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
from uuid import uuid4

import numpy as np
import pytest

from zenml.artifacts.utils import (
    _get_new_artifact_version,
    _load_artifact_from_uri,
    load_artifact_from_response,
    load_model_from_metadata,
    save_model_metadata,
)
from zenml.client import Client
from zenml.constants import MODEL_METADATA_YAML_FILE_NAME
from zenml.materializers.numpy_materializer import NUMPY_FILENAME
from zenml.models import ArtifactVersionResponse, Page


@pytest.fixture
def model_artifact(mocker, clean_client: "Client"):
    return mocker.Mock(
        spec=ArtifactVersionResponse,
        id="123",
        created="2023-01-01T00:00:00Z",
        updated="2023-01-01T00:00:00Z",
        workspace="workspace-name",
        name="model-name",
        type="type",
        uri="gs://my-bucket/model.joblib",
        data_type="path/to/model/class",
        materializer="path/to/materializer/class",
        artifact_store_id=clean_client.active_stack.artifact_store.id,
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


@pytest.fixture
def numpy_file_uri(clean_client: "Client"):
    # Create a temporary file to save the numpy array
    temp_dir = tempfile.mkdtemp(
        dir=clean_client.active_stack.artifact_store.path
    )
    numpy_file = os.path.join(temp_dir, NUMPY_FILENAME)

    # Save a numpy array to the temporary file
    arr = np.array([1, 2, 3, 4, 5])
    np.save(numpy_file, arr)

    # Yield the temporary directory
    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


def test__load_artifact(numpy_file_uri):
    """Test the _load_artifact function."""
    materializer = (
        "random_materializer_class_path.random_materializer_class_name"
    )
    data_type = "random_data_type_class_path.random_data_type_class_name"

    # Test with invalid materializer and ensure that a ModuleNotFoundError is
    # raised
    try:
        _load_artifact_from_uri(materializer, data_type, numpy_file_uri)
        assert False, "Expected a ModuleNotFoundError to be raised."
    except ModuleNotFoundError as e:
        assert (
            str(e) == "No module named 'random_materializer_class_path'"
        ), "Unexpected error message."

    # Test with invalid data type and ensure that a ModuleNotFoundError is
    # raised
    materializer = "zenml.materializers.numpy_materializer.NumpyMaterializer"
    try:
        _load_artifact_from_uri(materializer, data_type, numpy_file_uri)
        assert False, "Expected a ModuleNotFoundError to be raised."
    except ModuleNotFoundError as e:
        assert (
            str(e) == "No module named 'random_data_type_class_path'"
        ), "Unexpected error message."

    # Test with valid materializer and data type and ensure that the artifact
    # is loaded correctly
    data_type = "numpy.ndarray"
    artifact = _load_artifact_from_uri(materializer, data_type, numpy_file_uri)
    assert artifact is not None
    assert isinstance(artifact, np.ndarray)


def test__get_new_artifact_version(mocker, sample_artifact_version_model):
    """Unit test for the `_get_new_artifact_version` function."""
    # If no artifact exists, "1" should be returned
    mocker.patch(
        "zenml.client.Client.list_artifact_versions",
        return_value=Page(
            index=1,
            max_size=1,
            total_pages=1,
            total=0,
            items=[],
        ),
    )
    assert _get_new_artifact_version(sample_artifact_version_model.name) == 1

    # If an artifact exists, the next version should be returned
    mocker.patch(
        "zenml.client.Client.list_artifact_versions",
        return_value=Page(
            index=1,
            max_size=1,
            total_pages=1,
            total=1,
            items=[sample_artifact_version_model],
        ),
    )
    assert (
        _get_new_artifact_version(sample_artifact_version_model.name)
        == int(sample_artifact_version_model.version) + 1
    )
