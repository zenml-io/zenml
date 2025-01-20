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

from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)
from uuid import UUID

from pydantic import Field, model_validator

from zenml.config.schedule import Schedule
from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.models.v2.base.base import BaseUpdate
from zenml.models.v2.base.page import Page
from zenml.models.v2.base.scoped import (
    WorkspaceScopedFilter,
    WorkspaceScopedRequest,
    WorkspaceScopedResponse,
    WorkspaceScopedResponseBody,
    WorkspaceScopedResponseMetadata,
    WorkspaceScopedResponseResources,
)
from zenml.models.v2.core.trigger_execution import TriggerExecutionResponse

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement

    from zenml.models.v2.core.action import (
        ActionResponse,
    )
    from zenml.models.v2.core.event_source import EventSourceResponse
    from zenml.zen_stores.schemas import BaseSchema

    AnySchema = TypeVar("AnySchema", bound=BaseSchema)


# ------------------ Request Model ------------------


class TriggerRequest(WorkspaceScopedRequest):
    """Model for creating a new trigger."""

    name: str = Field(
        title="The name of the trigger.", max_length=STR_FIELD_MAX_LENGTH
    )
    description: str = Field(
        default="",
        title="The description of the trigger",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    action_id: UUID = Field(
        title="The action that is executed by this trigger.",
    )
    schedule: Optional[Schedule] = Field(
        default=None,
        title="The schedule for the trigger. Either a schedule or an event "
        "source is required.",
    )
    event_source_id: Optional[UUID] = Field(
        default=None,
        title="The event source that activates this trigger. Either a schedule "
        "or an event source is required.",
    )
    event_filter: Optional[Dict[str, Any]] = Field(
        default=None,
        title="Filter applied to events that activate this trigger. Only "
        "set if the trigger is activated by an event source.",
    )

    @model_validator(mode="after")
    def _validate_schedule_or_event_source(self) -> "TriggerRequest":
        """Validate that either a schedule or an event source is provided.

        Returns:
            The validated request.

        Raises:
            ValueError: If neither a schedule nor an event source is provided,
                or if both are provided.
        """
        if not self.schedule and not self.event_source_id:
            raise ValueError(
                "Either a schedule or an event source is required."
            )

        if self.schedule and self.event_source_id:
            raise ValueError("Only a schedule or an event source is allowed.")

        return self


# ------------------ Update Model ------------------


class TriggerUpdate(BaseUpdate):
    """Update model for triggers."""

    name: Optional[str] = Field(
        default=None,
        title="The new name for the trigger.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    description: Optional[str] = Field(
        default=None,
        title="The new description for the trigger.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    event_filter: Optional[Dict[str, Any]] = Field(
        default=None,
        title="New filter applied to events that activate this trigger. Only "
        "valid if the trigger is already configured to be activated by an "
        "event source.",
    )
    schedule: Optional[Schedule] = Field(
        default=None,
        title="The updated schedule for the trigger. Only valid if the trigger "
        "is already configured to be activated by a schedule.",
    )
    is_active: Optional[bool] = Field(
        default=None,
        title="The new status of the trigger.",
    )


# ------------------ Response Model ------------------


class TriggerResponseBody(WorkspaceScopedResponseBody):
    """Response body for triggers."""

    action_flavor: str = Field(
        title="The flavor of the action that is executed by this trigger.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    action_subtype: str = Field(
        title="The subtype of the action that is executed by this trigger.",
    )
    event_source_flavor: Optional[str] = Field(
        default=None,
        title="The flavor of the event source that activates this trigger. Not "
        "set if the trigger is activated by a schedule.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    event_source_subtype: Optional[str] = Field(
        default=None,
        title="The subtype of the event source that activates this trigger. "
        "Not set if the trigger is activated by a schedule.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    is_active: bool = Field(
        title="Whether the trigger is active.",
    )


class TriggerResponseMetadata(WorkspaceScopedResponseMetadata):
    """Response metadata for triggers."""

    description: str = Field(
        default="",
        title="The description of the trigger.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    event_filter: Optional[Dict[str, Any]] = Field(
        default=None,
        title="The event that activates this trigger. Not set if the trigger "
        "is activated by a schedule.",
    )
    schedule: Optional[Schedule] = Field(
        default=None,
        title="The schedule that activates this trigger. Not set if the "
        "trigger is activated by an event source.",
    )


class TriggerResponseResources(WorkspaceScopedResponseResources):
    """Class for all resource models associated with the trigger entity."""

    action: "ActionResponse" = Field(
        title="The action that is executed by this trigger.",
    )
    event_source: Optional["EventSourceResponse"] = Field(
        default=None,
        title="The event source that activates this trigger. Not set if the "
        "trigger is activated by a schedule.",
    )
    executions: Page[TriggerExecutionResponse] = Field(
        title="The executions of this trigger.",
    )


class TriggerResponse(
    WorkspaceScopedResponse[
        TriggerResponseBody, TriggerResponseMetadata, TriggerResponseResources
    ]
):
    """Response model for models."""

    name: str = Field(
        title="The name of the trigger",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    def get_hydrated_version(self) -> "TriggerResponse":
        """Get the hydrated version of this trigger.

        Returns:
            An instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_trigger(self.id)

    @property
    def action_flavor(self) -> str:
        """The `action_flavor` property.

        Returns:
            the value of the property.
        """
        return self.get_body().action_flavor

    @property
    def action_subtype(self) -> str:
        """The `action_subtype` property.

        Returns:
            the value of the property.
        """
        return self.get_body().action_subtype

    @property
    def event_source_flavor(self) -> Optional[str]:
        """The `event_source_flavor` property.

        Returns:
            the value of the property.
        """
        return self.get_body().event_source_flavor

    @property
    def event_source_subtype(self) -> Optional[str]:
        """The `event_source_subtype` property.

        Returns:
            the value of the property.
        """
        return self.get_body().event_source_subtype

    @property
    def is_active(self) -> bool:
        """The `is_active` property.

        Returns:
            the value of the property.
        """
        return self.get_body().is_active

    @property
    def event_filter(self) -> Optional[Dict[str, Any]]:
        """The `event_filter` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().event_filter

    @property
    def description(self) -> str:
        """The `description` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().description

    @property
    def action(self) -> "ActionResponse":
        """The `action` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().action

    @property
    def event_source(self) -> Optional["EventSourceResponse"]:
        """The `event_source` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().event_source

    @property
    def executions(self) -> Page[TriggerExecutionResponse]:
        """The `event_source` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().executions


# ------------------ Filter Model ------------------


class TriggerFilter(WorkspaceScopedFilter):
    """Model to enable advanced filtering of all triggers."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *WorkspaceScopedFilter.FILTER_EXCLUDE_FIELDS,
        "action_flavor",
        "action_subtype",
        "event_source_flavor",
        "event_source_subtype",
    ]

    name: Optional[str] = Field(
        default=None,
        description="Name of the trigger.",
    )
    event_source_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="The event source this trigger is attached to.",
        union_mode="left_to_right",
    )
    action_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="The action this trigger is attached to.",
        union_mode="left_to_right",
    )
    is_active: Optional[bool] = Field(
        default=None,
        description="Whether the trigger is active.",
    )
    action_flavor: Optional[str] = Field(
        default=None,
        title="The flavor of the action that is executed by this trigger.",
    )
    action_subtype: Optional[str] = Field(
        default=None,
        title="The subtype of the action that is executed by this trigger.",
    )
    event_source_flavor: Optional[str] = Field(
        default=None,
        title="The flavor of the event source that activates this trigger.",
    )
    event_source_subtype: Optional[str] = Field(
        default=None,
        title="The subtype of the event source that activates this trigger.",
    )

    def get_custom_filters(
        self, table: Type["AnySchema"]
    ) -> List["ColumnElement[bool]"]:
        """Get custom filters.

        Args:
            table: The query table.

        Returns:
            A list of custom filters.
        """
        from sqlmodel import and_

        from zenml.zen_stores.schemas import (
            ActionSchema,
            EventSourceSchema,
            TriggerSchema,
        )

        custom_filters = super().get_custom_filters(table)

        if self.event_source_flavor:
            event_source_flavor_filter = and_(
                EventSourceSchema.id == TriggerSchema.event_source_id,
                EventSourceSchema.flavor == self.event_source_flavor,
            )
            custom_filters.append(event_source_flavor_filter)

        if self.event_source_subtype:
            event_source_subtype_filter = and_(
                EventSourceSchema.id == TriggerSchema.event_source_id,
                EventSourceSchema.plugin_subtype == self.event_source_subtype,
            )
            custom_filters.append(event_source_subtype_filter)

        if self.action_flavor:
            action_flavor_filter = and_(
                ActionSchema.id == TriggerSchema.action_id,
                ActionSchema.flavor == self.action_flavor,
            )
            custom_filters.append(action_flavor_filter)

        if self.action_subtype:
            action_subtype_filter = and_(
                ActionSchema.id == TriggerSchema.action_id,
                ActionSchema.plugin_subtype == self.action_subtype,
            )
            custom_filters.append(action_subtype_filter)

        return custom_filters
