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
"""Tests for the S3 artifact store."""

import asyncio
import io
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from botocore.exceptions import ClientError

from zenml.artifact_stores import ObjectInfo
from zenml.enums import StackComponentType
from zenml.exceptions import ArtifactStoreInterfaceError
from zenml.integrations.s3.artifact_stores.s3_artifact_store import (
    S3ArtifactStore,
    ZenMLS3Filesystem,
)
from zenml.integrations.s3.flavors.s3_artifact_store_flavor import (
    S3ArtifactStoreConfig,
)


class _FakePaginator:
    """Fake boto3 paginator that records pagination calls."""

    def __init__(self, pages: List[Dict[str, Any]]) -> None:
        self.pages = pages
        self.calls: List[Dict[str, Any]] = []

    def paginate(self, **kwargs: Any) -> List[Dict[str, Any]]:
        """Record and return configured pages."""
        self.calls.append(kwargs)
        return self.pages


class _FakeS3Client:
    """Fake S3 client for mocked native artifact-store tests."""

    def __init__(self) -> None:
        self.paginators: Dict[str, _FakePaginator] = {}
        self.delete_calls: List[Dict[str, Any]] = []
        self.delete_responses: List[Dict[str, Any]] = []
        self.get_object_calls: List[Dict[str, Any]] = []
        self.get_object_bodies: List[bytes] = []
        self.download_calls: List[Dict[str, Any]] = []

    def get_paginator(self, name: str) -> _FakePaginator:
        """Return a configured fake paginator."""
        return self.paginators[name]

    def delete_objects(self, **kwargs: Any) -> Dict[str, Any]:
        """Record delete calls and return queued responses."""
        self.delete_calls.append(kwargs)
        if self.delete_responses:
            return self.delete_responses.pop(0)
        return {"Deleted": kwargs["Delete"]["Objects"]}

    def get_object(self, **kwargs: Any) -> Dict[str, Any]:
        """Record ranged get calls and return queued bytes."""
        self.get_object_calls.append(kwargs)
        return {"Body": io.BytesIO(self.get_object_bodies.pop(0))}

    def download_file(self, **kwargs: Any) -> None:
        """Record transfer downloads and write a small local file."""
        self.download_calls.append(kwargs)
        with open(kwargs["Filename"], "wb") as file:
            file.write(kwargs["Key"].encode())


def _get_mocked_s3_artifact_store(
    client: _FakeS3Client, path: str = "s3://bucket/root"
) -> S3ArtifactStore:
    """Create an S3 artifact store wired to a fake native S3 client."""
    with patch("boto3.resource") as mock_resource:
        bucket = MagicMock()
        bucket.Versioning.return_value.status = "Disabled"
        mock_resource.return_value.Bucket.return_value = bucket
        artifact_store = S3ArtifactStore(
            name="",
            id=uuid4(),
            config=S3ArtifactStoreConfig(path=path),
            flavor="s3",
            type=StackComponentType.ARTIFACT_STORE,
            user=uuid4(),
            created=datetime.now(),
            updated=datetime.now(),
        )

    artifact_store._boto3_client_holder = client
    return artifact_store


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


def test_boto3_client_receives_client_kwargs():
    """Tests that native S3 clients preserve configured endpoint kwargs."""
    with (
        patch("boto3.resource") as mock_resource,
        patch("boto3.client") as mock_client,
    ):
        bucket = MagicMock()
        bucket.Versioning.return_value.status = "Disabled"
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

        _ = artifact_store._boto3_client

    assert mock_client.call_args.args == ("s3",)
    assert mock_client.call_args.kwargs["endpoint_url"] == "http://minio:9000"


def test_boto3_client_receives_config_kwargs():
    """Tests that native S3 clients preserve botocore config kwargs."""
    with (
        patch("boto3.resource") as mock_resource,
        patch("boto3.client") as mock_client,
    ):
        bucket = MagicMock()
        bucket.Versioning.return_value.status = "Disabled"
        mock_resource.return_value.Bucket.return_value = bucket

        artifact_store = S3ArtifactStore(
            name="",
            id=uuid4(),
            config=S3ArtifactStoreConfig(
                path="s3://mybucket",
                config_kwargs={"s3": {"addressing_style": "path"}},
            ),
            flavor="s3",
            type=StackComponentType.ARTIFACT_STORE,
            user=uuid4(),
            created=datetime.now(),
            updated=datetime.now(),
        )

        _ = artifact_store._boto3_client

    config = mock_client.call_args.kwargs["config"]
    assert config.s3 == {"addressing_style": "path"}


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


