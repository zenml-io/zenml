# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Frozen V1 records and canonical, section-checksummed JSON lines."""

import hashlib
import json
from typing import (
    Annotated,
    Any,
    ClassVar,
    Dict,
    List,
    Literal,
    Optional,
    Type,
    Union,
)
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    NaiveDatetime,
    model_validator,
)
from typing_extensions import Self

# Shared capture, object-write, and verified-read limits.
MAX_RECORDS = 10_000
MAX_DECODED_BYTES = 16 * 1024 * 1024
MAX_OBJECT_BYTES = 32 * 1024 * 1024
Sha256Hex = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
TableName = Literal[
    "pipeline_run",
    "step_run",
    "pipeline_snapshot",
    "step_configuration",
]
TABLE_ORDER: tuple[TableName, ...] = (
    "pipeline_run",
    "step_run",
    "pipeline_snapshot",
    "step_configuration",
)


class UnsupportedArchiveFormatError(ValueError):
    """Identify a valid format version that needs a different server reader."""


class ArchivedRecord(BaseModel):
    """Freeze archived payload fields and their retained row identity."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    table: ClassVar[TableName]
    archived_columns: ClassVar[tuple[str, ...]]
    id: UUID
    created: NaiveDatetime
    updated: NaiveDatetime


class RunRecord(ArchivedRecord):
    """Run detail with retained ownership context, never restored headers."""

    table: ClassVar[TableName] = "pipeline_run"
    archived_columns: ClassVar[tuple[str, ...]] = (
        "orchestrator_environment",
        "exception_info",
        "pipeline_configuration",
        "client_environment",
    )
    project_id: UUID
    root_run_id: Optional[UUID]
    parent_run_id: Optional[UUID]
    snapshot_id: Optional[UUID]
    orchestrator_environment: Optional[str]
    exception_info: Optional[str]
    pipeline_configuration: Optional[str]
    client_environment: Optional[str]


class StepRecord(ArchivedRecord):
    """Step detail plus projections obtained from the unarchived reader."""

    table: ClassVar[TableName] = "step_run"
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
    """Only exclusively owned snapshot detail may be retired."""

    table: ClassVar[TableName] = "pipeline_snapshot"
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
    """Complete configuration row with exactly one surviving owner."""

    table: ClassVar[TableName] = "step_configuration"
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
        """Require one owner.

        Returns:
            The validated row.

        Raises:
            ValueError: If ownership is missing or ambiguous.
        """
        if (self.snapshot_id is None) == (self.step_run_id is None):
            raise ValueError("Configuration must have exactly one owner.")
        return self


Record = Union[
    RunRecord,
    StepRecord,
    SnapshotRecord,
    ConfigurationRecord,
]
RECORDS_BY_TABLE: Dict[TableName, Type[Record]] = {
    record.table: record
    for record in (
        RunRecord,
        StepRecord,
        SnapshotRecord,
        ConfigurationRecord,
    )
}


def canonical_json(value: Dict[str, Any]) -> bytes:
    """Encode an outer record without changing text stored inside it.

    Args:
        value: JSON-compatible values.

    Returns:
        Stable UTF-8 bytes.
    """
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    """Hash exact bytes.

    Args:
        data: Bytes to fingerprint.

    Returns:
        Lowercase SHA-256.
    """
    return hashlib.sha256(data).hexdigest()


def record_bytes(record: Record) -> bytes:
    """Encode a record as one canonical line.

    Args:
        record: Explicitly typed record.

    Returns:
        A newline-terminated JSON record.
    """
    return canonical_json(record.model_dump(mode="json")) + b"\n"


def strict_json(data: bytes) -> Dict[str, Any]:
    """Parse a JSON object; callers enforce canonical bytes after validation.

    Args:
        data: Bounded UTF-8 JSON.

    Returns:
        The decoded object.

    Raises:
        ValueError: If the JSON is malformed or ambiguous.
    """
    decoded_object = json.loads(
        data.decode("utf-8"),
        object_pairs_hook=_unique_keys,
        parse_constant=_reject_constant,
    )
    if not isinstance(decoded_object, dict):
        raise ValueError("Expected a JSON object.")
    return decoded_object


def _unique_keys(pairs: List[tuple[str, Any]]) -> Dict[str, Any]:
    """Reject ambiguous repeated object keys.

    Args:
        pairs: JSON object entries in source order.

    Returns:
        An object with unique keys.

    Raises:
        ValueError: If the same key occurs twice.
    """
    unique_entries: Dict[str, Any] = {}
    for key, item in pairs:
        if key in unique_entries:
            raise ValueError("Duplicate JSON key.")
        unique_entries[key] = item
    return unique_entries


def _reject_constant(constant: str) -> None:
    """Reject non-finite JSON numbers.

    Args:
        constant: Non-standard numeric token.

    Raises:
        ValueError: Always, because these tokens are outside JSON.
    """
    raise ValueError(f"Invalid JSON constant: {constant}.")


def parse_record(data: bytes, cls: Type[Record]) -> Record:
    """Validate a bounded canonical record.

    Args:
        data: A single JSON line.
        cls: Record class selected by the enclosing section.

    Returns:
        The typed record.

    Raises:
        ValueError: If its encoding or fields are invalid.
    """
    if len(data) > MAX_DECODED_BYTES:
        raise ValueError("Record exceeds decoded size limit.")
    record = cls.model_validate(strict_json(data))
    if record_bytes(record) != data:
        raise ValueError("Record is not canonical JSONL.")
    return record


class Section(BaseModel):
    """A manifest's exact section identity, count and checksum."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    table: TableName
    ids: List[UUID] = Field(max_length=MAX_RECORDS)
    decoded_bytes: int = Field(ge=0, le=MAX_DECODED_BYTES)
    sha256: Sha256Hex


