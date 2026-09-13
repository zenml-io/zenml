# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Archive format version 1: one gzip-compressed JSON document per run.

A document carries the detail columns of one pipeline run, its steps, the
snapshots only that run uses, and their step configurations. The encoder
writes canonical JSON, so the SHA-256 of the decoded bytes, stored on the
bundle row, identifies the content exactly.

Documents are untrusted input on every read: decompression stops one byte
past the size cap, the hash is checked before any parsing, duplicate JSON
keys and non-finite numbers are rejected, every record model forbids unknown
fields, and the relational closure must hold. A newer format version is an
integrity error; there are no adapters.
"""

import gzip
import hashlib
import json
import zlib
from typing import Any, ClassVar, Dict, Iterator, List, Optional, Union
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    NaiveDatetime,
    ValidationError,
    model_validator,
)
from typing_extensions import Self

from zenml.enums import RetentionFailure
from zenml.exceptions import (
    ExecutionRetentionConflictError,
    ExecutionRetentionIntegrityError,
)

FORMAT_VERSION = 1
MAX_RECORDS = 50_000
MAX_DECODED_BYTES = 64 * 1024 * 1024
# gzip can grow incompressible input by a few bytes per 16 KiB block.
MAX_OBJECT_BYTES = MAX_DECODED_BYTES + 1024 * 1024


class ArchivedRecord(BaseModel):
    """Archived detail of one SQL row plus its retained identity."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    archived_columns: ClassVar[tuple[str, ...]]

    id: UUID
    created: NaiveDatetime
    updated: NaiveDatetime


class RunRecord(ArchivedRecord):
    """Run detail; ownership columns are compared again on restore."""

    archived_columns: ClassVar[tuple[str, ...]] = (
        "orchestrator_environment",
        "exception_info",
        "pipeline_configuration",
        "client_environment",
    )
    project_id: UUID
    snapshot_id: Optional[UUID]
    orchestrator_environment: Optional[str]
    exception_info: Optional[str]
    pipeline_configuration: Optional[str]
    client_environment: Optional[str]


class StepRecord(ArchivedRecord):
    """Step detail plus the projections kept in SQL while archived."""

    archived_columns: ClassVar[tuple[str, ...]] = (
        "exception_info",
        "step_configuration",
    )
    project_id: UUID
    pipeline_run_id: UUID
    snapshot_id: Optional[UUID]
    name: str
    exception_info: Optional[str]
    step_configuration: Optional[str]
    step_type: Optional[str]
    substitutions: Dict[str, str]


class SnapshotRecord(ArchivedRecord):
    """Detail of a snapshot that only the archived run uses."""

    archived_columns: ClassVar[tuple[str, ...]] = (
        "pipeline_configuration",
        "client_environment",
        "pipeline_spec",
        "source_code",
        "description",
    )
    project_id: UUID
    pipeline_configuration: str
    client_environment: str
    pipeline_spec: Optional[str]
    source_code: Optional[str]
    description: Optional[str]


class ConfigurationRecord(ArchivedRecord):
    """Complete step configuration row with exactly one owner."""

    archived_columns: ClassVar[tuple[str, ...]] = (
        "id",
        "created",
        "updated",
        "index",
        "name",
        "config",
        "snapshot_id",
        "step_run_id",
    )
    index: int
    name: str
    config: str
    snapshot_id: Optional[UUID]
    step_run_id: Optional[UUID]

    @model_validator(mode="after")
    def validate_owner(self) -> Self:
        """Require exactly one owner.

        Returns:
            The validated record.

        Raises:
            ValueError: If ownership is missing or ambiguous.
        """
        if (self.snapshot_id is None) == (self.step_run_id is None):
            raise ValueError("Configuration must have exactly one owner.")
        return self


Record = Union[RunRecord, StepRecord, SnapshotRecord, ConfigurationRecord]


