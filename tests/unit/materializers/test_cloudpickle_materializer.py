#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Unit tests for the `CloudpickleMaterializer`."""

import os
import pickle
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

import cloudpickle
import pytest

from tests.unit.test_general import _test_materializer
from zenml.artifact_stores.base_artifact_store import BaseArtifactStore
from zenml.environment import Environment
from zenml.materializers.cloudpickle_materializer import (
    DEFAULT_FILENAME,
    CloudpickleMaterializer,
)
from zenml.materializers.materializer_registry import materializer_registry


class Unmaterializable:
    """A class that has no materializer."""

    cat = "aria"


def test_cloudpickle_materializer(clean_client):
    """Test that the cloudpickle materializer is used if no other is found."""
    output = _test_materializer(
        step_output=Unmaterializable(), expected_metadata_size=1
    )
    assert output.cat == "aria"


def test_cloudpickle_materializer_python_version_check(clean_client):
    """Test that the cloudpickle materializer saves the Python version."""
    with TemporaryDirectory(
        dir=clean_client.active_stack.artifact_store.path
    ) as artifact_uri:
        materializer = CloudpickleMaterializer(uri=artifact_uri)
        # Returns "unknown" before save
        assert materializer._load_python_version() == "unknown"

        materializer._save_python_version()
        version = materializer._load_python_version()
        assert version == Environment().python_version()


def test_cloudpickle_materializer_remote_artifact_store_python_version():
    """Test that python version check uses artifact store for remote URIs."""
    mock_store = MagicMock(spec=BaseArtifactStore)
    remote_uri = "s3://my-bucket/path/to/artifact"
    version_file = os.path.join(remote_uri, "python_version.txt")

    materializer = CloudpickleMaterializer(
        uri=remote_uri, artifact_store=mock_store
    )

    # When file does not exist in store
    mock_store.exists.return_value = False
    assert materializer._load_python_version() == "unknown"
    mock_store.exists.assert_called_with(version_file)

    # When file exists in store
    mock_store.exists.return_value = True
    mock_store.open.return_value.__enter__.return_value.read.return_value = (
        "3.11.0\n"
    )
    assert materializer._load_python_version() == "3.11.0"

    # Saving python version writes via artifact store
    mock_file = MagicMock()
    mock_store.open.return_value.__enter__.return_value = mock_file
    materializer._save_python_version()
    mock_store.open.assert_called_with(version_file, "w")
    mock_file.write.assert_called_with(Environment().python_version())


def test_cloudpickle_materializer_is_not_registered(clean_client):
    """Test that the cloudpickle materializer is not registered by default."""
    assert (
        CloudpickleMaterializer
        not in materializer_registry.materializer_types.values()
    )


def test_cloudpickle_materializer_can_load_pickle(clean_client):
    """Test that the cloudpickle materializer can load regular pickle."""
    my_object = Unmaterializable()
    with TemporaryDirectory(
        dir=clean_client.active_stack.artifact_store.path
    ) as artifact_uri:
        artifact_filepath = os.path.join(artifact_uri, DEFAULT_FILENAME)
        with open(artifact_filepath, "wb") as f:
            pickle.dump(my_object, f)
        materializer = CloudpickleMaterializer(uri=artifact_uri)
        loaded_object = materializer.load(data_type=Unmaterializable)
        assert loaded_object.cat == "aria"


def test_cloudpickle_materializer_load_without_content_hash(clean_client):
    """Test that loading works if no content hash is recorded."""
    my_object = Unmaterializable()
    with TemporaryDirectory(
        dir=clean_client.active_stack.artifact_store.path
    ) as artifact_uri:
        with open(os.path.join(artifact_uri, DEFAULT_FILENAME), "wb") as f:
            pickle.dump(my_object, f)
        materializer = CloudpickleMaterializer(uri=artifact_uri)
        assert materializer.expected_content_hash is None
        loaded_object = materializer.load(data_type=Unmaterializable)
        assert loaded_object.cat == "aria"


def test_cloudpickle_materializer_load_with_matching_content_hash(
    clean_client,
):
    """Test that loading works if the stored data matches the recorded hash."""
    my_object = Unmaterializable()
    with TemporaryDirectory(
        dir=clean_client.active_stack.artifact_store.path
    ) as artifact_uri:
        materializer = CloudpickleMaterializer(uri=artifact_uri)
        assert materializer.compute_content_hash(my_object) is None
        materializer.save(my_object)
        content_hash = materializer.compute_content_hash(my_object)
        assert content_hash is not None

        loader = CloudpickleMaterializer(uri=artifact_uri)
        loader.expected_content_hash = content_hash
        loaded_object = loader.load(data_type=Unmaterializable)
        assert loaded_object.cat == "aria"


def test_cloudpickle_materializer_load_with_content_hash_mismatch(
    clean_client,
):
    """Test that loading fails if the stored data does not match the hash."""
    my_object = Unmaterializable()
    with TemporaryDirectory(
        dir=clean_client.active_stack.artifact_store.path
    ) as artifact_uri:
        materializer = CloudpickleMaterializer(uri=artifact_uri)
        materializer.save(my_object)
        content_hash = materializer.compute_content_hash(my_object)
        assert content_hash is not None

        with open(os.path.join(artifact_uri, DEFAULT_FILENAME), "wb") as f:
            cloudpickle.dump({"other": "object"}, f)

        loader = CloudpickleMaterializer(uri=artifact_uri)
        loader.expected_content_hash = content_hash
        with pytest.raises(
            RuntimeError, match="does not match its recorded content hash"
        ):
            loader.load(data_type=Unmaterializable)
