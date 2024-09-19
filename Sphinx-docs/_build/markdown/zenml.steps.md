# zenml.steps package

## Submodules

## zenml.steps.base_parameters module

Step parameters.

### *class* zenml.steps.base_parameters.BaseParameters

Bases: `BaseModel`

Base class to pass parameters into a step.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

## zenml.steps.base_step module

Base Step for ZenML.

### *class* zenml.steps.base_step.BaseStep(\*args: Any, name: str | None = None, enable_cache: bool | None = None, enable_artifact_metadata: bool | None = None, enable_artifact_visualization: bool | None = None, enable_step_logs: bool | None = None, experiment_tracker: str | None = None, step_operator: str | None = None, parameters: ParametersOrDict | None = None, output_materializers: OutputMaterializersSpecification | None = None, settings: Mapping[str, SettingsOrDict] | None = None, extra: Dict[str, Any] | None = None, on_failure: HookSpecification | None = None, on_success: HookSpecification | None = None, model: [Model](zenml.md#zenml.Model) | None = None, retry: [StepRetryConfig](zenml.config.md#zenml.config.retry_config.StepRetryConfig) | None = None, \*\*kwargs: Any)

Bases: `object`

Abstract base class for all ZenML steps.

#### after(step: [BaseStep](#zenml.steps.base_step.BaseStep)) → None

Adds an upstream step to this step.

Calling this method makes sure this step only starts running once the
given step has successfully finished executing.

**Note**: This can only be called inside the pipeline connect function
which is decorated with the @pipeline decorator. Any calls outside
this function will be ignored.

Example:
The following pipeline will run its steps sequentially in the following
order: step_2 -> step_1 -> step_3

```
``
```

```
`
```

python
@pipeline
def example_pipeline(step_1, step_2, step_3):

> step_1.after(step_2)
> step_3(step_1(), step_2())

```
``
```

```
`
```

Args:
: step: A step which should finish executing before this step is
  : started.

#### *property* caching_parameters *: Dict[str, Any]*

Caching parameters for this step.

Returns:
: A dictionary containing the caching parameters

#### call_entrypoint(\*args: Any, \*\*kwargs: Any) → Any

Calls the entrypoint function of the step.

Args:
: ```
  *
  ```
  <br/>
  args: Entrypoint function arguments.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Entrypoint function keyword arguments.

Returns:
: The return value of the entrypoint function.

Raises:
: StepInterfaceError: If the arguments to the entrypoint function are
  : invalid.

#### *property* configuration *: [PartialStepConfiguration](zenml.config.md#zenml.config.step_configurations.PartialStepConfiguration)*

The configuration of the step.

Returns:
: The configuration of the step.

#### configure(name: str | None = None, enable_cache: bool | None = None, enable_artifact_metadata: bool | None = None, enable_artifact_visualization: bool | None = None, enable_step_logs: bool | None = None, experiment_tracker: str | None = None, step_operator: str | None = None, parameters: ParametersOrDict | None = None, output_materializers: OutputMaterializersSpecification | None = None, settings: Mapping[str, SettingsOrDict] | None = None, extra: Dict[str, Any] | None = None, on_failure: HookSpecification | None = None, on_success: HookSpecification | None = None, model: [Model](zenml.md#zenml.Model) | None = None, merge: bool = True, retry: [StepRetryConfig](zenml.config.md#zenml.config.retry_config.StepRetryConfig) | None = None) → T

Configures the step.

Configuration merging example:
\* merge==True:

> step.configure(extra={“key1”: 1})
> step.configure(extra={“key2”: 2}, merge=True)
> step.configuration.extra # {“key1”: 1, “key2”: 2}
* merge==False:
  : step.configure(extra={“key1”: 1})
    step.configure(extra={“key2”: 2}, merge=False)
    step.configuration.extra # {“key2”: 2}

Args:
: name: DEPRECATED: The name of the step.
  enable_cache: If caching should be enabled for this step.
  enable_artifact_metadata: If artifact metadata should be enabled
  <br/>
  > for this step.
  <br/>
  enable_artifact_visualization: If artifact visualization should be
  : enabled for this step.
  <br/>
  enable_step_logs: If step logs should be enabled for this step.
  experiment_tracker: The experiment tracker to use for this step.
  step_operator: The step operator to use for this step.
  parameters: Function parameters for this step
  output_materializers: Output materializers for this step. If
  <br/>
  > given as a dict, the keys must be a subset of the output names
  > of this step. If a single value (type or string) is given, the
  > materializer will be used for all outputs.
  <br/>
  settings: settings for this step.
  extra: Extra configurations for this step.
  on_failure: Callback function in event of failure of the step. Can
  <br/>
  > be a function with a single argument of type BaseException, or
  > a source path to such a function (e.g. module.my_function).
  <br/>
  on_success: Callback function in event of success of the step. Can
  : be a function with no arguments, or a source path to such a
    function (e.g. module.my_function).
  <br/>
  model: configuration of the model version in the Model Control Plane.
  merge: If True, will merge the given dictionary configurations
  <br/>
  > like parameters and settings with existing
  > configurations. If False the given configurations will
  > overwrite all existing ones. See the general description of this
  > method for an example.
  <br/>
  retry: Configuration for retrying the step in case of failure.

Returns:
: The step instance that this method was called on.

#### copy() → [BaseStep](#zenml.steps.base_step.BaseStep)

Copies the step.

Returns:
: The step copy.

#### *property* docstring *: str | None*

The docstring of this step.

Returns:
: The docstring of this step.

#### *property* enable_cache *: bool | None*

If caching is enabled for the step.

Returns:
: If caching is enabled for the step.

#### *abstract* entrypoint(\*args: Any, \*\*kwargs: Any) → Any

Abstract method for core step logic.

Args:
: ```
  *
  ```
  <br/>
  args: Positional arguments passed to the step.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments passed to the step.

Returns:
: The output of the step.

#### *classmethod* load_from_source(source: [Source](zenml.config.md#zenml.config.source.Source) | str) → [BaseStep](#zenml.steps.base_step.BaseStep)

