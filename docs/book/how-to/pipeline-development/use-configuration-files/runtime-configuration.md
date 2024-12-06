---
description: Using settings to configure runtime configuration.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Stack component specific configuration

{% embed url="https://www.youtube.com/embed/AdwW6DlCWFE" %}
Stack Component Config vs Settings in ZenML
{% endembed %}

Part of the configuration of a pipeline are its `Settings`. These allow you to configure runtime configurations for stack components and pipelines. Concretely, they allow you to configure:

* The [resources](../../advanced-topics/training-with-gpus/training-with-gpus.md#specify-resource-requirements-for-steps) required for a step
* Configuring the [containerization](../../infrastructure-deployment/customize-docker-builds/README.md) process of a pipeline (e.g. What requirements get installed in the Docker image)
* Stack component-specific configuration, e.g., if you have an experiment tracker passing in the name of the experiment at runtime

You will learn about all of the above in more detail later, but for now, let's try to understand that all of this configuration flows through one central concept called `BaseSettings`. (From here on, we use `settings` and `BaseSettings` as analogous in this guide).

## Types of settings

Settings are categorized into two types:

* **General settings** that can be used on all ZenML pipelines. Examples of these are:
  * [`DockerSettings`](../customize-docker-builds/README.md) to specify Docker settings.
  * [`ResourceSettings`](../training-with-gpus/training-with-gpus.md) to specify resource settings.
* **Stack-component-specific settings**: These can be used to supply runtime configurations to certain stack components (the key should be `<COMPONENT_CATEGORY>` or `<COMPONENT_CATEGORY>.<COMPONENT_FLAVOR>`). Settings for components not in the active stack will be ignored. Examples of these are:
  * [`SkypilotAWSOrchestratorSettings`](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-skypilot_aws/#zenml.integrations.skypilot_aws.flavors.skypilot_orchestrator_aws_vm_flavor.SkypilotAWSOrchestratorSettings) to specify Skypilot settings (works for `SkypilotGCPOrchestratorSettings` and `SkypilotAzureOrchestratorSettings` as well).
  * [`KubeflowOrchestratorSettings`](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-kubeflow/#zenml.integrations.kubeflow.flavors.kubeflow_orchestrator_flavor.KubeflowOrchestratorSettings) to specify Kubeflow settings.
  * [`MLflowExperimentTrackerSettings`](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-mlflow/#zenml.integrations.mlflow.flavors.mlflow_experiment_tracker_flavor.MLFlowExperimentTrackerSettings) to specify MLflow settings.
  * [`WandbExperimentTrackerSettings`](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-wandb/#zenml.integrations.wandb.flavors.wandb_experiment_tracker_flavor.WandbExperimentTrackerSettings) to specify W\&B settings.
  * [`WhylogsDataValidatorSettings`](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-whylogs/#zenml.integrations.whylogs.flavors.whylogs_data_validator_flavor.WhylogsDataValidatorSettings) to specify Whylogs settings.
  * [`SagemakerStepOperatorSettings`](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-aws/#zenml.integrations.aws.flavors.sagemaker_step_operator_flavor.SagemakerStepOperatorSettings) to specify AWS Sagemaker step operator settings.
  * [`VertexStepOperatorSettings`](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-gcp/#zenml.integrations.gcp.flavors.vertex_step_operator_flavor.VertexStepOperatorSettings) to specify GCP Vertex step operator settings.
  * [`AzureMLStepOperatorSettings`](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-azure/#zenml.integrations.azure.flavors.azureml_step_operator_flavor.AzureMLStepOperatorSettings) to specify AzureML step operator settings.

### Difference between stack component settings at registration-time vs real-time

For stack-component-specific settings, you might be wondering what the difference is between these and the configuration passed in while doing `zenml stack-component register <NAME> --config1=configvalue --config2=configvalue`, etc. The answer is that the configuration passed in at registration time is static and fixed throughout all pipeline runs, while the settings can change.

A good example of this is the [`MLflow Experiment Tracker`](../../../component-guide/experiment-trackers/mlflow.md), where configuration which remains static such as the `tracking_url` is sent through at registration time, while runtime configuration such as the `experiment_name` (which might change every pipeline run) is sent through as runtime settings.

Even though settings can be overridden at runtime, you can also specify _default_ values for settings while configuring a stack component. For example, you could set a default value for the `nested` setting of your MLflow experiment tracker: `zenml experiment-tracker register <NAME> --flavor=mlflow --nested=True`

This means that all pipelines that run using this experiment tracker use nested MLflow runs unless overridden by specifying settings for the pipeline at runtime.

### Using the right key for Stack-component-specific settings

When specifying stack-component-specific settings, a key needs to be passed. This key should always correspond to the pattern: `<COMPONENT_CATEGORY>` or `<COMPONENT_CATEGORY>.<COMPONENT_FLAVOR>`. If you specify just the category (e.g. `step_operator` or `orchestrator`), ZenML will try to apply those settings to whatever flavor of component is in your stack when running a pipeline. If your settings don't apply to this flavor, they will be ignored.

For example, the [SagemakerStepOperator](../../../component-guide/step-operators/sagemaker.md) supports passing in [`estimator_args`](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-aws/#zenml.integrations.aws.flavors.sagemaker\_step\_operator\_flavor.SagemakerStepOperatorSettings). The way to specify this would be to use the key `step_operator`

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
