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
"""Model definitions for ZenML service connectors."""

import json
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Type, Union
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    SecretStr,
    root_validator,
    validator,
)

from zenml.models.base_models import (
    ShareableRequestModel,
    ShareableResponseModel,
    update_model,
)
from zenml.models.constants import STR_FIELD_MAX_LENGTH
from zenml.models.filter_models import ShareableWorkspaceScopedFilterModel

# ---- #
# BASE #
# ---- #


class ResourceTypeModel(BaseModel):
    """Resource type specification.

    Describes the authentication methods and resource instantiation model for
    one or more resource types.
    """

    name: str = Field(
        title="User readable name for the resource type.",
    )
    resource_type: str = Field(
        title="Resource type identifier.",
    )
    description: str = Field(
        default="",
        title="A description of the resource type.",
    )
    auth_methods: List[str] = Field(
        title="The list of authentication methods that can be used to access "
        "resources of this type.",
    )
    multi_instance: bool = Field(
        default=False,
        title="Models if the connector can be used to access multiple "
        "instances of this resource type. If set to False, the "
        "resource ID field is ignored. If set to True, the resource ID can "
        "be supplied either when the connector is configured or when it is "
        "used to access the resource.",
    )
    logo_url: Optional[str] = Field(
        default=None,
        title="Optionally, a url pointing to a png,"
        "svg or jpg can be attached.",
    )

    def is_equivalent_resource_id(
        self, resource_id: str, target_resource_id: str
    ) -> bool:
        """Check whether a resource ID is equivalent to another one.

        Given two resource instance IDs, this method returns True if they are
        equivalent to each other, and False otherwise.

        This method is used to answer the questions: "Can this connector be
        used to access a resource instance with this ID ?" and "Which
        connector instances can be used to access a resource instance with
        this ID?".

        Override this method to implement mechanisms such as:

        * resource instance ID aliases, where two or more identifiers can be
        used interchangeably to refer to the same resource instance (e.g. a
        GCS bucket can be referred to by its name, its URI or its ID).
        * multiple resource ID formats, where the same resource instance ID can
        have multiple forms, all of which are equivalent to each other
        (e.g. an S3 bucket can be referred to by using s3://bucket-name or
        bucket-name).

        Args:
            resource_id: The resource instance ID to match.
            target_resource_id: The resource instance ID to match
                against.

        Returns:
            True if the resource IDs are equivalent, False otherwise.
        """
        return resource_id == target_resource_id


