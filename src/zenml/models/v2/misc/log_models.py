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
"""Models used for logs retrieval and pagination."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from zenml.enums import LoggingLevels


class LogEntry(BaseModel):
    """A structured log entry with parsed information."""

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


class LogsEntriesResponse(BaseModel):
    """Response model for a paginated logs entries request."""

    items: List[LogEntry] = Field(
        default_factory=list,
        description="Log entries ordered from newest to oldest.",
    )
    before: Optional[str] = Field(
        default=None,
        description=(
            "Opaque token to fetch entries older than the oldest entry in `items`."
        ),
    )
    after: Optional[str] = Field(
        default=None,
        description=(
            "Opaque token to fetch entries newer than the newest entry in `items`."
        ),
    )


class LogsEntriesFilter(BaseModel):
    """Filters for logs entries retrieval."""

    search: Optional[str] = None
    level: Optional[LoggingLevels] = None
    since: Optional[datetime] = None
    until: Optional[datetime] = None

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def validate_filter(self) -> "LogsEntriesFilter":
        """Validate and normalize filter fields."""
        if (
            self.search is not None and self.search.strip() == ""
        ):
            self.search = None
        if self.since is not None and self.until is not None:
            if self.since > self.until:
                raise ValueError("`since` must be <= `until`.")
        return self

    @field_validator("level", mode="before")
    @classmethod
    def parse_level(cls, value: Optional[object]) -> Optional[LoggingLevels]:
        """Accept both numeric and string log level."""
        if value is None:
            return None
        if isinstance(value, LoggingLevels):
            return value
        if isinstance(value, int):
            return LoggingLevels(value)
        if isinstance(value, str):
            name = value.strip().upper()
            if name in LoggingLevels.__members__:
                return LoggingLevels[name]
            return LoggingLevels(int(value))
        raise ValueError("Invalid log level.")
