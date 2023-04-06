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
"""Base ZenML Service Connector class."""

import re
import uuid
from abc import abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Type, Union
from uuid import UUID

from pydantic import (
    BaseModel,
    SecretStr,
    ValidationError,
    root_validator,
    validator,
)

from zenml.client import Client
from zenml.enums import SecretScope
from zenml.models.secret_models import SecretBaseModel, SecretRequestModel


class AuthenticationConfig(BaseModel):
    """Base authentication configuration."""


class AuthenticationSecrets(BaseModel):
    """Base authentication secrets."""

    @root_validator(pre=True)
    def _validate_secret_fields(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Prevent subclasses from using fields that are not of type SecretStr.

        Args:
            values: The values to validate.

        Returns:
            The validated values.
        """
        for k, v in cls.__fields__.items():
            if not issubclass(v.type_, SecretStr):
                raise TypeError(
                    f"Field '{k}' of authentication secret class "
                    f"'{cls}' is not of type 'SecretStr'."
                )

        return values

    @property
    def secret_values(self) -> Dict[str, str]:
        """Get the values of the secrets as a dictionary.

        Returns:
            A dictionary of the secrets.
        """
        values: Dict[str, str] = {}
        for k, v in self.dict().items():
            if not isinstance(v, SecretStr):
                # This should never happen because the root validator
                # should have caught it, but we check it here just in case.
                raise TypeError(
                    f"Field '{k}' of authentication secret class "
                    f"'{self.__class__.__name__}' is not of type 'SecretStr'."
                )
            values[k] = v.get_secret_value()
        return values

    @classmethod
    def from_secret(cls, secret: SecretBaseModel) -> "AuthenticationSecrets":
        """Validate and load values from a ZenML secret into an instance.

        The default implementation checks that the secret has all the fields
        required by the authentication secrets class.

        Args:
            secret: The secret to validate and load.

        Returns:
            A new instance of the authentication secrets class with the values
            loaded from the ZenML secret.

        Raises:
            ValueError: If the secret is not valid.
        """
        secrets = secret.secret_values
        if "secret_reference" in secrets:
            # Silently ignore the secret reference field.
            del secrets["secret_reference"]

        try:
            return cls(**secrets)
        except ValidationError as e:
            raise ValueError(
                f"the values loaded from the ZenML secret are not valid: {e}"
            )

    def to_secret(
        self, name: str, user: UUID, workspace: UUID, scope: SecretScope
    ) -> SecretRequestModel:
        """Convert the authentication secrets to a ZenML secret.

        Args:
            name: The name of the secret.
            user: The ID of the user that owns the secret.
            workspace: The ID of the workspace that the secret belongs to.
            scope: The scope of the secret.

        Returns:
            A ZenML secret with the values from the authentication secrets.
        """
        secret = SecretRequestModel(
            name=name,
            user=user,
            workspace=workspace,
            scope=scope,
        )
        for k, v in self.secret_values.items():
            secret.add_secret(k, v)

        return secret


class ServiceConnectorConfig(BaseModel):
    """Base configuration for a connector instance.

    Attributes:
        auth_method: Identifies the authentication method that the connector
            instance uses to access the service. Must be one of the
            authentication methods declared in the connector's specification.
        resource_type: Identifies the type of resource that the connector
            instance can be used to gain access to. Only applicable if the
            connector's specification indicates that resource types are
            supported, in which case this field is mandatory. If the connector's
            specification doesn't allow arbitrary resource types, then this
            value must be one of those enumerated in the specification. The
            connector instance may support other types of resources in addition
            to the one specified here, e.g. if the connector implements aliasing
            or subordination of resource types.
        resource_id: Uniquely identifies a specific resource instance that the
            connector instance can be used to access. Only applicable if the
            connector's specification indicates that resource IDs are
            supported for the configured authentication method and resource
            type. If omitted in the connector configuration, the resource ID
            must be provided by the connector consumer.
        auth_config: Configuration for the authentication method.
        auth_secrets: Secrets for the authentication method.
        secret_reference: Reference to a ZenML secret that stores the secrets
            for the authentication method.
    """

    auth_method: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    auth_config: Optional[AuthenticationConfig] = None
    auth_secrets: Optional[AuthenticationSecrets] = None
    secret_reference: Optional[Union[str, UUID]] = None


class AuthenticationMethodSpecification(BaseModel):
    """Authentication method specification.

    Describes the schema for the configuration and secrets that need to be
    provided to configure an authentication method, as well as the types of
    resources that the authentication method can be used to access.

    Attributes:
        auth_method: Identifies the authentication method.
        description: A description of the authentication method.
        resource_types: A list of resource types that the authentication method
            can be used to access. Use this to override the resource types
            declared in the service connector specification. If not specified,
            the resource types configuration in the service connector
            specification applies.
        supports_resource_ids: Models whether the authentication method can be
            used to access multiple instances of the same resource. Use this to
            override the resource IDs configuration in the service connector.
            If not specified, the resource IDs configuration in the service
            connector specification applies.
        auth_config: The schema for the configuration that needs to be provided to
            configure the authentication method. Can be omitted if the
            authentication method does not require any configuration.
        auth_secrets: The schema for the secrets that need to be provided to
            configure the authentication method. Can be omitted if the
            authentication method does not require any secrets.
    """

    auth_method: str
    description: str = ""
    resource_types: Optional[List[str]] = None
    supports_resource_ids: Optional[bool] = None
    auth_config: Optional[Type[AuthenticationConfig]] = None
    auth_secrets: Optional[Type[AuthenticationSecrets]] = None


class ServiceConnectorSpecification(BaseModel):
    """Service connector specification.

    Describes the types of resources to which the service connector can be used
    to gain access and the authentication methods that are supported by the
    service connector.

    The connector type, resource types, resource IDs and authentication
    methods can all be used as search criteria to lookup and filter service
    connector instances that are compatible with the requirements of a consumer
    (e.g. a stack component).

    Attributes:
        connector_type: The type of service connector. It can be used to
            represent a generic resource (e.g. Docker, Kubernetes) or a group of
            different resources accessible through a common interface or
            point of access and authentication (e.g. a cloud provider or a
            platform).
        description: A description of the service connector.
        auth_methods: A list of specifications describing the authentication
            methods that are supported by the service connector, along with
            the configuration and secrets attributes that need to be configured
            for them. This list may contain multiple entries listing the same
            authentication method but with different configurations regarding
            resource types and resource IDs. The list is ordered by decreasing
            preference and specificity, with the preferred and more specific
            entries appearing first.
        supports_resource_types: Models whether the service connector
            implementation can be used to access multiple types of resources.
            If set to True, the resource type field must be used in the
            connector configuration or dynamically supplied by consumers to
            specify the type of resource that the connector instance can be used
            to gain access to. If set to False, the resource type is ignored.
        resource_types: A list of resource types that the service connector can
            be used to connect to. Only applicable if the connector supports
            resource types. If the arbitrary_resource_types flag is set
            to False, this is an exhaustive list of resource types, otherwise
            arbitrary resource types may be specified in addition to the ones
            listed here. This option may also be configured individually for
            each authentication method.
        arbitrary_resource_types: Indicates whether the service connector can
            be used to access resource types other than those listed in the
            resource types field. If set to False, the resource type field in
            the connector configuration may only be set to one of the resource
            types listed in the authentication method or connector
            specification.
        supports_resource_ids: Models whether the service connector
            implementation can be used to access multiple instances of the same
            resource. If set to True, the resource ID field must be used in
            the connector configuration or dynamically supplied by consumers to
            specify the ID of the resource instance that the connector instance
            can be used to gain access to. If set to False, the resource ID is
            ignored. This option may also be configured individually for each
            authentication method.
        client_types: For each resource type, this field may be used to
            list the types of client that the service connector can
            initialize and provide to consumers.
    """

    connector_type: str
    description: str = ""
    auth_methods: List[AuthenticationMethodSpecification]
    supports_resource_types: bool = False
    resource_types: Optional[List[str]] = None
    arbitrary_resource_types: bool = False
    supports_resource_ids: bool = False
    client_types: Optional[Dict[str, List[str]]] = None

    @classmethod
    def get_equivalent_resource_types(cls, resource_type: str) -> List[str]:
        """Get a list of resource types that are equivalent to the given one.

        Given a resource type identifier, this method returns a list of one or
        more resource types identifiers that can be used as a 1-to-1 equivalent
        substitute or are a subordinated specialization of the given resource
        type.

        This method is used to answer the questions: "What are all possible
        types of resources that this connector instance can be used to access?"
        and "Which connector instances can be used to access a resource of this
        type?".

        Override this method to implement mechanisms such as:

        * resource type aliases, where two or more identifiers can be used
        interchangeably to refer to the same resource type (e.g. "GCS" and
        "google_cloud_storage" or "S3" and "aws_s3" can be used interchangeably
        to refer to the same resource type).
        * resource type wildcards, where a resource type can be used to
        generally refer to a larger group of resource types that share a common
        interface or point of access and authentication (e.g. "AWS" can be used
        to represent all AWS resources, including S3, ECR, EKS, etc.).
        * resource type inheritance, where a resource type is a specialization
        of a more general resource type (e.g. "GKE" and "EKS" are both
        special flavors of "Kubernetes").

        Args:
            resource_type: The resource type identifier to match.

        Returns:
            A list of resource type identifiers that are equivalent to or
            subordinate to the given one.
        """
        return [resource_type]

    @classmethod
    def is_equivalent_resource_type(
        cls, resource_type: str, target_resource_types: List[str]
    ) -> bool:
        """Check whether a resource type is equivalent to any of the given ones.

        Args:
            resource_type: The resource type identifier to match.
            target_resource_types: A list of resource type identifiers to match
                against.

        Returns:
            True if the resource type is equivalent to any of the given ones,
            False otherwise.
        """
        return any(
            [
                resource_type in cls.get_equivalent_resource_types(rt)
                for rt in target_resource_types
            ]
        )

    @classmethod
    def is_equivalent_resource_id(
        cls, resource_id: str, target_resource_id: str
    ) -> bool:
        """Check whether a resource ID is equivalent to another one.

        Given two resource instance IDs, this method returns True if they are
        equivalent to each other, and False otherwise.

        This method is used to answer the questions: "Can this connector be
        used to access this resource instance with this ID ?" and "Which
        connector instances can be used to access a resource instance with of
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


class ServiceConnector(BaseModel):
    """Base service connector class.

    Service connectors are standalone components that can be used to link ZenML
    to external resources. They are responsible for validating and storing
    authentication configuration and sensitive credentials and for providing
    authentication services to other ZenML components. Service connectors are
    built on top of the (otherwise opaque) ZenML secrets and secrets store
    mechanisms and add secret auto-configuration, secret discovery and secret
    schema validation capabilities.

    The implementation independent service connector abstraction is made
    possible through the use of generic "resource types" and "resource IDs".
    These constitute the "contract" between connectors and the consumers of the
    authentication services that they provide. In a nutshell, a connector
    instance advertises what resource(s) it can be used to gain access to,
    whereas a consumer may run a query to search for compatible connectors by
    specifying the resource(s) that they need to access and then use a
    returned connector instance to connect to the resource(s).

    The resource types and authentication methods supported by a connector are
    declared in the connector's specification. The role of the specification
    is two-fold:

    - it declares a schema for the configuration that needs to be provided to
    configure the connector. This can be used to validate the configuration
    without having to instantiate the connector itself (e.g. in the CLI and
    dashboard), which also makes it possible to configure connectors and
    store their configuration without having to instantiate them.
    - it provides a way for ZenML to keep a registry of available connector
    implementations and configured connector instances. Users who want to
    connect ZenML to external resources via connectors can use this registry
    to discover what types of connectors are available and what types of
    resources they can be configured to access. Consumers can also use the
    registry to find connector instances that are compatible with the
    types of resources that they need to access.
    """

    config: ServiceConnectorConfig

    @classmethod
    @abstractmethod
    def get_specification(cls) -> ServiceConnectorSpecification:
        """Get the connector specification.

        Returns:
            The connector specification.
        """

    @abstractmethod
    def _connect_to_resource(
        self,
        config: ServiceConnectorConfig,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        client_type: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Authenticate and connect to a resource.

        This method uses the connector's configuration to initialize
        and return an implementation specific object representing an
        authenticated service client, connection or session that can be used
        to access the indicated resource type.

        Args:
            config: The connector configuration.
            resource_type: The type of resource to connect to. Omitted if the
                connector does not support multiple resource types.
            resource_id: The ID of the resource to connect to. Omitted if the
                configured authentication method does not require a resource ID.
            client_type: The type of client to instantiate, configure and
                return. Omitted if the connector does not support multiple
                client types.
            kwargs: Additional implementation specific keyword arguments to use
                to configure the client.

        Returns:
            An implementation specific object representing the authenticated
            service client, connection or session.

        Raises:
            AuthorizationException: If authentication failed.
            NotImplementedError: If the connector instance does not support
                connecting to the indicated resource type or client type.
        """

    @abstractmethod
    def _configure_local_client(
        self,
        config: ServiceConnectorConfig,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        client_type: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Configure a local client for a service using the specified authentication method.

        This method uses the connector's configuration to configure a local
        client or SDK installed on the localhost for the indicated resource.

        Args:
            config: The connector configuration.
            resource_type: The type of resource to connect to. Omitted if the
                connector does not support multiple resource types.
            resource_id: The ID of the resource to connect to. Omitted if the
                configured authentication method does not require a resource ID.
            client_type: The type of client to configure. If not specified,
                the connector implementation must decide which client to
                configure or raise an exception. For connectors and resources
                that do not support multiple client types, this parameter may be
                omitted.
            kwargs: Additional implementation specific keyword arguments to use
                to configure the client.

        Raises:
            AuthorizationException: If authentication failed.
            NotImplementedError: If the connector instance does not support
                local configuration for the indicated resource type or client
                type.
        """

    @classmethod
    @abstractmethod
    def _auto_configure(
        cls,
        auth_method: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        client_type: Optional[str] = None,
        **kwargs: Any,
    ) -> ServiceConnectorConfig:
        """Auto-configure the connector.

        Auto-configure the connector by looking for authentication
        configuration in the environment (e.g. environment variables or
        configuration files) and storing it in the connector configuration.

        Args:
            auth_method: The particular authentication method to use. If not
                specified, the connector implementation must decide which
                authentication method to use or raise an exception.
            resource_type: The type of resource to configure. Omitted if the
                connector does not support resource types.
            resource_id: The ID of the resource to configure. The
                implementation may choose to either require or ignore this
                parameter if it does not support or detect an authentication
                methods that uses a resource ID.
            client_type: The type of client to configure. Omitted if the
                connector does not support multiple client types.
            kwargs: Additional implementation specific keyword arguments to use.

        Returns:
            The connector configuration populated with auto-configured
            authentication credentials.

        Raises:
            NotImplementedError: If the connector does not support
                auto-configuration.
        """

    @classmethod
    def validate_auth_method_config(
        cls,
        auth_method_spec: AuthenticationMethodSpecification,
        auth_method: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        allow_partial_config: bool = True,
        restrict_resource_type: Optional[str] = None,
        restrict_resource_id: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Validate the configuration for an authentication method against a method specification.

        Args:
            auth_method_spec: The specification for the authentication method.
            auth_method: The name of the authentication method.
            resource_type: The type of resource being configured. Only valid
                (and mandatory) for connectors that support resource types.
            resource_id: The ID of the resource being configured. Only valid
                for authentication methods that support resource IDs.
            allow_partial_config: Whether to allow the authentication method
                configuration to be incomplete (i.e. the resource ID to be
                omitted when the authentication method requires it).
            restrict_resource_type: An optional resource type used to further
                restrict the list of valid resource types allowed for the
                authentication method. If provided, only resource types that
                are equivalent to the specified resource type will be allowed.
                Only valid for connectors that support resource types.
            restrict_resource_id: An optional resource ID used to further
                restrict the list of valid resource IDs allowed for the
                authentication method. If provided, only resource IDs that are
                equivalent to the specified resource ID will be allowed. Only
                valid for authentication methods that support resource IDs.

        Returns:
            A tuple containing a boolean indicating whether the configuration
            is valid and a string containing an error message if the
            configuration is invalid.
        """
        spec = cls.get_specification()

        # Verify the authentication method
        if auth_method_spec.auth_method != auth_method:
            # The authentication method does not match
            return False, (
                f"authentication method '{auth_method}' does not match "
                f"expected value '{auth_method_spec.auth_method}'."
            )

        if restrict_resource_type:
            auth_method_resource_types = [restrict_resource_type]
        else:
            auth_method_resource_types = auth_method_spec.resource_types
            if auth_method_resource_types is None:
                auth_method_resource_types = spec.resource_types
            auth_method_resource_types = auth_method_resource_types or []

        uses_resource_ids = auth_method_spec.supports_resource_ids
        if uses_resource_ids is None:
            uses_resource_ids = spec.supports_resource_ids

        # Verify the resource type
        resource_type_msg = ""
        if resource_type:

            # Verify that the connector supports resource types
            if spec.supports_resource_types is False:
                return False, (
                    f"connector '{spec.connector_type}' does not "
                    "support resource types, but a resource type was "
                    f"provided: '{resource_type}'."
                )

            # Verify that the resource type configured for the authentication
            # method is one of those supported by the authentication method
            if (
                not spec.arbitrary_resource_types
                and not spec.is_equivalent_resource_type(
                    resource_type, auth_method_resource_types
                )
            ):
                # The resource types do not match
                return False, (
                    f"the '{auth_method}' authentication method is not "
                    f"supported for resource type '{resource_type}'."
                    "This authentication method only supports the following "
                    "resource types and their equivalents: "
                    f"{auth_method_resource_types}."
                )

            resource_type_msg = f" for the '{resource_type}' resource type"

        elif spec.supports_resource_types:

            # The resource type is required
            return False, (
                f"the '{auth_method}' authentication method requires a "
                "resource type, but none was provided."
            )

        if resource_id:

            if not uses_resource_ids:
                # The auth method does not support resource IDs
                return False, (
                    f"the '{auth_method}' authentication method does not "
                    f"support resource IDs{resource_type_msg}, but a resource "
                    f"ID was provided: '{resource_id}'."
                )

            if restrict_resource_id and not spec.is_equivalent_resource_id(
                resource_id, restrict_resource_id
            ):
                # The resource ID does not match
                return False, (
                    f"the '{auth_method}' authentication method is configured "
                    f"for resource with ID '{restrict_resource_id}', but a "
                    f"different resource ID was provided: '{resource_id}'."
                )

        elif not allow_partial_config and uses_resource_ids:

            if not restrict_resource_id:
                # The resource ID is required and not restricted to a value
                # that can be used as a default
                return False, (
                    f"the '{auth_method}' authentication method requires a "
                    f"resource ID to be specified{resource_type_msg}, but none "
                    "was provided."
                )

        return True, None

    @classmethod
    def find_auth_method_specification(
        cls,
        auth_method: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> AuthenticationMethodSpecification:
        """Find the specification for a configurable authentication method.

        Args:
            auth_method: The name of the authentication method.
            resource_type: The type of resource being configured. Only valid
                for connectors that support resource types.
            resource_id: The ID of the resource being configured. Only valid
                for authentication methods that support resource IDs.

        Returns:
            The authentication method specification.

        Raises:
            KeyError: If the authentication method is not supported by the
                connector for the specified resource type and ID.
            ValueError: If the connector does not support resource types or
                resource IDs, but one of them was provided.
        """
        spec = cls.get_specification()

        # Verify the resource type
        if resource_type:

            # Verify that the connector supports resource types
            if spec.supports_resource_types is False:
                raise ValueError(
                    f"connector '{spec.connector_type}' does not "
                    "support resource types, but a resource type was "
                    f"provided: '{resource_type}'."
                )

        auth_method_found = False
        auth_method_errors: List[str] = []

        # Find an auth method specification that matches the configured
        # authentication method, resource type and resource ID
        for auth_method_spec in spec.auth_methods:

            if auth_method_spec.auth_method != auth_method:
                # The authentication method does not match
                continue

            auth_method_found = True

            valid, error = cls.validate_auth_method_config(
                auth_method_spec,
                auth_method,
                resource_type=resource_type,
                resource_id=resource_id,
                allow_partial_config=True,
            )

            if not valid:
                if error:
                    auth_method_errors.append(error)
                continue

            return auth_method_spec

        if not auth_method_found:
            raise KeyError(
                f"the '{spec.connector_type}' connector does not support the "
                f"'{auth_method}' authentication method."
            )

        error = "\n".join(auth_method_errors)
        raise KeyError(
            f"the configuration didn't match any of the valid ways in which "
            f"the '{auth_method}' authentication method can be used:\n{error}"
        )

    @classmethod
    def validate_connector_config(
        cls,
        config: ServiceConnectorConfig,
    ) -> None:
        """Validate the connector configuration against the connector specification.

        Validate that the connector configuration conforms to the connector
        specification. This includes validating that the authentication method
        is supported by the connector and that the authentication configuration
        abides by the schema and rules defined in the specification.

        Args:
            config: The connector configuration to validate.

        Raises:
            ValueError: If the connector configuration is not valid.
        """
        method_spec = cls.find_auth_method_specification(
            config.auth_method,
            config.resource_type,
            config.resource_id,
        )

        # Verify the authentication configuration
        if method_spec.auth_config:
            if not config.auth_config:
                raise ValueError(
                    f"authentication method '{config.auth_method}' requires a "
                    f"configuration."
                )
            if not isinstance(config.auth_config, method_spec.auth_config):
                raise ValueError(
                    f"authentication method '{config.auth_method}' requires a "
                    f"configuration of type '{method_spec.auth_config.__name__}' "
                    "to be supplied, but a different type was provided."
                )
        elif config:
            raise ValueError(
                f"authentication method '{config.auth_method}' does not "
                "require a configuration, but one was provided."
            )

        # Verify the authentication secrets
        if method_spec.auth_secrets:
            if not config.auth_secrets and not config.secret_reference:
                raise ValueError(
                    f"authentication method '{config.auth_method}' requires "
                    f"secrets to be configured either explicitly or by using "
                    "a reference to an existing ZenML secret."
                )
            if config.auth_secrets:
                if not isinstance(
                    config.auth_secrets, method_spec.auth_secrets
                ):
                    raise ValueError(
                        f"authentication method '{config.auth_method}' expects "
                        f"secrets of type '{method_spec.auth_secrets.__name__}' "
                        "to be configured, but a different type was provided."
                    )

            elif config.secret_reference:
                # TODO: using the Client in the context of the server
                # doesn't work. We need to find a way to access the ZenML
                # secrets store without using the client.
                client = Client()
                try:
                    if isinstance(config.secret_reference, str):
                        secret = client.get_secret_by_name_and_scope(
                            name=config.secret_reference,
                        )
                    elif isinstance(config.secret_reference, uuid.UUID):
                        secret = client.get_secret(
                            name_id_or_prefix=config.secret_reference,
                        )
                    else:
                        raise ValueError(
                            f"the secret reference '{config.secret_reference}' "
                            "is not valid. It must be either a string or a "
                            "UUID."
                        )
                except KeyError:
                    raise ValueError(
                        f"the secret '{config.secret_reference}' could not be "
                        "resolved."
                    )

                try:
                    config.auth_secrets = method_spec.auth_secrets.from_secret(
                        secret
                    )
                except ValueError as e:
                    raise ValueError(
                        "the contents of the referenced secret "
                        f"'{config.secret_reference}' are not valid for "
                        f"authentication method '{config.auth_method}': {e}"
                    )

                config.secret_reference = secret.id

        elif config.auth_secrets or config.secret_reference:
            raise ValueError(
                f"authentication method '{config.auth_method}' does not "
                "require secrets to be configured, but some were provided."
            )

    def validate_runtime_args(
        self,
        auth_method: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        client_type: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """Validate the runtime arguments against the connector configuration.

        Validate that the runtime arguments are compatible with the connector
        configuration and its specification. This includes validating that the
        authentication method, resource type and resource ID are compatible
        with the connector configuration and its capabilities.

        Args:
            auth_method: The authentication method to use.
            resource_type: The type of resource to connect to.
            resource_id: The ID of the resource to connect to.
            client_type: The type of client to connect to the resource with.

        Returns:
            A tuple containing the validated authentication method, resource
            type, resource ID and client type.

        Raises:
            ValueError: If the runtime arguments are not valid.
        """
        if auth_method and auth_method != self.config.auth_method:
            raise ValueError(
                f"the authentication method '{auth_method}' is not compatible "
                "with the one configured for the connector: "
                f"'{self.config.auth_method}'"
            )

        auth_method = auth_method or self.config.auth_method

        spec = self.get_specification()

        # Get the authentication method specification originally used to
        # validate the connector configuration.
        method_spec = self.find_auth_method_specification(
            self.config.auth_method,
            self.config.resource_type,
            self.config.resource_id,
        )

        # Validate the the resource type and resource ID supplied by the
        # consumer connector config against the connector configuration.
        # This time we require that the configuration be complete.
        valid, error = self.validate_auth_method_config(
            auth_method_spec=method_spec,
            auth_method=auth_method,
            resource_type=resource_type,
            resource_id=resource_id,
            allow_partial_config=False,
            restrict_resource_type=self.config.resource_type,
            restrict_resource_id=self.config.resource_id,
        )

        if not valid:
            raise ValueError(
                f"the connector configuration is not valid: {error}"
            )

        # Ignore the supplied resource type if the connector does not support
        # resource types.
        if not spec.supports_resource_types:
            resource_type = None
        else:
            resource_type = resource_type or self.config.resource_type

        supports_resource_ids = (
            method_spec.supports_resource_ids
            if method_spec.supports_resource_ids is not None
            else spec.supports_resource_ids
        )

        # Ignore the supplied resource ID if the authentication method does not
        # support resource IDs.
        if not supports_resource_ids:
            resource_id = None
        else:
            resource_id = resource_id or self.config.resource_id

        return (
            auth_method,
            resource_type,
            resource_id,
            client_type,
        )

    def save(self) -> None:
        """Save the connector configuration.

        Persists the connector configuration in the ZenML database and
        Secrets Store.
        """
        pass  # TBD

    def load(self) -> None:
        """Load the connector configuration.

        Loads the connector configuration from the ZenML database and
        Secrets Store.
        """
        pass

    def connect(
        self,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        client_type: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Authenticate and connect to a resource.

        Initialize and return an implementation specific object representing an
        authenticated service client, connection or session that can be used
        to access the indicated resource type.

        Args:
            resource_type: The type of resource to connect to. If the connector
                instance configured with a resource type and the supplied value
                is not the same or equivalent, or if the connector does not
                support resource types, an exception is raised.
            resource_id: The ID of a particular resource instance to connect
                to. Use this with connector instances configured to allow
                a resource ID to be dynamically supplied at runtime.
                If the connector instance is already configured with a resource
                ID and this parameter has a different value, an exception will
                be raised. If the connector instance does not support resource
                instances, this parameter is ignored.
            client_type: The particular type of client to instantiate, configure
                and return.
            kwargs: Additional implementation specific keyword arguments to use
                to configure the client.

        Returns:
            An implementation specific object representing the authenticated
            service client, connection or session.
        """
        (
            auth_method,
            resource_type,
            resource_id,
            client_type,
        ) = self.validate_runtime_args(
            resource_type=resource_type,
            resource_id=resource_id,
            client_type=client_type,
        )

        return self._connect_to_resource(
            config=self.config,
            resource_type=resource_type,
            resource_id=resource_id,
            client_type=client_type,
            **kwargs,
        )

    def auto_configure(
        self,
        auth_method: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        client_type: Optional[str] = None,
        **kwargs: Any,
    ) -> ServiceConnectorConfig:
        """Auto-configure the connector.

        Auto-configure the connector by looking for authentication
        configuration in the environment (e.g. environment variables or
        configuration files) and storing it in the connector configuration.

        Args:
            auth_method: The particular authentication method to use. If
                omitted and if the connector implementation cannot decide which
                authentication method to use, it may raise an exception.
            resource_type: The type of resource to configure. If the connector
                does not support resource types, an exception is raised.
            resource_id: The ID of the resource to configure. The connector
                implementation may choose to either require or ignore this
                parameter if it does not support or detect an authentication
                methods that uses a resource ID.
            client_type: The particular type of client to auto-configure.
            kwargs: Additional implementation specific keyword arguments to use.

        Returns:
            The connector configuration populated with auto-configured
            parameters and authentication credentials.

        Raises:
            ValueError: If the connector does not support resource types and
                the resource type parameter is supplied.
        """
        spec = self.get_specification()

        if resource_type and not spec.supports_resource_types:
            raise ValueError("the connector does not support resource types")

        return self._auto_configure(
            auth_method=auth_method,
            resource_type=resource_type,
            resource_id=resource_id,
            client_type=client_type,
            **kwargs,
        )
