# What can be configured

### `enable_XXX` parameters

These are boolean flags for various configurations:

* `enable_artifact_metadata`: Whether to [associate metadata with artifacts or not](../handle-data-artifacts/handle-custom-data-types.md#optional-which-metadata-to-extract-for-the-artifact).
* `enable_artifact_visualization`: Whether to [attach visualizations of artifacts](../handle-data-artifacts/visualize-artifacts.md).
* `enable_cache`: Utilize [caching](../overview/control-caching-behavior.md) or not.
* `enable_step_logs`: Enable tracking [step logs](../overview/enable-or-disable-logs-storing.md).

### `build` ID

The UUID of the [`build`](../customize-docker-builds/) to use for this pipeline. If specified, Docker image building is skipped for remote orchestrators, and the Docker image specified in this build is used.

### `extra` dict

This is a dictionary that is available to be passed to steps and pipelines called `extra`. This dictionary is meant to be used to pass any configuration down to the pipeline, step, or stack components that the user has use of. See an example in [this section](what-can-be-configured.md).

### Configuring the `model`

Specifies the ZenML [Model](../../user-guide/starter-guide/track-ml-models.md) to use for this pipeline.

### Pipeline and step `parameters`

A dictionary of JSON-serializable [parameters](./) specified at the pipeline or step level. For example:

```yaml
parameters:
    gamma: 0.01

steps:
    trainer:
        parameters:
            gamma: 0.001
```

Corresponds to:

```python
from zenml import step, pipeline

@step
def trainer(gamma: float):
    # Use gamma as normal
    print(gamma)

@pipeline
def my_pipeline(gamma: float):
    # use gamma or pass it into the step
    print(0.01)
    trainer(gamma=gamma)
```

Important note, in the above case, the value of the step would be the one defined in the `steps` key (i.e. 0.001). So the YAML config always takes precedence over pipeline parameters that are passed down to steps in code. Read [this section for more details](configuration-hierarchy.md).

Normally, parameters defined at the pipeline level are used in multiple steps, and then no step-level configuration is defined.

{% hint style="info" %}
Note that `parameters` are different from `artifacts`. Parameters are JSON-serializable values that are passed in the runtime configuration of a pipeline. Artifacts are inputs and outputs of a step, and need not always be JSON-serializable ([materializers](../handle-data-artifacts/handle-custom-data-types.md) handle their persistence in the [artifact store](../../stacks-and-components/component-guide/artifact-stores/)).
{% endhint %}

### Setting the `run_name`

To change the name for a run, pass `run_name` as a parameter. This can be a dynamic value as well. Read [here for details](../../user-guide/starter-guide/create-an-ml-pipeline.md).

### Real-time `settings`

Settings are special runtime configurations of a pipeline or a step that require a [dedicated section](../../user-guide/advanced-guide/pipelining-features/pipeline-settings.md). In short, they define a bunch of execution configuration such as Docker building and resource settings.

### `failure_hook_source` and `success_hook_source`

The `source` of the [failure and success hooks](../overview/use-failure-success-hooks.md).

### Step-specific configuration

A lot of pipeline-level configuration can also be applied at a step level (as we have already seen with the `enable_cache` flag). However, there is some configuration that is step-specific, meaning it cannot be applied at a pipeline level, but only at a step level.

* `experiment_tracker`: Name of the [experiment\_tracker](../../stacks-and-components/component-guide/experiment-trackers/) to enable for this step. This experiment\_tracker should be defined in the active stack with the same name.
* `step_operator`: Name of the [step\_operator](../../stacks-and-components/component-guide/step-operators/) to enable for this step. This step\_operator should be defined in the active stack with the same name.
* `outputs`: This is configuration of the output artifacts of this step. This is further keyed by output name (by default, step outputs [are named `output`](../handle-data-artifacts/return-multiple-outputs-from-a-step.md)). The most interesting configuration here is the `materializer_source`, which is the UDF path of the materializer in code to use for this output (e.g. `materializers.some_data.materializer.materializer_class`). Read more about this source path [here](../handle-data-artifacts/handle-custom-data-types.md).