def test_list_objects_uses_native_s3_listing_and_metadata():
    """Tests S3 list_objects returns direct children and metadata."""
    last_modified = datetime.now()
    client = _FakeS3Client()
    paginator = _FakePaginator(
        pages=[
            {
                "Contents": [
                    {
                        "Key": "root/logs/1.log",
                        "Size": 3,
                        "ETag": '"etag-1"',
                        "LastModified": last_modified,
                    },
                    {
                        "Key": "root/logs/nested/2.log",
                        "Size": 3,
                        "ETag": '"etag-2"',
                    },
                    {"Key": "root/logs2/3.log", "Size": 5},
                    {"Key": "root/logs/", "Size": 0},
                ]
            }
        ]
    )
    client.paginators["list_objects_v2"] = paginator
    artifact_store = _get_mocked_s3_artifact_store(client)

    objects = list(artifact_store.list_objects("s3://bucket/root/logs"))

    assert paginator.calls == [{"Bucket": "bucket", "Prefix": "root/logs"}]
    assert [object_info.relative_path for object_info in objects] == ["1.log"]
    assert objects[0].uri == "s3://bucket/root/logs/1.log"
    assert objects[0].size == 3
    assert objects[0].etag == '"etag-1"'
    assert objects[0].last_modified == last_modified

    recursive_objects = list(
        artifact_store.list_objects("s3://bucket/root/logs", recursive=True)
    )

    assert [
        object_info.relative_path for object_info in recursive_objects
    ] == ["1.log", "nested/2.log"]


def test_list_objects_at_bucket_root_preserves_relative_paths():
    """Tests bucket-root S3 listings keep nested relative paths intact."""
    client = _FakeS3Client()
    client.paginators["list_objects_v2"] = _FakePaginator(
        pages=[
            {
                "Contents": [
                    {"Key": "a/file.txt", "Size": 1},
                    {"Key": "b/file.txt", "Size": 1},
                    {"Key": "top.log", "Size": 3},
                ]
            }
        ]
    )
    artifact_store = _get_mocked_s3_artifact_store(
        client, path="s3://bucket"
    )

    objects = list(artifact_store.list_objects("s3://bucket"))
    recursive_objects = list(
        artifact_store.list_objects("s3://bucket", recursive=True)
    )

    assert [object_info.relative_path for object_info in objects] == [
        "top.log"
    ]
    assert [
        object_info.relative_path for object_info in recursive_objects
    ] == ["a/file.txt", "b/file.txt", "top.log"]


def test_delete_objects_batches_native_s3_deletes_and_reports_failures():
    """Tests S3 delete_objects chunks requests and preserves failures."""
    client = _FakeS3Client()
    first_batch_deleted = [
        {"Key": f"root/file-{index:04d}.txt"} for index in range(1000)
    ]
    client.delete_responses = [
        {"Deleted": first_batch_deleted},
        {
            "Errors": [
                {
                    "Key": "root/file-1000.txt",
                    "Code": "AccessDenied",
                    "Message": "denied",
                }
            ]
        },
    ]
    artifact_store = _get_mocked_s3_artifact_store(client)
    paths = [
        f"s3://bucket/root/file-{index:04d}.txt" for index in range(1001)
    ]

    result = artifact_store.delete_objects(paths)

    assert len(client.delete_calls) == 2
    assert len(client.delete_calls[0]["Delete"]["Objects"]) == 1000
    assert client.delete_calls[1]["Delete"]["Objects"] == [
        {"Key": "root/file-1000.txt"}
    ]
    assert len(result.deleted_paths) == 1000
    assert [failure.path for failure in result.failures] == [
        "s3://bucket/root/file-1000.txt"
    ]


