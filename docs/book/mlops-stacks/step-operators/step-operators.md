---
description: How to execute individual steps in specialized environments
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


The step operator enables the execution of individual pipeline steps in
specialized runtime environments that are optimized for certain workloads.
These specialized environments can give your steps access to resources like 
GPUs or distributed processing frameworks like [Spark](https://spark.apache.org/).

{% hint style="info" %}
**Comparison to orchestrators:**
The [orchestrator](../orchestrators/orchestrators.md) is a mandatory stack component that is responsible 
for executing all steps of a pipeline in the correct order and provide 
additional features such as scheduling pipeline runs. The step operator 
on the other hand is used to only execute individual steps of the pipeline 
in a separate environment in case the environment provided by the orchestrator
is not feasible.
{% endhint %}

## When to use it

A step operator should be used if one or more steps of a pipeline require resources
that are not available in the runtime environments provided by the [orchestrator](../orchestrators/orchestrators.md).
An example would be a step that trains a computer vision model and requires a GPU to
run in reasonable time, combined with a [Kubeflow orchestrator](../orchestrators/kubeflow.md) running on a kubernetes 
cluster which does not contain any GPU nodes. In that case it makes sense to include a 
step operator like [SageMaker](./amazon-sagemaker.md), [Vertex](./gcloud-vertexai.md) 
or [AzureML](./azureml.md) to execute the training step with a GPU.

## Step Operator Flavors

Step operators to execute steps on one of the big cloud providers are provided
by the following ZenML integrations:

| Step Operator | Flavor | Integration | Notes             |
|----------------|--------|-------------|-------------------|
| [SageMaker](./amazon-sagemaker.md) | `sagemaker` | `aws` | Uses SageMaker to execute steps |
| [Vertex](./gcloud-vertexai.md) | `vertex` | `gcp` |  Uses Vertex AI to execute steps |
| [AzureML](./azureml.md) | `azureml` | `azure` |  Uses AzureML to execute steps |
| [Custom Implementation](./custom.md) | _custom_ | | Extend the step operator abstraction and provide your own implementation |

If you would like to see the available flavors of step operators, you can 
use the command:

```shell
zenml step-operator flavor list
```

## How to use it

You don't need to directly interact with any ZenML step operator in your code.
As long as the step operator that you want to use is part of your active 
[ZenML stack](../../developer-guide/stacks-profiles-repositories/stack.md),
you can simply specify it in the `@step `decorator of your
[step](../../developer-guide/steps-pipelines/steps-and-pipelines.md#step):

```python
from zenml.steps import step

@step(custom_step_operator=<STEP_OPERATOR_NAME>)
def my_step(...) -> ...:
    ...
```

### Specifying per-step resources

If some of your steps require additional hardware resources,
you can specify them on your steps as described
[here](../../developer-guide/advanced-usage/specify-step-resources.md).
