# zenml.orchestrators package

## Subpackages

* [zenml.orchestrators.local package](zenml.orchestrators.local.md)
  * [Submodules](zenml.orchestrators.local.md#submodules)
  * [zenml.orchestrators.local.local_orchestrator module](zenml.orchestrators.local.md#module-zenml.orchestrators.local.local_orchestrator)
    * [`LocalOrchestrator`](zenml.orchestrators.local.md#zenml.orchestrators.local.local_orchestrator.LocalOrchestrator)
      * [`LocalOrchestrator.get_orchestrator_run_id()`](zenml.orchestrators.local.md#zenml.orchestrators.local.local_orchestrator.LocalOrchestrator.get_orchestrator_run_id)
      * [`LocalOrchestrator.prepare_or_run_pipeline()`](zenml.orchestrators.local.md#zenml.orchestrators.local.local_orchestrator.LocalOrchestrator.prepare_or_run_pipeline)
    * [`LocalOrchestratorConfig`](zenml.orchestrators.local.md#zenml.orchestrators.local.local_orchestrator.LocalOrchestratorConfig)
      * [`LocalOrchestratorConfig.is_local`](zenml.orchestrators.local.md#zenml.orchestrators.local.local_orchestrator.LocalOrchestratorConfig.is_local)
      * [`LocalOrchestratorConfig.is_synchronous`](zenml.orchestrators.local.md#zenml.orchestrators.local.local_orchestrator.LocalOrchestratorConfig.is_synchronous)
      * [`LocalOrchestratorConfig.model_computed_fields`](zenml.orchestrators.local.md#zenml.orchestrators.local.local_orchestrator.LocalOrchestratorConfig.model_computed_fields)
      * [`LocalOrchestratorConfig.model_config`](zenml.orchestrators.local.md#zenml.orchestrators.local.local_orchestrator.LocalOrchestratorConfig.model_config)
      * [`LocalOrchestratorConfig.model_fields`](zenml.orchestrators.local.md#zenml.orchestrators.local.local_orchestrator.LocalOrchestratorConfig.model_fields)
    * [`LocalOrchestratorFlavor`](zenml.orchestrators.local.md#zenml.orchestrators.local.local_orchestrator.LocalOrchestratorFlavor)
      * [`LocalOrchestratorFlavor.config_class`](zenml.orchestrators.local.md#zenml.orchestrators.local.local_orchestrator.LocalOrchestratorFlavor.config_class)
      * [`LocalOrchestratorFlavor.docs_url`](zenml.orchestrators.local.md#zenml.orchestrators.local.local_orchestrator.LocalOrchestratorFlavor.docs_url)
      * [`LocalOrchestratorFlavor.implementation_class`](zenml.orchestrators.local.md#zenml.orchestrators.local.local_orchestrator.LocalOrchestratorFlavor.implementation_class)
      * [`LocalOrchestratorFlavor.logo_url`](zenml.orchestrators.local.md#zenml.orchestrators.local.local_orchestrator.LocalOrchestratorFlavor.logo_url)
      * [`LocalOrchestratorFlavor.name`](zenml.orchestrators.local.md#zenml.orchestrators.local.local_orchestrator.LocalOrchestratorFlavor.name)
      * [`LocalOrchestratorFlavor.sdk_docs_url`](zenml.orchestrators.local.md#zenml.orchestrators.local.local_orchestrator.LocalOrchestratorFlavor.sdk_docs_url)
  * [Module contents](zenml.orchestrators.local.md#module-zenml.orchestrators.local)
* [zenml.orchestrators.local_docker package](zenml.orchestrators.local_docker.md)
  * [Submodules](zenml.orchestrators.local_docker.md#submodules)
  * [zenml.orchestrators.local_docker.local_docker_orchestrator module](zenml.orchestrators.local_docker.md#module-zenml.orchestrators.local_docker.local_docker_orchestrator)
    * [`LocalDockerOrchestrator`](zenml.orchestrators.local_docker.md#zenml.orchestrators.local_docker.local_docker_orchestrator.LocalDockerOrchestrator)
      * [`LocalDockerOrchestrator.get_orchestrator_run_id()`](zenml.orchestrators.local_docker.md#zenml.orchestrators.local_docker.local_docker_orchestrator.LocalDockerOrchestrator.get_orchestrator_run_id)
      * [`LocalDockerOrchestrator.prepare_or_run_pipeline()`](zenml.orchestrators.local_docker.md#zenml.orchestrators.local_docker.local_docker_orchestrator.LocalDockerOrchestrator.prepare_or_run_pipeline)
      * [`LocalDockerOrchestrator.settings_class`](zenml.orchestrators.local_docker.md#zenml.orchestrators.local_docker.local_docker_orchestrator.LocalDockerOrchestrator.settings_class)
      * [`LocalDockerOrchestrator.validator`](zenml.orchestrators.local_docker.md#zenml.orchestrators.local_docker.local_docker_orchestrator.LocalDockerOrchestrator.validator)
    * [`LocalDockerOrchestratorConfig`](zenml.orchestrators.local_docker.md#zenml.orchestrators.local_docker.local_docker_orchestrator.LocalDockerOrchestratorConfig)
      * [`LocalDockerOrchestratorConfig.is_local`](zenml.orchestrators.local_docker.md#zenml.orchestrators.local_docker.local_docker_orchestrator.LocalDockerOrchestratorConfig.is_local)
      * [`LocalDockerOrchestratorConfig.is_synchronous`](zenml.orchestrators.local_docker.md#zenml.orchestrators.local_docker.local_docker_orchestrator.LocalDockerOrchestratorConfig.is_synchronous)
      * [`LocalDockerOrchestratorConfig.model_computed_fields`](zenml.orchestrators.local_docker.md#zenml.orchestrators.local_docker.local_docker_orchestrator.LocalDockerOrchestratorConfig.model_computed_fields)
      * [`LocalDockerOrchestratorConfig.model_config`](zenml.orchestrators.local_docker.md#zenml.orchestrators.local_docker.local_docker_orchestrator.LocalDockerOrchestratorConfig.model_config)
      * [`LocalDockerOrchestratorConfig.model_fields`](zenml.orchestrators.local_docker.md#zenml.orchestrators.local_docker.local_docker_orchestrator.LocalDockerOrchestratorConfig.model_fields)
    * [`LocalDockerOrchestratorFlavor`](zenml.orchestrators.local_docker.md#zenml.orchestrators.local_docker.local_docker_orchestrator.LocalDockerOrchestratorFlavor)
      * [`LocalDockerOrchestratorFlavor.config_class`](zenml.orchestrators.local_docker.md#zenml.orchestrators.local_docker.local_docker_orchestrator.LocalDockerOrchestratorFlavor.config_class)
      * [`LocalDockerOrchestratorFlavor.docs_url`](zenml.orchestrators.local_docker.md#zenml.orchestrators.local_docker.local_docker_orchestrator.LocalDockerOrchestratorFlavor.docs_url)
      * [`LocalDockerOrchestratorFlavor.implementation_class`](zenml.orchestrators.local_docker.md#zenml.orchestrators.local_docker.local_docker_orchestrator.LocalDockerOrchestratorFlavor.implementation_class)
      * [`LocalDockerOrchestratorFlavor.logo_url`](zenml.orchestrators.local_docker.md#zenml.orchestrators.local_docker.local_docker_orchestrator.LocalDockerOrchestratorFlavor.logo_url)
      * [`LocalDockerOrchestratorFlavor.name`](zenml.orchestrators.local_docker.md#zenml.orchestrators.local_docker.local_docker_orchestrator.LocalDockerOrchestratorFlavor.name)
      * [`LocalDockerOrchestratorFlavor.sdk_docs_url`](zenml.orchestrators.local_docker.md#zenml.orchestrators.local_docker.local_docker_orchestrator.LocalDockerOrchestratorFlavor.sdk_docs_url)
    * [`LocalDockerOrchestratorSettings`](zenml.orchestrators.local_docker.md#zenml.orchestrators.local_docker.local_docker_orchestrator.LocalDockerOrchestratorSettings)
      * [`LocalDockerOrchestratorSettings.model_computed_fields`](zenml.orchestrators.local_docker.md#zenml.orchestrators.local_docker.local_docker_orchestrator.LocalDockerOrchestratorSettings.model_computed_fields)
      * [`LocalDockerOrchestratorSettings.model_config`](zenml.orchestrators.local_docker.md#zenml.orchestrators.local_docker.local_docker_orchestrator.LocalDockerOrchestratorSettings.model_config)
      * [`LocalDockerOrchestratorSettings.model_fields`](zenml.orchestrators.local_docker.md#zenml.orchestrators.local_docker.local_docker_orchestrator.LocalDockerOrchestratorSettings.model_fields)
      * [`LocalDockerOrchestratorSettings.run_args`](zenml.orchestrators.local_docker.md#zenml.orchestrators.local_docker.local_docker_orchestrator.LocalDockerOrchestratorSettings.run_args)
  * [Module contents](zenml.orchestrators.local_docker.md#module-zenml.orchestrators.local_docker)

## Submodules

## zenml.orchestrators.base_orchestrator module

Base orchestrator class.

### *class* zenml.orchestrators.base_orchestrator.BaseOrchestrator(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`StackComponent`](zenml.stack.md#zenml.stack.stack_component.StackComponent), `ABC`

Base class for all orchestrators.

In order to implement an orchestrator you will need to subclass from this
class.

### How it works:

The run(…) method is the entrypoint that is executed when the
pipeline’s run method is called within the user code
(pipeline_instance.run(…)).

This method will do some internal preparation and then call the
prepare_or_run_pipeline(…) method. BaseOrchestrator subclasses must
implement this method and either run the pipeline steps directly or deploy
the pipeline to some remote infrastructure.

#### *property* config *: [BaseOrchestratorConfig](#zenml.orchestrators.base_orchestrator.BaseOrchestratorConfig)*

Returns the BaseOrchestratorConfig config.

Returns:
: The configuration.

#### *abstract* get_orchestrator_run_id() → str

Returns the run id of the active orchestrator run.

Important: This needs to be a unique ID and return the same value for
all steps of a pipeline run.

Returns:
: The orchestrator run id.

#### *abstract* prepare_or_run_pipeline(deployment: [PipelineDeploymentResponse](zenml.models.md#zenml.models.PipelineDeploymentResponse), stack: [Stack](zenml.stack.md#zenml.stack.stack.Stack), environment: Dict[str, str]) → Any

The method needs to be implemented by the respective orchestrator.

Depending on the type of orchestrator you’ll have to perform slightly
different operations.

#### Simple Case:

The Steps are run directly from within the same environment in which
the orchestrator code is executed. In this case you will need to
deal with implementation-specific runtime configurations (like the
schedule) and then iterate through the steps and finally call
self.run_step(…) to execute each step.

#### Advanced Case:

Most orchestrators will not run the steps directly. Instead, they
build some intermediate representation of the pipeline that is then
used to create and run the pipeline and its steps on the target
environment. For such orchestrators this method will have to build
this representation and deploy it.

Regardless of the implementation details, the orchestrator will need
to run each step in the target environment. For this the
self.run_step(…) method should be used.

The easiest way to make this work is by using an entrypoint
configuration to run single steps (zenml.entrypoints.step_entrypoint_configuration.StepEntrypointConfiguration)
or entire pipelines (zenml.entrypoints.pipeline_entrypoint_configuration.PipelineEntrypointConfiguration).

Args:
: deployment: The pipeline deployment to prepare or run.
  stack: The stack the pipeline will run on.
  environment: Environment variables to set in the orchestration
  <br/>
  > environment. These don’t need to be set if running locally.

Returns:
: The optional return value from this method will be returned by the
  pipeline_instance.run() call when someone is running a pipeline.

#### *static* requires_resources_in_orchestration_environment(step: [Step](zenml.config.md#zenml.config.step_configurations.Step)) → bool

Checks if the orchestrator should run this step on special resources.

Args:
: step: The step that will be checked.

Returns:
: True if the step requires special resources in the orchestration
  environment, False otherwise.

#### run(deployment: [PipelineDeploymentResponse](zenml.models.md#zenml.models.PipelineDeploymentResponse), stack: [Stack](zenml.stack.md#zenml.stack.stack.Stack)) → Any

Runs a pipeline on a stack.

Args:
: deployment: The pipeline deployment.
  stack: The stack on which to run the pipeline.

Returns:
: Orchestrator-specific return value.

#### run_step(step: [Step](zenml.config.md#zenml.config.step_configurations.Step)) → None

Runs the given step.

Args:
: step: The step to run.

### *class* zenml.orchestrators.base_orchestrator.BaseOrchestratorConfig(warn_about_plain_text_secrets: bool = False)

Bases: [`StackComponentConfig`](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig)

Base orchestrator config.

#### *property* is_schedulable *: bool*

Whether the orchestrator is schedulable or not.

Returns:
: Whether the orchestrator is schedulable or not.

#### *property* is_synchronous *: bool*

Whether the orchestrator runs synchronous or not.

Returns:
: Whether the orchestrator runs synchronous or not.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.orchestrators.base_orchestrator.BaseOrchestratorFlavor

Bases: [`Flavor`](zenml.stack.md#zenml.stack.flavor.Flavor)

Base orchestrator flavor class.

#### *property* config_class *: Type[[BaseOrchestratorConfig](#zenml.orchestrators.base_orchestrator.BaseOrchestratorConfig)]*

Config class for the base orchestrator flavor.

Returns:
: The config class.

#### *abstract property* implementation_class *: Type[[BaseOrchestrator](#zenml.orchestrators.base_orchestrator.BaseOrchestrator)]*

Implementation class for this flavor.

Returns:
: The implementation class.

#### *property* type *: [StackComponentType](zenml.md#zenml.enums.StackComponentType)*

Returns the flavor type.

Returns:
: The flavor type.

## zenml.orchestrators.cache_utils module

Utilities for caching.

### zenml.orchestrators.cache_utils.generate_cache_key(step: [Step](zenml.config.md#zenml.config.step_configurations.Step), input_artifact_ids: Dict[str, UUID], artifact_store: [BaseArtifactStore](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore), workspace_id: UUID) → str

Generates a cache key for a step run.

If the cache key is the same for two step runs, we conclude that the step
runs are identical and can be cached.

The cache key is a MD5 hash of:
- the workspace ID,
- the artifact store ID and path,
- the source code that defines the step,
- the parameters of the step,
- the names and IDs of the input artifacts of the step,
- the names and source codes of the output artifacts of the step,
- the source codes of the output materializers of the step.
- additional custom caching parameters of the step.

Args:
: step: The step to generate the cache key for.
  input_artifact_ids: The input artifact IDs for the step.
  artifact_store: The artifact store of the active stack.
  workspace_id: The ID of the active workspace.

Returns:
: A cache key.

### zenml.orchestrators.cache_utils.get_cached_step_run(cache_key: str) → [StepRunResponse](zenml.models.md#zenml.models.StepRunResponse) | None

If a given step can be cached, get the corresponding existing step run.

A step run can be cached if there is an existing step run in the same
workspace which has the same cache key and was successfully executed.

Args:
: cache_key: The cache key of the step.

Returns:
: The existing step run if the step can be cached, otherwise None.

## zenml.orchestrators.containerized_orchestrator module

Containerized orchestrator class.

### *class* zenml.orchestrators.containerized_orchestrator.ContainerizedOrchestrator(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`BaseOrchestrator`](#zenml.orchestrators.base_orchestrator.BaseOrchestrator), `ABC`

Base class for containerized orchestrators.

#### get_docker_builds(deployment: [PipelineDeploymentBase](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentBase)) → List[[BuildConfiguration](zenml.config.md#zenml.config.build_configuration.BuildConfiguration)]

Gets the Docker builds required for the component.

Args:
: deployment: The pipeline deployment for which to get the builds.

Returns:
: The required Docker builds.

#### *static* get_image(deployment: [PipelineDeploymentResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentResponse), step_name: str | None = None) → str

Gets the Docker image for the pipeline/a step.

Args:
: deployment: The deployment from which to get the image.
  step_name: Pipeline step name for which to get the image. If not
  <br/>
  > given the generic pipeline image will be returned.

Raises:
: RuntimeError: If the deployment does not have an associated build.

Returns:
: The image name or digest.

## zenml.orchestrators.dag_runner module

DAG (Directed Acyclic Graph) Runners.

### *class* zenml.orchestrators.dag_runner.NodeStatus(value, names=None, \*, module=None, qualname=None, type=None, start=1, boundary=None)

Bases: `Enum`

Status of the execution of a node.

#### COMPLETED *= 'Completed'*

#### RUNNING *= 'Running'*

#### WAITING *= 'Waiting'*

### *class* zenml.orchestrators.dag_runner.ThreadedDagRunner(dag: Dict[str, List[str]], run_fn: Callable[[str], Any], parallel_node_startup_waiting_period: float = 0.0)

Bases: `object`

Multi-threaded DAG Runner.

This class expects a DAG of strings in adjacency list representation, as
well as a custom run_fn as input, then calls run_fn(node) for each
string node in the DAG.

Steps that can be executed in parallel will be started in separate threads.

#### run() → None

Call self.run_fn on all nodes in self.dag.

The order of execution is determined using topological sort.
Each node is run in a separate thread to enable parallelism.

### zenml.orchestrators.dag_runner.reverse_dag(dag: Dict[str, List[str]]) → Dict[str, List[str]]

Reverse a DAG.

Args:
: dag: Adjacency list representation of a DAG.

Returns:
: Adjacency list representation of the reversed DAG.

## zenml.orchestrators.input_utils module

Utilities for inputs.

### zenml.orchestrators.input_utils.resolve_step_inputs(step: [Step](zenml.config.md#zenml.config.step_configurations.Step), run_id: UUID) → Tuple[Dict[str, [ArtifactVersionResponse](zenml.models.md#zenml.models.ArtifactVersionResponse)], List[UUID]]

Resolves inputs for the current step.

Args:
: step: The step for which to resolve the inputs.
  run_id: The ID of the current pipeline run.

Raises:
: InputResolutionError: If input resolving failed due to a missing
  : step or output.
  <br/>
  ValueError: If object from model version passed into a step cannot be
  : resolved in runtime due to missing object.

Returns:
: The IDs of the input artifact versions and the IDs of parent steps of
  : the current step.

## zenml.orchestrators.output_utils module

Utilities for outputs.

### zenml.orchestrators.output_utils.generate_artifact_uri(artifact_store: [BaseArtifactStore](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore), step_run: [StepRunResponse](zenml.models.md#zenml.models.StepRunResponse), output_name: str) → str

Generates a URI for an output artifact.

Args:
: artifact_store: The artifact store on which the artifact will be stored.
  step_run: The step run that created the artifact.
  output_name: The name of the output in the step run for this artifact.

Returns:
: The URI of the output artifact.

### zenml.orchestrators.output_utils.prepare_output_artifact_uris(step_run: [StepRunResponse](zenml.models.md#zenml.models.StepRunResponse), stack: [Stack](zenml.stack.md#zenml.stack.stack.Stack), step: [Step](zenml.config.md#zenml.config.step_configurations.Step)) → Dict[str, str]

Prepares the output artifact URIs to run the current step.

Args:
: step_run: The step run for which to prepare the artifact URIs.
  stack: The stack on which the pipeline is running.
  step: The step configuration.

Raises:
: RuntimeError: If an artifact URI already exists.

Returns:
: A dictionary mapping output names to artifact URIs.

### zenml.orchestrators.output_utils.remove_artifact_dirs(artifact_uris: Sequence[str]) → None

Removes the artifact directories.

Args:
: artifact_uris: URIs of the artifacts to remove the directories for.

## zenml.orchestrators.publish_utils module

Utilities to publish pipeline and step runs.

### zenml.orchestrators.publish_utils.get_pipeline_run_status(step_statuses: List[[ExecutionStatus](zenml.md#zenml.enums.ExecutionStatus)], num_steps: int) → [ExecutionStatus](zenml.md#zenml.enums.ExecutionStatus)

Gets the pipeline run status for the given step statuses.

Args:
: step_statuses: The status of steps in this run.
  num_steps: The total amount of steps in this run.

Returns:
: The run status.

### zenml.orchestrators.publish_utils.publish_failed_pipeline_run(pipeline_run_id: UUID) → [PipelineRunResponse](zenml.models.md#zenml.models.PipelineRunResponse)

Publishes a failed pipeline run.

Args:
: pipeline_run_id: The ID of the pipeline run to update.

Returns:
: The updated pipeline run.

### zenml.orchestrators.publish_utils.publish_failed_step_run(step_run_id: UUID) → [StepRunResponse](zenml.models.md#zenml.models.StepRunResponse)

Publishes a failed step run.

Args:
: step_run_id: The ID of the step run to update.

Returns:
: The updated step run.

### zenml.orchestrators.publish_utils.publish_pipeline_run_metadata(pipeline_run_id: UUID, pipeline_run_metadata: Dict[UUID, Dict[str, MetadataType]]) → None

Publishes the given pipeline run metadata.

Args:
: pipeline_run_id: The ID of the pipeline run.
  pipeline_run_metadata: A dictionary mapping stack component IDs to the
  <br/>
  > metadata they created.

### zenml.orchestrators.publish_utils.publish_step_run_metadata(step_run_id: UUID, step_run_metadata: Dict[UUID, Dict[str, MetadataType]]) → None

Publishes the given step run metadata.

Args:
: step_run_id: The ID of the step run.
  step_run_metadata: A dictionary mapping stack component IDs to the
  <br/>
  > metadata they created.

### zenml.orchestrators.publish_utils.publish_successful_step_run(step_run_id: UUID, output_artifact_ids: Dict[str, UUID]) → [StepRunResponse](zenml.models.md#zenml.models.StepRunResponse)

Publishes a successful step run.

Args:
: step_run_id: The ID of the step run to update.
  output_artifact_ids: The output artifact IDs for the step run.

Returns:
: The updated step run.

## zenml.orchestrators.step_launcher module

Class to launch (run directly or using a step operator) steps.

### *class* zenml.orchestrators.step_launcher.StepLauncher(deployment: [PipelineDeploymentResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentResponse), step: [Step](zenml.config.md#zenml.config.step_configurations.Step), orchestrator_run_id: str)

Bases: `object`

A class responsible for launching a step of a ZenML pipeline.

This class follows these steps to launch and publish a ZenML step:
1. Publish or reuse a PipelineRun
2. Resolve the input artifacts of the step
3. Generate a cache key for the step
4. Check if the step can be cached or not
5. Publish a new StepRun
6. If the step can’t be cached, the step will be executed in one of these
two ways depending on its configuration:

> - Calling a step operator to run the step in a different environment
> - Calling a step runner to run the step in the current environment
1. Update the status of the previously published StepRun
2. Update the status of the PipelineRun

#### launch() → None

Launches the step.

Raises:
: BaseException: If the step failed to launch, run, or publish.

## zenml.orchestrators.step_runner module

Class to run steps.

### *class* zenml.orchestrators.step_runner.StepRunner(step: [Step](zenml.config.md#zenml.config.step_configurations.Step), stack: [Stack](zenml.stack.md#zenml.stack.stack.Stack))

Bases: `object`

Class to run steps.

#### *property* configuration *: [StepConfiguration](zenml.config.md#zenml.config.step_configurations.StepConfiguration)*

Configuration of the step to run.

Returns:
: The step configuration.

#### load_and_run_hook(hook_source: [Source](zenml.config.md#zenml.config.source.Source), step_exception: BaseException | None) → None

Loads hook source and runs the hook.

Args:
: hook_source: The source of the hook function.
  step_exception: The exception of the original step.

#### run(pipeline_run: [PipelineRunResponse](zenml.models.md#zenml.models.PipelineRunResponse), step_run: [StepRunResponse](zenml.models.md#zenml.models.StepRunResponse), input_artifacts: Dict[str, [ArtifactVersionResponse](zenml.models.md#zenml.models.ArtifactVersionResponse)], output_artifact_uris: Dict[str, str], step_run_info: [StepRunInfo](zenml.config.md#zenml.config.step_run_info.StepRunInfo)) → None

Runs the step.

Args:
: pipeline_run: The model of the current pipeline run.
  step_run: The model of the current step run.
  input_artifacts: The input artifact versions of the step.
  output_artifact_uris: The URIs of the output artifacts of the step.
  step_run_info: The step run info.

Raises:
: BaseException: A general exception if the step fails.

## zenml.orchestrators.topsort module

Utilities for topological sort.

Implementation heavily inspired by TFX:
[https://github.com/tensorflow/tfx/blob/master/tfx/utils/topsort.py](https://github.com/tensorflow/tfx/blob/master/tfx/utils/topsort.py)

### zenml.orchestrators.topsort.topsorted_layers(nodes: Sequence[NodeT], get_node_id_fn: Callable[[NodeT], str], get_parent_nodes: Callable[[NodeT], List[NodeT]], get_child_nodes: Callable[[NodeT], List[NodeT]]) → List[List[NodeT]]

Sorts the DAG of nodes in topological order.

Args:
: nodes: A sequence of nodes.
  get_node_id_fn: Callable that returns a unique text identifier for a node.
  get_parent_nodes: Callable that returns a list of parent nodes for a node.
  <br/>
  > If a parent node’s id is not found in the list of node ids, that parent
  > node will be omitted.
  <br/>
  get_child_nodes: Callable that returns a list of child nodes for a node.
  : If a child node’s id is not found in the list of node ids, that child
    node will be omitted.

Returns:
: A list of topologically ordered node layers. Each layer of nodes is sorted
  by its node id given by get_node_id_fn.

Raises:
: RuntimeError: If the input nodes don’t form a DAG.
  ValueError: If the nodes are not unique.

## zenml.orchestrators.utils module

Utility functions for the orchestrator.

### zenml.orchestrators.utils.get_config_environment_vars(deployment: [PipelineDeploymentResponse](zenml.models.md#zenml.models.PipelineDeploymentResponse) | None = None) → Dict[str, str]

Gets environment variables to set for mirroring the active config.

If a pipeline deployment is given, the environment variables will be set to
include a newly generated API token valid for the duration of the pipeline
run instead of the API token from the global config.

Args:
: deployment: Optional deployment to use for the environment variables.

Returns:
: Environment variable dict.

### zenml.orchestrators.utils.get_orchestrator_run_name(pipeline_name: str) → str

Gets an orchestrator run name.

This run name is not the same as the ZenML run name but can instead be
used to display in the orchestrator UI.

Args:
: pipeline_name: Name of the pipeline that will run.

Returns:
: The orchestrator run name.

### zenml.orchestrators.utils.get_run_name(run_name_template: str) → str

Fill out the run name template to get a complete run name.

Args:
: run_name_template: The run name template to fill out.

Raises:
: ValueError: If the run name is empty.

Returns:
: The run name derived from the template.

### zenml.orchestrators.utils.is_setting_enabled(is_enabled_on_step: bool | None, is_enabled_on_pipeline: bool | None) → bool

Checks if a certain setting is enabled within a step run.

This is the case if:
- the setting is explicitly enabled for the step, or
- the setting is neither explicitly disabled for the step nor the pipeline.

Args:
: is_enabled_on_step: The setting of the step.
  is_enabled_on_pipeline: The setting of the pipeline.

Returns:
: True if the setting is enabled within the step run, False otherwise.

### *class* zenml.orchestrators.utils.register_artifact_store_filesystem(target_artifact_store_id: UUID | None)

Bases: `object`

Context manager for the artifact_store/filesystem_registry dependency.

Even though it is rare, sometimes we bump into cases where we are trying to
load artifacts that belong to an artifact store which is different from
the active artifact store.

In cases like this, we will try to instantiate the target artifact store
by creating the corresponding artifact store Python object, which ends up
registering the right filesystem in the filesystem registry.

The problem is, the keys in the filesystem registry are schemes (such as
“s3://” or “gcs://”). If we have two artifact stores with the same set of
supported schemes, we might end up overwriting the filesystem that belongs
to the active artifact store (and its authentication). That’s why we have
to re-instantiate the active artifact store again, so the correct filesystem
will be restored.

## zenml.orchestrators.wheeled_orchestrator module

Wheeled orchestrator class.

### *class* zenml.orchestrators.wheeled_orchestrator.WheeledOrchestrator(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`BaseOrchestrator`](#zenml.orchestrators.base_orchestrator.BaseOrchestrator), `ABC`

Base class for wheeled orchestrators.

#### copy_repository_to_temp_dir_and_add_setup_py() → str

Copy the repository to a temporary directory and add a setup.py file.

Returns:
: Path to the temporary directory containing the copied repository.

#### create_wheel(temp_dir: str) → str

Create a wheel for the package in the given temporary directory.

Args:
: temp_dir (str): Path to the temporary directory containing the package.

Raises:
: RuntimeError: If the wheel file could not be created.

Returns:
: str: Path to the created wheel file.

#### package_name *= 'zenmlproject'*

#### package_version *= '0.66.0'*

#### sanitize_name(name: str) → str

Sanitize the value to be used in a cluster name.

Args:
: name: Arbitrary input cluster name.

Returns:
: Sanitized cluster name.

## Module contents

Initialization for ZenML orchestrators.

An orchestrator is a special kind of backend that manages the running of each
step of the pipeline. Orchestrators administer the actual pipeline runs. You can
think of it as the ‘root’ of any pipeline job that you run during your
experimentation.

ZenML supports a local orchestrator out of the box which allows you to run your
pipelines in a local environment. We also support using Apache Airflow as the
orchestrator to handle the steps of your pipeline.

### *class* zenml.orchestrators.BaseOrchestrator(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`StackComponent`](zenml.stack.md#zenml.stack.stack_component.StackComponent), `ABC`

Base class for all orchestrators.

In order to implement an orchestrator you will need to subclass from this
class.

### How it works:

The run(…) method is the entrypoint that is executed when the
pipeline’s run method is called within the user code
(pipeline_instance.run(…)).

This method will do some internal preparation and then call the
prepare_or_run_pipeline(…) method. BaseOrchestrator subclasses must
implement this method and either run the pipeline steps directly or deploy
the pipeline to some remote infrastructure.

#### *property* config *: [BaseOrchestratorConfig](#zenml.orchestrators.base_orchestrator.BaseOrchestratorConfig)*

Returns the BaseOrchestratorConfig config.

Returns:
: The configuration.

#### *abstract* get_orchestrator_run_id() → str

Returns the run id of the active orchestrator run.

Important: This needs to be a unique ID and return the same value for
all steps of a pipeline run.

Returns:
: The orchestrator run id.

#### *abstract* prepare_or_run_pipeline(deployment: [PipelineDeploymentResponse](zenml.models.md#zenml.models.PipelineDeploymentResponse), stack: [Stack](zenml.stack.md#zenml.stack.stack.Stack), environment: Dict[str, str]) → Any

The method needs to be implemented by the respective orchestrator.

Depending on the type of orchestrator you’ll have to perform slightly
different operations.

#### Simple Case:

The Steps are run directly from within the same environment in which
the orchestrator code is executed. In this case you will need to
deal with implementation-specific runtime configurations (like the
schedule) and then iterate through the steps and finally call
self.run_step(…) to execute each step.

#### Advanced Case:

Most orchestrators will not run the steps directly. Instead, they
build some intermediate representation of the pipeline that is then
used to create and run the pipeline and its steps on the target
environment. For such orchestrators this method will have to build
this representation and deploy it.

Regardless of the implementation details, the orchestrator will need
to run each step in the target environment. For this the
self.run_step(…) method should be used.

The easiest way to make this work is by using an entrypoint
configuration to run single steps (zenml.entrypoints.step_entrypoint_configuration.StepEntrypointConfiguration)
or entire pipelines (zenml.entrypoints.pipeline_entrypoint_configuration.PipelineEntrypointConfiguration).

Args:
: deployment: The pipeline deployment to prepare or run.
  stack: The stack the pipeline will run on.
  environment: Environment variables to set in the orchestration
  <br/>
  > environment. These don’t need to be set if running locally.

Returns:
: The optional return value from this method will be returned by the
  pipeline_instance.run() call when someone is running a pipeline.

#### *static* requires_resources_in_orchestration_environment(step: [Step](zenml.config.md#zenml.config.step_configurations.Step)) → bool

Checks if the orchestrator should run this step on special resources.

Args:
: step: The step that will be checked.

Returns:
: True if the step requires special resources in the orchestration
  environment, False otherwise.

#### run(deployment: [PipelineDeploymentResponse](zenml.models.md#zenml.models.PipelineDeploymentResponse), stack: [Stack](zenml.stack.md#zenml.stack.stack.Stack)) → Any

Runs a pipeline on a stack.

Args:
: deployment: The pipeline deployment.
  stack: The stack on which to run the pipeline.

Returns:
: Orchestrator-specific return value.

#### run_step(step: [Step](zenml.config.md#zenml.config.step_configurations.Step)) → None

Runs the given step.

Args:
: step: The step to run.

### *class* zenml.orchestrators.BaseOrchestratorConfig(warn_about_plain_text_secrets: bool = False)

Bases: [`StackComponentConfig`](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig)

Base orchestrator config.

#### *property* is_schedulable *: bool*

Whether the orchestrator is schedulable or not.

Returns:
: Whether the orchestrator is schedulable or not.

#### *property* is_synchronous *: bool*

Whether the orchestrator runs synchronous or not.

Returns:
: Whether the orchestrator runs synchronous or not.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.orchestrators.BaseOrchestratorFlavor

Bases: [`Flavor`](zenml.stack.md#zenml.stack.flavor.Flavor)

Base orchestrator flavor class.

#### *property* config_class *: Type[[BaseOrchestratorConfig](#zenml.orchestrators.base_orchestrator.BaseOrchestratorConfig)]*

Config class for the base orchestrator flavor.

Returns:
: The config class.

#### *abstract property* implementation_class *: Type[[BaseOrchestrator](#zenml.orchestrators.base_orchestrator.BaseOrchestrator)]*

Implementation class for this flavor.

Returns:
: The implementation class.

#### *property* type *: [StackComponentType](zenml.md#zenml.enums.StackComponentType)*

Returns the flavor type.

Returns:
: The flavor type.

### *class* zenml.orchestrators.ContainerizedOrchestrator(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`BaseOrchestrator`](#zenml.orchestrators.base_orchestrator.BaseOrchestrator), `ABC`

Base class for containerized orchestrators.

#### get_docker_builds(deployment: [PipelineDeploymentBase](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentBase)) → List[[BuildConfiguration](zenml.config.md#zenml.config.build_configuration.BuildConfiguration)]

Gets the Docker builds required for the component.

Args:
: deployment: The pipeline deployment for which to get the builds.

Returns:
: The required Docker builds.

#### *static* get_image(deployment: [PipelineDeploymentResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentResponse), step_name: str | None = None) → str

Gets the Docker image for the pipeline/a step.

Args:
: deployment: The deployment from which to get the image.
  step_name: Pipeline step name for which to get the image. If not
  <br/>
  > given the generic pipeline image will be returned.

Raises:
: RuntimeError: If the deployment does not have an associated build.

Returns:
: The image name or digest.

### *class* zenml.orchestrators.LocalDockerOrchestrator(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`ContainerizedOrchestrator`](#zenml.orchestrators.containerized_orchestrator.ContainerizedOrchestrator)

Orchestrator responsible for running pipelines locally using Docker.

This orchestrator does not allow for concurrent execution of steps and also
does not support running on a schedule.

#### get_orchestrator_run_id() → str

Returns the active orchestrator run id.

Raises:
: RuntimeError: If the environment variable specifying the run id
  : is not set.

Returns:
: The orchestrator run id.

#### prepare_or_run_pipeline(deployment: [PipelineDeploymentResponse](zenml.models.md#zenml.models.PipelineDeploymentResponse), stack: [Stack](zenml.stack.md#zenml.stack.stack.Stack), environment: Dict[str, str]) → Any

Sequentially runs all pipeline steps in local Docker containers.

Args:
: deployment: The pipeline deployment to prepare or run.
  stack: The stack the pipeline will run on.
  environment: Environment variables to set in the orchestration
  <br/>
  > environment.

Raises:
: RuntimeError: If a step fails.

#### *property* settings_class *: Type[[BaseSettings](zenml.config.md#zenml.config.base_settings.BaseSettings)] | None*

Settings class for the Local Docker orchestrator.

Returns:
: The settings class.

#### *property* validator *: [StackValidator](zenml.stack.md#zenml.stack.stack_validator.StackValidator) | None*

Ensures there is an image builder in the stack.

Returns:
: A StackValidator instance.

### *class* zenml.orchestrators.LocalDockerOrchestratorFlavor

Bases: [`BaseOrchestratorFlavor`](#zenml.orchestrators.base_orchestrator.BaseOrchestratorFlavor)

Flavor for the local Docker orchestrator.

#### *property* config_class *: Type[[BaseOrchestratorConfig](#zenml.orchestrators.base_orchestrator.BaseOrchestratorConfig)]*

Config class for the base orchestrator flavor.

Returns:
: The config class.

#### *property* docs_url *: str | None*

A url to point at docs explaining this flavor.

Returns:
: A flavor docs url.

#### *property* implementation_class *: Type[[LocalDockerOrchestrator](zenml.orchestrators.local_docker.md#zenml.orchestrators.local_docker.local_docker_orchestrator.LocalDockerOrchestrator)]*

Implementation class for this flavor.

Returns:
: Implementation class for this flavor.

#### *property* logo_url *: str*

A url to represent the flavor in the dashboard.

Returns:
: The flavor logo.

#### *property* name *: str*

Name of the orchestrator flavor.

Returns:
: Name of the orchestrator flavor.

#### *property* sdk_docs_url *: str | None*

A url to point at SDK docs explaining this flavor.

Returns:
: A flavor SDK docs url.

### *class* zenml.orchestrators.LocalOrchestrator(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`BaseOrchestrator`](#zenml.orchestrators.base_orchestrator.BaseOrchestrator)

Orchestrator responsible for running pipelines locally.

This orchestrator does not allow for concurrent execution of steps and also
does not support running on a schedule.

#### get_orchestrator_run_id() → str

Returns the active orchestrator run id.

Raises:
: RuntimeError: If no run id exists. This happens when this method
  : gets called while the orchestrator is not running a pipeline.

Returns:
: The orchestrator run id.

#### prepare_or_run_pipeline(deployment: [PipelineDeploymentResponse](zenml.models.md#zenml.models.PipelineDeploymentResponse), stack: [Stack](zenml.stack.md#zenml.stack.stack.Stack), environment: Dict[str, str]) → Any

Iterates through all steps and executes them sequentially.

Args:
: deployment: The pipeline deployment to prepare or run.
  stack: The stack on which the pipeline is deployed.
  environment: Environment variables to set in the orchestration
  <br/>
  > environment.

### *class* zenml.orchestrators.LocalOrchestratorFlavor

Bases: [`BaseOrchestratorFlavor`](#zenml.orchestrators.base_orchestrator.BaseOrchestratorFlavor)

Class for the LocalOrchestratorFlavor.

#### *property* config_class *: Type[[BaseOrchestratorConfig](#zenml.orchestrators.base_orchestrator.BaseOrchestratorConfig)]*

Config class for the base orchestrator flavor.

Returns:
: The config class.

#### *property* docs_url *: str | None*

A URL to point at docs explaining this flavor.

Returns:
: A flavor docs url.

#### *property* implementation_class *: Type[[LocalOrchestrator](zenml.orchestrators.local.md#zenml.orchestrators.local.local_orchestrator.LocalOrchestrator)]*

Implementation class for this flavor.

Returns:
: The implementation class for this flavor.

#### *property* logo_url *: str*

A URL to represent the flavor in the dashboard.

Returns:
: The flavor logo.

#### *property* name *: str*

The flavor name.

Returns:
: The flavor name.

#### *property* sdk_docs_url *: str | None*

A URL to point at SDK docs explaining this flavor.

Returns:
: A flavor SDK docs url.

### *class* zenml.orchestrators.WheeledOrchestrator(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`BaseOrchestrator`](#zenml.orchestrators.base_orchestrator.BaseOrchestrator), `ABC`

Base class for wheeled orchestrators.

#### copy_repository_to_temp_dir_and_add_setup_py() → str

Copy the repository to a temporary directory and add a setup.py file.

Returns:
: Path to the temporary directory containing the copied repository.

#### create_wheel(temp_dir: str) → str

Create a wheel for the package in the given temporary directory.

Args:
: temp_dir (str): Path to the temporary directory containing the package.

Raises:
: RuntimeError: If the wheel file could not be created.

Returns:
: str: Path to the created wheel file.

#### package_name *= 'zenmlproject'*

#### package_version *= '0.66.0'*

#### sanitize_name(name: str) → str

Sanitize the value to be used in a cluster name.

Args:
: name: Arbitrary input cluster name.

Returns:
: Sanitized cluster name.