class ArchiveDocument(BaseModel):
    """The archived detail of one pipeline run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    format_version: int = FORMAT_VERSION
    project_id: UUID
    run_id: UUID
    run: RunRecord
    steps: List[StepRecord]
    snapshots: List[SnapshotRecord]
    configurations: List[ConfigurationRecord]

    @model_validator(mode="after")
    def validate_closure(self) -> Self:
        """Require every record to belong to this run and project.

        Returns:
            The validated document.

        Raises:
            ValueError: If a record falls outside the archived run.
        """
        if self.format_version != FORMAT_VERSION:
            raise ValueError("Unsupported archive format version.")
        if self.run.id != self.run_id:
            raise ValueError("Run record does not match the document.")
        if self.record_count > MAX_RECORDS:
            raise ValueError("Document exceeds the record limit.")
        owners: List[Union[RunRecord, StepRecord, SnapshotRecord]] = [
            self.run,
            *self.steps,
            *self.snapshots,
        ]
        if any(owner.project_id != self.project_id for owner in owners):
            raise ValueError("Record belongs to another project.")
        if any(step.pipeline_run_id != self.run_id for step in self.steps):
            raise ValueError("Step belongs to another run.")
        identities = [record.id for record in self.records()]
        if len(identities) != len(set(identities)):
            raise ValueError("Duplicate record identity.")
        snapshot_ids = {snapshot.id for snapshot in self.snapshots}
        referenced = {self.run.snapshot_id} | {
            step.snapshot_id for step in self.steps
        }
        if not snapshot_ids <= referenced:
            raise ValueError("Snapshot is not used by the archived run.")
        step_ids = {step.id for step in self.steps}
        for configuration in self.configurations:
            if (
                configuration.snapshot_id is not None
                and configuration.snapshot_id not in snapshot_ids
                or configuration.step_run_id is not None
                and configuration.step_run_id not in step_ids
            ):
                raise ValueError("Configuration owner is outside the run.")
        return self

    @property
    def record_count(self) -> int:
        """Count the SQL rows this document covers.

        Returns:
            One run plus every step, snapshot, and configuration.
        """
        return (
            1
            + len(self.steps)
            + len(self.snapshots)
            + len(self.configurations)
        )

    def records(self) -> Iterator[Record]:
        """Iterate records in lock and restore order.

        Yields:
            The run, then steps, snapshots, and configurations.
        """
        yield self.run
        yield from self.steps
        yield from self.snapshots
        yield from self.configurations


class EncodedDocument(BaseModel):
    """Compressed object bytes and the hash of their decoded content."""

    model_config = ConfigDict(frozen=True)

    data: bytes
    content_hash: str


def canonical_json(value: Any) -> bytes:
    """Encode JSON with one byte representation per value.

    Args:
        value: JSON-compatible value.

    Returns:
        Sorted, compact UTF-8 bytes.
    """
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _serialize_and_hash(document: ArchiveDocument) -> tuple[bytes, str]:
    """Serialize, bound, and hash one archive document canonically.

    Args:
        document: Captured run detail.

    Returns:
        The canonical bytes and their SHA-256 hash.

    Raises:
        ExecutionRetentionConflictError: The document exceeds the size cap.
    """
    decoded = canonical_json(document.model_dump(mode="json"))
    if len(decoded) > MAX_DECODED_BYTES:
        raise ExecutionRetentionConflictError(
            "Run exceeds the archive size limit.",
            error_code=RetentionFailure.OVERSIZED,
        )
    return decoded, hashlib.sha256(decoded).hexdigest()


def compute_content_hash(document: ArchiveDocument) -> str:
    """Compute the bounded canonical content hash without compression.

    Args:
        document: Captured run detail.

    Returns:
        The SHA-256 hash used by encoded archive objects.

    Raises:
        ExecutionRetentionConflictError: The document exceeds the size cap.
    """  # noqa: DOC502
    _, content_hash = _serialize_and_hash(document)
    return content_hash


def encode(document: ArchiveDocument) -> EncodedDocument:
    """Serialize and compress a document deterministically.

    Args:
        document: Captured run detail.

    Returns:
        The object bytes and content hash.

    Raises:
        ExecutionRetentionConflictError: The document exceeds the size cap.
    """  # noqa: DOC502
    decoded, content_hash = _serialize_and_hash(document)
    return EncodedDocument(
        data=gzip.compress(decoded, mtime=0),
        content_hash=content_hash,
    )


def decode(data: bytes, content_hash: str) -> ArchiveDocument:
    """Verify and parse untrusted object bytes.

    Args:
        data: Compressed object bytes read from storage.
        content_hash: Expected hash of the decoded content.

    Returns:
        The validated document.

    Raises:
        ExecutionRetentionIntegrityError: The bytes are oversized, corrupt,
            modified, malformed, or in an unsupported format version.
    """
    if len(data) > MAX_OBJECT_BYTES:
        raise ExecutionRetentionIntegrityError("Archive object is oversized.")
    decoder = zlib.decompressobj(wbits=31)
    try:
        decoded = decoder.decompress(data, MAX_DECODED_BYTES + 1)
    except zlib.error as error:
        raise ExecutionRetentionIntegrityError(
            "Archive object is not valid gzip data."
        ) from error
    if len(decoded) > MAX_DECODED_BYTES or decoder.unconsumed_tail:
        raise ExecutionRetentionIntegrityError(
            "Archive content exceeds the size limit."
        )
    if not decoder.eof or decoder.unused_data:
        raise ExecutionRetentionIntegrityError(
            "Archive object is truncated or has trailing data."
        )
    if hashlib.sha256(decoded).hexdigest() != content_hash:
        raise ExecutionRetentionIntegrityError(
            "Archive content does not match its recorded hash."
        )
    try:
        fields = json.loads(
            decoded.decode("utf-8"),
            object_pairs_hook=_unique_keys,
            parse_constant=_reject_constant,
        )
    except ValueError as error:
        raise ExecutionRetentionIntegrityError(
            "Archive content is not valid JSON."
        ) from error
    if not isinstance(fields, dict):
        raise ExecutionRetentionIntegrityError(
            "Archive content is not a JSON object."
        )
    version = fields.get("format_version")
    # bool is an int subclass, but True is not format version 1.
    if type(version) is not int or version < 1:
        raise ExecutionRetentionIntegrityError(
            "Archive format version is malformed."
        )
    if version != FORMAT_VERSION:
        raise ExecutionRetentionIntegrityError(
            f"Archive format {version} requires a newer server; this server "
            f"reads format {FORMAT_VERSION}."
        )
    try:
        return ArchiveDocument.model_validate(fields)
    except ValidationError as error:
        raise ExecutionRetentionIntegrityError(
            "Archive content failed validation."
        ) from error


def _unique_keys(pairs: List[tuple[str, Any]]) -> Dict[str, Any]:
    """Reject ambiguous repeated object keys.

    Args:
        pairs: JSON object entries in source order.

    Returns:
        An object with unique keys.

    Raises:
        ValueError: If the same key occurs twice.
    """
    unique: Dict[str, Any] = {}
    for key, item in pairs:
        if key in unique:
            raise ValueError("Duplicate JSON key.")
        unique[key] = item
    return unique


def _reject_constant(constant: str) -> None:
    """Reject non-finite JSON numbers.

    Args:
        constant: Non-standard numeric token.

    Raises:
        ValueError: Always, because these tokens are outside JSON.
    """
    raise ValueError(f"Invalid JSON constant: {constant}.")
