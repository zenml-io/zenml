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

from abc import abstractmethod
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import (
    BaseModel,
    SecretStr,
    ValidationError,
)

from zenml.client import Client
from zenml.models.service_connector_models import (
    ServiceConnectorBaseModel,
    ServiceConnectorRequestModel,
    ServiceConnectorResponseModel,
    ServiceConnectorSpecificationModel,
)


class AuthenticationConfig(BaseModel):
    """Base authentication configuration."""

    @property
    def secret_values(self) -> Dict[str, SecretStr]:
        """Get the secret values as a dictionary.

        Returns:
            A dictionary of all secret values in the configuration.
        """
        return {
            k: v for k, v in self.dict().items() if isinstance(v, SecretStr)
        }

    @property
    def non_secret_values(self) -> Dict[str, str]:
        """Get the non-secret values as a dictionary.

        Returns:
            A dictionary of all non-secret values in the configuration.
        """
        return {
            k: v
            for k, v in self.dict().items()
            if not isinstance(v, SecretStr)
        }


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
    matching connector instance to connect to said resource(s).

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

    id: Optional[UUID] = None
    name: Optional[str] = None
    auth_method: str
    resource_type: str
    resource_id: Optional[str] = None
    config: AuthenticationConfig

    @classmethod
    @abstractmethod
    def get_specification(cls) -> ServiceConnectorSpecificationModel:
        """Get the connector specification.

        Returns:
            The connector specification.
        """

    @abstractmethod
    def _connect_to_resource(
        self,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Authenticate and connect to a resource.

        This method uses the connector's configuration to initialize
        and return an implementation specific object representing an
        authenticated service client, connection or session that can be used
        to access the indicated resource type.

        Args:
            resource_type: The type of resource to connect to. Can be different
                than the resource type that the connector is configured to
                access if alternative resource types or arbitrary
                resource types are allowed by the connector configuration.
            resource_id: The ID of the resource to connect to. Omitted if the
                configured resource type does not allow multiple instances.
                Can be different than the resource ID that the connector is
                configured to access if resource ID aliases or wildcards
                are supported.
            kwargs: Additional implementation specific keyword arguments to use
                to configure the client.

        Returns:
            An implementation specific object representing the authenticated
            service client, connection or session.

        Raises:
            AuthorizationException: If authentication failed.
            NotImplementedError: If the connector instance does not support
                connecting to the indicated resource type.
        """

    @abstractmethod
    def _configure_local_client(
        self,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Configure a local client to authenticate and connect to a resource.

        This method uses the connector's configuration to configure a local
        client or SDK installed on the localhost for the indicated resource.

        Args:
            resource_type: The type of resource to connect to. Can be different
                than the resource type that the connector is configured to
                access if alternative resource types or arbitrary
                resource types are allowed by the connector configuration.
            resource_id: The ID of the resource to connect to. Omitted if the
                configured resource type does not allow multiple instances.
                Can be different than the resource ID that the connector is
                configured to access if resource ID aliases or wildcards
                are supported.
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
        **kwargs: Any,
    ) -> "ServiceConnector":
        """Auto-configure a connector instance.

        Instantiate a connector with a configuration extracted from the
        authentication configuration available in the environment (e.g.
        environment variables or local client/SDK configuration files).

        Args:
            auth_method: The particular authentication method to use. If not
                specified, the connector implementation must decide which
                authentication method to use or raise an exception.
            resource_type: The type of resource to configure. The implementation
                may choose to either require or ignore this parameter if it
                does not support or is able to detect a resource type and the
                connector specification does not allow arbitrary resource types.
            resource_id: The ID of the resource to configure. The
                implementation may choose to either require or ignore this
                parameter if it does not support or detect an resource type that
                supports multiple instances.
            kwargs: Additional implementation specific keyword arguments to use.

        Returns:
            A connector instance configured with authentication credentials
            automatically extracted from the environment.

        Raises:
            NotImplementedError: If the connector does not support
                auto-configuration.
        """

    @classmethod
    def from_model(
        cls, model: "ServiceConnectorBaseModel"
    ) -> "ServiceConnector":
        """Creates a service connector instance from a service connector model.

        Args:
            model: The service connector model.

        Returns:
            The created service connector instance.
        """
        # Validate the connector configuration model
        spec = cls.get_specification()
        try:
            method_spec, _ = spec.find_resource_specifications(
                model.auth_method,
                model.resource_type,
                model.resource_id,
            )
        except (KeyError, ValueError) as e:
            raise ValueError(
                f"connector configuration is not valid: {e}"
            ) from e

        # Unpack the authentication configuration
        config = model.configuration.copy()
        if (
            isinstance(model, ServiceConnectorResponseModel)
            and model.secret_id
        ):
            try:
                secret = Client().get_secret(model.secret_id)
            except KeyError as e:
                raise ValueError(
                    f"could not fetch secret with ID '{model.secret_id}' "
                    f"referenced in the connector configuration: {e}"
                ) from e
            config.update(secret.secret_values)

        if model.secrets:
            config.update(
                {
                    k: v.get_secret_value()
                    for k, v in model.secrets.items()
                    if v
                }
            )

        # Validate the authentication configuration
        try:
            auth_config = method_spec.config_class(**config)
        except ValidationError as e:
            raise ValueError(
                f"connector configuration is not valid: {e}"
            ) from e

        assert isinstance(auth_config, AuthenticationConfig)

        connector = cls(
            auth_method=model.auth_method,
            resource_type=model.resource_type,
            resource_id=model.resource_id,
            config=auth_config,
        )
        if isinstance(model, ServiceConnectorResponseModel):
            connector.id = model.id
            connector.name = model.name

        return connector

    def to_model(
        self,
        name: str,
        user: UUID,
        workspace: UUID,
        is_shared: bool = False,
        description: str = "",
    ) -> "ServiceConnectorRequestModel":
        """Convert the connector instance to a service connector model.

        Args:
            name: The name of the connector.
            user: The ID of the user that created the connector.
            workspace: The ID of the workspace that the connector belongs to.
            is_shared: Whether the connector is shared with other users.
            description: The description of the connector.

        Returns:
            The service connector model corresponding to the connector
            instance.

        Raises:
            ValueError: If the connector configuration is not valid.
        """
        spec = self.get_specification()
        try:
            # Get the resource specification corresponding to the
            # connector configuration.
            _, resource_spec = spec.find_resource_specifications(
                self.auth_method,
                self.resource_type,
                self.resource_id,
            )
        except (KeyError, ValueError) as e:
            raise ValueError(
                f"connector configuration is not valid: {e}"
            ) from e

        return ServiceConnectorRequestModel(
            type=self.get_specification().type,
            name=name,
            description=description,
            user=user,
            workspace=workspace,
            is_shared=is_shared,
            auth_method=self.auth_method,
            resource_type=self.resource_type,
            alt_resource_types=resource_spec.resource_types,
            resource_id=self.resource_id,
            configuration=self.config.non_secret_values,
            secrets=self.config.secret_values,
        )

    def validate_runtime_args(
        self,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> None:
        """Validate the runtime arguments against the connector configuration.

        Validate that the runtime arguments supplied by the connector's consumer
        are compatible with the connector configuration and its specification.
        This includes validating that the authentication method, resource type
        and resource ID are compatible with the connector configuration and its
        capabilities.

        Args:
            resource_type: The type of resource requested by the connector's
                consumer. Can be different than the resource type that the
                connector is configured to access if alternative resource
                types or arbitrary resource types are allowed by the connector
                configuration.
            resource_id: The ID of the resource requested by the connector's
                consumer. Can be different than the resource ID that the
                connector is configured to access, e.g. if resource ID aliases
                or wildcards are used.

        Raises:
            ValueError: If the runtime arguments are not valid.
        """
        spec = self.get_specification()
        try:
            # Get the resource specification corresponding to the
            # connector configuration.
            _, resource_spec = spec.find_resource_specifications(
                self.auth_method,
                self.resource_type,
                self.resource_id,
            )
        except (KeyError, ValueError) as e:
            raise ValueError(
                f"connector configuration is not valid: {e}"
            ) from e

        # Verify that the requested resource type is the same as or an
        # alternative of the one configured for the connector.
        if resource_type and not resource_spec.is_supported_resource_type(
            resource_type,
        ):
            raise ValueError(
                f"the connector is configured to provide access to a "
                f"'{self.resource_type}' resource type, but an "
                f"incompatible '{resource_type}' resource type was requested."
            )

        # Verify the resource ID
        if resource_id:
            if not resource_spec.multi_instance:
                raise ValueError(
                    f"the connector is configured to provide access to a "
                    f"'{self.resource_type}' resource type that does not "
                    "support multiple instances, but a resource ID was "
                    f"requested: '{resource_id}'."
                )

            if (
                self.resource_id
                and not resource_spec.is_equivalent_resource_id(
                    resource_id, self.resource_id
                )
            ):
                raise ValueError(
                    f"the connector is configured to provide access to a "
                    f"'{self.resource_type}' resource with a "
                    f"resource ID of '{self.resource_id}', but an "
                    f"incompatible resource ID was requested: '{resource_id}'."
                )

        else:
            if resource_spec.multi_instance:
                raise ValueError(
                    f"the connector is configured to provide access to a "
                    f"'{self.resource_type}' resource type that supports "
                    "multiple instances, but no resource ID was provided."
                )

    def connect(
        self,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Authenticate and connect to a resource.

        Initialize and return an implementation specific object representing an
        authenticated service client, connection or session that can be used
        to access the indicated resource type.

        Args:
            resource_type: The type of resource to connect to. If the connector
                instance is configured with a resource type that is not the same
                or an alternative to the one requested, a `ValueError` exception
                is raised.
            resource_id: The ID of a particular resource instance to connect
                to. Use this with resource types that allow multiple instances.
                If the connector instance is already configured with a resource
                ID that is not the same or equivalent to the one requested, or
                if the resource type does not support multiple instances, a
                `ValueError` exception is raised.
            kwargs: Additional implementation specific keyword arguments to use
                to configure the client.

        Returns:
            An implementation specific object representing the authenticated
            service client, connection or session.
        """
        self.validate_runtime_args(
            resource_type=resource_type,
            resource_id=resource_id,
        )

        return self._connect_to_resource(
            resource_type=resource_type,
            resource_id=resource_id,
            **kwargs,
        )

    @classmethod
    def auto_configure(
        cls,
        auth_method: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs: Any,
    ) -> "ServiceConnector":
        """Auto-configure a connector instance.

        Instantiate a connector with a configuration extracted from the
        authentication configuration available in the environment (e.g.
        environment variables or local client/SDK configuration files).

        Args:
            auth_method: The particular authentication method to use. If
                omitted and if the connector implementation cannot decide which
                authentication method to use, it may raise an exception.
            resource_type: The type of resource to configure. If omitted and
                if the connector implementation cannot decide which resource
                type to use, it may raise an exception.
            resource_id: The ID of the resource instance to configure. The
                connector implementation may choose to either require or ignore
                this parameter if it does not support or detect a resource type
                that supports multiple instances.
            kwargs: Additional implementation specific keyword arguments to use.

        Returns:
            A connector instance configured with authentication credentials
            automatically extracted from the environment.

        Raises:
            ValueError: If the connector does not support the requested
                authentication method or resource type.
        """
        spec = cls.get_specification()

        auth_methods = spec.auth_method_map.keys()
        if auth_method and auth_method not in auth_methods:
            raise ValueError(
                f"unsupported authentication method: '{auth_method}'"
            )

        resource_types = spec.resource_type_map.keys()
        if (
            resource_type
            and resource_type not in spec.resource_type_map
            and None not in resource_types
        ):
            raise ValueError(f"unsupported resource type: '{resource_type}'")

        return cls._auto_configure(
            auth_method=auth_method,
            resource_type=resource_type,
            resource_id=resource_id,
            **kwargs,
        )

    def configure_local_client(
        self,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Configure a local client to authenticate and connect to a resource.

        This method uses the connector's configuration to configure a local
        client or SDK installed on the localhost for the indicated resource.

        Args:
            resource_type: The type of resource to configure the local client
                to connect to. If the connector instance is configured with a
                resource type that is not the same or an alternative to the one
                requested, a `ValueError` exception is raised.
            resource_id: The ID of a particular resource instance to configure
                the local client to connect to. Use this with resource types
                that allow multiple instances. If the connector instance is
                already configured with a resource ID that is not the same or
                equivalent to the one requested, or if the resource type does
                not support multiple instances, a `ValueError` exception is
                raised.
            kwargs: Additional implementation specific keyword arguments to use
                to configure the client.
        """
        self.validate_runtime_args(
            resource_type=resource_type,
            resource_id=resource_id,
        )

        self._configure_local_client(
            resource_type=resource_type,
            resource_id=resource_id,
            **kwargs,
        )
