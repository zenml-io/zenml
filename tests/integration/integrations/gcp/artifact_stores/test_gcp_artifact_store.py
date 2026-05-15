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


from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Sequence, Tuple
from uuid import uuid4

import pytest

from zenml.artifact_stores import ObjectInfo
from zenml.enums import StackComponentType
from zenml.exceptions import ArtifactStoreInterfaceError


def _get_gcp_artifact_store(**kwargs):
    from zenml.integrations.gcp.artifact_stores.gcp_artifact_store import (
        GCPArtifactStore,
    )
    from zenml.integrations.gcp.flavors.gcp_artifact_store_flavor import (
        GCPArtifactStoreConfig,
    )

    return GCPArtifactStore(
        name="",
        id=uuid4(),
        config=GCPArtifactStoreConfig(**kwargs),
        flavor="gcp",
        type=StackComponentType.ARTIFACT_STORE,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def test_must_be_gcs_path():
    """Checks that a gcp artifact store can only be initialized with a gcspath."""
    with pytest.raises(ArtifactStoreInterfaceError):
        _get_gcp_artifact_store(path="/local/path")

    with pytest.raises(ArtifactStoreInterfaceError):
        _get_gcp_artifact_store(path="s3://local/path")

    artifact_store = _get_gcp_artifact_store(path="gs://mybucket")
    assert artifact_store.path == "gs://mybucket"


class _FakePreconditionFailed(Exception):
    """Fake GCS precondition error used by compose tests."""


class _FakeBlob:
    """In-memory stand-in for a google.cloud.storage Blob."""

    def __init__(
        self,
        bucket: "_FakeBucket",
        name: str,
        requested_generation: Optional[int] = None,
    ) -> None:
        """Initialize a fake blob."""
        self.bucket = bucket
        self.name = name
        self.requested_generation = requested_generation

    @property
    def size(self) -> Optional[int]:
        """Return the fake object size."""
        content = self.bucket.objects.get(self.name)
        return len(content) if content is not None else None

    @property
    def etag(self) -> Optional[str]:
        """Return a stable fake etag for existing objects."""
        if self.name in self.bucket.objects:
            return f"etag-{self.name}"
        return None

    @property
    def generation(self) -> Optional[int]:
        """Return a stable fake generation for existing objects."""
        return 1 if self.name in self.bucket.objects else None

    @property
    def updated(self) -> datetime:
        """Return a stable fake updated timestamp."""
        return datetime(2026, 5, 14)

    def compose(
        self,
        sources: Sequence["_FakeBlob"],
        client: "_FakeGCSClient",
        if_generation_match: Optional[int] = None,
    ) -> None:
        """Compose source blobs by concatenating their bytes in order."""
        self.bucket.compose_calls.append(
            (
                [source.name for source in sources],
                self.name,
                if_generation_match,
            )
        )
        if self.name == self.bucket.fail_compose_destination:
            raise RuntimeError("compose failed")
        if if_generation_match == 0 and self.name in self.bucket.objects:
            raise _FakePreconditionFailed("destination exists")

        self.bucket.objects[self.name] = b"".join(
            self.bucket.objects[source.name] for source in sources
        )

    def exists(self, client: "_FakeGCSClient") -> bool:
        """Return whether the fake object exists."""
        return self.name in self.bucket.objects

    def delete(self, client: "_FakeGCSClient") -> None:
        """Delete the fake object or raise a configured cleanup error."""
        self.bucket.delete_calls.append(self.name)
        if self.name in self.bucket.delete_failures:
            raise RuntimeError("delete failed")
        self.bucket.objects.pop(self.name, None)


class _FakeBucket:
    """In-memory stand-in for a GCS bucket."""

    def __init__(self, objects: Dict[str, bytes]) -> None:
        """Initialize a fake bucket."""
        self.objects = objects
        self.compose_calls: List[tuple[List[str], str, Optional[int]]] = []
        self.delete_calls: List[str] = []
        self.delete_failures: set[str] = set()
        self.fail_compose_destination: Optional[str] = None

    def blob(self, name: str, generation: Optional[int] = None) -> _FakeBlob:
        """Return a fake blob handle."""
        return _FakeBlob(
            bucket=self, name=name, requested_generation=generation
        )


class _FakeGCSClient:
    """In-memory stand-in for a GCS storage client."""

    def __init__(self, objects: Dict[str, bytes]) -> None:
        """Initialize a fake GCS client with one bucket."""
        self.bucket_ = _FakeBucket(objects=objects)
        self.list_calls: List[tuple[str, str]] = []

    def bucket(self, bucket_name: str) -> _FakeBucket:
        """Return the fake bucket."""
        assert bucket_name == "bucket"
        return self.bucket_

    def list_blobs(self, bucket_name: str, prefix: str):  # type: ignore[no-untyped-def]
        """List fake blobs by prefix."""
        assert bucket_name == "bucket"
        self.list_calls.append((bucket_name, prefix))
        return [
            self.bucket_.blob(name)
            for name in sorted(self.bucket_.objects)
            if name.startswith(prefix)
        ]


def _get_fake_gcp_artifact_store(
    client: _FakeGCSClient, path: str = "gs://bucket/root"
):  # type: ignore[no-untyped-def]
    """Create a GCP artifact store wired to an in-memory storage client."""
    artifact_store = _get_gcp_artifact_store(path=path)
    object.__setattr__(artifact_store, "_storage_client", client)
    return artifact_store


def _fragment_objects(count: int) -> Dict[str, bytes]:
    """Build ordered fake log fragments for compose tests."""
    return {
        f"root/logs/{index:04d}.log": f"{index:04d}\n".encode()
        for index in range(count)
    }


def test_list_objects_uses_native_gcs_listing_and_metadata():
    """Tests GCS list_objects returns direct children and metadata."""
    client = _FakeGCSClient(
        objects={
            "root/logs/1.log": b"one",
            "root/logs/nested/2.log": b"two",
            "root/logs2/3.log": b"three",
        }
    )
    artifact_store = _get_fake_gcp_artifact_store(client)

    objects = list(artifact_store.list_objects("gs://bucket/root/logs"))

    assert client.list_calls == [("bucket", "root/logs")]
    assert [object_info.relative_path for object_info in objects] == ["1.log"]
    assert objects[0].uri == "gs://bucket/root/logs/1.log"
    assert objects[0].size == 3
    assert objects[0].etag == "etag-root/logs/1.log"
    assert objects[0].generation == "1"

    recursive_objects = list(
        artifact_store.list_objects("gs://bucket/root/logs", recursive=True)
    )

    assert [
        object_info.relative_path for object_info in recursive_objects
    ] == [
        "1.log",
        "nested/2.log",
    ]


def test_list_objects_at_bucket_root_preserves_relative_paths():
    """Tests bucket-root listings keep nested relative paths intact."""
    client = _FakeGCSClient(
        objects={
            "top.log": b"top",
            "a/file.txt": b"a",
            "b/file.txt": b"b",
        }
    )
    artifact_store = _get_fake_gcp_artifact_store(client, path="gs://bucket")

    objects = list(artifact_store.list_objects("gs://bucket"))
    recursive_objects = list(
        artifact_store.list_objects("gs://bucket", recursive=True)
    )

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


def test_delete_objects_reports_per_object_cleanup_failures():
    """Tests GCS delete_objects keeps successful and failed deletes separate."""
    client = _FakeGCSClient(
        objects={
            "root/logs/1.log": b"one",
            "root/logs/2.log": b"two",
        }
    )
    client.bucket_.delete_failures.add("root/logs/2.log")
    artifact_store = _get_fake_gcp_artifact_store(client)

    result = artifact_store.delete_objects(
        ["gs://bucket/root/logs/1.log", "gs://bucket/root/logs/2.log"]
    )

    assert result.deleted_paths == ["gs://bucket/root/logs/1.log"]
    assert [failure.path for failure in result.failures] == [
        "gs://bucket/root/logs/2.log"
    ]
    assert "root/logs/1.log" not in client.bucket_.objects
    assert client.bucket_.objects["root/logs/2.log"] == b"two"


def test_download_objects_to_directory_uses_gcs_transfer_manager(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    """Tests GCS downloads many objects without ZenML file opens."""
    from zenml.integrations.gcp.artifact_stores import gcp_artifact_store

    client = _FakeGCSClient(
        objects={
            "root/artifact/a.txt": b"a",
            "root/artifact/nested/b.txt": b"b",
        }
    )
    artifact_store = _get_fake_gcp_artifact_store(client)
    download_calls: List[
        Tuple[List[Tuple[_FakeBlob, str]], Dict[str, Any]]
    ] = []

    def fail_open(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("download_objects_to_directory must not use open")

    def fake_download_many(
        blob_file_pairs: Sequence[Tuple[_FakeBlob, str]],
        **kwargs: Any,
    ) -> List[None]:
        pairs = list(blob_file_pairs)
        download_calls.append((pairs, kwargs))
        for blob, destination in pairs:
            Path(destination).write_bytes(blob.bucket.objects[blob.name])
        return [None for _ in pairs]

    monkeypatch.setattr(gcp_artifact_store.GCPArtifactStore, "open", fail_open)
    monkeypatch.setattr(
        gcp_artifact_store.transfer_manager,
        "download_many",
        fake_download_many,
    )

    downloaded = artifact_store.download_objects_to_directory(
        [
            ObjectInfo(
                uri="gs://bucket/root/artifact/a.txt",
                relative_path="a.txt",
                generation="11",
            ),
            ObjectInfo(
                uri="gs://bucket/root/artifact/nested/b.txt",
                relative_path="nested/b.txt",
                generation="12",
            ),
        ],
        str(tmp_path),
        max_workers=4,
    )

    assert downloaded is True
    assert (tmp_path / "a.txt").read_bytes() == b"a"
    assert (tmp_path / "nested" / "b.txt").read_bytes() == b"b"
    assert len(download_calls) == 1
    pairs, kwargs = download_calls[0]
    assert [blob.name for blob, _ in pairs] == [
        "root/artifact/a.txt",
        "root/artifact/nested/b.txt",
    ]
    assert [blob.requested_generation for blob, _ in pairs] == [11, 12]
    assert kwargs["raise_exception"] is True
    assert kwargs["worker_type"] == gcp_artifact_store.transfer_manager.THREAD
    assert kwargs["max_workers"] == 4


def test_download_objects_to_directory_rejects_path_traversal(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    """Tests GCS downloads refuse object paths outside the target dir."""
    from zenml.integrations.gcp.artifact_stores import gcp_artifact_store

    client = _FakeGCSClient(objects={"root/artifact/evil.txt": b"evil"})
    artifact_store = _get_fake_gcp_artifact_store(client)
    download_calls: List[object] = []

    def fake_download_many(*args: Any, **kwargs: Any) -> List[None]:
        download_calls.append((args, kwargs))
        return []

    monkeypatch.setattr(
        gcp_artifact_store.transfer_manager,
        "download_many",
        fake_download_many,
    )

    with pytest.raises(
        ValueError, match="escapes the local download directory"
    ):
        artifact_store.download_objects_to_directory(
            [
                ObjectInfo(
                    uri="gs://bucket/root/artifact/evil.txt",
                    relative_path="../evil.txt",
                )
            ],
            str(tmp_path),
        )

    assert download_calls == []
    assert not (tmp_path.parent / "evil.txt").exists()


def test_compose_objects_returns_false_for_empty_source_list():
    """Tests empty GCS compose requests are treated as unsupported."""
    client = _FakeGCSClient(objects={})
    artifact_store = _get_fake_gcp_artifact_store(client)

    composed = artifact_store.compose_objects(
        [], "gs://bucket/root/logs/merged.log"
    )

    assert composed is False
    assert client.bucket_.compose_calls == []


def test_compose_objects_returns_false_for_single_source():
    """Tests one-fragment GCS merges avoid provider compose overhead."""
    client = _FakeGCSClient(objects={"root/logs/1.log": b"fragment"})
    artifact_store = _get_fake_gcp_artifact_store(client)

    composed = artifact_store.compose_objects(
        ["gs://bucket/root/logs/1.log"],
        "gs://bucket/root/logs/merged.log",
    )

    assert composed is False
    assert "root/logs/merged.log" not in client.bucket_.objects
    assert client.bucket_.compose_calls == []


@pytest.mark.parametrize("fragment_count", [2, 32])
def test_compose_objects_uses_single_gcs_compose_for_up_to_32_sources(
    fragment_count: int,
):
    """Tests GCS compose preserves source order without intermediates."""
    client = _FakeGCSClient(objects=_fragment_objects(fragment_count))
    artifact_store = _get_fake_gcp_artifact_store(client)
    sources = [
        f"gs://bucket/root/logs/{index:04d}.log"
        for index in range(fragment_count)
    ]

    composed = artifact_store.compose_objects(
        sources, "gs://bucket/root/logs/merged.log"
    )

    assert composed is True
    assert client.bucket_.objects["root/logs/merged.log"] == b"".join(
        f"{index:04d}\n".encode() for index in range(fragment_count)
    )
    assert client.bucket_.compose_calls == [
        (
            [f"root/logs/{index:04d}.log" for index in range(fragment_count)],
            "root/logs/merged.log",
            0,
        )
    ]
    assert client.bucket_.delete_calls == []


@pytest.mark.parametrize("fragment_count", [33, 1025])
def test_compose_objects_uses_tree_composition_for_more_than_32_sources(
    fragment_count: int,
    monkeypatch: pytest.MonkeyPatch,
):
    """Tests GCS compose trees keep ordering and remove intermediates."""
    from zenml.integrations.gcp.artifact_stores import gcp_artifact_store

    monkeypatch.setattr(
        gcp_artifact_store, "uuid4", lambda: SimpleNamespace(hex="fixed")
    )
    client = _FakeGCSClient(objects=_fragment_objects(fragment_count))
    artifact_store = _get_fake_gcp_artifact_store(client)
    sources = [
        f"gs://bucket/root/logs/{index:04d}.log"
        for index in range(fragment_count)
    ]

    composed = artifact_store.compose_objects(
        sources, "gs://bucket/root/logs/merged.log"
    )

    assert composed is True
    assert client.bucket_.objects["root/logs/merged.log"] == b"".join(
        f"{index:04d}\n".encode() for index in range(fragment_count)
    )
    assert all(
        not name.startswith("root/logs/.zenml-compose-")
        for name in client.bucket_.objects
    )
    assert client.bucket_.compose_calls[0][0] == [
        f"root/logs/{index:04d}.log" for index in range(32)
    ]
    assert client.bucket_.compose_calls[-1][1] == "root/logs/merged.log"
    assert client.bucket_.delete_calls


def test_compose_objects_treats_existing_destination_as_successful_retry(
    monkeypatch: pytest.MonkeyPatch,
):
    """Tests duplicate finalization does not fall back after GCS precondition failure."""
    from zenml.integrations.gcp.artifact_stores import gcp_artifact_store

    monkeypatch.setattr(
        gcp_artifact_store, "PreconditionFailed", _FakePreconditionFailed
    )
    client = _FakeGCSClient(
        objects={
            "root/logs/1.log": b"fragment-1",
            "root/logs/2.log": b"fragment-2",
            "root/logs/merged.log": b"existing",
        }
    )
    artifact_store = _get_fake_gcp_artifact_store(client)

    composed = artifact_store.compose_objects(
        ["gs://bucket/root/logs/1.log", "gs://bucket/root/logs/2.log"],
        "gs://bucket/root/logs/merged.log",
    )

    assert composed is True
    assert client.bucket_.objects["root/logs/merged.log"] == b"existing"


def test_compose_objects_reraises_intermediate_precondition_failure(
    monkeypatch: pytest.MonkeyPatch,
):
    """Tests only final destination precondition errors are idempotent."""
    from zenml.integrations.gcp.artifact_stores import gcp_artifact_store

    monkeypatch.setattr(
        gcp_artifact_store, "PreconditionFailed", _FakePreconditionFailed
    )
    monkeypatch.setattr(
        gcp_artifact_store, "uuid4", lambda: SimpleNamespace(hex="fixed")
    )
    objects = _fragment_objects(33)
    objects["root/logs/.zenml-compose-fixed-0-000000.log"] = b"old-temp"
    objects["root/logs/merged.log"] = b"existing"
    client = _FakeGCSClient(objects=objects)
    artifact_store = _get_fake_gcp_artifact_store(client)
    sources = [f"gs://bucket/root/logs/{index:04d}.log" for index in range(33)]

    with pytest.raises(_FakePreconditionFailed):
        artifact_store.compose_objects(
            sources, "gs://bucket/root/logs/merged.log"
        )

    assert client.bucket_.objects["root/logs/merged.log"] == b"existing"


def test_compose_objects_cleans_intermediates_after_final_compose_failure(
    monkeypatch: pytest.MonkeyPatch,
):
    """Tests temporary GCS compose objects are removed on fallback errors."""
    from zenml.integrations.gcp.artifact_stores import gcp_artifact_store

    monkeypatch.setattr(
        gcp_artifact_store, "uuid4", lambda: SimpleNamespace(hex="fixed")
    )
    client = _FakeGCSClient(objects=_fragment_objects(33))
    client.bucket_.fail_compose_destination = "root/logs/merged.log"
    artifact_store = _get_fake_gcp_artifact_store(client)
    sources = [f"gs://bucket/root/logs/{index:04d}.log" for index in range(33)]

    with pytest.raises(RuntimeError, match="compose failed"):
        artifact_store.compose_objects(
            sources, "gs://bucket/root/logs/merged.log"
        )

    assert all(
        not name.startswith("root/logs/.zenml-compose-")
        for name in client.bucket_.objects
    )
    assert client.bucket_.delete_calls == [
        "root/logs/.zenml-compose-fixed-0-000000.log",
        "root/logs/.zenml-compose-fixed-0-000001.log",
    ]


def test_compose_objects_warns_but_succeeds_when_cleanup_fails(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    """Tests cleanup errors after final compose do not fail finalization."""
    from zenml.integrations.gcp.artifact_stores import gcp_artifact_store

    monkeypatch.setattr(
        gcp_artifact_store, "uuid4", lambda: SimpleNamespace(hex="fixed")
    )
    client = _FakeGCSClient(objects=_fragment_objects(33))
    client.bucket_.delete_failures.add(
        "root/logs/.zenml-compose-fixed-0-000001.log"
    )
    artifact_store = _get_fake_gcp_artifact_store(client)
    sources = [f"gs://bucket/root/logs/{index:04d}.log" for index in range(33)]

    composed = artifact_store.compose_objects(
        sources, "gs://bucket/root/logs/merged.log"
    )

    assert composed is True
    assert client.bucket_.objects["root/logs/merged.log"] == b"".join(
        f"{index:04d}\n".encode() for index in range(33)
    )
    assert "failed to clean up 1 temporary compose objects" in caplog.text
    assert (
        "root/logs/.zenml-compose-fixed-0-000001.log" in client.bucket_.objects
    )
