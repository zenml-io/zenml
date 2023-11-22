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

from tests.unit.test_general import _test_materializer
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
    with TemporaryDirectory() as artifact_uri:
        materializer = CloudpickleMaterializer(uri=artifact_uri)
        materializer._save_python_version()
        version = materializer._load_python_version()
        assert version == Environment().python_version()


def test_cloudpickle_materializer_is_not_registered(clean_client):
    """Test that the cloudpickle materializer is not registered by default."""
    assert (
        CloudpickleMaterializer
        not in materializer_registry.materializer_types.values()
    )


def test_cloudpickle_materializer_can_load_pickle(clean_client):
    """Test that the cloudpickle materializer can load regular pickle."""
    my_object = Unmaterializable()
    with TemporaryDirectory() as artifact_uri:
        artifact_filepath = os.path.join(artifact_uri, DEFAULT_FILENAME)
        with open(artifact_filepath, "wb") as f:
            pickle.dump(my_object, f)
        materializer = CloudpickleMaterializer(uri=artifact_uri)
        loaded_object = materializer.load(data_type=Unmaterializable)
        assert loaded_object.cat == "aria"
