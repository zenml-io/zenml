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
"""Tests for Azure artifact store behavior."""

import sys
from datetime import datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, Dict, List, Optional
from uuid import uuid4

import pytest


class _DummyAzureBlobFileSystem:
    """Import-time stand-in for the optional adlfs filesystem class."""


adlfs_module = ModuleType("adlfs")
adlfs_module.AzureBlobFileSystem = _DummyAzureBlobFileSystem  # type: ignore[attr-defined]
sys.modules.setdefault("adlfs", adlfs_module)

from zenml.artifact_stores import ObjectInfo  # noqa: E402
from zenml.enums import StackComponentType  # noqa: E402
from zenml.exceptions import ArtifactStoreInterfaceError  # noqa: E402
from zenml.integrations.azure.artifact_stores.azure_artifact_store import (  # noqa: E402
    AzureArtifactStore,
)
from zenml.integrations.azure.flavors.azure_artifact_store_flavor import (  # noqa: E402
    AzureArtifactStoreConfig,
)


class ResourceExistsError(Exception):
    """Fake Azure resource-exists exception."""


class ResourceNotFoundError(Exception):
    """Fake Azure resource-not-found exception."""


@pytest.fixture(autouse=True)
def _mock_azure_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide Azure exception classes without requiring Azure SDK installs."""
    azure_module = ModuleType("azure")
    core_module = ModuleType("azure.core")
    exceptions_module = ModuleType("azure.core.exceptions")
    exceptions_module.ResourceExistsError = ResourceExistsError  # type: ignore[attr-defined]
    exceptions_module.ResourceNotFoundError = ResourceNotFoundError  # type: ignore[attr-defined]
    core_module.exceptions = exceptions_module  # type: ignore[attr-defined]
    azure_module.core = core_module  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "azure", azure_module)
    monkeypatch.setitem(sys.modules, "azure.core", core_module)
    monkeypatch.setitem(
        sys.modules, "azure.core.exceptions", exceptions_module
    )


class _FakeDownload:
    """In-memory Azure blob download response."""

    def __init__(self, content: bytes) -> None:
        """Initialize a fake download response."""
        self.content = content

    def readall(self) -> bytes:
        """Return all downloaded bytes."""
        return self.content


class _FakeBlobClient:
    """In-memory stand-in for an Azure BlobClient."""

    def __init__(self, container: "_FakeContainerClient", name: str) -> None:
        """Initialize the fake blob client."""
        self.container = container
        self.name = name
        self.download_calls: List[Dict[str, Optional[int]]] = []

    def get_blob_properties(self):  # type: ignore[no-untyped-def]
        """Return fake blob properties or raise if the blob is absent."""
        if self.name not in self.container.objects:
            raise ResourceNotFoundError("missing")

        return SimpleNamespace(
            blob_type=self.container.blob_types.get(self.name, "BlockBlob"),
            append_blob_committed_block_count=self.container.append_counts.get(
                self.name, 0
            ),
        )

    def create_append_blob(self) -> None:
        """Create an empty append blob."""
        self.container.create_append_blob_calls.append(self.name)
        if self.name in self.container.objects:
            raise ResourceExistsError("exists")

        self.container.objects[self.name] = b""
        self.container.blob_types[self.name] = "AppendBlob"
        self.container.append_counts[self.name] = 0

    def append_block(self, data: bytes) -> None:
        """Append bytes to the fake append blob."""
        self.container.append_block_calls.append((self.name, data))
        self.container.objects[self.name] += data
        self.container.append_counts[self.name] = (
            self.container.append_counts.get(self.name, 0) + 1
        )

    def download_blob(self, **kwargs):  # type: ignore[no-untyped-def]
        """Download fake blob bytes, optionally using a byte range."""
        self.download_calls.append(kwargs)
        content = self.container.objects[self.name]
        offset = kwargs.get("offset", 0) or 0
        length = kwargs.get("length")
        if length is None:
            return _FakeDownload(content[offset:])
        return _FakeDownload(content[offset : offset + length])


class _FakeContainerClient:
    """In-memory stand-in for an Azure ContainerClient."""

    def __init__(self, objects: Dict[str, bytes]) -> None:
        """Initialize the fake container client."""
        self.objects = objects
        self.blob_types: Dict[str, Any] = {
            name: "BlockBlob" for name in objects
        }
        self.append_counts: Dict[str, int] = {}
        self.list_calls: List[str] = []
        self.delete_batch_calls: List[List[str]] = []
        self.delete_blob_calls: List[str] = []
        self.delete_failures: set[str] = set()
        self.fail_batch_delete = False
        self.create_append_blob_calls: List[str] = []
        self.append_block_calls: List[tuple[str, bytes]] = []

    def list_blobs(self, name_starts_with: str):  # type: ignore[no-untyped-def]
        """List fake blob metadata by prefix."""
        self.list_calls.append(name_starts_with)
        return [
            SimpleNamespace(
                name=name,
                size=len(content),
                etag=f"etag-{name}",
                version_id=f"version-{name}",
                last_modified=datetime(2026, 5, 14),
            )
            for name, content in sorted(self.objects.items())
            if name.startswith(name_starts_with)
        ]

    def delete_blobs(self, *blob_names: str, **kwargs):  # type: ignore[no-untyped-def]
        """Delete fake blobs in a batch."""
        self.delete_batch_calls.append(list(blob_names))
        if self.fail_batch_delete:
            raise RuntimeError("batch failed")

        for blob_name in blob_names:
            self.objects.pop(blob_name, None)
        return [SimpleNamespace(status_code=202) for _ in blob_names]

    def delete_blob(self, blob_name: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """Delete one fake blob."""
        self.delete_blob_calls.append(blob_name)
        if blob_name in self.delete_failures:
            raise RuntimeError("delete failed")
        if blob_name not in self.objects:
            raise ResourceNotFoundError("missing")
        self.objects.pop(blob_name)


class _FakeBlobServiceClient:
    """In-memory stand-in for an Azure BlobServiceClient."""

    def __init__(self, container: _FakeContainerClient) -> None:
        """Initialize the fake blob service client."""
        self.container = container
        self.blob_clients: Dict[str, _FakeBlobClient] = {}

    def get_container_client(
        self, container_name: str
    ) -> _FakeContainerClient:
        """Return the fake container client."""
        assert container_name == "container"
        return self.container

    def get_blob_client(self, container: str, blob: str) -> _FakeBlobClient:
        """Return a stable fake blob client."""
        assert container == "container"
        if blob not in self.blob_clients:
            self.blob_clients[blob] = _FakeBlobClient(
                container=self.container, name=blob
            )
        return self.blob_clients[blob]


class _FakeFilesystem:
    """Small fake adlfs filesystem used to assert append fallback."""

    def __init__(self) -> None:
        """Initialize the fake filesystem."""
        self.open_calls: List[tuple[str, str]] = []
        self.open_return_value = object()

    def open(self, path: str, mode: str):  # type: ignore[no-untyped-def]
        """Record and return a fake file object."""
        self.open_calls.append((path, mode))
        return self.open_return_value


class _FakeBlobType:
    """Azure enum-like blob type with a value attribute."""

    value = "AppendBlob"


def _get_azure_artifact_store(path: str = "az://container/root"):
    """Create an Azure artifact store for tests."""
    return AzureArtifactStore(
        name="",
        id=uuid4(),
        config=AzureArtifactStoreConfig(path=path),
        flavor="azure",
        type=StackComponentType.ARTIFACT_STORE,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def _get_fake_azure_artifact_store(
    container: _FakeContainerClient,
    path: str = "az://container/root",
):
    """Create an Azure artifact store wired to an in-memory blob client."""
    artifact_store = _get_azure_artifact_store(path=path)
    object.__setattr__(
        artifact_store,
        "_blob_service_client",
        _FakeBlobServiceClient(container),
    )
    return artifact_store


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
    """Checks that an azure artifact store can only use valid paths.

    Invalid local and non-Azure remote paths are rejected.
    """
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


def test_list_objects_uses_native_azure_listing_and_metadata():
    """Tests Azure list_objects returns direct children and metadata."""
    container = _FakeContainerClient(
        objects={
            "root/logs/1.log": b"one",
            "root/logs/nested/2.log": b"two",
            "root/logs2/3.log": b"three",
        }
    )
    artifact_store = _get_fake_azure_artifact_store(container)

    objects = list(artifact_store.list_objects("az://container/root/logs"))

    assert container.list_calls == ["root/logs"]
    assert [object_info.relative_path for object_info in objects] == ["1.log"]
    assert objects[0].uri == "az://container/root/logs/1.log"
    assert objects[0].size == 3
    assert objects[0].etag == "etag-root/logs/1.log"
    assert objects[0].version == "version-root/logs/1.log"

    recursive_objects = list(
        artifact_store.list_objects("az://container/root/logs", recursive=True)
    )

    assert [
        object_info.relative_path for object_info in recursive_objects
    ] == [
        "1.log",
        "nested/2.log",
    ]


def test_list_objects_preserves_abfs_scheme_and_bucket_root_paths():
    """Tests Azure listings preserve abfs:// URIs and root relative paths."""
    container = _FakeContainerClient(
        objects={
            "top.log": b"top",
            "a/file.txt": b"a",
            "b/file.txt": b"b",
        }
    )
    artifact_store = _get_fake_azure_artifact_store(
        container, path="abfs://container"
    )

    objects = list(artifact_store.list_objects("abfs://container"))
    recursive_objects = list(
        artifact_store.list_objects("abfs://container", recursive=True)
    )

    assert [object_info.uri for object_info in objects] == [
        "abfs://container/top.log"
    ]
    assert [object_info.relative_path for object_info in objects] == [
        "top.log"
    ]
    assert [
        object_info.relative_path for object_info in recursive_objects
    ] == [
        "a/file.txt",
        "b/file.txt",
        "top.log",
    ]


