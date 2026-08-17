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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Models used to retrieve and paginate the entries of a log stream."""

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)
from typing_extensions import Annotated

from zenml.enums import LoggingLevels
from zenml.utils.time_utils import to_utc_timezone


def parse_log_level(value: Any) -> Any:
    """Resolve a log level given as a name or as a numeric value.

    Args:
        value: The value to resolve.

    Returns:
        The log level, or the value unchanged for Pydantic to validate.

    Raises:
        ValueError: If the value is a string that names no log level.
    """
    if isinstance(value, str):
        candidate = value.strip()
        if candidate.upper() in LoggingLevels.__members__:
            return LoggingLevels[candidate.upper()]
        if candidate.isdigit():
            return int(candidate)

        raise ValueError(
            f"'{value}' is not a log level. Use one of "
            f"{', '.join(LoggingLevels.__members__)} or the equivalent number."
        )

    return value


# A log level that may be given by name or by number. Query parameters always
# arrive as strings, so `level=ERROR`, `level=error` and `level=40` all have to
# resolve to the same level.
NamedLoggingLevel = Annotated[LoggingLevels, BeforeValidator(parse_log_level)]


class LogEntry(BaseModel):
    """A single structured log entry.

    This is used in two distinct ways:
        1. If we are using the artifact log store, we save the
        entries as JSON-serialized LogEntry's in the artifact store.
        2. When queried, the server returns logs as a list of LogEntry's.
    """

    message: str = Field(description="The log message content")
    name: Optional[str] = Field(
        default=None,
        description="The name of the logger",
    )
    level: Optional[LoggingLevels] = Field(
        default=None,
        description="The log level",
    )
    timestamp: Optional[datetime] = Field(
        default=None,
        description="When the log was created",
    )
    module: Optional[str] = Field(
        default=None, description="The module that generated this log entry"
    )
    filename: Optional[str] = Field(
        default=None,
        description="The name of the file that generated this log entry",
    )
    lineno: Optional[int] = Field(
        default=None, description="The fileno that generated this log entry"
    )
    chunk_index: int = Field(
        default=0,
        description="The index of the chunk in the log entry",
    )
    total_chunks: int = Field(
        default=1,
        description="The total number of chunks in the log entry",
    )
    id: UUID = Field(
        default_factory=uuid4,
        description="The unique identifier of the log entry",
    )

    model_config = ConfigDict(
        # ignore extra attributes during model initialization
        extra="ignore",
    )


class LogsEntriesFilter(BaseModel):
    """Filters applied while retrieving the entries of a log stream."""

    search: Optional[str] = Field(
        default=None,
        description="Only return entries whose message contains this string.",
    )
    level: Optional[NamedLoggingLevel] = Field(
        default=None,
        description="Only return entries at or above this log level.",
    )
    since: Optional[datetime] = Field(
        default=None,
        description="Only return entries at or after this timestamp.",
    )
    until: Optional[datetime] = Field(
        default=None,
        description="Only return entries at or before this timestamp.",
    )

    @field_validator("since", "until")
    @classmethod
    def normalize_bound(cls, value: Optional[datetime]) -> Optional[datetime]:
        """Make the time bounds timezone-aware.

        Timestamps arriving from query parameters may be naive, while log
        entries are timezone-aware, so the bounds are normalized once here
        instead of at every comparison.

        Args:
            value: The bound to normalize.

        Returns:
            The bound in the UTC timezone.
        """
        return to_utc_timezone(value) if value is not None else None

    @model_validator(mode="after")
    def validate_time_range(self) -> "LogsEntriesFilter":
        """Reject an inverted time range.

        Returns:
            The validated filter.

        Raises:
            ValueError: If `since` is greater than `until`.
        """
        if self.since and self.until and self.since > self.until:
            raise ValueError("`since` must be earlier than `until`.")

        return self


class LogsEntriesResponse(BaseModel):
    """A single page of log entries, with cursors to fetch adjacent pages.

    A cursor is `None` when there is nothing more to fetch in that direction.
    Log stores that cannot paginate at all (the artifact log store) always
    return `None` for both, which tells the caller that `items` is everything
    it is going to get.
    """

    items: List[LogEntry] = Field(
        default_factory=list,
        description="Log entries, ordered from oldest to newest.",
    )
    before: Optional[str] = Field(
        default=None,
        description=(
            "Opaque token to fetch the entries immediately older than the "
            "oldest entry in `items`."
        ),
    )
    after: Optional[str] = Field(
        default=None,
        description=(
            "Opaque token to fetch the entries immediately newer than the "
            "newest entry in `items`."
        ),
    )
