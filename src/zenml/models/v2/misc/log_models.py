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
"""Models for log entries, filters, and pagination."""

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
    """Parse a log level name or number.

    Args:
        value: The value to resolve.

    Returns:
        The log level, or the value unchanged for Pydantic to validate.

    Raises:
        ValueError: If a string is not a recognized level name or number.
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


# Query parameters accept both level names and numeric values.
NamedLoggingLevel = Annotated[LoggingLevels, BeforeValidator(parse_log_level)]


class LogEntry(BaseModel):
    """A structured log entry for storage and API responses."""

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
        default=None, description="The source line number"
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
        description=(
            "Entry identifier. Chunks share an ID and have distinct "
            "chunk_index values."
        ),
    )

    model_config = ConfigDict(
        extra="ignore",
    )


class LogsEntriesFilter(BaseModel):
    """Backend filters for log retrieval.

    Unsupported filters raise an error.
    """

    search: Optional[str] = Field(
        default=None,
        description=(
            "Message text to search using backend matching rules. "
            "Tokenization, case sensitivity, and punctuation handling depend "
            "on the backend; literal substring matching is not guaranteed."
        ),
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
        """Normalize time bounds to UTC.

        Args:
            value: Timestamp to normalize. Naive values are interpreted as UTC.

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
    """A page of log entries with backend continuation cursors."""

    items: List[LogEntry] = Field(
        default_factory=list,
        description="Log entries, ordered from oldest to newest.",
    )
    before: Optional[str] = Field(
        default=None,
        description=(
            "Cursor for older entries, or None when continuation in this "
            "direction is unavailable."
        ),
    )
    after: Optional[str] = Field(
        default=None,
        description=(
            "Cursor for newer entries, or None when continuation in this "
            "direction is unavailable."
        ),
    )