def test_delete_objects_uses_batch_delete():
    """Tests Azure delete_objects batches native delete requests."""
    container = _FakeContainerClient(
        objects={
            "root/logs/1.log": b"one",
            "root/logs/2.log": b"two",
        }
    )
    artifact_store = _get_fake_azure_artifact_store(container)

    result = artifact_store.delete_objects(
        ["az://container/root/logs/1.log", "az://container/root/logs/2.log"]
    )

    assert result.successful
    assert result.deleted_paths == [
        "az://container/root/logs/1.log",
        "az://container/root/logs/2.log",
    ]
    assert container.delete_batch_calls == [
        ["root/logs/1.log", "root/logs/2.log"]
    ]
    assert container.objects == {}


def test_delete_objects_reports_per_object_failures_after_batch_failure():
    """Tests Azure delete_objects falls back to per-object failure reporting."""
    container = _FakeContainerClient(
        objects={
            "root/logs/1.log": b"one",
            "root/logs/2.log": b"two",
        }
    )
    container.fail_batch_delete = True
    container.delete_failures.add("root/logs/2.log")
    artifact_store = _get_fake_azure_artifact_store(container)

    result = artifact_store.delete_objects(
        ["az://container/root/logs/1.log", "az://container/root/logs/2.log"]
    )

    assert result.deleted_paths == ["az://container/root/logs/1.log"]
    assert [failure.path for failure in result.failures] == [
        "az://container/root/logs/2.log"
    ]
    assert container.delete_blob_calls == [
        "root/logs/1.log",
        "root/logs/2.log",
    ]
    assert container.objects == {"root/logs/2.log": b"two"}


