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
"""Object kinds and the manifest of an archive generation."""

from datetime import datetime
from typing import Dict, List, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeInt,
    PositiveInt,
    model_validator,
)

from zenml.models import ExecutionArchiveObject
from zenml.models.v2.misc.execution_archive import Sha256Digest
from zenml.utils.enum_utils import StrEnum
from zenml.utils.time_utils import utc_now


class ArchiveObjectKind(StrEnum):
    """Kinds of content-addressed objects an archive generation writes."""

    MANIFEST = "manifests"
    EXECUTION = "executions"
    SNAPSHOT = "snapshots"
    PROBE = "probes"

    @property
    def extension(self) -> str:
        """The file extension of objects of this kind.

        Returns:
            The extension.
        """
        return {
            ArchiveObjectKind.MANIFEST: "json",
            ArchiveObjectKind.EXECUTION: "json.gz",
            ArchiveObjectKind.SNAPSHOT: "json.gz",
            ArchiveObjectKind.PROBE: "bin",
        }[self]


class ExecutionArchiveManifest(BaseModel):
    """Closure proof of one archived execution family.

    Lists every row the archive covers and the two objects holding their
    payload, so verification and restore can check completeness.
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
    run_ids: List[UUID] = Field(min_length=1)
    step_run_ids: List[UUID] = Field(default_factory=list)
    snapshot_ids: List[UUID] = Field(default_factory=list)
    static_configuration_ids: List[UUID] = Field(default_factory=list)
    table_counts: Dict[str, NonNegativeInt] = Field(default_factory=dict)
    storage_target_id: UUID
    execution_payload: ExecutionArchiveObject
    snapshot_payload: ExecutionArchiveObject
    created_at: datetime = Field(default_factory=utc_now)

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def _validate_unique_entities(self) -> "ExecutionArchiveManifest":
        """Reject repeated row IDs.

        Returns:
            The validated manifest.

        Raises:
            ValueError: If a row ID is repeated.
        """
        for name, identifiers in (
            ("run_ids", self.run_ids),
            ("step_run_ids", self.step_run_ids),
            ("snapshot_ids", self.snapshot_ids),
            ("static_configuration_ids", self.static_configuration_ids),
        ):
            if len(identifiers) != len(set(identifiers)):
                raise ValueError(f"Archive {name} must be unique.")
        return self

    @property
    def stored_bytes(self) -> int:
        """Total bytes of the two payload objects.

        Returns:
            The stored bytes.
        """
        return int(self.execution_payload.stored_bytes) + int(
            self.snapshot_payload.stored_bytes
        )
