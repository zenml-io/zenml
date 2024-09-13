# zenml.zen_server.deploy.docker package

## Submodules

## zenml.zen_server.deploy.docker.docker_provider module

Zen Server docker deployer implementation.

### *class* zenml.zen_server.deploy.docker.docker_provider.DockerServerProvider

Bases: [`BaseServerProvider`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.base_provider.BaseServerProvider)

Docker ZenML server provider.

#### CONFIG_TYPE

alias of [`DockerServerDeploymentConfig`](#zenml.zen_server.deploy.docker.docker_zen_server.DockerServerDeploymentConfig)

#### TYPE *: ClassVar[[ServerProviderType](zenml.md#zenml.enums.ServerProviderType)]* *= 'docker'*

## zenml.zen_server.deploy.docker.docker_zen_server module

Service implementation for the ZenML docker server deployment.

### *class* zenml.zen_server.deploy.docker.docker_zen_server.DockerServerDeploymentConfig(\*, name: str, provider: [ServerProviderType](zenml.md#zenml.enums.ServerProviderType), port: int = 8238, image: str = 'zenmldocker/zenml-server:0.66.0', store: [StoreConfiguration](zenml.config.md#zenml.config.store_config.StoreConfiguration) | None = None, use_legacy_dashboard: bool = False)

Bases: [`ServerDeploymentConfig`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployment.ServerDeploymentConfig)

Docker server deployment configuration.

Attributes:
: port: The TCP port number where the server is accepting connections.
  image: The Docker image to use for the server.

#### image *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'image': FieldInfo(annotation=str, required=False, default='zenmldocker/zenml-server:0.66.0'), 'name': FieldInfo(annotation=str, required=True), 'port': FieldInfo(annotation=int, required=False, default=8238), 'provider': FieldInfo(annotation=ServerProviderType, required=True), 'store': FieldInfo(annotation=Union[StoreConfiguration, NoneType], required=False, default=None), 'use_legacy_dashboard': FieldInfo(annotation=bool, required=False, default=False)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### port *: int*

#### store *: [StoreConfiguration](zenml.config.md#zenml.config.store_config.StoreConfiguration) | None*

#### use_legacy_dashboard *: bool*

### *class* zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServer(\*, type: Literal['zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServer'] = 'zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServer', uuid: UUID, admin_state: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, config: [DockerZenServerConfig](#zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServerConfig), status: [ContainerServiceStatus](zenml.services.container.md#zenml.services.container.container_service.ContainerServiceStatus) = None, endpoint: [ContainerServiceEndpoint](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpoint))

Bases: [`ContainerService`](zenml.services.container.md#zenml.services.container.container_service.ContainerService)

Service that can be used to start a docker ZenServer.

Attributes:
: config: service configuration
  endpoint: service endpoint

#### SERVICE_TYPE *: ClassVar[[ServiceType](zenml.services.md#zenml.services.service_type.ServiceType)]* *= ServiceType(type='zen_server', flavor='docker', name='docker_zenml_server', description='Docker ZenML server deployment', logo_url='')*

#### config *: [DockerZenServerConfig](#zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServerConfig)*

#### *classmethod* config_path() → str

Path to the directory where the docker ZenML server files are located.

Returns:
: Path to the docker ZenML server runtime directory.

#### endpoint *: [ContainerServiceEndpoint](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpoint)*

#### *classmethod* get_service() → [DockerZenServer](#zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServer) | None

Load and return the docker ZenML server service, if present.

Returns:
: The docker ZenML server service or None, if the docker server
  deployment is not found.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'admin_state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'config': FieldInfo(annotation=DockerZenServerConfig, required=True), 'endpoint': FieldInfo(annotation=ContainerServiceEndpoint, required=True), 'status': FieldInfo(annotation=ContainerServiceStatus, required=False, default_factory=ContainerServiceStatus), 'type': FieldInfo(annotation=Literal['zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServer'], required=False, default='zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServer'), 'uuid': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### provision() → None

Provision the service.

#### run() → None

Run the ZenML Server.

Raises:
: ValueError: if started with a global configuration that connects to
  : another ZenML server.

#### type *: Literal['zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServer']*

### *class* zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServerConfig(\*, type: Literal['zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServerConfig'] = 'zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServerConfig', name: str = '', description: str = '', pipeline_name: str = '', pipeline_step_name: str = '', model_name: str = '', model_version: str = '', service_name: str = '', root_runtime_path: str | None = None, singleton: bool = False, image: str = 'zenmldocker/zenml', server: [DockerServerDeploymentConfig](#zenml.zen_server.deploy.docker.docker_zen_server.DockerServerDeploymentConfig))

Bases: [`ContainerServiceConfig`](zenml.services.container.md#zenml.services.container.container_service.ContainerServiceConfig)

Docker Zen server configuration.

Attributes:
: server: The deployment configuration.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'protected_namespaces': ()}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'description': FieldInfo(annotation=str, required=False, default=''), 'image': FieldInfo(annotation=str, required=False, default='zenmldocker/zenml'), 'model_name': FieldInfo(annotation=str, required=False, default=''), 'model_version': FieldInfo(annotation=str, required=False, default=''), 'name': FieldInfo(annotation=str, required=False, default=''), 'pipeline_name': FieldInfo(annotation=str, required=False, default=''), 'pipeline_step_name': FieldInfo(annotation=str, required=False, default=''), 'root_runtime_path': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'server': FieldInfo(annotation=DockerServerDeploymentConfig, required=True), 'service_name': FieldInfo(annotation=str, required=False, default=''), 'singleton': FieldInfo(annotation=bool, required=False, default=False), 'type': FieldInfo(annotation=Literal['zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServerConfig'], required=False, default='zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServerConfig')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### server *: [DockerServerDeploymentConfig](#zenml.zen_server.deploy.docker.docker_zen_server.DockerServerDeploymentConfig)*

#### type *: Literal['zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServerConfig']*

## Module contents

ZenML Server Docker Deployment.

### *class* zenml.zen_server.deploy.docker.DockerServerProvider

Bases: [`BaseServerProvider`](zenml.zen_server.deploy.md#zenml.zen_server.deploy.base_provider.BaseServerProvider)

Docker ZenML server provider.

#### CONFIG_TYPE

alias of [`DockerServerDeploymentConfig`](#zenml.zen_server.deploy.docker.docker_zen_server.DockerServerDeploymentConfig)

#### TYPE *: ClassVar[[ServerProviderType](zenml.md#zenml.enums.ServerProviderType)]* *= 'docker'*