def test_delete_objects_handles_mixed_success_and_errors():
    """Tests one S3 delete response can include successes and failures."""
    client = _FakeS3Client()
    client.delete_responses = [
        {
            "Deleted": [{"Key": "root/a.txt"}],
            "Errors": [
                {
                    "Key": "root/b.txt",
                    "Code": "AccessDenied",
                    "Message": "denied",
                }
            ],
        }
    ]
    artifact_store = _get_mocked_s3_artifact_store(client)

    result = artifact_store.delete_objects(
        ["s3://bucket/root/a.txt", "s3://bucket/root/b.txt"]
    )

    assert result.deleted_paths == ["s3://bucket/root/a.txt"]
    assert [failure.path for failure in result.failures] == [
        "s3://bucket/root/b.txt"
    ]


def test_read_range_uses_native_s3_range_header():
    """Tests S3 read_range sends the expected HTTP range header."""
    client = _FakeS3Client()
    client.get_object_bodies = [b"bcd", b"def"]
    artifact_store = _get_mocked_s3_artifact_store(client)

    assert (
        artifact_store.read_range(
            "s3://bucket/root/file.txt", offset=1, length=3
        )
        == b"bcd"
    )
    assert (
        artifact_store.read_range("s3://bucket/root/file.txt", offset=3)
        == b"def"
    )
    assert artifact_store.read_range(
        "s3://bucket/root/file.txt", offset=3, length=0
    ) == b""

    assert client.get_object_calls == [
        {"Bucket": "bucket", "Key": "root/file.txt", "Range": "bytes=1-3"},
        {"Bucket": "bucket", "Key": "root/file.txt", "Range": "bytes=3-"},
    ]


def test_download_objects_to_directory_uses_boto3_transfers(tmp_path):
    """Tests S3 download_objects_to_directory preserves relative paths."""
    client = _FakeS3Client()
    artifact_store = _get_mocked_s3_artifact_store(client)
    objects = [
        ObjectInfo(
            uri="s3://bucket/root/a.txt",
            relative_path="a.txt",
        ),
        ObjectInfo(
            uri="s3://bucket/root/nested/b.txt",
            relative_path="nested/b.txt",
        ),
    ]

    handled = artifact_store.download_objects_to_directory(
        objects, str(tmp_path), max_workers=1
    )

    assert handled is True
    assert (tmp_path / "a.txt").read_bytes() == b"root/a.txt"
    assert (tmp_path / "nested" / "b.txt").read_bytes() == b"root/nested/b.txt"
    assert [call["Key"] for call in client.download_calls] == [
        "root/a.txt",
        "root/nested/b.txt",
    ]


def test_download_objects_to_directory_rejects_path_traversal(tmp_path):
    """Tests S3 transfer downloads cannot escape the local target."""
    client = _FakeS3Client()
    artifact_store = _get_mocked_s3_artifact_store(client)

    with pytest.raises(ValueError, match="escapes"):
        artifact_store.download_objects_to_directory(
            [
                ObjectInfo(
                    uri="s3://bucket/root/a.txt",
                    relative_path="../a.txt",
                )
            ],
            str(tmp_path),
            max_workers=1,
        )


def test_remove_previous_file_versions_batches_versioned_deletes():
    """Tests versioned S3 cleanup deletes old version IDs in batches."""
    client = _FakeS3Client()
    paginator = _FakePaginator(
        pages=[
            {
                "Versions": [
                    {
                        "Key": "root/log.txt",
                        "VersionId": "latest",
                        "IsLatest": True,
                    },
                    {
                        "Key": "root/log.txt",
                        "VersionId": "old-version",
                        "IsLatest": False,
                    },
                    {
                        "Key": "root/log.txt.backup",
                        "VersionId": "backup-old-version",
                        "IsLatest": False,
                    },
                ],
                "DeleteMarkers": [
                    {
                        "Key": "root/log.txt",
                        "VersionId": "old-marker",
                        "IsLatest": False,
                    },
                    {
                        "Key": "root/log.txt.backup",
                        "VersionId": "backup-old-marker",
                        "IsLatest": False,
                    },
                ],
            }
        ]
    )
    client.paginators["list_object_versions"] = paginator
    artifact_store = _get_mocked_s3_artifact_store(client)
    artifact_store.is_versioned = True

    artifact_store._remove_previous_file_versions("s3://bucket/root/log.txt")

    assert paginator.calls == [
        {"Bucket": "bucket", "Prefix": "root/log.txt"}
    ]
    assert client.delete_calls == [
        {
            "Bucket": "bucket",
            "Delete": {
                "Objects": [
                    {"Key": "root/log.txt", "VersionId": "old-version"},
                    {"Key": "root/log.txt", "VersionId": "old-marker"},
                ],
                "Quiet": False,
            },
        }
    ]


