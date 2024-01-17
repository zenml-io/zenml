---
description: Using settings to configure runtime configuration.
---

# Controlling settings of your pipeline

{% embed url="https://www.youtube.com/embed/AdwW6DlCWFE" %}
Stack Component Config vs Settings in ZenML
{% endembed %}

As we [saw before](configure-steps-pipelines.md#real-time-settings), one special type of configuration is called `Settings`. These allow you to configure runtime configurations for stack components and pipelines. Concretely, they allow you to configure:

* The [resources](../infrastructure-management/scale-compute-to-the-cloud.md#specify-resource-requirements-for-steps) required for a step
* Configuring the [containerization](../infrastructure-management/containerize-your-pipeline.md) process of a pipeline (e.g. What requirements get installed in the Docker image)
* Stack component-specific configuration, e.g., if you have an experiment tracker passing in the name of the experiment at runtime

You will learn about all of the above in more detail later, but for now, let's try to understand that all of this configuration flows through one central concept called `BaseSettings`. (From here on, we use `settings` and `BaseSettings` as analogous in this guide).

## Types of settings

Settings are categorized into two types:

* **General settings** that can be used on all ZenML pipelines. Examples of these are:
  * [`DockerSettings`](../infrastructure-management/containerize-your-pipeline.md) to specify docker settings.
  * [`ResourceSettings`](../infrastructure-management/scale-compute-to-the-cloud.md#specify-resource-requirements-for-steps) to specify resource settings.
* **Stack-component-specific settings**: These can be used to supply runtime configurations to certain stack components (key= \<COMPONENT\_CATEGORY>.\<COMPONENT\_FLAVOR>). Settings for components not in the active stack will be ignored. Examples of these are:
  * [`SkypilotAWSOrchestratorSettings`](../../../stacks-and-components/component-guide/orchestrators/skypilot-vm.md) to specify Skypilot settings (works for `SkypilotGCPOrchestratorSettings` and `SkypilotAzureOrchestratorSettings` as well).
  * [`KubeflowOrchestratorSettings`](../../../stacks-and-components/component-guide/orchestrators/kubeflow.md) to specify Kubeflow settings.
  * [`MLflowExperimentTrackerSettings`](../../../stacks-and-components/component-guide/experiment-trackers/mlflow.md) to specify MLflow settings.
  * [`WandbExperimentTrackerSettings`](../../../stacks-and-components/component-guide/experiment-trackers/wandb.md) to specify W\&B settings.
  * [`WhylogsDataValidatorSettings`](../../../stacks-and-components/component-guide/data-validators/whylogs.md) to specify Whylogs settings.
  * [`SagemakerStepOperatorSettings`](../../../stacks-and-components/component-guide/step-operators/sagemaker.md) to specify AWS Sagemaker step operator settings.
  * [`VertexStepOperatorSettings`](../../../stacks-and-components/component-guide/step-operators/vertex.md) to specify GCP Vertex step operator settings.
  * [`AzureMLStepOeratorSettings`](../../../stacks-and-components/component-guide/step-operators/azureml.md) to specify AzureML step operator settings.

### Difference between stack component settings at registration-time vs real-time

For stack-component-specific settings, you might be wondering what the difference is between these and the configuration passed in while doing `zenml stack-component register <NAME> --config1=configvalue --config2=configvalue`, etc. The answer is that the configuration passed in at registration time is static and fixed throughout all pipeline runs, while the settings can change.

A good example of this is the [`MLflow Experiment Tracker`](../../../stacks-and-components/component-guide/experiment-trackers/mlflow.md), where configuration which remains static such as the `tracking_url` is sent through at registration time, while runtime configuration such as the `experiment_name` (which might change every pipeline run) is sent through as runtime settings.

Even though settings can be overridden at runtime, you can also specify _default_ values for settings while configuring a stack component. For example, you could set a default value for the `nested` setting of your MLflow experiment tracker: `zenml experiment-tracker register <NAME> --flavor=mlflow --nested=True`

This means that all pipelines that run using this experiment tracker use nested MLflow runs unless overridden by specifying settings for the pipeline at runtime.

### Using objects or dicts

Settings can be passed in directly as `BaseSettings`-subclassed objects, or a dictionary representation of the object. For example, a Docker configuration can be passed in as follows:

```python
from zenml.config import DockerSettings

settings = {'docker': DockerSettings(requirements=['pandas'])}
```

Or like this:

```python
settings = {'docker': {'requirements': ['pandas']}}
```

Or in a YAML like this:

```yaml
settings:
  docker:
    requirements:
      - pandas
```

### Using the right key for Stack-component-specific settings

When specifying stack-component-specific settings, a key needs to be passed. This key should always correspond to the pattern: \<COMPONENT\_CATEGORY>.\<COMPONENT\_FLAVOR>

For example, the [SagemakerStepOperator](../../../stacks-and-components/component-guide/step-operators/sagemaker.md) supports passing in [`estimator_args`](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-aws/#zenml.integrations.aws.flavors.sagemaker_step_operator_flavor.SagemakerStepOperatorSettings). The way to specify this would be to use the key `step_operator.sagemaker`

```python
@step(step_operator="nameofstepoperator", settings= {"step_operator.sagemaker": {"estimator_args": {"instance_type": "m7g.medium"}}})
def my_step():
  ...

# Using the class
@step(step_operator="nameofstepoperator", settings= {"step_operator.sagemaker": SagemakerStepOperatorSettings(instance_type="m7g.medium")})
def my_step():
  ...
```

or in YAML:

```yaml
steps:
  my_step:
    step_operator: "nameofstepoperator"
    settings:
      step_operator.sagemaker:
        estimator_args:
          instance_type: m7g.medium
```

## Utilizing the settings

Settings can be configured in the same way as any [other configuration](configure-steps-pipelines.md). For example, users have the option to send all configurations in via a YAML file. This is useful in situations where code changes are not desirable.

To use a YAML file, you must pass it to the `with_options(...)` method of a pipeline:

```python
@step
def my_step() -> None:
    print("my step")


@pipeline
def my_pipeline():
    my_step()


# Pass in a config file
my_pipeline = my_pipeline.with_options(config_path='/local/path/to/config.yaml')
```

The format of a YAML config file is exactly the same as the configurations you would pass in Python in the above two sections. Step-specific configurations can be passed by using the [step invocation ID](configure-steps-pipelines.md#using-a-custom-step-invocation-id) inside the `steps` dictionary. Here is a rough skeleton of a valid YAML config. All keys are optional.

```yaml
# Pipeline level settings
settings: 
  docker:
    build_context_root: .
    build_options: Mapping[str, Any]
    source_files: str
    copy_global_config: bool
    dockerfile: Optional[str]
    dockerignore: Optional[str]
    environment: Mapping[str, Any]
    install_stack_requirements: bool
    parent_image: Optional[str]
    replicate_local_python_environment: Optional
    required_integrations: List[str]
    requirements:
      - pandas
  resources:
    cpu_count: 1
    gpu_count: 1
    memory: "1GB"
    
steps:
  step_invocation_id:
    settings: { }  # overrides pipeline settings
  other_step_invocation_id:
    settings: { }
  ...
```

## Hierarchy and precedence

Some settings can be configured on pipelines and steps, some only on one of the two. Pipeline-level settings will be automatically applied to all steps, but if the same setting is configured on a step as well that takes precedence.

When a settings object is configured, ZenML merges the values with previously configured keys. E.g.:

```python
from zenml.config import ResourceSettings


@step(settings={"resources": ResourceSettings(cpu_count=2, memory="1GB")})
def my_step() -> None:
    ...


my_step.configure(
    settings={"resources": ResourceSettings(gpu_count=1, memory="2GB")}
)

my_step.configuration.settings["resources"]
# cpu_count: 2, gpu_count=1, memory="2GB"
```

In the above example, the two settings were automatically merged.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
