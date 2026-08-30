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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
#  implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Immutable versioned payloads for archived execution trees."""

import json
from datetime import datetime
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
    TypeAlias,
)
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PositiveInt,
    ValidationError,
    model_validator,
)

from zenml.models.v2.misc.execution_archive import Sha256Digest
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.execution_archive.codec import (
    canonical_json,
    sha256_digest,
)
from zenml.zen_stores.execution_archive.exceptions import (
    ArchiveObjectInvalidError,
)


class _ExecutionArchivePayloadModel(BaseModel):
    """Strict immutable base for persisted execution archive records."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ArchivedPipelineRunPayload(_ExecutionArchivePayloadModel):
    """Payload columns of one pipeline run."""

    id: UUID
    orchestrator_environment: Optional[str] = None
    exception_info: Optional[str] = None
    pipeline_configuration: Optional[str] = None
    client_environment: Optional[str] = None


class ArchivedStepRunPayload(_ExecutionArchivePayloadModel):
    """Payload columns of one step run."""

    id: UUID
    source_code: Optional[str] = None
    docstring: Optional[str] = None
    exception_info: Optional[str] = None
    step_configuration: Optional[str] = None


class ArchivedPipelineSnapshotPayload(_ExecutionArchivePayloadModel):
    """Payload columns of one pipeline snapshot."""

    id: UUID
    pipeline_configuration: str
    client_environment: str
    pipeline_spec: Optional[str] = None
    source_code: Optional[str] = None


class ArchivedStepConfigurationPayload(_ExecutionArchivePayloadModel):
    """Payload columns of one static or dynamic step configuration."""

    id: UUID
    snapshot_id: Optional[UUID] = None
    step_run_id: Optional[UUID] = None
    index: int
    name: str
    config: str

    @model_validator(mode="after")
    def _validate_single_owner(self) -> "ArchivedStepConfigurationPayload":
        """Require exactly one owner.

        Returns:
            The validated payload.

        Raises:
            ValueError: If the owner is missing or ambiguous.
        """
        if (self.snapshot_id is None) == (self.step_run_id is None):
            raise ValueError(
                "An archived step configuration needs exactly one owner."
            )
        return self


class ExecutionArchivePayloadV1(_ExecutionArchivePayloadModel):
    """Immutable version-one object for one root execution tree.

    This model is a persisted wire contract and must never gain, lose, or
    reinterpret fields. Format evolution requires a new versioned model and
    decoder entry.
    """

    schema_version: Literal[1] = 1
    archive_id: UUID
    workspace_id: UUID
    project_id: UUID
    root_run_id: UUID
    generation: PositiveInt
    writer_version: str = Field(min_length=1, max_length=64)
    writer_alembic_revision: str = Field(min_length=1, max_length=64)
    source_fingerprint: Sha256Digest
    created_at: datetime = Field(default_factory=utc_now)
    runs: List[ArchivedPipelineRunPayload] = Field(min_length=1)
    steps: List[ArchivedStepRunPayload] = Field(default_factory=list)
    snapshots: List[ArchivedPipelineSnapshotPayload] = Field(
        default_factory=list
    )
    step_configurations: List[ArchivedStepConfigurationPayload] = Field(
        default_factory=list
    )

    @model_validator(mode="after")
    def _validate_closure(self) -> "ExecutionArchivePayloadV1":
        """Validate identity uniqueness and configuration ownership.

        Returns:
            The validated payload.

        Raises:
            ValueError: If the object is not a closed execution tree.
        """
        _require_unique("pipeline_run", [record.id for record in self.runs])
        _require_unique("step_run", [record.id for record in self.steps])
        _require_unique(
            "pipeline_snapshot", [record.id for record in self.snapshots]
        )
        _require_unique(
            "step_configuration",
            [record.id for record in self.step_configurations],
        )
        if self.root_run_id not in {run.id for run in self.runs}:
            raise ValueError("The archive payload must contain its root run.")

        step_ids = {step.id for step in self.steps}
        snapshot_ids = {snapshot.id for snapshot in self.snapshots}
        for configuration in self.step_configurations:
            if (
                configuration.step_run_id is not None
                and configuration.step_run_id not in step_ids
            ) or (
                configuration.snapshot_id is not None
                and configuration.snapshot_id not in snapshot_ids
            ):
                raise ValueError(
                    "Every archived step configuration must belong to an "
                    "archived step run or snapshot."
                )
        return self


ExecutionArchivePayload: TypeAlias = ExecutionArchivePayloadV1

_PayloadDecoder: TypeAlias = Callable[
    [Dict[str, Any]], ExecutionArchivePayload
]


ARCHIVED_RUN_FIELDS: Tuple[str, ...] = (
    "orchestrator_environment",
    "exception_info",
    "pipeline_configuration",
    "client_environment",
)
ARCHIVED_STEP_FIELDS: Tuple[str, ...] = (
    "source_code",
    "docstring",
    "exception_info",
    "step_configuration",
)
ARCHIVED_SNAPSHOT_FIELDS: Tuple[str, ...] = (
    "pipeline_configuration",
    "client_environment",
    "pipeline_spec",
    "source_code",
)
ARCHIVED_CONFIGURATION_FIELDS: Tuple[str, ...] = ("config",)


def execution_archive_source_fingerprint(
    *,
    runs: Sequence[ArchivedPipelineRunPayload],
    steps: Sequence[ArchivedStepRunPayload],
    snapshots: Sequence[ArchivedPipelineSnapshotPayload],
    step_configurations: Sequence[ArchivedStepConfigurationPayload],
) -> str:
    """Fingerprint version-one source records independently of compression.

    Args:
        runs: Archived run payload records.
        steps: Archived step payload records.
        snapshots: Archived snapshot payload records.
        step_configurations: Archived configuration records.

    Returns:
        SHA-256 digest of deterministic semantic JSON.
    """
    return sha256_digest(
        canonical_json(
            {
                "runs": [record.model_dump(mode="json") for record in runs],
                "steps": [record.model_dump(mode="json") for record in steps],
                "snapshots": [
                    record.model_dump(mode="json") for record in snapshots
                ],
                "step_configurations": [
                    record.model_dump(mode="json")
                    for record in step_configurations
                ],
            }
        )
    )


def payload_source_fingerprint(payload: ExecutionArchivePayload) -> str:
    """Recompute the semantic fingerprint carried by an archive object.

    Args:
        payload: Decoded versioned archive payload.

    Returns:
        SHA-256 digest of its source records.
    """
    return execution_archive_source_fingerprint(
        runs=payload.runs,
        steps=payload.steps,
        snapshots=payload.snapshots,
        step_configurations=payload.step_configurations,
    )


def parse_execution_archive_payload(
    decoded: bytes,
) -> ExecutionArchivePayload:
    """Decode canonical bytes through the matching immutable format version.

    Args:
        decoded: Uncompressed canonical JSON bytes.

    Returns:
        Strictly validated versioned archive payload.

    Raises:
        ArchiveObjectInvalidError: If the bytes are malformed, unsupported,
            non-canonical, or carry an invalid semantic fingerprint.
    """
    try:
        value = json.loads(decoded)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ArchiveObjectInvalidError(
            "The execution archive payload is not valid JSON."
        ) from error
    if not isinstance(value, dict):
        raise ArchiveObjectInvalidError(
            "The execution archive payload must be a JSON object."
        )
    version = value.get("schema_version")
    decoder = _PAYLOAD_DECODERS.get(version) if type(version) is int else None
    if decoder is None:
        raise ArchiveObjectInvalidError(
            f"Unsupported execution archive schema version: {version!r}."
        )
    try:
        payload = decoder(value)
    except ValidationError as error:
        raise ArchiveObjectInvalidError(
            "The execution archive payload violates its versioned schema."
        ) from error
    if canonical_json(payload) != decoded:
        raise ArchiveObjectInvalidError(
            "The execution archive payload is not canonically encoded."
        )
    if payload_source_fingerprint(payload) != payload.source_fingerprint:
        raise ArchiveObjectInvalidError(
            "The execution archive payload has an invalid source fingerprint."
        )
    return payload


def _decode_v1(value: Dict[str, Any]) -> ExecutionArchivePayload:
    return ExecutionArchivePayloadV1.model_validate(value)


_PAYLOAD_DECODERS: Dict[int, _PayloadDecoder] = {1: _decode_v1}


def _require_unique(name: str, identifiers: List[UUID]) -> None:
    if len(identifiers) != len(set(identifiers)):
        raise ValueError(f"Archive payload {name} IDs must be unique.")
