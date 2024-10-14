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
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from zenml.enums import StackComponentType
from zenml.exceptions import ArtifactStoreInterfaceError
from zenml.integrations.s3.artifact_stores.s3_artifact_store import (
    S3ArtifactStore,
)
from zenml.integrations.s3.flavors.s3_artifact_store_flavor import (
    S3ArtifactStoreConfig,
)


def test_s3_artifact_store_attributes():
    """Tests that the basic attributes of the s3 artifact store are set correctly."""
    with patch("boto3.resource", MagicMock()):
        artifact_store = S3ArtifactStore(
            name="",
            id=uuid4(),
            config=S3ArtifactStoreConfig(path="s3://tmp"),
            flavor="s3",
            type=StackComponentType.ARTIFACT_STORE,
            user=uuid4(),
            workspace=uuid4(),
            created=datetime.now(),
            updated=datetime.now(),
        )
    assert artifact_store.type == StackComponentType.ARTIFACT_STORE
    assert artifact_store.flavor == "s3"


def test_must_be_s3_path():
    """Checks that a s3 artifact store can only be initialized with a s3 path."""
    with patch("boto3.resource", MagicMock()):
        with pytest.raises(ArtifactStoreInterfaceError):
            S3ArtifactStore(
                name="",
                id=uuid4(),
                config=S3ArtifactStoreConfig(path="/local/path"),
                flavor="s3",
                type=StackComponentType.ARTIFACT_STORE,
                user=uuid4(),
                workspace=uuid4(),
                created=datetime.now(),
                updated=datetime.now(),
            )

        with pytest.raises(ArtifactStoreInterfaceError):
            S3ArtifactStore(
                name="",
                id=uuid4(),
                config=S3ArtifactStoreConfig(path="gs://mybucket"),
                flavor="s3",
                type=StackComponentType.ARTIFACT_STORE,
                user=uuid4(),
                workspace=uuid4(),
                created=datetime.now(),
                updated=datetime.now(),
            )

        artifact_store = S3ArtifactStore(
            name="",
            id=uuid4(),
            config=S3ArtifactStoreConfig(path="s3://mybucket"),
            flavor="s3",
            type=StackComponentType.ARTIFACT_STORE,
            user=uuid4(),
            workspace=uuid4(),
            created=datetime.now(),
            updated=datetime.now(),
        )
    assert artifact_store.path == "s3://mybucket"