Loads a step from source.

Args:
: source: The path to the step source.

Returns:
: The loaded step.

Raises:
: ValueError: If the source is not a valid step source.

#### *property* name *: str*

The name of the step.

Returns:
: The name of the step.

#### resolve() → [Source](zenml.config.md#zenml.config.source.Source)

Resolves the step.

Returns:
: The step source.

#### *property* source_code *: str*

The source code of this step.

Returns:
: The source code of this step.

#### *property* source_object *: Any*

The source object of this step.

Returns:
: The source object of this step.

#### *property* upstream_steps *: Set[[BaseStep](#zenml.steps.base_step.BaseStep)]*

Names of the upstream steps of this step.

This property will only contain the full set of upstream steps once
it’s parent pipeline connect(…) method was called.

Returns:
: Set of upstream step names.

#### with_options(enable_cache: bool | None = None, enable_artifact_metadata: bool | None = None, enable_artifact_visualization: bool | None = None, enable_step_logs: bool | None = None, experiment_tracker: str | None = None, step_operator: str | None = None, parameters: ParametersOrDict | None = None, output_materializers: OutputMaterializersSpecification | None = None, settings: Mapping[str, SettingsOrDict] | None = None, extra: Dict[str, Any] | None = None, on_failure: HookSpecification | None = None, on_success: HookSpecification | None = None, model: [Model](zenml.md#zenml.Model) | None = None, merge: bool = True) → [BaseStep](#zenml.steps.base_step.BaseStep)

Copies the step and applies the given configurations.

Args:
: enable_cache: If caching should be enabled for this step.
  enable_artifact_metadata: If artifact metadata should be enabled
  <br/>
  > for this step.
  <br/>
  enable_artifact_visualization: If artifact visualization should be
  : enabled for this step.
  <br/>
  enable_step_logs: If step logs should be enabled for this step.
  experiment_tracker: The experiment tracker to use for this step.
  step_operator: The step operator to use for this step.
  parameters: Function parameters for this step
  output_materializers: Output materializers for this step. If
  <br/>
  > given as a dict, the keys must be a subset of the output names
  > of this step. If a single value (type or string) is given, the
  > materializer will be used for all outputs.
  <br/>
  settings: settings for this step.
  extra: Extra configurations for this step.
  on_failure: Callback function in event of failure of the step. Can
  <br/>
  > be a function with a single argument of type BaseException, or
  > a source path to such a function (e.g. module.my_function).
  <br/>
  on_success: Callback function in event of success of the step. Can
  : be a function with no arguments, or a source path to such a
    function (e.g. module.my_function).
  <br/>
  model: configuration of the model version in the Model Control Plane.
  merge: If True, will merge the given dictionary configurations
  <br/>
  > like parameters and settings with existing
  > configurations. If False the given configurations will
  > overwrite all existing ones. See the general description of this
  > method for an example.

Returns:
: The copied step instance.

### *class* zenml.steps.base_step.BaseStepMeta(name: str, bases: Tuple[Type[Any], ...], dct: Dict[str, Any])

Bases: `type`

Metaclass for BaseStep.

Makes sure that the entrypoint function has valid parameters and type
annotations.

## zenml.steps.entrypoint_function_utils module

Util functions for step and pipeline entrypoint functions.

### *class* zenml.steps.entrypoint_function_utils.EntrypointFunctionDefinition(inputs: Dict[str, Parameter], outputs: Dict[str, [OutputSignature](#zenml.steps.utils.OutputSignature)], context: Parameter | None, legacy_params: Parameter | None)

Bases: `NamedTuple`

Class representing a step entrypoint function.

Attributes:
: inputs: The entrypoint function inputs.
  outputs: The entrypoint function outputs. This dictionary maps output
  <br/>
  > names to output annotations.
  <br/>
  context: Optional parameter representing the StepContext input.
  legacy_params: Optional parameter representing the BaseParameters
  <br/>
  > input.

#### context *: Parameter | None*

Alias for field number 2

#### inputs *: Dict[str, Parameter]*

Alias for field number 0

#### legacy_params *: Parameter | None*

Alias for field number 3

#### outputs *: Dict[str, [OutputSignature](#zenml.steps.utils.OutputSignature)]*

Alias for field number 1

#### validate_input(key: str, value: Any) → None

Validates an input to the step entrypoint function.

Args:
: key: The key for which the input was passed
  value: The input value.

Raises:
: KeyError: If the function has no input for the given key.
  RuntimeError: If a parameter is passed for an input that is
  <br/>
  > annotated as an UnmaterializedArtifact.
  <br/>
  RuntimeError: If the input value is not valid for the type
  : annotation provided for the function parameter.
  <br/>
  StepInterfaceError: If the input is a parameter and not JSON
  : serializable.

### *class* zenml.steps.entrypoint_function_utils.StepArtifact(invocation_id: str, output_name: str, annotation: Any, pipeline: [Pipeline](zenml.new.pipelines.md#zenml.new.pipelines.pipeline.Pipeline))

Bases: `object`

Class to represent step output artifacts.

### zenml.steps.entrypoint_function_utils.get_step_entrypoint_signature(step: [BaseStep](#zenml.steps.base_step.BaseStep)) → Signature

Get the entrypoint signature of a step.

Args:
: step: The step for which to get the entrypoint signature.

Returns:
: The entrypoint function signature.

### zenml.steps.entrypoint_function_utils.validate_entrypoint_function(func: Callable[[...], Any], reserved_arguments: Sequence[str] = ()) → [EntrypointFunctionDefinition](#zenml.steps.entrypoint_function_utils.EntrypointFunctionDefinition)

Validates a step entrypoint function.

Args:
: func: The step entrypoint function to validate.
  reserved_arguments: The reserved arguments for the entrypoint function.

