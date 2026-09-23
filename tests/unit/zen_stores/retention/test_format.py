# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Bounded decompression, content integrity, and strict bundle ownership."""

import gzip
import hashlib
from datetime import datetime
from uuid import uuid4

import pytest

from zenml.exceptions import (
    ExecutionRetentionIntegrityError,
)
from zenml.zen_stores.retention import format as archive_format
from zenml.zen_stores.retention.format import (
    ArchiveDocument,
    canonical_json,
    decode,
)


@pytest.fixture
def document() -> ArchiveDocument:
    """Build one run, step, and configuration for corruption checks.

    Returns:
        The verified v1 document.
    """
    project_id, run_id, step_id = uuid4(), uuid4(), uuid4()
    timestamps = {
        "created": datetime(2026, 1, 1),
        "updated": datetime(2026, 1, 1),
    }
    archive = ArchiveDocument(
        project_id=project_id,
        run_id=run_id,
        run=archive_format.RunRecord(
            id=run_id,
            **timestamps,
            project_id=project_id,
            snapshot_id=None,
            orchestrator_environment=None,
            exception_info=None,
            pipeline_configuration=None,
            client_environment=None,
        ),
        steps=[
            archive_format.StepRecord(
                id=step_id,
                **timestamps,
                project_id=project_id,
                pipeline_run_id=run_id,
                snapshot_id=None,
                name="step",
                exception_info=None,
                step_configuration=None,
                source_code=None,
                docstring=None,
                step_type=None,
                substitutions={},
            )
        ],
        snapshots=[],
        configurations=[
            archive_format.ConfigurationRecord(
                id=uuid4(),
                **timestamps,
                index=0,
                name="step",
                config="{}",
                snapshot_id=None,
                step_run_id=step_id,
            )
        ],
    )
    raw = canonical_json(archive.model_dump(mode="json"))
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
        fields["configurations"][0]["step_run_id"] = str(uuid4())
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
