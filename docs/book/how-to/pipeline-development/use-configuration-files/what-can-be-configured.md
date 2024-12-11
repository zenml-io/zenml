# What can be configured

Here is an example of a sample YAML file, with the most important configuration highlighted. For brevity,
we have removed all possible keys. To view a sample file with all possible keys, refer to
[this page](./autogenerate-a-template-yaml-file.md).

```yaml
# Build ID (i.e. which Docker image to use)
build: dcd6fafb-c200-4e85-8328-428bef98d804

# Enable flags (boolean flags that control behavior)
enable_artifact_metadata: True
enable_artifact_visualization: False
enable_cache: False
enable_step_logs: True

# Extra dictionary to pass in arbitrary values
extra: 
  any_param: 1
  another_random_key: "some_string"

# Specify the "ZenML Model"
model:
  name: "classification_model"
  version: production

  audience: "Data scientists"
  description: "This classifies hotdogs and not hotdogs"
  ethics: "No ethical implications"
  license: "Apache 2.0"
  limitations: "Only works for hotdogs"
  tags: ["sklearn", "hotdog", "classification"]

# Parameters of the pipeline 
parameters: 
  dataset_name: "another_dataset"

# Name of the run
run_name: "my_great_run"

# Schedule, if supported on the orchestrator
schedule:
  catchup: true
  cron_expression: "* * * * *"

# Real-time settings for Docker and resources
settings:
  # Controls Docker building
  docker:
    apt_packages: ["curl"]
    copy_files: True
    dockerfile: "Dockerfile"
    dockerignore: ".dockerignore"
    environment:
      ZENML_LOGGING_VERBOSITY: DEBUG
    parent_image: "zenml-io/zenml-cuda"
    requirements: ["torch"]
    skip_build: False
  
  # Control resources for the entire pipeline
  resources:
    cpu_count: 2
    gpu_count: 1
    memory: "4Gb"
  
# Per step configuration
steps:
  # Top-level key should be the name of the step invocation ID
  train_model:
    # Parameters of the step
    parameters:
      data_source: "best_dataset"

    # Step-only configuration
    experiment_tracker: "mlflow_production"
    step_operator: "vertex_gpu"
    outputs: {}
    failure_hook_source: {}
    success_hook_source: {}

    # Same as pipeline level configuration, if specified overrides for this step
    enable_artifact_metadata: True
    enable_artifact_visualization: True
    enable_cache: False
    enable_step_logs: True

    # Same as pipeline level configuration, if specified overrides for this step
    extra: {}

    # Same as pipeline level configuration, if specified overrides for this step
    model: {}
      
    # Same as pipeline level configuration, if specified overrides for this step
    settings:
      docker: {}
      resources: {}

      # Stack component specific settings
      step_operator.sagemaker:
        estimator_args:
          instance_type: m7g.medium
```

## Deep-dive

### `enable_XXX` parameters

These are boolean flags for various configurations:

* `enable_artifact_metadata`: Whether to [associate metadata with artifacts or not](../../data-artifact-management/handle-data-artifacts/handle-custom-data-types.md#optional-which-metadata-to-extract-for-the-artifact).
* `enable_artifact_visualization`: Whether to [attach visualizations of artifacts](../../data-artifact-management/visualize-artifacts/README.md).
* `enable_cache`: Utilize [caching](../build-pipelines/control-caching-behavior.md) or not.
* `enable_step_logs`: Enable tracking [step logs](../../advanced-topics/control-logging/enable-or-disable-logs-storing.md).

```yaml
enable_artifact_metadata: True
enable_artifact_visualization: True
enable_cache: True
enable_step_logs: True
```

### `build` ID

The UUID of the [`build`](../../infrastructure-deployment/customize-docker-builds/README.md) to use for this pipeline. If specified, Docker image building is skipped for remote orchestrators, and the Docker image specified in this build is used.

```yaml
build: <INSERT-BUILD-ID-HERE>
```

### Configuring the `model`

Specifies the ZenML [Model](../../../user-guide/starter-guide/track-ml-models.md) to use for this pipeline.

```yaml
model:
  name: "ModelName"
  version: "production"
  description: An example model
  tags: ["classifier"]
```

### Pipeline and step `parameters`

A dictionary of JSON-serializable [parameters](../../pipeline-development/build-pipelines/use-pipeline-step-parameters.md) specified at the pipeline or step level. For example:

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
Note that `parameters` are different from `artifacts`. Parameters are JSON-serializable values that are passed in the runtime configuration of a pipeline. Artifacts are inputs and outputs of a step, and need not always be JSON-serializable ([materializers](../../data-artifact-management/handle-data-artifacts/handle-custom-data-types.md) handle their persistence in the [artifact store](../../../component-guide/artifact-stores/artifact-stores.md)).
{% endhint %}

### Setting the `run_name`

To change the name for a run, pass `run_name` as a parameter. This can be a dynamic value as well.&#x20;

```python
run_name: <INSERT_RUN_NAME_HERE>  
```

{% hint style="warning" %}
You will not be able to run with the same run\_name twice. Do not set this statically when running on a schedule. Try to include some auto-incrementation or timestamp to the name.
{% endhint %}

### Stack Component Runtime settings

Settings are special runtime configurations of a pipeline or a step that require a [dedicated section](runtime-configuration.md). In short, they define a bunch of execution configuration such as Docker building and resource settings.

### Docker Settings

Docker Settings can be passed in directly as objects, or a dictionary representation of the object. For example, the Docker configuration can be set in configuration files as follows:

```yaml
settings:
  docker:
    requirements:
      - pandas
    
```

{% hint style="info" %}
Find a complete list of all Docker Settings [here](https://sdkdocs.zenml.io/latest/core\_code\_docs/core-config/#zenml.config.docker\_settings.DockerSettings). To learn more about pipeline containerization consult our documentation on this [here](../../infrastructure-deployment/customize-docker-builds/README.md).
{% endhint %}

### Resource Settings

Some stacks allow setting the resource settings using these settings.

```yaml
resources:
  cpu_count: 2
  gpu_count: 1
  memory: "4Gb"
```

Note that this may not work for all types of stack components. To learn which components support this,
please refer to the specific orchestrator docs.

### `failure_hook_source` and `success_hook_source`

The `source` of the [failure and success hooks](../../pipeline-development/build-pipelines/use-failure-success-hooks.md) can be specified.

### Step-specific configuration

A lot of pipeline-level configuration can also be applied at a step level (as we have already seen with the `enable_cache` flag). However, there is some configuration that is step-specific, meaning it cannot be applied at a pipeline level, but only at a step level.

* `experiment_tracker`: Name of the [experiment\_tracker](../../../component-guide/experiment-trackers/experiment-trackers.md) to enable for this step. This experiment\_tracker should be defined in the active stack with the same name.
* `step_operator`: Name of the [step\_operator](../../../component-guide/step-operators/step-operators.md) to enable for this step. This step\_operator should be defined in the active stack with the same name.
* `outputs`: This is configuration of the output artifacts of this step. This is further keyed by output name (by default, step outputs [are named `output`](../../data-artifact-management/handle-data-artifacts/return-multiple-outputs-from-a-step.md)). The most interesting configuration here is the `materializer_source`, which is the UDF path of the materializer in code to use for this output (e.g. `materializers.some_data.materializer.materializer_class`). Read more about this source path [here](../../data-artifact-management/handle-data-artifacts/handle-custom-data-types.md).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
