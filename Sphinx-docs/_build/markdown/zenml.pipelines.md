# zenml.pipelines package

## Submodules

## zenml.pipelines.base_pipeline module

Legacy ZenML pipeline class definition.

### *class* zenml.pipelines.base_pipeline.BasePipeline(\*args: Any, \*\*kwargs: Any)

Bases: [`Pipeline`](zenml.new.pipelines.md#zenml.new.pipelines.pipeline.Pipeline), `ABC`

Legacy pipeline class.

#### *abstract* connect(\*args: [BaseStep](zenml.steps.md#zenml.steps.base_step.BaseStep), \*\*kwargs: [BaseStep](zenml.steps.md#zenml.steps.base_step.BaseStep)) → None

Abstract method that connects the pipeline steps.

Args:
: ```
  *
  ```
  <br/>
  args: Connect method arguments.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Connect method keyword arguments.

#### resolve() → [Source](zenml.config.md#zenml.config.source.Source)

Resolves the pipeline.

Returns:
: The pipeline source.

#### run(\*, run_name: str | None = None, enable_cache: bool | None = None, enable_artifact_metadata: bool | None = None, enable_artifact_visualization: bool | None = None, enable_step_logs: bool | None = None, schedule: [Schedule](zenml.config.md#zenml.config.schedule.Schedule) | None = None, build: str | UUID | [PipelineBuildBase](zenml.models.md#zenml.models.PipelineBuildBase) | None = None, settings: Mapping[str, SettingsOrDict] | None = None, step_configurations: Mapping[str, StepConfigurationUpdateOrDict] | None = None, extra: Dict[str, Any] | None = None, config_path: str | None = None, unlisted: bool = False, prevent_build_reuse: bool = False) → None

Runs the pipeline on the active stack.

Args:
: run_name: Name of the pipeline run.
  enable_cache: If caching should be enabled for this pipeline run.
  enable_artifact_metadata: If artifact metadata should be enabled
  <br/>
  > for this pipeline run.
  <br/>
  enable_artifact_visualization: If artifact visualization should be
  : enabled for this pipeline run.
  <br/>
  enable_step_logs: If step logs should be enabled for this pipeline
  : run.
  <br/>
  schedule: Optional schedule to use for the run.
  build: Optional build to use for the run.
  settings: Settings for this pipeline run.
  step_configurations: Configurations for steps of the pipeline.
  extra: Extra configurations for this pipeline run.
  config_path: Path to a yaml configuration file. This file will
  <br/>
  > be parsed as a
  > zenml.config.pipeline_configurations.PipelineRunConfiguration
  > object. Options provided in this file will be overwritten by
  > options provided in code using the other arguments of this
  > method.
  <br/>
  unlisted: Whether the pipeline run should be unlisted (not assigned
  : to any pipeline).
  <br/>
  prevent_build_reuse: Whether to prevent the reuse of a build.

#### *property* source_object *: Any*

The source object of this pipeline.

Returns:
: The source object of this pipeline.

#### *property* steps *: Dict[str, [BaseStep](zenml.steps.md#zenml.steps.base_step.BaseStep)]*

Returns the steps of the pipeline.

Returns:
: The steps of the pipeline.

## zenml.pipelines.pipeline_decorator module

Legacy ZenML pipeline decorator definition.

### zenml.pipelines.pipeline_decorator.pipeline(\_func: F) → Type[[BasePipeline](#zenml.pipelines.base_pipeline.BasePipeline)]

### zenml.pipelines.pipeline_decorator.pipeline(\*, name: str | None = None, enable_cache: bool | None = None, enable_artifact_metadata: bool | None = None, enable_artifact_visualization: bool | None = None, enable_step_logs: bool | None = None, settings: Dict[str, 'SettingsOrDict'] | None = None, extra: Dict[str, Any] | None = None, model: [Model](zenml.model.md#zenml.model.model.Model) | None = None) → Callable[[F], Type[[BasePipeline](#zenml.pipelines.base_pipeline.BasePipeline)]]

Outer decorator function for the creation of a ZenML pipeline.

Args:
: \_func: The decorated function.
  name: The name of the pipeline. If left empty, the name of the
  <br/>
  > decorated function will be used as a fallback.
  <br/>
  enable_cache: Whether to use caching or not.
  enable_artifact_metadata: Whether to enable artifact metadata or not.
  enable_artifact_visualization: Whether to enable artifact visualization.
  enable_step_logs: Whether to enable step logs.
  settings: Settings for this pipeline.
  extra: Extra configurations for this pipeline.
  on_failure: Callback function in event of failure of the step. Can be a
  <br/>
  > function with a single argument of type BaseException, or a source
  > path to such a function (e.g. module.my_function).
  <br/>
  on_success: Callback function in event of success of the step. Can be a
  : function with no arguments, or a source path to such a function
    (e.g. module.my_function).
  <br/>
  model: configuration of the model in the Model Control Plane.

Returns:
: the inner decorator which creates the pipeline class based on the
  ZenML BasePipeline

## Module contents

A ZenML pipeline consists of tasks that execute in order and yield artifacts.

The artifacts are automatically stored within the artifact store and metadata 
is tracked by ZenML. Each individual task within a pipeline is known as a
step. The standard pipelines within ZenML are designed to have easy interfaces
to add pre-decided steps, with the order also pre-decided. Other sorts of
pipelines can be created as well from scratch, building on the BasePipeline class.

Pipelines can be written as simple functions. They are created by using decorators appropriate to the specific use case you have. The moment it is run, a pipeline is compiled and passed directly to the orchestrator.

### *class* zenml.pipelines.BasePipeline(\*args: Any, \*\*kwargs: Any)

Bases: [`Pipeline`](zenml.new.pipelines.md#zenml.new.pipelines.pipeline.Pipeline), `ABC`

Legacy pipeline class.

#### *abstract* connect(\*args: [BaseStep](zenml.steps.md#zenml.steps.base_step.BaseStep), \*\*kwargs: [BaseStep](zenml.steps.md#zenml.steps.base_step.BaseStep)) → None

Abstract method that connects the pipeline steps.

Args:
: ```
  *
  ```
  <br/>
  args: Connect method arguments.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Connect method keyword arguments.

#### resolve() → [Source](zenml.config.md#zenml.config.source.Source)

Resolves the pipeline.

Returns:
: The pipeline source.

#### run(\*, run_name: str | None = None, enable_cache: bool | None = None, enable_artifact_metadata: bool | None = None, enable_artifact_visualization: bool | None = None, enable_step_logs: bool | None = None, schedule: [Schedule](zenml.config.md#zenml.config.schedule.Schedule) | None = None, build: str | UUID | [PipelineBuildBase](zenml.models.md#zenml.models.PipelineBuildBase) | None = None, settings: Mapping[str, SettingsOrDict] | None = None, step_configurations: Mapping[str, StepConfigurationUpdateOrDict] | None = None, extra: Dict[str, Any] | None = None, config_path: str | None = None, unlisted: bool = False, prevent_build_reuse: bool = False) → None

Runs the pipeline on the active stack.

Args:
: run_name: Name of the pipeline run.
  enable_cache: If caching should be enabled for this pipeline run.
  enable_artifact_metadata: If artifact metadata should be enabled
  <br/>
  > for this pipeline run.
  <br/>
  enable_artifact_visualization: If artifact visualization should be
  : enabled for this pipeline run.
  <br/>
  enable_step_logs: If step logs should be enabled for this pipeline
  : run.
  <br/>
  schedule: Optional schedule to use for the run.
  build: Optional build to use for the run.
  settings: Settings for this pipeline run.
  step_configurations: Configurations for steps of the pipeline.
  extra: Extra configurations for this pipeline run.
  config_path: Path to a yaml configuration file. This file will
  <br/>
  > be parsed as a
  > zenml.config.pipeline_configurations.PipelineRunConfiguration
  > object. Options provided in this file will be overwritten by
  > options provided in code using the other arguments of this
  > method.
  <br/>
  unlisted: Whether the pipeline run should be unlisted (not assigned
  : to any pipeline).
  <br/>
  prevent_build_reuse: Whether to prevent the reuse of a build.

#### *property* source_object *: Any*

The source object of this pipeline.

Returns:
: The source object of this pipeline.

#### *property* steps *: Dict[str, [BaseStep](zenml.steps.md#zenml.steps.base_step.BaseStep)]*

Returns the steps of the pipeline.

Returns:
: The steps of the pipeline.

### *class* zenml.pipelines.DockerSettings(warn_about_plain_text_secrets: bool = False, \*, parent_image: str | None = None, dockerfile: str | None = None, build_context_root: str | None = None, parent_image_build_config: [DockerBuildConfig](zenml.config.md#zenml.config.docker_settings.DockerBuildConfig) | None = None, skip_build: bool = False, prevent_build_reuse: bool = False, target_repository: str | None = None, python_package_installer: [PythonPackageInstaller](zenml.config.md#zenml.config.docker_settings.PythonPackageInstaller) = PythonPackageInstaller.PIP, python_package_installer_args: Dict[str, Any] = {}, replicate_local_python_environment: Annotated[List[str] | [PythonEnvironmentExportMethod](zenml.config.md#zenml.config.docker_settings.PythonEnvironmentExportMethod) | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, requirements: Annotated[None | str | List[str], \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, required_integrations: List[str] = [], install_stack_requirements: bool = True, apt_packages: List[str] = [], environment: Dict[str, Any] = {}, user: str | None = None, build_config: [DockerBuildConfig](zenml.config.md#zenml.config.docker_settings.DockerBuildConfig) | None = None, allow_including_files_in_images: bool = True, allow_download_from_code_repository: bool = True, allow_download_from_artifact_store: bool = True, build_options: Dict[str, Any] = {}, dockerignore: str | None = None, copy_files: bool = True, copy_global_config: bool = True, source_files: str | None = None, required_hub_plugins: List[str] = [])

Bases: [`BaseSettings`](zenml.config.md#zenml.config.base_settings.BaseSettings)

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

#### build_config *: [DockerBuildConfig](zenml.config.md#zenml.config.docker_settings.DockerBuildConfig) | None*

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

#### parent_image_build_config *: [DockerBuildConfig](zenml.config.md#zenml.config.docker_settings.DockerBuildConfig) | None*

#### prevent_build_reuse *: bool*

#### python_package_installer *: [PythonPackageInstaller](zenml.config.md#zenml.config.docker_settings.PythonPackageInstaller)*

#### python_package_installer_args *: Dict[str, Any]*

#### replicate_local_python_environment *: List[str] | [PythonEnvironmentExportMethod](zenml.config.md#zenml.config.docker_settings.PythonEnvironmentExportMethod) | None*

#### required_hub_plugins *: List[str]*

#### required_integrations *: List[str]*

#### requirements *: None | str | List[str]*

#### skip_build *: bool*

#### source_files *: str | None*

#### target_repository *: str | None*

#### user *: str | None*

### *class* zenml.pipelines.Schedule(\*, name: str | None = None, cron_expression: str | None = None, start_time: datetime | None = None, end_time: datetime | None = None, interval_second: timedelta | None = None, catchup: bool = False, run_once_start_time: datetime | None = None)

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

### zenml.pipelines.pipeline(\_func: F | None = None, \*, name: str | None = None, enable_cache: bool | None = None, enable_artifact_metadata: bool | None = None, enable_artifact_visualization: bool | None = None, enable_step_logs: bool | None = None, settings: Dict[str, SettingsOrDict] | None = None, extra: Dict[str, Any] | None = None, on_failure: HookSpecification | None = None, on_success: HookSpecification | None = None, model: [Model](zenml.md#zenml.Model) | None = None) → Type[[BasePipeline](#zenml.pipelines.base_pipeline.BasePipeline)] | Callable[[F], Type[[BasePipeline](#zenml.pipelines.base_pipeline.BasePipeline)]]

Outer decorator function for the creation of a ZenML pipeline.

Args:
: \_func: The decorated function.
  name: The name of the pipeline. If left empty, the name of the
  <br/>
  > decorated function will be used as a fallback.
  <br/>
  enable_cache: Whether to use caching or not.
  enable_artifact_metadata: Whether to enable artifact metadata or not.
  enable_artifact_visualization: Whether to enable artifact visualization.
  enable_step_logs: Whether to enable step logs.
  settings: Settings for this pipeline.
  extra: Extra configurations for this pipeline.
  on_failure: Callback function in event of failure of the step. Can be a
  <br/>
  > function with a single argument of type BaseException, or a source
  > path to such a function (e.g. module.my_function).
  <br/>
  on_success: Callback function in event of success of the step. Can be a
  : function with no arguments, or a source path to such a function
    (e.g. module.my_function).
  <br/>
  model: configuration of the model in the Model Control Plane.

Returns:
: the inner decorator which creates the pipeline class based on the
  ZenML BasePipeline
