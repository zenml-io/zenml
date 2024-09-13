# zenml.image_builders package

## Submodules

## zenml.image_builders.base_image_builder module

Base class for all ZenML image builders.

### *class* zenml.image_builders.base_image_builder.BaseImageBuilder(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`StackComponent`](zenml.stack.md#zenml.stack.stack_component.StackComponent), `ABC`

Base class for all ZenML image builders.

#### *abstract* build(image_name: str, build_context: [BuildContext](#zenml.image_builders.build_context.BuildContext), docker_build_options: Dict[str, Any], container_registry: [BaseContainerRegistry](zenml.container_registries.md#zenml.container_registries.base_container_registry.BaseContainerRegistry) | None = None) → str

Builds a Docker image.

If a container registry is passed, the image will be pushed to that
registry.

Args:
: image_name: Name of the image to build.
  build_context: The build context to use for the image.
  docker_build_options: Docker build options.
  container_registry: Optional container registry to push to.

Returns:
: The Docker image repo digest or name.

#### *property* build_context_class *: Type[[BuildContext](#zenml.image_builders.build_context.BuildContext)]*

Build context class to use.

The default build context class creates a build context that works
for the Docker daemon. Override this method if your image builder
requires a custom context.

Returns:
: The build context class.

#### *property* config *: [BaseImageBuilderConfig](#zenml.image_builders.base_image_builder.BaseImageBuilderConfig)*

The stack component configuration.

Returns:
: The configuration.

#### *abstract property* is_building_locally *: bool*

Whether the image builder builds the images on the client machine.

Returns:
: True if the image builder builds locally, False otherwise.

### *class* zenml.image_builders.base_image_builder.BaseImageBuilderConfig(warn_about_plain_text_secrets: bool = False)

Bases: [`StackComponentConfig`](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig)

Base config for image builders.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.image_builders.base_image_builder.BaseImageBuilderFlavor

