# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Bounded decompression, content integrity, and strict bundle ownership."""

import gzip
import hashlib
from pathlib import Path
from typing import Callable
from uuid import uuid4

import pytest

from zenml.exceptions import (
    ExecutionRetentionConflictError,
    ExecutionRetentionIntegrityError,
)
from zenml.zen_stores.retention import format as archive_format
from zenml.zen_stores.retention.format import (
    ArchiveDocument,
    canonical_json,
    compute_content_hash,
    decode,
    encode,
)


@pytest.fixture
def document() -> ArchiveDocument:
    """Read a frozen archive without depending on a running database.

    Returns:
        The verified v1 document.
    """
    raw = (
        Path(__file__).with_name("fixtures") / "archive_v1_static.json"
    ).read_bytes()
    return decode(gzip.compress(raw, mtime=0), hashlib.sha256(raw).hexdigest())


@pytest.mark.parametrize(
    "defect",
    [
        "foreign_run",
        "foreign_configuration",
        "extra_field",
        "version",
        "duplicate_key",
        "hash",
        "truncated",
        "not_gzip",
    ],
)
def test_decode_rejects_invalid_bundles(document, defect):
    """A matching hash never bypasses format or ownership validation."""
    fields = document.model_dump(mode="json")
    if defect == "foreign_run":
        fields["steps"][0]["pipeline_run_id"] = str(uuid4())
    elif defect == "foreign_configuration":
        fields["configurations"][0]["snapshot_id"] = str(uuid4())
    elif defect == "extra_field":
        fields["run"]["unexpected"] = "value"
    elif defect == "version":
        fields["format_version"] = 2
    decoded = (
        b'{"run_id": 1, "run_id": 2}'
        if defect == "duplicate_key"
        else canonical_json(fields)
    )
    data = gzip.compress(decoded, mtime=0)
    content_hash = hashlib.sha256(decoded).hexdigest()
    if defect == "hash":
        content_hash = "0" * 64
    elif defect == "truncated":
        data = data[:-8]
    elif defect == "not_gzip":
        data = b"not gzip"
    with pytest.raises(ExecutionRetentionIntegrityError):
        decode(data, content_hash)


def test_decompression_stops_at_the_size_cap(monkeypatch):
    """A compression bomb is rejected one byte past the cap."""
    monkeypatch.setattr(archive_format, "MAX_DECODED_BYTES", 1024)
    bomb = gzip.compress(b" " * (1024 * 1024), mtime=0)

    with pytest.raises(ExecutionRetentionIntegrityError, match="size limit"):
        decode(bomb, "0" * 64)


def test_content_hash_matches_encode_without_compression(
    document: ArchiveDocument, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hash-only validation uses the encoded object's exact canonical hash."""
    encoded = encode(document)

    def fail_compression(*args, **kwargs):
        pytest.fail("content hashing compressed the document")

    monkeypatch.setattr(archive_format.gzip, "compress", fail_compression)

    assert compute_content_hash(document) == encoded.content_hash


@pytest.mark.parametrize(
    "operation",
    [encode, compute_content_hash],
    ids=["encode", "hash"],
)
def test_encode_and_hash_apply_the_same_size_limit(
    document: ArchiveDocument,
    monkeypatch: pytest.MonkeyPatch,
    operation: Callable[[ArchiveDocument], object],
) -> None:
    """Compression and comparison reject the same oversized canonical input."""
    monkeypatch.setattr(archive_format, "MAX_DECODED_BYTES", 1)

    with pytest.raises(
        ExecutionRetentionConflictError, match="archive size limit"
    ):
        operation(document)
