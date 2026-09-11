# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Archive format version 1: determinism, hostile objects, and the golden file."""

import gzip
import hashlib
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict
from uuid import UUID, uuid4

import pytest
from sqlalchemy import DateTime, Uuid
from sqlmodel import SQLModel

from tests.unit.zen_stores.retention.fixture_graph import (
    DETAIL_TABLES,
    golden_document,
    insert_rows,
    read_tables,
)
from zenml.enums import RestoreOutcome, RetentionFailure
from zenml.exceptions import (
    ExecutionRetentionConflictError,
    ExecutionRetentionIntegrityError,
)
from zenml.utils.json_utils import pydantic_encoder
from zenml.zen_stores.retention import format as archive_format
from zenml.zen_stores.retention.format import (
    ArchiveDocument,
    canonical_json,
    decode,
    encode,
)
from zenml.zen_stores.schemas import ArchiveBundleSchema

FIXTURES = Path(__file__).parent / "fixtures"


def golden_source() -> Dict[str, Any]:
    """Load the golden SQL rows with typed UUID and datetime values.

    Returns:
        Rows grouped by table, as the generator built them.
    """
    source = json.loads((FIXTURES / "v1-sql.json").read_text())["before"]
    for name, table_rows in source.items():
        for row in table_rows:
            for column, value in row.items():
                sql_type = SQLModel.metadata.tables[name].c[column].type
                if value is not None and isinstance(sql_type, Uuid):
                    row[column] = UUID(value)
                elif value is not None and isinstance(sql_type, DateTime):
                    row[column] = datetime.fromisoformat(value)
    return source


@pytest.fixture
def document() -> ArchiveDocument:
    """Provide the golden run's document."""
    return golden_document(golden_source())


def seal(fields: Dict[str, Any]) -> tuple[bytes, str]:
    """Compress arbitrary JSON with a matching content hash.

    Args:
        fields: JSON object, possibly invalid as a document.

    Returns:
        Object bytes and the hash of their decoded content.
    """
    decoded = canonical_json(fields)
    return gzip.compress(decoded, mtime=0), hashlib.sha256(decoded).hexdigest()


def test_encoding_is_deterministic_and_round_trips(document):
    """The same document always produces the same bytes and hash."""
    first, second = encode(document), encode(document)

    assert first == second
    assert decode(first.data, first.content_hash) == document


def test_golden_object_decodes_to_the_golden_document(document):
    """The checked-in object is exactly what today's encoder writes."""
    bundle = json.loads((FIXTURES / "v1-bundle.json").read_text())
    data = (FIXTURES / "v1-document.json.gz").read_bytes()

    assert decode(data, bundle["content_hash"]) == document
    assert encode(document).data == data


def mutate(change: Callable[[Dict[str, Any]], None]) -> Callable:
    """Build a test case that edits a valid document's JSON.

    Args:
        change: Edit applied to the document fields in place.

    Returns:
        A function producing sealed bytes and hash from a document.
    """

    def build(document: ArchiveDocument) -> tuple[bytes, str]:
        fields = document.model_dump(mode="json")
        change(fields)
        return seal(fields)

    return build


def raw(decoded: bytes) -> Callable:
    """Build a test case from literal decoded content.

    Args:
        decoded: Content to compress and hash as-is.

    Returns:
        A function producing sealed bytes and hash.
    """
    return lambda document: (
        gzip.compress(decoded, mtime=0),
        hashlib.sha256(decoded).hexdigest(),
    )


def with_step_of_another_run(fields: Dict[str, Any]) -> None:
    """Move a step to another run."""
    fields["steps"][0]["pipeline_run_id"] = str(uuid4())


def with_foreign_configuration(fields: Dict[str, Any]) -> None:
    """Give a configuration an owner outside the document."""
    fields["configurations"][0]["snapshot_id"] = str(uuid4())


def with_extra_field(fields: Dict[str, Any]) -> None:
    """Add a field no record model declares."""
    fields["run"]["unexpected"] = "value"


def with_version(version: Any) -> Callable[[Dict[str, Any]], None]:
    """Set the document format version."""

    def change(fields: Dict[str, Any]) -> None:
        fields["format_version"] = version

    return change