Bases: [`Flavor`](zenml.stack.md#zenml.stack.flavor.Flavor), `ABC`

Base class for all ZenML image builder flavors.

#### *property* config_class *: Type[[BaseImageBuilderConfig](#zenml.image_builders.base_image_builder.BaseImageBuilderConfig)]*

Config class.

Returns:
: The config class.

#### *property* implementation_class *: Type[[BaseImageBuilder](#zenml.image_builders.base_image_builder.BaseImageBuilder)]*

Implementation class.

Returns:
: The implementation class.

#### *property* type *: [StackComponentType](zenml.md#zenml.enums.StackComponentType)*

Returns the flavor type.

Returns:
: The flavor type.

## zenml.image_builders.build_context module

Image build context.

### *class* zenml.image_builders.build_context.BuildContext(root: str | None = None, dockerignore_file: str | None = None)

Bases: [`Archivable`](zenml.utils.md#zenml.utils.archivable.Archivable)

Image build context.

This class is responsible for creating an archive of the files needed to
build a container image.

#### *property* dockerignore_file *: str | None*

The dockerignore file to use.

Returns:
: Path to the dockerignore file to use.

#### get_files() → Dict[str, str]

Gets all regular files that should be included in the archive.

Returns:
: A dict {path_in_archive: path_on_filesystem} for all regular files
  in the archive.

#### write_archive(output_file: IO[bytes], use_gzip: bool = True) → None

Writes an archive of the build context to the given file.

Args:
: output_file: The file to write the archive to.
  use_gzip: Whether to use gzip to compress the file.

## zenml.image_builders.local_image_builder module

Local Docker image builder implementation.

### *class* zenml.image_builders.local_image_builder.LocalImageBuilder(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`BaseImageBuilder`](#zenml.image_builders.base_image_builder.BaseImageBuilder)

Local image builder implementation.

#### build(image_name: str, build_context: [BuildContext](#zenml.image_builders.build_context.BuildContext), docker_build_options: Dict[str, Any] | None = None, container_registry: [BaseContainerRegistry](zenml.container_registries.md#zenml.container_registries.base_container_registry.BaseContainerRegistry) | None = None) → str

Builds and optionally pushes an image using the local Docker client.

Args:
: image_name: Name of the image to build and push.
  build_context: The build context to use for the image.
  docker_build_options: Docker build options.
  container_registry: Optional container registry to push to.

Returns:
: The Docker image repo digest.

#### *property* config *: [LocalImageBuilderConfig](#zenml.image_builders.local_image_builder.LocalImageBuilderConfig)*

The stack component configuration.

Returns:
: The configuration.

#### *property* is_building_locally *: bool*

Whether the image builder builds the images on the client machine.

Returns:
: True if the image builder builds locally, False otherwise.

### *class* zenml.image_builders.local_image_builder.LocalImageBuilderConfig(warn_about_plain_text_secrets: bool = False)

Bases: [`BaseImageBuilderConfig`](#zenml.image_builders.base_image_builder.BaseImageBuilderConfig)

Local image builder configuration.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.image_builders.local_image_builder.LocalImageBuilderFlavor

Bases: [`BaseImageBuilderFlavor`](#zenml.image_builders.base_image_builder.BaseImageBuilderFlavor)

Local image builder flavor.

#### *property* config_class *: Type[[LocalImageBuilderConfig](#zenml.image_builders.local_image_builder.LocalImageBuilderConfig)]*

Config class.

Returns:
: The config class.

#### *property* docs_url *: str | None*

A url to point at docs explaining this flavor.

Returns:
: A flavor docs url.

#### *property* implementation_class *: Type[[LocalImageBuilder](#zenml.image_builders.local_image_builder.LocalImageBuilder)]*

Implementation class.

Returns:
: The implementation class.

#### *property* logo_url *: str*

A url to represent the flavor in the dashboard.

Returns:
: The flavor logo.

#### *property* name *: str*

The flavor name.

Returns:
: The flavor name.

#### *property* sdk_docs_url *: str | None*

A url to point at docs explaining this flavor.

Returns:
: A flavor docs url.

## Module contents

Image builders allow you to build container images.

### *class* zenml.image_builders.BaseImageBuilder(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`StackComponent`](zenml.stack.md#zenml.stack.stack_component.StackComponent), `ABC`

Base class for all ZenML image builders.

#### *abstract* build(image_name: str, build_context: [BuildContext](#zenml.image_builders.BuildContext), docker_build_options: Dict[str, Any], container_registry: [BaseContainerRegistry](zenml.container_registries.md#zenml.container_registries.base_container_registry.BaseContainerRegistry) | None = None) → str

Builds a Docker image.

If a container registry is passed, the image will be pushed to that
registry.

Args:
: image_name: Name of the image to build.
  build_context: The build context to use for the image.
  docker_build_options: Docker build options.
  container_registry: Optional container registry to push to.

Returns:
: The Docker image repo digest or name.

#### *property* build_context_class *: Type[[BuildContext](#zenml.image_builders.BuildContext)]*

Build context class to use.

The default build context class creates a build context that works
for the Docker daemon. Override this method if your image builder
requires a custom context.

Returns:
: The build context class.

#### *property* config *: [BaseImageBuilderConfig](#zenml.image_builders.base_image_builder.BaseImageBuilderConfig)*

The stack component configuration.

Returns:
: The configuration.

#### *abstract property* is_building_locally *: bool*

Whether the image builder builds the images on the client machine.

Returns:
: True if the image builder builds locally, False otherwise.

### *class* zenml.image_builders.BaseImageBuilderConfig(warn_about_plain_text_secrets: bool = False)

Bases: [`StackComponentConfig`](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig)

Base config for image builders.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.image_builders.BaseImageBuilderFlavor

Bases: [`Flavor`](zenml.stack.md#zenml.stack.flavor.Flavor), `ABC`

Base class for all ZenML image builder flavors.

#### *property* config_class *: Type[[BaseImageBuilderConfig](#zenml.image_builders.base_image_builder.BaseImageBuilderConfig)]*

Config class.

Returns:
: The config class.

#### *property* implementation_class *: Type[[BaseImageBuilder](#zenml.image_builders.base_image_builder.BaseImageBuilder)]*

Implementation class.

Returns:
: The implementation class.

#### *property* type *: [StackComponentType](zenml.md#zenml.enums.StackComponentType)*

Returns the flavor type.

Returns:
: The flavor type.

### *class* zenml.image_builders.BuildContext(root: str | None = None, dockerignore_file: str | None = None)

Bases: [`Archivable`](zenml.utils.md#zenml.utils.archivable.Archivable)

Image build context.

This class is responsible for creating an archive of the files needed to
build a container image.

#### *property* dockerignore_file *: str | None*

The dockerignore file to use.

Returns:
: Path to the dockerignore file to use.

#### get_files() → Dict[str, str]

Gets all regular files that should be included in the archive.

Returns:
: A dict {path_in_archive: path_on_filesystem} for all regular files
  in the archive.

#### write_archive(output_file: IO[bytes], use_gzip: bool = True) → None

Writes an archive of the build context to the given file.

Args:
: output_file: The file to write the archive to.
  use_gzip: Whether to use gzip to compress the file.

### *class* zenml.image_builders.LocalImageBuilder(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`BaseImageBuilder`](#zenml.image_builders.base_image_builder.BaseImageBuilder)

Local image builder implementation.

#### build(image_name: str, build_context: [BuildContext](#zenml.image_builders.BuildContext), docker_build_options: Dict[str, Any] | None = None, container_registry: [BaseContainerRegistry](zenml.container_registries.md#zenml.container_registries.base_container_registry.BaseContainerRegistry) | None = None) → str

Builds and optionally pushes an image using the local Docker client.

Args:
: image_name: Name of the image to build and push.
  build_context: The build context to use for the image.
  docker_build_options: Docker build options.
  container_registry: Optional container registry to push to.

Returns:
: The Docker image repo digest.

#### *property* config *: [LocalImageBuilderConfig](#zenml.image_builders.local_image_builder.LocalImageBuilderConfig)*

The stack component configuration.

Returns:
: The configuration.

#### *property* is_building_locally *: bool*

Whether the image builder builds the images on the client machine.

Returns:
: True if the image builder builds locally, False otherwise.

### *class* zenml.image_builders.LocalImageBuilderConfig(warn_about_plain_text_secrets: bool = False)

Bases: [`BaseImageBuilderConfig`](#zenml.image_builders.base_image_builder.BaseImageBuilderConfig)

Local image builder configuration.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.image_builders.LocalImageBuilderFlavor

Bases: [`BaseImageBuilderFlavor`](#zenml.image_builders.base_image_builder.BaseImageBuilderFlavor)

Local image builder flavor.

#### *property* config_class *: Type[[LocalImageBuilderConfig](#zenml.image_builders.local_image_builder.LocalImageBuilderConfig)]*

Config class.

Returns:
: The config class.

#### *property* docs_url *: str | None*

A url to point at docs explaining this flavor.

Returns:
: A flavor docs url.

#### *property* implementation_class *: Type[[LocalImageBuilder](#zenml.image_builders.local_image_builder.LocalImageBuilder)]*

Implementation class.

Returns:
: The implementation class.

#### *property* logo_url *: str*

A url to represent the flavor in the dashboard.

Returns:
: The flavor logo.

#### *property* name *: str*

The flavor name.

Returns:
: The flavor name.

#### *property* sdk_docs_url *: str | None*

A url to point at docs explaining this flavor.

Returns:
: A flavor docs url.