Raises:
: StepInterfaceError: If the entrypoint function has variable arguments
  : or keyword arguments.
  <br/>
  StepInterfaceError: If the entrypoint function has multiple
  : BaseParameter arguments.
  <br/>
  StepInterfaceError: If the entrypoint function has multiple
  : StepContext arguments.
  <br/>
  RuntimeError: If type annotations should be enforced and a type
  : annotation is missing.

Returns:
: A validated definition of the entrypoint function.

### zenml.steps.entrypoint_function_utils.validate_reserved_arguments(signature: Signature, reserved_arguments: Sequence[str]) → None

Validates that the signature does not contain any reserved arguments.

Args:
: signature: The signature to validate.
  reserved_arguments: The reserved arguments for the signature.

Raises:
: RuntimeError: If the signature contains a reserved argument.

## zenml.steps.external_artifact module

Backward compatibility for the ExternalArtifact class.

### *class* zenml.steps.external_artifact.ExternalArtifact(\*, id: UUID | None = None, name: str | None = None, version: str | None = None, model: [Model](zenml.model.md#zenml.model.model.Model) | None = None, value: Any | None = None, materializer: Annotated[str | [Source](zenml.config.md#zenml.config.source.Source) | Type[[BaseMaterializer](zenml.materializers.md#zenml.materializers.base_materializer.BaseMaterializer)] | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, store_artifact_metadata: bool = True, store_artifact_visualizations: bool = True)

