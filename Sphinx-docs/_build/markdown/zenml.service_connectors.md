# zenml.service_connectors package

## Submodules

## zenml.service_connectors.docker_service_connector module

Docker Service Connector.

The Docker Service Connector is responsible for authenticating with a Docker
(or compatible) registry.

### *class* zenml.service_connectors.docker_service_connector.DockerAuthenticationMethods(value, names=None, \*, module=None, qualname=None, type=None, start=1, boundary=None)

Bases: [`StrEnum`](zenml.utils.md#zenml.utils.enum_utils.StrEnum)

Docker Authentication methods.

#### PASSWORD *= 'password'*

### *class* zenml.service_connectors.docker_service_connector.DockerConfiguration(\*, username: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)], password: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)], registry: str | None = None)

Bases: [`DockerCredentials`](#zenml.service_connectors.docker_service_connector.DockerCredentials)

Docker client configuration.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'password': FieldInfo(annotation=SecretStr, required=True, title='Password', metadata=[PlainSerializer(func=<function <lambda>>, return_type=PydanticUndefined, when_used='json')]), 'registry': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Registry server URL. Omit to use DockerHub.'), 'username': FieldInfo(annotation=SecretStr, required=True, title='Username', metadata=[PlainSerializer(func=<function <lambda>>, return_type=PydanticUndefined, when_used='json')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### registry *: str | None*

### *class* zenml.service_connectors.docker_service_connector.DockerCredentials(\*, username: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)], password: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)])

Bases: [`AuthenticationConfig`](#zenml.service_connectors.service_connector.AuthenticationConfig)

Docker client authentication credentials.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'password': FieldInfo(annotation=SecretStr, required=True, title='Password', metadata=[PlainSerializer(func=<function <lambda>>, return_type=PydanticUndefined, when_used='json')]), 'username': FieldInfo(annotation=SecretStr, required=True, title='Username', metadata=[PlainSerializer(func=<function <lambda>>, return_type=PydanticUndefined, when_used='json')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### password *: <lambda>, return_type=PydanticUndefined, when_used=json)]*

#### username *: <lambda>, return_type=PydanticUndefined, when_used=json)]*

### *class* zenml.service_connectors.docker_service_connector.DockerServiceConnector(\*, id: UUID | None = None, name: str | None = None, auth_method: str, resource_type: str | None = None, resource_id: str | None = None, expires_at: datetime | None = None, expires_skew_tolerance: int | None = None, expiration_seconds: int | None = None, config: [DockerConfiguration](#zenml.service_connectors.docker_service_connector.DockerConfiguration), allow_implicit_auth_methods: bool = False)

Bases: [`ServiceConnector`](#zenml.service_connectors.service_connector.ServiceConnector)

Docker service connector.

#### config *: [DockerConfiguration](#zenml.service_connectors.docker_service_connector.DockerConfiguration)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'allow_implicit_auth_methods': FieldInfo(annotation=bool, required=False, default=False), 'auth_method': FieldInfo(annotation=str, required=True), 'config': FieldInfo(annotation=DockerConfiguration, required=True), 'expiration_seconds': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'expires_at': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None), 'expires_skew_tolerance': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'resource_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'resource_type': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

## zenml.service_connectors.service_connector module

Base ZenML Service Connector class.

### *class* zenml.service_connectors.service_connector.AuthenticationConfig

Bases: `BaseModel`

Base authentication configuration.

#### *property* all_values *: Dict[str, Any]*

Get all values as a dictionary.

Returns:
: A dictionary of all values in the configuration.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### *property* non_secret_values *: Dict[str, str]*

Get the non-secret values as a dictionary.

Returns:
: A dictionary of all non-secret values in the configuration.

#### *property* secret_values *: Dict[str, SecretStr]*

Get the secret values as a dictionary.

Returns:
: A dictionary of all secret values in the configuration.

### *class* zenml.service_connectors.service_connector.ServiceConnector(\*, id: UUID | None = None, name: str | None = None, auth_method: str, resource_type: str | None = None, resource_id: str | None = None, expires_at: datetime | None = None, expires_skew_tolerance: int | None = None, expiration_seconds: int | None = None, config: [AuthenticationConfig](#zenml.service_connectors.service_connector.AuthenticationConfig), allow_implicit_auth_methods: bool = False)

Bases: `BaseModel`

Base service connector class.

Service connectors are standalone components that can be used to link ZenML
to external resources. They are responsible for validating and storing
authentication configuration and sensitive credentials and for providing
authentication services to other ZenML components. Service connectors are
built on top of the (otherwise opaque) ZenML secrets and secrets store
mechanisms and add secret auto-configuration, secret discovery and secret
schema validation capabilities.

The implementation independent service connector abstraction is made
possible through the use of generic “resource types” and “resource IDs”.
These constitute the “contract” between connectors and the consumers of the
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

#### allow_implicit_auth_methods *: bool*

#### auth_method *: str*

#### *classmethod* auto_configure(auth_method: str | None = None, resource_type: str | None = None, resource_id: str | None = None, \*\*kwargs: Any) → [ServiceConnector](#zenml.service_connectors.service_connector.ServiceConnector) | None

Auto-configure a connector instance.

Instantiate a connector with a configuration extracted from the
authentication configuration available in the environment (e.g.
environment variables or local client/SDK configuration files).

Args:
: auth_method: The particular authentication method to use. If
  : omitted and if the connector implementation cannot decide which
    authentication method to use, it may raise an exception.
  <br/>
  resource_type: The type of resource to configure. If not specified,
  : the method returns a connector instance configured to access any
    of the supported resource types (multi-type connector) or
    configured to use a default resource type. If the connector
    doesn’t support multi-type configurations or if it cannot decide
    which resource type to use, it may raise an exception.
  <br/>
  resource_id: The ID of the resource instance to configure. The
  : connector implementation may choose to either require or ignore
    this parameter if it does not support or detect a resource type
    that supports multiple instances.
  <br/>
  kwargs: Additional implementation specific keyword arguments to use.

Returns:
: A connector instance configured with authentication credentials
  automatically extracted from the environment or None if
  auto-configuration is not supported.

Raises:
: ValueError: If the connector does not support the requested
  : authentication method or resource type.
  <br/>
  AuthorizationException: If the connector’s authentication
  : credentials have expired.

#### config *: [AuthenticationConfig](#zenml.service_connectors.service_connector.AuthenticationConfig)*

#### configure_local_client(\*\*kwargs: Any) → None

Configure a local client to authenticate and connect to a resource.

This method uses the connector’s configuration to configure a local
client or SDK installed on the localhost so that it can authenticate
and connect to the resource that the connector is configured to access.

The connector has to be fully configured for this method to succeed
(i.e. the connector’s configuration must be valid, a resource type must
be specified and the resource ID must be specified if the resource type
supports multiple instances). This method should only be called on a
connector client retrieved by calling get_connector_client on the
main service connector.

Args:
: kwargs: Additional implementation specific keyword arguments to use
  : to configure the client.

Raises:
: AuthorizationException: If the connector’s authentication
  : credentials have expired.

#### connect(verify: bool = True, \*\*kwargs: Any) → Any

Authenticate and connect to a resource.

Initialize and return an implementation specific object representing an
authenticated service client, connection or session that can be used
to access the resource that the connector is configured to access.

The connector has to be fully configured for this method to succeed
(i.e. the connector’s configuration must be valid, a resource type and
a resource ID must be configured). This method should only be called on
a connector client retrieved by calling get_connector_client on the
main service connector.

Args:
: verify: Whether to verify that the connector can access the
  : configured resource before connecting to it.
  <br/>
  kwargs: Additional implementation specific keyword arguments to use
  : to configure the client.

Returns:
: An implementation specific object representing the authenticated
  service client, connection or session.

Raises:
: AuthorizationException: If the connector’s authentication
  : credentials have expired.

#### expiration_seconds *: int | None*

#### expires_at *: datetime | None*

#### expires_skew_tolerance *: int | None*

#### *classmethod* from_model(model: [ServiceConnectorRequest](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorRequest) | [ServiceConnectorResponse](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorResponse)) → [ServiceConnector](#zenml.service_connectors.service_connector.ServiceConnector)

Creates a service connector instance from a service connector model.

Args:
: model: The service connector model.

Returns:
: The created service connector instance.

Raises:
: ValueError: If the connector configuration is invalid.

#### get_connector_client(resource_type: str | None = None, resource_id: str | None = None) → [ServiceConnector](#zenml.service_connectors.service_connector.ServiceConnector)

Get a connector client that can be used to connect to a resource.

The connector client can be used by consumers to connect to a resource
(i.e. make calls to connect and configure_local_client).

The returned connector may be the same as the original connector
or it may a different instance configured with different credentials or
even of a different connector type.

Args:
: resource_type: The type of the resource to connect to.
  resource_id: The ID of a particular resource to connect to.

Returns:
: A service connector client that can be used to connect to the
  resource.

Raises:
: AuthorizationException: If authentication failed.

#### *classmethod* get_type() → [ServiceConnectorTypeModel](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorTypeModel)

Get the connector type specification.

Returns:
: The connector type specification.

#### has_expired() → bool

Check if the connector authentication credentials have expired.

Verify that the authentication credentials associated with the connector
have not expired by checking the expiration time against the current
time.

Returns:
: True if the connector has expired, False otherwise.

#### id *: UUID | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'allow_implicit_auth_methods': FieldInfo(annotation=bool, required=False, default=False), 'auth_method': FieldInfo(annotation=str, required=True), 'config': FieldInfo(annotation=AuthenticationConfig, required=True), 'expiration_seconds': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'expires_at': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None), 'expires_skew_tolerance': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'resource_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'resource_type': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str | None*

#### resource_id *: str | None*

#### resource_type *: str | None*

#### *property* supported_resource_types *: List[str]*

The resource types supported by this connector instance.

Returns:
: A list with the resource types supported by this connector instance.

#### to_model(user: UUID, workspace: UUID, name: str | None = None, description: str = '', labels: Dict[str, str] | None = None) → [ServiceConnectorRequest](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorRequest)

Convert the connector instance to a service connector model.

Args:
: name: The name of the connector.
  user: The ID of the user that created the connector.
  workspace: The ID of the workspace that the connector belongs to.
  description: The description of the connector.
  labels: The labels of the connector.

Returns:
: The service connector model corresponding to the connector
  instance.

Raises:
: ValueError: If the connector configuration is not valid.

#### to_response_model(workspace: [WorkspaceResponse](zenml.models.v2.core.md#zenml.models.v2.core.workspace.WorkspaceResponse), user: [UserResponse](zenml.models.v2.core.md#zenml.models.v2.core.user.UserResponse) | None = None, name: str | None = None, id: UUID | None = None, description: str = '', labels: Dict[str, str] | None = None) → [ServiceConnectorResponse](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorResponse)

Convert the connector instance to a service connector response model.

Args:
: workspace: The workspace that the connector belongs to.
  user: The user that created the connector.
  name: The name of the connector.
  id: The ID of the connector.
  description: The description of the connector.
  labels: The labels of the connector.

Returns:
: The service connector response model corresponding to the connector
  instance.

Raises:
: ValueError: If the connector configuration is not valid.

#### *property* type *: [ServiceConnectorTypeModel](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorTypeModel)*

Get the connector type specification.

Returns:
: The connector type specification.

#### validate_runtime_args(resource_type: str | None, resource_id: str | None = None, require_resource_type: bool = False, require_resource_id: bool = False, \*\*kwargs: Any) → Tuple[str | None, str | None]

Validate the runtime arguments against the connector configuration.

Validate that the supplied runtime arguments are compatible with the
connector configuration and its specification. This includes validating
that the resource type and resource ID are compatible with the connector
configuration and its capabilities.

Args:
: resource_type: The type of the resource supplied at runtime by the
  : connector’s consumer. Must be the same as the resource type that
    the connector is configured to access, unless the connector is
    configured to access any resource type.
  <br/>
  resource_id: The ID of the resource requested by the connector’s
  : consumer. Can be different than the resource ID that the
    connector is configured to access, e.g. if it is not in the
    canonical form.
  <br/>
  require_resource_type: Whether the resource type is required.
  require_resource_id: Whether the resource ID is required.
  kwargs: Additional runtime arguments.

Returns:
: The validated resource type and resource ID.

Raises:
: ValueError: If the runtime arguments are not valid.

#### verify(resource_type: str | None = None, resource_id: str | None = None, list_resources: bool = True) → [ServiceConnectorResourcesModel](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorResourcesModel)

Verify and optionally list all the resources that the connector can access.

This method uses the connector’s configuration to verify that it can
authenticate and access the indicated resource(s).

If list_resources is set, the list of resources that the connector can
access, scoped to the supplied resource type and resource ID is included
in the response, otherwise the connector only verifies that it can
globally authenticate and doesn’t verify or return resource information
(i.e. the resource_ids fields in the response are empty).

Args:
: resource_type: The type of the resource to verify. If the connector
  : instance is already configured with a resource type, this
    argument must be the same as the one configured if supplied.
  <br/>
  resource_id: The ID of a particular resource instance to check
  : whether the connector can access. If the connector instance is
    already configured with a resource ID that is not the same or
    equivalent to the one requested, a ValueError exception is
    raised.
  <br/>
  list_resources: Whether to list the resources that the connector can
  : access.

Returns:
: A list of resources that the connector can access.

Raises:
: ValueError: If the arguments or the connector configuration are
  : not valid.

### *class* zenml.service_connectors.service_connector.ServiceConnectorMeta(name: str, bases: Tuple[Type[Any], ...], dct: Dict[str, Any])

Bases: `ModelMetaclass`

Metaclass responsible for automatically registering ServiceConnector classes.

## zenml.service_connectors.service_connector_registry module

Implementation of a service connector registry.

### *class* zenml.service_connectors.service_connector_registry.ServiceConnectorRegistry

Bases: `object`

Service connector registry.

#### get_service_connector_type(connector_type: str) → [ServiceConnectorTypeModel](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorTypeModel)

Get a service connector type by its connector type identifier.

Args:
: connector_type: The service connector type identifier.

Returns:
: A service connector type that was registered for the given
  connector type identifier.

Raises:
: KeyError: If no service connector was registered for the given type
  : identifier.

#### instantiate_connector(model: [ServiceConnectorRequest](zenml.models.md#zenml.models.ServiceConnectorRequest) | [ServiceConnectorResponse](zenml.models.md#zenml.models.ServiceConnectorResponse)) → [ServiceConnector](#zenml.service_connectors.service_connector.ServiceConnector)

Validate a service connector model and create an instance from it.

Args:
: model: The service connector model to validate and instantiate.

Returns:
: A service connector instance.

Raises:
: NotImplementedError: If no service connector is registered for the
  : given type identifier.
  <br/>
  ValueError: If the service connector model is not valid.

#### is_registered(connector_type: str) → bool

Returns if a service connector is registered for the given type identifier.

Args:
: connector_type: The service connector type identifier.

Returns:
: True if a service connector is registered for the given type
  identifier, False otherwise.

#### list_service_connector_types(connector_type: str | None = None, resource_type: str | None = None, auth_method: str | None = None) → List[[ServiceConnectorTypeModel](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorTypeModel)]

Find one or more service connector types that match the given criteria.

Args:
: connector_type: Filter by service connector type identifier.
  resource_type: Filter by a resource type that the connector can
  <br/>
  > be used to give access to.
  <br/>
  auth_method: Filter by an authentication method that the connector
  : uses to authenticate with the resource provider.

Returns:
: A list of service connector type models that match the given
  criteria.

#### register_builtin_service_connectors() → None

Registers the default built-in service connectors.

#### register_service_connector_type(service_connector_type: [ServiceConnectorTypeModel](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorTypeModel), overwrite: bool = False) → None

Registers a service connector type.

Args:
: service_connector_type: Service connector type.
  overwrite: Whether to overwrite an existing service connector type.

## zenml.service_connectors.service_connector_utils module

Utility methods for Service Connectors.

### zenml.service_connectors.service_connector_utils.get_resources_options_from_resource_model_for_full_stack(connector_details: UUID | [ServiceConnectorInfo](zenml.models.v2.misc.md#zenml.models.v2.misc.info_models.ServiceConnectorInfo)) → [ServiceConnectorResourcesInfo](zenml.models.v2.misc.md#zenml.models.v2.misc.info_models.ServiceConnectorResourcesInfo)

Get the resource options from the resource model for the full stack.

Args:
: connector_details: The service connector details (UUID or Info).

Returns:
: All available service connector resource options.

## Module contents

ZenML Service Connectors.