class AuthenticationMethodModel(BaseModel):
    """Authentication method specification.

    Describes the schema for the configuration and secrets that need to be
    provided to configure an authentication method, as well as the types of
    resources that the authentication method can be used to access.
    """

    name: str = Field(
        title="User readable name for the authentication method.",
    )
    auth_method: str = Field(
        title="The name of the authentication method.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    description: str = Field(
        default="",
        title="A description of the authentication method.",
    )
    config_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        title="The JSON schema of the configuration for this authentication "
        "method.",
    )
    config_class: Type[BaseModel]

    @root_validator(pre=True)
    def convert_config_schema_to_model(
        cls, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert the config class into a JSON schema.

        Args:
            values: The values to validate.

        Returns:
            The validated values.
        """
        if "config_schema" in values or "config_class" not in values:
            # Let the other validators handle the config schema and
            # config class
            return values

        config_class = values["config_class"]
        if issubclass(config_class, BaseModel):
            values["config_schema"] = json.loads(config_class.schema_json())

        return values

    class Config:
        """Pydantic config class."""

        # Exclude the config class from the model schema. This is only used
        # internally to convert the config schema into a Pydantic model.
        fields = {"config_class": {"exclude": True}}


class ServiceConnectorTypeModel(BaseModel):
    """Service connector type specification.

    Describes the types of resources to which the service connector can be used
    to gain access and the authentication methods that are supported by the
    service connector.

    The connector type, resource types, resource IDs and authentication
    methods can all be used as search criteria to lookup and filter service
    connector instances that are compatible with the requirements of a consumer
    (e.g. a stack component).
    """

    name: str = Field(
        title="User readable name for the service connector type.",
    )
    type: str = Field(
        title="The type of service connector. It can be used to represent a "
        "generic resource (e.g. Docker, Kubernetes) or a group of different "
        "resources accessible through a common interface or point of access "
        "and authentication (e.g. a cloud provider or a platform).",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    description: str = Field(
        default="",
        title="A description of the service connector.",
    )
    resource_types: List[ResourceTypeModel] = Field(
        title="A list of resource types that the connector can be used to "
        "access.",
    )
    auth_methods: List[AuthenticationMethodModel] = Field(
        title="A list of specifications describing the authentication "
        "methods that are supported by the service connector, along with the "
        "configuration and secrets attributes that need to be configured for "
        "them.",
    )
    source: Optional[str] = Field(
        default=None,
        title="The path to the module which contains this service connector.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    integration: Optional[str] = Field(
        default=None,
        title="The name of the integration that the service connector belongs "
        "to.",
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
        "within apidocs.zenml.io.",
    )

    @validator("resource_types")
    def validate_resource_types(
        cls, v: List[ResourceTypeModel]
    ) -> List[ResourceTypeModel]:
        """Validate that the resource types are unique.

        Args:
            v: The list of resource types.

        Returns:
            The list of resource types.
        """
        # Gather all resource types from the list of resource type
        # specifications.
        resource_types = [r.resource_type for r in v]
        if len(resource_types) != len(set(resource_types)):
            raise ValueError(
                "Two or more resource type specifications must not list "
                "the same resource type."
            )

        return v

    @validator("auth_methods")
    def validate_auth_methods(
        cls, v: List[AuthenticationMethodModel]
    ) -> List[AuthenticationMethodModel]:
        """Validate that the authentication methods are unique.

        Args:
            v: The list of authentication methods.

        Returns:
            The list of authentication methods.
        """
        # Gather all auth methods from the list of auth method
        # specifications.
        auth_methods = [a.auth_method for a in v]
        if len(auth_methods) != len(set(auth_methods)):
            raise ValueError(
                "Two or more authentication method specifications must not "
                "share the same authentication method value."
            )

        return v

    @property
    def resource_type_map(
        self,
    ) -> Dict[str, ResourceTypeModel]:
        """Returns a map of resource types to resource type specifications.

        Returns:
            A map of resource types to resource type specifications.
        """
        return {r.resource_type: r for r in self.resource_types}

    @property
    def auth_method_map(
        self,
    ) -> Dict[str, AuthenticationMethodModel]:
        """Returns a map of authentication methods to authentication method specifications.

        Returns:
            A map of authentication methods to authentication method
            specifications.
        """
        return {a.auth_method: a for a in self.auth_methods}

    def find_resource_specifications(
        self,
        auth_method: str,
        resource_type: str,
        resource_id: Optional[str] = None,
    ) -> Tuple[AuthenticationMethodModel, ResourceTypeModel]:
        """Find the specifications for a configurable resource.

        Validate the supplied connector configuration parameters against the
        connector specification and return the matching authentication method
        specification and resource specification.

        Args:
            auth_method: The name of the authentication method.
            resource_type: The type of resource being configured.
            resource_id: The ID of the resource being configured. Only valid
                for authentication methods that support resource IDs.

        Returns:
            The authentication method specification and resource specification
            for the specified authentication method and resource type.

        Raises:
            KeyError: If the authentication method is not supported by the
                connector for the specified resource type and ID.
            ValueError: If a resource ID is provided for a resource type that
                does not support multiple instances.

        """
        # Verify the authentication method
        auth_method_map = self.auth_method_map
        if auth_method in auth_method_map:
            # A match was found for the authentication method
            auth_method_spec = auth_method_map[auth_method]
        else:
            # No match was found for the authentication method
            raise KeyError(
                f"connector type '{self.type}' does not support the "
                f"'{auth_method}' authentication method. Supported "
                f"authentication methods are: {list(auth_method_map.keys())}."
            )

        # Verify the resource type
        resource_type_map = self.resource_type_map
        if resource_type in resource_type_map:
            resource_type_spec = resource_type_map[resource_type]
        else:
            raise KeyError(
                f"connector type '{self.type}' does not support resource type "
                f"'{resource_type}'. Supported resource types are: "
                f"{list(resource_type_map.keys())}."
            )

        if auth_method not in resource_type_spec.auth_methods:
            raise KeyError(
                f"the '{self.type}' connector type does not support the "
                f"'{auth_method}' authentication method for the "
                f"'{resource_type}' resource type. Supported authentication "
                f"methods are: {resource_type_spec.auth_methods}."
            )

        # Verify the resource ID
        if resource_id and not resource_type_spec.multi_instance:
            raise ValueError(
                f"the '{self.type}' connector type does not support "
                f"multiple instances for the '{resource_type}' resource type "
                f"but a resource ID value was provided: {resource_id}"
            )

        return auth_method_spec, resource_type_spec


class ServiceConnectorBaseModel(BaseModel):
    """Base model for service connectors."""

    name: str = Field(
        title="The service connector name.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    type: str = Field(
        title="The type of service connector.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    description: str = Field(
        default="",
        title="The service connector instance description.",
    )
    auth_method: str = Field(
        title="The authentication method that the connector instance uses to "
        "access the resources.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    resource_type: str = Field(
        title="The type of resource that the connector instance can be used "
        "to gain access to.",
    )
    resource_id: Optional[str] = Field(
        default=None,
        title="Uniquely identifies a specific resource instance that the "
        "connector instance can be used to access. Only applicable if the "
        "connector's specification indicates that resource IDs are supported "
        "for the configured resource type. If applicable and if omitted in the "
        "connector configuration, a resource ID must be provided by the "
        "connector consumer at runtime.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    configuration: Dict[str, Any] = Field(
        default_factory=dict,
        title="The service connector configuration, not including secrets.",
    )
    secrets: Dict[str, Optional[SecretStr]] = Field(
        default_factory=dict,
        title="The service connector secrets.",
    )
    labels: Dict[str, str] = Field(
        default_factory=dict,
        title="Service connector labels.",
    )


class ServiceConnectorRequirements(BaseModel):
    """Service connector requirements.

    Describes requirements that a service connector consumer has for a
    service connector instance that it needs in order to access a resource.

    Attributes:
        connector_type: The type of service connector that is required. If
            omitted, any service connector type can be used.
        resource_type: The type of resource that the service connector instance
            must be able to access. If omitted, any resource type can be
            accessed.
    """

    connector_type: Optional[str] = None
    resource_type: Optional[str] = None

    def is_satisfied_by(
        self, connector: "ServiceConnectorBaseModel"
    ) -> Tuple[bool, str]:
        """Check if the requirements are satisfied by a connector.

        Args:
            connector: The connector to check.

        Returns:
            True if the requirements are satisfied, False otherwise, and a
            message describing the reason for the failure.
        """
        if self.connector_type and self.connector_type != connector.type:
            return (
                False,
                f"connector type '{connector.type}' does not match the "
                f"'{self.connector_type}' connector type specified in the "
                "requirements",
            )
        if (
            self.resource_type
            and self.resource_type != connector.resource_type
        ):
            return False, (
                f"connector resource type '{connector.resource_type}' "
                f"does not match the '{self.resource_type}' "
                "resource type specified in the requirements"
            )

        return True, ""


# -------- #
# RESPONSE #
# -------- #


class ServiceConnectorResponseModel(
    ServiceConnectorBaseModel, ShareableResponseModel
):
    """Response model for service connectors."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = [
        "type",
        "auth_method",
        "resource_type",
    ]

    secret_id: Optional[UUID] = Field(
        default=None,
        title="The ID of the secret that contains the service connector "
        "secret configuration values.",
    )


