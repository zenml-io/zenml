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
"""Tests for artifact log retrieval."""

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4

import pytest

from zenml.artifact_stores.local_artifact_store import LocalArtifactStore
from zenml.enums import LoggingLevels
from zenml.log_stores.artifact.artifact_log_store import ArtifactLogStore
from zenml.models import LogEntry, LogsEntriesFilter, LogsResponse

START = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_entry(
    message: str,
    index: int = 0,
    level: LoggingLevels = LoggingLevels.INFO,
    chunk_index: int = 0,
    total_chunks: int = 1,
    entry_id: Optional[UUID] = None,
) -> LogEntry:
    """Build a log entry at a distinct point in time."""
    return LogEntry(
        message=message,
        level=level,
        timestamp=START + timedelta(seconds=index),
        chunk_index=chunk_index,
        total_chunks=total_chunks,
        id=entry_id or uuid4(),
    )


def write_log_file(path: str, entries: List[LogEntry]) -> None:
    """Write entries in the artifact log exporter's JSON-lines format."""
    with open(path, "w") as file:
        for entry in entries:
            file.write(entry.model_dump_json() + "\n")


@pytest.fixture
def log_store(artifact_store) -> ArtifactLogStore:
    """An artifact log store backed by a local artifact store."""
    return ArtifactLogStore.from_artifact_store(artifact_store)


@pytest.fixture
def logs_uri(artifact_store) -> str:
    """The path of a log file inside the artifact store."""
    return os.path.join(artifact_store.path, "logs.log")


@pytest.mark.parametrize("limit,expected_count", [(None, 3), (2, 2), (100, 3)])
def test_fetch_returns_a_capped_batch(
    log_store: ArtifactLogStore,
    logs_model_factory: Callable[..., LogsResponse],
    logs_uri: str,
    artifact_store: LocalArtifactStore,
    monkeypatch: pytest.MonkeyPatch,
    limit: Optional[int],
    expected_count: int,
) -> None:
    """Test ordered batches with requested and global limits, without cursors."""
    monkeypatch.setattr(
        "zenml.log_stores.base_log_store.LOGS_MAX_ENTRIES_PER_REQUEST", 3
    )
    write_log_file(logs_uri, [make_entry(f"line {i}", i) for i in range(5)])
    logs = logs_model_factory(
        uri=logs_uri, artifact_store_id=artifact_store.id
    )

    page = log_store.fetch(logs, limit=limit, filter_=LogsEntriesFilter())

    assert [entry.message for entry in page.items] == [
        f"line {i}" for i in range(expected_count)
    ]
    assert page.before is None
    assert page.after is None


def test_stored_chunk_ids_remain_stable_uuids(
    log_store, logs_model_factory, logs_uri, artifact_store
):
    """Stored UUIDs remain shared by chunks across repeated reads."""
    entry_id = uuid4()
    write_log_file(
        logs_uri,
        [
            make_entry(
                f"part-{index}",
                chunk_index=index,
                total_chunks=2,
                entry_id=entry_id,
            )
            for index in range(2)
        ],
    )
    logs = logs_model_factory(
        uri=logs_uri, artifact_store_id=artifact_store.id
    )

    first = log_store.fetch(logs)
    second = log_store.fetch(logs)

    expected_keys = [(entry_id, 0), (entry_id, 1)]
    assert [
        (entry.id, entry.chunk_index) for entry in first.items
    ] == expected_keys
    assert [
        (entry.id, entry.chunk_index) for entry in second.items
    ] == expected_keys


@pytest.mark.parametrize(
    "kwargs",
    [
        {"before": ""},
        {"after": "a-cursor"},
        {"start": "newest"},
        {"limit": 0},
        {"limit": -1},
        {"filter_": LogsEntriesFilter(search="boom")},
        {"filter_": LogsEntriesFilter(level=LoggingLevels.ERROR)},
        {
            "filter_": LogsEntriesFilter(
                since=datetime(2026, 1, 1, tzinfo=timezone.utc)
            )
        },
    ],
)
def test_fetch_rejects_invalid_parameters(
    log_store: ArtifactLogStore,
    logs_model_factory: Callable[..., LogsResponse],
    logs_uri: str,
    artifact_store: LocalArtifactStore,
    kwargs: Dict[str, Any],
) -> None:
    """Test rejection of invalid limits and unsupported pagination or filters."""
    write_log_file(logs_uri, [make_entry("only line")])
    logs = logs_model_factory(
        uri=logs_uri, artifact_store_id=artifact_store.id
    )

    with pytest.raises(ValueError):
        log_store.fetch(logs, **kwargs)


def test_fetch_reads_every_file_of_a_log_directory(
    log_store, logs_model_factory, artifact_store
):
    """An immutable artifact store writes a log stream as several files."""
    logs_dir = os.path.join(artifact_store.path, "logs")
    os.makedirs(logs_dir)
    write_log_file(
        os.path.join(logs_dir, "1700000000.log"),
        [make_entry("first", 0), make_entry("second", 1)],
    )
    write_log_file(
        os.path.join(logs_dir, "1700000100.log"),
        [make_entry("third", 2)],
    )
    logs = logs_model_factory(
        uri=logs_dir, artifact_store_id=artifact_store.id
    )

    page = log_store.fetch(logs)

    assert [entry.message for entry in page.items] == [
        "first",
        "second",
        "third",
    ]


def test_fetch_of_missing_logs_is_empty(
    log_store, logs_model_factory, artifact_store
):
    """Test that a missing log file returns an empty page."""
    logs = logs_model_factory(
        uri=os.path.join(artifact_store.path, "does-not-exist.log"),
        artifact_store_id=artifact_store.id,
    )

    page = log_store.fetch(logs)

    assert page.items == []


def test_fetch_rejects_a_foreign_artifact_store(
    log_store, logs_model_factory, logs_uri
):
    """Test rejection of a mismatched artifact store ID."""
    logs = logs_model_factory(uri=logs_uri, artifact_store_id=uuid4())

    with pytest.raises(ValueError, match="does not match"):
        log_store.fetch(logs)


def test_a_chunked_message_does_not_overshoot_the_limit(
    log_store, logs_model_factory, logs_uri, artifact_store
):
    """Test that each stored message chunk counts toward the limit."""
    entry_id = uuid4()
    chunks = [
        make_entry(
            f"part-{index}",
            1,
            chunk_index=index,
            total_chunks=3,
            entry_id=entry_id,
        )
        for index in range(3)
    ]
    write_log_file(logs_uri, [make_entry("before", 0), *chunks])
    logs = logs_model_factory(
        uri=logs_uri, artifact_store_id=artifact_store.id
    )

    page = log_store.fetch(logs, limit=2)

    assert [entry.message for entry in page.items] == ["before", "part-0"]


def test_plain_text_logs_are_readable(
    log_store, logs_model_factory, logs_uri, artifact_store
):
    """Log files written before the structured format are still readable."""
    with open(logs_uri, "w") as file:
        file.write("[2026-01-01 12:00:00 UTC] first line\n")
        file.write("second line\n")
    logs = logs_model_factory(
        uri=logs_uri, artifact_store_id=artifact_store.id
    )

    page = log_store.fetch(logs)

    assert [entry.message for entry in page.items] == [
        "first line",
        "second line",
    ]
