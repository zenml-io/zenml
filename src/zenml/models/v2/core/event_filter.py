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
from typing import Dict, Any

from pydantic import Field
from zenml.models.v2.base.scoped import WorkspaceScopedResponseBody, \
    WorkspaceScopedResponseMetadata, WorkspaceScopedResponse, \
    WorkspaceScopedFilter

from zenml import BaseRequest
from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.models.v2.base.update import update_model


# ------------------ Request Model ------------------

class EventFilterRequest(BaseRequest):
    """BaseModel for all event sources."""

    event_type: str = Field(
        title="The type of event.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    configuration: Dict[str, Any] = Field(
        title="The event source configuration.",
    )


# ------------------ Update Model ------------------

@update_model
class EventFilterUpdate(EventFilterRequest):
    """Update model for event sources."""


# ------------------ Response Model ------------------

class EventFilterResponseBody(WorkspaceScopedResponseBody):
    """ResponseBody for events."""


class EventFilterResponseMetadata(WorkspaceScopedResponseMetadata):
    """Response metadata for events."""

    description: str = Field(
        default="",
        title="The description of the event",
        max_length=STR_FIELD_MAX_LENGTH,
    )


class EventFilterResponse(
    WorkspaceScopedResponse[EventFilterResponseBody, EventFilterResponseMetadata]
):
    """Response model for models."""

    name: str = Field(
        title="The name of the model",
        max_length=STR_FIELD_MAX_LENGTH,
    )


# ------------------ Filter Model ------------------


class EventFilterFilter(WorkspaceScopedFilter):
    """Model to enable advanced filtering of all EventFilterModels."""
