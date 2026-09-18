#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Unit tests for the artifact log exporter."""

import os
from typing import Dict
from unittest.mock import patch

import pytest

from zenml.artifact_stores.local_artifact_store import LocalArtifactStore
from zenml.log_stores.artifact.artifact_log_exporter import (
    ArtifactLogExporter,
)


@pytest.fixture
def exporter(local_artifact_store: LocalArtifactStore) -> ArtifactLogExporter:
    """Fixture that creates an artifact log exporter for testing.

    Args:
        local_artifact_store: A local artifact store.

    Returns:
        The artifact log exporter.
    """
    return ArtifactLogExporter(artifact_store=local_artifact_store)


def _write_log_files(log_uri: str, contents: Dict[str, bytes]) -> None:
    os.makedirs(log_uri, exist_ok=True)
    for filename, content in contents.items():
        with open(os.path.join(log_uri, filename), "wb") as f:
            f.write(content)


def test_merge_concatenates_log_files_in_order(
    exporter: ArtifactLogExporter,
    local_artifact_store: LocalArtifactStore,
) -> None:
    """Test that merging concatenates all log files in sorted order."""
    log_uri = os.path.join(local_artifact_store.path, "logs")
    _write_log_files(
        log_uri,
        {
            "1.log": b"first log line\n" * 3,
            "2.log": b"second log line\n",
        },
    )

    exporter._merge(log_uri)

    files = os.listdir(log_uri)
    assert len(files) == 1
    assert files[0].endswith("_merged.log")

    with open(os.path.join(log_uri, files[0]), "rb") as f:
        assert f.read() == b"first log line\n" * 3 + b"second log line\n"


def test_merge_leaves_single_log_file_untouched(
    exporter: ArtifactLogExporter,
    local_artifact_store: LocalArtifactStore,
) -> None:
    """Test that merging is skipped if there is only a single log file."""
    log_uri = os.path.join(local_artifact_store.path, "logs")
    _write_log_files(log_uri, {"1.log": b"only line\n"})

    exporter._merge(log_uri)

    assert os.listdir(log_uri) == ["1.log"]
    with open(os.path.join(log_uri, "1.log"), "rb") as f:
        assert f.read() == b"only line\n"


def test_merge_preserves_non_utf8_content(
    exporter: ArtifactLogExporter,
    local_artifact_store: LocalArtifactStore,
) -> None:
    """Test that merging copies log files byte-for-byte.

    Log files can contain arbitrary bytes (e.g. binary output captured from a
    subprocess), so the merge must not make any assumptions about their
    encoding.
    """
    log_uri = os.path.join(local_artifact_store.path, "logs")
    content = b"valid line\n\xff\xfe invalid utf-8 \x80\n"
    _write_log_files(log_uri, {"1.log": content, "2.log": content})

    exporter._merge(log_uri)

    files = os.listdir(log_uri)
    assert len(files) == 1
    with open(os.path.join(log_uri, files[0]), "rb") as f:
        assert f.read() == content * 2


def test_merge_skips_missing_files(
    exporter: ArtifactLogExporter,
    local_artifact_store: LocalArtifactStore,
) -> None:
    """Test that files deleted concurrently during a merge are skipped."""
    log_uri = os.path.join(local_artifact_store.path, "logs")
    _write_log_files(
        log_uri,
        {
            "1.log": b"first\n",
            "2.log": b"second\n",
        },
    )

    with patch.object(
        LocalArtifactStore,
        "listdir",
        return_value=["1.log", "2.log", "ghost.log"],
    ):
        exporter._merge(log_uri)

    files = os.listdir(log_uri)
    assert len(files) == 1
    with open(os.path.join(log_uri, files[0]), "rb") as f:
        assert f.read() == b"first\nsecond\n"
