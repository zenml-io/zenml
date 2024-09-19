# zenml.zen_server.deploy package

## Subpackages

* [zenml.zen_server.deploy.docker package](zenml.zen_server.deploy.docker.md)
  * [Submodules](zenml.zen_server.deploy.docker.md#submodules)
  * [zenml.zen_server.deploy.docker.docker_provider module](zenml.zen_server.deploy.docker.md#module-zenml.zen_server.deploy.docker.docker_provider)
    * [`DockerServerProvider`](zenml.zen_server.deploy.docker.md#zenml.zen_server.deploy.docker.docker_provider.DockerServerProvider)
      * [`DockerServerProvider.CONFIG_TYPE`](zenml.zen_server.deploy.docker.md#zenml.zen_server.deploy.docker.docker_provider.DockerServerProvider.CONFIG_TYPE)
      * [`DockerServerProvider.TYPE`](zenml.zen_server.deploy.docker.md#zenml.zen_server.deploy.docker.docker_provider.DockerServerProvider.TYPE)
  * [zenml.zen_server.deploy.docker.docker_zen_server module](zenml.zen_server.deploy.docker.md#module-zenml.zen_server.deploy.docker.docker_zen_server)
    * [`DockerServerDeploymentConfig`](zenml.zen_server.deploy.docker.md#zenml.zen_server.deploy.docker.docker_zen_server.DockerServerDeploymentConfig)
      * [`DockerServerDeploymentConfig.image`](zenml.zen_server.deploy.docker.md#zenml.zen_server.deploy.docker.docker_zen_server.DockerServerDeploymentConfig.image)
      * [`DockerServerDeploymentConfig.model_computed_fields`](zenml.zen_server.deploy.docker.md#zenml.zen_server.deploy.docker.docker_zen_server.DockerServerDeploymentConfig.model_computed_fields)
      * [`DockerServerDeploymentConfig.model_config`](zenml.zen_server.deploy.docker.md#zenml.zen_server.deploy.docker.docker_zen_server.DockerServerDeploymentConfig.model_config)
      * [`DockerServerDeploymentConfig.model_fields`](zenml.zen_server.deploy.docker.md#zenml.zen_server.deploy.docker.docker_zen_server.DockerServerDeploymentConfig.model_fields)
      * [`DockerServerDeploymentConfig.port`](zenml.zen_server.deploy.docker.md#zenml.zen_server.deploy.docker.docker_zen_server.DockerServerDeploymentConfig.port)
      * [`DockerServerDeploymentConfig.store`](zenml.zen_server.deploy.docker.md#zenml.zen_server.deploy.docker.docker_zen_server.DockerServerDeploymentConfig.store)
      * [`DockerServerDeploymentConfig.use_legacy_dashboard`](zenml.zen_server.deploy.docker.md#zenml.zen_server.deploy.docker.docker_zen_server.DockerServerDeploymentConfig.use_legacy_dashboard)
    * [`DockerZenServer`](zenml.zen_server.deploy.docker.md#zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServer)
      * [`DockerZenServer.SERVICE_TYPE`](zenml.zen_server.deploy.docker.md#zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServer.SERVICE_TYPE)
      * [`DockerZenServer.config`](zenml.zen_server.deploy.docker.md#zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServer.config)
      * [`DockerZenServer.config_path()`](zenml.zen_server.deploy.docker.md#zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServer.config_path)
      * [`DockerZenServer.endpoint`](zenml.zen_server.deploy.docker.md#zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServer.endpoint)
      * [`DockerZenServer.get_service()`](zenml.zen_server.deploy.docker.md#zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServer.get_service)
      * [`DockerZenServer.model_computed_fields`](zenml.zen_server.deploy.docker.md#zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServer.model_computed_fields)
      * [`DockerZenServer.model_config`](zenml.zen_server.deploy.docker.md#zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServer.model_config)
      * [`DockerZenServer.model_fields`](zenml.zen_server.deploy.docker.md#zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServer.model_fields)
      * [`DockerZenServer.model_post_init()`](zenml.zen_server.deploy.docker.md#zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServer.model_post_init)
      * [`DockerZenServer.provision()`](zenml.zen_server.deploy.docker.md#zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServer.provision)
      * [`DockerZenServer.run()`](zenml.zen_server.deploy.docker.md#zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServer.run)
      * [`DockerZenServer.type`](zenml.zen_server.deploy.docker.md#zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServer.type)
    * [`DockerZenServerConfig`](zenml.zen_server.deploy.docker.md#zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServerConfig)
      * [`DockerZenServerConfig.model_computed_fields`](zenml.zen_server.deploy.docker.md#zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServerConfig.model_computed_fields)
      * [`DockerZenServerConfig.model_config`](zenml.zen_server.deploy.docker.md#zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServerConfig.model_config)
      * [`DockerZenServerConfig.model_fields`](zenml.zen_server.deploy.docker.md#zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServerConfig.model_fields)
      * [`DockerZenServerConfig.server`](zenml.zen_server.deploy.docker.md#zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServerConfig.server)
      * [`DockerZenServerConfig.type`](zenml.zen_server.deploy.docker.md#zenml.zen_server.deploy.docker.docker_zen_server.DockerZenServerConfig.type)
  * [Module contents](zenml.zen_server.deploy.docker.md#module-zenml.zen_server.deploy.docker)
    * [`DockerServerProvider`](zenml.zen_server.deploy.docker.md#zenml.zen_server.deploy.docker.DockerServerProvider)
      * [`DockerServerProvider.CONFIG_TYPE`](zenml.zen_server.deploy.docker.md#zenml.zen_server.deploy.docker.DockerServerProvider.CONFIG_TYPE)
      * [`DockerServerProvider.TYPE`](zenml.zen_server.deploy.docker.md#zenml.zen_server.deploy.docker.DockerServerProvider.TYPE)
* [zenml.zen_server.deploy.local package](zenml.zen_server.deploy.local.md)
  * [Submodules](zenml.zen_server.deploy.local.md#submodules)
  * [zenml.zen_server.deploy.local.local_provider module](zenml.zen_server.deploy.local.md#module-zenml.zen_server.deploy.local.local_provider)
    * [`LocalServerProvider`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.local_provider.LocalServerProvider)
      * [`LocalServerProvider.CONFIG_TYPE`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.local_provider.LocalServerProvider.CONFIG_TYPE)
      * [`LocalServerProvider.TYPE`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.local_provider.LocalServerProvider.TYPE)
      * [`LocalServerProvider.check_local_server_dependencies()`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.local_provider.LocalServerProvider.check_local_server_dependencies)
  * [zenml.zen_server.deploy.local.local_zen_server module](zenml.zen_server.deploy.local.md#module-zenml.zen_server.deploy.local.local_zen_server)
    * [`LocalServerDeploymentConfig`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.local_zen_server.LocalServerDeploymentConfig)
      * [`LocalServerDeploymentConfig.blocking`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.local_zen_server.LocalServerDeploymentConfig.blocking)
      * [`LocalServerDeploymentConfig.ip_address`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.local_zen_server.LocalServerDeploymentConfig.ip_address)
      * [`LocalServerDeploymentConfig.model_computed_fields`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.local_zen_server.LocalServerDeploymentConfig.model_computed_fields)
      * [`LocalServerDeploymentConfig.model_config`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.local_zen_server.LocalServerDeploymentConfig.model_config)
      * [`LocalServerDeploymentConfig.model_fields`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.local_zen_server.LocalServerDeploymentConfig.model_fields)
      * [`LocalServerDeploymentConfig.port`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.local_zen_server.LocalServerDeploymentConfig.port)
      * [`LocalServerDeploymentConfig.store`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.local_zen_server.LocalServerDeploymentConfig.store)
      * [`LocalServerDeploymentConfig.use_legacy_dashboard`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.local_zen_server.LocalServerDeploymentConfig.use_legacy_dashboard)
    * [`LocalZenServer`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.local_zen_server.LocalZenServer)
      * [`LocalZenServer.SERVICE_TYPE`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.local_zen_server.LocalZenServer.SERVICE_TYPE)
      * [`LocalZenServer.config`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.local_zen_server.LocalZenServer.config)
      * [`LocalZenServer.config_path()`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.local_zen_server.LocalZenServer.config_path)
      * [`LocalZenServer.endpoint`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.local_zen_server.LocalZenServer.endpoint)
      * [`LocalZenServer.get_service()`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.local_zen_server.LocalZenServer.get_service)
      * [`LocalZenServer.model_computed_fields`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.local_zen_server.LocalZenServer.model_computed_fields)
      * [`LocalZenServer.model_config`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.local_zen_server.LocalZenServer.model_config)
      * [`LocalZenServer.model_fields`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.local_zen_server.LocalZenServer.model_fields)
      * [`LocalZenServer.provision()`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.local_zen_server.LocalZenServer.provision)
      * [`LocalZenServer.run()`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.local_zen_server.LocalZenServer.run)
      * [`LocalZenServer.start()`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.local_zen_server.LocalZenServer.start)
      * [`LocalZenServer.type`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.local_zen_server.LocalZenServer.type)
    * [`LocalZenServerConfig`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.local_zen_server.LocalZenServerConfig)
      * [`LocalZenServerConfig.model_computed_fields`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.local_zen_server.LocalZenServerConfig.model_computed_fields)
      * [`LocalZenServerConfig.model_config`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.local_zen_server.LocalZenServerConfig.model_config)
      * [`LocalZenServerConfig.model_fields`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.local_zen_server.LocalZenServerConfig.model_fields)
      * [`LocalZenServerConfig.server`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.local_zen_server.LocalZenServerConfig.server)
      * [`LocalZenServerConfig.type`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.local_zen_server.LocalZenServerConfig.type)
  * [Module contents](zenml.zen_server.deploy.local.md#module-zenml.zen_server.deploy.local)
    * [`LocalServerProvider`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.LocalServerProvider)
      * [`LocalServerProvider.CONFIG_TYPE`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.LocalServerProvider.CONFIG_TYPE)
      * [`LocalServerProvider.TYPE`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.LocalServerProvider.TYPE)
      * [`LocalServerProvider.check_local_server_dependencies()`](zenml.zen_server.deploy.local.md#zenml.zen_server.deploy.local.LocalServerProvider.check_local_server_dependencies)
* [zenml.zen_server.deploy.terraform package](zenml.zen_server.deploy.terraform.md)
  * [Subpackages](zenml.zen_server.deploy.terraform.md#subpackages)
    * [zenml.zen_server.deploy.terraform.providers package](zenml.zen_server.deploy.terraform.providers.md)
      * [Submodules](zenml.zen_server.deploy.terraform.providers.md#submodules)
      * [zenml.zen_server.deploy.terraform.providers.aws_provider module](zenml.zen_server.deploy.terraform.providers.md#zenml-zen-server-deploy-terraform-providers-aws-provider-module)
      * [zenml.zen_server.deploy.terraform.providers.azure_provider module](zenml.zen_server.deploy.terraform.providers.md#zenml-zen-server-deploy-terraform-providers-azure-provider-module)
      * [zenml.zen_server.deploy.terraform.providers.gcp_provider module](zenml.zen_server.deploy.terraform.providers.md#zenml-zen-server-deploy-terraform-providers-gcp-provider-module)
      * [zenml.zen_server.deploy.terraform.providers.terraform_provider module](zenml.zen_server.deploy.terraform.providers.md#zenml-zen-server-deploy-terraform-providers-terraform-provider-module)
      * [Module contents](zenml.zen_server.deploy.terraform.providers.md#module-zenml.zen_server.deploy.terraform.providers)
  * [Submodules](zenml.zen_server.deploy.terraform.md#submodules)
  * [zenml.zen_server.deploy.terraform.terraform_zen_server module](zenml.zen_server.deploy.terraform.md#zenml-zen-server-deploy-terraform-terraform-zen-server-module)
  * [Module contents](zenml.zen_server.deploy.terraform.md#module-contents)

## Submodules

## zenml.zen_server.deploy.base_provider module

Base ZenML server provider class.

### *class* zenml.zen_server.deploy.base_provider.BaseServerProvider

Bases: `ABC`

Base ZenML server provider class.

All ZenML server providers must extend and implement this base class.

#### CONFIG_TYPE

alias of [`ServerDeploymentConfig`](#zenml.zen_server.deploy.deployment.ServerDeploymentConfig)

#### TYPE *: ClassVar[[ServerProviderType](zenml.md#zenml.enums.ServerProviderType)]*

#### deploy_server(config: [ServerDeploymentConfig](#zenml.zen_server.deploy.deployment.ServerDeploymentConfig), timeout: int | None = None) → [ServerDeployment](#zenml.zen_server.deploy.deployment.ServerDeployment)

Deploy a new ZenML server.

Args:
: config: The generic server deployment configuration.
  timeout: The timeout in seconds to wait until the deployment is
  <br/>
  > successful. If not supplied, the default timeout value specified
  > by the provider is used.

Returns:
: The newly created server deployment.

Raises:
: ServerDeploymentExistsError: If a deployment with the same name
  : already exists.

#### get_server(config: [ServerDeploymentConfig](#zenml.zen_server.deploy.deployment.ServerDeploymentConfig)) → [ServerDeployment](#zenml.zen_server.deploy.deployment.ServerDeployment)

Retrieve information about a ZenML server deployment.

Args:
: config: The generic server deployment configuration.

Returns:
: The server deployment.

Raises:
: ServerDeploymentNotFoundError: If a deployment with the given name
  : doesn’t exist.

#### get_server_logs(config: [ServerDeploymentConfig](#zenml.zen_server.deploy.deployment.ServerDeploymentConfig), follow: bool = False, tail: int | None = None) → Generator[str, bool, None]

Retrieve the logs of a ZenML server.

Args:
: config: The generic server deployment configuration.
  follow: if True, the logs will be streamed as they are written
  tail: only retrieve the last NUM lines of log output.

Returns:
: A generator that can be accessed to get the service logs.

Raises:
: ServerDeploymentNotFoundError: If a deployment with the given name
  : doesn’t exist.

#### list_servers() → List[[ServerDeployment](#zenml.zen_server.deploy.deployment.ServerDeployment)]

List all server deployments managed by this provider.

Returns:
: The list of server deployments.

#### *classmethod* register_as_provider() → None

Register the class as a server provider.

#### remove_server(config: [ServerDeploymentConfig](#zenml.zen_server.deploy.deployment.ServerDeploymentConfig), timeout: int | None = None) → None

Tears down and removes all resources and files associated with a ZenML server deployment.

Args:
: config: The generic server deployment configuration.
  timeout: The timeout in seconds to wait until the server is
  <br/>
  > removed. If not supplied, the default timeout value specified
  > by the provider is used.

Raises:
: ServerDeploymentNotFoundError: If a deployment with the given name
  : doesn’t exist.

#### update_server(config: [ServerDeploymentConfig](#zenml.zen_server.deploy.deployment.ServerDeploymentConfig), timeout: int | None = None) → [ServerDeployment](#zenml.zen_server.deploy.deployment.ServerDeployment)

Update an existing ZenML server deployment.

Args:
: config: The new generic server deployment configuration.
  timeout: The timeout in seconds to wait until the update is
  <br/>
  > successful. If not supplied, the default timeout value specified
  > by the provider is used.

Returns:
: The updated server deployment.

Raises:
: ServerDeploymentNotFoundError: If a deployment with the given name
  : doesn’t exist.

## zenml.zen_server.deploy.deployer module

ZenML server deployer singleton implementation.

### *class* zenml.zen_server.deploy.deployer.ServerDeployer(\*args: Any, \*\*kwargs: Any)

Bases: `object`

Server deployer singleton.

This class is responsible for managing the various server provider
implementations and for directing server deployment lifecycle requests to
the responsible provider. It acts as a facade built on top of the various
server providers.

#### connect_to_server(server_name: str, username: str, password: str, verify_ssl: bool | str = True) → None

Connect to a ZenML server instance.

Args:
: server_name: The server deployment name.
  username: The username to use to connect to the server.
  password: The password to use to connect to the server.
  verify_ssl: Either a boolean, in which case it controls whether we
  <br/>
  > verify the server’s TLS certificate, or a string, in which case
  > it must be a path to a CA bundle to use or the CA bundle value
  > itself.

Raises:
: ServerDeploymentError: If the ZenML server is not running or
  : is unreachable.

#### deploy_server(config: [ServerDeploymentConfig](#zenml.zen_server.deploy.deployment.ServerDeploymentConfig), timeout: int | None = None) → [ServerDeployment](#zenml.zen_server.deploy.deployment.ServerDeployment)

Deploy a new ZenML server or update an existing deployment.

Args:
: config: The server deployment configuration.
  timeout: The timeout in seconds to wait until the deployment is
  <br/>
  > successful. If not supplied, the default timeout value specified
  > by the provider is used.

Returns:
: The server deployment.

#### disconnect_from_server(server_name: str | None = None) → None

Disconnect from a ZenML server instance.

Args:
: server_name: The server deployment name. If supplied, the deployer
  : will check if the ZenML client is indeed connected to the server
    and disconnect only if that is the case. Otherwise the deployer
    will disconnect from any ZenML server.

#### *classmethod* get_provider(provider_type: [ServerProviderType](zenml.md#zenml.enums.ServerProviderType)) → [BaseServerProvider](#zenml.zen_server.deploy.base_provider.BaseServerProvider)

Get the server provider associated with a provider type.

Args:
: provider_type: The server provider type.

Returns:
: The server provider associated with the provider type.

Raises:
: ServerProviderNotFoundError: If no provider is registered for the
  : given provider type.

#### get_server(server_name: str) → [ServerDeployment](#zenml.zen_server.deploy.deployment.ServerDeployment)

Get a server deployment.

Args:
: server_name: The server deployment name.

Returns:
: The requested server deployment.

Raises:
: ServerDeploymentNotFoundError: If no server deployment with the
  : given name is found.

#### get_server_logs(server_name: str, follow: bool = False, tail: int | None = None) → Generator[str, bool, None]

Retrieve the logs of a ZenML server.

Args:
: server_name: The server deployment name.
  follow: if True, the logs will be streamed as they are written
  tail: only retrieve the last NUM lines of log output.

Returns:
: A generator that can be accessed to get the service logs.

#### is_connected_to_server(server_name: str) → bool

Check if the ZenML client is currently connected to a ZenML server.

Args:
: server_name: The server deployment name.

Returns:
: True if the ZenML client is connected to the ZenML server, False
  otherwise.

#### list_servers(server_name: str | None = None, provider_type: [ServerProviderType](zenml.md#zenml.enums.ServerProviderType) | None = None) → List[[ServerDeployment](#zenml.zen_server.deploy.deployment.ServerDeployment)]

List all server deployments.

Args:
: server_name: The server deployment name to filter by.
  provider_type: The server provider type to filter by.

Returns:
: The list of server deployments.

#### *classmethod* register_provider(provider: Type[[BaseServerProvider](#zenml.zen_server.deploy.base_provider.BaseServerProvider)]) → None

Register a server provider.

Args:
: provider: The server provider to register.

Raises:
: TypeError: If a provider with the same type is already registered.

#### remove_server(server_name: str, timeout: int | None = None) → None

Tears down and removes all resources and files associated with a ZenML server deployment.

Args:
: server_name: The server deployment name.
  timeout: The timeout in seconds to wait until the deployment is
  <br/>
  > successfully torn down. If not supplied, a provider specific
  > default timeout value is used.

#### update_server(config: [ServerDeploymentConfig](#zenml.zen_server.deploy.deployment.ServerDeploymentConfig), timeout: int | None = None) → [ServerDeployment](#zenml.zen_server.deploy.deployment.ServerDeployment)

Update an existing ZenML server deployment.

Args:
: config: The new server deployment configuration.
  timeout: The timeout in seconds to wait until the deployment is
  <br/>
  > successful. If not supplied, a default timeout value of 30
  > seconds is used.

Returns:
: The updated server deployment.

Raises:
: ServerDeploymentExistsError: If an existing deployment with the same
  : name but a different provider type is found.

## zenml.zen_server.deploy.deployment module

Zen Server deployment definitions.

### *class* zenml.zen_server.deploy.deployment.ServerDeployment(\*, config: [ServerDeploymentConfig](#zenml.zen_server.deploy.deployment.ServerDeploymentConfig), status: [ServerDeploymentStatus](#zenml.zen_server.deploy.deployment.ServerDeploymentStatus) | None = None)

Bases: `BaseModel`

Server deployment.

Attributes:
: config: The server deployment configuration.
  status: The server deployment status.

#### config *: [ServerDeploymentConfig](#zenml.zen_server.deploy.deployment.ServerDeploymentConfig)*

#### *property* is_running *: bool*

Check if the server is running.

Returns:
: Whether the server is running.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'config': FieldInfo(annotation=ServerDeploymentConfig, required=True), 'status': FieldInfo(annotation=Union[ServerDeploymentStatus, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### status *: [ServerDeploymentStatus](#zenml.zen_server.deploy.deployment.ServerDeploymentStatus) | None*

### *class* zenml.zen_server.deploy.deployment.ServerDeploymentConfig(\*, name: str, provider: [ServerProviderType](zenml.md#zenml.enums.ServerProviderType), \*\*extra_data: Any)

Bases: `BaseModel`

Generic server deployment configuration.

All server deployment configurations should inherit from this class and
handle extra attributes as provider specific attributes.

Attributes:
: name: Name of the server deployment.
  provider: The server provider type.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'name': FieldInfo(annotation=str, required=True), 'provider': FieldInfo(annotation=ServerProviderType, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### provider *: [ServerProviderType](zenml.md#zenml.enums.ServerProviderType)*

### *class* zenml.zen_server.deploy.deployment.ServerDeploymentStatus(\*, status: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState), status_message: str | None = None, connected: bool, url: str | None = None, ca_crt: str | None = None)

Bases: `BaseModel`

Server deployment status.

Ideally this should convey the following information:

* whether the server’s deployment is managed by this client (i.e. if

the server was deployed with zenml up)
\* for a managed deployment, the status of the deployment/tear-down, e.g.
not deployed, deploying, running, deleting, deployment timeout/error,
tear-down timeout/error etc.
\* for an unmanaged deployment, the operational status (i.e. whether the
server is reachable)
\* the URL of the server

Attributes:
: status: The status of the server deployment.
  status_message: A message describing the last status.
  connected: Whether the client is currently connected to this server.
  url: The URL of the server.

#### ca_crt *: str | None*

#### connected *: bool*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'ca_crt': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'connected': FieldInfo(annotation=bool, required=True), 'status': FieldInfo(annotation=ServiceState, required=True), 'status_message': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### status *: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState)*

#### status_message *: str | None*

#### url *: str | None*

## zenml.zen_server.deploy.exceptions module

ZenML server deployment exceptions.

### *exception* zenml.zen_server.deploy.exceptions.ServerDeploymentConfigurationError(message: str | None = None, url: str | None = None)

Bases: [`ServerDeploymentError`](#zenml.zen_server.deploy.exceptions.ServerDeploymentError)

Raised when there is a ZenML server deployment configuration error .

### *exception* zenml.zen_server.deploy.exceptions.ServerDeploymentError(message: str | None = None, url: str | None = None)

Bases: [`ZenMLBaseException`](zenml.md#zenml.exceptions.ZenMLBaseException)

Base exception class for all ZenML server deployment related errors.

### *exception* zenml.zen_server.deploy.exceptions.ServerDeploymentExistsError(message: str | None = None, url: str | None = None)

Bases: [`ServerDeploymentError`](#zenml.zen_server.deploy.exceptions.ServerDeploymentError)

Raised when trying to deploy a new ZenML server with the same name.

### *exception* zenml.zen_server.deploy.exceptions.ServerDeploymentNotFoundError(message: str | None = None, url: str | None = None)

Bases: [`ServerDeploymentError`](#zenml.zen_server.deploy.exceptions.ServerDeploymentError)

Raised when trying to fetch a ZenML server deployment that doesn’t exist.

### *exception* zenml.zen_server.deploy.exceptions.ServerProviderNotFoundError(message: str | None = None, url: str | None = None)

Bases: [`ServerDeploymentError`](#zenml.zen_server.deploy.exceptions.ServerDeploymentError)

Raised when using a ZenML server provider that doesn’t exist.

## Module contents

ZenML server deployments.

### *class* zenml.zen_server.deploy.ServerDeployer(\*args: Any, \*\*kwargs: Any)

Bases: `object`

Server deployer singleton.

This class is responsible for managing the various server provider
implementations and for directing server deployment lifecycle requests to
the responsible provider. It acts as a facade built on top of the various
server providers.

#### connect_to_server(server_name: str, username: str, password: str, verify_ssl: bool | str = True) → None

Connect to a ZenML server instance.

Args:
: server_name: The server deployment name.
  username: The username to use to connect to the server.
  password: The password to use to connect to the server.
  verify_ssl: Either a boolean, in which case it controls whether we
  <br/>
  > verify the server’s TLS certificate, or a string, in which case
  > it must be a path to a CA bundle to use or the CA bundle value
  > itself.

Raises:
: ServerDeploymentError: If the ZenML server is not running or
  : is unreachable.

#### deploy_server(config: [ServerDeploymentConfig](#zenml.zen_server.deploy.deployment.ServerDeploymentConfig), timeout: int | None = None) → [ServerDeployment](#zenml.zen_server.deploy.deployment.ServerDeployment)

Deploy a new ZenML server or update an existing deployment.

Args:
: config: The server deployment configuration.
  timeout: The timeout in seconds to wait until the deployment is
  <br/>
  > successful. If not supplied, the default timeout value specified
  > by the provider is used.

Returns:
: The server deployment.

#### disconnect_from_server(server_name: str | None = None) → None

Disconnect from a ZenML server instance.

Args:
: server_name: The server deployment name. If supplied, the deployer
  : will check if the ZenML client is indeed connected to the server
    and disconnect only if that is the case. Otherwise the deployer
    will disconnect from any ZenML server.

#### *classmethod* get_provider(provider_type: [ServerProviderType](zenml.md#zenml.enums.ServerProviderType)) → [BaseServerProvider](#zenml.zen_server.deploy.base_provider.BaseServerProvider)

Get the server provider associated with a provider type.

Args:
: provider_type: The server provider type.

Returns:
: The server provider associated with the provider type.

Raises:
: ServerProviderNotFoundError: If no provider is registered for the
  : given provider type.

#### get_server(server_name: str) → [ServerDeployment](#zenml.zen_server.deploy.deployment.ServerDeployment)

Get a server deployment.

Args:
: server_name: The server deployment name.

Returns:
: The requested server deployment.

Raises:
: ServerDeploymentNotFoundError: If no server deployment with the
  : given name is found.

#### get_server_logs(server_name: str, follow: bool = False, tail: int | None = None) → Generator[str, bool, None]

Retrieve the logs of a ZenML server.

Args:
: server_name: The server deployment name.
  follow: if True, the logs will be streamed as they are written
  tail: only retrieve the last NUM lines of log output.

Returns:
: A generator that can be accessed to get the service logs.

#### is_connected_to_server(server_name: str) → bool

Check if the ZenML client is currently connected to a ZenML server.

Args:
: server_name: The server deployment name.

Returns:
: True if the ZenML client is connected to the ZenML server, False
  otherwise.

#### list_servers(server_name: str | None = None, provider_type: [ServerProviderType](zenml.md#zenml.enums.ServerProviderType) | None = None) → List[[ServerDeployment](#zenml.zen_server.deploy.deployment.ServerDeployment)]

List all server deployments.

Args:
: server_name: The server deployment name to filter by.
  provider_type: The server provider type to filter by.

Returns:
: The list of server deployments.

#### *classmethod* register_provider(provider: Type[[BaseServerProvider](#zenml.zen_server.deploy.base_provider.BaseServerProvider)]) → None

Register a server provider.

Args:
: provider: The server provider to register.

Raises:
: TypeError: If a provider with the same type is already registered.

#### remove_server(server_name: str, timeout: int | None = None) → None

Tears down and removes all resources and files associated with a ZenML server deployment.

Args:
: server_name: The server deployment name.
  timeout: The timeout in seconds to wait until the deployment is
  <br/>
  > successfully torn down. If not supplied, a provider specific
  > default timeout value is used.

#### update_server(config: [ServerDeploymentConfig](#zenml.zen_server.deploy.deployment.ServerDeploymentConfig), timeout: int | None = None) → [ServerDeployment](#zenml.zen_server.deploy.deployment.ServerDeployment)

Update an existing ZenML server deployment.

Args:
: config: The new server deployment configuration.
  timeout: The timeout in seconds to wait until the deployment is
  <br/>
  > successful. If not supplied, a default timeout value of 30
  > seconds is used.

Returns:
: The updated server deployment.

Raises:
: ServerDeploymentExistsError: If an existing deployment with the same
  : name but a different provider type is found.

### *class* zenml.zen_server.deploy.ServerDeployment(\*, config: [ServerDeploymentConfig](#zenml.zen_server.deploy.deployment.ServerDeploymentConfig), status: [ServerDeploymentStatus](#zenml.zen_server.deploy.deployment.ServerDeploymentStatus) | None = None)

Bases: `BaseModel`

Server deployment.

Attributes:
: config: The server deployment configuration.
  status: The server deployment status.

#### config *: [ServerDeploymentConfig](#zenml.zen_server.deploy.deployment.ServerDeploymentConfig)*

#### *property* is_running *: bool*

Check if the server is running.

Returns:
: Whether the server is running.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'config': FieldInfo(annotation=ServerDeploymentConfig, required=True), 'status': FieldInfo(annotation=Union[ServerDeploymentStatus, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### status *: [ServerDeploymentStatus](#zenml.zen_server.deploy.deployment.ServerDeploymentStatus) | None*

### *class* zenml.zen_server.deploy.ServerDeploymentConfig(\*, name: str, provider: [ServerProviderType](zenml.md#zenml.enums.ServerProviderType), \*\*extra_data: Any)

Bases: `BaseModel`

Generic server deployment configuration.

All server deployment configurations should inherit from this class and
handle extra attributes as provider specific attributes.

Attributes:
: name: Name of the server deployment.
  provider: The server provider type.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'name': FieldInfo(annotation=str, required=True), 'provider': FieldInfo(annotation=ServerProviderType, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### provider *: [ServerProviderType](zenml.md#zenml.enums.ServerProviderType)*
