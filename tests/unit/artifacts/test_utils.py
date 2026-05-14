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
import io
import os
import shutil
import tempfile
import zipfile

import pytest
from pydantic import BaseModel

from zenml.artifact_stores.base_artifact_store import ObjectInfo
from zenml.artifacts.utils import (
    _load_artifact_from_uri,
    _strip_timestamp_from_multiline_string,
    download_artifact_files_from_response,
    load_artifact_from_response,
    load_model_from_metadata,
    save_model_metadata,
)
from zenml.client import Client
from zenml.constants import MODEL_METADATA_YAML_FILE_NAME
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


class _ListdirOnlyArtifactStore:
    """Small fake store that only supports the legacy download path."""

    def __init__(self, artifact_uri: str, files: dict[str, bytes]) -> None:
        self.artifact_uri = artifact_uri
        self.files = files
        self.listdir_calls: list[str] = []
        self.open_calls: list[str] = []

    def listdir(self, path: str) -> list[str]:
        self.listdir_calls.append(path)
        return list(self.files)

    def open(self, path: str, mode: str = "rb") -> io.BytesIO:
        self.open_calls.append(path)
        relative_path = os.path.relpath(path, self.artifact_uri)
        return io.BytesIO(self.files[relative_path])


class _NativeListStreamingArtifactStore:
    """Small fake store with native listing but no native download."""

    def __init__(self, objects: dict[str, bytes]) -> None:
        self.objects = objects
        self.list_objects_calls: list[tuple[str, bool]] = []
        self.open_calls: list[str] = []
        self.download_calls = 0

    def list_objects(
        self, prefix: str, recursive: bool = False
    ) -> list[ObjectInfo]:
        self.list_objects_calls.append((prefix, recursive))
        return [
            ObjectInfo(uri=uri, relative_path=os.path.basename(uri))
            for uri in self.objects
        ]

    def download_objects_to_directory(
        self,
        objects: list[ObjectInfo],
        local_dir: str,
        max_workers: int | None = None,
    ) -> bool:
        self.download_calls += 1
        return False

    def open(self, path: str, mode: str = "rb") -> io.BytesIO:
        self.open_calls.append(path)
        return io.BytesIO(self.objects[path])


class _AcceleratedArtifactStore:
    """Small fake store that handles bulk artifact downloads."""

    def __init__(self, objects: dict[str, bytes]) -> None:
        self.objects = objects
        self.downloaded_relative_paths: list[str] = []

    def list_objects(
        self, prefix: str, recursive: bool = False
    ) -> list[ObjectInfo]:
        return [
            ObjectInfo(uri=uri, relative_path=os.path.basename(uri))
            for uri in self.objects
        ]

    def download_objects_to_directory(
        self,
        objects: list[ObjectInfo],
        local_dir: str,
        max_workers: int | None = None,
    ) -> bool:
        for object_info in objects:
            self.downloaded_relative_paths.append(object_info.relative_path)
            destination = os.path.join(local_dir, object_info.relative_path)
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            with open(destination, "wb") as file:
                file.write(self.objects[object_info.uri])
        return True

    def open(self, path: str, mode: str = "rb") -> io.BytesIO:
        raise AssertionError("Accelerated downloads should not stream files.")


def _patch_artifact_store(mocker, artifact_store):
    return mocker.patch(
        "zenml.artifacts.utils."
        "_get_artifact_store_from_response_or_from_active_stack",
        return_value=artifact_store,
    )


def _read_zip_contents(path: str) -> dict[str, bytes]:
    with zipfile.ZipFile(path, "r") as zip_file:
        return {
            entry_name: zip_file.read(entry_name)
            for entry_name in zip_file.namelist()
        }


def test_download_artifact_files_uses_listdir_streaming_fallback(
    tmp_path, mocker
):
    """Test that stores without optional hooks keep listdir/open behavior."""
    artifact_uri = str(tmp_path / "artifact")
    files = {
        f"file-{index}.txt": f"value-{index}".encode() for index in range(20)
    }
    artifact_store = _ListdirOnlyArtifactStore(artifact_uri, files)
    artifact = mocker.Mock(id="artifact-id", uri=artifact_uri)
    _patch_artifact_store(mocker, artifact_store)

    zipfile_path = str(tmp_path / "artifact.zip")
    download_artifact_files_from_response(artifact, path=zipfile_path)

    assert _read_zip_contents(zipfile_path) == files
    assert artifact_store.listdir_calls == [artifact_uri]
    assert artifact_store.open_calls == [
        str(os.path.join(artifact_uri, file_name)) for file_name in files
    ]


def test_download_artifact_files_streams_after_native_list_if_download_unsupported(
    tmp_path, mocker
):
    """Test native listing with streaming fallback for stores like GCS."""
    artifact_uri = "gs://bucket/artifact"
    objects = {
        f"{artifact_uri}/file-{index}.txt": f"value-{index}".encode()
        for index in range(3)
    }
    artifact_store = _NativeListStreamingArtifactStore(objects)
    artifact = mocker.Mock(id="artifact-id", uri=artifact_uri)
    _patch_artifact_store(mocker, artifact_store)

    zipfile_path = str(tmp_path / "artifact.zip")
    download_artifact_files_from_response(artifact, path=zipfile_path)

    assert _read_zip_contents(zipfile_path) == {
        os.path.basename(uri): content for uri, content in objects.items()
    }
    assert artifact_store.list_objects_calls == [(artifact_uri, False)]
    assert artifact_store.download_calls == 1
    assert artifact_store.open_calls == list(objects)


def test_download_artifact_files_uses_accelerated_download_helper(
    tmp_path, mocker
):
    """Test native list/download helper path before ZIP creation."""
    artifact_uri = "s3://bucket/artifact"
    objects = {
        f"{artifact_uri}/file-{index}.txt": f"value-{index}".encode()
        for index in range(25)
    }
    artifact_store = _AcceleratedArtifactStore(objects)
    artifact = mocker.Mock(id="artifact-id", uri=artifact_uri)
    _patch_artifact_store(mocker, artifact_store)

    zipfile_path = str(tmp_path / "artifact.zip")
    download_artifact_files_from_response(artifact, path=zipfile_path)

    assert _read_zip_contents(zipfile_path) == {
        os.path.basename(uri): content for uri, content in objects.items()
    }
    assert artifact_store.downloaded_relative_paths == [
        os.path.basename(uri) for uri in objects
    ]


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
