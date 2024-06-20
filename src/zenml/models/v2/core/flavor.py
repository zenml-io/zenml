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

from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional, Union
from uuid import UUID

from pydantic import Field

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.enums import StackComponentType
from zenml.models.v2.base.base import BaseUpdate
from zenml.models.v2.base.scoped import (
    UserScopedRequest,
    UserScopedResponse,
    UserScopedResponseBody,
    UserScopedResponseMetadata,
    UserScopedResponseResources,
    WorkspaceScopedFilter,
)

if TYPE_CHECKING:
    from zenml.models import (
        ServiceConnectorRequirements,
    )
    from zenml.models.v2.core.workspace import WorkspaceResponse

# ------------------ Request Model ------------------


class FlavorRequest(UserScopedRequest):
    """Request model for flavors."""

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
    workspace: Optional[UUID] = Field(
        default=None, title="The workspace to which this resource belongs."
    )


class InternalFlavorRequest(FlavorRequest):
    """Internal flavor request model."""

    user: Optional[UUID] = Field(  # type: ignore[assignment]
        title="The id of the user that created this resource.",
        default=None,
    )


# ------------------ Update Model ------------------


class FlavorUpdate(BaseUpdate):
    """Update model for flavors."""

    name: Optional[str] = Field(
        title="The name of the Flavor.",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )
    type: Optional[StackComponentType] = Field(
        title="The type of the Flavor.", default=None
    )
    config_schema: Optional[Dict[str, Any]] = Field(
        title="The JSON schema of this flavor's corresponding configuration.",
        default=None,
    )
    connector_type: Optional[str] = Field(
        title="The type of the connector that this flavor uses.",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )
    connector_resource_type: Optional[str] = Field(
        title="The resource type of the connector that this flavor uses.",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )
    connector_resource_id_attr: Optional[str] = Field(
        title="The name of an attribute in the stack component configuration "
        "that plays the role of resource ID when linked to a service "
        "connector.",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )
    source: Optional[str] = Field(
        title="The path to the module which contains this Flavor.",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )
    integration: Optional[str] = Field(
        title="The name of the integration that the Flavor belongs to.",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )
    logo_url: Optional[str] = Field(
        title="Optionally, a url pointing to a png,"
        "svg or jpg can be attached.",
        default=None,
    )
    docs_url: Optional[str] = Field(
        title="Optionally, a url pointing to docs, within docs.zenml.io.",
        default=None,
    )
    sdk_docs_url: Optional[str] = Field(
        title="Optionally, a url pointing to SDK docs,"
        "within sdkdocs.zenml.io.",
        default=None,
    )
    is_custom: Optional[bool] = Field(
        title="Whether or not this flavor is a custom, user created flavor.",
        default=None,
    )
    workspace: Optional[UUID] = Field(
        title="The workspace to which this resource belongs.",
        default=None,
    )


# ------------------ Response Model ------------------


class FlavorResponseBody(UserScopedResponseBody):
    """Response body for flavor."""

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


class FlavorResponseMetadata(UserScopedResponseMetadata):
    """Response metadata for flavors."""

    workspace: Optional["WorkspaceResponse"] = Field(
        title="The project of this resource."
    )
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


class FlavorResponseResources(UserScopedResponseResources):
    """Class for all resource models associated with the flavor entity."""


class FlavorResponse(
    UserScopedResponse[
        FlavorResponseBody, FlavorResponseMetadata, FlavorResponseResources
    ]
):
    """Response model for flavors."""

    # Analytics
    ANALYTICS_FIELDS: ClassVar[List[str]] = [
        "id",
        "type",
        "integration",
    ]

    name: str = Field(
        title="The name of the Flavor.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    def get_hydrated_version(self) -> "FlavorResponse":
        """Get the hydrated version of the flavor.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_flavor(self.id)

    # Helper methods
    @property
    def connector_requirements(
        self,
    ) -> Optional["ServiceConnectorRequirements"]:
        """Returns the connector requirements for the flavor.

        Returns:
            The connector requirements for the flavor.
        """
        from zenml.models import (
            ServiceConnectorRequirements,
        )

        if not self.connector_resource_type:
            return None

        return ServiceConnectorRequirements(
            connector_type=self.connector_type,
            resource_type=self.connector_resource_type,
            resource_id_attr=self.connector_resource_id_attr,
        )

    # Body and metadata properties
    @property
    def type(self) -> StackComponentType:
        """The `type` property.

        Returns:
            the value of the property.
        """
        return self.get_body().type

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
    def workspace(self) -> Optional["WorkspaceResponse"]:
        """The `workspace` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().workspace

    @property
    def config_schema(self) -> Dict[str, Any]:
        """The `config_schema` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().config_schema

    @property
    def connector_type(self) -> Optional[str]:
        """The `connector_type` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().connector_type

    @property
    def connector_resource_type(self) -> Optional[str]:
        """The `connector_resource_type` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().connector_resource_type

    @property
    def connector_resource_id_attr(self) -> Optional[str]:
        """The `connector_resource_id_attr` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().connector_resource_id_attr

    @property
    def source(self) -> str:
        """The `source` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().source

    @property
    def docs_url(self) -> Optional[str]:
        """The `docs_url` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().docs_url

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """The `sdk_docs_url` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().sdk_docs_url

    @property
    def is_custom(self) -> bool:
        """The `is_custom` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().is_custom


# ------------------ Filter Model ------------------


class FlavorFilter(WorkspaceScopedFilter):
    """Model to enable advanced filtering of all Flavors."""

    name: Optional[str] = Field(
        default=None,
        description="Name of the flavor",
    )
    type: Optional[str] = Field(
        default=None,
        description="Stack Component Type of the stack flavor",
    )
    integration: Optional[str] = Field(
        default=None,
        description="Integration associated with the flavor",
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
