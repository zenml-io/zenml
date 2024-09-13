# zenml.orchestrators.local package

## Submodules

## zenml.orchestrators.local.local_orchestrator module

Implementation of the ZenML local orchestrator.

### *class* zenml.orchestrators.local.local_orchestrator.LocalOrchestrator(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`BaseOrchestrator`](zenml.orchestrators.md#zenml.orchestrators.base_orchestrator.BaseOrchestrator)

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

### *class* zenml.orchestrators.local.local_orchestrator.LocalOrchestratorConfig(warn_about_plain_text_secrets: bool = False)

Bases: [`BaseOrchestratorConfig`](zenml.orchestrators.md#zenml.orchestrators.base_orchestrator.BaseOrchestratorConfig)

Local orchestrator config.

#### *property* is_local *: bool*

Checks if this stack component is running locally.

Returns:
: True if this config is for a local component, False otherwise.

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

### *class* zenml.orchestrators.local.local_orchestrator.LocalOrchestratorFlavor

Bases: [`BaseOrchestratorFlavor`](zenml.orchestrators.md#zenml.orchestrators.base_orchestrator.BaseOrchestratorFlavor)

Class for the LocalOrchestratorFlavor.

#### *property* config_class *: Type[[BaseOrchestratorConfig](zenml.orchestrators.md#zenml.orchestrators.base_orchestrator.BaseOrchestratorConfig)]*

Config class for the base orchestrator flavor.

Returns:
: The config class.

#### *property* docs_url *: str | None*

A URL to point at docs explaining this flavor.

Returns:
: A flavor docs url.

#### *property* implementation_class *: Type[[LocalOrchestrator](#zenml.orchestrators.local.local_orchestrator.LocalOrchestrator)]*

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

## Module contents

Initialization for the local orchestrator.
