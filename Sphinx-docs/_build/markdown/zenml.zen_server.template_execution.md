# zenml.zen_server.template_execution package

## Submodules

## zenml.zen_server.template_execution.runner_entrypoint_configuration module

Runner entrypoint configuration.

### *class* zenml.zen_server.template_execution.runner_entrypoint_configuration.RunnerEntrypointConfiguration(arguments: List[str])

Bases: [`BaseEntrypointConfiguration`](zenml.entrypoints.md#zenml.entrypoints.base_entrypoint_configuration.BaseEntrypointConfiguration)

Runner entrypoint configuration.

#### run() → None

Run the entrypoint configuration.

This method runs the pipeline defined by the deployment given as input
to the entrypoint configuration.

## zenml.zen_server.template_execution.utils module

Utility functions to run a pipeline from the server.

### zenml.zen_server.template_execution.utils.deployment_request_from_template(template: [RunTemplateResponse](zenml.models.v2.core.md#zenml.models.v2.core.run_template.RunTemplateResponse), config: [PipelineRunConfiguration](zenml.config.md#zenml.config.pipeline_run_configuration.PipelineRunConfiguration), user_id: UUID) → [PipelineDeploymentRequest](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentRequest)

Generate a deployment request from a template.

Args:
: template: The template from which to create the deployment request.
  config: The run configuration.
  user_id: ID of the user that is trying to run the template.

Raises:
: ValueError: If the run configuration is missing step parameters.

Returns:
: The generated deployment request.

### zenml.zen_server.template_execution.utils.ensure_async_orchestrator(deployment: [PipelineDeploymentRequest](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentRequest), stack: [StackResponse](zenml.models.v2.core.md#zenml.models.v2.core.stack.StackResponse)) → None

Ensures the orchestrator is configured to run async.

Args:
: deployment: Deployment request in which the orchestrator
  : configuration should be updated to ensure the orchestrator is
    running async.
  <br/>
  stack: The stack on which the deployment will run.

### zenml.zen_server.template_execution.utils.generate_dockerfile(pypi_requirements: List[str], apt_packages: List[str], zenml_version: str, python_version: str) → str

Generate a Dockerfile that installs the requirements.

Args:
: pypi_requirements: The PyPI requirements to install.
  apt_packages: The APT packages to install.
  zenml_version: The ZenML version to use as parent image.
  python_version: The Python version to use as parent image.

Returns:
: The Dockerfile.

### zenml.zen_server.template_execution.utils.generate_image_hash(dockerfile: str) → str

Generate a hash of the Dockerfile.

Args:
: dockerfile: The Dockerfile for which to generate the hash.

Returns:
: The hash of the Dockerfile.

### zenml.zen_server.template_execution.utils.get_pipeline_run_analytics_metadata(deployment: [PipelineDeploymentResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentResponse), stack: [StackResponse](zenml.models.v2.core.md#zenml.models.v2.core.stack.StackResponse), template_id: UUID, run_id: UUID) → Dict[str, Any]

Get metadata for the pipeline run analytics event.

Args:
: deployment: The deployment of the run.
  stack: The stack on which the run will happen.
  template_id: ID of the template from which the run was started.
  run_id: ID of the run.

Returns:
: The analytics metadata.

### zenml.zen_server.template_execution.utils.get_requirements_for_component(component: [ComponentResponse](zenml.models.v2.core.md#zenml.models.v2.core.component.ComponentResponse)) → Tuple[List[str], List[str]]

Get requirements for a component model.

Args:
: component: The component for which to get the requirements.

Returns:
: Tuple of PyPI and APT requirements of the component.

### zenml.zen_server.template_execution.utils.get_requirements_for_stack(stack: [StackResponse](zenml.models.v2.core.md#zenml.models.v2.core.stack.StackResponse)) → Tuple[List[str], List[str]]

Get requirements for a stack model.

Args:
: stack: The stack for which to get the requirements.

Returns:
: Tuple of PyPI and APT requirements of the stack.

### zenml.zen_server.template_execution.utils.run_template(template: [RunTemplateResponse](zenml.models.v2.core.md#zenml.models.v2.core.run_template.RunTemplateResponse), auth_context: [AuthContext](zenml.zen_server.md#zenml.zen_server.auth.AuthContext), background_tasks: BackgroundTasks | None = None, run_config: [PipelineRunConfiguration](zenml.config.md#zenml.config.pipeline_run_configuration.PipelineRunConfiguration) | None = None) → [PipelineRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunResponse)

Run a pipeline from a template.

Args:
: template: The template to run.
  auth_context: Authentication context.
  background_tasks: Background tasks.
  run_config: The run configuration.

Raises:
: ValueError: If the template can not be run.
  RuntimeError: If the server URL is not set in the server configuration.

Returns:
: ID of the new pipeline run.

## zenml.zen_server.template_execution.workload_manager_interface module

Workload manager interface definition.

### *class* zenml.zen_server.template_execution.workload_manager_interface.WorkloadManagerInterface

Bases: `ABC`

Workload manager interface.

#### *abstract* build_and_push_image(workload_id: UUID, dockerfile: str, image_name: str, sync: bool = True, timeout_in_seconds: int = 0) → str

Build and push a Docker image.

Args:
: workload_id: Workload ID.
  dockerfile: The dockerfile content to build the image.
  image_name: The image repository and tag.
  sync: If True, will wait until the build finished before returning.
  timeout_in_seconds: Timeout in seconds to wait before cancelling
  <br/>
  > the container. If set to 0 the container will run until it
  > fails or finishes.

Returns:
: The full image name including container registry.

#### *abstract* delete_workload(workload_id: UUID) → None

Delete a workload.

Args:
: workload_id: Workload ID.

#### *abstract* get_logs(workload_id: UUID) → str

Get logs for a workload.

Args:
: workload_id: Workload ID.

Returns:
: The stored logs.

#### *abstract* log(workload_id: UUID, message: str) → None

Log a message.

Args:
: workload_id: Workload ID.
  message: The message to log.

#### *abstract* run(workload_id: UUID, image: str, command: List[str], arguments: List[str], environment: Dict[str, str] | None = None, sync: bool = True, timeout_in_seconds: int = 0) → None

Run a Docker container.

Args:
: workload_id: Workload ID.
  image: The Docker image to run.
  command: The command to run in the container.
  arguments: The arguments for the command.
  environment: The environment to set in the container.
  sync: If True, will wait until the container finished running before
  <br/>
  > returning.
  <br/>
  timeout_in_seconds: Timeout in seconds to wait before cancelling
  : the container. If set to 0 the container will run until it
    fails or finishes.

## Module contents
