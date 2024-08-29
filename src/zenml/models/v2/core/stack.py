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
"""Models representing stacks."""

import json
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional, Union
from uuid import UUID

from pydantic import Field, model_validator
from sqlmodel import and_

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.enums import StackComponentType
from zenml.models.v2.base.base import BaseRequest, BaseUpdate
from zenml.models.v2.base.scoped import (
    WorkspaceScopedFilter,
    WorkspaceScopedResponse,
    WorkspaceScopedResponseBody,
    WorkspaceScopedResponseMetadata,
    WorkspaceScopedResponseResources,
)
from zenml.models.v2.misc.info_models import (
    ComponentInfo,
    ServiceConnectorInfo,
)

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement

    from zenml.models.v2.core.component import ComponentResponse


# ------------------ Request Model ------------------


class StackRequest(BaseRequest):
    """Request model for a stack."""

    user: Optional[UUID] = None
    workspace: Optional[UUID] = None

    name: str = Field(
        title="The name of the stack.", max_length=STR_FIELD_MAX_LENGTH
    )
    description: str = Field(
        default="",
        title="The description of the stack",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    stack_spec_path: Optional[str] = Field(
        default=None,
        title="The path to the stack spec used for mlstacks deployments.",
    )
    components: Dict[StackComponentType, List[Union[UUID, ComponentInfo]]] = (
        Field(
            title="The mapping for the components of the full stack registration.",
            description="The mapping from component types to either UUIDs of "
            "existing components or request information for brand new "
            "components.",
        )
    )
    labels: Optional[Dict[str, Any]] = Field(
        default=None,
        title="The stack labels.",
    )
    service_connectors: List[Union[UUID, ServiceConnectorInfo]] = Field(
        default=[],
        title="The service connectors dictionary for the full stack "
        "registration.",
        description="The UUID of an already existing service connector or "
        "request information to create a service connector from "
        "scratch.",
    )

    @property
    def is_valid(self) -> bool:
        """Check if the stack is valid.

        Returns:
            True if the stack is valid, False otherwise.
        """
        if not self.components:
            return False
        return (
            StackComponentType.ARTIFACT_STORE in self.components
            and StackComponentType.ORCHESTRATOR in self.components
        )

    @model_validator(mode="after")
    def _validate_indexes_in_components(self) -> "StackRequest":
        for components in self.components.values():
            for component in components:
                if isinstance(component, ComponentInfo):
                    if component.service_connector_index is not None:
                        if (
                            component.service_connector_index < 0
                            or component.service_connector_index
                            >= len(self.service_connectors)
                        ):
                            raise ValueError(
                                f"Service connector index "
                                f"{component.service_connector_index} "
                                "is out of range. Please provide a valid index "
                                "referring to the position in the list of service "
                                "connectors."
                            )
        return self


# ------------------ Update Model ------------------


class StackUpdate(BaseUpdate):
    """Update model for stacks."""

    name: Optional[str] = Field(
        title="The name of the stack.",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )
    description: Optional[str] = Field(
        title="The description of the stack",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )
    stack_spec_path: Optional[str] = Field(
        title="The path to the stack spec used for mlstacks deployments.",
        default=None,
    )
    components: Optional[Dict[StackComponentType, List[UUID]]] = Field(
        title="A mapping of stack component types to the actual"
        "instances of components of this type.",
        default=None,
    )
    labels: Optional[Dict[str, Any]] = Field(
        default=None,
        title="The stack labels.",
    )


# ------------------ Response Model ------------------


class StackResponseBody(WorkspaceScopedResponseBody):
    """Response body for stacks."""


class StackResponseMetadata(WorkspaceScopedResponseMetadata):
    """Response metadata for stacks."""

    components: Dict[StackComponentType, List["ComponentResponse"]] = Field(
        title="A mapping of stack component types to the actual"
        "instances of components of this type."
    )
    description: Optional[str] = Field(
        default="",
        title="The description of the stack",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    stack_spec_path: Optional[str] = Field(
        default=None,
        title="The path to the stack spec used for mlstacks deployments.",
    )
    labels: Optional[Dict[str, Any]] = Field(
        default=None,
        title="The stack labels.",
    )


class StackResponseResources(WorkspaceScopedResponseResources):
    """Class for all resource models associated with the stack entity."""


class StackResponse(
    WorkspaceScopedResponse[
        StackResponseBody, StackResponseMetadata, StackResponseResources
    ]
):
    """Response model for stacks."""

    name: str = Field(
        title="The name of the stack.", max_length=STR_FIELD_MAX_LENGTH
    )

    def get_hydrated_version(self) -> "StackResponse":
        """Get the hydrated version of this stack.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_stack(self.id)

    # Helper methods
    @property
    def is_valid(self) -> bool:
        """Check if the stack is valid.

        Returns:
            True if the stack is valid, False otherwise.
        """
        return (
            StackComponentType.ARTIFACT_STORE in self.components
            and StackComponentType.ORCHESTRATOR in self.components
        )

    def to_yaml(self) -> Dict[str, Any]:
        """Create yaml representation of the Stack Model.

        Returns:
            The yaml representation of the Stack Model.
        """
        component_data = {}
        for component_type, components_list in self.components.items():
            component = components_list[0]
            component_dict = dict(
                name=component.name,
                type=str(component.type),
                flavor=component.flavor,
            )
            configuration = json.loads(
                component.get_metadata().model_dump_json(
                    include={"configuration"}
                )
            )
            component_dict.update(configuration)

            component_data[component_type.value] = component_dict

        # write zenml version and stack dict to YAML
        yaml_data = {
            "stack_name": self.name,
            "components": component_data,
        }

        return yaml_data

    # Analytics
    def get_analytics_metadata(self) -> Dict[str, Any]:
        """Add the stack components to the stack analytics metadata.

        Returns:
            Dict of analytics metadata.
        """
        metadata = super().get_analytics_metadata()
        metadata.update({ct: c[0].flavor for ct, c in self.components.items()})

        if self.labels is not None:
            metadata.update(
                {
                    label[6:]: value
                    for label, value in self.labels.items()
                    if label.startswith("zenml:")
                }
            )
        return metadata

    @property
    def description(self) -> Optional[str]:
        """The `description` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().description

    @property
    def stack_spec_path(self) -> Optional[str]:
        """The `stack_spec_path` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().stack_spec_path

    @property
    def components(
        self,
    ) -> Dict[StackComponentType, List["ComponentResponse"]]:
        """The `components` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().components

    @property
    def labels(self) -> Optional[Dict[str, Any]]:
        """The `labels` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().labels


# ------------------ Filter Model ------------------


class StackFilter(WorkspaceScopedFilter):
    """Model to enable advanced filtering of all StackModels.

    The Stack Model needs additional scoping. As such the `_scope_user` field
    can be set to the user that is doing the filtering. The
    `generate_filter()` method of the baseclass is overwritten to include the
    scoping.
    """

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *WorkspaceScopedFilter.FILTER_EXCLUDE_FIELDS,
        "component_id",
        "user_name",
        "component_name",
    ]

    name: Optional[str] = Field(
        default=None,
        description="Name of the stack",
    )
    description: Optional[str] = Field(
        default=None, description="Description of the stack"
    )
    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Workspace of the stack",
        union_mode="left_to_right",
    )
    user_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="User of the stack",
        union_mode="left_to_right",
    )
    component_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Component in the stack",
        union_mode="left_to_right",
    )
    user_name: Optional[str] = Field(
        default=None,
        description="Name of the user that created the stack.",
    )
    component_name: Optional[str] = Field(
        default=None, description="Name of component in the stack."
    )

    def get_custom_filters(self) -> List["ColumnElement[bool]"]:
        """Get custom filters.

        Returns:
            A list of custom filters.
        """
        custom_filters = super().get_custom_filters()

        from zenml.zen_stores.schemas import (
            StackComponentSchema,
            StackCompositionSchema,
            StackSchema,
            UserSchema,
        )

        if self.component_id:
            component_id_filter = and_(
                StackCompositionSchema.stack_id == StackSchema.id,
                StackCompositionSchema.component_id == self.component_id,
            )
            custom_filters.append(component_id_filter)

        if self.user_name is not None:
            user_name_filter = and_(
                StackSchema.user_id == UserSchema.id,
                self.generate_custom_filter_conditions_for_column(
                    value=self.user_name, table=UserSchema, column="name"
                ),
            )
            custom_filters.append(user_name_filter)

        if self.component_name is not None:
            component_name_filter = and_(
                StackCompositionSchema.stack_id == StackSchema.id,
                StackCompositionSchema.component_id == StackComponentSchema.id,
                self.generate_custom_filter_conditions_for_column(
                    value=self.component_name,
                    table=StackComponentSchema,
                    column="name",
                ),
            )
            custom_filters.append(component_name_filter)

        return custom_filters
