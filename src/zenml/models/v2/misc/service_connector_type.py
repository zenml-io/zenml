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
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.models.v2.core.component import ComponentBase, ComponentResponse
    from zenml.models.v2.core.service_connector import (
        ServiceConnectorRequest,
        ServiceConnectorResponse,
    )
    from zenml.service_connectors.service_connector import ServiceConnector

logger = get_logger(__name__)


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
    supports_instances: bool = Field(
        default=False,
        title="Specifies if a single connector instance can be used to access "
        "multiple instances of this resource type. If set to True, the "
        "connector is able to provide a list of resource IDs identifying all "
        "the resources that it can access and a resource ID needs to be "
        "explicitly configured or supplied when access to a resource is "
        "requested. If set to False, a connector instance is only able to "
        "access a single resource and a resource ID is not required to access "
        "the resource.",
    )
    logo_url: Optional[str] = Field(
        default=None,
        title="Optionally, a URL pointing to a png,"
        "svg or jpg file can be attached.",
    )
    emoji: Optional[str] = Field(
        default=None,
        title="Optionally, a python-rich emoji can be attached.",
    )

    @property
    def emojified_resource_type(self) -> str:
        """Get the emojified resource type.

        Returns:
            The emojified resource type.
        """
        if not self.emoji:
            return self.resource_type
        return f"{self.emoji} {self.resource_type}"


