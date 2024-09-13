# zenml.new.pipelines package

## Submodules

## zenml.new.pipelines.build_utils module

Pipeline build utilities.

### zenml.new.pipelines.build_utils.build_required(deployment: [PipelineDeploymentBase](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentBase)) → bool

Checks whether a build is required for the deployment and active stack.

Args:
: deployment: The deployment for which to check.

Returns:
: If a build is required.

### zenml.new.pipelines.build_utils.code_download_possible(deployment: [PipelineDeploymentBase](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentBase), code_repository: [BaseCodeRepository](zenml.code_repositories.md#zenml.code_repositories.base_code_repository.BaseCodeRepository) | None = None) → bool

Checks whether code download is possible for the deployment.

Args:
: deployment: The deployment.
  code_repository: If provided, this code repository can be used to
  <br/>
  > download the code inside the container images.

Returns:
: Whether code download is possible for the deployment.

### zenml.new.pipelines.build_utils.compute_build_checksum(items: List[[BuildConfiguration](zenml.config.md#zenml.config.build_configuration.BuildConfiguration)], stack: [Stack](zenml.stack.md#zenml.stack.stack.Stack), code_repository: [BaseCodeRepository](zenml.code_repositories.md#zenml.code_repositories.base_code_repository.BaseCodeRepository) | None = None) → str

Compute an overall checksum for a pipeline build.

Args:
: items: Items of the build.
  stack: The stack associated with the build. Will be used to gather
  <br/>
  > its requirements.
  <br/>
  code_repository: The code repository that will be used to download
  : files inside the build. Will be used for its dependency
    specification.

Returns:
: The build checksum.

### zenml.new.pipelines.build_utils.compute_stack_checksum(stack: [StackResponse](zenml.models.v2.core.md#zenml.models.v2.core.stack.StackResponse)) → str

Compute a stack checksum.

Args:
: stack: The stack for which to compute the checksum.

Returns:
: The checksum.

### zenml.new.pipelines.build_utils.create_pipeline_build(deployment: [PipelineDeploymentBase](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentBase), pipeline_id: UUID | None = None, code_repository: [BaseCodeRepository](zenml.code_repositories.md#zenml.code_repositories.base_code_repository.BaseCodeRepository) | None = None) → [PipelineBuildResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_build.PipelineBuildResponse) | None

Builds images and registers the output in the server.

Args:
: deployment: The pipeline deployment.
  pipeline_id: The ID of the pipeline.
  code_repository: If provided, this code repository will be used to
  <br/>
  > download inside the build images.

Returns:
: The build output.

Raises:
: RuntimeError: If multiple builds with the same key but different
  : settings were specified.

### zenml.new.pipelines.build_utils.find_existing_build(deployment: [PipelineDeploymentBase](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentBase), code_repository: [BaseCodeRepository](zenml.code_repositories.md#zenml.code_repositories.base_code_repository.BaseCodeRepository) | None = None) → [PipelineBuildResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_build.PipelineBuildResponse) | None

Find an existing build for a deployment.

Args:
: deployment: The deployment for which to find an existing build.
  code_repository: The code repository that will be used to download
  <br/>
  > files in the images.

Returns:
: The existing build to reuse if found.

### zenml.new.pipelines.build_utils.requires_download_from_code_repository(deployment: [PipelineDeploymentBase](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentBase)) → bool

Checks whether the deployment needs to download code from a repository.

Args:
: deployment: The deployment.

Returns:
: If the deployment needs to download code from a code repository.

### zenml.new.pipelines.build_utils.requires_included_code(deployment: [PipelineDeploymentBase](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentBase), code_repository: [BaseCodeRepository](zenml.code_repositories.md#zenml.code_repositories.base_code_repository.BaseCodeRepository) | None = None) → bool

Checks whether the deployment requires included code.

Args:
: deployment: The deployment.
  code_repository: If provided, this code repository can be used to
  <br/>
  > download the code inside the container images.

Returns:
: If the deployment requires code included in the container images.

