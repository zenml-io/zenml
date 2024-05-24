---
description: Using settings to configure runtime configuration.
---

# 🍜 Runtime configuration

{% embed url="https://www.youtube.com/embed/AdwW6DlCWFE" %}
Stack Component Config vs Settings in ZenML
{% endembed %}

As we [saw before](https://github.com/zenml-io/zenml/blob/feature/gro-1047-docs/docs/book/user-guide/advanced-guide/pipelining-features/broken-reference/README.md), one special type of configuration is called `Settings`. These allow you to configure runtime configurations for stack components and pipelines. Concretely, they allow you to configure:

* The [resources](../overview/scale-compute-to-the-cloud.md#specify-resource-requirements-for-steps) required for a step
* Configuring the [containerization](../customize-docker-builds/) process of a pipeline (e.g. What requirements get installed in the Docker image)
* Stack component-specific configuration, e.g., if you have an experiment tracker passing in the name of the experiment at runtime

You will learn about all of the above in more detail later, but for now, let's try to understand that all of this configuration flows through one central concept called `BaseSettings`. (From here on, we use `settings` and `BaseSettings` as analogous in this guide).

## Types of settings

Settings are categorized into two types:

* **General settings** that can be used on all ZenML pipelines. Examples of these are:
  * [`DockerSettings`](../customize-docker-builds/) to specify docker settings.
  * [`ResourceSettings`](../overview/scale-compute-to-the-cloud.md#specify-resource-requirements-for-steps) to specify resource settings.
* **Stack-component-specific settings**: These can be used to supply runtime configurations to certain stack components (key= \<COMPONENT\_CATEGORY>.\<COMPONENT\_FLAVOR>). Settings for components not in the active stack will be ignored. Examples of these are:
  * [`SkypilotAWSOrchestratorSettings`](https://github.com/zenml-io/zenml/blob/feature/gro-1047-docs/docs/book/stacks-and-components/component-guide/orchestrators/skypilot-vm.md) to specify Skypilot settings (works for `SkypilotGCPOrchestratorSettings` and `SkypilotAzureOrchestratorSettings` as well).
  * [`KubeflowOrchestratorSettings`](https://github.com/zenml-io/zenml/blob/feature/gro-1047-docs/docs/book/stacks-and-components/component-guide/orchestrators/kubeflow.md) to specify Kubeflow settings.
  * [`MLflowExperimentTrackerSettings`](https://github.com/zenml-io/zenml/blob/feature/gro-1047-docs/docs/book/stacks-and-components/component-guide/experiment-trackers/mlflow.md) to specify MLflow settings.
  * [`WandbExperimentTrackerSettings`](https://github.com/zenml-io/zenml/blob/feature/gro-1047-docs/docs/book/stacks-and-components/component-guide/experiment-trackers/wandb.md) to specify W\&B settings.
  * [`WhylogsDataValidatorSettings`](https://github.com/zenml-io/zenml/blob/feature/gro-1047-docs/docs/book/how-to/configure-stack-components/data-validators/whylogs.md) to specify Whylogs settings.
  * [`SagemakerStepOperatorSettings`](https://github.com/zenml-io/zenml/blob/feature/gro-1047-docs/docs/book/stacks-and-components/component-guide/step-operators/sagemaker.md) to specify AWS Sagemaker step operator settings.
  * [`VertexStepOperatorSettings`](https://github.com/zenml-io/zenml/blob/feature/gro-1047-docs/docs/book/stacks-and-components/component-guide/step-operators/vertex.md) to specify GCP Vertex step operator settings.
  * [`AzureMLStepOeratorSettings`](https://github.com/zenml-io/zenml/blob/feature/gro-1047-docs/docs/book/stacks-and-components/component-guide/step-operators/azureml.md) to specify AzureML step operator settings.

### Difference between stack component settings at registration-time vs real-time

For stack-component-specific settings, you might be wondering what the difference is between these and the configuration passed in while doing `zenml stack-component register <NAME> --config1=configvalue --config2=configvalue`, etc. The answer is that the configuration passed in at registration time is static and fixed throughout all pipeline runs, while the settings can change.

A good example of this is the [`MLflow Experiment Tracker`](https://github.com/zenml-io/zenml/blob/feature/gro-1047-docs/docs/book/stacks-and-components/component-guide/experiment-trackers/mlflow.md), where configuration which remains static such as the `tracking_url` is sent through at registration time, while runtime configuration such as the `experiment_name` (which might change every pipeline run) is sent through as runtime settings.

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

For example, the [SagemakerStepOperator](https://github.com/zenml-io/zenml/blob/feature/gro-1047-docs/docs/book/stacks-and-components/component-guide/step-operators/sagemaker.md) supports passing in [`estimator_args`](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-aws/#zenml.integrations.aws.flavors.sagemaker\_step\_operator\_flavor.SagemakerStepOperatorSettings). The way to specify this would be to use the key `step_operator.sagemaker`

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

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
