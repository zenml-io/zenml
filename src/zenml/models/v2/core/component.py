#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Models representing components."""

from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Type,
    Union,
)
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.enums import LogicalOperators, StackComponentType
from zenml.models.v2.base.base import BaseUpdate
from zenml.models.v2.base.scoped import (
    WorkspaceScopedFilter,
    WorkspaceScopedRequest,
    WorkspaceScopedResponse,
    WorkspaceScopedResponseBody,
    WorkspaceScopedResponseMetadata,
    WorkspaceScopedResponseResources,
)
from zenml.utils import secret_utils

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement
    from sqlmodel import SQLModel

    from zenml.models import FlavorResponse, ServiceConnectorResponse

# ------------------ Base Model ------------------


class ComponentBase(BaseModel):
    """Base model for components."""

    name: str = Field(
        title="The name of the stack component.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    type: StackComponentType = Field(
        title="The type of the stack component.",
    )

    flavor: str = Field(
        title="The flavor of the stack component.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    configuration: Dict[str, Any] = Field(
        title="The stack component configuration.",
    )

    connector_resource_id: Optional[str] = Field(
        default=None,
        description="The ID of a specific resource instance to "
        "gain access to through the connector",
    )

    labels: Optional[Dict[str, Any]] = Field(
        default=None,
        title="The stack component labels.",
    )


# ------------------ Request Model ------------------


