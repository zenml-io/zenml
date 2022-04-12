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


import pytest

from zenml.enums import StackComponentType
from zenml.exceptions import ArtifactStoreInterfaceError
from zenml.integrations.azure.artifact_stores.azure_artifact_store import (
    AzureArtifactStore,
)


def test_azure_artifact_store_attributes():
    """Tests that the basic attributes of the azure artifact store are set
    correctly."""
    artifact_store = AzureArtifactStore(name="", path="az://tmp")
    assert artifact_store.TYPE == StackComponentType.ARTIFACT_STORE
    assert artifact_store.FLAVOR == "azure"


def test_must_be_azure_path():
    """Checks that an azure artifact store can only be initialized with a valid
    path."""
    with pytest.raises(ArtifactStoreInterfaceError):
        AzureArtifactStore(name="", path="/local/path")

    with pytest.raises(ArtifactStoreInterfaceError):
        AzureArtifactStore(name="", path="s3://mybucket")

    artifact_store = AzureArtifactStore(name="", path="az://mycontainer")
    assert artifact_store.path == "az://mycontainer"

    artifact_store = AzureArtifactStore(name="", path="abfs://mycontainer")
    assert artifact_store.path == "abfs://mycontainer"