### zenml.new.pipelines.build_utils.reuse_or_create_pipeline_build(deployment: [PipelineDeploymentBase](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentBase), allow_build_reuse: bool, pipeline_id: UUID | None = None, build: UUID | [PipelineBuildBase](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_build.PipelineBuildBase) | None = None, code_repository: [BaseCodeRepository](zenml.code_repositories.md#zenml.code_repositories.base_code_repository.BaseCodeRepository) | None = None) → [PipelineBuildResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_build.PipelineBuildResponse) | None

Loads or creates a pipeline build.

Args:
: deployment: The pipeline deployment for which to load or create the
  : build.
  <br/>
  allow_build_reuse: If True, the build is allowed to reuse an
  : existing build.
  <br/>
  pipeline_id: Optional ID of the pipeline to reference in the build.
  build: Optional existing build. If given, the build will be fetched
  <br/>
  > (or registered) in the database. If not given, a new build will
  > be created.
  <br/>
  code_repository: If provided, this code repository can be used to
  : download code inside the container images.

Returns:
: The build response.

### zenml.new.pipelines.build_utils.should_upload_code(deployment: [PipelineDeploymentBase](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentBase), build: [PipelineBuildResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_build.PipelineBuildResponse) | None, code_reference: [CodeReferenceRequest](zenml.models.v2.core.md#zenml.models.v2.core.code_reference.CodeReferenceRequest) | None) → bool

Checks whether the current code should be uploaded for the deployment.

Args:
: deployment: The deployment.
  build: The build for the deployment.
  code_reference: The code reference for the deployment.

Returns:
: Whether the current code should be uploaded for the deployment.

### zenml.new.pipelines.build_utils.verify_custom_build(build: [PipelineBuildResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_build.PipelineBuildResponse), deployment: [PipelineDeploymentBase](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentBase), code_repository: [BaseCodeRepository](zenml.code_repositories.md#zenml.code_repositories.base_code_repository.BaseCodeRepository) | None = None) → None

Verify a custom build for a pipeline deployment.

Args:
: build: The build to verify.
  deployment: The deployment for which to verify the build.
  code_repository: Code repository that will be used to download files
  <br/>
  > for the deployment.

Raises:
: RuntimeError: If the build can’t be used for the deployment.

### zenml.new.pipelines.build_utils.verify_local_repository_context(deployment: [PipelineDeploymentBase](zenml.models.md#zenml.models.PipelineDeploymentBase), local_repo_context: [LocalRepositoryContext](zenml.code_repositories.md#zenml.code_repositories.local_repository_context.LocalRepositoryContext) | None) → [BaseCodeRepository](zenml.code_repositories.md#zenml.code_repositories.base_code_repository.BaseCodeRepository) | None

Verifies the local repository.

If the local repository exists and has no local changes, code download
inside the images is possible.

Args:
: deployment: The pipeline deployment.
  local_repo_context: The local repository active at the source root.

Raises:
: RuntimeError: If the deployment requires code download but code download
  : is not possible.

Returns:
: The code repository from which to download files for the runs of the
  deployment, or None if code download is not possible.

## zenml.new.pipelines.code_archive module

Code archive.

### *class* zenml.new.pipelines.code_archive.CodeArchive(root: str)

