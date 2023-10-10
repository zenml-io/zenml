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
    SharableResponseMetadataModel,
    ShareableRequestModel,
    ShareableResponseModel,
    hydrated_property,
    update_model,
)
from zenml.utils import secret_utils

if TYPE_CHECKING:
    from zenml.new_models.core.service_connector_models import (
        ServiceConnectorResponseModel,
    )
# ------------------ Request Model ------------------


class ComponentRequestModel(ShareableRequestModel):
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
class ComponentUpdateModel(ComponentRequestModel):
    """Update model for stack components."""


# ------------------ Response Model ------------------


class ComponentResponseMetadataModel(SharableResponseMetadataModel):
    """Response metadata model for components."""

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


class ComponentResponseModel(ShareableResponseModel):
    """Response model for components."""

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
    connector_resource_id: Optional[str] = Field(
        default=None,
        description="The ID of a specific resource instance to "
        "gain access to through the connector",
    )
    connector: Optional["ServiceConnectorResponseModel"] = Field(
        default=None,
        title="The service connector linked to this stack component.",
    )

    # Metadata related field, method and properties
    metadata: Optional["ComponentResponseMetadataModel"]

    def get_hydrated_version(self) -> "ComponentResponseModel":
        # TODO: Implement it with the parameterized calls
        from zenml.client import Client

        return Client().get_stack_component(self.id, hydrate=True)

    @hydrated_property
    def configuration(self):
        """The configuration property."""
        return self.metadata.configuration

    @hydrated_property
    def labels(self):
        """The labels property."""
        return self.metadata.labels

    @hydrated_property
    def component_spec_path(self):
        """The component_spec_path property."""
        return self.metadata.component_spec_path
