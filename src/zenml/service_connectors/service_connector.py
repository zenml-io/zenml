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

import logging
from abc import abstractmethod
from datetime import datetime, timedelta, timezone
from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
)
from uuid import UUID

from pydantic import (
    BaseModel,
    SecretStr,
    ValidationError,
)
from pydantic._internal._model_construction import ModelMetaclass

from zenml.client import Client
from zenml.constants import (
    ENV_ZENML_ENABLE_IMPLICIT_AUTH_METHODS,
    SERVICE_CONNECTOR_SKEW_TOLERANCE_SECONDS,
    handle_bool_env_var,
)
from zenml.exceptions import AuthorizationException
from zenml.logger import get_logger
from zenml.models import (
    ServiceConnectorRequest,
    ServiceConnectorResourcesModel,
    ServiceConnectorResponse,
    ServiceConnectorResponseBody,
    ServiceConnectorResponseMetadata,
    ServiceConnectorResponseResources,
    ServiceConnectorTypedResourcesModel,
    ServiceConnectorTypeModel,
    UserResponse,
)
from zenml.utils.time_utils import utc_now

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
            for k, v in self.model_dump(exclude_none=True).items()
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
            for k, v in self.model_dump(exclude_none=True).items()
            if not isinstance(v, SecretStr)
        }

    @property
    def all_values(self) -> Dict[str, Any]:
        """Get all values as a dictionary.

        Returns:
            A dictionary of all values in the configuration.
        """
        return self.model_dump(exclude_none=True)


class ServiceConnectorMeta(ModelMetaclass):
    """Metaclass responsible for automatically registering ServiceConnector classes."""

    def __new__(
        mcs, name: str, bases: Tuple[Type[Any], ...], dct: Dict[str, Any]
    ) -> "ServiceConnectorMeta":
        """Creates a new ServiceConnector class and registers it.

        Args:
            name: The name of the class.
            bases: The base classes of the class.
            dct: The dictionary of the class.

        Returns:
            The ServiceConnectorMeta class.
        """
        cls = cast(
            Type["ServiceConnector"], super().__new__(mcs, name, bases, dct)
        )

        # Skip the following validation and registration for the base class.
        if name == "ServiceConnector":
            return cls

        else:
            from zenml.service_connectors.service_connector_registry import (
                service_connector_registry,
            )

            # Register the service connector.
            service_connector_registry.register_service_connector_type(
                cls.get_type()
            )

        return cls