Bases: [`Archivable`](zenml.utils.md#zenml.utils.archivable.Archivable)

Code archive class.

This class is used to archive user code before uploading it to the artifact
store. If the user code is stored in a Git repository, only files not
excluded by gitignores will be included in the archive.

#### get_files() → Dict[str, str]

Gets all regular files that should be included in the archive.

Raises:
: RuntimeError: If the code archive would not include any files.

Returns:
: A dict {path_in_archive: path_on_filesystem} for all regular files
  in the archive.

#### *property* git_repo *: Repo | None*

Git repository active at the code archive root.

Returns:
: The git repository if available.

#### write_archive(output_file: IO[bytes], use_gzip: bool = True) → None

Writes an archive of the build context to the given file.

Args:
: output_file: The file to write the archive to.
  use_gzip: Whether to use gzip to compress the file.

## zenml.new.pipelines.pipeline module

Definition of a ZenML pipeline.

### *class* zenml.new.pipelines.pipeline.Pipeline(name: str, entrypoint: F, enable_cache: bool | None = None, enable_artifact_metadata: bool | None = None, enable_artifact_visualization: bool | None = None, enable_step_logs: bool | None = None, settings: Mapping[str, SettingsOrDict] | None = None, extra: Dict[str, Any] | None = None, on_failure: HookSpecification | None = None, on_success: HookSpecification | None = None, model: [Model](zenml.md#zenml.Model) | None = None)

Bases: `object`

ZenML pipeline class.

#### ACTIVE_PIPELINE *: ClassVar[[Pipeline](#zenml.new.pipelines.pipeline.Pipeline) | None]* *= None*

#### add_step_invocation(step: [BaseStep](zenml.steps.md#zenml.steps.base_step.BaseStep), input_artifacts: Dict[str, [StepArtifact](zenml.steps.md#zenml.steps.entrypoint_function_utils.StepArtifact)], external_artifacts: Dict[str, [ExternalArtifact](zenml.md#zenml.ExternalArtifact)], model_artifacts_or_metadata: Dict[str, [ModelVersionDataLazyLoader](zenml.model.md#zenml.model.lazy_load.ModelVersionDataLazyLoader)], client_lazy_loaders: Dict[str, [ClientLazyLoader](zenml.md#zenml.client_lazy_loader.ClientLazyLoader)], parameters: Dict[str, Any], default_parameters: Dict[str, Any], upstream_steps: Set[str], custom_id: str | None = None, allow_id_suffix: bool = True) → str

Adds a step invocation to the pipeline.

Args:
: step: The step for which to add an invocation.
  input_artifacts: The input artifacts for the invocation.
  external_artifacts: The external artifacts for the invocation.
  model_artifacts_or_metadata: The model artifacts or metadata for
  <br/>
  > the invocation.
  <br/>
  client_lazy_loaders: The client lazy loaders for the invocation.
  parameters: The parameters for the invocation.
  default_parameters: The default parameters for the invocation.
  upstream_steps: The upstream steps for the invocation.
  custom_id: Custom ID to use for the invocation.
  allow_id_suffix: Whether a suffix can be appended to the invocation
  <br/>
  > ID.

Raises:
: RuntimeError: If the method is called on an inactive pipeline.
  RuntimeError: If the invocation was called with an artifact from
  <br/>
  > a different pipeline.

Returns:
: The step invocation ID.

#### build(settings: Mapping[str, SettingsOrDict] | None = None, step_configurations: Mapping[str, StepConfigurationUpdateOrDict] | None = None, config_path: str | None = None) → [PipelineBuildResponse](zenml.models.md#zenml.models.PipelineBuildResponse) | None

Builds Docker images for the pipeline.

Args:
: settings: Settings for the pipeline.
  step_configurations: Configurations for steps of the pipeline.
  config_path: Path to a yaml configuration file. This file will
  <br/>
  > be parsed as a
  > zenml.config.pipeline_configurations.PipelineRunConfiguration
  > object. Options provided in this file will be overwritten by
  > options provided in code using the other arguments of this
  > method.

Returns:
: The build output.

#### *property* configuration *: [PipelineConfiguration](zenml.config.md#zenml.config.pipeline_configurations.PipelineConfiguration)*

The configuration of the pipeline.

Returns:
: The configuration of the pipeline.

#### configure(enable_cache: bool | None = None, enable_artifact_metadata: bool | None = None, enable_artifact_visualization: bool | None = None, enable_step_logs: bool | None = None, settings: Mapping[str, SettingsOrDict] | None = None, extra: Dict[str, Any] | None = None, on_failure: HookSpecification | None = None, on_success: HookSpecification | None = None, model: [Model](zenml.md#zenml.Model) | None = None, parameters: Dict[str, Any] | None = None, merge: bool = True) → T

Configures the pipeline.

Configuration merging example:
\* merge==True:

> pipeline.configure(extra={“key1”: 1})
> pipeline.configure(extra={“key2”: 2}, merge=True)
> pipeline.configuration.extra # {“key1”: 1, “key2”: 2}
* merge==False:
  : pipeline.configure(extra={“key1”: 1})
    pipeline.configure(extra={“key2”: 2}, merge=False)
    pipeline.configuration.extra # {“key2”: 2}

Args:
: enable_cache: If caching should be enabled for this pipeline.
  enable_artifact_metadata: If artifact metadata should be enabled for
  <br/>
  > this pipeline.
  <br/>
  enable_artifact_visualization: If artifact visualization should be
  : enabled for this pipeline.
  <br/>
  enable_step_logs: If step logs should be enabled for this pipeline.
  settings: settings for this pipeline.
  extra: Extra configurations for this pipeline.
  on_failure: Callback function in event of failure of the step. Can
  <br/>
  > be a function with a single argument of type BaseException, or
  > a source path to such a function (e.g. module.my_function).
  <br/>
  on_success: Callback function in event of success of the step. Can
  : be a function with no arguments, or a source path to such a
    function (e.g. module.my_function).
  <br/>
  merge: If True, will merge the given dictionary configurations
  : like extra and settings with existing
    configurations. If False the given configurations will
    overwrite all existing ones. See the general description of this
    method for an example.
  <br/>
  model: configuration of the model version in the Model Control Plane.
  parameters: input parameters for the pipeline.

Returns:
: The pipeline instance that this method was called on.

#### copy() → [Pipeline](#zenml.new.pipelines.pipeline.Pipeline)

Copies the pipeline.

Returns:
: The pipeline copy.

#### *property* enable_cache *: bool | None*

If caching is enabled for the pipeline.

Returns:
: If caching is enabled for the pipeline.

#### get_runs(\*\*kwargs: Any) → List[[PipelineRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunResponse)]

(Deprecated) Get runs of this pipeline.

Args:
: ```
  **
  ```
  <br/>
  kwargs: Further arguments for filtering or pagination that are
  : passed to client.list_pipeline_runs().

Returns:
: List of runs of this pipeline.

#### *property* invocations *: Dict[str, [StepInvocation](zenml.steps.md#zenml.steps.step_invocation.StepInvocation)]*

Returns the step invocations of this pipeline.

This dictionary will only be populated once the pipeline has been
called.

Returns:
: The step invocations.

#### *property* is_prepared *: bool*

If the pipeline is prepared.

Prepared means that the pipeline entrypoint has been called and the
pipeline is fully defined.

Returns:
: If the pipeline is prepared.

#### *static* log_pipeline_deployment_metadata(deployment_model: [PipelineDeploymentResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentResponse)) → None

Displays logs based on the deployment model upon running a pipeline.

Args:
: deployment_model: The model for the pipeline deployment

#### *property* model *: [PipelineResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline.PipelineResponse)*

Gets the registered pipeline model for this instance.

Returns:
: The registered pipeline model.

Raises:
: RuntimeError: If the pipeline has not been registered yet.

#### *property* name *: str*

The name of the pipeline.

Returns:
: The name of the pipeline.

#### prepare(\*args: Any, \*\*kwargs: Any) → None

Prepares the pipeline.

Args:
: ```
  *
  ```
  <br/>
  args: Pipeline entrypoint input arguments.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Pipeline entrypoint input keyword arguments.

Raises:
: RuntimeError: If the pipeline has parameters configured differently in
  : configuration file and code.

#### register() → [PipelineResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline.PipelineResponse)

Register the pipeline in the server.

Returns:
: The registered pipeline model.

#### *property* requires_parameters *: bool*

If the pipeline entrypoint requires parameters.

Returns:
: If the pipeline entrypoint requires parameters.

#### resolve() → [Source](zenml.config.md#zenml.config.source.Source)

Resolves the pipeline.

Returns:
: The pipeline source.

#### *property* source_code *: str*

The source code of this pipeline.

Returns:
: The source code of this pipeline.

#### *property* source_object *: Any*

The source object of this pipeline.

Returns:
: The source object of this pipeline.

#### with_options(run_name: str | None = None, schedule: [Schedule](zenml.config.md#zenml.config.schedule.Schedule) | None = None, build: str | UUID | [PipelineBuildBase](zenml.models.md#zenml.models.PipelineBuildBase) | None = None, step_configurations: Mapping[str, StepConfigurationUpdateOrDict] | None = None, steps: Mapping[str, StepConfigurationUpdateOrDict] | None = None, config_path: str | None = None, unlisted: bool = False, prevent_build_reuse: bool = False, \*\*kwargs: Any) → [Pipeline](#zenml.new.pipelines.pipeline.Pipeline)

Copies the pipeline and applies the given configurations.

Args:
: run_name: Name of the pipeline run.
  schedule: Optional schedule to use for the run.
  build: Optional build to use for the run.
  step_configurations: Configurations for steps of the pipeline.
  steps: Configurations for steps of the pipeline. This is equivalent
  <br/>
  > to step_configurations, and will be ignored if
  > step_configurations is set as well.
  <br/>
  config_path: Path to a yaml configuration file. This file will
  : be parsed as a
    zenml.config.pipeline_configurations.PipelineRunConfiguration
    object. Options provided in this file will be overwritten by
    options provided in code using the other arguments of this
    method.
  <br/>
  unlisted: Whether the pipeline run should be unlisted (not assigned
  : to any pipeline).
  <br/>
  prevent_build_reuse: DEPRECATED: Use
  : DockerSettings.prevent_build_reuse instead.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Pipeline configuration options. These will be passed
  : to the pipeline.configure(…) method.

Returns:
: The copied pipeline instance.

#### write_run_configuration_template(path: str, stack: [Stack](zenml.stack.md#zenml.stack.stack.Stack) | None = None) → None

Writes a run configuration yaml template.

Args:
: path: The path where the template will be written.
  stack: The stack for which the template should be generated. If
  <br/>
  > not given, the active stack will be used.

## zenml.new.pipelines.pipeline_context module

Pipeline context class.

### *class* zenml.new.pipelines.pipeline_context.PipelineContext(pipeline_configuration: [PipelineConfiguration](zenml.config.md#zenml.config.pipeline_configurations.PipelineConfiguration))

Bases: `object`

Provides pipeline configuration context.

Usage example:

```
``
```

```
`
```

python
from zenml import get_pipeline_context

…

@pipeline(
: extra={
  : “complex_parameter”: [
    : (“sklearn.tree”, “DecisionTreeClassifier”),
      (“sklearn.ensemble”, “RandomForestClassifier”),
    <br/>
    ]
  <br/>
  }

)
def my_pipeline():

> context = get_pipeline_context()

> after = []
> search_steps_prefix = “

> ```
> hp_tuning_search_
> ```

> ”
> for i, model_search_configuration in enumerate(

> > context.extra[“complex_parameter”]

> ):
> : step_name = f”{search_steps_prefix}{i}”
>   cross_validation(
>   <br/>
>   > model_package=model_search_configuration[0],
>   > model_class=model_search_configuration[1],
>   > id=step_name
>   <br/>
>   )
>   after.append(step_name)

> select_best_model(
> : search_steps_prefix=search_steps_prefix,
>   after=after,

> )

```
``
```

```
`
```

#### *property* model_version *: [Model](zenml.md#zenml.Model) | None*

DEPRECATED, use model instead.

Returns:
: The Model object associated with the current pipeline.

### zenml.new.pipelines.pipeline_context.get_pipeline_context() → [PipelineContext](#zenml.new.pipelines.pipeline_context.PipelineContext)

Get the context of the current pipeline.

Returns:
: The context of the current pipeline.

Raises:
: RuntimeError: If no active pipeline is found.
  RuntimeError: If inside a running step.

## zenml.new.pipelines.pipeline_decorator module

ZenML pipeline decorator definition.

### zenml.new.pipelines.pipeline_decorator.pipeline(\_func: F) → [Pipeline](#zenml.new.pipelines.pipeline.Pipeline)

### zenml.new.pipelines.pipeline_decorator.pipeline(\*, name: str | None = None, enable_cache: bool | None = None, enable_artifact_metadata: bool | None = None, enable_step_logs: bool | None = None, settings: Dict[str, 'SettingsOrDict'] | None = None, extra: Dict[str, Any] | None = None) → Callable[['F'], 'Pipeline']

Decorator to create a pipeline.

Args:
: \_func: The decorated function.
  name: The name of the pipeline. If left empty, the name of the
  <br/>
  > decorated function will be used as a fallback.
  <br/>
  enable_cache: Whether to use caching or not.
  enable_artifact_metadata: Whether to enable artifact metadata or not.
  enable_step_logs: If step logs should be enabled for this pipeline.
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
  model_version: DEPRECATED, please use model instead.

Returns:
: A pipeline instance.

## zenml.new.pipelines.run_utils module

Utility functions for running pipelines.

### zenml.new.pipelines.run_utils.create_placeholder_run(deployment: [PipelineDeploymentResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentResponse)) → [PipelineRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunResponse) | None

Create a placeholder run for the deployment.

If the deployment contains a schedule, no placeholder run will be
created.

Args:
: deployment: The deployment for which to create the placeholder run.

Returns:
: The placeholder run or None if no run was created.

### zenml.new.pipelines.run_utils.deploy_pipeline(deployment: [PipelineDeploymentResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentResponse), stack: [Stack](zenml.stack.md#zenml.stack.stack.Stack), placeholder_run: [PipelineRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunResponse) | None = None) → None

Run a deployment.

Args:
: deployment: The deployment to run.
  stack: The stack on which to run the deployment.
  placeholder_run: An optional placeholder run for the deployment. This
  <br/>
  > will be deleted in case the pipeline deployment failed.

Raises:
: Exception: Any exception that happened while deploying or running
  : (in case it happens synchronously) the pipeline.

### zenml.new.pipelines.run_utils.get_all_sources_from_value(value: Any) → List[[Source](zenml.config.md#zenml.config.source.Source)]

Get all source objects from a value.

Args:
: value: The value from which to get all the source objects.

Returns:
: List of source objects for the given value.

### zenml.new.pipelines.run_utils.get_default_run_name(pipeline_name: str) → str

Gets the default name for a pipeline run.

Args:
: pipeline_name: Name of the pipeline which will be run.

Returns:
: Run name.

### zenml.new.pipelines.run_utils.get_placeholder_run(deployment_id: UUID) → [PipelineRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunResponse) | None

Get the placeholder run for a deployment.

Args:
: deployment_id: ID of the deployment for which to get the placeholder
  : run.

Returns:
: The placeholder run or None if there exists no placeholder run for the
  deployment.

### zenml.new.pipelines.run_utils.upload_notebook_cell_code_if_necessary(deployment: [PipelineDeploymentBase](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentBase), stack: [Stack](zenml.stack.md#zenml.stack.stack.Stack)) → None

Upload notebook cell code if necessary.

This function checks if any of the steps of the pipeline that will be
executed in a different process are defined in a notebook. If that is the
case, it will extract that notebook cell code into python files and upload
an archive of all the necessary files to the artifact store.

Args:
: deployment: The deployment.
  stack: The stack on which the deployment will happen.

Raises:
: RuntimeError: If the code for one of the steps that will run out of
  : process cannot be extracted into a python file.

### zenml.new.pipelines.run_utils.validate_run_config_is_runnable_from_server(run_configuration: [PipelineRunConfiguration](zenml.config.md#zenml.config.pipeline_run_configuration.PipelineRunConfiguration)) → None

Validates that the run configuration can be used to run from the server.

Args:
: run_configuration: The run configuration to validate.

Raises:
: ValueError: If there are values in the run configuration that are not
  : allowed when running a pipeline from the server.

### zenml.new.pipelines.run_utils.validate_stack_is_runnable_from_server(zen_store: [BaseZenStore](zenml.zen_stores.md#zenml.zen_stores.base_zen_store.BaseZenStore), stack: [StackResponse](zenml.models.v2.core.md#zenml.models.v2.core.stack.StackResponse)) → None

Validate if a stack model is runnable from the server.

Args:
: zen_store: ZenStore to use for listing flavors.
  stack: The stack to validate.

Raises:
: ValueError: If the stack has components of a custom flavor or local
  : components.

### zenml.new.pipelines.run_utils.wait_for_pipeline_run_to_finish(run_id: UUID) → [PipelineRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunResponse)

Waits until a pipeline run is finished.

Args:
: run_id: ID of the run for which to wait.

Returns:
: Model of the finished run.

## Module contents
