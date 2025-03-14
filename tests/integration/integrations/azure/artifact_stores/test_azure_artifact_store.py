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

from datetime import datetime
from uuid import uuid4

import pytest

from zenml.enums import StackComponentType
from zenml.exceptions import ArtifactStoreInterfaceError
from zenml.integrations.azure.artifact_stores.azure_artifact_store import (
    AzureArtifactStore,
)
from zenml.integrations.azure.flavors.azure_artifact_store_flavor import (
    AzureArtifactStoreConfig,
)


def test_azure_artifact_store_attributes():
    """Tests that the basic attributes of the azure artifact store are set correctly."""
    artifact_store = AzureArtifactStore(
        name="",
        id=uuid4(),
        config=AzureArtifactStoreConfig(path="az://mycontainer"),
        flavor="azure",
        type=StackComponentType.ARTIFACT_STORE,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )
    assert artifact_store.type == StackComponentType.ARTIFACT_STORE
    assert artifact_store.flavor == "azure"


def test_must_be_azure_path():
    """Checks that an azure artifact store can only be initialized with a valid
    path."""
    with pytest.raises(ArtifactStoreInterfaceError):
        AzureArtifactStore(
            name="",
            id=uuid4(),
            config=AzureArtifactStoreConfig(path="/local/path"),
            flavor="azure",
            type=StackComponentType.ARTIFACT_STORE,
            user=uuid4(),
            created=datetime.now(),
            updated=datetime.now(),
        )

    with pytest.raises(ArtifactStoreInterfaceError):
        AzureArtifactStore(
            name="",
            id=uuid4(),
            config=AzureArtifactStoreConfig(path="s3://mybucket"),
            flavor="azure",
            type=StackComponentType.ARTIFACT_STORE,
            user=uuid4(),
            created=datetime.now(),
            updated=datetime.now(),
        )

    artifact_store = AzureArtifactStore(
        name="",
        id=uuid4(),
        config=AzureArtifactStoreConfig(path="az://mycontainer"),
        flavor="azure",
        type=StackComponentType.ARTIFACT_STORE,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )
    assert artifact_store.path == "az://mycontainer"

    artifact_store = AzureArtifactStore(
        name="",
        id=uuid4(),
        config=AzureArtifactStoreConfig(path="abfs://mycontainer"),
        flavor="azure",
        type=StackComponentType.ARTIFACT_STORE,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )
    assert artifact_store.path == "abfs://mycontainer"
