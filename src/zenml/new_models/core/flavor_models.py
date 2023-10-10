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
"""Models representing flavors."""

from typing import Any, ClassVar, Dict, List, Optional

from pydantic import Field

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.enums import StackComponentType
from zenml.models.service_connector_models import (
    ServiceConnectorRequirements,
)
from zenml.new_models.base import (
    WorkspaceScopedRequestModel,
    WorkspaceScopedResponseMetadataModel,
    WorkspaceScopedResponseModel,
    hydrated_property,
    update_model,
)

# ------------------ Request Model ------------------


class FlavorRequestModel(WorkspaceScopedRequestModel):
    """Request model for flavors"""

    ANALYTICS_FIELDS: ClassVar[List[str]] = [
        "type",
        "integration",
    ]

    name: str = Field(
        title="The name of the Flavor.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    type: StackComponentType = Field(title="The type of the Flavor.")
    config_schema: Dict[str, Any] = Field(
        title="The JSON schema of this flavor's corresponding configuration.",
    )
    connector_type: Optional[str] = Field(
        default=None,
        title="The type of the connector that this flavor uses.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    connector_resource_type: Optional[str] = Field(
        default=None,
        title="The resource type of the connector that this flavor uses.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    connector_resource_id_attr: Optional[str] = Field(
        default=None,
        title="The name of an attribute in the stack component configuration "
        "that plays the role of resource ID when linked to a service "
        "connector.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    source: str = Field(
        title="The path to the module which contains this Flavor.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    integration: Optional[str] = Field(
        title="The name of the integration that the Flavor belongs to.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    logo_url: Optional[str] = Field(
        default=None,
        title="Optionally, a url pointing to a png,"
        "svg or jpg can be attached.",
    )
    docs_url: Optional[str] = Field(
        default=None,
        title="Optionally, a url pointing to docs, within docs.zenml.io.",
    )
    sdk_docs_url: Optional[str] = Field(
        default=None,
        title="Optionally, a url pointing to SDK docs,"
        "within sdkdocs.zenml.io.",
    )
    is_custom: bool = Field(
        title="Whether or not this flavor is a custom, user created flavor.",
        default=True,
    )


# ------------------ Update Model ------------------


@update_model
class FlavorUpdateModel(FlavorRequestModel):
    """Update model for flavors."""


# ------------------ Response Model ------------------


class FlavorResponseMetadataModel(WorkspaceScopedResponseMetadataModel):
    """Response metadata model for flavors"""

    config_schema: Dict[str, Any] = Field(
        title="The JSON schema of this flavor's corresponding configuration.",
    )
    connector_type: Optional[str] = Field(
        default=None,
        title="The type of the connector that this flavor uses.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    connector_resource_type: Optional[str] = Field(
        default=None,
        title="The resource type of the connector that this flavor uses.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    connector_resource_id_attr: Optional[str] = Field(
        default=None,
        title="The name of an attribute in the stack component configuration "
        "that plays the role of resource ID when linked to a service "
        "connector.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    source: str = Field(
        title="The path to the module which contains this Flavor.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    docs_url: Optional[str] = Field(
        default=None,
        title="Optionally, a url pointing to docs, within docs.zenml.io.",
    )
    sdk_docs_url: Optional[str] = Field(
        default=None,
        title="Optionally, a url pointing to SDK docs,"
        "within sdkdocs.zenml.io.",
    )
    is_custom: bool = Field(
        title="Whether or not this flavor is a custom, user created flavor.",
        default=True,
    )


class FlavorResponseModel(WorkspaceScopedResponseModel):
    """Response model for flavors"""

    # Analytics
    ANALYTICS_FIELDS: ClassVar[List[str]] = [
        "id",
        "type",
        "integration",
    ]

    # Entity fields
    name: str = Field(
        title="The name of the Flavor.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    type: StackComponentType = Field(title="The type of the Flavor.")
    integration: Optional[str] = Field(
        title="The name of the integration that the Flavor belongs to.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    logo_url: Optional[str] = Field(
        default=None,
        title="Optionally, a url pointing to a png,"
        "svg or jpg can be attached.",
    )

    # Metadata related field, method and properties
    metadata: Optional["FlavorResponseMetadataModel"]

    def get_hydrated_version(self) -> "FlavorResponseModel":
        # TODO: Implement it with the parameterized calls
        from zenml.client import Client

        return Client().get_flavor(self.id, hydrate=True)

    @hydrated_property
    def config_schema(self):
        """The config_schema property."""
        return self.metadata.config_schema

    @hydrated_property
    def connector_type(self):
        """The connector_type property."""
        return self.metadata.connector_type

    @hydrated_property
    def connector_resource_type(self):
        """The connector_resource_type property."""
        return self.metadata.connector_resource_type

    @hydrated_property
    def connector_resource_id_attr(self):
        """The connector_resource_id_attr property."""
        return self.metadata.connector_resource_id_attr

    @hydrated_property
    def source(self):
        """The source property."""
        return self.metadata.source

    @hydrated_property
    def docs_url(self):
        """The docs_url property."""
        return self.metadata.docs_url

    @hydrated_property
    def sdk_docs_url(self):
        """The sdk_docs_url property."""
        return self.metadata.sdk_docs_url

    @hydrated_property
    def is_custom(self):
        """The is_custom property."""
        return self.metadata.is_custom

    # Helper methods
    @property
    def connector_requirements(self) -> Optional[ServiceConnectorRequirements]:
        """Returns the connector requirements for the flavor.

        Returns:
            The connector requirements for the flavor.
        """
        if not self.connector_resource_type:
            return None

        return ServiceConnectorRequirements(
            connector_type=self.connector_type,
            resource_type=self.connector_resource_type,
            resource_id_attr=self.connector_resource_id_attr,
        )