@pytest.mark.parametrize("scheme", ["az://", "abfs://"])
def test_read_range_uses_native_azure_range_download(scheme: str):
    """Tests Azure read_range forwards offset and length to download_blob."""
    container = _FakeContainerClient(objects={"root/file.txt": b"abcdef"})
    artifact_store = _get_fake_azure_artifact_store(
        container, path=f"{scheme}container/root"
    )

    content = artifact_store.read_range(
        f"{scheme}container/root/file.txt", offset=2, length=3
    )

    blob_client = artifact_store.blob_service_client.get_blob_client(
        container="container", blob="root/file.txt"
    )
    assert content == b"cde"
    assert blob_client.download_calls == [{"offset": 2, "length": 3}]


def test_download_objects_to_directory_uses_blob_downloads(tmp_path: Path):
    """Tests Azure download_objects_to_directory preserves relative paths."""
    container = _FakeContainerClient(
        objects={
            "root/file.txt": b"file",
            "root/nested/other.txt": b"other",
        }
    )
    artifact_store = _get_fake_azure_artifact_store(container)
    objects = [
        ObjectInfo(
            uri="az://container/root/file.txt",
            relative_path="file.txt",
            size=4,
        ),
        ObjectInfo(
            uri="az://container/root/nested/other.txt",
            relative_path="nested/other.txt",
            size=5,
        ),
    ]

    downloaded = artifact_store.download_objects_to_directory(
        objects, tmp_path, max_workers=3
    )

    assert downloaded is True
    assert (tmp_path / "file.txt").read_bytes() == b"file"
    assert (tmp_path / "nested" / "other.txt").read_bytes() == b"other"
    blob_client = artifact_store.blob_service_client.get_blob_client(
        container="container", blob="root/file.txt"
    )
    assert blob_client.download_calls == [{"max_concurrency": 3}]


