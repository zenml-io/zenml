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
"""Collection of all models concerning trigger executions."""
from typing import TYPE_CHECKING, Any, Dict, Optional, Union
from uuid import UUID

from pydantic import Field

from zenml.models import (
    BaseFilter,
    BaseRequest,
    BaseDBResponse,
    BaseResponseBody,
    BaseResponseMetadata,
)

if TYPE_CHECKING:
    from zenml.models import TriggerResponse


# ------------------ Request Model ------------------


class TriggerExecutionRequest(BaseRequest):
    """Model for creating a new Trigger execution."""

    trigger: UUID
    event_metadata: Dict[str, Any] = {}


# ------------------ Update Model ------------------


# ------------------ Response Model ------------------


class TriggerExecutionResponseBody(BaseResponseBody):
    """Response body for trigger executions."""

    trigger: "TriggerResponse"


class TriggerExecutionResponseMetadata(BaseResponseMetadata):
    """Response metadata for trigger executions."""

    event_metadata: Dict[str, Any] = {}


class TriggerExecutionResponse(
    BaseDBResponse[
        TriggerExecutionResponseBody, TriggerExecutionResponseMetadata
    ]
):
    """Response model for trigger executions."""

    def get_hydrated_version(self) -> "TriggerExecutionResponse":
        """Get the hydrated version of this trigger execution.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_trigger_execution(self.id)

    # Body and metadata properties

    @property
    def trigger(self) -> "TriggerResponse":
        """The `trigger` property.

        Returns:
            the value of the property.
        """
        return self.get_body().trigger

    @property
    def event_metadata(self) -> Dict[str, Any]:
        """The `event_metadata` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().event_metadata


# ------------------ Filter Model ------------------


class TriggerExecutionFilter(BaseFilter):
    """Model to enable advanced filtering of all trigger executions."""

    trigger_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="ID of the trigger of the execution.",
    )
