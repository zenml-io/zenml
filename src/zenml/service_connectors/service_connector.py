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
from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional, Tuple
from uuid import UUID

from pydantic import (
    BaseModel,
    SecretStr,
    ValidationError,
)

from zenml.client import Client
from zenml.exceptions import AuthorizationException
from zenml.logger import get_logger
from zenml.models import (
    ServiceConnectorBaseModel,
    ServiceConnectorRequestModel,
    ServiceConnectorResourceListModel,
    ServiceConnectorResponseModel,
    ServiceConnectorTypedResourceListModel,
    ServiceConnectorTypeModel,
    UserResponseModel,
    WorkspaceResponseModel,
)

logger = get_logger(__name__)


class AuthenticationConfig(BaseModel):
    """Base authentication configuration."""

    @property
    def secret_values(self) -> Dict[str, SecretStr]:
        """Get the secret values as a dictionary.

        Returns:
            A dictionary of all secret values in the configuration.
        """
        return {
            k: v
            for k, v in self.dict(exclude_none=True).items()
            if isinstance(v, SecretStr)
        }

    @property
    def non_secret_values(self) -> Dict[str, str]:
        """Get the non-secret values as a dictionary.

        Returns:
            A dictionary of all non-secret values in the configuration.
        """
        return {
            k: v
            for k, v in self.dict(exclude_none=True).items()
            if not isinstance(v, SecretStr)
        }

    @property
    def all_values(self) -> Dict[str, Any]:
        """Get all values as a dictionary.

        Returns:
            A dictionary of all values in the configuration.
        """
        return self.dict(exclude_none=True)


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
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    expiration_seconds: Optional[int] = None
    config: AuthenticationConfig

    _TYPE: ClassVar[Optional[ServiceConnectorTypeModel]] = None

    def __init__(self, **kwargs: Any) -> None:
        """Initialize a new service connector instance.

        Args:
            kwargs: Additional keyword arguments to pass to the base class
                constructor.
        """
        super().__init__(**kwargs)

        # Convert the resource ID in canonical form
        if self.resource_type and self.resource_id:
            self.resource_id = self._canonical_resource_id(
                self.resource_type, self.resource_id
            )

    @classmethod
    @abstractmethod
    def _get_connector_type(cls) -> ServiceConnectorTypeModel:
        """Get the connector type specification.

        Returns:
            The connector type specification.
        """

    def _canonical_resource_id(
        self, resource_type: str, resource_id: str
    ) -> str:
        """Convert a resource ID to its canonical form.

        This method is used to canonicalize the resource ID before it is
        stored in the connector instance. The default implementation simply
        returns the supplied resource ID as-is.

        Args:
            resource_type: The resource type to canonicalize.
            resource_id: The resource ID to canonicalize.

        Returns:
            The canonical resource ID.
        """
        return resource_id

    @abstractmethod
    def _connect_to_resource(
        self,
        **kwargs: Any,
    ) -> Any:
        """Authenticate and connect to a resource.

        This method initializes and returns an implementation specific object
        representing an authenticated service client, connection or session that
        can be used to access the resource that the connector instance is
        configured to connect to.

        The implementation should assume that the the resource type and resource
        ID configured in the connector instance are properly set and ready to
        be used.

        Args:
            kwargs: Additional implementation specific keyword arguments to use
                to configure the client.

        Returns:
            An implementation specific object representing the authenticated
            service client, connection or session.

        Raises:
            AuthorizationException: If authentication failed.
        """

    @abstractmethod
    def _configure_local_client(
        self,
        **kwargs: Any,
    ) -> None:
        """Configure a local client to authenticate and connect to a resource.

        This method configures a local client or SDK installed on the localhost
        to connect to the resource that the connector instance is configured
        to access.

        The implementation should assume that the the resource type and resource
        ID configured in the connector instance are properly set and ready to
        be used.

        Args:
            kwargs: Additional implementation specific keyword arguments to use
                to configure the client.

        Raises:
            AuthorizationException: If authentication failed.
            NotImplementedError: If the connector instance does not support
                local configuration for the configured resource type or
                authentication method.
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
            resource_type: The type of resource to configure. If not specified,
                the connector implementation must return a connector instance
                configured to access any of the supported resource types or
                decide to use a default resource type or raise an exception.
            resource_id: The ID of the resource to configure. The
                implementation may choose to either require or ignore this
                parameter if it does not support or detect a resource type that
                supports multiple instances.
            kwargs: Additional implementation specific keyword arguments to use.

        Returns:
            A connector instance configured with authentication credentials
            automatically extracted from the environment.

        Raises:
            NotImplementedError: If the connector auto-configuration fails or
                is not supported.
        """

    @abstractmethod
    def _verify(
        self,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> None:
        """Verify that the connector can authenticate and connect.

        This method uses the connector's configuration to verify that it can
        authenticate and connect to the indicated resource.

        The implementation should not rely on the resource type and resource
        ID configured in the connector instance because they might be
        missing or different than the ones supplied to this method (e.g. if
        this is a multi-type or multi-instance connector).

        Args:
            resource_type: The type of the resource to verify. If omitted and
                if the connector supports multiple resource types, the
                implementation must verify that it can authenticate and connect
                to any of the supported resource types or raise a
                NotImplementedError exception.
            resource_id: The ID of the resource to connect to. Omitted if the
                supplied resource type does not allow multiple instances or
                if a resource type is not specified. If the supplied resource
                type allows multiple instances, this parameter may still be
                omitted to verify that the connector can authenticate and
                connect to any instance of the given resource type.

        Raises:
            ValueError: If the connector configuration is invalid.
            AuthorizationException: If authentication failed.
            NotImplementedError: If the connector instance does not support
                verification for the configured resource type or
                authentication method.
        """

    @abstractmethod
    def _list_resource_ids(
        self,
        resource_type: str,
        resource_id: Optional[str] = None,
    ) -> List[str]:
        """List the resource IDs for the given resource type.

        This method uses the connector's configuration to retrieve a list with
        the IDs of all resource instances of the given type that the connector
        can access. If the resource type does not support multiple instances,
        an empty list must be returned.

        Args:
            resource_type: The type of the resources to list.
            resource_id: The ID of a particular resource to filter by.

        Raises:
            AuthorizationException: If authentication failed.
            NotImplementedError: If the connector instance does not support
                listing resource IDs for the configured resource type or
                authentication method.
        """

    def _get_client_connector(
        self,
        resource_type: str,
        resource_id: Optional[str] = None,
    ) -> "ServiceConnector":
        """Get a connector instance that can be used to connect to a resource.

        This method should return a connector instance that is fully configured
        and ready to use to connect to the indicated resource:
        - has proper authentication configuration and credentials. These can be
        either the same as the ones configured in this connector instance or
        different ones (e.g. if this connector is able to generate temporary
        credentials for a particular resource).
        - has a resource type
        - has a resource ID, if applicable

        This method is useful in cases where the connector instance responsible
        for authentication is not the same as the connector instance that
        provides clients to access the authenticated resource. Some example
        use-cases:

        - a connector is configured with long-lived credentials or credentials
        with wide permissions and is able to generate temporary credentials or
        credentials with a narrower permissions scope for a particular resource.
        In this case, the "server connector" instance stores the long-lived
        credentials and is used to generate temporary credentials that are used
        by the "client connector" instance to instantiate clients for the resource.

        - a connector is able to handle multiple types of resources (e.g. cloud
        providers). In this case, the main connector instance can be
        configured without a resource type and is able to grant access to any
        resource type. It can instantiate "client connectors" for a particular
        resource type and instance. The "client connector" can even be an
        instance of a different implementation (e.g. the AWS connector can
        instantiate a Kubernetes connector to access an EKS resource).

        The default implementation returns the connector instance itself, if it
        is ready to use to connect to the indicated resource, or raises an error
        if it is not.

        Args:
            resource_type: The type of the resources to connect to.
            resource_id: The ID of a particular resource to connect to.

        Raises:
            AuthorizationException: If authentication failed.
            NotImplementedError: If the connector instance does not support
                connecting to the configured resource type or authentication
                method.
        """
        self.validate_runtime_args(
            resource_type=resource_type,
            resource_id=resource_id,
            require_resource_type=True,
            require_resource_id=True,
        )

        return self

    @classmethod
    def get_type(cls) -> ServiceConnectorTypeModel:
        """Get the connector type specification.

        Returns:
            The connector type specification.
        """
        if cls._TYPE is not None:
            return cls._TYPE

        connector_type = cls._get_connector_type()
        connector_type.set_connector_class(cls)
        cls._TYPE = connector_type
        return cls._TYPE

    @property
    def type(self) -> ServiceConnectorTypeModel:
        """Get the connector type specification.

        Returns:
            The connector type specification.
        """
        return self.get_type()

    @property
    def supported_resource_types(self) -> List[str]:
        """The resource types supported by this connector instance.

        Returns:
            A list with the resource types supported by this connector instance.
        """
        spec = self.get_type()

        # An unset resource type means that the connector is configured to
        # access any of the supported resource types (a multi-type connector).
        # In that case, we report all the supported resource types to
        # allow it to be discovered as compatible with any of them.
        if self.resource_type:
            resource_types = [self.resource_type]
        else:
            resource_types = list(spec.resource_type_map.keys())

        return resource_types

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
        spec = cls.get_type()

        # Multiple resource types in the model means that the connector
        # instance is configured to access any of the supported resource
        # types (a multi-type connector). We represent that here by setting the
        # resource type to None.
        resource_type: Optional[str] = None
        if len(model.resource_types) == 1:
            resource_type = model.resource_types[0]

        expiration_seconds: Optional[int] = None
        try:
            method_spec, _ = spec.find_resource_specifications(
                model.auth_method,
                resource_type,
                model.resource_id,
            )
            expiration_seconds = method_spec.validate_expiration(
                model.expiration_seconds
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

            if secret.has_missing_values:
                raise ValueError(
                    f"secret with ID '{model.secret_id}' referenced in the "
                    "connector configuration has missing values. This can "
                    "happen for example if your user lacks the permissions "
                    "required to access the secret."
                )

            config.update(secret.secret_values)

        if model.secrets:
            config.update(
                {
                    k: v.get_secret_value()
                    for k, v in model.secrets.items()
                    if v
                }
            )

        if method_spec.config_class is None:
            raise ValueError(
                f"the implementation of the {model.name} connector type is "
                "not available in the environment. Please check that you "
                "have installed the required dependencies."
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
            resource_type=resource_type,
            resource_id=model.resource_id,
            config=auth_config,
            expires=model.expires_at,
            expiration_seconds=expiration_seconds,
        )
        if isinstance(model, ServiceConnectorResponseModel):
            connector.id = model.id
            connector.name = model.name

        return connector

    def to_model(
        self,
        user: UUID,
        workspace: UUID,
        name: Optional[str] = None,
        is_shared: bool = False,
        description: str = "",
        labels: Optional[Dict[str, str]] = None,
    ) -> "ServiceConnectorRequestModel":
        """Convert the connector instance to a service connector model.

        Args:
            name: The name of the connector.
            user: The ID of the user that created the connector.
            workspace: The ID of the workspace that the connector belongs to.
            is_shared: Whether the connector is shared with other users.
            description: The description of the connector.
            labels: The labels of the connector.

        Returns:
            The service connector model corresponding to the connector
            instance.

        Raises:
            ValueError: If the connector configuration is not valid.
        """
        spec = self.get_type()

        name = name or self.name
        if name is None:
            raise ValueError(
                "connector configuration is not valid: name must be set"
            )

        model = ServiceConnectorRequestModel(
            type=spec.type,
            name=name,
            description=description,
            user=user,
            workspace=workspace,
            is_shared=is_shared,
            auth_method=self.auth_method,
            expires_at=self.expires_at,
            expiration_seconds=self.expiration_seconds,
            labels=labels or {},
        )

        # Validate the connector configuration.
        model.validate_and_configure_resources(
            connector_type=spec,
            resource_types=self.resource_type,
            resource_id=self.resource_id,
            configuration=self.config.non_secret_values,
            secrets=self.config.secret_values,
        )

        return model

    def to_response_model(
        self,
        workspace: WorkspaceResponseModel,
        user: Optional[UserResponseModel] = None,
        name: Optional[str] = None,
        id: Optional[UUID] = None,
        is_shared: bool = False,
        description: str = "",
        labels: Optional[Dict[str, str]] = None,
    ) -> "ServiceConnectorResponseModel":
        """Convert the connector instance to a service connector response model.

        Args:
            workspace: The workspace that the connector belongs to.
            user: The user that created the connector.
            name: The name of the connector.
            id: The ID of the connector.
            is_shared: Whether the connector is shared with other users.
            description: The description of the connector.
            labels: The labels of the connector.

        Returns:
            The service connector response model corresponding to the connector
            instance.

        Raises:
            ValueError: If the connector configuration is not valid.
        """
        spec = self.get_type()

        name = name or self.name
        id = id or self.id
        if name is None or id is None:
            raise ValueError(
                "connector configuration is not valid: name and ID must be set"
            )

        model = ServiceConnectorResponseModel(
            id=id,
            created=datetime.utcnow(),
            updated=datetime.utcnow(),
            type=self.get_type().type,
            name=name,
            description=description,
            user=user,
            workspace=workspace,
            is_shared=is_shared,
            auth_method=self.auth_method,
            expires_at=self.expires_at,
            expiration_seconds=self.expiration_seconds,
            labels=labels or {},
        )

        # Validate the connector configuration.
        model.validate_and_configure_resources(
            connector_type=spec,
            resource_types=self.resource_type,
            resource_id=self.resource_id,
            configuration=self.config.non_secret_values,
            secrets=self.config.secret_values,
        )

        return model

    def has_expired(self) -> bool:
        """Check if the connector has expired.

        Verify that the authentication credentials associated with the connector
        have not expired by checking the expiration time against the current
        time.

        Returns:
            True if the connector has expired, False otherwise.
        """
        if not self.expires_at:
            return False

        return self.expires_at < datetime.now(timezone.utc)

    def validate_runtime_args(
        self,
        resource_type: Optional[str],
        resource_id: Optional[str] = None,
        require_resource_type: bool = False,
        require_resource_id: bool = False,
        **kwargs: Any,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Validate the runtime arguments against the connector configuration.

        Validate that the runtime arguments supplied by the connector's consumer
        are compatible with the connector configuration and its specification.
        This includes validating that the resource type and resource ID are
        compatible with the connector configuration and its capabilities.

        Args:
            resource_type: The type of the resource requested by the connector's
                consumer. Must be the same as the resource type that the
                connector is configured to access, unless the connector is
                configured to access any resource type.
            resource_id: The ID of the resource requested by the connector's
                consumer. Can be different than the resource ID that the
                connector is configured to access, e.g. if it is not in the
                canonical form.
            require_resource_type: Whether the resource type is required.
            require_resource_id: Whether the resource ID is required when the
                resource type supports multiple instances.
            kwargs: Additional runtime arguments.

        Returns:
            The validated resource type and resource ID.

        Raises:
            ValueError: If the runtime arguments are not valid.
            AuthorizationException: If the connector's authentication
                credentials have expired.
        """
        if self.has_expired():
            raise AuthorizationException(
                "the connector's authentication credentials have expired."
            )

        if (
            self.resource_type
            and resource_type
            and (self.resource_type != resource_type)
        ):
            raise ValueError(
                f"the connector is configured to provide access to a "
                f"'{self.resource_type}' resource type, but a different "
                f"resource type was requested: '{resource_type}'."
            )

        resource_type = resource_type or self.resource_type
        resource_id = resource_id or self.resource_id

        if require_resource_type and not resource_type:
            raise ValueError(
                "the connector is configured to provide access to any "
                "resource type. A resource type must be specified when "
                "requesting access to a resource."
            )

        spec = self.get_type()

        try:
            # Get the resource specification corresponding to the
            # connector configuration.
            _, resource_spec = spec.find_resource_specifications(
                self.auth_method,
                resource_type,
                resource_id,
            )
        except (KeyError, ValueError) as e:
            raise ValueError(
                f"connector configuration is not valid: {e}"
            ) from e

        if not resource_type or not resource_spec:
            if resource_id:
                raise ValueError(
                    "a resource ID was specified, but no resource type was "
                    "provided nor is the connector configured to provide "
                    "access to a particular resource type."
                )

            return resource_type, resource_id

        # Verify the resource ID
        if resource_id:

            # Convert the resource ID to its canonical form.
            resource_id = self._canonical_resource_id(
                resource_type, resource_id
            )

            if self.resource_id and self.resource_id != resource_id:
                raise ValueError(
                    f"the connector is configured to provide access to a "
                    f"'{resource_type}' resource with a "
                    f"resource ID of '{self.resource_id}', but an "
                    f"incompatible resource ID was requested: '{resource_id}'."
                )

        else:
            if (
                not self.resource_id
                and resource_spec.multi_instance
                and require_resource_id
            ):
                raise ValueError(
                    f"the connector is configured to provide access to a "
                    f"'{resource_type}' resource type that supports "
                    "multiple instances, but no resource ID was provided."
                )

        return resource_type, resource_id

    def connect(
        self,
        **kwargs: Any,
    ) -> Any:
        """Authenticate and connect to a resource.

        Initialize and return an implementation specific object representing an
        authenticated service client, connection or session that can be used
        to access the resource that the connector is configured to access.

        The connector has to be fully configured for this method to succeed
        (i.e. the connector's configuration must be valid, a resource type must
        be specified and the resource ID must be specified if the resource type
        supports multiple instances). For service connectors that are configured
        to access multiple resource types or multiple resource instances, this
        method should only be called on a client connector retrieved by calling
        `get_client_connector` on the service connector.

        Args:
            kwargs: Additional implementation specific keyword arguments to use
                to configure the client.

        Returns:
            An implementation specific object representing the authenticated
            service client, connection or session.
        """
        self.validate_runtime_args(
            resource_type=self.resource_type,
            resource_id=self.resource_id,
            require_resource_type=True,
            require_resource_id=True,
        )

        return self._connect_to_resource(
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
            resource_type: The type of resource to configure. If not specified,
                the method returns a connector instance configured to access any
                of the supported resource types (multi-type connector) or
                configured to use a default resource type. If the connector
                doesn't support multi-type configurations or if it cannot decide
                which resource type to use, it may raise an exception.
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
        spec = cls.get_type()

        if auth_method and auth_method not in spec.auth_method_map:
            raise ValueError(
                f"unsupported authentication method: '{auth_method}'"
            )

        if resource_type and resource_type not in spec.resource_type_map:
            raise ValueError(f"unsupported resource type: '{resource_type}'")

        return cls._auto_configure(
            auth_method=auth_method,
            resource_type=resource_type,
            resource_id=resource_id,
            **kwargs,
        )

    def configure_local_client(
        self,
        **kwargs: Any,
    ) -> None:
        """Configure a local client to authenticate and connect to a resource.

        This method uses the connector's configuration to configure a local
        client or SDK installed on the localhost so that it can authenticate
        and connect to the resource that the connector is configured to access.

        The connector has to be fully configured for this method to succeed
        (i.e. the connector's configuration must be valid, a resource type must
        be specified and the resource ID must be specified if the resource type
        supports multiple instances). For service connectors that are configured
        to access multiple resource types or multiple resource instances, this
        method should only be called on a client connector retrieved by calling
        `get_client_connector` on the service connector.

        Args:
            kwargs: Additional implementation specific keyword arguments to use
                to configure the client.
        """
        self.validate_runtime_args(
            resource_type=self.resource_type,
            resource_id=self.resource_id,
            require_resource_type=True,
            require_resource_id=True,
        )

        self._configure_local_client(
            **kwargs,
        )

    def verify(
        self,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Verify that the connector can connect to a remote resource.

        This method verifies that the connector is configured with valid
        credentials and resource information by actively trying to connect to
        the remote resource provider service.

        Args:
            resource_type: The type of the resource to verify. If the connector
                instance is already configured with a resource type, this
                argument must be the same as the one configured if supplied. If
                omitted, the connector verifies that the configuration can be
                used to connect to any of the supported resource types.
            resource_id: The ID of a particular resource instance to configure
                the local client to connect to. Use this with resource types
                that allow multiple instances. If the connector instance is
                already configured with a resource ID that is not the same or
                equivalent to the one requested, or if the resource type does
                not support multiple instances, a `ValueError` exception is
                raised.
            kwargs: Additional implementation specific keyword arguments to use
                to configure the client.

        Raises:
            ValueError: If the connector is not configured with valid
                credentials or resource information.
            AuthorizationException: If the connector is not authorized to
                connect to the remote resource.
        """
        try:
            resource_type, resource_id = self.validate_runtime_args(
                resource_type=resource_type,
                resource_id=resource_id,
                require_resource_type=False,
                require_resource_id=False,
            )

            self._verify(
                resource_type=resource_type, resource_id=resource_id, **kwargs
            )
        except ValueError as exc:
            logger.exception("connector validation failed")
            raise ValueError(
                "The connector configuration is incomplete, invalid or does "
                f"not allow for a verification: {exc}",
            )
        except AuthorizationException as exc:
            logger.exception("connector validation failed")
            raise AuthorizationException(
                "The connector is not authorized to connect to the remote "
                f"resource: {exc}",
            )

    def list_resources(
        self,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> ServiceConnectorResourceListModel:
        """List all resources that the connector can access.

        This method retrieves the types and IDs of all resources that
        the connector can access. The connector must be configured with valid
        credentials. If the connector is configured with a resource type, it
        will only list the IDs of resources of that type. Otherwise, it will
        list the IDs of resources of all supported types grouped by resource
        type.

        Args:
            resource_type: The type of the resources to list. If the connector
                instance is already configured with a resource type, this
                argument must be the same as the one configured if supplied.
            resource_id: The ID of a particular resource instance to filter by.

        Returns:
            A list of resource list models containing the resource types and
            resource IDs of all resources that the connector can access.

        Raises:
            ValueError: If the connector is not configured with valid
                credentials or resource information.
            AuthorizationException: If the connector is not authorized to
                connect to the remote resource.
        """
        try:
            resource_type, resource_id = self.validate_runtime_args(
                resource_type=resource_type,
                resource_id=resource_id,
                require_resource_type=False,
                require_resource_id=False,
            )

            if resource_type is not None:
                resource_types = [resource_type]
            else:
                resource_types = self.supported_resource_types

            spec = self.get_type()

            resource_list = (
                ServiceConnectorResourceListModel.from_connector_model(
                    connector_type_model=spec,
                )
            )
            resource_list.id = self.id
            resource_list.name = self.name

            for resource_type in resource_types:
                resource_type_spec = spec.resource_type_map[resource_type]

                typed_resources = ServiceConnectorTypedResourceListModel.from_resource_type_model(
                    resource_type_spec
                )

                resource_list.resources.append(typed_resources)

                if resource_type_spec.multi_instance:
                    if resource_type_spec.instance_discovery:
                        typed_resources.resource_ids = self._list_resource_ids(
                            resource_type=resource_type,
                            resource_id=resource_id,
                        )
                    elif resource_id:
                        typed_resources.resource_ids = [resource_id]

            return resource_list
        except ValueError as exc:
            logger.exception("connector validation failed")
            raise ValueError(
                "The connector configuration is incomplete, invalid or does "
                f"not allow listing resource instances: {exc}",
            )
        except AuthorizationException as exc:
            logger.exception("connector validation failed")
            raise AuthorizationException(
                "The connector is not authorized to connect to the remote "
                f"resource: {exc}",
            )

    def get_client_connector(
        self,
        resource_type: Optional[str],
        resource_id: Optional[str] = None,
    ) -> "ServiceConnector":
        """Get a client connector that can be used to connect to a resource.

        The client connector can be used by consumers to connect to a resource
        (i.e. make calls to `connect` and `configure_local_client`).

        The returned connector may be the same as the original connector
        or it may a different instance configured with different credentials or
        even of a different connector type.

        Args:
            resource_type: The type of the resource to connect to.
            resource_id: The ID of a particular resource to connect to.

        Raises:
            AuthorizationException: If authentication failed.
            NotImplementedError: If the connector instance does not support
                connecting to the configured resource type or authentication
                method.
        """
        resource_type, resource_id = self.validate_runtime_args(
            resource_type=resource_type,
            resource_id=resource_id,
            require_resource_type=True,
            require_resource_id=True,
        )

        # Verify if the connector allows access to the requested resource type
        # and instance.
        self._verify(
            resource_type=resource_type,
            resource_id=resource_id,
        )

        assert resource_type is not None

        return self._get_client_connector(
            resource_type=resource_type,
            resource_id=resource_id,
        )
