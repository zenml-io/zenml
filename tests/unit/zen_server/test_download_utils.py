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
"""Unit tests for the ZenML server download utilities."""

import io
import os
from unittest.mock import MagicMock, patch

import pytest

from tests.unit.conftest import ReadTrackingBytesIO
from zenml.io import fileio
from zenml.zen_server import download_utils


def test_download_snapshot_code_archive_streams_in_chunks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that code archives are streamed in bounded chunks.

    Regression test: the code archive used to be loaded into memory with a
    single unbounded `read()`, which could consume up to the entire file
    download size limit (2 GiB by default) of server memory per request.
    """
    chunk_size = 8
    monkeypatch.setattr(fileio, "FILEIO_COPY_CHUNK_SIZE", chunk_size)

    data = b"0123456789" * 5  # 50 bytes -> 7 chunks of 8 bytes
    tracking_file = ReadTrackingBytesIO(data)
    artifact_store = MagicMock()
    artifact_store.open.return_value = tracking_file

    path = download_utils.download_snapshot_code_archive(
        code_path="s3://bucket/code/archive.tar.gz",
        artifact_store=artifact_store,
    )

    try:
        with open(path, "rb") as f:
            assert f.read() == data

        artifact_store.open.assert_called_once_with(
            "s3://bucket/code/archive.tar.gz", "rb"
        )
        assert all(size == chunk_size for size in tracking_file.read_sizes)
    finally:
        os.remove(path)


def test_download_snapshot_code_archive_with_empty_archive() -> None:
    """Test that an empty code archive results in an empty temp file."""
    artifact_store = MagicMock()
    artifact_store.open.return_value = io.BytesIO()

    path = download_utils.download_snapshot_code_archive(
        code_path="s3://bucket/code/archive.tar.gz",
        artifact_store=artifact_store,
    )

    try:
        assert os.path.getsize(path) == 0
    finally:
        os.remove(path)


def test_download_snapshot_code_archive_cleans_up_on_failure() -> None:
    """Test that the temp file is removed if the download fails."""
    artifact_store = MagicMock()
    artifact_store.open.side_effect = RuntimeError("connection lost")

    with patch(
        "zenml.zen_server.download_utils.os.remove", wraps=os.remove
    ) as mock_remove:
        with pytest.raises(RuntimeError, match="connection lost"):
            download_utils.download_snapshot_code_archive(
                code_path="s3://bucket/code/archive.tar.gz",
                artifact_store=artifact_store,
            )

    mock_remove.assert_called_once()
    assert not os.path.exists(mock_remove.call_args[0][0])
