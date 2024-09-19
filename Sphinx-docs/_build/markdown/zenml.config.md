# zenml.config package

## Submodules

## zenml.config.base_settings module

Base class for all ZenML settings.

### *class* zenml.config.base_settings.BaseSettings(warn_about_plain_text_secrets: bool = False, \*\*kwargs: Any)

Bases: [`SecretReferenceMixin`](#zenml.config.secret_reference_mixin.SecretReferenceMixin)

Base class for settings.

The LEVEL class variable defines on which level the settings can be
specified. By default, subclasses can be defined on both pipelines and
steps.

#### LEVEL *: ClassVar[[ConfigurationLevel](#zenml.config.base_settings.ConfigurationLevel)]* *= 3*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.config.base_settings.ConfigurationLevel(value, names=None, \*, module=None, qualname=None, type=None, start=1, boundary=None)

Bases: `IntFlag`

Settings configuration level.

Bit flag that can be used to specify where a BaseSettings subclass
can be specified.

#### PIPELINE *= 2*

#### STEP *= 1*

## zenml.config.build_configuration module

Build configuration class.

### *class* zenml.config.build_configuration.BuildConfiguration(\*, key: str, settings: [DockerSettings](#zenml.config.docker_settings.DockerSettings), step_name: str | None = None, entrypoint: str | None = None, extra_files: Dict[str, str] = {})

Bases: `BaseModel`

Configuration of Docker builds.

Attributes:
: key: The key to store the build.
  settings: Settings for the build.
  step_name: Name of the step for which this image will be built.
  entrypoint: Optional entrypoint for the image.
  extra_files: Extra files to include in the Docker image.

#### compute_settings_checksum(stack: [Stack](zenml.stack.md#zenml.stack.stack.Stack), code_repository: [BaseCodeRepository](zenml.code_repositories.md#zenml.code_repositories.base_code_repository.BaseCodeRepository) | None = None) → str

Checksum for all build settings.

Args:
: stack: The stack for which to compute the checksum. This is needed
  : to gather the stack integration requirements in case the
    Docker settings specify to install them.
  <br/>
  code_repository: Optional code repository that will be used to
  : download files inside the image.

Returns:
: The checksum.

#### entrypoint *: str | None*

#### extra_files *: Dict[str, str]*

#### key *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'entrypoint': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'extra_files': FieldInfo(annotation=Dict[str, str], required=False, default={}), 'key': FieldInfo(annotation=str, required=True), 'settings': FieldInfo(annotation=DockerSettings, required=True), 'step_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### settings *: [DockerSettings](#zenml.config.docker_settings.DockerSettings)*

#### should_download_files(code_repository: [BaseCodeRepository](zenml.code_repositories.md#zenml.code_repositories.base_code_repository.BaseCodeRepository) | None) → bool

Whether files should be downloaded in the image.

Args:
: code_repository: Code repository that can be used to download files
  : inside the image.

Returns:
: Whether files should be downloaded in the image.

#### should_download_files_from_code_repository(code_repository: [BaseCodeRepository](zenml.code_repositories.md#zenml.code_repositories.base_code_repository.BaseCodeRepository) | None) → bool

Whether files should be downloaded from the code repository.

Args:
: code_repository: Code repository that can be used to download files
  : inside the image.

Returns:
: Whether files should be downloaded from the code repository.

#### should_include_files(code_repository: [BaseCodeRepository](zenml.code_repositories.md#zenml.code_repositories.base_code_repository.BaseCodeRepository) | None) → bool

Whether files should be included in the image.

Args:
: code_repository: Code repository that can be used to download files
  : inside the image.

Returns:
: Whether files should be included in the image.

#### step_name *: str | None*

## zenml.config.compiler module

Class for compiling ZenML pipelines into a serializable format.

### *class* zenml.config.compiler.Compiler

Bases: `object`

Compiles ZenML pipelines to serializable representations.

#### compile(pipeline: [Pipeline](zenml.new.pipelines.md#zenml.new.pipelines.pipeline.Pipeline), stack: [Stack](zenml.stack.md#zenml.stack.stack.Stack), run_configuration: [PipelineRunConfiguration](#zenml.config.pipeline_run_configuration.PipelineRunConfiguration)) → [PipelineDeploymentBase](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentBase)

Compiles a ZenML pipeline to a serializable representation.

Args:
: pipeline: The pipeline to compile.
  stack: The stack on which the pipeline will run.
  run_configuration: The run configuration for this pipeline.

Returns:
: The compiled pipeline deployment.

#### compile_spec(pipeline: [Pipeline](zenml.new.pipelines.md#zenml.new.pipelines.pipeline.Pipeline)) → [PipelineSpec](#zenml.config.pipeline_spec.PipelineSpec)

Compiles a ZenML pipeline to a pipeline spec.

This method can be used when a pipeline spec is needed but the full
deployment including stack information is not required.

Args:
: pipeline: The pipeline to compile.

Returns:
: The compiled pipeline spec.

### zenml.config.compiler.convert_component_shortcut_settings_keys(settings: Dict[str, [BaseSettings](#zenml.config.base_settings.BaseSettings)], stack: [Stack](zenml.stack.md#zenml.stack.stack.Stack)) → None

Convert component shortcut settings keys.

Args:
: settings: Dictionary of settings.
  stack: The stack that the pipeline will run on.

Raises:
: ValueError: If stack component settings were defined both using the
  : full and the shortcut key.

### zenml.config.compiler.get_zenml_versions() → Tuple[str, str]

Returns the version of ZenML on the client and server side.

Returns:
: the ZenML versions on the client and server side respectively.

## zenml.config.constants module

ZenML settings constants.

## zenml.config.docker_settings module

Docker settings.

### *class* zenml.config.docker_settings.DockerBuildConfig(\*, build_options: Dict[str, Any] = {}, dockerignore: str | None = None)

Bases: `BaseModel`

Configuration for a Docker build.

Attributes:
: build_options: Additional options that will be passed unmodified to the
  : Docker build call when building an image. You can use this to for
    example specify build args or a target stage. See
    [https://docker-py.readthedocs.io/en/stable/images.html#docker.models.images.ImageCollection.build](https://docker-py.readthedocs.io/en/stable/images.html#docker.models.images.ImageCollection.build)
    for a full list of available options.
  <br/>
  dockerignore: Path to a dockerignore file to use when building the
  : Docker image.

#### build_options *: Dict[str, Any]*

#### dockerignore *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'build_options': FieldInfo(annotation=Dict[str, Any], required=False, default={}), 'dockerignore': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.config.docker_settings.DockerSettings(warn_about_plain_text_secrets: bool = False, \*, parent_image: str | None = None, dockerfile: str | None = None, build_context_root: str | None = None, parent_image_build_config: [DockerBuildConfig](#zenml.config.docker_settings.DockerBuildConfig) | None = None, skip_build: bool = False, prevent_build_reuse: bool = False, target_repository: str | None = None, python_package_installer: [PythonPackageInstaller](#zenml.config.docker_settings.PythonPackageInstaller) = PythonPackageInstaller.PIP, python_package_installer_args: Dict[str, Any] = {}, replicate_local_python_environment: Annotated[List[str] | [PythonEnvironmentExportMethod](#zenml.config.docker_settings.PythonEnvironmentExportMethod) | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, requirements: Annotated[None | str | List[str], \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, required_integrations: List[str] = [], install_stack_requirements: bool = True, apt_packages: List[str] = [], environment: Dict[str, Any] = {}, user: str | None = None, build_config: [DockerBuildConfig](#zenml.config.docker_settings.DockerBuildConfig) | None = None, allow_including_files_in_images: bool = True, allow_download_from_code_repository: bool = True, allow_download_from_artifact_store: bool = True, build_options: Dict[str, Any] = {}, dockerignore: str | None = None, copy_files: bool = True, copy_global_config: bool = True, source_files: str | None = None, required_hub_plugins: List[str] = [])

Bases: [`BaseSettings`](#zenml.config.base_settings.BaseSettings)

Settings for building Docker images to run ZenML pipelines.

### Build process:

* No dockerfile specified: If any of the options regarding

requirements, environment variables or copying files require us to build an
image, ZenML will build this image. Otherwise, the parent_image will be
used to run the pipeline.
\* dockerfile specified: ZenML will first build an image based on the
specified Dockerfile. If any of the options regarding
requirements, environment variables or copying files require an additional
image built on top of that, ZenML will build a second image. If not, the
image build from the specified Dockerfile will be used to run the pipeline.

### Requirements installation order:

Depending on the configuration of this object, requirements will be
installed in the following order (each step optional):
- The packages installed in your local python environment
- The packages required by the stack unless this is disabled by setting

> install_stack_requirements=False.
- The packages specified via the required_integrations
- The packages specified via the requirements attribute

Attributes:
: parent_image: Full name of the Docker image that should be
  : used as the parent for the image that will be built. Defaults to
    a ZenML image built for the active Python and ZenML version.
    <br/>
    Additional notes:
    \* If you specify a custom image here, you need to make sure it has
    ZenML installed.
    \* If this is a non-local image, the environment which is running
    the pipeline and building the Docker image needs to be able to pull
    this image.
    \* If a custom dockerfile is specified for this settings
    object, this parent image will be ignored.
  <br/>
  dockerfile: Path to a custom Dockerfile that should be built. Depending
  : on the other values you specify in this object, the resulting
    image will be used directly to run your pipeline or ZenML will use
    it as a parent image to build on top of. See the general docstring
    of this class for more information.
    <br/>
    Additional notes:
    \* If you specify this, the parent_image attribute will be ignored.
    \* If you specify this, the image built from this Dockerfile needs
    to have ZenML installed.
  <br/>
  build_context_root: Build context root for the Docker build, only used
  : when the dockerfile attribute is set. If this is left empty, the
    build context will only contain the Dockerfile.
  <br/>
  parent_image_build_config: Configuration for the parent image build.
  skip_build: If set to True, the parent image will be used directly to
  <br/>
  > run the steps of your pipeline.
  <br/>
  prevent_build_reuse: Prevent the reuse of an existing build.
  target_repository: Name of the Docker repository to which the
  <br/>
  > image should be pushed. This repository will be appended to the
  > registry URI of the container registry of your stack and should
  > therefore **not** include any registry. If not specified, the
  > default repository name configured in the container registry
  > stack component settings will be used.
  <br/>
  python_package_installer: The package installer to use for python
  : packages.
  <br/>
  python_package_installer_args: Arguments to pass to the python package
  : installer.
  <br/>
  replicate_local_python_environment: If not None, ZenML will use the
  : specified method to generate a requirements file that replicates
    the packages installed in the currently running python environment.
    This requirements file will then be installed in the Docker image.
  <br/>
  requirements: Path to a requirements file or a list of required pip
  : packages. During the image build, these requirements will be
    installed using pip. If you need to use a different tool to
    resolve and/or install your packages, please use a custom parent
    image or specify a custom dockerfile.
  <br/>
  required_integrations: List of ZenML integrations that should be
  : installed. All requirements for the specified integrations will
    be installed inside the Docker image.
  <br/>
  required_hub_plugins: DEPRECATED/UNUSED.
  install_stack_requirements: If True, ZenML will automatically detect
  <br/>
  > if components of your active stack are part of a ZenML integration
  > and install the corresponding requirements and apt packages.
  > If you set this to False or use custom components in your stack,
  > you need to make sure these get installed by specifying them in
  > the requirements and apt_packages attributes.
  <br/>
  apt_packages: APT packages to install inside the Docker image.
  environment: Dictionary of environment variables to set inside the
  <br/>
  > Docker image.
  <br/>
  build_config: Configuration for the main image build.
  user: If not None, will set the user, make it owner of the /app
  <br/>
  > directory which contains all the user code and run the container
  > entrypoint as this user.
  <br/>
  allow_including_files_in_images: If True, code can be included in the
  : Docker images if code download from a code repository or artifact
    store is disabled or not possible.
  <br/>
  allow_download_from_code_repository: If True, code can be downloaded
  : from a code repository if possible.
  <br/>
  allow_download_from_artifact_store: If True, code can be downloaded
  : from the artifact store.
  <br/>
  build_options: DEPRECATED, use parent_image_build_config.build_options
  : instead.
  <br/>
  dockerignore: DEPRECATED, use build_config.dockerignore instead.
  copy_files: DEPRECATED/UNUSED.
  copy_global_config: DEPRECATED/UNUSED.
  source_files: DEPRECATED. Use allow_including_files_in_images,
  <br/>
  > allow_download_from_code_repository and
  > allow_download_from_artifact_store instead.

#### allow_download_from_artifact_store *: bool*

#### allow_download_from_code_repository *: bool*

#### allow_including_files_in_images *: bool*

#### apt_packages *: List[str]*

#### build_config *: [DockerBuildConfig](#zenml.config.docker_settings.DockerBuildConfig) | None*

#### build_context_root *: str | None*

#### build_options *: Dict[str, Any]*

#### copy_files *: bool*

#### copy_global_config *: bool*

#### dockerfile *: str | None*

#### dockerignore *: str | None*

#### environment *: Dict[str, Any]*

#### install_stack_requirements *: bool*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'allow_download_from_artifact_store': FieldInfo(annotation=bool, required=False, default=True), 'allow_download_from_code_repository': FieldInfo(annotation=bool, required=False, default=True), 'allow_including_files_in_images': FieldInfo(annotation=bool, required=False, default=True), 'apt_packages': FieldInfo(annotation=List[str], required=False, default=[]), 'build_config': FieldInfo(annotation=Union[DockerBuildConfig, NoneType], required=False, default=None), 'build_context_root': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'build_options': FieldInfo(annotation=Dict[str, Any], required=False, default={}), 'copy_files': FieldInfo(annotation=bool, required=False, default=True), 'copy_global_config': FieldInfo(annotation=bool, required=False, default=True), 'dockerfile': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'dockerignore': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'environment': FieldInfo(annotation=Dict[str, Any], required=False, default={}), 'install_stack_requirements': FieldInfo(annotation=bool, required=False, default=True), 'parent_image': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'parent_image_build_config': FieldInfo(annotation=Union[DockerBuildConfig, NoneType], required=False, default=None), 'prevent_build_reuse': FieldInfo(annotation=bool, required=False, default=False), 'python_package_installer': FieldInfo(annotation=PythonPackageInstaller, required=False, default=<PythonPackageInstaller.PIP: 'pip'>), 'python_package_installer_args': FieldInfo(annotation=Dict[str, Any], required=False, default={}), 'replicate_local_python_environment': FieldInfo(annotation=Union[List[str], PythonEnvironmentExportMethod, NoneType], required=False, default=None, metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'required_hub_plugins': FieldInfo(annotation=List[str], required=False, default=[]), 'required_integrations': FieldInfo(annotation=List[str], required=False, default=[]), 'requirements': FieldInfo(annotation=Union[NoneType, str, List[str]], required=False, default=None, metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'skip_build': FieldInfo(annotation=bool, required=False, default=False), 'source_files': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'target_repository': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'user': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### parent_image *: str | None*

#### parent_image_build_config *: [DockerBuildConfig](#zenml.config.docker_settings.DockerBuildConfig) | None*

#### prevent_build_reuse *: bool*

#### python_package_installer *: [PythonPackageInstaller](#zenml.config.docker_settings.PythonPackageInstaller)*

#### python_package_installer_args *: Dict[str, Any]*

#### replicate_local_python_environment *: List[str] | [PythonEnvironmentExportMethod](#zenml.config.docker_settings.PythonEnvironmentExportMethod) | None*

#### required_hub_plugins *: List[str]*

#### required_integrations *: List[str]*

#### requirements *: None | str | List[str]*

#### skip_build *: bool*

#### source_files *: str | None*

#### target_repository *: str | None*

#### user *: str | None*

### *class* zenml.config.docker_settings.PythonEnvironmentExportMethod(value, names=None, \*, module=None, qualname=None, type=None, start=1, boundary=None)

Bases: `Enum`

Different methods to export the local Python environment.

#### PIP_FREEZE *= 'pip_freeze'*

#### POETRY_EXPORT *= 'poetry_export'*

#### *property* command *: str*

Shell command that outputs local python packages.

The output string must be something that can be interpreted as a
requirements file for pip once it’s written to a file.

Returns:
: Shell command.

### *class* zenml.config.docker_settings.PythonPackageInstaller(value, names=None, \*, module=None, qualname=None, type=None, start=1, boundary=None)

Bases: `Enum`

Different installers for python packages.

#### PIP *= 'pip'*

#### UV *= 'uv'*

## zenml.config.global_config module

Functionality to support ZenML GlobalConfiguration.

### *class* zenml.config.global_config.GlobalConfigMetaClass(cls_name: str, bases: tuple[type[Any], ...], namespace: dict[str, Any], \_\_pydantic_generic_metadata_\_: PydanticGenericMetadata | None = None, \_\_pydantic_reset_parent_namespace_\_: bool = True, \_create_model_module: str | None = None, \*\*kwargs: Any)

Bases: `ModelMetaclass`

Global configuration metaclass.

This metaclass is used to enforce a singleton instance of the
GlobalConfiguration class with the following additional properties:

* the GlobalConfiguration is initialized automatically on import with the

default configuration, if no config file exists yet.
\* the GlobalConfiguration undergoes a schema migration if the version of the
config file is older than the current version of the ZenML package.
\* a default store is set if no store is configured yet.

### *class* zenml.config.global_config.GlobalConfiguration(\*, user_id: UUID = None, user_email: str | None = None, user_email_opt_in: bool | None = None, analytics_opt_in: bool = True, version: str | None = None, store: Annotated[[StoreConfiguration](#zenml.config.store_config.StoreConfiguration), SerializeAsAny()] | None = None, active_stack_id: UUID | None = None, active_workspace_name: str | None = None, \*\*data: Any)

Bases: `BaseModel`

Stores global configuration options.

Configuration options are read from a config file, but can be overwritten
by environment variables. See GlobalConfiguration._\_getattribute_\_ for
more details.

Attributes:
: user_id: Unique user id.
  user_email: Email address associated with this client.
  user_email_opt_in: Whether the user has opted in to email communication.
  analytics_opt_in: If a user agreed to sending analytics or not.
  version: Version of ZenML that was last used to create or update the
  <br/>
  > global config.
  <br/>
  store: Store configuration.
  active_stack_id: The ID of the active stack.
  active_workspace_name: The name of the active workspace.

#### active_stack_id *: UUID | None*

#### active_workspace_name *: str | None*

#### analytics_opt_in *: bool*

#### *property* config_directory *: str*

Directory where the global configuration file is located.

Returns:
: The directory where the global configuration file is located.

#### get_active_stack_id() → UUID

Get the ID of the active stack.

If the active stack doesn’t exist yet, the ZenStore is reinitialized.

Returns:
: The active stack ID.

#### get_active_workspace() → [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)

Get a model of the active workspace for the local client.

Returns:
: The model of the active workspace.

#### get_active_workspace_name() → str

Get the name of the active workspace.

If the active workspace doesn’t exist yet, the ZenStore is reinitialized.

Returns:
: The name of the active workspace.

#### get_config_environment_vars() → Dict[str, str]

Convert the global configuration to environment variables.

Returns:
: Environment variables dictionary.

#### get_default_store() → [StoreConfiguration](#zenml.config.store_config.StoreConfiguration)

Get the default SQLite store configuration.

Returns:
: The default SQLite store configuration.

#### *classmethod* get_instance() → [GlobalConfiguration](#zenml.config.global_config.GlobalConfiguration) | None

Return the GlobalConfiguration singleton instance.

Returns:
: The GlobalConfiguration singleton instance or None, if the
  GlobalConfiguration hasn’t been initialized yet.

#### *property* local_stores_path *: str*

Path where local stores information is stored.

Returns:
: The path where local stores information is stored.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'active_stack_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None), 'active_workspace_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'analytics_opt_in': FieldInfo(annotation=bool, required=False, default=True), 'store': FieldInfo(annotation=Union[Annotated[StoreConfiguration, SerializeAsAny], NoneType], required=False, default=None), 'user_email': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'user_email_opt_in': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None), 'user_id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

This function is meant to behave like a BaseModel method to initialise private attributes.

It takes context as an argument since that’s what pydantic-core passes when calling it.

Args:
: self: The BaseModel instance.
  context: The context.

#### set_active_stack(stack: [StackResponse](zenml.models.md#zenml.models.StackResponse)) → None

Set the active stack for the local client.

Args:
: stack: The model of the stack to set active.

#### set_active_workspace(workspace: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)) → [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)

Set the workspace for the local client.

Args:
: workspace: The workspace to set active.

Returns:
: The workspace that was set active.

#### set_default_store() → None

Initializes and sets the default store configuration.

Call this method to initialize or revert the store configuration to the
default store.

#### set_store(config: [StoreConfiguration](#zenml.config.store_config.StoreConfiguration), skip_default_registrations: bool = False, \*\*kwargs: Any) → None

Update the active store configuration.

Call this method to validate and update the active store configuration.

Args:
: config: The new store configuration to use.
  skip_default_registrations: If True, the creation of the default
  <br/>
  > stack and user in the store will be skipped.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Additional keyword arguments to pass to the store
  : constructor.

#### store *: Annotated[[StoreConfiguration](#zenml.config.store_config.StoreConfiguration), SerializeAsAny()] | None*

#### *property* store_configuration *: [StoreConfiguration](#zenml.config.store_config.StoreConfiguration)*

Get the current store configuration.

Returns:
: The store configuration.

#### user_email *: str | None*

#### user_email_opt_in *: bool | None*

#### user_id *: UUID*

#### uses_default_store() → bool

Check if the global configuration uses the default store.

Returns:
: True if the global configuration uses the default store.

#### version *: str | None*

#### *property* zen_store *: [BaseZenStore](zenml.zen_stores.md#zenml.zen_stores.base_zen_store.BaseZenStore)*

Initialize and/or return the global zen store.

If the store hasn’t been initialized yet, it is initialized when this
property is first accessed according to the global store configuration.

Returns:
: The current zen store.

## zenml.config.pipeline_configurations module

Pipeline configuration classes.

### *class* zenml.config.pipeline_configurations.PipelineConfiguration(\*, enable_cache: bool | None = None, enable_artifact_metadata: bool | None = None, enable_artifact_visualization: bool | None = None, enable_step_logs: bool | None = None, settings: Dict[str, Annotated[[BaseSettings](#zenml.config.base_settings.BaseSettings), SerializeAsAny()]] = {}, extra: Dict[str, Any] = {}, failure_hook_source: Annotated[[Source](#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)] | None = None, success_hook_source: Annotated[[Source](#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)] | None = None, model: [Model](zenml.model.md#zenml.model.model.Model) | None = None, parameters: Dict[str, Any] | None = None, retry: [StepRetryConfig](#zenml.config.retry_config.StepRetryConfig) | None = None, name: str)

Bases: [`PipelineConfigurationUpdate`](#zenml.config.pipeline_configurations.PipelineConfigurationUpdate)

Pipeline configuration class.

#### *property* docker_settings *: [DockerSettings](#zenml.config.docker_settings.DockerSettings)*

Docker settings of this pipeline.

Returns:
: The Docker settings of this pipeline.

#### *classmethod* ensure_pipeline_name_allowed(name: str) → str

Ensures the pipeline name is allowed.

Args:
: name: Name of the pipeline.

Returns:
: The validated name of the pipeline.

Raises:
: ValueError: If the name is not allowed.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'enable_artifact_metadata': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None), 'enable_artifact_visualization': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None), 'enable_cache': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None), 'enable_step_logs': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None), 'extra': FieldInfo(annotation=Dict[str, Any], required=False, default={}), 'failure_hook_source': FieldInfo(annotation=Union[Annotated[Source, SerializeAsAny, BeforeValidator], NoneType], required=False, default=None), 'model': FieldInfo(annotation=Union[Model, NoneType], required=False, default=None), 'name': FieldInfo(annotation=str, required=True), 'parameters': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None), 'retry': FieldInfo(annotation=Union[StepRetryConfig, NoneType], required=False, default=None), 'settings': FieldInfo(annotation=Dict[str, Annotated[BaseSettings, SerializeAsAny]], required=False, default={}), 'success_hook_source': FieldInfo(annotation=Union[Annotated[Source, SerializeAsAny, BeforeValidator], NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

### *class* zenml.config.pipeline_configurations.PipelineConfigurationUpdate(\*, enable_cache: bool | None = None, enable_artifact_metadata: bool | None = None, enable_artifact_visualization: bool | None = None, enable_step_logs: bool | None = None, settings: Dict[str, Annotated[[BaseSettings](#zenml.config.base_settings.BaseSettings), SerializeAsAny()]] = {}, extra: Dict[str, Any] = {}, failure_hook_source: Annotated[[Source](#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)] | None = None, success_hook_source: Annotated[[Source](#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)] | None = None, model: [Model](zenml.model.md#zenml.model.model.Model) | None = None, parameters: Dict[str, Any] | None = None, retry: [StepRetryConfig](#zenml.config.retry_config.StepRetryConfig) | None = None)

Bases: [`StrictBaseModel`](#zenml.config.strict_base_model.StrictBaseModel)

Class for pipeline configuration updates.

#### enable_artifact_metadata *: bool | None*

#### enable_artifact_visualization *: bool | None*

#### enable_cache *: bool | None*

#### enable_step_logs *: bool | None*

#### extra *: Dict[str, Any]*

#### failure_hook_source *: Annotated[[Source](#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)] | None*

#### model *: [Model](zenml.model.md#zenml.model.model.Model) | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'enable_artifact_metadata': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None), 'enable_artifact_visualization': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None), 'enable_cache': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None), 'enable_step_logs': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None), 'extra': FieldInfo(annotation=Dict[str, Any], required=False, default={}), 'failure_hook_source': FieldInfo(annotation=Union[Annotated[Source, SerializeAsAny, BeforeValidator], NoneType], required=False, default=None), 'model': FieldInfo(annotation=Union[Model, NoneType], required=False, default=None), 'parameters': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None), 'retry': FieldInfo(annotation=Union[StepRetryConfig, NoneType], required=False, default=None), 'settings': FieldInfo(annotation=Dict[str, Annotated[BaseSettings, SerializeAsAny]], required=False, default={}), 'success_hook_source': FieldInfo(annotation=Union[Annotated[Source, SerializeAsAny, BeforeValidator], NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### parameters *: Dict[str, Any] | None*

#### retry *: [StepRetryConfig](#zenml.config.retry_config.StepRetryConfig) | None*

#### settings *: Dict[str, Annotated[[BaseSettings](#zenml.config.base_settings.BaseSettings), SerializeAsAny()]]*

#### success_hook_source *: Annotated[[Source](#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)] | None*

## zenml.config.pipeline_run_configuration module

Pipeline run configuration class.

### *class* zenml.config.pipeline_run_configuration.PipelineRunConfiguration(\*, run_name: str | None = None, enable_cache: bool | None = None, enable_artifact_metadata: bool | None = None, enable_artifact_visualization: bool | None = None, enable_step_logs: bool | None = None, schedule: [Schedule](#zenml.config.schedule.Schedule) | None = None, build: Annotated[[PipelineBuildBase](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_build.PipelineBuildBase) | UUID | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, steps: Dict[str, [StepConfigurationUpdate](#zenml.config.step_configurations.StepConfigurationUpdate)] = {}, settings: Dict[str, Annotated[[BaseSettings](#zenml.config.base_settings.BaseSettings), SerializeAsAny()]] = {}, extra: Dict[str, Any] = {}, model: [Model](zenml.model.md#zenml.model.model.Model) | None = None, parameters: Dict[str, Any] | None = None, retry: [StepRetryConfig](#zenml.config.retry_config.StepRetryConfig) | None = None, failure_hook_source: Annotated[[Source](#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)] | None = None, success_hook_source: Annotated[[Source](#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)] | None = None)

Bases: [`StrictBaseModel`](#zenml.config.strict_base_model.StrictBaseModel), [`YAMLSerializationMixin`](zenml.utils.md#zenml.utils.pydantic_utils.YAMLSerializationMixin)

Class for pipeline run configurations.

#### build *: [PipelineBuildBase](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_build.PipelineBuildBase) | UUID | None*

#### enable_artifact_metadata *: bool | None*

#### enable_artifact_visualization *: bool | None*

#### enable_cache *: bool | None*

#### enable_step_logs *: bool | None*

#### extra *: Dict[str, Any]*

#### failure_hook_source *: Annotated[[Source](#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)] | None*

#### model *: [Model](zenml.model.md#zenml.model.model.Model) | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'build': FieldInfo(annotation=Union[PipelineBuildBase, UUID, NoneType], required=False, default=None, metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'enable_artifact_metadata': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None), 'enable_artifact_visualization': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None), 'enable_cache': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None), 'enable_step_logs': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None), 'extra': FieldInfo(annotation=Dict[str, Any], required=False, default={}), 'failure_hook_source': FieldInfo(annotation=Union[Annotated[Source, SerializeAsAny, BeforeValidator], NoneType], required=False, default=None), 'model': FieldInfo(annotation=Union[Model, NoneType], required=False, default=None), 'parameters': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None), 'retry': FieldInfo(annotation=Union[StepRetryConfig, NoneType], required=False, default=None), 'run_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'schedule': FieldInfo(annotation=Union[Schedule, NoneType], required=False, default=None), 'settings': FieldInfo(annotation=Dict[str, Annotated[BaseSettings, SerializeAsAny]], required=False, default={}), 'steps': FieldInfo(annotation=Dict[str, StepConfigurationUpdate], required=False, default={}), 'success_hook_source': FieldInfo(annotation=Union[Annotated[Source, SerializeAsAny, BeforeValidator], NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### parameters *: Dict[str, Any] | None*

#### retry *: [StepRetryConfig](#zenml.config.retry_config.StepRetryConfig) | None*

#### run_name *: str | None*

#### schedule *: [Schedule](#zenml.config.schedule.Schedule) | None*

#### settings *: Dict[str, Annotated[[BaseSettings](#zenml.config.base_settings.BaseSettings), SerializeAsAny()]]*

#### steps *: Dict[str, [StepConfigurationUpdate](#zenml.config.step_configurations.StepConfigurationUpdate)]*

#### success_hook_source *: Annotated[[Source](#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)] | None*

## zenml.config.pipeline_spec module

Pipeline configuration classes.

### *class* zenml.config.pipeline_spec.PipelineSpec(\*, version: str = '0.4', source: Annotated[[Source](#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)] | None = None, parameters: Dict[str, Any] = {}, steps: List[[StepSpec](#zenml.config.step_configurations.StepSpec)])

Bases: [`StrictBaseModel`](#zenml.config.strict_base_model.StrictBaseModel)

Specification of a pipeline.

#### *property* json_with_string_sources *: str*

JSON representation with sources replaced by their import path.

Returns:
: The JSON representation.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'parameters': FieldInfo(annotation=Dict[str, Any], required=False, default={}), 'source': FieldInfo(annotation=Union[Annotated[Source, SerializeAsAny, BeforeValidator], NoneType], required=False, default=None), 'steps': FieldInfo(annotation=List[StepSpec], required=True), 'version': FieldInfo(annotation=str, required=False, default='0.4')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### parameters *: Dict[str, Any]*

#### source *: Annotated[[Source](#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)] | None*

#### steps *: List[[StepSpec](#zenml.config.step_configurations.StepSpec)]*

#### version *: str*

## zenml.config.resource_settings module

Resource settings class used to specify resources for a step.

### *class* zenml.config.resource_settings.ByteUnit(value, names=None, \*, module=None, qualname=None, type=None, start=1, boundary=None)

Bases: `Enum`

Enum for byte units.

#### GB *= 'GB'*

#### GIB *= 'GiB'*

#### KB *= 'KB'*

#### KIB *= 'KiB'*

#### MB *= 'MB'*

#### MIB *= 'MiB'*

#### PB *= 'PB'*

#### PIB *= 'PiB'*

#### TB *= 'TB'*

#### TIB *= 'TiB'*

#### *property* byte_value *: int*

Returns the amount of bytes that this unit represents.

Returns:
: The byte value of this unit.

### *class* zenml.config.resource_settings.ResourceSettings(warn_about_plain_text_secrets: bool = False, \*, cpu_count: Annotated[float, Gt(gt=0)] | None = None, gpu_count: Annotated[int, Ge(ge=0)] | None = None, memory: Annotated[str | None, \_PydanticGeneralMetadata(pattern='^[0-9]+(KB|KiB|MB|MiB|GB|GiB|TB|TiB|PB|PiB)$')] = None)

Bases: [`BaseSettings`](#zenml.config.base_settings.BaseSettings)

Hardware resource settings.

Attributes:
: cpu_count: The amount of CPU cores that should be configured.
  gpu_count: The amount of GPUs that should be configured.
  memory: The amount of memory that should be configured.

#### cpu_count *: Annotated[float, Gt(gt=0)] | None*

#### *property* empty *: bool*

Returns if this object is “empty” (=no values configured) or not.

Returns:
: True if no values were configured, False otherwise.

#### get_memory(unit: str | [ByteUnit](#zenml.config.resource_settings.ByteUnit) = ByteUnit.GB) → float | None

Gets the memory configuration in a specific unit.

Args:
: unit: The unit to which the memory should be converted.

Raises:
: ValueError: If the memory string is invalid.

Returns:
: The memory configuration converted to the requested unit, or None
  if no memory was configured.

#### gpu_count *: Annotated[int, Ge(ge=0)] | None*

#### memory *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'cpu_count': FieldInfo(annotation=Union[Annotated[float, Gt], NoneType], required=False, default=None), 'gpu_count': FieldInfo(annotation=Union[Annotated[int, Ge], NoneType], required=False, default=None), 'memory': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, metadata=[_PydanticGeneralMetadata(pattern='^[0-9]+(KB|KiB|MB|MiB|GB|GiB|TB|TiB|PB|PiB)$')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

## zenml.config.retry_config module

Retry configuration for a step.

### *class* zenml.config.retry_config.StepRetryConfig(\*, max_retries: int = 1, delay: int = 0, backoff: int = 0)

Bases: [`StrictBaseModel`](#zenml.config.strict_base_model.StrictBaseModel)

Retry configuration for a step.

Delay is an integer (specified in seconds).

#### backoff *: int*

#### delay *: int*

#### max_retries *: int*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'backoff': FieldInfo(annotation=int, required=False, default=0), 'delay': FieldInfo(annotation=int, required=False, default=0), 'max_retries': FieldInfo(annotation=int, required=False, default=1)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

## zenml.config.schedule module

Class for defining a pipeline schedule.

### *class* zenml.config.schedule.Schedule(\*, name: str | None = None, cron_expression: str | None = None, start_time: datetime | None = None, end_time: datetime | None = None, interval_second: timedelta | None = None, catchup: bool = False, run_once_start_time: datetime | None = None)

Bases: `BaseModel`

Class for defining a pipeline schedule.

Attributes:
: name: Optional name to give to the schedule. If not set, a default name
  : will be generated based on the pipeline name and the current date
    and time.
  <br/>
  cron_expression: Cron expression for the pipeline schedule. If a value
  : for this is set it takes precedence over the start time + interval.
  <br/>
  start_time: datetime object to indicate when to start the schedule.
  end_time: datetime object to indicate when to end the schedule.
  interval_second: datetime timedelta indicating the seconds between two
  <br/>
  > recurring runs for a periodic schedule.
  <br/>
  catchup: Whether the recurring run should catch up if behind schedule.
  : For example, if the recurring run is paused for a while and
    re-enabled afterward. If catchup=True, the scheduler will catch
    up on (backfill) each missed interval. Otherwise, it only
    schedules the latest interval if more than one interval is ready to
    be scheduled. Usually, if your pipeline handles backfill
    internally, you should turn catchup off to avoid duplicate backfill.
  <br/>
  run_once_start_time: datetime object to indicate when to run the
  : pipeline once. This is useful for one-off runs.

#### catchup *: bool*

#### cron_expression *: str | None*

#### end_time *: datetime | None*

#### interval_second *: timedelta | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'catchup': FieldInfo(annotation=bool, required=False, default=False), 'cron_expression': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'end_time': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None), 'interval_second': FieldInfo(annotation=Union[timedelta, NoneType], required=False, default=None), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'run_once_start_time': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None), 'start_time': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str | None*

#### run_once_start_time *: datetime | None*

#### start_time *: datetime | None*

#### *property* utc_end_time *: str | None*

Optional ISO-formatted string of the UTC end time.

Returns:
: Optional ISO-formatted string of the UTC end time.

#### *property* utc_start_time *: str | None*

Optional ISO-formatted string of the UTC start time.

Returns:
: Optional ISO-formatted string of the UTC start time.

## zenml.config.secret_reference_mixin module

Secret reference mixin implementation.

### *class* zenml.config.secret_reference_mixin.SecretReferenceMixin(warn_about_plain_text_secrets: bool = False)

Bases: `BaseModel`

Mixin class for secret references in pydantic model attributes.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### *property* required_secrets *: Set[[SecretReference](zenml.utils.md#zenml.utils.secret_utils.SecretReference)]*

All required secrets for this object.

Returns:
: The required secrets of this object.

## zenml.config.secrets_store_config module

Functionality to support ZenML secrets store configurations.

### *class* zenml.config.secrets_store_config.SecretsStoreConfiguration(\*, type: [SecretsStoreType](zenml.md#zenml.enums.SecretsStoreType), class_path: str | None = None, \*\*extra_data: Any)

Bases: `BaseModel`

Generic secrets store configuration.

The store configurations of concrete secrets store implementations must
inherit from this class and validate any extra attributes that are
configured in addition to those defined in this class.

Attributes:
: type: The type of store backend.
  class_path: The Python class path of the store backend. Should point to
  <br/>
  > a subclass of BaseSecretsStore. This is optional and only
  > required if the store backend is not one of the built-in
  > implementations.

#### class_path *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'class_path': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'type': FieldInfo(annotation=SecretsStoreType, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### type *: [SecretsStoreType](zenml.md#zenml.enums.SecretsStoreType)*

#### validate_custom() → [SecretsStoreConfiguration](#zenml.config.secrets_store_config.SecretsStoreConfiguration)

Validate that class_path is set for custom secrets stores.

Returns:
: Validated settings.

Raises:
: ValueError: If class_path is not set when using a custom secrets
  : store.

## zenml.config.server_config module

Functionality to support ZenML GlobalConfiguration.

### *class* zenml.config.server_config.ServerConfiguration(\*, deployment_type: [ServerDeploymentType](zenml.models.v2.misc.md#zenml.models.v2.misc.server_models.ServerDeploymentType) = ServerDeploymentType.OTHER, server_url: str | None = None, dashboard_url: str | None = None, root_url_path: str = '', metadata: Dict[str, Any] = {}, auth_scheme: [AuthScheme](zenml.md#zenml.enums.AuthScheme) = AuthScheme.OAUTH2_PASSWORD_BEARER, jwt_token_algorithm: str = 'HS256', jwt_token_issuer: str | None = None, jwt_token_audience: str | None = None, jwt_token_leeway_seconds: int = 10, jwt_token_expire_minutes: int | None = None, jwt_secret_key: str = None, auth_cookie_name: str | None = None, auth_cookie_domain: str | None = None, cors_allow_origins: List[str] | None = None, max_failed_device_auth_attempts: int = 3, device_auth_timeout: int = 300, device_auth_polling_interval: int = 5, device_expiration_minutes: int | None = None, trusted_device_expiration_minutes: int | None = None, external_login_url: str | None = None, external_user_info_url: str | None = None, external_cookie_name: str | None = None, external_server_id: UUID | None = None, rbac_implementation_source: str | None = None, feature_gate_implementation_source: str | None = None, workload_manager_implementation_source: str | None = None, pipeline_run_auth_window: int = 2880, rate_limit_enabled: bool = False, login_rate_limit_minute: int = 5, login_rate_limit_day: int = 1000, secure_headers_server: Annotated[bool | str, \_PydanticGeneralMetadata(union_mode='left_to_right')] = True, secure_headers_hsts: Annotated[bool | str, \_PydanticGeneralMetadata(union_mode='left_to_right')] = 'max-age=63072000; includeSubdomains', secure_headers_xfo: Annotated[bool | str, \_PydanticGeneralMetadata(union_mode='left_to_right')] = 'SAMEORIGIN', secure_headers_xxp: Annotated[bool | str, \_PydanticGeneralMetadata(union_mode='left_to_right')] = '0', secure_headers_content: Annotated[bool | str, \_PydanticGeneralMetadata(union_mode='left_to_right')] = 'nosniff', secure_headers_csp: Annotated[bool | str, \_PydanticGeneralMetadata(union_mode='left_to_right')] = "default-src 'none'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://widgets-v3.featureos.app; connect-src 'self' https://sdkdocs.zenml.io https://analytics.zenml.io; img-src 'self' data: https://public-flavor-logos.s3.eu-central-1.amazonaws.com https://avatar.vercel.sh; style-src 'self' 'unsafe-inline'; base-uri 'self'; form-action 'self'; font-src 'self';frame-src https://zenml.hellonext.co https://sdkdocs.zenml.io https://widgets-v3.hellonext.co https://widgets-v3.featureos.app https://zenml.portal.trainn.co", secure_headers_referrer: Annotated[bool | str, \_PydanticGeneralMetadata(union_mode='left_to_right')] = 'no-referrer-when-downgrade', secure_headers_cache: Annotated[bool | str, \_PydanticGeneralMetadata(union_mode='left_to_right')] = 'no-store, no-cache, must-revalidate', secure_headers_permissions: Annotated[bool | str, \_PydanticGeneralMetadata(union_mode='left_to_right')] = 'accelerometer=(), autoplay=(), camera=(), encrypted-media=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), midi=(), payment=(), sync-xhr=(), usb=()', use_legacy_dashboard: bool = False, server_name: str = 'default', display_announcements: bool = True, display_updates: bool = True, auto_activate: bool = False, thread_pool_size: int = 40, \*\*extra_data: Any)

Bases: `BaseModel`

ZenML Server configuration attributes.

All these attributes can be set through the environment with the ZENML_SERVER_-Prefix.
The value of the ZENML_SERVER_DEPLOYMENT_TYPE environment variable will be extracted to deployment_type.

Attributes:
: deployment_type: The type of ZenML server deployment that is running.
  server_url: The URL where the ZenML server API is reachable. Must be
  <br/>
  > configured for features that involve triggering workloads from the
  > ZenML dashboard (e.g., running pipelines). If not specified, the
  > clients will use the same URL used to connect them to the ZenML
  > server.
  <br/>
  dashboard_url: The URL where the ZenML dashboard is reachable.
  : If not specified, the server_url value is used. This should be
    configured if the dashboard is served from a different URL than the
    ZenML server.
  <br/>
  root_url_path: The root URL path for the ZenML API and dashboard.
  auth_scheme: The authentication scheme used by the ZenML server.
  jwt_token_algorithm: The algorithm used to sign and verify JWT tokens.
  jwt_token_issuer: The issuer of the JWT tokens. If not specified, the
  <br/>
  > issuer is set to the ZenML Server ID.
  <br/>
  jwt_token_audience: The audience of the JWT tokens. If not specified,
  : the audience is set to the ZenML Server ID.
  <br/>
  jwt_token_leeway_seconds: The leeway in seconds allowed when verifying
  : the expiration time of JWT tokens.
  <br/>
  jwt_token_expire_minutes: The expiration time of JWT tokens in minutes.
  : If not specified, generated JWT tokens will not be set to expire.
  <br/>
  jwt_secret_key: The secret key used to sign and verify JWT tokens. If
  : not specified, a random secret key is generated.
  <br/>
  auth_cookie_name: The name of the http-only cookie used to store the JWT
  : token. If not specified, the cookie name is set to a value computed
    from the ZenML server ID.
  <br/>
  auth_cookie_domain: The domain of the http-only cookie used to store the
  : JWT token. If not specified, the cookie will be valid for the
    domain where the ZenML server is running.
  <br/>
  cors_allow_origins: The origins allowed to make cross-origin requests
  : to the ZenML server. If not specified, all origins are allowed.
  <br/>
  max_failed_device_auth_attempts: The maximum number of failed OAuth 2.0
  : device authentication attempts before the device is locked.
  <br/>
  device_auth_timeout: The timeout in seconds after which a pending OAuth
  : 2.0 device authorization request expires.
  <br/>
  device_auth_polling_interval: The polling interval in seconds used to
  : poll the OAuth 2.0 device authorization endpoint.
  <br/>
  device_expiration_minutes: The time in minutes that an OAuth 2.0 device is
  : allowed to be used to authenticate with the ZenML server. If not
    set or if jwt_token_expire_minutes is not set, the devices are
    allowed to be used indefinitely. This controls the expiration time
    of the JWT tokens issued to clients after they have authenticated
    with the ZenML server using an OAuth 2.0 device.
  <br/>
  trusted_device_expiration_minutes: The time in minutes that a trusted OAuth 2.0
  : device is allowed to be used to authenticate with the ZenML server.
    If not set or if jwt_token_expire_minutes is not set, the devices
    are allowed to be used indefinitely. This controls the expiration
    time of the JWT tokens issued to clients after they have
    authenticated with the ZenML server using an OAuth 2.0 device
    that has been marked as trusted.
  <br/>
  external_login_url: The login URL of an external authenticator service
  : to use with the EXTERNAL authentication scheme.
  <br/>
  external_user_info_url: The user info URL of an external authenticator
  : service to use with the EXTERNAL authentication scheme.
  <br/>
  external_cookie_name: The name of the http-only cookie used to store the
  : bearer token used to authenticate with the external authenticator
    service. Must be specified if the EXTERNAL authentication scheme
    is used.
  <br/>
  external_server_id: The ID of the ZenML server to use with the
  : EXTERNAL authentication scheme. If not specified, the regular
    ZenML server ID is used.
  <br/>
  metadata: Additional metadata to be associated with the ZenML server.
  rbac_implementation_source: Source pointing to a class implementing
  <br/>
  > the RBAC interface defined by
  > zenml.zen_server.rbac_interface.RBACInterface. If not specified,
  > RBAC will not be enabled for this server.
  <br/>
  feature_gate_implementation_source: Source pointing to a class
  : implementing the feature gate interface defined by
    zenml.zen_server.feature_gate.feature_gate_interface.FeatureGateInterface.
    If not specified, feature usage will not be gated/tracked for this
    server.
  <br/>
  workload_manager_implementation_source: Source pointing to a class
  : implementing the workload management interface.
  <br/>
  pipeline_run_auth_window: The default time window in minutes for which
  : a pipeline run action is allowed to authenticate with the ZenML
    server.
  <br/>
  login_rate_limit_minute: The number of login attempts allowed per minute.
  login_rate_limit_day: The number of login attempts allowed per day.
  secure_headers_server: Custom value to be set in the Server HTTP
  <br/>
  > header to identify the server. If not specified, or if set to one of
  > the reserved values enabled, yes, true, on, the Server
  > header will be set to the default value (ZenML server ID). If set to
  > one of the reserved values disabled, no, none, false, off
  > or to an empty string, the Server header will not be included in
  > responses.
  <br/>
  secure_headers_hsts: The server header value to be set in the HTTP
  : header Strict-Transport-Security. If not specified, or if set to
    one of the reserved values enabled, yes, true, on, the
    Strict-Transport-Security header will be set to the default value
    (max-age=63072000; includeSubdomains). If set to one of
    the reserved values disabled, no, none, false, off or to
    an empty string, the Strict-Transport-Security header will not be
    included in responses.
  <br/>
  secure_headers_xfo: The server header value to be set in the HTTP
  : header X-Frame-Options. If not specified, or if set to one of the
    reserved values enabled, yes, true, on, the X-Frame-Options
    header will be set to the default value (SAMEORIGIN). If set to
    one of the reserved values disabled, no, none, false, off
    or to an empty string, the X-Frame-Options header will not be
    included in responses.
  <br/>
  secure_headers_xxp: The server header value to be set in the HTTP
  : header X-XSS-Protection. If not specified, or if set to one of the
    reserved values enabled, yes, true, on, the X-XSS-Protection
    header will be set to the default value (0). If set to one of the
    reserved values disabled, no, none, false, off or
    to an empty string, the X-XSS-Protection header will not be
    included in responses. NOTE: this header is deprecated and should
    always be set to 0. The Content-Security-Policy header should be
    used instead.
  <br/>
  secure_headers_content: The server header value to be set in the HTTP
  : header X-Content-Type-Options. If not specified, or if set to one
    of the reserved values enabled, yes, true, on, the
    X-Content-Type-Options header will be set to the default value
    (nosniff). If set to one of the reserved values disabled, no,
    none, false, off or to an empty string, the
    X-Content-Type-Options header will not be included in responses.
  <br/>
  secure_headers_csp: The server header value to be set in the HTTP
  : header Content-Security-Policy. If not specified, or if set to one
    of the reserved values enabled, yes, true, on, the
    Content-Security-Policy header will be set to a default value
    that is compatible with the ZenML dashboard. If set to one of the
    reserved values disabled, no, none, false, off or to an
    empty string, the Content-Security-Policy header will not be
    included in responses.
  <br/>
  secure_headers_referrer: The server header value to be set in the HTTP
  : header Referrer-Policy. If not specified, or if set to one of the
    reserved values enabled, yes, true, on, the Referrer-Policy
    header will be set to the default value
    (no-referrer-when-downgrade). If set to one of the reserved values
    disabled, no, none, false, off or to an empty string, the
    Referrer-Policy header will not be included in responses.
  <br/>
  secure_headers_cache: The server header value to be set in the HTTP
  : header Cache-Control. If not specified, or if set to one of the
    reserved values enabled, yes, true, on, the Cache-Control
    header will be set to the default value
    (no-store, no-cache, must-revalidate). If set to one of the
    reserved values disabled, no, none, false, off or to an
    empty string, the Cache-Control header will not be included in
    responses.
  <br/>
  secure_headers_permissions: The server header value to be set in the
  : HTTP header Permissions-Policy. If not specified, or if set to one
    of the reserved values enabled, yes, true, on, the
    Permissions-Policy header will be set to the default value
    (accelerometer=(), camera=(), geolocation=(), gyroscope=(),
    magnetometer=(), microphone=(), payment=(), usb=()). If set to
    one of the reserved values disabled, no, none, false, off
    or to an empty string, the Permissions-Policy header will not be
    included in responses.
  <br/>
  use_legacy_dashboard: Whether to use the legacy dashboard. If set to
  : True, the dashboard will be used with the old UI. If set to
    False, the new dashboard will be used.
  <br/>
  server_name: The name of the ZenML server. Used only during initial
  : deployment. Can be changed later as a part of the server settings.
  <br/>
  display_announcements: Whether to display announcements about ZenML in
  : the dashboard. Used only during initial deployment. Can be changed
    later as a part of the server settings.
  <br/>
  display_updates: Whether to display notifications about ZenML updates in
  : the dashboard. Used only during initial deployment. Can be changed
    later as a part of the server settings.
  <br/>
  auto_activate: Whether to automatically activate the server and create a
  : default admin user account with an empty password during the initial
    deployment.

#### auth_cookie_domain *: str | None*

#### auth_cookie_name *: str | None*

#### auth_scheme *: [AuthScheme](zenml.md#zenml.enums.AuthScheme)*

#### auto_activate *: bool*

#### cors_allow_origins *: List[str] | None*

#### dashboard_url *: str | None*

#### *property* deployment_id *: UUID*

Get the ZenML server deployment ID.

Returns:
: The ZenML server deployment ID.

#### deployment_type *: [ServerDeploymentType](zenml.models.v2.misc.md#zenml.models.v2.misc.server_models.ServerDeploymentType)*

#### device_auth_polling_interval *: int*

#### device_auth_timeout *: int*

#### device_expiration_minutes *: int | None*

#### display_announcements *: bool*

#### display_updates *: bool*

#### external_cookie_name *: str | None*

#### external_login_url *: str | None*

#### external_server_id *: UUID | None*

#### external_user_info_url *: str | None*

#### *property* feature_gate_enabled *: bool*

Whether feature gating is enabled on the server or not.

Returns:
: Whether feature gating is enabled on the server or not.

#### feature_gate_implementation_source *: str | None*

#### get_auth_cookie_name() → str

Get the authentication cookie name.

If not configured, the cookie name is set to a value computed from the
ZenML server ID.

Returns:
: The authentication cookie name.

#### get_external_server_id() → UUID

Get the external server ID.

If not configured, the regular ZenML server ID is used.

Returns:
: The external server ID.

#### get_jwt_token_audience() → str

Get the JWT token audience.

If not configured, the audience is set to the ZenML Server ID.

Returns:
: The JWT token audience.

#### get_jwt_token_issuer() → str

Get the JWT token issuer.

If not configured, the issuer is set to the ZenML Server ID.

Returns:
: The JWT token issuer.

#### *classmethod* get_server_config() → [ServerConfiguration](#zenml.config.server_config.ServerConfiguration)

Get the server configuration.

Returns:
: The server configuration.

#### jwt_secret_key *: str*

#### jwt_token_algorithm *: str*

#### jwt_token_audience *: str | None*

#### jwt_token_expire_minutes *: int | None*

#### jwt_token_issuer *: str | None*

#### jwt_token_leeway_seconds *: int*

#### login_rate_limit_day *: int*

#### login_rate_limit_minute *: int*

#### max_failed_device_auth_attempts *: int*

#### metadata *: Dict[str, Any]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'auth_cookie_domain': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'auth_cookie_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'auth_scheme': FieldInfo(annotation=AuthScheme, required=False, default=<AuthScheme.OAUTH2_PASSWORD_BEARER: 'OAUTH2_PASSWORD_BEARER'>), 'auto_activate': FieldInfo(annotation=bool, required=False, default=False), 'cors_allow_origins': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None), 'dashboard_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'deployment_type': FieldInfo(annotation=ServerDeploymentType, required=False, default=<ServerDeploymentType.OTHER: 'other'>), 'device_auth_polling_interval': FieldInfo(annotation=int, required=False, default=5), 'device_auth_timeout': FieldInfo(annotation=int, required=False, default=300), 'device_expiration_minutes': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'display_announcements': FieldInfo(annotation=bool, required=False, default=True), 'display_updates': FieldInfo(annotation=bool, required=False, default=True), 'external_cookie_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'external_login_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'external_server_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None), 'external_user_info_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'feature_gate_implementation_source': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'jwt_secret_key': FieldInfo(annotation=str, required=False, default_factory=generate_jwt_secret_key), 'jwt_token_algorithm': FieldInfo(annotation=str, required=False, default='HS256'), 'jwt_token_audience': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'jwt_token_expire_minutes': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'jwt_token_issuer': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'jwt_token_leeway_seconds': FieldInfo(annotation=int, required=False, default=10), 'login_rate_limit_day': FieldInfo(annotation=int, required=False, default=1000), 'login_rate_limit_minute': FieldInfo(annotation=int, required=False, default=5), 'max_failed_device_auth_attempts': FieldInfo(annotation=int, required=False, default=3), 'metadata': FieldInfo(annotation=Dict[str, Any], required=False, default={}), 'pipeline_run_auth_window': FieldInfo(annotation=int, required=False, default=2880), 'rate_limit_enabled': FieldInfo(annotation=bool, required=False, default=False), 'rbac_implementation_source': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'root_url_path': FieldInfo(annotation=str, required=False, default=''), 'secure_headers_cache': FieldInfo(annotation=Union[bool, str], required=False, default='no-store, no-cache, must-revalidate', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'secure_headers_content': FieldInfo(annotation=Union[bool, str], required=False, default='nosniff', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'secure_headers_csp': FieldInfo(annotation=Union[bool, str], required=False, default="default-src 'none'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://widgets-v3.featureos.app; connect-src 'self' https://sdkdocs.zenml.io https://analytics.zenml.io; img-src 'self' data: https://public-flavor-logos.s3.eu-central-1.amazonaws.com https://avatar.vercel.sh; style-src 'self' 'unsafe-inline'; base-uri 'self'; form-action 'self'; font-src 'self';frame-src https://zenml.hellonext.co https://sdkdocs.zenml.io https://widgets-v3.hellonext.co https://widgets-v3.featureos.app https://zenml.portal.trainn.co", metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'secure_headers_hsts': FieldInfo(annotation=Union[bool, str], required=False, default='max-age=63072000; includeSubdomains', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'secure_headers_permissions': FieldInfo(annotation=Union[bool, str], required=False, default='accelerometer=(), autoplay=(), camera=(), encrypted-media=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), midi=(), payment=(), sync-xhr=(), usb=()', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'secure_headers_referrer': FieldInfo(annotation=Union[bool, str], required=False, default='no-referrer-when-downgrade', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'secure_headers_server': FieldInfo(annotation=Union[bool, str], required=False, default=True, metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'secure_headers_xfo': FieldInfo(annotation=Union[bool, str], required=False, default='SAMEORIGIN', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'secure_headers_xxp': FieldInfo(annotation=Union[bool, str], required=False, default='0', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'server_name': FieldInfo(annotation=str, required=False, default='default'), 'server_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'thread_pool_size': FieldInfo(annotation=int, required=False, default=40), 'trusted_device_expiration_minutes': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'use_legacy_dashboard': FieldInfo(annotation=bool, required=False, default=False), 'workload_manager_implementation_source': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

This function is meant to behave like a BaseModel method to initialise private attributes.

It takes context as an argument since that’s what pydantic-core passes when calling it.

Args:
: self: The BaseModel instance.
  context: The context.

#### pipeline_run_auth_window *: int*

#### rate_limit_enabled *: bool*

#### *property* rbac_enabled *: bool*

Whether RBAC is enabled on the server or not.

Returns:
: Whether RBAC is enabled on the server or not.

#### rbac_implementation_source *: str | None*

#### root_url_path *: str*

#### secure_headers_cache *: bool | str*

#### secure_headers_content *: bool | str*

#### secure_headers_csp *: bool | str*

#### secure_headers_hsts *: bool | str*

#### secure_headers_permissions *: bool | str*

#### secure_headers_referrer *: bool | str*

#### secure_headers_server *: bool | str*

#### secure_headers_xfo *: bool | str*

#### secure_headers_xxp *: bool | str*

#### server_name *: str*

#### server_url *: str | None*

#### thread_pool_size *: int*

#### trusted_device_expiration_minutes *: int | None*

#### use_legacy_dashboard *: bool*

#### *property* workload_manager_enabled *: bool*

Whether workload management is enabled on the server or not.

Returns:
: Whether workload management is enabled on the server or not.

#### workload_manager_implementation_source *: str | None*

### zenml.config.server_config.generate_jwt_secret_key() → str

Generate a random JWT secret key.

This key is used to sign and verify generated JWT tokens.

Returns:
: A random JWT secret key.

## zenml.config.settings_resolver module

Class for resolving settings.

### *class* zenml.config.settings_resolver.SettingsResolver(key: str, settings: [BaseSettings](#zenml.config.base_settings.BaseSettings))

Bases: `object`

Class for resolving settings.

This class converts a BaseSettings instance to the correct subclass
depending on the key for which these settings were specified.

#### resolve(stack: [Stack](zenml.stack.md#zenml.stack.stack.Stack)) → [BaseSettings](#zenml.config.base_settings.BaseSettings)

Resolves settings for the given stack.

Args:
: stack: The stack for which to resolve the settings.

Returns:
: The resolved settings.

## zenml.config.source module

Source classes.

### *class* zenml.config.source.CodeRepositorySource(\*, module: str, attribute: str | None = None, type: [SourceType](#zenml.config.source.SourceType) = SourceType.CODE_REPOSITORY, repository_id: UUID, commit: str, subdirectory: str, \*\*extra_data: Any)

Bases: [`Source`](#zenml.config.source.Source)

Source representing an object from a code repository.

Attributes:
: repository_id: The code repository ID.
  commit: The commit.
  subdirectory: The subdirectory of the source root inside the code
  <br/>
  > repository.

#### commit *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'attribute': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'commit': FieldInfo(annotation=str, required=True), 'module': FieldInfo(annotation=str, required=True), 'repository_id': FieldInfo(annotation=UUID, required=True), 'subdirectory': FieldInfo(annotation=str, required=True), 'type': FieldInfo(annotation=SourceType, required=False, default=<SourceType.CODE_REPOSITORY: 'code_repository'>)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### repository_id *: UUID*

#### subdirectory *: str*

#### type *: [SourceType](#zenml.config.source.SourceType)*

### *class* zenml.config.source.DistributionPackageSource(\*, module: str, attribute: str | None = None, type: [SourceType](#zenml.config.source.SourceType) = SourceType.DISTRIBUTION_PACKAGE, package_name: str, version: str | None = None, \*\*extra_data: Any)

Bases: [`Source`](#zenml.config.source.Source)

Source representing an object from a distribution package.

Attributes:
: package_name: Name of the package.
  version: The package version.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'attribute': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'module': FieldInfo(annotation=str, required=True), 'package_name': FieldInfo(annotation=str, required=True), 'type': FieldInfo(annotation=SourceType, required=False, default=<SourceType.DISTRIBUTION_PACKAGE: 'distribution_package'>), 'version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### package_name *: str*

#### type *: [SourceType](#zenml.config.source.SourceType)*

#### version *: str | None*

### *class* zenml.config.source.NotebookSource(\*, module: str, attribute: str | None = None, type: [SourceType](#zenml.config.source.SourceType) = SourceType.NOTEBOOK, replacement_module: str | None = None, artifact_store_id: UUID | None = None, \*\*extra_data: Any)

Bases: [`Source`](#zenml.config.source.Source)

Source representing an object defined in a notebook.

Attributes:
: replacement_module: Name of the module from which this source should
  : be loaded in case the code is not running in a notebook.
  <br/>
  artifact_store_id: ID of the artifact store in which the replacement
  : module code is stored.

#### artifact_store_id *: UUID | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'artifact_store_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None), 'attribute': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'module': FieldInfo(annotation=str, required=True), 'replacement_module': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'type': FieldInfo(annotation=SourceType, required=False, default=<SourceType.NOTEBOOK: 'notebook'>)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### replacement_module *: str | None*

#### type *: [SourceType](#zenml.config.source.SourceType)*

### *class* zenml.config.source.Source(\*, module: str, attribute: str | None = None, type: [SourceType](#zenml.config.source.SourceType), \*\*extra_data: Any)

Bases: `BaseModel`

Source specification.

A source specifies a module name as well as an optional attribute of that
module. These values can be used to import the module and get the value
of the attribute inside the module.

Example:
: The source Source(module=”zenml.config.source”, attribute=”Source”)
  references the class that this docstring is describing. This class is
  defined in the zenml.config.source module and the name of the
  attribute is the class name Source.

Attributes:
: module: The module name.
  attribute: Optional name of the attribute inside the module.
  type: The type of the source.

#### attribute *: str | None*

#### *classmethod* from_import_path(import_path: str, is_module_path: bool = False) → [Source](#zenml.config.source.Source)

Creates a source from an import path.

Args:
: import_path: The import path.
  is_module_path: If the import path points to a module or not.

Raises:
: ValueError: If the import path is empty.

Returns:
: The source.

#### *property* import_path *: str*

The import path of the source.

Returns:
: The import path of the source.

#### *property* is_internal *: bool*

If the source is internal (=from the zenml package).

Returns:
: True if the source is internal, False otherwise

#### *property* is_module_source *: bool*

If the source is a module source.

Returns:
: If the source is a module source.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_dump(\*\*kwargs: Any) → Dict[str, Any]

Dump the source as a dictionary.

Args:
: ```
  **
  ```
  <br/>
  kwargs: Additional keyword arguments.

Returns:
: The source as a dictionary.

#### model_dump_json(\*\*kwargs: Any) → str

Dump the source as a JSON string.

Args:
: ```
  **
  ```
  <br/>
  kwargs: Additional keyword arguments.

Returns:
: The source as a JSON string.

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'attribute': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'module': FieldInfo(annotation=str, required=True), 'type': FieldInfo(annotation=SourceType, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### module *: str*

#### type *: [SourceType](#zenml.config.source.SourceType)*

### *class* zenml.config.source.SourceType(value, names=None, \*, module=None, qualname=None, type=None, start=1, boundary=None)

Bases: `Enum`

Enum representing different types of sources.

#### BUILTIN *= 'builtin'*

#### CODE_REPOSITORY *= 'code_repository'*

#### DISTRIBUTION_PACKAGE *= 'distribution_package'*

#### INTERNAL *= 'internal'*

#### NOTEBOOK *= 'notebook'*

#### UNKNOWN *= 'unknown'*

#### USER *= 'user'*

### zenml.config.source.convert_source(source: Any) → Any

Converts an old source string to a source object.

Args:
: source: Source string or object.

Returns:
: The converted source.

## zenml.config.step_configurations module

Pipeline configuration classes.

### *class* zenml.config.step_configurations.ArtifactConfiguration(\*, materializer_source: Tuple[Annotated[[Source](#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)], ...], default_materializer_source: Annotated[[Source](#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)] | None = None)

Bases: [`PartialArtifactConfiguration`](#zenml.config.step_configurations.PartialArtifactConfiguration)

Class representing a complete input/output artifact configuration.

#### materializer_source *: Tuple[Annotated[[Source](#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)], ...]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'default_materializer_source': FieldInfo(annotation=Union[Annotated[Source, SerializeAsAny, BeforeValidator], NoneType], required=False, default=None), 'materializer_source': FieldInfo(annotation=Tuple[Annotated[Source, SerializeAsAny, BeforeValidator], ...], required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.config.step_configurations.InputSpec(\*, step_name: str, output_name: str)

Bases: [`StrictBaseModel`](#zenml.config.strict_base_model.StrictBaseModel)

Step input specification.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'output_name': FieldInfo(annotation=str, required=True), 'step_name': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### output_name *: str*

#### step_name *: str*

### *class* zenml.config.step_configurations.PartialArtifactConfiguration(\*, materializer_source: Tuple[Annotated[[Source](#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)], ...] | None = None, default_materializer_source: Annotated[[Source](#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)] | None = None)

Bases: [`StrictBaseModel`](#zenml.config.strict_base_model.StrictBaseModel)

Class representing a partial input/output artifact configuration.

#### default_materializer_source *: Annotated[[Source](#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)] | None*

#### materializer_source *: Tuple[Annotated[[Source](#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)], ...] | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'default_materializer_source': FieldInfo(annotation=Union[Annotated[Source, SerializeAsAny, BeforeValidator], NoneType], required=False, default=None), 'materializer_source': FieldInfo(annotation=Union[Tuple[Annotated[Source, SerializeAsAny, BeforeValidator], ...], NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.config.step_configurations.PartialStepConfiguration(\*, name: str, enable_cache: bool | None = None, enable_artifact_metadata: bool | None = None, enable_artifact_visualization: bool | None = None, enable_step_logs: bool | None = None, step_operator: str | None = None, experiment_tracker: str | None = None, parameters: Dict[str, Any] = {}, settings: Dict[str, Annotated[[BaseSettings](#zenml.config.base_settings.BaseSettings), SerializeAsAny()]] = {}, extra: Dict[str, Any] = {}, failure_hook_source: Annotated[[Source](#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)] | None = None, success_hook_source: Annotated[[Source](#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)] | None = None, model: [Model](zenml.model.md#zenml.model.model.Model) | None = None, retry: [StepRetryConfig](#zenml.config.retry_config.StepRetryConfig) | None = None, outputs: Mapping[str, [PartialArtifactConfiguration](#zenml.config.step_configurations.PartialArtifactConfiguration)] = {}, caching_parameters: Mapping[str, Any] = {}, external_input_artifacts: Mapping[str, [ExternalArtifactConfiguration](zenml.artifacts.md#zenml.artifacts.external_artifact_config.ExternalArtifactConfiguration)] = {}, model_artifacts_or_metadata: Mapping[str, [ModelVersionDataLazyLoader](zenml.model.md#zenml.model.lazy_load.ModelVersionDataLazyLoader)] = {}, client_lazy_loaders: Mapping[str, [ClientLazyLoader](zenml.md#zenml.client_lazy_loader.ClientLazyLoader)] = {})

Bases: [`StepConfigurationUpdate`](#zenml.config.step_configurations.StepConfigurationUpdate)

Class representing a partial step configuration.

#### caching_parameters *: Mapping[str, Any]*

#### client_lazy_loaders *: Mapping[str, [ClientLazyLoader](zenml.md#zenml.client_lazy_loader.ClientLazyLoader)]*

#### external_input_artifacts *: Mapping[str, [ExternalArtifactConfiguration](zenml.artifacts.md#zenml.artifacts.external_artifact_config.ExternalArtifactConfiguration)]*

#### model_artifacts_or_metadata *: Mapping[str, [ModelVersionDataLazyLoader](zenml.model.md#zenml.model.lazy_load.ModelVersionDataLazyLoader)]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True, 'protected_namespaces': ()}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'caching_parameters': FieldInfo(annotation=Mapping[str, Any], required=False, default={}), 'client_lazy_loaders': FieldInfo(annotation=Mapping[str, ClientLazyLoader], required=False, default={}), 'enable_artifact_metadata': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None), 'enable_artifact_visualization': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None), 'enable_cache': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None), 'enable_step_logs': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None), 'experiment_tracker': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'external_input_artifacts': FieldInfo(annotation=Mapping[str, ExternalArtifactConfiguration], required=False, default={}), 'extra': FieldInfo(annotation=Dict[str, Any], required=False, default={}), 'failure_hook_source': FieldInfo(annotation=Union[Annotated[Source, SerializeAsAny, BeforeValidator], NoneType], required=False, default=None), 'model': FieldInfo(annotation=Union[Model, NoneType], required=False, default=None), 'model_artifacts_or_metadata': FieldInfo(annotation=Mapping[str, ModelVersionDataLazyLoader], required=False, default={}), 'name': FieldInfo(annotation=str, required=True), 'outputs': FieldInfo(annotation=Mapping[str, PartialArtifactConfiguration], required=False, default={}), 'parameters': FieldInfo(annotation=Dict[str, Any], required=False, default={}), 'retry': FieldInfo(annotation=Union[StepRetryConfig, NoneType], required=False, default=None), 'settings': FieldInfo(annotation=Dict[str, Annotated[BaseSettings, SerializeAsAny]], required=False, default={}), 'step_operator': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'success_hook_source': FieldInfo(annotation=Union[Annotated[Source, SerializeAsAny, BeforeValidator], NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### outputs *: Mapping[str, [PartialArtifactConfiguration](#zenml.config.step_configurations.PartialArtifactConfiguration)]*

### *class* zenml.config.step_configurations.Step(\*, spec: [StepSpec](#zenml.config.step_configurations.StepSpec), config: [StepConfiguration](#zenml.config.step_configurations.StepConfiguration))

Bases: [`StrictBaseModel`](#zenml.config.strict_base_model.StrictBaseModel)

Class representing a ZenML step.

#### config *: [StepConfiguration](#zenml.config.step_configurations.StepConfiguration)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'config': FieldInfo(annotation=StepConfiguration, required=True), 'spec': FieldInfo(annotation=StepSpec, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### spec *: [StepSpec](#zenml.config.step_configurations.StepSpec)*

### *class* zenml.config.step_configurations.StepConfiguration(\*, name: str, enable_cache: bool | None = None, enable_artifact_metadata: bool | None = None, enable_artifact_visualization: bool | None = None, enable_step_logs: bool | None = None, step_operator: str | None = None, experiment_tracker: str | None = None, parameters: Dict[str, Any] = {}, settings: Dict[str, Annotated[[BaseSettings](#zenml.config.base_settings.BaseSettings), SerializeAsAny()]] = {}, extra: Dict[str, Any] = {}, failure_hook_source: Annotated[[Source](#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)] | None = None, success_hook_source: Annotated[[Source](#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)] | None = None, model: [Model](zenml.model.md#zenml.model.model.Model) | None = None, retry: [StepRetryConfig](#zenml.config.retry_config.StepRetryConfig) | None = None, outputs: Mapping[str, [ArtifactConfiguration](#zenml.config.step_configurations.ArtifactConfiguration)] = {}, caching_parameters: Mapping[str, Any] = {}, external_input_artifacts: Mapping[str, [ExternalArtifactConfiguration](zenml.artifacts.md#zenml.artifacts.external_artifact_config.ExternalArtifactConfiguration)] = {}, model_artifacts_or_metadata: Mapping[str, [ModelVersionDataLazyLoader](zenml.model.md#zenml.model.lazy_load.ModelVersionDataLazyLoader)] = {}, client_lazy_loaders: Mapping[str, [ClientLazyLoader](zenml.md#zenml.client_lazy_loader.ClientLazyLoader)] = {})

Bases: [`PartialStepConfiguration`](#zenml.config.step_configurations.PartialStepConfiguration)

Step configuration class.

#### *property* docker_settings *: [DockerSettings](#zenml.config.docker_settings.DockerSettings)*

Docker settings of this step configuration.

Returns:
: The Docker settings of this step configuration.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True, 'protected_namespaces': ()}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'caching_parameters': FieldInfo(annotation=Mapping[str, Any], required=False, default={}), 'client_lazy_loaders': FieldInfo(annotation=Mapping[str, ClientLazyLoader], required=False, default={}), 'enable_artifact_metadata': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None), 'enable_artifact_visualization': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None), 'enable_cache': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None), 'enable_step_logs': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None), 'experiment_tracker': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'external_input_artifacts': FieldInfo(annotation=Mapping[str, ExternalArtifactConfiguration], required=False, default={}), 'extra': FieldInfo(annotation=Dict[str, Any], required=False, default={}), 'failure_hook_source': FieldInfo(annotation=Union[Annotated[Source, SerializeAsAny, BeforeValidator], NoneType], required=False, default=None), 'model': FieldInfo(annotation=Union[Model, NoneType], required=False, default=None), 'model_artifacts_or_metadata': FieldInfo(annotation=Mapping[str, ModelVersionDataLazyLoader], required=False, default={}), 'name': FieldInfo(annotation=str, required=True), 'outputs': FieldInfo(annotation=Mapping[str, ArtifactConfiguration], required=False, default={}), 'parameters': FieldInfo(annotation=Dict[str, Any], required=False, default={}), 'retry': FieldInfo(annotation=Union[StepRetryConfig, NoneType], required=False, default=None), 'settings': FieldInfo(annotation=Dict[str, Annotated[BaseSettings, SerializeAsAny]], required=False, default={}), 'step_operator': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'success_hook_source': FieldInfo(annotation=Union[Annotated[Source, SerializeAsAny, BeforeValidator], NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### outputs *: Mapping[str, [ArtifactConfiguration](#zenml.config.step_configurations.ArtifactConfiguration)]*

#### *property* resource_settings *: [ResourceSettings](#zenml.config.resource_settings.ResourceSettings)*

Resource settings of this step configuration.

Returns:
: The resource settings of this step configuration.

### *class* zenml.config.step_configurations.StepConfigurationUpdate(\*, name: str | None = None, enable_cache: bool | None = None, enable_artifact_metadata: bool | None = None, enable_artifact_visualization: bool | None = None, enable_step_logs: bool | None = None, step_operator: str | None = None, experiment_tracker: str | None = None, parameters: Dict[str, Any] = {}, settings: Dict[str, Annotated[[BaseSettings](#zenml.config.base_settings.BaseSettings), SerializeAsAny()]] = {}, extra: Dict[str, Any] = {}, failure_hook_source: Annotated[[Source](#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)] | None = None, success_hook_source: Annotated[[Source](#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)] | None = None, model: [Model](zenml.model.md#zenml.model.model.Model) | None = None, retry: [StepRetryConfig](#zenml.config.retry_config.StepRetryConfig) | None = None, outputs: Mapping[str, [PartialArtifactConfiguration](#zenml.config.step_configurations.PartialArtifactConfiguration)] = {})

Bases: [`StrictBaseModel`](#zenml.config.strict_base_model.StrictBaseModel)

Class for step configuration updates.

#### enable_artifact_metadata *: bool | None*

#### enable_artifact_visualization *: bool | None*

#### enable_cache *: bool | None*

#### enable_step_logs *: bool | None*

#### experiment_tracker *: str | None*

#### extra *: Dict[str, Any]*

#### failure_hook_source *: Annotated[[Source](#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)] | None*

#### model *: [Model](zenml.model.md#zenml.model.model.Model) | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'enable_artifact_metadata': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None), 'enable_artifact_visualization': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None), 'enable_cache': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None), 'enable_step_logs': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None), 'experiment_tracker': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'extra': FieldInfo(annotation=Dict[str, Any], required=False, default={}), 'failure_hook_source': FieldInfo(annotation=Union[Annotated[Source, SerializeAsAny, BeforeValidator], NoneType], required=False, default=None), 'model': FieldInfo(annotation=Union[Model, NoneType], required=False, default=None), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'outputs': FieldInfo(annotation=Mapping[str, PartialArtifactConfiguration], required=False, default={}), 'parameters': FieldInfo(annotation=Dict[str, Any], required=False, default={}), 'retry': FieldInfo(annotation=Union[StepRetryConfig, NoneType], required=False, default=None), 'settings': FieldInfo(annotation=Dict[str, Annotated[BaseSettings, SerializeAsAny]], required=False, default={}), 'step_operator': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'success_hook_source': FieldInfo(annotation=Union[Annotated[Source, SerializeAsAny, BeforeValidator], NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str | None*

#### outputs *: Mapping[str, [PartialArtifactConfiguration](#zenml.config.step_configurations.PartialArtifactConfiguration)]*

#### parameters *: Dict[str, Any]*

#### retry *: [StepRetryConfig](#zenml.config.retry_config.StepRetryConfig) | None*

#### settings *: Dict[str, Annotated[[BaseSettings](#zenml.config.base_settings.BaseSettings), SerializeAsAny()]]*

#### step_operator *: str | None*

#### success_hook_source *: Annotated[[Source](#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)] | None*

### *class* zenml.config.step_configurations.StepSpec(\*, source: Annotated[[Source](#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)], upstream_steps: List[str], inputs: Dict[str, [InputSpec](#zenml.config.step_configurations.InputSpec)] = {}, pipeline_parameter_name: str = '')

Bases: [`StrictBaseModel`](#zenml.config.strict_base_model.StrictBaseModel)

Specification of a pipeline.

#### inputs *: Dict[str, [InputSpec](#zenml.config.step_configurations.InputSpec)]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'inputs': FieldInfo(annotation=Dict[str, InputSpec], required=False, default={}), 'pipeline_parameter_name': FieldInfo(annotation=str, required=False, default=''), 'source': FieldInfo(annotation=Source, required=True, metadata=[SerializeAsAny(), BeforeValidator(func=<function convert_source>)]), 'upstream_steps': FieldInfo(annotation=List[str], required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### pipeline_parameter_name *: str*

#### source *: Annotated[[Source](#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)]*

#### upstream_steps *: List[str]*

## zenml.config.step_run_info module

Step run info.

### *class* zenml.config.step_run_info.StepRunInfo(\*, step_run_id: UUID, run_id: UUID, run_name: str, pipeline_step_name: str, config: [StepConfiguration](#zenml.config.step_configurations.StepConfiguration), pipeline: [PipelineConfiguration](#zenml.config.pipeline_configurations.PipelineConfiguration), force_write_logs: Callable[[...], Any])

Bases: [`StrictBaseModel`](#zenml.config.strict_base_model.StrictBaseModel)

All information necessary to run a step.

#### config *: [StepConfiguration](#zenml.config.step_configurations.StepConfiguration)*

#### force_write_logs *: Callable[[...], Any]*

#### get_image(key: str) → str

Gets the Docker image for the given key.

Args:
: key: The key for which to get the image.

Raises:
: RuntimeError: If the run does not have an associated build.

Returns:
: The image name or digest.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'config': FieldInfo(annotation=StepConfiguration, required=True), 'force_write_logs': FieldInfo(annotation=Callable[..., Any], required=True), 'pipeline': FieldInfo(annotation=PipelineConfiguration, required=True), 'pipeline_step_name': FieldInfo(annotation=str, required=True), 'run_id': FieldInfo(annotation=UUID, required=True), 'run_name': FieldInfo(annotation=str, required=True), 'step_run_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### pipeline *: [PipelineConfiguration](#zenml.config.pipeline_configurations.PipelineConfiguration)*

#### pipeline_step_name *: str*

#### run_id *: UUID*

#### run_name *: str*

#### step_run_id *: UUID*

## zenml.config.store_config module

Functionality to support ZenML store configurations.

### *class* zenml.config.store_config.StoreConfiguration(\*, type: [StoreType](zenml.md#zenml.enums.StoreType), url: str, secrets_store: Annotated[[SecretsStoreConfiguration](#zenml.config.secrets_store_config.SecretsStoreConfiguration), SerializeAsAny()] | None = None, backup_secrets_store: Annotated[[SecretsStoreConfiguration](#zenml.config.secrets_store_config.SecretsStoreConfiguration), SerializeAsAny()] | None = None, \*\*extra_data: Any)

Bases: `BaseModel`

Generic store configuration.

The store configurations of concrete store implementations must inherit from
this class and validate any extra attributes that are configured in addition
to those defined in this class.

Attributes:
: type: The type of store backend.
  url: The URL of the store backend.
  secrets_store: The configuration of the secrets store to use to store
  <br/>
  > secrets. If not set, secrets management is disabled.
  <br/>
  backup_secrets_store: The configuration of the secrets store to use to
  : store backups of secrets. If not set, backup and restore of secrets
    are disabled.

#### backup_secrets_store *: Annotated[[SecretsStoreConfiguration](#zenml.config.secrets_store_config.SecretsStoreConfiguration), SerializeAsAny()] | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'backup_secrets_store': FieldInfo(annotation=Union[Annotated[SecretsStoreConfiguration, SerializeAsAny], NoneType], required=False, default=None), 'secrets_store': FieldInfo(annotation=Union[Annotated[SecretsStoreConfiguration, SerializeAsAny], NoneType], required=False, default=None), 'type': FieldInfo(annotation=StoreType, required=True), 'url': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### secrets_store *: Annotated[[SecretsStoreConfiguration](#zenml.config.secrets_store_config.SecretsStoreConfiguration), SerializeAsAny()] | None*

#### *classmethod* supports_url_scheme(url: str) → bool

Check if a URL scheme is supported by this store.

Concrete store configuration classes should override this method to
check if a URL scheme is supported by the store.

Args:
: url: The URL to check.

Returns:
: True if the URL scheme is supported, False otherwise.

#### type *: [StoreType](zenml.md#zenml.enums.StoreType)*

#### url *: str*

#### *classmethod* validate_store_config(data: Any, validation_info: ValidationInfo) → Any

Wrapper method to handle the raw data.

Args:
: cls: the class handler
  data: the raw input data
  validation_info: the context of the validation.

Returns:
: the validated data

## zenml.config.strict_base_model module

Strict immutable pydantic model.

### *class* zenml.config.strict_base_model.StrictBaseModel

Bases: `BaseModel`

Immutable pydantic model which prevents extra attributes.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

## Module contents

The config module contains classes and functions that manage user-specific configuration.

ZenML’s configuration is stored in a file called
`config.yaml`, located on the user’s directory for configuration files.
(The exact location differs from operating system to operating system.)

The `GlobalConfiguration` class is the main class in this module. It provides
a Pydantic configuration object that is used to store and retrieve
configuration. This `GlobalConfiguration` object handles the serialization and
deserialization of the configuration options that are stored in the file in
order to persist the configuration across sessions.

### *class* zenml.config.DockerSettings(warn_about_plain_text_secrets: bool = False, \*, parent_image: str | None = None, dockerfile: str | None = None, build_context_root: str | None = None, parent_image_build_config: [DockerBuildConfig](#zenml.config.docker_settings.DockerBuildConfig) | None = None, skip_build: bool = False, prevent_build_reuse: bool = False, target_repository: str | None = None, python_package_installer: [PythonPackageInstaller](#zenml.config.docker_settings.PythonPackageInstaller) = PythonPackageInstaller.PIP, python_package_installer_args: Dict[str, Any] = {}, replicate_local_python_environment: Annotated[List[str] | [PythonEnvironmentExportMethod](#zenml.config.docker_settings.PythonEnvironmentExportMethod) | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, requirements: Annotated[None | str | List[str], \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, required_integrations: List[str] = [], install_stack_requirements: bool = True, apt_packages: List[str] = [], environment: Dict[str, Any] = {}, user: str | None = None, build_config: [DockerBuildConfig](#zenml.config.docker_settings.DockerBuildConfig) | None = None, allow_including_files_in_images: bool = True, allow_download_from_code_repository: bool = True, allow_download_from_artifact_store: bool = True, build_options: Dict[str, Any] = {}, dockerignore: str | None = None, copy_files: bool = True, copy_global_config: bool = True, source_files: str | None = None, required_hub_plugins: List[str] = [])

Bases: [`BaseSettings`](#zenml.config.base_settings.BaseSettings)

Settings for building Docker images to run ZenML pipelines.

### Build process:

* No dockerfile specified: If any of the options regarding

requirements, environment variables or copying files require us to build an
image, ZenML will build this image. Otherwise, the parent_image will be
used to run the pipeline.
\* dockerfile specified: ZenML will first build an image based on the
specified Dockerfile. If any of the options regarding
requirements, environment variables or copying files require an additional
image built on top of that, ZenML will build a second image. If not, the
image build from the specified Dockerfile will be used to run the pipeline.

### Requirements installation order:

Depending on the configuration of this object, requirements will be
installed in the following order (each step optional):
- The packages installed in your local python environment
- The packages required by the stack unless this is disabled by setting

> install_stack_requirements=False.
- The packages specified via the required_integrations
- The packages specified via the requirements attribute

Attributes:
: parent_image: Full name of the Docker image that should be
  : used as the parent for the image that will be built. Defaults to
    a ZenML image built for the active Python and ZenML version.
    <br/>
    Additional notes:
    \* If you specify a custom image here, you need to make sure it has
    ZenML installed.
    \* If this is a non-local image, the environment which is running
    the pipeline and building the Docker image needs to be able to pull
    this image.
    \* If a custom dockerfile is specified for this settings
    object, this parent image will be ignored.
  <br/>
  dockerfile: Path to a custom Dockerfile that should be built. Depending
  : on the other values you specify in this object, the resulting
    image will be used directly to run your pipeline or ZenML will use
    it as a parent image to build on top of. See the general docstring
    of this class for more information.
    <br/>
    Additional notes:
    \* If you specify this, the parent_image attribute will be ignored.
    \* If you specify this, the image built from this Dockerfile needs
    to have ZenML installed.
  <br/>
  build_context_root: Build context root for the Docker build, only used
  : when the dockerfile attribute is set. If this is left empty, the
    build context will only contain the Dockerfile.
  <br/>
  parent_image_build_config: Configuration for the parent image build.
  skip_build: If set to True, the parent image will be used directly to
  <br/>
  > run the steps of your pipeline.
  <br/>
  prevent_build_reuse: Prevent the reuse of an existing build.
  target_repository: Name of the Docker repository to which the
  <br/>
  > image should be pushed. This repository will be appended to the
  > registry URI of the container registry of your stack and should
  > therefore **not** include any registry. If not specified, the
  > default repository name configured in the container registry
  > stack component settings will be used.
  <br/>
  python_package_installer: The package installer to use for python
  : packages.
  <br/>
  python_package_installer_args: Arguments to pass to the python package
  : installer.
  <br/>
  replicate_local_python_environment: If not None, ZenML will use the
  : specified method to generate a requirements file that replicates
    the packages installed in the currently running python environment.
    This requirements file will then be installed in the Docker image.
  <br/>
  requirements: Path to a requirements file or a list of required pip
  : packages. During the image build, these requirements will be
    installed using pip. If you need to use a different tool to
    resolve and/or install your packages, please use a custom parent
    image or specify a custom dockerfile.
  <br/>
  required_integrations: List of ZenML integrations that should be
  : installed. All requirements for the specified integrations will
    be installed inside the Docker image.
  <br/>
  required_hub_plugins: DEPRECATED/UNUSED.
  install_stack_requirements: If True, ZenML will automatically detect
  <br/>
  > if components of your active stack are part of a ZenML integration
  > and install the corresponding requirements and apt packages.
  > If you set this to False or use custom components in your stack,
  > you need to make sure these get installed by specifying them in
  > the requirements and apt_packages attributes.
  <br/>
  apt_packages: APT packages to install inside the Docker image.
  environment: Dictionary of environment variables to set inside the
  <br/>
  > Docker image.
  <br/>
  build_config: Configuration for the main image build.
  user: If not None, will set the user, make it owner of the /app
  <br/>
  > directory which contains all the user code and run the container
  > entrypoint as this user.
  <br/>
  allow_including_files_in_images: If True, code can be included in the
  : Docker images if code download from a code repository or artifact
    store is disabled or not possible.
  <br/>
  allow_download_from_code_repository: If True, code can be downloaded
  : from a code repository if possible.
  <br/>
  allow_download_from_artifact_store: If True, code can be downloaded
  : from the artifact store.
  <br/>
  build_options: DEPRECATED, use parent_image_build_config.build_options
  : instead.
  <br/>
  dockerignore: DEPRECATED, use build_config.dockerignore instead.
  copy_files: DEPRECATED/UNUSED.
  copy_global_config: DEPRECATED/UNUSED.
  source_files: DEPRECATED. Use allow_including_files_in_images,
  <br/>
  > allow_download_from_code_repository and
  > allow_download_from_artifact_store instead.

#### allow_download_from_artifact_store *: bool*

#### allow_download_from_code_repository *: bool*

#### allow_including_files_in_images *: bool*

#### apt_packages *: List[str]*

#### build_config *: [DockerBuildConfig](#zenml.config.docker_settings.DockerBuildConfig) | None*

#### build_context_root *: str | None*

#### build_options *: Dict[str, Any]*

#### copy_files *: bool*

#### copy_global_config *: bool*

#### dockerfile *: str | None*

#### dockerignore *: str | None*

#### environment *: Dict[str, Any]*

#### install_stack_requirements *: bool*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'allow_download_from_artifact_store': FieldInfo(annotation=bool, required=False, default=True), 'allow_download_from_code_repository': FieldInfo(annotation=bool, required=False, default=True), 'allow_including_files_in_images': FieldInfo(annotation=bool, required=False, default=True), 'apt_packages': FieldInfo(annotation=List[str], required=False, default=[]), 'build_config': FieldInfo(annotation=Union[DockerBuildConfig, NoneType], required=False, default=None), 'build_context_root': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'build_options': FieldInfo(annotation=Dict[str, Any], required=False, default={}), 'copy_files': FieldInfo(annotation=bool, required=False, default=True), 'copy_global_config': FieldInfo(annotation=bool, required=False, default=True), 'dockerfile': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'dockerignore': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'environment': FieldInfo(annotation=Dict[str, Any], required=False, default={}), 'install_stack_requirements': FieldInfo(annotation=bool, required=False, default=True), 'parent_image': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'parent_image_build_config': FieldInfo(annotation=Union[DockerBuildConfig, NoneType], required=False, default=None), 'prevent_build_reuse': FieldInfo(annotation=bool, required=False, default=False), 'python_package_installer': FieldInfo(annotation=PythonPackageInstaller, required=False, default=<PythonPackageInstaller.PIP: 'pip'>), 'python_package_installer_args': FieldInfo(annotation=Dict[str, Any], required=False, default={}), 'replicate_local_python_environment': FieldInfo(annotation=Union[List[str], PythonEnvironmentExportMethod, NoneType], required=False, default=None, metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'required_hub_plugins': FieldInfo(annotation=List[str], required=False, default=[]), 'required_integrations': FieldInfo(annotation=List[str], required=False, default=[]), 'requirements': FieldInfo(annotation=Union[NoneType, str, List[str]], required=False, default=None, metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'skip_build': FieldInfo(annotation=bool, required=False, default=False), 'source_files': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'target_repository': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'user': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### parent_image *: str | None*

#### parent_image_build_config *: [DockerBuildConfig](#zenml.config.docker_settings.DockerBuildConfig) | None*

#### prevent_build_reuse *: bool*

#### python_package_installer *: [PythonPackageInstaller](#zenml.config.docker_settings.PythonPackageInstaller)*

#### python_package_installer_args *: Dict[str, Any]*

#### replicate_local_python_environment *: List[str] | [PythonEnvironmentExportMethod](#zenml.config.docker_settings.PythonEnvironmentExportMethod) | None*

#### required_hub_plugins *: List[str]*

#### required_integrations *: List[str]*

#### requirements *: None | str | List[str]*

#### skip_build *: bool*

#### source_files *: str | None*

#### target_repository *: str | None*

#### user *: str | None*

### *class* zenml.config.ResourceSettings(warn_about_plain_text_secrets: bool = False, \*, cpu_count: Annotated[float, Gt(gt=0)] | None = None, gpu_count: Annotated[int, Ge(ge=0)] | None = None, memory: Annotated[str | None, \_PydanticGeneralMetadata(pattern='^[0-9]+(KB|KiB|MB|MiB|GB|GiB|TB|TiB|PB|PiB)$')] = None)

Bases: [`BaseSettings`](#zenml.config.base_settings.BaseSettings)

Hardware resource settings.

Attributes:
: cpu_count: The amount of CPU cores that should be configured.
  gpu_count: The amount of GPUs that should be configured.
  memory: The amount of memory that should be configured.

#### cpu_count *: Annotated[float, Gt(gt=0)] | None*

#### *property* empty *: bool*

Returns if this object is “empty” (=no values configured) or not.

Returns:
: True if no values were configured, False otherwise.

#### get_memory(unit: str | [ByteUnit](#zenml.config.resource_settings.ByteUnit) = ByteUnit.GB) → float | None

Gets the memory configuration in a specific unit.

Args:
: unit: The unit to which the memory should be converted.

Raises:
: ValueError: If the memory string is invalid.

Returns:
: The memory configuration converted to the requested unit, or None
  if no memory was configured.

#### gpu_count *: Annotated[int, Ge(ge=0)] | None*

#### memory *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'cpu_count': FieldInfo(annotation=Union[Annotated[float, Gt], NoneType], required=False, default=None), 'gpu_count': FieldInfo(annotation=Union[Annotated[int, Ge], NoneType], required=False, default=None), 'memory': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, metadata=[_PydanticGeneralMetadata(pattern='^[0-9]+(KB|KiB|MB|MiB|GB|GiB|TB|TiB|PB|PiB)$')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.config.StepRetryConfig(\*, max_retries: int = 1, delay: int = 0, backoff: int = 0)

Bases: [`StrictBaseModel`](#zenml.config.strict_base_model.StrictBaseModel)

Retry configuration for a step.

Delay is an integer (specified in seconds).

#### backoff *: int*

#### delay *: int*

#### max_retries *: int*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'backoff': FieldInfo(annotation=int, required=False, default=0), 'delay': FieldInfo(annotation=int, required=False, default=0), 'max_retries': FieldInfo(annotation=int, required=False, default=1)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.