class ServiceConnector(BaseModel, metaclass=ServiceConnectorMeta):
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
    declared in the connector type specification. The role of this specification
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
    expires_skew_tolerance: Optional[int] = None
    expiration_seconds: Optional[int] = None
    config: AuthenticationConfig
    allow_implicit_auth_methods: bool = False

    _TYPE: ClassVar[Optional[ServiceConnectorTypeModel]] = None

    def __init__(self, **kwargs: Any) -> None:
        """Initialize a new service connector instance.

        Args:
            kwargs: Additional keyword arguments to pass to the base class
                constructor.
        """
        super().__init__(**kwargs)

        # Convert the resource ID to its canonical form. For resource types
        # that don't support multiple instances:
        # - if a resource ID is not provided, we use the default resource ID for
        # the resource type
        # - if a resource ID is provided, we verify that it matches the default
        # resource ID for the resource type
        if self.resource_type:
            try:
                self.resource_id = self._validate_resource_id(
                    self.resource_type, self.resource_id
                )
            except AuthorizationException as e:
                error = (
                    f"Authorization error validating resource ID "
                    f"{self.resource_id} for resource type "
                    f"{self.resource_type}: {e}"
                )
                # Log an exception if debug logging is enabled
                if logger.isEnabledFor(logging.DEBUG):
                    logger.exception(error)
                else:
                    logger.warning(error)

                self.resource_id = None

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

    def _get_default_resource_id(self, resource_type: str) -> str:
        """Get the default resource ID for a resource type.

        Service connector implementations must override this method and provide
        a default resource ID for resources that do not support multiple
        instances.

        Args:
            resource_type: The type of the resource to get a default resource ID
                for. Only called with resource types that do not support
                multiple instances.

        Raises:
            RuntimeError: If the resource type does not support multiple
                instances and the connector implementation did not provide a
                default resource ID.
        """
        # If a resource type does not support multiple instances, raise an
        # exception; the connector implementation must override this method and
        # provide a default resource ID in this case.
        raise RuntimeError(
            f"Resource type '{resource_type}' does not support multiple "
            f"instances and the connector implementation didn't provide "
            f"a default resource ID."
        )

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
        ID configured in the connector instance are both set, valid and ready to
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
        ID configured in the connector instance are both set, valid and ready to
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
    ) -> List[str]:
        """Verify and list all the resources that the connector can access.

        This method uses the connector's configuration to verify that it can
        authenticate and access the indicated resource(s). A non-empty list of
        resource IDs in canonical format MUST be returned if the resource type
        is supplied, otherwise the connector is marked as being in an error
        state that doesn't allow it to be used to access any resources.

        The implementation should not rely on the resource type and resource
        ID configured in the connector instance because they might be
        missing or different than the ones supplied to this method (e.g. if
        this is a multi-type or multi-instance connector).

        If a resource type is not supplied, the implementation must verify that
        it can authenticate and connect to any of the supported resource types
        and should not return any resource IDs. A list of resource IDs may be
        returned in this case, but is not required.

        For resource types that do not support multiple instances, the
        resource ID parameter, if supplied, is the same as the default
        resource ID for the resource type as returned by
        `_get_default_resource_id`, in which case, the implementation should
        return it unmodified.

        For resource types that do support multiple instances, if the resource
        ID is not supplied, the implementation MUST return a non-empty list of
        resource IDs in canonical format identifying all the resources that the
        connector can access of the specified type.

        Args:
            resource_type: The type of the resource to verify. If omitted and
                if the connector supports multiple resource types, the
                implementation must verify that it can authenticate and connect
                to any and all of the supported resource types.
            resource_id: The ID of the resource to connect to. Omitted if a
                resource type is not specified. It has the same value as the
                default resource ID if the supplied resource type doesn't
                support multiple instances. If the supplied resource type does
                allows multiple instances, this parameter may still be omitted
                to fetch a list of resource IDs identifying all the resources
                of the indicated type that the connector can access.

        Returns:
            The list of resources IDs in canonical format identifying the
            resources that the connector can access. This list may be empty only
            if the resource type is not specified (i.e. for multi-type
            connectors).

        Raises:
            ValueError: If the connector configuration is invalid.
            AuthorizationException: If authentication failed.
        """

    def _get_connector_client(
        self,
        resource_type: str,
        resource_id: str,
    ) -> "ServiceConnector":
        """Get a connector instance that can be used to connect to a resource.

        This method should return a connector instance that is fully configured
        and ready to use to access the indicated resource:
        - has proper authentication configuration and credentials. These can be
        either the same as the ones configured in this connector instance or
        different ones (e.g. if this connector is able to generate temporary
        credentials for a particular resource).
        - has a resource type
        - has a resource ID

        This method is useful in cases where the connector capable of
        authenticating against the target service and accessing the configured
        resource is different than the connector configured by the user. Some
        example use-cases for this are:

        - a connector is configured with long-lived credentials or credentials
        with wide permissions but is able to generate temporary credentials or
        credentials with a narrower permissions scope for a particular resource.
        In this case, the "main connector" instance stores the long-lived
        credentials and is used to generate temporary credentials that are used
        by the "connector client" instance to authenticate against the target
        service and access the resource.

        - a connector is configured to access multiple types of resources (e.g.
        cloud providers) or multiple resource instances. In this case, the "main
        connector" instance is configured without a resource type or without a
        resource ID and is able to grant access to any resource type/resource
        ID. It can instantiate "connector clients" for a particular
        resource type and resource ID.

        - a connector is configured with a resource type but it is able to
        generate configurations for a different resource type. In this case,
        the "main connector" and the "connector client" can even belong to
        different connector implementations and the "main connector" can
        generate a "connector client" configuration of a different resource type
        that is used to access the final resource (e.g. the AWS connector can
        instantiate a Kubernetes connector client to access an EKS resource as
        if it were a generic Kubernetes cluster).

        The default implementation returns this connector instance itself, or a
        copy of it if the resource type or resource ID are different than the
        ones configured in the connector instance.

        Args:
            resource_type: The type of the resources to connect to.
            resource_id: The ID of a particular resource to connect to.

        Returns:
            A service connector client instance that can be used to connect to
            the indicated resource.
        """
        if (
            self.resource_type == resource_type
            and self.resource_id == resource_id
        ):
            return self

        copy = self.model_copy()
        copy.resource_type = resource_type
        copy.resource_id = resource_id
        return copy

    def _validate_resource_id(
        self, resource_type: str, resource_id: Optional[str]
    ) -> Optional[str]:
        """Validate a resource ID value of a certain type against the connector configuration.

        Args:
            resource_type: The type of resource to validate.
            resource_id: The resource ID to validate.

        Returns:
            The validated resource ID, or a default resource ID if the resource
            type supports multiple instances and one was not supplied.

        Raises:
            AuthorizationException: If the connector is not authorized to
                access the provided resource ID.
        """
        # Fetch the resource type specification
        resource_type_spec = self.type.resource_type_dict[resource_type]
        # If the resource type supports multiple instances, return the supplied
        # resource converted to canonical format, if supplied
        if resource_type_spec.supports_instances:
            if resource_id is None:
                return None
            return self._canonical_resource_id(resource_type, resource_id)

        # If the resource type does not support multiple instances, the
        # connector implementation must provide a default resource ID based
        # on the connector configuration
        default_resource_id = self._get_default_resource_id(resource_type)

        if resource_id is None:
            return default_resource_id

        resource_id = self._canonical_resource_id(resource_type, resource_id)
        if resource_id != default_resource_id:
            raise AuthorizationException(
                f"The connector does not allow access to the provided "
                f"'{resource_id}' {resource_type_spec.name} resource. It "
                f"only allows access to the following resource: "
                f"'{default_resource_id}'."
            )

        return resource_id

    def _check_implicit_auth_method_allowed(self) -> None:
        """Check if implicit authentication methods are allowed.

        Raises:
            AuthorizationException: If implicit authentication methods are
                not enabled.
        """
        # If the connector instance is especially configured to allow implicit
        # authentication methods, skip the check.
        if self.allow_implicit_auth_methods:
            return
        if not handle_bool_env_var(ENV_ZENML_ENABLE_IMPLICIT_AUTH_METHODS):
            raise AuthorizationException(
                "Implicit authentication methods for service connectors are "
                "implicitly disabled for security reasons. To enabled them, "
                f"the {ENV_ZENML_ENABLE_IMPLICIT_AUTH_METHODS} environment "
                "variable must be set for the ZenML deployment."
            )

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
            resource_types = list(spec.resource_type_dict.keys())

        return resource_types

    @classmethod
    def from_model(
        cls,
        model: Union["ServiceConnectorRequest", "ServiceConnectorResponse"],
    ) -> "ServiceConnector":
        """Creates a service connector instance from a service connector model.

        Args:
            model: The service connector model.

        Returns:
            The created service connector instance.

        Raises:
            ValueError: If the connector configuration is invalid.
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
        if isinstance(model, ServiceConnectorResponse) and model.secret_id:
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
            expires_at=model.expires_at,
            expires_skew_tolerance=model.expires_skew_tolerance,
            expiration_seconds=expiration_seconds,
        )
        if isinstance(model, ServiceConnectorResponse):
            connector.id = model.id
            connector.name = model.name

        return connector

    def to_model(
        self,
        name: Optional[str] = None,
        description: str = "",
        labels: Optional[Dict[str, str]] = None,
    ) -> "ServiceConnectorRequest":
        """Convert the connector instance to a service connector model.

        Args:
            name: The name of the connector.
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

        model = ServiceConnectorRequest(
            connector_type=spec.connector_type,
            name=name,
            description=description,
            auth_method=self.auth_method,
            expires_at=self.expires_at,
            expires_skew_tolerance=self.expires_skew_tolerance,
            expiration_seconds=self.expiration_seconds,
            labels=labels or {},
        )

        # Validate the connector configuration.
        model.validate_and_configure_resources(
            connector_type=spec,
            resource_types=self.resource_type,
            resource_id=self.resource_id,
            configuration=self.config.non_secret_values,
            secrets=self.config.secret_values,  # type: ignore[arg-type]
        )

        return model

    def to_response_model(
        self,
        user: Optional[UserResponse] = None,
        name: Optional[str] = None,
        id: Optional[UUID] = None,
        description: str = "",
        labels: Optional[Dict[str, str]] = None,
    ) -> "ServiceConnectorResponse":
        """Convert the connector instance to a service connector response model.

        Args:
            user: The user that created the connector.
            name: The name of the connector.
            id: The ID of the connector.
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

        now = utc_now()
        model = ServiceConnectorResponse(
            id=id,
            name=name,
            body=ServiceConnectorResponseBody(
                user_id=user.id if user else None,
                created=now,
                updated=now,
                description=description,
                connector_type=self.get_type(),
                auth_method=self.auth_method,
                expires_at=self.expires_at,
                expires_skew_tolerance=self.expires_skew_tolerance,
            ),
            metadata=ServiceConnectorResponseMetadata(
                expiration_seconds=self.expiration_seconds,
                labels=labels or {},
            ),
            resources=ServiceConnectorResponseResources(
                user=user,
            ),
        )

        # Validate the connector configuration.
        model.validate_and_configure_resources(
            connector_type=spec,
            resource_types=self.resource_type,
            resource_id=self.resource_id,
            configuration=self.config.non_secret_values,
            secrets=self.config.secret_values,  # type: ignore[arg-type]
        )

        return model

    def has_expired(self) -> bool:
        """Check if the connector authentication credentials have expired.

        Verify that the authentication credentials associated with the connector
        have not expired by checking the expiration time against the current
        time.

        Returns:
            True if the connector has expired, False otherwise.
        """
        if not self.expires_at:
            return False

        expires_at = self.expires_at.replace(tzinfo=timezone.utc)
        # Subtract some time to account for clock skew or other delays.
        expires_at = expires_at - timedelta(
            seconds=self.expires_skew_tolerance
            if self.expires_skew_tolerance is not None
            else SERVICE_CONNECTOR_SKEW_TOLERANCE_SECONDS
        )
        now = utc_now(tz_aware=expires_at)
        delta = expires_at - now
        result = delta < timedelta(seconds=0)

        logger.debug(
            f"Checking if connector {self.name} has expired.\n"
            f"Expires at: {self.expires_at}\n"
            f"Expires at (+skew): {expires_at}\n"
            f"Current UTC time: {now}\n"
            f"Delta: {delta}\n"
            f"Result: {result}\n"
        )

        return result

    def validate_runtime_args(
        self,
        resource_type: Optional[str],
        resource_id: Optional[str] = None,
        require_resource_type: bool = False,
        require_resource_id: bool = False,
        **kwargs: Any,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Validate the runtime arguments against the connector configuration.

        Validate that the supplied runtime arguments are compatible with the
        connector configuration and its specification. This includes validating
        that the resource type and resource ID are compatible with the connector
        configuration and its capabilities.

        Args:
            resource_type: The type of the resource supplied at runtime by the
                connector's consumer. Must be the same as the resource type that
                the connector is configured to access, unless the connector is
                configured to access any resource type.
            resource_id: The ID of the resource requested by the connector's
                consumer. Can be different than the resource ID that the
                connector is configured to access, e.g. if it is not in the
                canonical form.
            require_resource_type: Whether the resource type is required.
            require_resource_id: Whether the resource ID is required.
            kwargs: Additional runtime arguments.

        Returns:
            The validated resource type and resource ID.

        Raises:
            ValueError: If the runtime arguments are not valid.
        """
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
                "the connector is configured to provide access to multiple "
                "resource types. A resource type must be specified when "
                "requesting access to a resource."
            )

        spec = self.get_type()

        try:
            # Get the resource specification corresponding to the
            # connector configuration.
            _, resource_spec = spec.find_resource_specifications(
                self.auth_method,
                resource_type,
            )
        except (KeyError, ValueError) as e:
            raise ValueError(
                f"connector configuration is not valid: {e}"
            ) from e

        if not resource_type or not resource_spec:
            if resource_id:
                raise ValueError(
                    "the connector is configured to provide access to multiple "
                    "resource types, but only a resource name was specified. A "
                    "resource type must also be specified when "
                    "requesting access to a resource."
                )

            return resource_type, resource_id

        # Validate and convert the resource ID to its canonical form.
        # A default resource ID is returned for resource types that do not
        # support instances, if no resource ID is specified.
        resource_id = self._validate_resource_id(
            resource_type=resource_type,
            resource_id=resource_id,
        )

        if resource_id:
            if self.resource_id and self.resource_id != resource_id:
                raise ValueError(
                    f"the connector is configured to provide access to a "
                    f"single {resource_spec.name} resource with a "
                    f"resource name of '{self.resource_id}', but a "
                    f"different resource name was requested: "
                    f"'{resource_id}'."
                )

        else:
            if not self.resource_id and require_resource_id:
                raise ValueError(
                    f"the connector is configured to provide access to "
                    f"multiple {resource_spec.name} resources. A resource name "
                    "must be specified when requesting access to a resource."
                )

        return resource_type, resource_id

    def connect(
        self,
        verify: bool = True,
        **kwargs: Any,
    ) -> Any:
        """Authenticate and connect to a resource.

        Initialize and return an implementation specific object representing an
        authenticated service client, connection or session that can be used
        to access the resource that the connector is configured to access.

        The connector has to be fully configured for this method to succeed
        (i.e. the connector's configuration must be valid, a resource type and
        a resource ID must be configured). This method should only be called on
        a connector client retrieved by calling `get_connector_client` on the
        main service connector.

        Args:
            verify: Whether to verify that the connector can access the
                configured resource before connecting to it.
            kwargs: Additional implementation specific keyword arguments to use
                to configure the client.

        Returns:
            An implementation specific object representing the authenticated
            service client, connection or session.

        Raises:
            AuthorizationException: If the connector's authentication
                credentials have expired.
        """
        if verify:
            resource_type, resource_id = self.validate_runtime_args(
                resource_type=self.resource_type,
                resource_id=self.resource_id,
                require_resource_type=True,
                require_resource_id=True,
            )

            if self.has_expired():
                raise AuthorizationException(
                    "the connector's authentication credentials have expired."
                )

            self._verify(
                resource_type=resource_type,
                resource_id=resource_id,
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
    ) -> Optional["ServiceConnector"]:
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
            automatically extracted from the environment or None if
            auto-configuration is not supported.

        Raises:
            ValueError: If the connector does not support the requested
                authentication method or resource type.
            AuthorizationException: If the connector's authentication
                credentials have expired.
        """
        spec = cls.get_type()

        if not spec.supports_auto_configuration:
            return None

        if auth_method and auth_method not in spec.auth_method_dict:
            raise ValueError(
                f"connector type {spec.name} does not support authentication "
                f"method: '{auth_method}'"
            )

        if resource_type and resource_type not in spec.resource_type_dict:
            raise ValueError(
                f"connector type {spec.name} does not support resource type: "
                f"'{resource_type}'"
            )

        connector = cls._auto_configure(
            auth_method=auth_method,
            resource_type=resource_type,
            resource_id=resource_id,
            **kwargs,
        )

        if connector.has_expired():
            raise AuthorizationException(
                "the connector's auto-configured authentication credentials "
                "have expired."
            )

        connector._verify(
            resource_type=connector.resource_type,
            resource_id=connector.resource_id,
        )
        return connector

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
        supports multiple instances). This method should only be called on a
        connector client retrieved by calling `get_connector_client` on the
        main service connector.

        Args:
            kwargs: Additional implementation specific keyword arguments to use
                to configure the client.

        Raises:
            AuthorizationException: If the connector's authentication
                credentials have expired.
        """
        resource_type, resource_id = self.validate_runtime_args(
            resource_type=self.resource_type,
            resource_id=self.resource_id,
            require_resource_type=True,
            require_resource_id=True,
        )

        if self.has_expired():
            raise AuthorizationException(
                "the connector's authentication credentials have expired."
            )

        self._verify(
            resource_type=resource_type,
            resource_id=resource_id,
        )

        self._configure_local_client(
            **kwargs,
        )

    def verify(
        self,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        list_resources: bool = True,
    ) -> ServiceConnectorResourcesModel:
        """Verify and optionally list all the resources that the connector can access.

        This method uses the connector's configuration to verify that it can
        authenticate and access the indicated resource(s).

        If `list_resources` is set, the list of resources that the connector can
        access, scoped to the supplied resource type and resource ID is included
        in the response, otherwise the connector only verifies that it can
        globally authenticate and doesn't verify or return resource information
        (i.e. the `resource_ids` fields in the response are empty).

        Args:
            resource_type: The type of the resource to verify. If the connector
                instance is already configured with a resource type, this
                argument must be the same as the one configured if supplied.
            resource_id: The ID of a particular resource instance to check
                whether the connector can access. If the connector instance is
                already configured with a resource ID that is not the same or
                equivalent to the one requested, a `ValueError` exception is
                raised.
            list_resources: Whether to list the resources that the connector can
                access.

        Returns:
            A list of resources that the connector can access.

        Raises:
            ValueError: If the arguments or the connector configuration are
                not valid.
        """
        spec = self.get_type()

        resources = ServiceConnectorResourcesModel(
            connector_type=spec,
            id=self.id,
            name=self.name,
        )

        name_msg = f" '{self.name}'" if self.name else ""

        resource_types = self.supported_resource_types
        if resource_type:
            if resource_type not in resource_types:
                raise ValueError(
                    f"connector{name_msg} does not support resource type: "
                    f"'{resource_type}'. Supported resource types are: "
                    f"{', '.join(resource_types)}"
                )
            resource_types = [resource_type]

        # Pre-populate the list of resources with entries corresponding to the
        # supported resource types and scoped to the supplied resource type
        resources.resources = [
            ServiceConnectorTypedResourcesModel(
                resource_type=rt,
            )
            for rt in resource_types
        ]

        if self.has_expired():
            error = "the connector's authentication credentials have expired."
            # Log the error in the resources object
            resources.set_error(error)
            return resources

        verify_resource_types: List[Optional[str]] = []
        verify_resource_id = None
        if not list_resources and not resource_id:
            # If we're not listing resources, we're only verifying that the
            # connector can authenticate globally (i.e. without supplying a
            # resource type or resource ID). This is the same as if no resource
            # type or resource ID was supplied. The only exception is when the
            # verification scope is already set to a single resource ID, in
            # which case we still perform the verification on that resource ID.
            verify_resource_types = [None]
            verify_resource_id = None
        else:
            if len(resource_types) > 1:
                # This forces the connector to verify that it can authenticate
                # globally (i.e. without supplying a resource type or resource
                # ID) before listing individual resources in the case of
                # multi-type service connectors.
                verify_resource_types = [None]

            verify_resource_types.extend(resource_types)
            if len(verify_resource_types) == 1:
                verify_resource_id = resource_id

        # Here we go through each resource type and attempt to verify and list
        # the resources that the connector can access for that resource type.
        # This list may start with a `None` resource type, which indicates that
        # the connector should verify that it can authenticate globally.
        for resource_type in verify_resource_types:
            try:
                resource_type, resource_id = self.validate_runtime_args(
                    resource_type=resource_type,
                    resource_id=verify_resource_id,
                    require_resource_type=False,
                    require_resource_id=False,
                )

                resource_ids = self._verify(
                    resource_type=resource_type,
                    resource_id=resource_id,
                )
            except ValueError as exc:
                raise ValueError(
                    f"The connector configuration is incomplete or invalid: "
                    f"{exc}",
                )
            except AuthorizationException as exc:
                error = f"connector{name_msg} authorization failure: {exc}"
                # Log an exception if debug logging is enabled
                if logger.isEnabledFor(logging.DEBUG):
                    logger.exception(error)
                else:
                    logger.warning(error)

                # Log the error in the resources object
                resources.set_error(error, resource_type=resource_type)
                if resource_type:
                    continue
                else:
                    # We stop on a global failure
                    break
            except Exception as exc:
                error = (
                    f"connector{name_msg} verification failed with "
                    f"unexpected error: {exc}"
                )
                # Log an exception if debug logging is enabled
                if logger.isEnabledFor(logging.DEBUG):
                    logger.exception(error)
                else:
                    logger.warning(error)
                error = (
                    "an unexpected error occurred while verifying the "
                    "connector."
                )
                # Log the error in the resources object
                resources.set_error(error, resource_type=resource_type)
                if resource_type:
                    continue
                else:
                    # We stop on a global failure
                    break

            if not resource_type:
                # If a resource type is not provided as argument, we don't
                # expect any resources to be listed
                continue

            resource_type_spec = spec.resource_type_dict[resource_type]

            if resource_id:
                # A single resource was requested, so we expect a single
                # resource to be listed
                if [resource_id] != resource_ids:
                    logger.error(
                        f"a different resource ID '{resource_ids}' was "
                        f"returned than the one requested: {resource_ids}. "
                        f"This is likely a bug in the {self.__class__} "
                        "connector implementation."
                    )
                resources.set_resource_ids(resource_type, [resource_id])
            elif not resource_ids:
                # If no resources were listed, signal this as an error that the
                # connector cannot access any resources.
                error = (
                    f"connector{name_msg} didn't list any "
                    f"{resource_type_spec.name} resources. This is likely "
                    "caused by the connector credentials not being valid or "
                    "not having sufficient permissions to list or access "
                    "resources of this type. Please check the connector "
                    "configuration and its credentials and try again."
                )
                logger.debug(error)
                resources.set_error(error, resource_type=resource_type)
            else:
                resources.set_resource_ids(resource_type, resource_ids)

        return resources

    def get_connector_client(
        self,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> "ServiceConnector":
        """Get a connector client that can be used to connect to a resource.

        The connector client can be used by consumers to connect to a resource
        (i.e. make calls to `connect` and `configure_local_client`).

        The returned connector may be the same as the original connector
        or it may a different instance configured with different credentials or
        even of a different connector type.

        Args:
            resource_type: The type of the resource to connect to.
            resource_id: The ID of a particular resource to connect to.

        Returns:
            A service connector client that can be used to connect to the
            resource.

        Raises:
            AuthorizationException: If authentication failed.
        """
        resource_type, resource_id = self.validate_runtime_args(
            resource_type=resource_type,
            resource_id=resource_id,
            require_resource_type=True,
            require_resource_id=True,
        )

        if self.has_expired():
            raise AuthorizationException(
                "the connector's authentication credentials have expired."
            )

        # Verify if the connector allows access to the requested resource type
        # and instance.
        self._verify(
            resource_type=resource_type,
            resource_id=resource_id,
        )

        assert resource_type is not None
        assert resource_id is not None

        connector_client = self._get_connector_client(
            resource_type=resource_type,
            resource_id=resource_id,
        )
        # Transfer the expiration skew tolerance to the connector client
        # if an expiration time is set for the connector client credentials.
        if connector_client.expires_at is not None:
            connector_client.expires_skew_tolerance = (
                self.expires_skew_tolerance
            )

        if connector_client.has_expired():
            raise AuthorizationException(
                "the connector's authentication credentials have expired."
            )

        connector_client._verify(
            resource_type=resource_type,
            resource_id=connector_client.resource_id,
        )

        return connector_client