# ------ #
# FILTER #
# ------ #


class ServiceConnectorFilterModel(ShareableWorkspaceScopedFilterModel):
    """Model to enable advanced filtering of service connectors."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *ShareableWorkspaceScopedFilterModel.FILTER_EXCLUDE_FIELDS,
        "scope_type",
    ]
    CLI_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *ShareableWorkspaceScopedFilterModel.CLI_EXCLUDE_FIELDS,
        "scope_type",
    ]
    scope_type: Optional[str] = Field(
        default=None,
        description="The type to scope this query to.",
    )

    is_shared: Optional[Union[bool, str]] = Field(
        default=None,
        description="If the service connector is shared or private",
    )
    name: Optional[str] = Field(
        default=None,
        description="The name to filter by",
    )
    type: Optional[str] = Field(
        default=None,
        description="The type of service connector to filter by",
    )
    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Workspace to filter by"
    )
    user_id: Optional[Union[UUID, str]] = Field(
        default=None, description="User to filter by"
    )
    auth_method: Optional[str] = Field(
        default=None,
        title="Filter by the authentication method configured for the "
        "connector",
    )
    resource_type: Optional[str] = Field(
        default=None,
        title="Filter by the type of resource that the connector can be used "
        "to access",
    )
    resource_id: Optional[str] = Field(
        default=None,
        title="Filter by the ID of the resource instance that the connector "
        "is configured to access",
    )
    labels: Optional[Dict[str, Optional[str]]] = Field(
        default=None,
        title="Filter by labels",
    )
    secret_id: Optional[Union[UUID, str]] = Field(
        default=None,
        title="Filter by the ID of the secret that contains the service "
        "connector's credentials",
    )


# ------- #
# REQUEST #
# ------- #


class ServiceConnectorRequestModel(
    ServiceConnectorBaseModel, ShareableRequestModel
):
    """Request model for service connectors."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = [
        "type",
        "auth_method",
        "resource_type",
    ]


# ------ #
# UPDATE #
# ------ #


@update_model
class ServiceConnectorUpdateModel(ServiceConnectorRequestModel):
    """Update model for service connectors."""
