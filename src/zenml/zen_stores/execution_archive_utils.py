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
"""SQL payload markers shared by schemas and execution archive services."""

from typing import Optional
from uuid import UUID

from zenml.exceptions import ExecutionArchiveRestoreRequiredError

_ARCHIVED_PAYLOAD_PREFIX = "zenml:execution-archive:"


def archived_payload_placeholder(archive_id: UUID) -> str:
    """Return the SQL placeholder for one authoritative archive.

    Args:
        archive_id: Archive generation that owns the payload.

    Returns:
        Placeholder persisted in compacted payload columns.
    """
    return f"{_ARCHIVED_PAYLOAD_PREFIX}{archive_id}"


def archived_payload_id(value: Optional[str]) -> Optional[UUID]:
    """Extract an archive ID from a compacted payload value.

    Args:
        value: Potential archived-payload placeholder.

    Returns:
        The encoded archive ID, or `None` for ordinary payload.
    """
    if not value or not value.startswith(_ARCHIVED_PAYLOAD_PREFIX):
        return None
    try:
        return UUID(value.removeprefix(_ARCHIVED_PAYLOAD_PREFIX))
    except ValueError:
        return None


def require_active_payload(*values: Optional[str]) -> None:
    """Reject response conversion that requires compacted payload.

    Args:
        *values: Payload values about to be decoded or returned.

    Raises:
        ExecutionArchiveRestoreRequiredError: If a value is archived.
    """
    for value in values:
        if archive_id := archived_payload_id(value):
            raise ExecutionArchiveRestoreRequiredError(archive_id)
