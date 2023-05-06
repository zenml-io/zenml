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
from datetime import datetime, timezone
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    SecretStr,
    validator,
)

from zenml.logger import get_logger
from zenml.models.base_models import (
    ShareableRequestModel,
    ShareableResponseModel,
    update_model,
)
from zenml.models.constants import STR_FIELD_MAX_LENGTH
from zenml.models.filter_models import ShareableWorkspaceScopedFilterModel

if TYPE_CHECKING:
    from zenml.service_connectors.service_connector import ServiceConnector

logger = get_logger(__name__)

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

        if self.default_expiration_seconds is not None:
            if expiration_seconds is None:
                expiration_seconds = self.default_expiration_seconds

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
        "within apidocs.zenml.io.",
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
        auth_method_map = self.auth_method_map
        if auth_method in auth_method_map:
            # A match was found for the authentication method
            auth_method_spec = auth_method_map[auth_method]
        else:
            # No match was found for the authentication method
            raise KeyError(
                f"connector type '{self.connector_type}' does not support the "
                f"'{auth_method}' authentication method. Supported "
                f"authentication methods are: {list(auth_method_map.keys())}."
            )

        if resource_type is None:
            # No resource type was specified, so no resource type
            # specification can be returned.
            return auth_method_spec, None

        # Verify the resource type
        resource_type_map = self.resource_type_map
        if resource_type in resource_type_map:
            resource_type_spec = resource_type_map[resource_type]
        else:
            raise KeyError(
                f"connector type '{self.connector_type}' does not support "
                f"resource type '{resource_type}'. Supported resource types "
                f"are: {list(resource_type_map.keys())}."
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


class ServiceConnectorBaseModel(BaseModel):
    """Base model for service connectors."""

    name: str = Field(
        title="The service connector name.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    connector_type: Union[str, "ServiceConnectorTypeModel"] = Field(
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
    resource_types: List[str] = Field(
        default_factory=list,
        title="The type(s) of resource that the connector instance can be used "
        "to gain access to.",
    )
    resource_id: Optional[str] = Field(
        default=None,
        title="Uniquely identifies a specific resource instance that the "
        "connector instance can be used to access. If omitted, the connector "
        "instance can be used to access any and all resource instances that "
        "the authentication method and resource type(s) allow.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    supports_instances: bool = Field(
        default=False,
        title="Indicates whether the connector instance can be used to access "
        "multiple instances of the configured resource type.",
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        title="Time when the authentication credentials configured for the "
        "connector expire. If omitted, the credentials do not expire.",
    )
    expiration_seconds: Optional[int] = Field(
        default=None,
        title="The duration, in seconds, that the temporary credentials "
        "generated by this connector should remain valid. Only applicable for "
        "connectors and authentication methods that involve generating "
        "temporary credentials from the ones configured in the connector.",
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

    @property
    def emojified_resource_types(self) -> List[str]:
        """Get the emojified connector type.

        Returns:
            The emojified connector type.
        """
        if not isinstance(self.connector_type, str):
            return [
                self.connector_type.resource_type_map[
                    resource_type
                ].emojified_resource_type
                for resource_type in self.resource_types
            ]

        return self.resource_types

    @property
    def is_multi_type(self) -> bool:
        """Checks if the connector is multi-type.

        A multi-type connector can be used to access multiple types of
        resources.

        Returns:
            True if the connector is multi-type, False otherwise.
        """
        return len(self.resource_types) > 1

    @property
    def is_multi_instance(self) -> bool:
        """Checks if the connector is multi-instance.

        A multi-instance connector is configured to access multiple instances
        of the configured resource type.

        Returns:
            True if the connector is multi-instance, False otherwise.
        """
        return (
            not self.is_multi_type
            and self.supports_instances
            and not self.resource_id
        )

    @property
    def is_single_instance(self) -> bool:
        """Checks if the connector is single-instance.

        A single-instance connector is configured to access only a single
        instance of the configured resource type or does not support multiple
        resource instances.

        Returns:
            True if the connector is single-instance, False otherwise.
        """
        return not self.is_multi_type and not self.is_multi_instance

    @property
    def full_configuration(self) -> Dict[str, str]:
        """Get the full connector configuration, including secrets.

        Returns:
            The full connector configuration, including secrets.
        """
        config = self.configuration.copy()
        config.update(
            {k: v.get_secret_value() for k, v in self.secrets.items() if v}
        )
        return config

    def has_expired(self) -> bool:
        """Check if the connector credentials have expired.

        Verify that the authentication credentials associated with the connector
        have not expired by checking the expiration time against the current
        time.

        Returns:
            True if the connector has expired, False otherwise.
        """
        if not self.expires_at:
            return False

        return self.expires_at < datetime.now(timezone.utc)

    def validate_and_configure_resources(
        self,
        connector_type: "ServiceConnectorTypeModel",
        resource_types: Optional[Union[str, List[str]]] = None,
        resource_id: Optional[str] = None,
        configuration: Optional[Dict[str, Any]] = None,
        secrets: Optional[Dict[str, Optional[SecretStr]]] = None,
    ) -> None:
        """Validate and configure the resources that the connector can be used to access.

        Args:
            connector_type: The connector type specification used to validate
                the connector configuration.
            resource_types: The type(s) of resource that the connector instance
                can be used to access. If omitted, a multi-type connector is
                configured.
            resource_id: Uniquely identifies a specific resource instance that
                the connector instance can be used to access.
            configuration: The connector configuration.
            secrets: The connector secrets.

        Raises:
            ValueError: If the connector configuration is not valid.
        """
        if resource_types is None:
            resource_type = None
        elif isinstance(resource_types, str):
            resource_type = resource_types
        elif len(resource_types) == 1:
            resource_type = resource_types[0]
        else:
            # Multiple or no resource types specified
            resource_type = None

        try:
            # Validate the connector configuration and retrieve the resource
            # specification
            (
                auth_method_spec,
                resource_spec,
            ) = connector_type.find_resource_specifications(
                self.auth_method,
                resource_type,
            )
        except (KeyError, ValueError) as e:
            raise ValueError(
                f"connector configuration is not valid: {e}"
            ) from e

        if resource_type and resource_spec:
            self.resource_types = [resource_spec.resource_type]
            self.resource_id = resource_id
            self.supports_instances = resource_spec.supports_instances
        else:
            # A multi-type connector is associated with all resource types
            # that it supports, does not have a resource ID configured
            # and it's unclear if it supports multiple instances or not
            self.resource_types = list(connector_type.resource_type_map.keys())
            self.supports_instances = False

        if configuration is None and secrets is None:
            # No configuration or secrets provided
            return

        self.configuration = {}
        self.secrets = {}

        # Validate and configure the connector configuration and secrets
        configuration = configuration or {}
        secrets = secrets or {}
        supported_attrs = []
        for attr_name, attr_schema in auth_method_spec.config_schema.get(
            "properties", {}
        ).items():
            supported_attrs.append(attr_name)
            required = attr_name in auth_method_spec.config_schema.get(
                "required", []
            )
            secret = attr_schema.get("format", "") == "password"
            value = configuration.get(attr_name, secrets.get(attr_name))
            if required:
                if value is None:
                    raise ValueError(
                        "connector configuration is not valid: missing "
                        f"required attribute '{attr_name}'"
                    )
            elif value is None:
                continue

            # Split the configuration into secrets and non-secrets
            if secret:
                if isinstance(value, SecretStr):
                    self.secrets[attr_name] = value
                else:
                    self.secrets[attr_name] = SecretStr(value)
            else:
                self.configuration[attr_name] = value

        # Warn about attributes that are not part of the configuration schema
        for attr_name in set(list(configuration.keys())) - set(
            supported_attrs
        ):
            logger.warning(
                f"Ignoring unknown attribute in connector '{self.name}' "
                f"configuration {attr_name}. Supported attributes are: "
                f"{supported_attrs}",
            )
        # Warn about secrets that are not part of the configuration schema
        for attr_name in set(secrets.keys()) - self.secrets.keys():
            logger.warning(
                f"Ignoring unknown attribute in connector '{self.name}' "
                f"configuration {attr_name}. Supported attributes are: "
                f"{supported_attrs}",
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
    resource_type: str

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
                "stack component requirements",
            )
        if self.resource_type not in connector.resource_types:
            return False, (
                f"connector does not provide the '{self.resource_type}' "
                "resource type specified in the stack component requirements. "
                "Only the following resource types are supported: "
                f"{', '.join(connector.resource_types)}"
            )

        return True, ""


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

    resource_type: Optional[str] = Field(
        default=None,
        title="The type of resource that the service connector instance can "
        "be used to access. Omitted for multi-type service connectors.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    resource_ids: Optional[List[str]] = Field(
        default=None,
        title="The resource IDs of all resource instances that the service "
        "connector instance can be used to access. Omitted (set to None) for "
        "multi-type service connectors. Also omitted if an error occurred "
        "while listing the resource instances or if no resources are listed "
        "due to authorization issues or lack of permissions (in both cases the "
        "'error' field is set to an error message). For resource types that "
        "do not support multiple instances, a single resource ID is listed.",
    )

    error: Optional[str] = Field(
        default=None,
        title="An error message describing why the service connector instance "
        "could not list the resources that it is configured to access.",
    )

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

    @property
    def emojified_resource_types(self) -> Optional[List[str]]:
        """Get the emojified resource types.

        Returns:
            The emojified resource types.
        """
        if not isinstance(self.connector_type, str):
            if self.resource_type:
                return [
                    self.connector_type.resource_type_map[
                        self.resource_type
                    ].emojified_resource_type
                ]
            else:
                return [
                    resource_type_spec.emojified_resource_type
                    for resource_type_spec in self.connector_type.resource_type_map.values()
                ]

        return [self.resource_type] if self.resource_type else None

    @property
    def supports_instances(self) -> bool:
        """Check if the configured resource type supports multiple instances.

        Returns:
            True if the resource type is configured and supports multiple
            instances, False otherwise.
        """
        if not self.resource_type:
            return False

        if isinstance(self.connector_type, str):
            return False

        resource_type_spec = self.connector_type.resource_type_map[
            self.resource_type
        ]
        return resource_type_spec.supports_instances

    def get_default_resource_id(self) -> Optional[str]:
        """Get the default resource ID, if included in the resource list.

        The default resource ID is a resource ID supplied by the connector
        implementation only for resource types that do not support multiple
        instances.

        Returns:
            The default resource ID, or None if no resource ID is set.
        """
        if not self.resource_ids or len(self.resource_ids) != 1:
            return None

        if self.supports_instances:
            return None

        return self.resource_ids[0]

    @classmethod
    def from_connector_model(
        cls,
        connector_model: "ServiceConnectorResponseModel",
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

        if resource_type:
            resources.resource_type = resource_type
        else:
            # Multi-type resources do not have a resource type set
            resources.resource_type = (
                connector_model.resource_types[0]
                if len(connector_model.resource_types) == 1
                else None
            )

        # Multi-type and multi-instance resources do not have resource IDs set
        resources.resource_ids = (
            [connector_model.resource_id]
            if connector_model.resource_id and resources.resource_type
            else []
        )

        return resources


# -------- #
# RESPONSE #
# -------- #


class ServiceConnectorResponseModel(
    ServiceConnectorBaseModel, ShareableResponseModel
):
    """Response model for service connectors."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = [
        "connector_type",
        "auth_method",
        "resource_types",
    ]

    secret_id: Optional[UUID] = Field(
        default=None,
        title="The ID of the secret that contains the service connector "
        "secret configuration values.",
    )

    def get_analytics_metadata(self) -> Dict[str, Any]:
        """Format the resource types in the analytics metadata.

        Returns:
            Dict of analytics metadata.
        """
        metadata = super().get_analytics_metadata()
        if len(self.resource_types) == 1:
            metadata["resource_types"] = self.resource_types[0]
        else:
            metadata["resource_types"] = ", ".join(self.resource_types)
        if not isinstance(self.connector_type, str):
            metadata["connector_type"] = self.connector_type.connector_type
        return metadata


# ------ #
# FILTER #
# ------ #


class ServiceConnectorFilterModel(ShareableWorkspaceScopedFilterModel):
    """Model to enable advanced filtering of service connectors."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *ShareableWorkspaceScopedFilterModel.FILTER_EXCLUDE_FIELDS,
        "scope_type",
        "resource_type",
        "labels",
    ]
    CLI_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *ShareableWorkspaceScopedFilterModel.CLI_EXCLUDE_FIELDS,
        "scope_type",
        "labels",
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
    connector_type: Optional[str] = Field(
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
        "connector_type",
        "auth_method",
        "resource_types",
    ]

    def get_analytics_metadata(self) -> Dict[str, Any]:
        """Format the resource types in the analytics metadata.

        Returns:
            Dict of analytics metadata.
        """
        metadata = super().get_analytics_metadata()
        if len(self.resource_types) == 1:
            metadata["resource_types"] = self.resource_types[0]
        else:
            metadata["resource_types"] = ", ".join(self.resource_types)
        if not isinstance(self.connector_type, str):
            metadata["connector_type"] = self.connector_type.connector_type
        return metadata


# ------ #
# UPDATE #
# ------ #


@update_model
class ServiceConnectorUpdateModel(ServiceConnectorRequestModel):
    """Model used for service connector updates."""
