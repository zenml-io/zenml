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
"""API models for execution-history archiving."""

from datetime import datetime
from typing import Annotated, List, Optional
from uuid import UUID

from pydantic import ConfigDict, Field, NonNegativeInt, StringConstraints

from zenml.enums import ExecutionArchiveState
from zenml.models.v2.base.base import BaseZenModel

Sha256Digest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]

MAX_ARCHIVE_MAINTENANCE_FAMILIES = 50


def validate_relative_path(value: str) -> str:
    """Require a relative path that cannot escape its root.

    Args:
        value: A slash-separated path.

    Returns:
        The validated path.

    Raises:
        ValueError: If the path is absolute, empty, or contains `.`/`..`.
    """
    parts = value.split("/")
    if (
        "\\" in value
        or value.startswith("/")
        or any(part in {"", ".", ".."} for part in parts)
    ):
        raise ValueError(
            "The path must be relative and must not contain empty, `.` or "
            "`..` segments."
        )
    return value


class ExecutionArchiveObject(BaseZenModel):
    """Reference to one content-addressed, immutable archive object.

    The digest identifies the object and is verified on every read; the
    object key is derived from it, so it is never stored.
    """

    sha256: Sha256Digest
    stored_bytes: NonNegativeInt

    model_config = ConfigDict(frozen=True)


class ExecutionArchiveResponse(BaseZenModel):
    """One archive generation of an execution family, as the catalog holds it.

    This is the only detached view of a catalog row: the archiver, the
    maintenance passes and the API all read it.
    """

    id: UUID
    project_id: UUID
    root_run_id: UUID
    generation: int
    state: ExecutionArchiveState
    source_fingerprint: str
    storage_target_id: UUID
    manifest: Optional[ExecutionArchiveObject] = Field(
        default=None, description="The manifest object, once exported."
    )
    execution_payload: Optional[ExecutionArchiveObject] = Field(
        default=None,
        description="The object holding the runs, step runs and dynamic "
        "step configurations, once exported.",
    )
    snapshot_payload: Optional[ExecutionArchiveObject] = Field(
        default=None,
        description="The object holding the snapshots and static step "
        "configurations, once exported.",
    )
    stored_bytes: Optional[int] = Field(
        default=None,
        description="Bytes of payload the family held in the database when "
        "it was captured.",
    )
    committed_at: Optional[datetime] = None
    compacted_at: Optional[datetime] = None
    restored_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created: datetime

    model_config = ConfigDict(frozen=True)


class ExecutionArchiveMaintenanceRequest(BaseZenModel):
    """Bounded archive maintenance pass over one project."""

    project: UUID = Field(description="The project to archive in.")
    root_run_ids: List[UUID] = Field(
        default_factory=list,
        max_length=MAX_ARCHIVE_MAINTENANCE_FAMILIES,
        description="Root runs to consider. If empty, the oldest completed "
        "root runs of the project that are not archived yet are considered.",
    )
    older_than_days: int = Field(
        default=180,
        ge=30,
        le=3650,
        description="Only families unchanged for at least this many days "
        "are archived.",
    )
    limit: int = Field(
        default=25,
        ge=1,
        le=MAX_ARCHIVE_MAINTENANCE_FAMILIES,
        description="Maximum number of execution families to consider.",
    )


class ExecutionArchiveCandidate(BaseZenModel):
    """Eligibility of one execution family."""

    root_run_id: UUID
    eligible: bool
    eligible_at: Optional[datetime] = None
    stored_bytes: Optional[int] = Field(
        default=None,
        description="Bytes of payload the family holds in the database.",
    )
    blockers: List[str] = Field(default_factory=list)
    archive_id: Optional[UUID] = None
    archive_state: Optional[ExecutionArchiveState] = None


class ExecutionArchiveMaintenanceResponse(BaseZenModel):
    """Result of a dry run, or the task scheduled for an apply."""

    candidates: List[ExecutionArchiveCandidate] = Field(
        default_factory=list,
        description="Eligibility of every considered family. Filled by a "
        "dry run only.",
    )
    task_id: Optional[str] = Field(
        default=None,
        description="ID of the background task running the pass, bound to "
        "every log record it emits. Unset for a dry run.",
    )