Bases: [`ExternalArtifactConfiguration`](zenml.artifacts.md#zenml.artifacts.external_artifact_config.ExternalArtifactConfiguration)

External artifacts can be used to provide values as input to ZenML steps.

ZenML steps accept either artifacts (=outputs of other steps), parameters
(raw, JSON serializable values) or external artifacts. External artifacts
can be used to provide any value as input to a step without needing to
write an additional step that returns this value.

The external artifact needs to have either a value associated with it
that will be uploaded to the artifact store, or reference an artifact
that is already registered in ZenML.

There are several ways to reference an existing artifact:
- By providing an artifact ID.
- By providing an artifact name and version. If no version is provided,

> the latest version of that artifact will be used.

Args:
: value: The artifact value.
  id: The ID of an artifact that should be referenced by this external
  <br/>
  > artifact.
  <br/>
  materializer: The materializer to use for saving the artifact value
  : to the artifact store. Only used when value is provided.
  <br/>
  store_artifact_metadata: Whether metadata for the artifact should
  : be stored. Only used when value is provided.
  <br/>
  store_artifact_visualizations: Whether visualizations for the
  : artifact should be stored. Only used when value is provided.

Example:

```
``
```

\`
from zenml import step, pipeline
from zenml.artifacts.external_artifact import ExternalArtifact
import numpy as np

@step
def my_step(value: np.ndarray) -> None:

> print(value)

my_array = np.array([1, 2, 3])

@pipeline
def my_pipeline():

> my_step(value=ExternalArtifact(my_array))

```
``
```

```
`
```

#### *property* config *: [ExternalArtifactConfiguration](zenml.artifacts.md#zenml.artifacts.external_artifact_config.ExternalArtifactConfiguration)*

Returns the lightweight config without hard for JSON properties.

Returns:
: The config object to be evaluated in runtime by step interface.

#### external_artifact_validator() → [ExternalArtifact](zenml.artifacts.md#zenml.artifacts.external_artifact.ExternalArtifact)

Model validator for the external artifact.

Raises:
: ValueError: if the value, id and name fields are set incorrectly.

Returns:
: the validated instance.

#### id *: UUID | None*

#### materializer *: str | [Source](zenml.config.md#zenml.config.source.Source) | Type[[BaseMaterializer](zenml.materializers.md#zenml.materializers.base_materializer.BaseMaterializer)] | None*

#### model *: [Model](zenml.md#zenml.Model) | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None), 'materializer': FieldInfo(annotation=Union[str, Source, Type[BaseMaterializer], NoneType], required=False, default=None, metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'model': FieldInfo(annotation=Union[Model, NoneType], required=False, default=None), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'store_artifact_metadata': FieldInfo(annotation=bool, required=False, default=True), 'store_artifact_visualizations': FieldInfo(annotation=bool, required=False, default=True), 'value': FieldInfo(annotation=Union[Any, NoneType], required=False, default=None), 'version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str | None*

#### store_artifact_metadata *: bool*

#### store_artifact_visualizations *: bool*

#### upload_by_value() → UUID

Uploads the artifact by value.

Returns:
: The uploaded artifact ID.

#### value *: Any | None*

#### version *: str | None*

## zenml.steps.step_decorator module

Step decorator function.

### zenml.steps.step_decorator.step(\_func: F) → Type[[BaseStep](#zenml.steps.base_step.BaseStep)]

### zenml.steps.step_decorator.step(\*, name: str | None = None, enable_cache: bool | None = None, enable_artifact_metadata: bool | None = None, enable_artifact_visualization: bool | None = None, enable_step_logs: bool | None = None, experiment_tracker: str | None = None, step_operator: str | None = None, output_materializers: 'OutputMaterializersSpecification' | None = None, settings: Dict[str, 'SettingsOrDict'] | None = None, extra: Dict[str, Any] | None = None, on_failure: 'HookSpecification' | None = None, on_success: 'HookSpecification' | None = None, model: 'Model' | None = None) → Callable[[F], Type[[BaseStep](#zenml.steps.base_step.BaseStep)]]

Outer decorator function for the creation of a ZenML step.

In order to be able to work with parameters such as name, it features a
nested decorator structure.

Args:
: \_func: The decorated function.
  name: The name of the step. If left empty, the name of the decorated
  <br/>
  > function will be used as a fallback.
  <br/>
  enable_cache: Specify whether caching is enabled for this step. If no
  : value is passed, caching is enabled by default.
  <br/>
  enable_artifact_metadata: Specify whether metadata is enabled for this
  : step. If no value is passed, metadata is enabled by default.
  <br/>
  enable_artifact_visualization: Specify whether visualization is enabled
  : for this step. If no value is passed, visualization is enabled by
    default.
  <br/>
  enable_step_logs: Specify whether step logs are enabled for this step.
  experiment_tracker: The experiment tracker to use for this step.
  step_operator: The step operator to use for this step.
  output_materializers: Output materializers for this step. If
  <br/>
  > given as a dict, the keys must be a subset of the output names
  > of this step. If a single value (type or string) is given, the
  > materializer will be used for all outputs.
  <br/>
  settings: Settings for this step.
  extra: Extra configurations for this step.
  on_failure: Callback function in event of failure of the step. Can be a
  <br/>
  > function with a single argument of type BaseException, or a source
  > path to such a function (e.g. module.my_function).
  <br/>
  on_success: Callback function in event of success of the step. Can be a
  : function with no arguments, or a source path to such a function
    (e.g. module.my_function).
  <br/>
  model: configuration of the model version in the Model Control Plane.

Returns:
: The inner decorator which creates the step class based on the
  ZenML BaseStep

## zenml.steps.step_environment module

Step environment class.

### *class* zenml.steps.step_environment.StepEnvironment(step_run_info: [StepRunInfo](zenml.config.md#zenml.config.step_run_info.StepRunInfo), cache_enabled: bool)

Bases: [`BaseEnvironmentComponent`](zenml.md#zenml.environment.BaseEnvironmentComponent)

(Deprecated) Added information about a run inside a step function.

This takes the form of an Environment component. This class can be used from
within a pipeline step implementation to access additional information about
the runtime parameters of a pipeline step, such as the pipeline name,
pipeline run ID and other pipeline runtime information. To use it, access it
inside your step function like this:

```
``
```

```
`
```

python
from zenml.environment import Environment

@step
def my_step(…)

> env = Environment().step_environment
> do_something_with(env.pipeline_name, env.run_name, env.step_name)

```
``
```

```
`
```

#### NAME *: str* *= 'step_environment'*

#### *property* cache_enabled *: bool*

Returns whether cache is enabled for the step.

Returns:
: True if cache is enabled for the step, otherwise False.

#### *property* pipeline_name *: str*

The name of the currently running pipeline.

Returns:
: The name of the currently running pipeline.

#### *property* run_name *: str*

The name of the current pipeline run.

Returns:
: The name of the current pipeline run.

#### *property* step_name *: str*

The name of the currently running step.

Returns:
: The name of the currently running step.

#### *property* step_run_info *: [StepRunInfo](zenml.config.md#zenml.config.step_run_info.StepRunInfo)*

Info about the currently running step.

Returns:
: Info about the currently running step.

## zenml.steps.step_invocation module

Step invocation class definition.

### *class* zenml.steps.step_invocation.StepInvocation(id: str, step: [BaseStep](#zenml.steps.base_step.BaseStep), input_artifacts: Dict[str, [StepArtifact](#zenml.steps.entrypoint_function_utils.StepArtifact)], external_artifacts: Dict[str, [ExternalArtifact](zenml.md#zenml.ExternalArtifact)], model_artifacts_or_metadata: Dict[str, [ModelVersionDataLazyLoader](zenml.model.md#zenml.model.lazy_load.ModelVersionDataLazyLoader)], client_lazy_loaders: Dict[str, [ClientLazyLoader](zenml.md#zenml.client_lazy_loader.ClientLazyLoader)], parameters: Dict[str, Any], default_parameters: Dict[str, Any], upstream_steps: Set[str], pipeline: [Pipeline](zenml.new.pipelines.md#zenml.new.pipelines.pipeline.Pipeline))

Bases: `object`

Step invocation class.

#### finalize(parameters_to_ignore: Set[str]) → [StepConfiguration](zenml.config.md#zenml.config.step_configurations.StepConfiguration)

Finalizes a step invocation.

It will validate the upstream steps and run final configurations on the
step that is represented by the invocation.

Args:
: parameters_to_ignore: Set of parameters that should not be applied
  : to the step instance.

Returns:
: The finalized step configuration.

#### *property* upstream_steps *: Set[str]*

The upstream steps of the invocation.

Returns:
: The upstream steps of the invocation.

## zenml.steps.step_output module

Step output class.

### *class* zenml.steps.step_output.Output(\*\*kwargs: Type[Any])

Bases: `object`

A named tuple with a default name that cannot be overridden.

#### items() → Iterator[Tuple[str, Type[Any]]]

Yields a tuple of type (output_name, output_type).

Yields:
: A tuple of type (output_name, output_type).

## zenml.steps.utils module

Utility functions and classes to run ZenML steps.

### *class* zenml.steps.utils.OnlyNoneReturnsVisitor

Bases: [`ReturnVisitor`](#zenml.steps.utils.ReturnVisitor)

Checks whether a function AST contains only None returns.

#### visit_Return(node: Return) → None

Visit a return statement.

Args:
: node: The return statement to visit.

### *class* zenml.steps.utils.OutputSignature(\*, resolved_annotation: Any = None, artifact_config: [ArtifactConfig](zenml.artifacts.md#zenml.artifacts.artifact_config.ArtifactConfig) | None = None, has_custom_name: bool = False)

Bases: `BaseModel`

The signature of an output artifact.

#### artifact_config *: [ArtifactConfig](zenml.artifacts.md#zenml.artifacts.artifact_config.ArtifactConfig) | None*

#### get_output_types() → Tuple[Any, ...]

Get all output types that match the type annotation.

Returns:
: All output types that match the type annotation.

#### has_custom_name *: bool*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'artifact_config': FieldInfo(annotation=Union[ArtifactConfig, NoneType], required=False, default=None), 'has_custom_name': FieldInfo(annotation=bool, required=False, default=False), 'resolved_annotation': FieldInfo(annotation=Any, required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### resolved_annotation *: Any*

### *class* zenml.steps.utils.ReturnVisitor(ignore_nested_functions: bool = True)

Bases: `NodeVisitor`

AST visitor class that can be subclassed to visit function returns.

#### visit_AsyncFunctionDef(node: FunctionDef | AsyncFunctionDef) → None

Visit a (async) function definition node.

Args:
: node: The node to visit.

#### visit_FunctionDef(node: FunctionDef | AsyncFunctionDef) → None

Visit a (async) function definition node.

Args:
: node: The node to visit.

### *class* zenml.steps.utils.TupleReturnVisitor

Bases: [`ReturnVisitor`](#zenml.steps.utils.ReturnVisitor)

Checks whether a function AST contains tuple returns.

#### visit_Return(node: Return) → None

Visit a return statement.

Args:
: node: The return statement to visit.

### zenml.steps.utils.get_args(obj: Any) → Tuple[Any, ...]

Get arguments of a type annotation.

Example:
: get_args(Union[int, str]) == (int, str)

Args:
: obj: The annotation.

Returns:
: The args of the annotation.

### zenml.steps.utils.get_artifact_config_from_annotation_metadata(annotation: Any) → [ArtifactConfig](zenml.artifacts.md#zenml.artifacts.artifact_config.ArtifactConfig) | None

Get the artifact config from the annotation metadata of a step output.

Example:
``python
get_output_name_from_annotation_metadata(int)  # None
get_output_name_from_annotation_metadata(Annotated[int, "name"]  # ArtifactConfig(name="name")
get_output_name_from_annotation_metadata(Annotated[int, ArtifactConfig(name="name", model_name="foo")]  # ArtifactConfig(name="name", model_name="foo")
``

Args:
: annotation: The type annotation.

Raises:
: ValueError: If the annotation is not following the expected format
  : or if the name was specified multiple times or is an empty string.

Returns:
: The artifact config.

### zenml.steps.utils.has_only_none_returns(func: Callable[[...], Any]) → bool

Checks whether a function contains only None returns.

A None return could be either an explicit return None or an empty
return statement.

Example:

```
``
```

```
`
```

python
def f1():

> return None

def f2():
: return

def f3(condition):
: if condition:
  : return None
  <br/>
  else:
  : return 1

has_only_none_returns(f1)  # True
has_only_none_returns(f2)  # True
has_only_none_returns(f3)  # False

```
``
```

```
`
```

Args:
: func: The function to check.

Returns:
: Whether the function contains only None returns.

### zenml.steps.utils.has_tuple_return(func: Callable[[...], Any]) → bool

Checks whether a function returns multiple values.

Multiple values means that the return statement is followed by a tuple
(with or without brackets).

Example:

```
``
```

```
`
```

python
def f1():

> return 1, 2

def f2():
: return (1, 2)

def f3():
: var = (1, 2)
  return var

has_tuple_return(f1)  # True
has_tuple_return(f2)  # True
has_tuple_return(f3)  # False

```
``
```

```
`
```

Args:
: func: The function to check.

Returns:
: Whether the function returns multiple values.

### zenml.steps.utils.log_step_metadata(metadata: Dict[str, str | int | float | bool | Dict[Any, Any] | List[Any] | Set[Any] | Tuple[Any, ...] | [Uri](zenml.metadata.md#zenml.metadata.metadata_types.Uri) | [Path](zenml.metadata.md#zenml.metadata.metadata_types.Path) | [DType](zenml.metadata.md#zenml.metadata.metadata_types.DType) | [StorageSize](zenml.metadata.md#zenml.metadata.metadata_types.StorageSize)], step_name: str | None = None, pipeline_name_id_or_prefix: UUID | str | None = None, run_id: str | None = None) → None

Logs step metadata.

Args:
: metadata: The metadata to log.
  step_name: The name of the step to log metadata for. Can be omitted
  <br/>
  > when being called inside a step.
  <br/>
  pipeline_name_id_or_prefix: The name of the pipeline to log metadata
  : for. Can be omitted when being called inside a step.
  <br/>
  run_id: The ID of the run to log metadata for. Can be omitted when
  : being called inside a step.

Raises:
: ValueError: If no step name is provided and the function is not called
  : from within a step or if no pipeline name or ID is provided and
    the function is not called from within a step.

### zenml.steps.utils.parse_return_type_annotations(func: Callable[[...], Any], enforce_type_annotations: bool = False) → Dict[str, [OutputSignature](#zenml.steps.utils.OutputSignature)]

Parse the return type annotation of a step function.

Args:
: func: The step function.
  enforce_type_annotations: If True, raises an exception if a type
  <br/>
  > annotation is missing.

Raises:
: RuntimeError: If the output annotation has variable length or contains
  : duplicate output names.
  <br/>
  RuntimeError: If type annotations should be enforced and a type
  : annotation is missing.

Returns:
: - A dictionary mapping output names to their output signatures.

### zenml.steps.utils.resolve_type_annotation(obj: Any) → Any

Returns the non-generic class for generic aliases of the typing module.

Example: if the input object is typing.Dict, this method will return the
concrete class dict.

Args:
: obj: The object to resolve.

Returns:
: The non-generic class for generic aliases of the typing module.

### zenml.steps.utils.run_as_single_step_pipeline(\_\_step: [BaseStep](#zenml.steps.base_step.BaseStep), \*args: Any, \*\*kwargs: Any) → Any

Runs the step as a single step pipeline.

- All inputs that are not JSON serializable will be uploaded to the

artifact store before the pipeline is being executed.
- All output artifacts of the step will be loaded using the materializer
that was used to store them.

Args:
: ```
  *
  ```
  <br/>
  args: Entrypoint function arguments.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Entrypoint function keyword arguments.

Raises:
: RuntimeError: If the step execution failed.
  StepInterfaceError: If the arguments to the entrypoint function are
  <br/>
  > invalid.

Returns:
: The output of the step entrypoint function.

## Module contents

Initializer for ZenML steps.

A step is a single piece or stage of a ZenML pipeline. Think of each step as
being one of the nodes of a Directed Acyclic Graph (or DAG). Steps are
responsible for one aspect of processing or interacting with the data /
artifacts in the pipeline.

Conceptually, a Step is a discrete and independent part of a pipeline that is
responsible for one particular aspect of data manipulation inside a ZenML
pipeline.

Steps can be subclassed from the BaseStep class, or used via our @step
decorator.

### *class* zenml.steps.BaseParameters

Bases: `BaseModel`

Base class to pass parameters into a step.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.steps.BaseStep(\*args: Any, name: str | None = None, enable_cache: bool | None = None, enable_artifact_metadata: bool | None = None, enable_artifact_visualization: bool | None = None, enable_step_logs: bool | None = None, experiment_tracker: str | None = None, step_operator: str | None = None, parameters: ParametersOrDict | None = None, output_materializers: OutputMaterializersSpecification | None = None, settings: Mapping[str, SettingsOrDict] | None = None, extra: Dict[str, Any] | None = None, on_failure: HookSpecification | None = None, on_success: HookSpecification | None = None, model: [Model](zenml.md#zenml.Model) | None = None, retry: [StepRetryConfig](zenml.config.md#zenml.config.retry_config.StepRetryConfig) | None = None, \*\*kwargs: Any)

Bases: `object`

Abstract base class for all ZenML steps.

#### after(step: [BaseStep](#zenml.steps.base_step.BaseStep)) → None

Adds an upstream step to this step.

Calling this method makes sure this step only starts running once the
given step has successfully finished executing.

**Note**: This can only be called inside the pipeline connect function
which is decorated with the @pipeline decorator. Any calls outside
this function will be ignored.

Example:
The following pipeline will run its steps sequentially in the following
order: step_2 -> step_1 -> step_3

```
``
```

```
`
```

python
@pipeline
def example_pipeline(step_1, step_2, step_3):

> step_1.after(step_2)
> step_3(step_1(), step_2())

```
``
```

```
`
```

Args:
: step: A step which should finish executing before this step is
  : started.

#### *property* caching_parameters *: Dict[str, Any]*

Caching parameters for this step.

Returns:
: A dictionary containing the caching parameters

#### call_entrypoint(\*args: Any, \*\*kwargs: Any) → Any

Calls the entrypoint function of the step.

Args:
: ```
  *
  ```
  <br/>
  args: Entrypoint function arguments.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Entrypoint function keyword arguments.

Returns:
: The return value of the entrypoint function.

Raises:
: StepInterfaceError: If the arguments to the entrypoint function are
  : invalid.

#### *property* configuration *: [PartialStepConfiguration](zenml.config.md#zenml.config.step_configurations.PartialStepConfiguration)*

The configuration of the step.

Returns:
: The configuration of the step.

#### configure(name: str | None = None, enable_cache: bool | None = None, enable_artifact_metadata: bool | None = None, enable_artifact_visualization: bool | None = None, enable_step_logs: bool | None = None, experiment_tracker: str | None = None, step_operator: str | None = None, parameters: ParametersOrDict | None = None, output_materializers: OutputMaterializersSpecification | None = None, settings: Mapping[str, SettingsOrDict] | None = None, extra: Dict[str, Any] | None = None, on_failure: HookSpecification | None = None, on_success: HookSpecification | None = None, model: [Model](zenml.md#zenml.Model) | None = None, merge: bool = True, retry: [StepRetryConfig](zenml.config.md#zenml.config.retry_config.StepRetryConfig) | None = None) → T

Configures the step.

Configuration merging example:
\* merge==True:

> step.configure(extra={“key1”: 1})
> step.configure(extra={“key2”: 2}, merge=True)
> step.configuration.extra # {“key1”: 1, “key2”: 2}
* merge==False:
  : step.configure(extra={“key1”: 1})
    step.configure(extra={“key2”: 2}, merge=False)
    step.configuration.extra # {“key2”: 2}

Args:
: name: DEPRECATED: The name of the step.
  enable_cache: If caching should be enabled for this step.
  enable_artifact_metadata: If artifact metadata should be enabled
  <br/>
  > for this step.
  <br/>
  enable_artifact_visualization: If artifact visualization should be
  : enabled for this step.
  <br/>
  enable_step_logs: If step logs should be enabled for this step.
  experiment_tracker: The experiment tracker to use for this step.
  step_operator: The step operator to use for this step.
  parameters: Function parameters for this step
  output_materializers: Output materializers for this step. If
  <br/>
  > given as a dict, the keys must be a subset of the output names
  > of this step. If a single value (type or string) is given, the
  > materializer will be used for all outputs.
  <br/>
  settings: settings for this step.
  extra: Extra configurations for this step.
  on_failure: Callback function in event of failure of the step. Can
  <br/>
  > be a function with a single argument of type BaseException, or
  > a source path to such a function (e.g. module.my_function).
  <br/>
  on_success: Callback function in event of success of the step. Can
  : be a function with no arguments, or a source path to such a
    function (e.g. module.my_function).
  <br/>
  model: configuration of the model version in the Model Control Plane.
  merge: If True, will merge the given dictionary configurations
  <br/>
  > like parameters and settings with existing
  > configurations. If False the given configurations will
  > overwrite all existing ones. See the general description of this
  > method for an example.
  <br/>
  retry: Configuration for retrying the step in case of failure.

Returns:
: The step instance that this method was called on.

#### copy() → [BaseStep](#zenml.steps.base_step.BaseStep)

Copies the step.

Returns:
: The step copy.

#### *property* docstring *: str | None*

The docstring of this step.

Returns:
: The docstring of this step.

#### *property* enable_cache *: bool | None*

If caching is enabled for the step.

Returns:
: If caching is enabled for the step.

#### *abstract* entrypoint(\*args: Any, \*\*kwargs: Any) → Any

Abstract method for core step logic.

Args:
: ```
  *
  ```
  <br/>
  args: Positional arguments passed to the step.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments passed to the step.

Returns:
: The output of the step.

#### *classmethod* load_from_source(source: [Source](zenml.config.md#zenml.config.source.Source) | str) → [BaseStep](#zenml.steps.base_step.BaseStep)

Loads a step from source.

Args:
: source: The path to the step source.

Returns:
: The loaded step.

Raises:
: ValueError: If the source is not a valid step source.

#### *property* name *: str*

The name of the step.

Returns:
: The name of the step.

#### resolve() → [Source](zenml.config.md#zenml.config.source.Source)

Resolves the step.

Returns:
: The step source.

#### *property* source_code *: str*

The source code of this step.

Returns:
: The source code of this step.

#### *property* source_object *: Any*

The source object of this step.

Returns:
: The source object of this step.

#### *property* upstream_steps *: Set[[BaseStep](#zenml.steps.base_step.BaseStep)]*

Names of the upstream steps of this step.

This property will only contain the full set of upstream steps once
it’s parent pipeline connect(…) method was called.

Returns:
: Set of upstream step names.

#### with_options(enable_cache: bool | None = None, enable_artifact_metadata: bool | None = None, enable_artifact_visualization: bool | None = None, enable_step_logs: bool | None = None, experiment_tracker: str | None = None, step_operator: str | None = None, parameters: ParametersOrDict | None = None, output_materializers: OutputMaterializersSpecification | None = None, settings: Mapping[str, SettingsOrDict] | None = None, extra: Dict[str, Any] | None = None, on_failure: HookSpecification | None = None, on_success: HookSpecification | None = None, model: [Model](zenml.md#zenml.Model) | None = None, merge: bool = True) → [BaseStep](#zenml.steps.BaseStep)

Copies the step and applies the given configurations.

Args:
: enable_cache: If caching should be enabled for this step.
  enable_artifact_metadata: If artifact metadata should be enabled
  <br/>
  > for this step.
  <br/>
  enable_artifact_visualization: If artifact visualization should be
  : enabled for this step.
  <br/>
  enable_step_logs: If step logs should be enabled for this step.
  experiment_tracker: The experiment tracker to use for this step.
  step_operator: The step operator to use for this step.
  parameters: Function parameters for this step
  output_materializers: Output materializers for this step. If
  <br/>
  > given as a dict, the keys must be a subset of the output names
  > of this step. If a single value (type or string) is given, the
  > materializer will be used for all outputs.
  <br/>
  settings: settings for this step.
  extra: Extra configurations for this step.
  on_failure: Callback function in event of failure of the step. Can
  <br/>
  > be a function with a single argument of type BaseException, or
  > a source path to such a function (e.g. module.my_function).
  <br/>
  on_success: Callback function in event of success of the step. Can
  : be a function with no arguments, or a source path to such a
    function (e.g. module.my_function).
  <br/>
  model: configuration of the model version in the Model Control Plane.
  merge: If True, will merge the given dictionary configurations
  <br/>
  > like parameters and settings with existing
  > configurations. If False the given configurations will
  > overwrite all existing ones. See the general description of this
  > method for an example.

Returns:
: The copied step instance.

### *class* zenml.steps.Output(\*\*kwargs: Type[Any])

Bases: `object`

A named tuple with a default name that cannot be overridden.

#### items() → Iterator[Tuple[str, Type[Any]]]

Yields a tuple of type (output_name, output_type).

Yields:
: A tuple of type (output_name, output_type).

### *class* zenml.steps.ResourceSettings(warn_about_plain_text_secrets: bool = False, \*, cpu_count: Annotated[float, Gt(gt=0)] | None = None, gpu_count: Annotated[int, Ge(ge=0)] | None = None, memory: Annotated[str | None, \_PydanticGeneralMetadata(pattern='^[0-9]+(KB|KiB|MB|MiB|GB|GiB|TB|TiB|PB|PiB)$')] = None)

Bases: [`BaseSettings`](zenml.config.md#zenml.config.base_settings.BaseSettings)

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

#### get_memory(unit: str | [ByteUnit](zenml.config.md#zenml.config.resource_settings.ByteUnit) = ByteUnit.GB) → float | None

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

### *class* zenml.steps.StepContext(\*args: Any, \*\*kwargs: Any)

Bases: `object`

Provides additional context inside a step function.

This singleton class is used to access information about the current run,
step run, or its outputs inside a step function.

Usage example:

```
``
```

```
`
```

python
from zenml.steps import get_step_context

@step
def my_trainer_step() -> Any:

> context = get_step_context()

> # get info about the current pipeline run
> current_pipeline_run = context.pipeline_run

> # get info about the current step run
> current_step_run = context.step_run

> # get info about the future output artifacts of this step
> output_artifact_uri = context.get_output_artifact_uri()

> …

```
``
```

```
`
```

#### add_output_metadata(metadata: Dict[str, MetadataType], output_name: str | None = None) → None

Adds metadata for a given step output.

Args:
: metadata: The metadata to add.
  output_name: Optional name of the output for which to add the
  <br/>
  > metadata. If no name is given and the step only has a single
  > output, the metadata of this output will be added. If the
  > step has multiple outputs, an exception will be raised.

#### add_output_tags(tags: List[str], output_name: str | None = None) → None

Adds tags for a given step output.

Args:
: tags: The tags to add.
  output_name: Optional name of the output for which to add the
  <br/>
  > tags. If no name is given and the step only has a single
  > output, the tags of this output will be added. If the
  > step has multiple outputs, an exception will be raised.

#### get_output_artifact_uri(output_name: str | None = None) → str

Returns the artifact URI for a given step output.

Args:
: output_name: Optional name of the output for which to get the URI.
  : If no name is given and the step only has a single output,
    the URI of this output will be returned. If the step has
    multiple outputs, an exception will be raised.

Returns:
: Artifact URI for the given output.

#### get_output_materializer(output_name: str | None = None, custom_materializer_class: Type[[BaseMaterializer](zenml.materializers.md#zenml.materializers.base_materializer.BaseMaterializer)] | None = None, data_type: Type[Any] | None = None) → [BaseMaterializer](zenml.materializers.md#zenml.materializers.base_materializer.BaseMaterializer)

Returns a materializer for a given step output.

Args:
: output_name: Optional name of the output for which to get the
  : materializer. If no name is given and the step only has a
    single output, the materializer of this output will be
    returned. If the step has multiple outputs, an exception
    will be raised.
  <br/>
  custom_materializer_class: If given, this BaseMaterializer
  : subclass will be initialized with the output artifact instead
    of the materializer that was registered for this step output.
  <br/>
  data_type: If the output annotation is of type Union and the step
  : therefore has multiple materializers configured, you can provide
    a data type for the output which will be used to select the
    correct materializer. If not provided, the first materializer
    will be used.

Returns:
: A materializer initialized with the output artifact for
  the given output.

#### get_output_metadata(output_name: str | None = None) → Dict[str, MetadataType]

Returns the metadata for a given step output.

Args:
: output_name: Optional name of the output for which to get the
  : metadata. If no name is given and the step only has a single
    output, the metadata of this output will be returned. If the
    step has multiple outputs, an exception will be raised.

Returns:
: Metadata for the given output.

#### get_output_tags(output_name: str | None = None) → List[str]

Returns the tags for a given step output.

Args:
: output_name: Optional name of the output for which to get the
  : metadata. If no name is given and the step only has a single
    output, the metadata of this output will be returned. If the
    step has multiple outputs, an exception will be raised.

Returns:
: Tags for the given output.

#### *property* inputs *: Dict[str, [ArtifactVersionResponse](zenml.models.md#zenml.models.ArtifactVersionResponse)]*

Returns the input artifacts of the current step.

Returns:
: The input artifacts of the current step.

#### *property* model *: [Model](zenml.md#zenml.Model)*

Returns configured Model.

Order of resolution to search for Model is:
: 1. Model from @step
  2. Model from @pipeline

Returns:
: The Model object associated with the current step.

Raises:
: StepContextError: If the Model object is not set in @step or @pipeline.

#### *property* model_version *: [Model](zenml.md#zenml.Model)*

DEPRECATED, use model instead.

Returns:
: The Model object associated with the current step.

#### *property* pipeline *: [PipelineResponse](zenml.models.md#zenml.models.PipelineResponse)*

Returns the current pipeline.

Returns:
: The current pipeline or None.

Raises:
: StepContextError: If the pipeline run does not have a pipeline.

### *class* zenml.steps.StepEnvironment(step_run_info: [StepRunInfo](zenml.config.md#zenml.config.step_run_info.StepRunInfo), cache_enabled: bool)

Bases: [`BaseEnvironmentComponent`](zenml.md#zenml.environment.BaseEnvironmentComponent)

(Deprecated) Added information about a run inside a step function.

This takes the form of an Environment component. This class can be used from
within a pipeline step implementation to access additional information about
the runtime parameters of a pipeline step, such as the pipeline name,
pipeline run ID and other pipeline runtime information. To use it, access it
inside your step function like this:

```
``
```

```
`
```

python
from zenml.environment import Environment

@step
def my_step(…)

> env = Environment().step_environment
> do_something_with(env.pipeline_name, env.run_name, env.step_name)

```
``
```

```
`
```

#### NAME *: str* *= 'step_environment'*

#### *property* cache_enabled *: bool*

Returns whether cache is enabled for the step.

Returns:
: True if cache is enabled for the step, otherwise False.

#### *property* pipeline_name *: str*

The name of the currently running pipeline.

Returns:
: The name of the currently running pipeline.

#### *property* run_name *: str*

The name of the current pipeline run.

Returns:
: The name of the current pipeline run.

#### *property* step_name *: str*

The name of the currently running step.

Returns:
: The name of the currently running step.

#### *property* step_run_info *: [StepRunInfo](zenml.config.md#zenml.config.step_run_info.StepRunInfo)*

Info about the currently running step.

Returns:
: Info about the currently running step.

### zenml.steps.step(\_func: F | None = None, \*, name: str | None = None, enable_cache: bool | None = None, enable_artifact_metadata: bool | None = None, enable_artifact_visualization: bool | None = None, enable_step_logs: bool | None = None, experiment_tracker: str | None = None, step_operator: str | None = None, output_materializers: OutputMaterializersSpecification | None = None, settings: Dict[str, SettingsOrDict] | None = None, extra: Dict[str, Any] | None = None, on_failure: HookSpecification | None = None, on_success: HookSpecification | None = None, model: [Model](zenml.md#zenml.Model) | None = None) → Type[[BaseStep](#zenml.steps.base_step.BaseStep)] | Callable[[F], Type[[BaseStep](#zenml.steps.base_step.BaseStep)]]

Outer decorator function for the creation of a ZenML step.

In order to be able to work with parameters such as name, it features a
nested decorator structure.

Args:
: \_func: The decorated function.
  name: The name of the step. If left empty, the name of the decorated
  <br/>
  > function will be used as a fallback.
  <br/>
  enable_cache: Specify whether caching is enabled for this step. If no
  : value is passed, caching is enabled by default.
  <br/>
  enable_artifact_metadata: Specify whether metadata is enabled for this
  : step. If no value is passed, metadata is enabled by default.
  <br/>
  enable_artifact_visualization: Specify whether visualization is enabled
  : for this step. If no value is passed, visualization is enabled by
    default.
  <br/>
  enable_step_logs: Specify whether step logs are enabled for this step.
  experiment_tracker: The experiment tracker to use for this step.
  step_operator: The step operator to use for this step.
  output_materializers: Output materializers for this step. If
  <br/>
  > given as a dict, the keys must be a subset of the output names
  > of this step. If a single value (type or string) is given, the
  > materializer will be used for all outputs.
  <br/>
  settings: Settings for this step.
  extra: Extra configurations for this step.
  on_failure: Callback function in event of failure of the step. Can be a
  <br/>
  > function with a single argument of type BaseException, or a source
  > path to such a function (e.g. module.my_function).
  <br/>
  on_success: Callback function in event of success of the step. Can be a
  : function with no arguments, or a source path to such a function
    (e.g. module.my_function).
  <br/>
  model: configuration of the model version in the Model Control Plane.

Returns:
: The inner decorator which creates the step class based on the
  ZenML BaseStep
