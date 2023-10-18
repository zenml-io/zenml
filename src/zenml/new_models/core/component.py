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

from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional
from uuid import UUID

from pydantic import Field, validator

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.enums import StackComponentType
from zenml.new_models.base import (
    SharableResponseBody,
    SharableResponseMetadata,
    ShareableRequest,
    ShareableResponse,
    hydrated_property,
    update_model,
)
from zenml.utils import secret_utils

if TYPE_CHECKING:
    from zenml.new_models.core.service_connector import (
        ServiceConnectorResponse,
    )
# ------------------ Request Model ------------------


class ComponentRequest(ShareableRequest):
    """Request model for components."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = ["type", "flavor"]

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
    labels: Optional[Dict[str, Any]] = Field(
        default=None,
        title="The stack component labels.",
    )
    component_spec_path: Optional[str] = Field(
        default=None,
        title="The path to the component spec used for mlstacks deployments.",
    )
    connector: Optional[UUID] = Field(
        default=None,
        title="The service connector linked to this stack component.",
    )
    connector_resource_id: Optional[str] = Field(
        default=None,
        description="The ID of a specific resource instance to "
        "gain access to through the connector",
    )

    @validator("name")
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


# ------------------ Update Model ------------------


@update_model
class ComponentUpdate(ComponentRequest):
    """Update model for stack components."""


# ------------------ Response Model ------------------
class ComponentResponseBody(SharableResponseBody):
    """Response body for components."""

    type: StackComponentType = Field(
        title="The type of the stack component.",
    )
    flavor: str = Field(
        title="The flavor of the stack component.",
        max_length=STR_FIELD_MAX_LENGTH,
    )


class ComponentResponseMetadata(SharableResponseMetadata):
    """Response metadata for components."""

    configuration: Dict[str, Any] = Field(
        title="The stack component configuration.",
    )
    labels: Optional[Dict[str, Any]] = Field(
        default=None,
        title="The stack component labels.",
    )
    component_spec_path: Optional[str] = Field(
        default=None,
        title="The path to the component spec used for mlstacks deployments.",
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


class ComponentResponse(ShareableResponse):
    """Response model for components."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = ["type", "flavor"]

    name: str = Field(
        title="The name of the stack component.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    # Body and metadata pair
    body: "ComponentResponseBody"
    metadata: Optional["ComponentResponseMetadata"]

    def get_hydrated_version(self) -> "ComponentResponse":
        """Get the hydrated version of this component."""
        from zenml.client import Client

        return Client().get_stack_component(self.id)

    # Body and metadata properties
    @property
    def type(self):
        """The `type` property."""
        return self.body.type

    @property
    def flavor(self):
        """The `flavor` property."""
        return self.body.flavor

    @hydrated_property
    def configuration(self):
        """The `configuration` property."""
        return self.metadata.configuration

    @hydrated_property
    def labels(self):
        """The `labels` property."""
        return self.metadata.labels

    @hydrated_property
    def component_spec_path(self):
        """The `component_spec_path` property."""
        return self.metadata.component_spec_path

    @hydrated_property
    def connector_resource_id(self):
        """The `connector_resource_id` property."""
        return self.metadata.connector_resource_id

    @hydrated_property
    def connector(self):
        """The `connector` property."""
        return self.metadata.connector
