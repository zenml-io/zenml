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
"""Shared models for execution-history archiving."""

from datetime import datetime
from typing import Annotated, Dict, Optional
from uuid import UUID

from pydantic import (
    ConfigDict,
    Field,
    NonNegativeInt,
    PositiveInt,
    StringConstraints,
)

from zenml.constants import MAX_ZENML_SERVER_EXECUTION_ARCHIVE_ERROR_LENGTH
from zenml.enums import ExecutionArchiveMode, ExecutionArchiveState
from zenml.models.v2.base.base import BaseZenModel

Sha256Digest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


def validate_relative_path(value: str) -> str:
    """Require a relative path that cannot escape its root.

    Args:
        value: Slash-separated path.

    Returns:
        The validated path.

    Raises:
        ValueError: If the path is empty, absolute, or contains traversal.
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
    """Verified object containing one complete execution tree."""

    sha256: Sha256Digest
    stored_bytes: NonNegativeInt
    decoded_bytes: NonNegativeInt

    model_config = ConfigDict(frozen=True)


class ExecutionArchiveResponse(BaseZenModel):
    """Detached view of one execution archive generation."""

    id: UUID
    project_id: UUID
    root_run_id: UUID
    generation: int
    state: ExecutionArchiveState
    requires_restore: bool
    source_fingerprint: Sha256Digest
    source_updated_at: datetime
    storage_target_digest: Sha256Digest
    object: Optional[ExecutionArchiveObject] = None
    source_bytes: Optional[NonNegativeInt] = None
    committed_at: Optional[datetime] = None
    compacted_at: Optional[datetime] = None
    restored_at: Optional[datetime] = None
    purge_pending_at: Optional[datetime] = None
    last_error: Optional[str] = Field(
        default=None,
        max_length=MAX_ZENML_SERVER_EXECUTION_ARCHIVE_ERROR_LENGTH,
    )
    created: datetime

    model_config = ConfigDict(frozen=True)


class ExecutionArchiveExportRequest(BaseZenModel):
    """Request to export one complete execution tree."""

    project_id: UUID
    root_run_id: UUID

    model_config = ConfigDict(frozen=True)


class ExecutionArchiveActionRequest(BaseZenModel):
    """Project scope for an action on one archive generation."""

    project_id: UUID

    model_config = ConfigDict(frozen=True)


class ExecutionArchivePolicy(BaseZenModel):
    """Workspace policy for automatic execution-history tiering."""

    mode: ExecutionArchiveMode = ExecutionArchiveMode.DISABLED
    retention_days: PositiveInt = Field(default=180, le=3650)

    model_config = ConfigDict(frozen=True)


class ExecutionArchivePolicyRequest(BaseZenModel):
    """Complete replacement of a workspace archive policy."""

    mode: ExecutionArchiveMode
    retention_days: PositiveInt = Field(le=3650)

    model_config = ConfigDict(frozen=True)


class ExecutionArchivePassResult(BaseZenModel):
    """Cached outcome of one bounded coordinator pass."""

    started_at: datetime
    completed_at: datetime
    scanned_trees: NonNegativeInt = 0
    eligible_trees: NonNegativeInt = 0
    blocked_trees: NonNegativeInt = 0
    blocker_counts: Dict[str, NonNegativeInt] = Field(default_factory=dict)
    failure_counts: Dict[str, NonNegativeInt] = Field(default_factory=dict)
    exported_trees: NonNegativeInt = 0
    compacted_trees: NonNegativeInt = 0
    resumed_trees: NonNegativeInt = 0
    purged_archives: NonNegativeInt = 0
    source_bytes_processed: NonNegativeInt = 0
    candidate_scan_incomplete: bool = False
    error: Optional[str] = Field(
        default=None,
        max_length=MAX_ZENML_SERVER_EXECUTION_ARCHIVE_ERROR_LENGTH,
    )

    model_config = ConfigDict(frozen=True)


class ExecutionArchiveStatus(BaseZenModel):
    """Workspace execution-history tiering status without storage probes."""

    workspace_id: UUID
    workspace_prefix: Optional[str] = None
    policy: ExecutionArchivePolicy
    storage_configured: bool
    compaction_gate_enabled: bool
    effective_mode: ExecutionArchiveMode
    message: str
    coordinator_running: bool
    cursor_completed_at: Optional[datetime] = None
    cursor_root_run_id: Optional[UUID] = None
    purge_pending_archives: NonNegativeInt = 0
    oldest_purge_pending_at: Optional[datetime] = None
    archives_requiring_restore: NonNegativeInt = 0
    corrupt_archives: NonNegativeInt = 0
    last_pass: Optional[ExecutionArchivePassResult] = None

    model_config = ConfigDict(frozen=True)
