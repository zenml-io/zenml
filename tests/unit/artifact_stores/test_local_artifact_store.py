#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

import pytest

from zenml.artifact_stores import LocalArtifactStore
from zenml.enums import StackComponentType
from zenml.exceptions import ArtifactStoreInterfaceError


def test_local_artifact_store_attributes():
    """Tests that the basic attributes of the local artifact store are set
    correctly."""
    artifact_store = LocalArtifactStore(name="", path="/tmp")
    assert artifact_store.TYPE == StackComponentType.ARTIFACT_STORE
    assert artifact_store.FLAVOR == "local"


def test_local_artifact_store_only_supports_local_paths():
    """Checks that a local artifact store can only be initialized with a local
    path."""
    with pytest.raises(ArtifactStoreInterfaceError):
        LocalArtifactStore(name="", path="gs://remote/path")

    with pytest.raises(ArtifactStoreInterfaceError):
        LocalArtifactStore(name="", path="s3://remote/path")

    with pytest.raises(ArtifactStoreInterfaceError):
        LocalArtifactStore(name="", path="hdfs://remote/path")

    artifact_store = LocalArtifactStore(name="", path="/local/path")
    assert artifact_store.path == "/local/path"
