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

import os
from datetime import datetime
from uuid import uuid4

import pytest

from zenml.artifact_stores import LocalArtifactStore, LocalArtifactStoreConfig
from zenml.enums import StackComponentType
from zenml.exceptions import ArtifactStoreInterfaceError


def test_local_artifact_store_attributes():
    """Tests that the basic attributes of the local artifact store are set correctly."""
    artifact_store = LocalArtifactStore(
        name="",
        id=uuid4(),
        config=LocalArtifactStoreConfig(),
        flavor="default",
        type=StackComponentType.ARTIFACT_STORE,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )
    assert artifact_store.type == StackComponentType.ARTIFACT_STORE
    assert artifact_store.flavor == "default"


def test_local_artifact_store_only_supports_local_paths():
    """Checks that a local artifact store can only be initialized with a local
    path."""
    with pytest.raises(ArtifactStoreInterfaceError):
        LocalArtifactStore(
            name="",
            id=uuid4(),
            config=LocalArtifactStoreConfig(path="gs://remote/path"),
            flavor="default",
            type=StackComponentType.ARTIFACT_STORE,
            user=uuid4(),
            created=datetime.now(),
            updated=datetime.now(),
        )

    with pytest.raises(ArtifactStoreInterfaceError):
        LocalArtifactStore(
            name="",
            id=uuid4(),
            config=LocalArtifactStoreConfig(path="s3://remote/path"),
            flavor="default",
            type=StackComponentType.ARTIFACT_STORE,
            user=uuid4(),
            created=datetime.now(),
            updated=datetime.now(),
        )

    with pytest.raises(ArtifactStoreInterfaceError):
        LocalArtifactStore(
            name="",
            id=uuid4(),
            config=LocalArtifactStoreConfig(path="hdfs://remote/path"),
            flavor="default",
            type=StackComponentType.ARTIFACT_STORE,
            user=uuid4(),
            created=datetime.now(),
            updated=datetime.now(),
        )

    artifact_store = LocalArtifactStore(
        name="",
        id=uuid4(),
        config=LocalArtifactStoreConfig(path=os.getcwd()),
        flavor="default",
        type=StackComponentType.ARTIFACT_STORE,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )
    assert artifact_store.path == os.getcwd()
