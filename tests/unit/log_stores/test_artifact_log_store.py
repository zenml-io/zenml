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
"""Tests for reading log entries back out of the artifact store."""

import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID, uuid4

import pytest

from zenml.enums import LoggingLevels
from zenml.log_stores.artifact.artifact_log_store import ArtifactLogStore
from zenml.models import LogEntry, LogsEntriesFilter

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
    """Write entries to a log file the way the artifact log exporter does."""
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


def test_fetch_returns_entries_oldest_first(
    log_store, logs_model_factory, logs_uri, artifact_store
):
    """A fetch returns the entries in the order they were written."""
    write_log_file(logs_uri, [make_entry(f"line {i}", i) for i in range(5)])
    logs = logs_model_factory(
        uri=logs_uri, artifact_store_id=artifact_store.id
    )

    page = log_store.fetch(logs)

    assert [entry.message for entry in page.items] == [
        f"line {i}" for i in range(5)
    ]


def test_fetch_reports_no_cursors(
    log_store, logs_model_factory, logs_uri, artifact_store
):
    """The artifact log store never claims to be pageable."""
    write_log_file(logs_uri, [make_entry("only line")])
    logs = logs_model_factory(
        uri=logs_uri, artifact_store_id=artifact_store.id
    )

    page = log_store.fetch(logs)

    assert page.before is None
    assert page.after is None
    assert len(page.items) == 1


@pytest.mark.parametrize(
    "kwargs",
    [
        {"before": "a-cursor"},
        {"after": "a-cursor"},
        {"start": "newest"},
        {"filter_": LogsEntriesFilter(search="boom")},
        {"filter_": LogsEntriesFilter(level=LoggingLevels.ERROR)},
        {
            "filter_": LogsEntriesFilter(
                since=datetime(2026, 1, 1, tzinfo=timezone.utc)
            )
        },
    ],
)
def test_fetch_refuses_what_it_cannot_honor(
    log_store, logs_model_factory, logs_uri, artifact_store, kwargs
):
    """Serving something other than what was asked for would mislead a caller."""
    write_log_file(logs_uri, [make_entry("only line")])
    logs = logs_model_factory(
        uri=logs_uri, artifact_store_id=artifact_store.id
    )

    with pytest.raises(ValueError, match="only reads a log file"):
        log_store.fetch(logs, **kwargs)


def test_fetch_accepts_an_empty_filter(
    log_store, logs_model_factory, logs_uri, artifact_store
):
    """A filter that narrows nothing down asks nothing of the log store."""
    write_log_file(logs_uri, [make_entry("only line")])
    logs = logs_model_factory(
        uri=logs_uri, artifact_store_id=artifact_store.id
    )

    page = log_store.fetch(logs, filter_=LogsEntriesFilter())

    assert len(page.items) == 1


def test_fetch_names_every_filter_it_refuses(
    log_store, logs_model_factory, logs_uri, artifact_store
):
    """A caller should not have to discover its refused filters one at a time."""
    write_log_file(logs_uri, [make_entry("only line")])
    logs = logs_model_factory(
        uri=logs_uri, artifact_store_id=artifact_store.id
    )

    with pytest.raises(ValueError) as failure:
        log_store.fetch(
            logs,
            filter_=LogsEntriesFilter(
                search="boom", level=LoggingLevels.ERROR
            ),
        )

    assert "search" in str(failure.value)
    assert "level" in str(failure.value)


def test_fetch_stops_at_the_limit(
    log_store, logs_model_factory, logs_uri, artifact_store
):
    """A stream longer than the limit is cut off at its end."""
    write_log_file(logs_uri, [make_entry(f"line {i}", i) for i in range(10)])
    logs = logs_model_factory(
        uri=logs_uri, artifact_store_id=artifact_store.id
    )

    page = log_store.fetch(logs, limit=3)

    assert [entry.message for entry in page.items] == [
        "line 0",
        "line 1",
        "line 2",
    ]


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
    """A log stream that was never written to reads as empty."""
    logs = logs_model_factory(
        uri=os.path.join(artifact_store.path, "does-not-exist.log"),
        artifact_store_id=artifact_store.id,
    )

    page = log_store.fetch(logs)

    assert page.items == []


def test_fetch_rejects_a_foreign_artifact_store(
    log_store, logs_model_factory, logs_uri
):
    """Logs collected by another artifact store are not readable here."""
    logs = logs_model_factory(uri=logs_uri, artifact_store_id=uuid4())

    with pytest.raises(ValueError, match="does not match"):
        log_store.fetch(logs)


def test_a_chunked_message_does_not_overshoot_the_limit(
    log_store, logs_model_factory, logs_uri, artifact_store
):
    """The limit counts stored entries, so a huge message cannot blow past it."""
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
