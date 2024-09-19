# zenml.zen_server.deploy.local package

## Submodules

## zenml.zen_server.deploy.local.local_provider module

Zen Server local provider implementation.

### *class* zenml.zen_server.deploy.local.local_provider.LocalServerProvider

Bases: [`BaseServerProvider`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.base_provider.BaseServerProvider)

Local ZenML server provider.

#### CONFIG_TYPE

alias of [`LocalServerDeploymentConfig`](#zenml.zen_server.deploy.local.local_zen_server.LocalServerDeploymentConfig)

#### TYPE *: ClassVar[[ServerProviderType](zenml.md#zenml.enums.ServerProviderType)]* *= 'local'*

#### *static* check_local_server_dependencies() → None

Check if local server dependencies are installed.

Raises:
: RuntimeError: If the dependencies are not installed.

## zenml.zen_server.deploy.local.local_zen_server module

Local ZenML server deployment service implementation.

### *class* zenml.zen_server.deploy.local.local_zen_server.LocalServerDeploymentConfig(\*, name: str, provider: [ServerProviderType](zenml.md#zenml.enums.ServerProviderType), port: int = 8237, ip_address: Annotated[IPv4Address | IPv6Address, \_PydanticGeneralMetadata(union_mode='left_to_right')] = IPv4Address('127.0.0.1'), blocking: bool = False, store: [StoreConfiguration](zenml.config.md#zenml.config.store_config.StoreConfiguration) | None = None, use_legacy_dashboard: bool = False)

Bases: [`ServerDeploymentConfig`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployment.ServerDeploymentConfig)

Local server deployment configuration.

Attributes:
: port: The TCP port number where the server is accepting connections.
  address: The IP address where the server is reachable.
  blocking: Run the server in blocking mode instead of using a daemon
  <br/>
  > process.

#### blocking *: bool*

#### ip_address *: IPv4Address | IPv6Address*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'blocking': FieldInfo(annotation=bool, required=False, default=False), 'ip_address': FieldInfo(annotation=Union[IPv4Address, IPv6Address], required=False, default=IPv4Address('127.0.0.1'), metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'name': FieldInfo(annotation=str, required=True), 'port': FieldInfo(annotation=int, required=False, default=8237), 'provider': FieldInfo(annotation=ServerProviderType, required=True), 'store': FieldInfo(annotation=Union[StoreConfiguration, NoneType], required=False, default=None), 'use_legacy_dashboard': FieldInfo(annotation=bool, required=False, default=False)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### port *: int*

#### store *: [StoreConfiguration](zenml.config.md#zenml.config.store_config.StoreConfiguration) | None*

#### use_legacy_dashboard *: bool*

### *class* zenml.zen_server.deploy.local.local_zen_server.LocalZenServer(\*, type: Literal['zenml.zen_server.deploy.local.local_zen_server.LocalZenServer'] = 'zenml.zen_server.deploy.local.local_zen_server.LocalZenServer', uuid: UUID, admin_state: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, config: [LocalZenServerConfig](#zenml.zen_server.deploy.local.local_zen_server.LocalZenServerConfig), status: [LocalDaemonServiceStatus](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceStatus) = None, endpoint: [LocalDaemonServiceEndpoint](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpoint))

Bases: [`LocalDaemonService`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonService)

Service daemon that can be used to start a local ZenML Server.

Attributes:
: config: service configuration
  endpoint: optional service endpoint

#### SERVICE_TYPE *: ClassVar[[ServiceType](zenml.services.md#zenml.services.service_type.ServiceType)]* *= ServiceType(type='zen_server', flavor='local', name='local_zenml_server', description='Local ZenML server deployment', logo_url='')*

#### config *: [LocalZenServerConfig](#zenml.zen_server.deploy.local.local_zen_server.LocalZenServerConfig)*

#### *classmethod* config_path() → str

Path to the directory where the local ZenML server files are located.

Returns:
: Path to the local ZenML server runtime directory.

#### endpoint *: [LocalDaemonServiceEndpoint](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpoint)*

#### *classmethod* get_service() → [LocalZenServer](#zenml.zen_server.deploy.local.local_zen_server.LocalZenServer) | None

Load and return the local ZenML server service, if present.

Returns:
: The local ZenML server service or None, if the local server
  deployment is not found.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'admin_state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'config': FieldInfo(annotation=LocalZenServerConfig, required=True), 'endpoint': FieldInfo(annotation=LocalDaemonServiceEndpoint, required=True), 'status': FieldInfo(annotation=LocalDaemonServiceStatus, required=False, default_factory=LocalDaemonServiceStatus), 'type': FieldInfo(annotation=Literal['zenml.zen_server.deploy.local.local_zen_server.LocalZenServer'], required=False, default='zenml.zen_server.deploy.local.local_zen_server.LocalZenServer'), 'uuid': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### provision() → None

Provision the service.

#### run() → None

Run the ZenML Server.

Raises:
: ValueError: if started with a global configuration that connects to
  : another ZenML server.

#### start(timeout: int = 0) → None

Start the service and optionally wait for it to become active.

Args:
: timeout: amount of time to wait for the service to become active.
  : If set to 0, the method will return immediately after checking
    the service status.

#### type *: Literal['zenml.zen_server.deploy.local.local_zen_server.LocalZenServer']*

### *class* zenml.zen_server.deploy.local.local_zen_server.LocalZenServerConfig(\*, type: Literal['zenml.zen_server.deploy.local.local_zen_server.LocalZenServerConfig'] = 'zenml.zen_server.deploy.local.local_zen_server.LocalZenServerConfig', name: str = '', description: str = '', pipeline_name: str = '', pipeline_step_name: str = '', model_name: str = '', model_version: str = '', service_name: str = '', silent_daemon: bool = False, root_runtime_path: str | None = None, singleton: bool = False, blocking: bool = False, server: [LocalServerDeploymentConfig](#zenml.zen_server.deploy.local.local_zen_server.LocalServerDeploymentConfig))

Bases: [`LocalDaemonServiceConfig`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceConfig)

Local Zen server configuration.

Attributes:
: server: The deployment configuration.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'protected_namespaces': ()}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'blocking': FieldInfo(annotation=bool, required=False, default=False), 'description': FieldInfo(annotation=str, required=False, default=''), 'model_name': FieldInfo(annotation=str, required=False, default=''), 'model_version': FieldInfo(annotation=str, required=False, default=''), 'name': FieldInfo(annotation=str, required=False, default=''), 'pipeline_name': FieldInfo(annotation=str, required=False, default=''), 'pipeline_step_name': FieldInfo(annotation=str, required=False, default=''), 'root_runtime_path': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'server': FieldInfo(annotation=LocalServerDeploymentConfig, required=True), 'service_name': FieldInfo(annotation=str, required=False, default=''), 'silent_daemon': FieldInfo(annotation=bool, required=False, default=False), 'singleton': FieldInfo(annotation=bool, required=False, default=False), 'type': FieldInfo(annotation=Literal['zenml.zen_server.deploy.local.local_zen_server.LocalZenServerConfig'], required=False, default='zenml.zen_server.deploy.local.local_zen_server.LocalZenServerConfig')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### server *: [LocalServerDeploymentConfig](#zenml.zen_server.deploy.local.local_zen_server.LocalServerDeploymentConfig)*

#### type *: Literal['zenml.zen_server.deploy.local.local_zen_server.LocalZenServerConfig']*

## Module contents

ZenML Server Local Deployment.

### *class* zenml.zen_server.deploy.local.LocalServerProvider

Bases: [`BaseServerProvider`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.base_provider.BaseServerProvider)

Local ZenML server provider.

#### CONFIG_TYPE

alias of [`LocalServerDeploymentConfig`](#zenml.zen_server.deploy.local.local_zen_server.LocalServerDeploymentConfig)

#### TYPE *: ClassVar[[ServerProviderType](zenml.md#zenml.enums.ServerProviderType)]* *= 'local'*

#### *static* check_local_server_dependencies() → None

Check if local server dependencies are installed.

Raises:
: RuntimeError: If the dependencies are not installed.
