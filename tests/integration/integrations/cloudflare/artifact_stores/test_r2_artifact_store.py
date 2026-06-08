#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from zenml.enums import StackComponentType
from zenml.exceptions import ArtifactStoreInterfaceError
from zenml.integrations.cloudflare.artifact_stores.r2_artifact_store import (
    R2ArtifactStore,
)
from zenml.integrations.cloudflare.flavors.cloudflare_r2_artifact_store_flavor import (
    R2ArtifactStoreConfig,
)


def _make_store(path: str = "r2://my-bucket") -> R2ArtifactStore:
    """Builds an R2 artifact store with a mocked filesystem.

    Args:
        path: The R2 path to configure the store with.

    Returns:
        An R2 artifact store whose `filesystem` is a `MagicMock`.
    """
    store = R2ArtifactStore(
        name="",
        id=uuid4(),
        config=R2ArtifactStoreConfig(path=path, account_id="abc123"),
        flavor="r2",
        type=StackComponentType.ARTIFACT_STORE,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )
    store._filesystem = MagicMock()
    # Avoid the credential/connector refresh path in the filesystem property.
    store.connector_has_expired = lambda: False  # type: ignore[method-assign]
    return store


def test_r2_store_attributes():
    """The R2 store does not probe bucket versioning on construction."""
    store = _make_store()
    assert store.type == StackComponentType.ARTIFACT_STORE
    assert store.flavor == "r2"
    # R2 never exposes the S3 versioning API.
    assert store.is_versioned is False


def test_must_be_r2_path():
    """The R2 store only accepts `r2://` paths."""
    for bad_path in ("/local/path", "s3://mybucket", "gs://mybucket"):
        with pytest.raises(ArtifactStoreInterfaceError):
            R2ArtifactStore(
                name="",
                id=uuid4(),
                config=R2ArtifactStoreConfig(
                    path=bad_path, account_id="abc123"
                ),
                flavor="r2",
                type=StackComponentType.ARTIFACT_STORE,
                user=uuid4(),
                created=datetime.now(),
                updated=datetime.now(),
            )


def test_scheme_stripped_before_filesystem():
    """`r2://` is stripped before paths reach the s3fs filesystem."""
    store = _make_store()

    store.open("r2://my-bucket/file.txt", mode="rb")
    store.filesystem.open.assert_called_once_with(
        path="my-bucket/file.txt", mode="rb"
    )

    store.exists("r2://my-bucket/file.txt")
    store.filesystem.exists.assert_called_once_with(path="my-bucket/file.txt")

    store.remove("r2://my-bucket/file.txt")
    store.filesystem.rm_file.assert_called_once_with(path="my-bucket/file.txt")


def test_glob_reprefixes_results_with_r2_scheme():
    """Glob strips the input scheme and re-adds `r2://` to results."""
    store = _make_store()
    store.filesystem.glob.return_value = [
        "my-bucket/a.txt",
        "my-bucket/b.txt",
    ]

    result = store.glob("r2://my-bucket/*.txt")

    store.filesystem.glob.assert_called_once_with(path="my-bucket/*.txt")
    assert result == ["r2://my-bucket/a.txt", "r2://my-bucket/b.txt"]


def test_walk_reprefixes_directories_with_r2_scheme():
    """Walk strips the input scheme and re-adds `r2://` to directories."""
    store = _make_store()
    store.filesystem.walk.return_value = [
        ("my-bucket/dir", ["sub"], ["f.txt"]),
    ]

    result = list(store.walk("r2://my-bucket/dir"))

    store.filesystem.walk.assert_called_once_with(path="my-bucket/dir")
    assert result == [("r2://my-bucket/dir", ["sub"], ["f.txt"])]
