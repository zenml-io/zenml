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
"""Collection of all models concerning actions."""
from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, Field

from zenml.models.v2.base.base import BaseRequest
from zenml.models.v2.base.scoped import WorkspaceScopedResponseBody
from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.models.v2.base.scoped import (
    WorkspaceScopedFilter,
    WorkspaceScopedResponse,
    WorkspaceScopedResponseMetadata,
)
from zenml.models.v2.base.update import update_model


class ActionPlanBase(BaseModel):
    """BaseModel for all ActionPlans."""
    flavor: str = Field(
        title="The flavor of action.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    configuration: Dict[str, Any] = Field(
        title="The event source configuration.",
    )


# ------------------ Request Model ------------------
class ActionPlanRequest(ActionPlanBase, BaseRequest):
    """Request model for components."""


# ------------------ Update Model ------------------


@update_model
class ActionPlanUpdate(ActionPlanRequest):
    """Update model for stack components."""


# ------------------ Response Model ------------------
class ActionPlanResponseBody(WorkspaceScopedResponseBody):
    """Response body for actions."""
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


class ActionPlanResponseMetadata(WorkspaceScopedResponseMetadata):
    """Response metadata for components."""


class ActionPlanResponse(
    WorkspaceScopedResponse[ActionPlanResponseBody, ActionPlanResponseMetadata]
):
    """Response model for actions."""


# ------------------ Filter Model ------------------


class ActionPlanFilter(WorkspaceScopedFilter):
    """Model to enable advanced filtering of all ActionPlanModels."""