class ComponentRequest(ComponentBase, WorkspaceScopedRequest):
    """Request model for components."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = ["type", "flavor"]

    connector: Optional[UUID] = Field(
        default=None,
        title="The service connector linked to this stack component.",
    )

    @field_validator("name")
    @classmethod
    def name_cant_be_a_secret_reference(cls, name: str) -> str:
        """Validator to ensure that the given name is not a secret reference.

        Args:
            name: The name to validate.

        Returns:
            The name if it is not a secret reference.

        Raises:
            ValueError: If the name is a secret reference.
        """
        if secret_utils.is_secret_reference(name):
            raise ValueError(
                "Passing the `name` attribute of a stack component as a "
                "secret reference is not allowed."
            )
        return name


class InternalComponentRequest(ComponentRequest):
    """Internal component request model."""

    user: Optional[UUID] = Field(  # type: ignore[assignment]
        title="The id of the user that created this resource.",
        default=None,
    )


# ------------------ Update Model ------------------


class ComponentUpdate(BaseUpdate):
    """Update model for stack components."""

    name: Optional[str] = Field(
        title="The name of the stack component.",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )
    configuration: Optional[Dict[str, Any]] = Field(
        title="The stack component configuration.",
        default=None,
    )
    connector_resource_id: Optional[str] = Field(
        description="The ID of a specific resource instance to "
        "gain access to through the connector",
        default=None,
    )
    labels: Optional[Dict[str, Any]] = Field(
        title="The stack component labels.",
        default=None,
    )
    connector: Optional[UUID] = Field(
        title="The service connector linked to this stack component.",
        default=None,
    )


# ------------------ Response Model ------------------


class ComponentResponseBody(WorkspaceScopedResponseBody):
    """Response body for components."""

    type: StackComponentType = Field(
        title="The type of the stack component.",
    )
    flavor_name: str = Field(
        title="The flavor of the stack component.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    integration: Optional[str] = Field(
        default=None,
        title="The name of the integration that the component's flavor "
        "belongs to.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    logo_url: Optional[str] = Field(
        default=None,
        title="Optionally, a url pointing to a png,"
        "svg or jpg can be attached.",
    )


class ComponentResponseMetadata(WorkspaceScopedResponseMetadata):
    """Response metadata for components."""

    configuration: Dict[str, Any] = Field(
        title="The stack component configuration.",
    )
    labels: Optional[Dict[str, Any]] = Field(
        default=None,
        title="The stack component labels.",
    )
    connector_resource_id: Optional[str] = Field(
        default=None,
        description="The ID of a specific resource instance to "
        "gain access to through the connector",
    )
    connector: Optional["ServiceConnectorResponse"] = Field(
        default=None,
        title="The service connector linked to this stack component.",
    )


class ComponentResponseResources(WorkspaceScopedResponseResources):
    """Class for all resource models associated with the component entity."""

    flavor: "FlavorResponse" = Field(
        title="The flavor of this stack component.",
    )


class ComponentResponse(
    WorkspaceScopedResponse[
        ComponentResponseBody,
        ComponentResponseMetadata,
        ComponentResponseResources,
    ]
):
    """Response model for components."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = ["type"]

    name: str = Field(
        title="The name of the stack component.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    def get_analytics_metadata(self) -> Dict[str, Any]:
        """Add the component labels to analytics metadata.

        Returns:
            Dict of analytics metadata.
        """
        metadata = super().get_analytics_metadata()

        if self.labels is not None:
            metadata.update(
                {
                    label[6:]: value
                    for label, value in self.labels.items()
                    if label.startswith("zenml:")
                }
            )
        metadata["flavor"] = self.flavor_name

        return metadata

    def get_hydrated_version(self) -> "ComponentResponse":
        """Get the hydrated version of this component.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_stack_component(self.id)

    # Body and metadata properties
    @property
    def type(self) -> StackComponentType:
        """The `type` property.

        Returns:
            the value of the property.
        """
        return self.get_body().type

    @property
    def flavor_name(self) -> str:
        """The `flavor_name` property.

        Returns:
            the value of the property.
        """
        return self.get_body().flavor_name

    @property
    def integration(self) -> Optional[str]:
        """The `integration` property.

        Returns:
            the value of the property.
        """
        return self.get_body().integration

    @property
    def logo_url(self) -> Optional[str]:
        """The `logo_url` property.

        Returns:
            the value of the property.
        """
        return self.get_body().logo_url

    @property
    def configuration(self) -> Dict[str, Any]:
        """The `configuration` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().configuration

    @property
    def labels(self) -> Optional[Dict[str, Any]]:
        """The `labels` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().labels

    @property
    def connector_resource_id(self) -> Optional[str]:
        """The `connector_resource_id` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().connector_resource_id

    @property
    def connector(self) -> Optional["ServiceConnectorResponse"]:
        """The `connector` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().connector

    @property
    def flavor(self) -> "FlavorResponse":
        """The `flavor` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().flavor


# ------------------ Filter Model ------------------


class ComponentFilter(WorkspaceScopedFilter):
    """Model to enable advanced filtering of all ComponentModels.

    The Component Model needs additional scoping. As such the `_scope_user`
    field can be set to the user that is doing the filtering. The
    `generate_filter()` method of the baseclass is overwritten to include the
    scoping.
    """

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *WorkspaceScopedFilter.FILTER_EXCLUDE_FIELDS,
        "scope_type",
        "stack_id",
    ]
    CLI_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *WorkspaceScopedFilter.CLI_EXCLUDE_FIELDS,
        "scope_type",
    ]
    scope_type: Optional[str] = Field(
        default=None,
        description="The type to scope this query to.",
    )
    name: Optional[str] = Field(
        default=None,
        description="Name of the stack component",
    )
    flavor: Optional[str] = Field(
        default=None,
        description="Flavor of the stack component",
    )
    type: Optional[str] = Field(
        default=None,
        description="Type of the stack component",
    )
    connector_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Connector linked to the stack component",
        union_mode="left_to_right",
    )
    stack_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Stack of the stack component",
        union_mode="left_to_right",
    )

    def set_scope_type(self, component_type: str) -> None:
        """Set the type of component on which to perform the filtering to scope the response.

        Args:
            component_type: The type of component to scope the query to.
        """
        self.scope_type = component_type

    def generate_filter(
        self, table: Type["SQLModel"]
    ) -> Union["ColumnElement[bool]"]:
        """Generate the filter for the query.

        Stack components can be scoped by type to narrow the search.

        Args:
            table: The Table that is being queried from.

        Returns:
            The filter expression for the query.
        """
        from sqlmodel import and_, or_

        from zenml.zen_stores.schemas import (
            StackComponentSchema,
            StackCompositionSchema,
        )

        base_filter = super().generate_filter(table)
        if self.scope_type:
            type_filter = getattr(table, "type") == self.scope_type
            return and_(base_filter, type_filter)

        if self.stack_id:
            operator = (
                or_ if self.logical_operator == LogicalOperators.OR else and_
            )

            stack_filter = and_(
                StackCompositionSchema.stack_id == self.stack_id,
                StackCompositionSchema.component_id == StackComponentSchema.id,
            )
            base_filter = operator(base_filter, stack_filter)

        return base_filter
