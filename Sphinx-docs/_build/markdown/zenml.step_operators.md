# zenml.step_operators package

## Submodules

## zenml.step_operators.base_step_operator module

Base class for ZenML step operators.

### *class* zenml.step_operators.base_step_operator.BaseStepOperator(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`StackComponent`](zenml.stack.md#zenml.stack.stack_component.StackComponent), `ABC`

Base class for all ZenML step operators.

#### *property* config *: [BaseStepOperatorConfig](#zenml.step_operators.base_step_operator.BaseStepOperatorConfig)*

Returns the config of the step operator.

Returns:
: The config of the step operator.

#### *property* entrypoint_config_class *: Type[[StepOperatorEntrypointConfiguration](#zenml.step_operators.step_operator_entrypoint_configuration.StepOperatorEntrypointConfiguration)]*

Returns the entrypoint configuration class for this step operator.

Concrete step operator implementations may override this property
to return a custom entrypoint configuration class if they need to
customize the entrypoint configuration.

Returns:
: The entrypoint configuration class for this step operator.

#### *abstract* launch(info: [StepRunInfo](zenml.config.md#zenml.config.step_run_info.StepRunInfo), entrypoint_command: List[str], environment: Dict[str, str]) → None

Abstract method to execute a step.

Subclasses must implement this method and launch a **synchronous**
job that executes the entrypoint_command.

Args:
: info: Information about the step run.
  entrypoint_command: Command that executes the step.
  environment: Environment variables to set in the step operator
  <br/>
  > environment.

### *class* zenml.step_operators.base_step_operator.BaseStepOperatorConfig(warn_about_plain_text_secrets: bool = False)

Bases: [`StackComponentConfig`](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig)

Base config for step operators.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.step_operators.base_step_operator.BaseStepOperatorFlavor

Bases: [`Flavor`](zenml.stack.md#zenml.stack.flavor.Flavor)

Base class for all ZenML step operator flavors.

#### *property* config_class *: Type[[BaseStepOperatorConfig](#zenml.step_operators.base_step_operator.BaseStepOperatorConfig)]*

Returns the config class for this flavor.

Returns:
: The config class for this flavor.

#### *abstract property* implementation_class *: Type[[BaseStepOperator](#zenml.step_operators.base_step_operator.BaseStepOperator)]*

Returns the implementation class for this flavor.

Returns:
: The implementation class for this flavor.

#### *property* type *: [StackComponentType](zenml.md#zenml.enums.StackComponentType)*

Returns the flavor type.

Returns:
: The type of the flavor.

## zenml.step_operators.step_operator_entrypoint_configuration module

Abstract base class for entrypoint configurations that run a single step.

### *class* zenml.step_operators.step_operator_entrypoint_configuration.StepOperatorEntrypointConfiguration(arguments: List[str])

Bases: [`StepEntrypointConfiguration`](zenml.entrypoints.md#zenml.entrypoints.step_entrypoint_configuration.StepEntrypointConfiguration)

Base class for step operator entrypoint configurations.

#### *classmethod* get_entrypoint_arguments(\*\*kwargs: Any) → List[str]

Gets all arguments that the entrypoint command should be called with.

Args:
: ```
  **
  ```
  <br/>
  kwargs: Kwargs, must include the step run id.

Returns:
: The superclass arguments as well as arguments for the step run id.

#### *classmethod* get_entrypoint_options() → Set[str]

Gets all options required for running with this configuration.

Returns:
: The superclass options as well as an option for the step run id.

## Module contents

Step operators allow you to run steps on custom infrastructure.

While an orchestrator defines how and where your entire pipeline runs, a step
operator defines how and where an individual step runs. This can be useful in a
variety of scenarios. An example could be if one step within a pipeline should
run on a separate environment equipped with a GPU (like a trainer step).

### *class* zenml.step_operators.BaseStepOperator(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`StackComponent`](zenml.stack.md#zenml.stack.stack_component.StackComponent), `ABC`

Base class for all ZenML step operators.

#### *property* config *: [BaseStepOperatorConfig](#zenml.step_operators.base_step_operator.BaseStepOperatorConfig)*

Returns the config of the step operator.

Returns:
: The config of the step operator.

#### *property* entrypoint_config_class *: Type[[StepOperatorEntrypointConfiguration](#zenml.step_operators.step_operator_entrypoint_configuration.StepOperatorEntrypointConfiguration)]*

Returns the entrypoint configuration class for this step operator.

Concrete step operator implementations may override this property
to return a custom entrypoint configuration class if they need to
customize the entrypoint configuration.

Returns:
: The entrypoint configuration class for this step operator.

#### *abstract* launch(info: [StepRunInfo](zenml.config.md#zenml.config.step_run_info.StepRunInfo), entrypoint_command: List[str], environment: Dict[str, str]) → None

Abstract method to execute a step.

Subclasses must implement this method and launch a **synchronous**
job that executes the entrypoint_command.

Args:
: info: Information about the step run.
  entrypoint_command: Command that executes the step.
  environment: Environment variables to set in the step operator
  <br/>
  > environment.

### *class* zenml.step_operators.BaseStepOperatorConfig(warn_about_plain_text_secrets: bool = False)

Bases: [`StackComponentConfig`](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig)

Base config for step operators.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.step_operators.BaseStepOperatorFlavor

Bases: [`Flavor`](zenml.stack.md#zenml.stack.flavor.Flavor)

Base class for all ZenML step operator flavors.

#### *property* config_class *: Type[[BaseStepOperatorConfig](#zenml.step_operators.base_step_operator.BaseStepOperatorConfig)]*

Returns the config class for this flavor.

Returns:
: The config class for this flavor.

#### *abstract property* implementation_class *: Type[[BaseStepOperator](#zenml.step_operators.base_step_operator.BaseStepOperator)]*

Returns the implementation class for this flavor.

Returns:
: The implementation class for this flavor.

#### *property* type *: [StackComponentType](zenml.md#zenml.enums.StackComponentType)*

Returns the flavor type.

Returns:
: The type of the flavor.
