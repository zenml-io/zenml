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
"""Tests for artifact-backed log storage helpers."""

import os
from datetime import datetime
from typing import ClassVar, Iterable, List, Sequence
from uuid import uuid4

from zenml.artifact_stores import LocalArtifactStore, LocalArtifactStoreConfig
from zenml.enums import StackComponentType
from zenml.log_stores.artifact.artifact_log_exporter import ArtifactLogExporter
from zenml.log_stores.artifact.artifact_log_store import (
    MERGED_LOG_FILE_NAME,
    fetch_log_records,
)


class ImmutableLocalArtifactStoreConfig(LocalArtifactStoreConfig):
    """Local artifact-store config that uses immutable log directories."""

    IS_IMMUTABLE_FILESYSTEM: ClassVar[bool] = True


class ConflictingListObjectsLocalArtifactStore(LocalArtifactStore):
    """Local fake with a pre-existing incompatible list_objects helper."""

    def list_objects(  # type: ignore[override]
        self, prefix: str, recursive: bool = False
    ) -> List[str]:
        """Return the wrong shape to simulate an existing custom helper."""
        return ["not-object-info"]


class AcceleratedImmutableLocalArtifactStore(LocalArtifactStore):
    """Local fake that exposes provider-side log compose support."""

    def compose_objects(
        self,
        sources: Sequence[str],
        destination: str,
        overwrite: bool = False,
    ) -> bool:
        """Compose source files into a destination file."""
        self.compose_calls.append((list(sources), destination, overwrite))
        if not overwrite and self.exists(destination):
            return False

        with self.open(destination, "w") as destination_file:
            for source in sources:
                with self.open(source, "r") as source_file:
                    destination_file.write(source_file.read())
        return True

    def delete_objects(self, paths: Iterable[str]):  # type: ignore[no-untyped-def]
        """Record bulk-delete calls before using the fallback implementation."""
        path_list = list(paths)
        self.deleted_batches.append(path_list)
        return super().delete_objects(path_list)


def _store(path, cls=LocalArtifactStore):  # type: ignore[no-untyped-def]
    store = cls(
        name="test-artifact-store",
        id=uuid4(),
        config=ImmutableLocalArtifactStoreConfig(path=str(path)),
        flavor="local",
        type=StackComponentType.ARTIFACT_STORE,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )
    object.__setattr__(store, "compose_calls", [])
    object.__setattr__(store, "deleted_batches", [])
    return store


def _write(store, path: str, content: str) -> None:  # type: ignore[no-untyped-def]
    parent = os.path.dirname(path)
    if not store.exists(parent):
        store.makedirs(parent)
    with store.open(path, "w") as file:
        file.write(content)


def test_immutable_log_merge_uses_python_fallback_without_compose(tmp_path):
    """Tests immutable log finalization on stores with no compose override."""
    store = _store(tmp_path)
    log_uri = os.path.join(store.path, "logs", "run")
    _write(store, os.path.join(log_uri, "2.log"), "second\n")
    _write(store, os.path.join(log_uri, "1.log"), "first\n")

    ArtifactLogExporter(store)._merge(log_uri)

    objects = list(store.list_objects(log_uri))
    assert len(objects) == 1
    assert objects[0].relative_path.endswith("_merged.log")
    with store.open(objects[0].uri, "r") as file:
        assert file.read() == "first\nsecond\n"


def test_immutable_log_merge_uses_compose_and_bulk_delete(tmp_path):
    """Tests immutable log finalization when compose support is available."""
    store = _store(tmp_path, cls=AcceleratedImmutableLocalArtifactStore)
    log_uri = os.path.join(store.path, "logs", "run")
    first = os.path.join(log_uri, "1.log")
    second = os.path.join(log_uri, "2.log")
    temporary = os.path.join(log_uri, ".zenml-compose-old.log")
    _write(store, second, "second\n")
    _write(store, first, "first\n")
    _write(store, temporary, "temporary\n")

    ArtifactLogExporter(store)._merge(log_uri)

    destination = os.path.join(log_uri, MERGED_LOG_FILE_NAME)
    assert store.compose_calls == [([first, second], destination, False)]
    assert store.deleted_batches == [[first, second, temporary]]
    with store.open(destination, "r") as file:
        assert file.read() == "first\nsecond\n"
    assert not store.exists(first)
    assert not store.exists(second)
    assert not store.exists(temporary)


def test_immutable_log_merge_with_existing_merged_log_only_cleans_up(
    tmp_path,
):
    """Tests retry finalization is cleanup-only after merged.log exists."""
    store = _store(tmp_path, cls=AcceleratedImmutableLocalArtifactStore)
    log_uri = os.path.join(store.path, "logs", "run")
    first = os.path.join(log_uri, "1.log")
    merged = os.path.join(log_uri, MERGED_LOG_FILE_NAME)
    _write(store, first, "fragment\n")
    _write(store, merged, "merged\n")

    ArtifactLogExporter(store)._merge(log_uri)

    assert store.compose_calls == []
    assert store.deleted_batches == [[first]]
    with store.open(merged, "r") as file:
        assert file.read() == "merged\n"
    assert not store.exists(first)


def test_fetch_prefers_merged_log_object_over_fragments(tmp_path):
    """Tests directory fetch reads the final merged log object first."""
    store = _store(tmp_path)
    log_uri = os.path.join(store.path, "logs", "run")
    _write(store, os.path.join(log_uri, "1.log"), "fragment\n")
    _write(store, os.path.join(log_uri, MERGED_LOG_FILE_NAME), "merged\n")

    entries = fetch_log_records(store, log_uri, limit=10)

    assert [entry.message for entry in entries] == ["merged"]


def test_fetch_reads_sorted_fragments_and_ignores_compose_temporary_files(
    tmp_path,
):
    """Tests directory fetch fallback when no merged object exists."""
    store = _store(tmp_path)
    log_uri = os.path.join(store.path, "logs", "run")
    _write(store, os.path.join(log_uri, "2.log"), "second\n")
    _write(store, os.path.join(log_uri, "1.log"), "first\n")
    _write(store, os.path.join(log_uri, ".zenml-compose-old.log"), "temp\n")

    entries = fetch_log_records(store, log_uri, limit=1)

    assert [entry.message for entry in entries] == ["first"]


def test_fetch_missing_log_file_returns_empty_entries(tmp_path):
    """Tests missing single-file log URIs behave like empty logs."""
    store = _store(tmp_path)

    entries = fetch_log_records(
        store,
        os.path.join(store.path, "logs", "missing.log"),
        limit=10,
    )

    assert entries == []


def test_fetch_falls_back_when_custom_list_objects_has_old_shape(tmp_path):
    """Tests existing custom list_objects helpers do not break log fetch."""
    store = _store(tmp_path, cls=ConflictingListObjectsLocalArtifactStore)
    log_uri = os.path.join(store.path, "logs", "run")
    _write(store, os.path.join(log_uri, "1.log"), "fragment\n")

    entries = fetch_log_records(store, log_uri, limit=10)

    assert [entry.message for entry in entries] == ["fragment"]