def test_download_objects_to_directory_rejects_path_traversal(
    tmp_path: Path,
):
    """Tests Azure downloads cannot escape the target directory."""
    container = _FakeContainerClient(objects={"root/file.txt": b"file"})
    artifact_store = _get_fake_azure_artifact_store(container)
    objects = [
        ObjectInfo(
            uri="az://container/root/file.txt",
            relative_path="../outside.txt",
            size=4,
        )
    ]

    with pytest.raises(ValueError, match="outside target directory"):
        artifact_store.download_objects_to_directory(objects, tmp_path)

    assert not (tmp_path.parent / "outside.txt").exists()


def test_open_append_uses_append_blob_for_new_blob(
    monkeypatch: pytest.MonkeyPatch,
):
    """Tests append mode writes through Azure append blobs when safe."""
    from zenml.integrations.azure.artifact_stores import azure_artifact_store

    monkeypatch.setattr(
        azure_artifact_store, "AZURE_APPEND_BLOB_MAX_BLOCK_BYTES", 3
    )
    container = _FakeContainerClient(objects={})
    artifact_store = _get_fake_azure_artifact_store(container)

    with artifact_store.open("az://container/root/logs/run.log", "a") as file:
        assert file.write("abcdef") == 6

    assert container.create_append_blob_calls == ["root/logs/run.log"]
    assert container.append_block_calls == [
        ("root/logs/run.log", b"abc"),
        ("root/logs/run.log", b"def"),
    ]
    assert container.objects["root/logs/run.log"] == b"abcdef"


def test_open_append_uses_existing_append_blob_with_enum_like_blob_type():
    """Tests append mode accepts SDK enum-like AppendBlob blob types."""
    container = _FakeContainerClient(objects={"root/logs/run.log": b"old"})
    container.blob_types["root/logs/run.log"] = _FakeBlobType()
    container.append_counts["root/logs/run.log"] = 1
    artifact_store = _get_fake_azure_artifact_store(container)

    with artifact_store.open("az://container/root/logs/run.log", "ab") as file:
        assert file.write(b"new") == 3

    assert container.create_append_blob_calls == []
    assert container.objects["root/logs/run.log"] == b"oldnew"
    assert container.append_counts["root/logs/run.log"] == 2


def test_open_append_falls_back_to_adlfs_for_existing_block_blob():
    """Tests append mode keeps the adlfs fallback for non-append blobs."""
    container = _FakeContainerClient(objects={"root/logs/run.log": b"old"})
    artifact_store = _get_fake_azure_artifact_store(container)
    filesystem = _FakeFilesystem()
    object.__setattr__(artifact_store, "_filesystem", filesystem)

    file = artifact_store.open("az://container/root/logs/run.log", "a")

    assert file is filesystem.open_return_value
    assert filesystem.open_calls == [("az://container/root/logs/run.log", "a")]
    assert container.append_block_calls == []


def test_append_blob_writer_rejects_writes_past_block_limit():
    """Tests append blob writer checks block limits before appending."""
    container = _FakeContainerClient(objects={"root/logs/run.log": b"old"})
    container.blob_types["root/logs/run.log"] = "AppendBlob"
    container.append_counts["root/logs/run.log"] = 50000
    artifact_store = _get_fake_azure_artifact_store(container)

    with artifact_store.open("az://container/root/logs/run.log", "a") as file:
        with pytest.raises(OSError, match="block limit"):
            file.write("new")

    assert container.append_block_calls == []
    assert container.objects["root/logs/run.log"] == b"old"
