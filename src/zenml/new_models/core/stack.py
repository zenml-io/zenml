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
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.enums import StackComponentType
from zenml.new_models.base import (
    SharableResponseMetadata,
    ShareableRequest,
    ShareableResponse,
    hydrated_property,
    update_model,
)

if TYPE_CHECKING:
    from zenml.new_models.core.component import ComponentResponse

# ------------------ Request Model ------------------


class StackRequest(ShareableRequest):
    """Request model for stacks."""

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
    components: Optional[Dict[StackComponentType, List[UUID]]] = Field(
        default=None,
        title="A mapping of stack component types to the actual"
        "instances of components of this type.",
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


# ------------------ Update Model ------------------


@update_model
class StackUpdate(StackRequest):
    """Update model for stacks."""


# ------------------ Response Model ------------------


class StackResponseMetadata(SharableResponseMetadata):
    """Response metadata model for stacks."""

    description: str = Field(
        default="",
        title="The description of the stack",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    stack_spec_path: Optional[str] = Field(
        default=None,
        title="The path to the stack spec used for mlstacks deployments.",
    )


class StackResponse(ShareableResponse):
    """Response model for stacks."""

    # Entity fields
    name: str = Field(
        title="The name of the stack.", max_length=STR_FIELD_MAX_LENGTH
    )
    components: Dict[StackComponentType, List["ComponentResponse"]] = Field(
        title="A mapping of stack component types to the actual"
        "instances of components of this type."
    )

    # Metadata related field, method and properties
    metadata: Optional["StackResponseMetadata"]

    def get_hydrated_version(self) -> "StackResponse":
        # TODO: Implement it with the parameterized calls
        from zenml.client import Client

        return Client().get_stack(self.id)

    @hydrated_property
    def description(self):
        """The description property."""
        return self.metadata.description

    @hydrated_property
    def stack_spec_path(self):
        """The stack_spec_path property."""
        return self.metadata.stack_spec_path

    # Analytics
    def get_analytics_metadata(self) -> Dict[str, Any]:
        """Add the stack components to the stack analytics metadata.

        Returns:
            Dict of analytics metadata.
        """
        metadata = super().get_analytics_metadata()
        metadata.update({ct: c[0].flavor for ct, c in self.components.items()})
        return metadata

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
            component_dict = json.loads(
                component.json(
                    include={"name", "type", "flavor", "configuration"}
                )
            )
            component_data[component_type.value] = component_dict

        # write zenml version and stack dict to YAML
        yaml_data = {
            "stack_name": self.name,
            "components": component_data,
        }

        return yaml_data
