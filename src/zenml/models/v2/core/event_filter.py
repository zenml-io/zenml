#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Collection of all models concerning event configurations."""
from datetime import datetime
from typing import Any, Dict

from pydantic import Field

from zenml import BaseRequest
from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.models.v2.base.scoped import (
    WorkspaceScopedFilter,
    WorkspaceScopedResponse,
    WorkspaceScopedResponseBody,
    WorkspaceScopedResponseMetadata,
)
from zenml.models.v2.base.update import update_model

# ------------------ Request Model ------------------

class EventFilterRequest(BaseRequest):
    """BaseModel for all event sources."""

    flavor: str = Field(
        title="The flavor of event.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    configuration: Dict[str, Any] = Field(
        title="The event filter configuration.",
    )


# ------------------ Update Model ------------------

@update_model
class EventFilterUpdate(EventFilterRequest):
    """Update model for event sources."""


# ------------------ Response Model ------------------

class EventFilterResponseBody(WorkspaceScopedResponseBody):
    """ResponseBody for events."""

    flavor: str = Field(
        title="The flavor of event.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    created: datetime = Field(
        title="The timestamp when this event filter was created."
    )
    updated: datetime = Field(
        title="The timestamp when this event filter was last updated.",
    )
    description: str = Field(
        default="",
        title="The description of the event",
        max_length=STR_FIELD_MAX_LENGTH,
    )


class EventFilterResponseMetadata(WorkspaceScopedResponseMetadata):
    """Response metadata for events."""


class EventFilterResponse(
    WorkspaceScopedResponse[EventFilterResponseBody, EventFilterResponseMetadata]
):
    """Response model for event filters."""


# ------------------ Filter Model ------------------


class EventFilterFilter(WorkspaceScopedFilter):
    """Model to enable advanced filtering of all EventFilterModels."""
