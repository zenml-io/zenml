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

from zenml.enums import StackComponentType
from zenml.exceptions import ArtifactStoreInterfaceError
from zenml.integrations.gcp.artifact_stores.gcp_artifact_store import (
    GCPArtifactStore,
)


def test_gcp_artifact_store_attributes():
    """Tests that the basic attributes of the gcp artifact store are set
    correctly."""
    artifact_store = GCPArtifactStore(name="", path="gs://tmp")
    assert artifact_store.TYPE == StackComponentType.ARTIFACT_STORE
    assert artifact_store.FLAVOR == "gcp"


def test_must_be_gcs_path():
    """Checks that a gcp artifact store can only be initialized with a gcs
    path."""
    with pytest.raises(ArtifactStoreInterfaceError):
        GCPArtifactStore(name="", path="/local/path")

    with pytest.raises(ArtifactStoreInterfaceError):
        GCPArtifactStore(name="", path="s3://local/path")

    artifact_store = GCPArtifactStore(name="", path="gs://mybucket")
    assert artifact_store.path == "gs://mybucket"
