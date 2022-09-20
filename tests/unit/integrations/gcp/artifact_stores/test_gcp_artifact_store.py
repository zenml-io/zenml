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


from uuid import uuid4

import pytest

from zenml.enums import StackComponentType
from zenml.exceptions import ArtifactStoreInterfaceError
from zenml.integrations.gcp.artifact_stores.gcp_artifact_store import (
    GCPArtifactStore,
)
from zenml.integrations.gcp.flavors.gcp_artifact_store_flavor import (
    GCPArtifactStoreConfig,
)


def test_gcp_artifact_store_attributes():
    """Tests that the basic attributes of the gcp artifact store are set
    correctly."""
    artifact_store = GCPArtifactStore(
        name="",
        id=uuid4(),
        config=GCPArtifactStoreConfig(path="gs://tmp"),
        flavor="gcp",
        type=StackComponentType.ARTIFACT_STORE,
        user=uuid4(),
        project=uuid4(),
    )
    assert artifact_store.type == StackComponentType.ARTIFACT_STORE
    assert artifact_store.flavor == "gcp"


def test_must_be_gcs_path():
    """Checks that a gcp artifact store can only be initialized with a gcs
    path."""
    with pytest.raises(ArtifactStoreInterfaceError):
        GCPArtifactStore(
            name="",
            id=uuid4(),
            config=GCPArtifactStoreConfig(path="/local/path"),
            flavor="gcp",
            type=StackComponentType.ARTIFACT_STORE,
            user=uuid4(),
            project=uuid4(),
        )

    with pytest.raises(ArtifactStoreInterfaceError):
        GCPArtifactStore(
            name="",
            id=uuid4(),
            config=GCPArtifactStoreConfig(path="s3://local/path"),
            flavor="gcp",
            type=StackComponentType.ARTIFACT_STORE,
            user=uuid4(),
            project=uuid4(),
        )

    gcp_path = "gs://mybucket"
    artifact_store = GCPArtifactStore(
        name="",
        id=uuid4(),
        config=GCPArtifactStoreConfig(path=gcp_path),
        flavor="gcp",
        type=StackComponentType.ARTIFACT_STORE,
        user=uuid4(),
        project=uuid4(),
    )

    assert artifact_store.path == gcp_path
