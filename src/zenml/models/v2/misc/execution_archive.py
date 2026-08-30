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
