# zenml.container_registries package

## Submodules

## zenml.container_registries.azure_container_registry module

Implementation of an Azure Container Registry class.

### *class* zenml.container_registries.azure_container_registry.AzureContainerRegistryFlavor

Bases: [`BaseContainerRegistryFlavor`](#zenml.container_registries.base_container_registry.BaseContainerRegistryFlavor)

Class for Azure Container Registry.

#### *property* docs_url *: str | None*

A url to point at docs explaining this flavor.

Returns:
: A flavor docs url.

#### *property* logo_url *: str*

A url to represent the flavor in the dashboard.

Returns:
: The flavor logo.

#### *property* name *: str*

Name of the flavor.

Returns:
: The name of the flavor.

#### *property* sdk_docs_url *: str | None*

A url to point at docs explaining this flavor.

Returns:
: A flavor docs url.

#### *property* service_connector_requirements *: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None*

Service connector resource requirements for service connectors.

Specifies resource requirements that are used to filter the available
service connector types that are compatible with this flavor.

Returns:
: Requirements for compatible service connectors, if a service
  connector is required for this flavor.

## zenml.container_registries.base_container_registry module

Implementation of a base container registry class.

### *class* zenml.container_registries.base_container_registry.BaseContainerRegistry(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`AuthenticationMixin`](zenml.stack.md#zenml.stack.authentication_mixin.AuthenticationMixin)

Base class for all ZenML container registries.

#### *property* config *: [BaseContainerRegistryConfig](#zenml.container_registries.base_container_registry.BaseContainerRegistryConfig)*

Returns the BaseContainerRegistryConfig config.

Returns:
: The configuration.

#### *property* credentials *: Tuple[str, str] | None*

Username and password to authenticate with this container registry.

Returns:
: Tuple with username and password if this container registry
  requires authentication, None otherwise.

#### *property* docker_client *: DockerClient*

Returns a Docker client for this container registry.

Returns:
: The Docker client.

Raises:
: RuntimeError: If the connector does not return a Docker client.

#### prepare_image_push(image_name: str) → None

Preparation before an image gets pushed.

Subclasses can overwrite this to do any necessary checks or
preparations before an image gets pushed.

Args:
: image_name: Name of the docker image that will be pushed.

#### push_image(image_name: str) → str

Pushes a docker image.

Args:
: image_name: Name of the docker image that will be pushed.

Returns:
: The Docker repository digest of the pushed image.

Raises:
: ValueError: If the image name is not associated with this
  : container registry.

#### *property* requires_authentication *: bool*

Returns whether the container registry requires authentication.

Returns:
: True if the container registry requires authentication,
  False otherwise.

### *class* zenml.container_registries.base_container_registry.BaseContainerRegistryConfig(warn_about_plain_text_secrets: bool = False, \*, authentication_secret: str | None = None, uri: str, default_repository: str | None = None)

Bases: [`AuthenticationConfigMixin`](zenml.stack.md#zenml.stack.authentication_mixin.AuthenticationConfigMixin)

Base config for a container registry.

Attributes:
: uri: The URI of the container registry.

#### default_repository *: str | None*

#### *property* is_local *: bool*

Checks if this stack component is running locally.

Returns:
: True if this config is for a local component, False otherwise.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'authentication_secret': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'default_repository': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'uri': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### *classmethod* strip_trailing_slash(uri: str) → str

Removes trailing slashes from the URI.

Args:
: uri: The URI to be stripped.

Returns:
: The URI without trailing slashes.

#### uri *: str*

### *class* zenml.container_registries.base_container_registry.BaseContainerRegistryFlavor

Bases: [`Flavor`](zenml.stack.md#zenml.stack.flavor.Flavor)

Base flavor for container registries.

#### *property* config_class *: Type[[BaseContainerRegistryConfig](#zenml.container_registries.base_container_registry.BaseContainerRegistryConfig)]*

Config class for this flavor.

Returns:
: The config class.

#### *property* implementation_class *: Type[[BaseContainerRegistry](#zenml.container_registries.base_container_registry.BaseContainerRegistry)]*

Implementation class.

Returns:
: The implementation class.

#### *property* service_connector_requirements *: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None*

Service connector resource requirements for service connectors.

Specifies resource requirements that are used to filter the available
service connector types that are compatible with this flavor.

Returns:
: Requirements for compatible service connectors, if a service
  connector is required for this flavor.

#### *property* type *: [StackComponentType](zenml.md#zenml.enums.StackComponentType)*

Returns the flavor type.

Returns:
: The flavor type.

## zenml.container_registries.default_container_registry module

Implementation of a default container registry class.

### *class* zenml.container_registries.default_container_registry.DefaultContainerRegistryFlavor

Bases: [`BaseContainerRegistryFlavor`](#zenml.container_registries.base_container_registry.BaseContainerRegistryFlavor)

Class for default ZenML container registries.

#### *property* docs_url *: str | None*

A URL to point at docs explaining this flavor.

Returns:
: A flavor docs url.

#### *property* logo_url *: str*

A URL to represent the flavor in the dashboard.

Returns:
: The flavor logo.

#### *property* name *: str*

Name of the flavor.

Returns:
: The name of the flavor.

#### *property* sdk_docs_url *: str | None*

A URL to point at docs explaining this flavor.

Returns:
: A flavor docs url.

## zenml.container_registries.dockerhub_container_registry module

Implementation of a DockerHub Container Registry class.

### *class* zenml.container_registries.dockerhub_container_registry.DockerHubContainerRegistryFlavor

Bases: [`BaseContainerRegistryFlavor`](#zenml.container_registries.base_container_registry.BaseContainerRegistryFlavor)

Class for DockerHub Container Registry.

#### *property* docs_url *: str | None*

A url to point at docs explaining this flavor.

Returns:
: A flavor docs url.

#### *property* logo_url *: str*

A url to represent the flavor in the dashboard.

Returns:
: The flavor logo.

#### *property* name *: str*

Name of the flavor.

Returns:
: The name of the flavor.

#### *property* sdk_docs_url *: str | None*

A url to point at docs explaining this flavor.

Returns:
: A flavor docs url.

#### *property* service_connector_requirements *: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None*

Service connector resource requirements for service connectors.

Specifies resource requirements that are used to filter the available
service connector types that are compatible with this flavor.

Returns:
: Requirements for compatible service connectors, if a service
  connector is required for this flavor.

## zenml.container_registries.gcp_container_registry module

Implementation of a GCP Container Registry class.

### *class* zenml.container_registries.gcp_container_registry.GCPContainerRegistryFlavor

Bases: [`BaseContainerRegistryFlavor`](#zenml.container_registries.base_container_registry.BaseContainerRegistryFlavor)

Class for GCP Container Registry.

#### *property* docs_url *: str | None*

A url to point at docs explaining this flavor.

Returns:
: A flavor docs url.

#### *property* logo_url *: str*

A url to represent the flavor in the dashboard.

Returns:
: The flavor logo.

#### *property* name *: str*

Name of the flavor.

Returns:
: The name of the flavor.

#### *property* sdk_docs_url *: str | None*

A url to point at docs explaining this flavor.

Returns:
: A flavor docs url.

#### *property* service_connector_requirements *: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None*

Service connector resource requirements for service connectors.

Specifies resource requirements that are used to filter the available
service connector types that are compatible with this flavor.

Returns:
: Requirements for compatible service connectors, if a service
  connector is required for this flavor.

## zenml.container_registries.github_container_registry module

Implementation of the GitHub Container Registry.

### *class* zenml.container_registries.github_container_registry.GitHubContainerRegistryConfig(warn_about_plain_text_secrets: bool = False, \*, authentication_secret: str | None = None, uri: str, default_repository: str | None = None)

Bases: [`BaseContainerRegistryConfig`](#zenml.container_registries.base_container_registry.BaseContainerRegistryConfig)

Configuration for the GitHub Container Registry.

#### authentication_secret *: str | None*

#### default_repository *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'authentication_secret': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'default_repository': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'uri': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### uri *: str*

### *class* zenml.container_registries.github_container_registry.GitHubContainerRegistryFlavor

Bases: [`BaseContainerRegistryFlavor`](#zenml.container_registries.base_container_registry.BaseContainerRegistryFlavor)

Class for GitHub Container Registry.

#### *property* docs_url *: str | None*

A url to point at docs explaining this flavor.

Returns:
: A flavor docs url.

#### *property* logo_url *: str*

A url to represent the flavor in the dashboard.

Returns:
: The flavor logo.

#### *property* name *: str*

Name of the flavor.

Returns:
: The name of the flavor.

#### *property* sdk_docs_url *: str | None*

A url to point at docs explaining this flavor.

Returns:
: A flavor docs url.

## Module contents

Initialization for ZenML’s container registries module.

A container registry is a store for (Docker) containers. A ZenML workflow
involving a container registry would automatically containerize your code to
be transported across stacks running remotely. As part of the deployment to
the cluster, the ZenML base image would be downloaded (from a cloud container
registry) and used as the basis for the deployed ‘run’.

For instance, when you are running a local container-based stack, you would
therefore have a local container registry which stores the container images
you create that bundle up your pipeline code. You could also use a remote
container registry like the Elastic Container Registry at AWS in a more
production setting.

### *class* zenml.container_registries.AzureContainerRegistryFlavor

Bases: [`BaseContainerRegistryFlavor`](#zenml.container_registries.base_container_registry.BaseContainerRegistryFlavor)

Class for Azure Container Registry.

#### *property* docs_url *: str | None*

A url to point at docs explaining this flavor.

Returns:
: A flavor docs url.

#### *property* logo_url *: str*

A url to represent the flavor in the dashboard.

Returns:
: The flavor logo.

#### *property* name *: str*

Name of the flavor.

Returns:
: The name of the flavor.

#### *property* sdk_docs_url *: str | None*

A url to point at docs explaining this flavor.

Returns:
: A flavor docs url.

#### *property* service_connector_requirements *: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None*

Service connector resource requirements for service connectors.

Specifies resource requirements that are used to filter the available
service connector types that are compatible with this flavor.

Returns:
: Requirements for compatible service connectors, if a service
  connector is required for this flavor.

### *class* zenml.container_registries.BaseContainerRegistry(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`AuthenticationMixin`](zenml.stack.md#zenml.stack.authentication_mixin.AuthenticationMixin)

Base class for all ZenML container registries.

#### *property* config *: [BaseContainerRegistryConfig](#zenml.container_registries.base_container_registry.BaseContainerRegistryConfig)*

Returns the BaseContainerRegistryConfig config.

Returns:
: The configuration.

#### *property* credentials *: Tuple[str, str] | None*

Username and password to authenticate with this container registry.

Returns:
: Tuple with username and password if this container registry
  requires authentication, None otherwise.

#### *property* docker_client *: DockerClient*

Returns a Docker client for this container registry.

Returns:
: The Docker client.

Raises:
: RuntimeError: If the connector does not return a Docker client.

#### prepare_image_push(image_name: str) → None

Preparation before an image gets pushed.

Subclasses can overwrite this to do any necessary checks or
preparations before an image gets pushed.

Args:
: image_name: Name of the docker image that will be pushed.

#### push_image(image_name: str) → str

Pushes a docker image.

Args:
: image_name: Name of the docker image that will be pushed.

Returns:
: The Docker repository digest of the pushed image.

Raises:
: ValueError: If the image name is not associated with this
  : container registry.

#### *property* requires_authentication *: bool*

Returns whether the container registry requires authentication.

Returns:
: True if the container registry requires authentication,
  False otherwise.

### *class* zenml.container_registries.DefaultContainerRegistryFlavor

Bases: [`BaseContainerRegistryFlavor`](#zenml.container_registries.base_container_registry.BaseContainerRegistryFlavor)

Class for default ZenML container registries.

#### *property* docs_url *: str | None*

A URL to point at docs explaining this flavor.

Returns:
: A flavor docs url.

#### *property* logo_url *: str*

A URL to represent the flavor in the dashboard.

Returns:
: The flavor logo.

#### *property* name *: str*

Name of the flavor.

Returns:
: The name of the flavor.

#### *property* sdk_docs_url *: str | None*

A URL to point at docs explaining this flavor.

Returns:
: A flavor docs url.

### *class* zenml.container_registries.DockerHubContainerRegistryFlavor

Bases: [`BaseContainerRegistryFlavor`](#zenml.container_registries.base_container_registry.BaseContainerRegistryFlavor)

Class for DockerHub Container Registry.

#### *property* docs_url *: str | None*

A url to point at docs explaining this flavor.

Returns:
: A flavor docs url.

#### *property* logo_url *: str*

A url to represent the flavor in the dashboard.

Returns:
: The flavor logo.

#### *property* name *: str*

Name of the flavor.

Returns:
: The name of the flavor.

#### *property* sdk_docs_url *: str | None*

A url to point at docs explaining this flavor.

Returns:
: A flavor docs url.

#### *property* service_connector_requirements *: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None*

Service connector resource requirements for service connectors.

Specifies resource requirements that are used to filter the available
service connector types that are compatible with this flavor.

Returns:
: Requirements for compatible service connectors, if a service
  connector is required for this flavor.

### *class* zenml.container_registries.GCPContainerRegistryFlavor

Bases: [`BaseContainerRegistryFlavor`](#zenml.container_registries.base_container_registry.BaseContainerRegistryFlavor)

Class for GCP Container Registry.

#### *property* docs_url *: str | None*

A url to point at docs explaining this flavor.

Returns:
: A flavor docs url.

#### *property* logo_url *: str*

A url to represent the flavor in the dashboard.

Returns:
: The flavor logo.

#### *property* name *: str*

Name of the flavor.

Returns:
: The name of the flavor.

#### *property* sdk_docs_url *: str | None*

A url to point at docs explaining this flavor.

Returns:
: A flavor docs url.

#### *property* service_connector_requirements *: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None*

Service connector resource requirements for service connectors.

Specifies resource requirements that are used to filter the available
service connector types that are compatible with this flavor.

Returns:
: Requirements for compatible service connectors, if a service
  connector is required for this flavor.

### *class* zenml.container_registries.GitHubContainerRegistryFlavor

Bases: [`BaseContainerRegistryFlavor`](#zenml.container_registries.base_container_registry.BaseContainerRegistryFlavor)

Class for GitHub Container Registry.

#### *property* docs_url *: str | None*

A url to point at docs explaining this flavor.

Returns:
: A flavor docs url.

#### *property* logo_url *: str*

A url to represent the flavor in the dashboard.

Returns:
: The flavor logo.

#### *property* name *: str*

Name of the flavor.

Returns:
: The name of the flavor.

#### *property* sdk_docs_url *: str | None*

A url to point at docs explaining this flavor.

Returns:
: A flavor docs url.