@pytest.mark.parametrize(
    "build,message",
    [
        (mutate(with_step_of_another_run), "failed validation"),
        (mutate(with_foreign_configuration), "failed validation"),
        (mutate(with_extra_field), "failed validation"),
        (mutate(with_version(2)), "format 2 requires a newer server"),
        (raw(b'{"run_id": 1, "run_id": 2}'), "not valid JSON"),
    ],
    ids=[
        "step-of-another-run",
        "configuration-outside-run",
        "extra-field",
        "newer-version",
        "duplicate-key",
    ],
)
def test_decode_rejects_invalid_content(document, build, message):
    """Content that hashes correctly is still validated completely."""
    data, content_hash = build(document)

    with pytest.raises(ExecutionRetentionIntegrityError, match=message):
        decode(data, content_hash)


def test_decode_rejects_modified_content(document):
    """Any change to the content breaks its recorded hash."""
    encoded = encode(document)
    fields = document.model_dump(mode="json")
    fields["run"]["exception_info"] = "tampered"
    data, _ = seal(fields)

    with pytest.raises(ExecutionRetentionIntegrityError, match="hash"):
        decode(data, encoded.content_hash)


@pytest.mark.parametrize(
    "corrupt,message",
    [
        (lambda data: data[:-8], "truncated or has trailing data"),
        (lambda data: b"not gzip" + data, "not valid gzip"),
    ],
    ids=["truncated", "not-gzip"],
)
def test_decode_rejects_corrupt_objects(document, corrupt, message):
    """Truncated, padded, or foreign bytes never reach the JSON parser."""
    encoded = encode(document)

    with pytest.raises(ExecutionRetentionIntegrityError, match=message):
        decode(corrupt(encoded.data), encoded.content_hash)


def test_decompression_stops_at_the_size_cap(monkeypatch):
    """A compression bomb is rejected one byte past the cap."""
    monkeypatch.setattr(archive_format, "MAX_DECODED_BYTES", 1024)
    bomb = gzip.compress(b" " * (1024 * 1024), mtime=0)

    with pytest.raises(ExecutionRetentionIntegrityError, match="size limit"):
        decode(bomb, "0" * 64)


def test_encoding_refuses_documents_over_the_size_cap(document, monkeypatch):
    """The pass counts a run whose document is too large as oversized."""
    monkeypatch.setattr(archive_format, "MAX_DECODED_BYTES", 1024)

    with pytest.raises(ExecutionRetentionConflictError) as error:
        encode(document)

    assert error.value.error_code == RetentionFailure.OVERSIZED


def test_golden_object_restores_into_the_current_schema(
    retention_store, storage
):
    """Restore the frozen version 1 object into today's SQL schema."""
    bundle = json.loads((FIXTURES / "v1-bundle.json").read_text())
    data = (FIXTURES / "v1-document.json.gz").read_bytes()
    before = golden_source()
    bundle_id = UUID(bundle["bundle_id"])
    run_id = UUID(bundle["run_id"])
    project_id = UUID(bundle["project_id"])
    uri = storage.object_uri(project_id, run_id, bundle_id)
    storage.write(uri, data)
    archived = deepcopy(before)
    # The frozen clearing contract of format version 1.
    cleared = {
        "pipeline_run": (
            "orchestrator_environment exception_info "
            "pipeline_configuration client_environment"
        ),
        "pipeline_snapshot": "pipeline_spec source_code description",
        "step_run": "exception_info step_configuration",
    }
    archived["step_configuration"] = []
    for name, columns in cleared.items():
        for row in archived[name]:
            row.update({column: None for column in columns.split()})
            row["archive_bundle_id"] = bundle_id
            if name == "pipeline_snapshot":
                row.update(
                    pipeline_configuration="{}", client_environment="{}"
                )
    created = datetime.fromisoformat(bundle["created"])
    archived["archive_bundle"] = [
        ArchiveBundleSchema(
            id=bundle_id,
            project_id=project_id,
            run_id=run_id,
            created=created,
            updated=created,
            uri=uri,
            size_bytes=bundle["size_bytes"],
            content_hash=bundle["content_hash"],
            format_version=1,
        ).model_dump()
    ]
    insert_rows(retention_store, archived)

    restored = retention_store.restore_pipeline_run(run_id)

    assert restored.outcome == RestoreOutcome.RESTORED
    actual = json.loads(
        json.dumps(read_tables(retention_store), default=pydantic_encoder)
    )
    expected = json.loads(json.dumps(before, default=pydantic_encoder))
    for name in DETAIL_TABLES:
        assert actual[name] == expected[name], name