class AuthenticationMethodModel(BaseModel):
    """Authentication method specification.

    Describes the schema for the configuration and secrets that need to be
    provided to configure an authentication method.
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
    config_schema: Dict[str, Any] = Field(
        default_factory=dict,
        title="The JSON schema of the configuration for this authentication "
        "method.",
    )
    min_expiration_seconds: Optional[int] = Field(
        default=None,
        title="The minimum number of seconds that the authentication "
        "session can be configured to be valid for. Set to None for "
        "authentication sessions and long-lived credentials that don't expire.",
    )
    max_expiration_seconds: Optional[int] = Field(
        default=None,
        title="The maximum number of seconds that the authentication "
        "session can be configured to be valid for. Set to None for "
        "authentication sessions and long-lived credentials that don't expire.",
    )
    default_expiration_seconds: Optional[int] = Field(
        default=None,
        title="The default number of seconds that the authentication "
        "session is valid for. Set to None for authentication sessions and "
        "long-lived credentials that don't expire.",
    )
    _config_class: Optional[Type[BaseModel]] = None

    def __init__(
        self, config_class: Optional[Type[BaseModel]] = None, **values: Any
    ):
        """Initialize the authentication method.

        Args:
            config_class: The configuration class for the authentication
                method.
            **values: The data to initialize the authentication method with.
        """
        if config_class:
            values["config_schema"] = json.loads(config_class.schema_json())
        super().__init__(**values)
        self._config_class = config_class

    @property
    def config_class(self) -> Optional[Type[BaseModel]]:
        """Get the configuration class for the authentication method.

        Returns:
            The configuration class for the authentication method.
        """
        return self._config_class

    def supports_temporary_credentials(self) -> bool:
        """Check if the authentication method supports temporary credentials.

        Returns:
            True if the authentication method supports temporary credentials,
            False otherwise.
        """
        return (
            self.min_expiration_seconds is not None
            or self.max_expiration_seconds is not None
            or self.default_expiration_seconds is not None
        )

    def validate_expiration(
        self, expiration_seconds: Optional[int]
    ) -> Optional[int]:
        """Validate the expiration time.

        Args:
            expiration_seconds: The expiration time in seconds. If None, the
                default expiration time is used, if applicable.

        Returns:
            The expiration time in seconds or None if not applicable.

        Raises:
            ValueError: If the expiration time is not valid.
        """
        if not self.supports_temporary_credentials():
            if expiration_seconds is not None:
                # Expiration is not supported
                raise ValueError(
                    "Expiration time is not supported for this authentication "
                    f"method but a value was provided: {expiration_seconds}"
                )

            return None

        expiration_seconds = (
            expiration_seconds or self.default_expiration_seconds
        )

        if expiration_seconds is None:
            return None

        if self.min_expiration_seconds is not None:
            if expiration_seconds < self.min_expiration_seconds:
                raise ValueError(
                    f"Expiration time must be at least "
                    f"{self.min_expiration_seconds} seconds."
                )

        if self.max_expiration_seconds is not None:
            if expiration_seconds > self.max_expiration_seconds:
                raise ValueError(
                    f"Expiration time must be at most "
                    f"{self.max_expiration_seconds} seconds."
                )

        return expiration_seconds

    class Config:
        """Pydantic config class."""

        underscore_attrs_are_private = True


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
    connector_type: str = Field(
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
    supports_auto_configuration: bool = Field(
        default=False,
        title="Models if the connector can be configured automatically based "
        "on information extracted from a local environment.",
    )
    logo_url: Optional[str] = Field(
        default=None,
        title="Optionally, a URL pointing to a png,"
        "svg or jpg can be attached.",
    )
    emoji: Optional[str] = Field(
        default=None,
        title="Optionally, a python-rich emoji can be attached.",
    )
    docs_url: Optional[str] = Field(
        default=None,
        title="Optionally, a URL pointing to docs, within docs.zenml.io.",
    )
    sdk_docs_url: Optional[str] = Field(
        default=None,
        title="Optionally, a URL pointing to SDK docs,"
        "within sdkdocs.zenml.io.",
    )
    local: bool = Field(
        default=True,
        title="If True, the service connector is available locally.",
    )
    remote: bool = Field(
        default=False,
        title="If True, the service connector is available remotely.",
    )
    _connector_class: Optional[Type["ServiceConnector"]] = None

    @property
    def connector_class(self) -> Optional[Type["ServiceConnector"]]:
        """Get the service connector class.

        Returns:
            The service connector class.
        """
        return self._connector_class

    @property
    def emojified_connector_type(self) -> str:
        """Get the emojified connector type.

        Returns:
            The emojified connector type.
        """
        if not self.emoji:
            return self.connector_type
        return f"{self.emoji} {self.connector_type}"

    @property
    def emojified_resource_types(self) -> List[str]:
        """Get the emojified connector types.

        Returns:
            The emojified connector types.
        """
        return [
            resource_type.emojified_resource_type
            for resource_type in self.resource_types
        ]

    def set_connector_class(
        self, connector_class: Type["ServiceConnector"]
    ) -> None:
        """Set the service connector class.

        Args:
            connector_class: The service connector class.
        """
        self._connector_class = connector_class

    @validator("resource_types")
    def validate_resource_types(
        cls, values: List[ResourceTypeModel]
    ) -> List[ResourceTypeModel]:
        """Validate that the resource types are unique.

        Args:
            values: The list of resource types.

        Returns:
            The list of resource types.

        Raises:
            ValueError: If two or more resource type specifications list the
                same resource type.
        """
        # Gather all resource types from the list of resource type
        # specifications.
        resource_types = [r.resource_type for r in values]
        if len(resource_types) != len(set(resource_types)):
            raise ValueError(
                "Two or more resource type specifications must not list "
                "the same resource type."
            )

        return values

    @validator("auth_methods")
    def validate_auth_methods(
        cls, values: List[AuthenticationMethodModel]
    ) -> List[AuthenticationMethodModel]:
        """Validate that the authentication methods are unique.

        Args:
            values: The list of authentication methods.

        Returns:
            The list of authentication methods.

        Raises:
            ValueError: If two or more authentication method specifications
                share the same authentication method value.
        """
        # Gather all auth methods from the list of auth method
        # specifications.
        auth_methods = [a.auth_method for a in values]
        if len(auth_methods) != len(set(auth_methods)):
            raise ValueError(
                "Two or more authentication method specifications must not "
                "share the same authentication method value."
            )

        return values

    @property
    def resource_type_dict(
        self,
    ) -> Dict[str, ResourceTypeModel]:
        """Returns a map of resource types to resource type specifications.

        Returns:
            A map of resource types to resource type specifications.
        """
        return {r.resource_type: r for r in self.resource_types}

    @property
    def auth_method_dict(
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
        resource_type: Optional[str] = None,
    ) -> Tuple[AuthenticationMethodModel, Optional[ResourceTypeModel]]:
        """Find the specifications for a configurable resource.

        Validate the supplied connector configuration parameters against the
        connector specification and return the matching authentication method
        specification and resource specification.

        Args:
            auth_method: The name of the authentication method.
            resource_type: The type of resource being configured.

        Returns:
            The authentication method specification and resource specification
            for the specified authentication method and resource type.

        Raises:
            KeyError: If the authentication method is not supported by the
                connector for the specified resource type and ID.
        """
        # Verify the authentication method
        auth_method_dict = self.auth_method_dict
        if auth_method in auth_method_dict:
            # A match was found for the authentication method
            auth_method_spec = auth_method_dict[auth_method]
        else:
            # No match was found for the authentication method
            raise KeyError(
                f"connector type '{self.connector_type}' does not support the "
                f"'{auth_method}' authentication method. Supported "
                f"authentication methods are: {list(auth_method_dict.keys())}."
            )

        if resource_type is None:
            # No resource type was specified, so no resource type
            # specification can be returned.
            return auth_method_spec, None

        # Verify the resource type
        resource_type_dict = self.resource_type_dict
        if resource_type in resource_type_dict:
            resource_type_spec = resource_type_dict[resource_type]
        else:
            raise KeyError(
                f"connector type '{self.connector_type}' does not support "
                f"resource type '{resource_type}'. Supported resource types "
                f"are: {list(resource_type_dict.keys())}."
            )

        if auth_method not in resource_type_spec.auth_methods:
            raise KeyError(
                f"the '{self.connector_type}' connector type does not support "
                f"the '{auth_method}' authentication method for the "
                f"'{resource_type}' resource type. Supported authentication "
                f"methods are: {resource_type_spec.auth_methods}."
            )

        return auth_method_spec, resource_type_spec

    class Config:
        """Pydantic config class."""

        underscore_attrs_are_private = True


class ServiceConnectorRequirements(BaseModel):
    """Service connector requirements.

    Describes requirements that a service connector consumer has for a
    service connector instance that it needs in order to access a resource.

    Attributes:
        connector_type: The type of service connector that is required. If
            omitted, any service connector type can be used.
        resource_type: The type of resource that the service connector instance
            must be able to access.
        resource_id_attr: The name of an attribute in the stack component
            configuration that contains the resource ID of the resource that
            the service connector instance must be able to access.
    """

    connector_type: Optional[str] = None
    resource_type: str
    resource_id_attr: Optional[str] = None

    def is_satisfied_by(
        self,
        connector: Union[
            "ServiceConnectorResponse", "ServiceConnectorRequest"
        ],
        component: Union["ComponentResponse", "ComponentBase"],
    ) -> Tuple[bool, str]:
        """Check if the requirements are satisfied by a connector.

        Args:
            connector: The connector to check.
            component: The stack component that the connector is associated
                with.

        Returns:
            True if the requirements are satisfied, False otherwise, and a
            message describing the reason for the failure.
        """
        if self.connector_type and self.connector_type != connector.type:
            return (
                False,
                f"connector type '{connector.type}' does not match the "
                f"'{self.connector_type}' connector type specified in the "
                "stack component requirements",
            )
        if self.resource_type not in connector.resource_types:
            return False, (
                f"connector does not provide the '{self.resource_type}' "
                "resource type specified in the stack component requirements. "
                "Only the following resource types are supported: "
                f"{', '.join(connector.resource_types)}"
            )
        if self.resource_id_attr:
            resource_id = component.configuration.get(self.resource_id_attr)
            if not resource_id:
                return (
                    False,
                    f"the '{self.resource_id_attr}' stack component "
                    f"configuration attribute plays the role of resource "
                    f"identifier, but the stack component does not contain a "
                    f"'{self.resource_id_attr}' attribute. Please add the "
                    f"'{self.resource_id_attr}' attribute to the stack "
                    "component configuration and try again.",
                )

        return True, ""


class ServiceConnectorTypedResourcesModel(BaseModel):
    """Service connector typed resources list.

    Lists the resource instances that a service connector can provide
    access to.
    """

    resource_type: str = Field(
        title="The type of resource that the service connector instance can "
        "be used to access.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    resource_ids: Optional[List[str]] = Field(
        default=None,
        title="The resource IDs of all resource instances that the service "
        "connector instance can be used to access. Omitted (set to None) for "
        "multi-type service connectors that didn't explicitly request to "
        "fetch resources for all resource types. Also omitted if an error "
        "occurred while listing the resource instances or if no resources are "
        "listed due to authorization issues or lack of permissions (in both "
        "cases the 'error' field is set to an error message). For resource "
        "types that do not support multiple instances, a single resource ID is "
        "listed.",
    )

    error: Optional[str] = Field(
        default=None,
        title="An error message describing why the service connector instance "
        "could not list the resources that it is configured to access.",
    )


class ServiceConnectorResourcesModel(BaseModel):
    """Service connector resources list.

    Lists the resource types and resource instances that a service connector
    can provide access to.
    """

    id: Optional[UUID] = Field(
        default=None,
        title="The ID of the service connector instance providing this "
        "resource.",
    )

    name: Optional[str] = Field(
        default=None,
        title="The name of the service connector instance providing this "
        "resource.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    connector_type: Union[str, "ServiceConnectorTypeModel"] = Field(
        title="The type of service connector.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    resources: List[ServiceConnectorTypedResourcesModel] = Field(
        default_factory=list,
        title="The list of resources that the service connector instance can "
        "give access to. Contains one entry for every resource type "
        "that the connector is configured for.",
    )

    error: Optional[str] = Field(
        default=None,
        title="A global error message describing why the service connector "
        "instance could not authenticate to the remote service.",
    )

    @property
    def resources_dict(self) -> Dict[str, ServiceConnectorTypedResourcesModel]:
        """Get the resources as a dictionary indexed by resource type.

        Returns:
            The resources as a dictionary indexed by resource type.
        """
        return {
            resource.resource_type: resource for resource in self.resources
        }

    @property
    def resource_types(self) -> List[str]:
        """Get the resource types.

        Returns:
            The resource types.
        """
        return [resource.resource_type for resource in self.resources]

    def set_error(
        self, error: str, resource_type: Optional[str] = None
    ) -> None:
        """Set a global error message or an error for a single resource type.

        Args:
            error: The error message.
            resource_type: The resource type to set the error message for. If
                omitted, or if there is only one resource type involved, the
                error message is (also) set globally.

        Raises:
            KeyError: If the resource type is not found in the resources list.
        """
        if resource_type:
            resource = self.resources_dict.get(resource_type)
            if not resource:
                raise KeyError(
                    f"resource type '{resource_type}' not found in "
                    "service connector resources list"
                )
            resource.error = error
            resource.resource_ids = None
            if len(self.resources) == 1:
                # If there is only one resource type involved, set the global
                # error message as well.
                self.error = error
        else:
            self.error = error
            for resource in self.resources:
                resource.error = error
                resource.resource_ids = None

    def set_resource_ids(
        self, resource_type: str, resource_ids: List[str]
    ) -> None:
        """Set the resource IDs for a resource type.

        Args:
            resource_type: The resource type to set the resource IDs for.
            resource_ids: The resource IDs to set.

        Raises:
            KeyError: If the resource type is not found in the resources list.
        """
        resource = self.resources_dict.get(resource_type)
        if not resource:
            raise KeyError(
                f"resource type '{resource_type}' not found in "
                "service connector resources list"
            )
        resource.resource_ids = resource_ids
        resource.error = None

    @property
    def type(self) -> str:
        """Get the connector type.

        Returns:
            The connector type.
        """
        if isinstance(self.connector_type, str):
            return self.connector_type
        return self.connector_type.connector_type

    @property
    def emojified_connector_type(self) -> str:
        """Get the emojified connector type.

        Returns:
            The emojified connector type.
        """
        if not isinstance(self.connector_type, str):
            return self.connector_type.emojified_connector_type

        return self.connector_type

    def get_emojified_resource_types(
        self, resource_type: Optional[str] = None
    ) -> List[str]:
        """Get the emojified resource type.

        Args:
            resource_type: The resource type to get the emojified resource type
                for. If omitted, the emojified resource type for all resource
                types is returned.


        Returns:
            The list of emojified resource types.
        """
        if not isinstance(self.connector_type, str):
            if resource_type:
                return [
                    self.connector_type.resource_type_dict[
                        resource_type
                    ].emojified_resource_type
                ]
            return [
                self.connector_type.resource_type_dict[
                    resource_type
                ].emojified_resource_type
                for resource_type in self.resources_dict.keys()
            ]
        if resource_type:
            return [resource_type]
        return list(self.resources_dict.keys())

    def get_default_resource_id(self) -> Optional[str]:
        """Get the default resource ID, if included in the resource list.

        The default resource ID is a resource ID supplied by the connector
        implementation only for resource types that do not support multiple
        instances.

        Returns:
            The default resource ID, or None if no resource ID is set.
        """
        if len(self.resources) != 1:
            # multi-type connectors do not have a default resource ID
            return None

        if isinstance(self.connector_type, str):
            # can't determine default resource ID for unknown connector types
            return None

        resource_type_spec = self.connector_type.resource_type_dict[
            self.resources[0].resource_type
        ]
        if resource_type_spec.supports_instances:
            # resource types that support multiple instances do not have a
            # default resource ID
            return None

        resource_ids = self.resources[0].resource_ids

        if not resource_ids or len(resource_ids) != 1:
            return None

        return resource_ids[0]

    @classmethod
    def from_connector_model(
        cls,
        connector_model: "ServiceConnectorResponse",
        resource_type: Optional[str] = None,
    ) -> "ServiceConnectorResourcesModel":
        """Initialize a resource model from a connector model.

        Args:
            connector_model: The connector model.
            resource_type: The resource type to set on the resource model. If
                omitted, the resource type is set according to the connector
                model.

        Returns:
            A resource list model instance.
        """
        resources = cls(
            id=connector_model.id,
            name=connector_model.name,
            connector_type=connector_model.type,
        )

        resource_types = resource_type or connector_model.resource_types
        for resource_type in resource_types:
            resources.resources.append(
                ServiceConnectorTypedResourcesModel(
                    resource_type=resource_type,
                    resource_ids=[connector_model.resource_id]
                    if connector_model.resource_id
                    else None,
                )
            )

        return resources