def test_versioning_permission_shield_reraises_unrelated_client_errors():
    """Tests unrelated S3 ClientErrors are not silently swallowed."""
    artifact_store = _get_mocked_s3_artifact_store(_FakeS3Client())
    error = ClientError(
        {"Error": {"Code": "NoSuchBucket", "Message": "missing bucket"}},
        "ListObjectVersions",
    )

    with pytest.raises(ClientError, match="NoSuchBucket"):
        with artifact_store._shield_lack_of_versioning_permissions(
            "s3:ListBucketVersions"
        ):
            raise error


def test_versioning_permission_shield_suppresses_access_denied():
    """Tests missing versioning permissions disable versioned cleanup."""
    artifact_store = _get_mocked_s3_artifact_store(_FakeS3Client())
    artifact_store.is_versioned = True
    error = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "denied"}},
        "ListObjectVersions",
    )

    with artifact_store._shield_lack_of_versioning_permissions(
        "s3:ListBucketVersions"
    ):
        raise error

    assert artifact_store.is_versioned is False


class _StubS3Creator:
    """Simulates an aiobotocore async context manager that crashes on double-close."""

    def __init__(self) -> None:
        self.exit_count = 0

    async def __aexit__(self, *args: object) -> None:
        """Raises AssertionError on second exit, like aiobotocore 3.x."""
        self.exit_count += 1
        if self.exit_count > 1:
            raise AssertionError("Session was never entered")


def test_explicit_close_then_finalizer_does_not_raise() -> None:
    """Regression test for #4586: double-close must not raise."""
    fs = ZenMLS3Filesystem.__new__(ZenMLS3Filesystem)
    creator = _StubS3Creator()
    fs._s3creator = creator
    fs._s3 = MagicMock()

    loop = asyncio.new_event_loop()
    try:
        # First close: explicit cleanup (what S3ArtifactStore.cleanup does)
        loop.run_until_complete(fs._close())
        assert fs._s3creator is None
        assert creator.exit_count == 1

        # Second close: simulates the weakref finalizer firing while the
        # loop is running (close_session checks loop.is_running()).
        async def _simulate_finalizer() -> None:
            ZenMLS3Filesystem.close_session(loop, creator)
            await asyncio.sleep(0)  # let the scheduled task run

        loop.run_until_complete(_simulate_finalizer())
        assert creator.exit_count == 2
    finally:
        loop.close()


def test_close_session_called_twice_does_not_raise() -> None:
    """close_session tolerates being called twice on the same creator."""
    creator = _StubS3Creator()

    loop = asyncio.new_event_loop()
    try:

        async def _call_close_session_twice() -> None:
            ZenMLS3Filesystem.close_session(loop, creator)
            await asyncio.sleep(0)
            assert creator.exit_count == 1

            ZenMLS3Filesystem.close_session(loop, creator)
            await asyncio.sleep(0)
            assert creator.exit_count == 2

        loop.run_until_complete(_call_close_session_twice())
    finally:
        loop.close()


def test_safe_aexit_propagates_unrelated_assertion_errors() -> None:
    """Assertion errors that aren't the double-close case must still propagate."""
    creator = AsyncMock()
    creator.__aexit__ = AsyncMock(
        side_effect=AssertionError("Something else broke")
    )

    with pytest.raises(AssertionError, match="Something else broke"):
        asyncio.get_event_loop().run_until_complete(
            ZenMLS3Filesystem._safe_aexit_s3_creator(creator)
        )
