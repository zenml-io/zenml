# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Bounded decompression, content integrity, and strict bundle ownership."""

import gzip
import hashlib
from uuid import uuid4

import pytest
from sqlmodel import Session

from zenml.exceptions import (
    ExecutionRetentionIntegrityError,
)
from zenml.zen_stores.retention import format as archive_format
from zenml.zen_stores.retention.format import (
    canonical_json,
    decode,
)
from zenml.zen_stores.schemas import ArchiveBundleSchema


@pytest.fixture
def document(retention_store, run_factory, archive_run, storage):
    """Read the document emitted by a real archive pass."""
    ids = run_factory(retention_store)
    bundle_id = archive_run(retention_store, ids)
    with Session(retention_store.engine) as session:
        bundle = session.get(ArchiveBundleSchema, bundle_id)
    document = decode(
        storage.read(bundle.uri, bundle.size_bytes), bundle.content_hash
    )
    return document


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
