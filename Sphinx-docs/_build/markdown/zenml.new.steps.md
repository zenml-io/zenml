# zenml.new.steps package

## Submodules

## zenml.new.steps.decorated_step module

Internal BaseStep subclass used by the step decorator.

## zenml.new.steps.step_context module

Step context class.

### *class* zenml.new.steps.step_context.StepContext(\*args: Any, \*\*kwargs: Any)

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

### *class* zenml.new.steps.step_context.StepContextOutput(materializer_classes: Sequence[Type[[BaseMaterializer](zenml.materializers.md#zenml.materializers.base_materializer.BaseMaterializer)]], artifact_uri: str, artifact_config: [ArtifactConfig](zenml.md#zenml.ArtifactConfig) | None)

Bases: `object`

Represents a step output in the step context.

#### artifact_config *: [ArtifactConfig](zenml.md#zenml.ArtifactConfig) | None*

#### artifact_uri *: str*

#### materializer_classes *: Sequence[Type[[BaseMaterializer](zenml.materializers.md#zenml.materializers.base_materializer.BaseMaterializer)]]*

#### run_metadata *: Dict[str, MetadataType] | None* *= None*

#### tags *: List[str] | None* *= None*

### zenml.new.steps.step_context.get_step_context() → [StepContext](#zenml.new.steps.step_context.StepContext)

Get the context of the currently running step.

Returns:
: The context of the currently running step.

Raises:
: RuntimeError: If no step is currently running.

## zenml.new.steps.step_decorator module

Step decorator function.

### zenml.new.steps.step_decorator.step(\_func: F) → [BaseStep](zenml.steps.md#zenml.steps.base_step.BaseStep)

### zenml.new.steps.step_decorator.step(\*, name: str | None = None, enable_cache: bool | None = None, enable_artifact_metadata: bool | None = None, enable_artifact_visualization: bool | None = None, enable_step_logs: bool | None = None, experiment_tracker: str | None = None, step_operator: str | None = None, output_materializers: 'OutputMaterializersSpecification' | None = None, settings: Dict[str, 'SettingsOrDict'] | None = None, extra: Dict[str, Any] | None = None, on_failure: 'HookSpecification' | None = None, on_success: 'HookSpecification' | None = None, model: 'Model' | None = None, retry: 'StepRetryConfig' | None = None, model_version: 'Model' | None = None) → Callable[['F'], 'BaseStep']

Decorator to create a ZenML step.

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
  model: configuration of the model in the Model Control Plane.
  retry: configuration of step retry in case of step failure.
  model_version: DEPRECATED, please use model instead.

Returns:
: The step instance.

## Module contents