class Manifest(BaseModel):
    """The immutable V1 manifest, containing four metadata-free sections."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    MAX_BYTES: ClassVar[int] = 2 * 1024 * 1024
    format_version: Literal[1] = 1
    bundle_id: UUID
    project_id: UUID
    root_run_id: UUID
    created_at: NaiveDatetime
    object_bytes: int = Field(gt=0, le=MAX_OBJECT_BYTES)
    object_sha256: Sha256Hex
    sections: List[Section] = Field(min_length=4, max_length=4)

    @model_validator(mode="after")
    def validate_sections(self) -> Self:
        """Require every section and enforce the aggregate bounds.

        Returns:
            The validated manifest.

        Raises:
            ValueError: If sections or total sizes violate the format.
        """
        tables = [section.table for section in self.sections]
        if tables != list(TABLE_ORDER):
            raise ValueError(
                "Manifest must contain all four ordered sections."
            )
        if any(
            section.ids != sorted(set(section.ids))
            for section in self.sections
        ):
            raise ValueError("Invalid section IDs.")
        if (
            sum(len(s.ids) for s in self.sections) > MAX_RECORDS
            or sum(s.decoded_bytes for s in self.sections) > MAX_DECODED_BYTES
        ):
            raise ValueError("Bundle exceeds tree limits.")
        return self

    @classmethod
    def from_bytes(cls, data: bytes) -> "Manifest":
        """Distinguish version skew from malformed manifests.

        Args:
            data: Untrusted manifest bytes.

        Returns:
            A validated manifest.

        Raises:
            ValueError: If malformed or oversized.
            UnsupportedArchiveFormatError: The archive requires another reader version.
        """
        if len(data) > cls.MAX_BYTES:
            raise ValueError("Manifest exceeds size limit.")
        manifest_fields = strict_json(data)
        version = manifest_fields.get("format_version")
        # bool is an int subclass, but True is not format version 1.
        if type(version) is not int or version < 1:
            raise ValueError("Malformed archive format version.")
        if version != 1:
            raise UnsupportedArchiveFormatError(
                f"Archive format {version} requires a compatible server; supported: 1."
            )
        manifest = cls.model_validate(manifest_fields)
        if canonical_json(manifest.model_dump(mode="json")) != data:
            raise ValueError("Manifest is not canonical.")
        return manifest
