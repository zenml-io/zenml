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
"""Collection of all models concerning triggers."""
from datetime import datetime
from typing import Any, Dict, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.models.v2.base.scoped import (
    WorkspaceScopedFilter,
    WorkspaceScopedRequest,
    WorkspaceScopedResponse,
    WorkspaceScopedResponseBody,
    WorkspaceScopedResponseMetadata,
)
from zenml.models.v2.base.update import update_model

# ------------------ Base Model ------------------


class TriggerBase(BaseModel):
    """Base model for triggers."""

    name: str = Field(
        title="The name of the Trigger.", max_length=STR_FIELD_MAX_LENGTH
    )
    description: str = Field(
        default="",
        title="The description of the trigger",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    event_source_id: UUID
    event_filter: Dict[str, Any]
    action_plan: Dict[str, Any]
    action_plan_flavor: str


# ------------------ Request Model ------------------
class TriggerRequest(TriggerBase, WorkspaceScopedRequest):
    """Model for creating a new Trigger."""

    # executions: somehow we need to link to executed Actions here


# ------------------ Update Model ------------------


@update_model
class TriggerUpdate(TriggerRequest):
    """Update model for stacks."""


# ------------------ Response Model ------------------


class TriggerResponseBody(WorkspaceScopedResponseBody):
    """ResponseBody for triggers."""

    created: datetime = Field(
        title="The timestamp when this trigger was created."
    )
    updated: datetime = Field(
        title="The timestamp when this trigger was last updated.",
    )
    action_plan_flavor: str
    event_flavor: str


class TriggerResponseMetadata(WorkspaceScopedResponseMetadata):
    """Response metadata for triggers."""

    event_filter: Dict[str, Any] = Field(
        title="The event that activates this trigger.",
    )
    action_plan: Dict[str, Any] = Field(
        title="The actions that is executed by this trigger.",
    )


class TriggerResponse(
    WorkspaceScopedResponse[TriggerResponseBody, TriggerResponseMetadata]
):
    """Response model for models."""

    name: str = Field(
        title="The name of the model",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    description: str = Field(
        default="",
        title="The description of the trigger",
        max_length=STR_FIELD_MAX_LENGTH,
    )


# ------------------ Filter Model ------------------


class TriggerFilter(WorkspaceScopedFilter):
    """Model to enable advanced filtering of all TriggerModels."""

    name: Optional[str] = Field(
        default=None,
        description="Name of the trigger",
    )
    event_source_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="By the event source this trigger is attached to.",
    )
