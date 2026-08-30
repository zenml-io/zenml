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
from typing import Annotated, Optional
from uuid import UUID

from pydantic import ConfigDict, Field, NonNegativeInt, StringConstraints

from zenml.constants import MAX_ZENML_SERVER_EXECUTION_ARCHIVE_ERROR_LENGTH
from zenml.enums import ExecutionArchiveState
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
