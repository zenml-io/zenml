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

import copy
from typing import Any, Dict, Optional

from pydantic import Field

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.enums import PluginSubType
from zenml.models.v2.base.base import BaseZenModel
from zenml.models.v2.base.page import Page
from zenml.models.v2.base.scoped import (
    WorkspaceScopedFilter,
    WorkspaceScopedRequest,
    WorkspaceScopedResponse,
    WorkspaceScopedResponseBody,
    WorkspaceScopedResponseMetadata,
    WorkspaceScopedResponseResources,
)
from zenml.models.v2.core.trigger import TriggerResponse

# ------------------ Request Model ------------------


class EventSourceRequest(WorkspaceScopedRequest):
    """BaseModel for all event sources."""

    name: str = Field(
        title="The name of the event source.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    flavor: str = Field(
        title="The flavor of event source.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    plugin_subtype: PluginSubType = Field(
        title="The plugin subtype of the event source.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    description: str = Field(
        default="",
        title="The description of the event source.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    configuration: Dict[str, Any] = Field(
        title="The event source configuration.",
    )


# ------------------ Update Model ------------------


class EventSourceUpdate(BaseZenModel):
    """Update model for event sources."""

    name: Optional[str] = Field(
        default=None,
        title="The updated name of the event source.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    description: Optional[str] = Field(
        default=None,
        title="The updated description of the event source.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    configuration: Optional[Dict[str, Any]] = Field(
        default=None,
        title="The updated event source configuration.",
    )
    is_active: Optional[bool] = Field(
        default=None,
        title="The status of the event source.",
    )

    @classmethod
    def from_response(
        cls, response: "EventSourceResponse"
    ) -> "EventSourceUpdate":
        """Create an update model from a response model.

        Args:
            response: The response model to create the update model from.

        Returns:
            The update model.
        """
        return EventSourceUpdate(
            name=response.name,
            description=response.description,
            configuration=copy.deepcopy(response.configuration),
            is_active=response.is_active,
        )


# ------------------ Response Model ------------------


class EventSourceResponseBody(WorkspaceScopedResponseBody):
    """ResponseBody for event sources."""

    flavor: str = Field(
        title="The flavor of event source.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    plugin_subtype: PluginSubType = Field(
        title="The plugin subtype of the event source.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    is_active: bool = Field(
        title="Whether the event source is active.",
    )


class EventSourceResponseMetadata(WorkspaceScopedResponseMetadata):
    """Response metadata for event sources."""

    description: str = Field(
        default="",
        title="The description of the event source.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    configuration: Dict[str, Any] = Field(
        title="The event source configuration.",
    )


class EventSourceResponseResources(WorkspaceScopedResponseResources):
    """Class for all resource models associated with the code repository entity."""

    triggers: Page[TriggerResponse] = Field(
        title="The triggers configured with this event source.",
    )


class EventSourceResponse(
    WorkspaceScopedResponse[
        EventSourceResponseBody,
        EventSourceResponseMetadata,
        EventSourceResponseResources,
    ]
):
    """Response model for event sources."""

    name: str = Field(
        title="The name of the event source.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    def get_hydrated_version(self) -> "EventSourceResponse":
        """Get the hydrated version of this event source.

        Returns:
            An instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_event_source(self.id)

    # Body and metadata properties
    @property
    def flavor(self) -> str:
        """The `flavor` property.

        Returns:
            the value of the property.
        """
        return self.get_body().flavor

    @property
    def is_active(self) -> bool:
        """The `is_active` property.

        Returns:
            the value of the property.
        """
        return self.get_body().is_active

    @property
    def plugin_subtype(self) -> PluginSubType:
        """The `plugin_subtype` property.

        Returns:
            the value of the property.
        """
        return self.get_body().plugin_subtype

    @property
    def description(self) -> str:
        """The `description` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().description

    @property
    def configuration(self) -> Dict[str, Any]:
        """The `configuration` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().configuration

    def set_configuration(self, configuration: Dict[str, Any]) -> None:
        """Set the `configuration` property.

        Args:
            configuration: The value to set.
        """
        self.get_metadata().configuration = configuration


# ------------------ Filter Model ------------------


class EventSourceFilter(WorkspaceScopedFilter):
    """Model to enable advanced filtering of all EventSourceModels."""

    name: Optional[str] = Field(
        default=None,
        description="Name of the event source",
    )
    flavor: Optional[str] = Field(
        default=None,
        description="Flavor of the event source",
    )
    plugin_subtype: Optional[str] = Field(
        title="The plugin sub type of the event source.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
