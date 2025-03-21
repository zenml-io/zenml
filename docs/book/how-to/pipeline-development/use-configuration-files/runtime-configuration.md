---
description: Using settings to configure runtime configuration.
---

# Stack component specific configuration

{% embed url="https://www.youtube.com/embed/AdwW6DlCWFE" %}
Stack Component Config vs Settings in ZenML
{% endembed %}

Part of the configuration of a pipeline are its `Settings`. These allow you to configure runtime configurations for stack components and pipelines. Concretely, they allow you to configure:

* The [resources](https://docs.zenml.io/how-to/pipeline-development/training-with-gpus/#specify-resource-requirements-for-steps) required for a step
* Configuring the [containerization](https://docs.zenml.io/how-to/customize-docker-builds) process of a pipeline (e.g. What requirements get installed in the Docker image)
* Stack component-specific configuration, e.g., if you have an experiment tracker passing in the name of the experiment at runtime

You will learn about all of the above in more detail later, but for now, let's try to understand that all of this configuration flows through one central concept called `BaseSettings`. (From here on, we use `settings` and `BaseSettings` as analogous in this guide).

## Types of settings

Settings are categorized into two types:

* **General settings** that can be used on all ZenML pipelines. Examples of these are:
  * [`DockerSettings`](https://docs.zenml.io//how-to/customize-docker-builds) to specify Docker settings.
  * [`ResourceSettings`](https://docs.zenml.io//how-to/pipeline-development/training-with-gpus) to specify resource settings.
* **Stack-component-specific settings**: These can be used to supply runtime configurations to certain stack components (the key should be `<COMPONENT_CATEGORY>` or `<COMPONENT_CATEGORY>.<COMPONENT_FLAVOR>`). Settings for components not in the active stack will be ignored. Examples of these are:
  * [`SkypilotAWSOrchestratorSettings`](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-skypilot_aws.html#zenml.integrations.skypilot_aws) to specify Skypilot settings (works for `SkypilotGCPOrchestratorSettings` and `SkypilotAzureOrchestratorSettings` as well).
  * [`KubeflowOrchestratorSettings`](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-kubeflow.html#zenml.integrations.kubeflow) to specify Kubeflow settings.
  * [`MLflowExperimentTrackerSettings`](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-mlflow.html#zenml.integrations.mlflow) to specify MLflow settings.
  * [`WandbExperimentTrackerSettings`](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-wandb.html#zenml.integrations.wandb) to specify W\&B settings.
  * [`WhylogsDataValidatorSettings`](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-whylogs.html#zenml.integrations.whylogs) to specify Whylogs settings.
  * [`SagemakerStepOperatorSettings`](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-aws.html#zenml.integrations.aws) to specify AWS Sagemaker step operator settings.
  * [`VertexStepOperatorSettings`](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-gcp.html#zenml.integrations.gcp) to specify GCP Vertex step operator settings.
  * [`AzureMLStepOperatorSettings`](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-azure.html#zenml.integrations.azure) to specify AzureML step operator settings.

### Difference between stack component settings at registration-time vs real-time

For stack-component-specific settings, you might be wondering what the difference is between these and the configuration passed in while doing `zenml stack-component register <NAME> --config1=configvalue --config2=configvalue`, etc. The answer is that the configuration passed in at registration time is static and fixed throughout all pipeline runs, while the settings can change.

A good example of this is the [`MLflow Experiment Tracker`](https://docs.zenml.io/stacks/experiment-trackers/mlflow), where configuration which remains static such as the `tracking_url` is sent through at registration time, while runtime configuration such as the `experiment_name` (which might change every pipeline run) is sent through as runtime settings.

Even though settings can be overridden at runtime, you can also specify _default_ values for settings while configuring a stack component. For example, you could set a default value for the `nested` setting of your MLflow experiment tracker: `zenml experiment-tracker register <NAME> --flavor=mlflow --nested=True`

This means that all pipelines that run using this experiment tracker use nested MLflow runs unless overridden by specifying settings for the pipeline at runtime.

### Using the right key for Stack-component-specific settings

When specifying stack-component-specific settings, a key needs to be passed. This key should always correspond to the pattern: `<COMPONENT_CATEGORY>` or `<COMPONENT_CATEGORY>.<COMPONENT_FLAVOR>`. If you specify just the category (e.g. `step_operator` or `orchestrator`), ZenML will try to apply those settings to whatever flavor of component is in your stack when running a pipeline. If your settings don't apply to this flavor, they will be ignored.

For example, the [SagemakerStepOperator](https://docs.zenml.io/stacks/step-operators/sagemaker) supports passing in [`estimator_args`](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-aws.html#zenml.integrations.aws). The way to specify this would be to use the key `step_operator`

```python
@step(step_operator="nameofstepoperator", settings= {"step_operator": {"estimator_args": {"instance_type": "m7g.medium"}}})
def my_step():
  ...

# Using the class
@step(step_operator="nameofstepoperator", settings= {"step_operator": SagemakerStepOperatorSettings(instance_type="m7g.medium")})
def my_step():
  ...
```

or in YAML:

```yaml
steps:
  my_step:
    step_operator: "nameofstepoperator"
    settings:
      step_operator:
        estimator_args:
          instance_type: m7g.medium
```

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
