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

"""Tests for the S3 artifact store implementation."""

from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from zenml.enums import StackComponentType
from zenml.exceptions import ArtifactStoreInterfaceError
from zenml.integrations.s3.artifact_stores.s3_artifact_store import (
    S3ArtifactStore,
    ZenMLS3Filesystem,
)
from zenml.integrations.s3.flavors.s3_artifact_store_flavor import (
    S3ArtifactStoreConfig,
)


class _CloseFailingWriteHandle:
    """Write handle that raises on close after storing written bytes."""

    def __init__(self) -> None:
        self.close_calls = 0
        self.closed = False
        self.data = b""

    def write(self, data: bytes) -> int:
        """Stores written data.

        Args:
            data: Data to write.

        Returns:
            Number of bytes written.
        """
        self.data += data
        return len(data)

    def close(self) -> None:
        """Raises a missing temp file error on close."""
        self.close_calls += 1
        raise FileNotFoundError(
            2, "No such file or directory", "/tmp/tmp-s3-upload"  # nosec B108
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
            created=datetime.now(),
            updated=datetime.now(),
        )
    assert artifact_store.path == "s3://mybucket"


def test_boto3_resource_receives_client_kwargs():
    """Tests that boto3.resource receives client_kwargs during initialization."""
    with patch("boto3.resource") as mock_resource:
        bucket = MagicMock()
        bucket.Versioning.return_value.status = "Enabled"
        mock_resource.return_value.Bucket.return_value = bucket

        S3ArtifactStore(
            name="",
            id=uuid4(),
            config=S3ArtifactStoreConfig(
                path="s3://custom",
                client_kwargs={
                    "endpoint_url": "http://minio:9000",
                    "foo": "bar",
                },
            ),
            flavor="s3",
            type=StackComponentType.ARTIFACT_STORE,
            user=uuid4(),
            created=datetime.now(),
            updated=datetime.now(),
        )

    assert (
        mock_resource.call_args.kwargs["endpoint_url"] == "http://minio:9000"
    )
    assert mock_resource.call_args.kwargs["foo"] == "bar"


def test_remove_previous_versions_uses_client_kwargs():
    """Tests that _remove_previous_file_versions uses client_kwargs when creating boto3 resource."""
    with patch("boto3.resource") as mock_resource:
        bucket = MagicMock()
        bucket.Versioning.return_value.status = "Enabled"
        bucket.object_versions.filter.return_value = []
        mock_resource.return_value.Bucket.return_value = bucket

        artifact_store = S3ArtifactStore(
            name="",
            id=uuid4(),
            config=S3ArtifactStoreConfig(
                path="s3://mybucket",
                client_kwargs={"endpoint_url": "http://minio:9000"},
            ),
            flavor="s3",
            type=StackComponentType.ARTIFACT_STORE,
            user=uuid4(),
            created=datetime.now(),
            updated=datetime.now(),
        )

        artifact_store.is_versioned = True
        artifact_store._boto3_bucket_holder = None

        artifact_store._remove_previous_file_versions("s3://mybucket/path")

    assert len(mock_resource.call_args_list) == 2
    for call in mock_resource.call_args_list:
        assert call.kwargs["endpoint_url"] == "http://minio:9000"


def test_client_kwargs_region_overrides_credentials_region():
    """Tests that client_kwargs region_name takes precedence over credential region."""
    with (
        patch(
            "zenml.integrations.s3.artifact_stores.s3_artifact_store.S3ArtifactStore.get_credentials",
            return_value=("key", "secret", "token", "us-west-2"),
        ),
        patch("boto3.resource") as mock_resource,
    ):
        bucket = MagicMock()
        bucket.Versioning.return_value.status = "Enabled"
        mock_resource.return_value.Bucket.return_value = bucket

        artifact_store = S3ArtifactStore(
            name="",
            id=uuid4(),
            config=S3ArtifactStoreConfig(
                path="s3://override-region",
                client_kwargs={
                    "endpoint_url": "http://minio",
                    "region_name": "eu-central-1",
                },
            ),
            flavor="s3",
            type=StackComponentType.ARTIFACT_STORE,
            user=uuid4(),
            created=datetime.now(),
            updated=datetime.now(),
        )

        _ = artifact_store._boto3_bucket

    assert mock_resource.call_args.kwargs["region_name"] == "eu-central-1"
    assert mock_resource.call_args.kwargs["aws_access_key_id"] == "key"
    assert mock_resource.call_args.kwargs["aws_secret_access_key"] == "secret"
    assert mock_resource.call_args.kwargs["aws_session_token"] == "token"


def test_s3_open_write_ignores_missing_temp_file_if_remote_exists() -> None:
    """Tests S3 write close does not fail if backend temp file was already removed."""
    filesystem = ZenMLS3Filesystem.__new__(ZenMLS3Filesystem)
    write_handle = _CloseFailingWriteHandle()

    with (
        patch.object(
            filesystem,
            "exists",
            return_value=True,
        ) as mock_exists,
        patch(
            "zenml.integrations.s3.artifact_stores."
            "s3_artifact_store.s3fs.S3FileSystem.open",
            return_value=write_handle,
        ),
    ):
        wrapped_file = filesystem.open(path="s3://bucket/path", mode="wb")
        wrapped_file.write(b"payload")
        wrapped_file.close()
        wrapped_file.close()

    assert write_handle.data == b"payload"
    assert write_handle.close_calls == 1
    assert mock_exists.call_count == 1


def test_s3_open_write_raises_missing_temp_file_if_remote_missing() -> None:
    """Tests S3 write close still fails if the remote file does not exist."""
    filesystem = ZenMLS3Filesystem.__new__(ZenMLS3Filesystem)
    write_handle = _CloseFailingWriteHandle()

    with (
        patch.object(filesystem, "exists", return_value=False),
        patch(
            "zenml.integrations.s3.artifact_stores."
            "s3_artifact_store.s3fs.S3FileSystem.open",
            return_value=write_handle,
        ),
    ):
        wrapped_file = filesystem.open(path="s3://bucket/path", mode="wb")
        wrapped_file.write(b"payload")

        with pytest.raises(FileNotFoundError):
            wrapped_file.close()

    assert write_handle.close_calls == 1
