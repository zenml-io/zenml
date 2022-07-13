---
description: Execute individual steps in specialized environments
---

The step operator enables the execution of individual pipeline steps in
specialized runtime environments that are optimized for certain workloads.
These specialized environments can give your steps access to resources like 
GPUs or distributed processing frameworks like [Spark](https://spark.apache.org/).

{% hint style="info" %}
**Comparison to orchestrators:**
The [orchestrator](../orchestrators/overview.md) is a mandatory stack component that is responsible 
for executing all steps of a pipeline in the correct order and provide 
additional features such as scheduling pipeline runs. The step operator 
on the other hand is used to only execute individual steps of the pipeline 
in a separate environment in case the environment provided by the orchestrator
is not feasible.
{% endhint %}

## When to use it

A step operator should be used if one or more steps of a pipeline require resources
that are not available in the runtime environments provided by the [orchestrator](../orchestrators/overview.md).
An example would be a step that trains a computer vision model and requires a GPU to
run in reasonable time, combined with a [Kubeflow orchestrator](../orchestrators/kubeflow.md) running on a kubernetes 
cluster which does not contain any GPU nodes. In that case it makes sense to include a 
step operator like [Sagemaker](./amazon_sagemaker.md), [Vertex](./gcloud_vertexai.md) 
or [AzureML](./azureml.md) to execute the training step with a GPU.

## Step Operator Flavors

Step operators to execute steps on one of the big cloud providers are provided
by the following ZenML integrations:

| Step Operator | Flavor | Integration | Notes             |
|----------------|--------|-------------|-------------------|
| [Sagemaker](./amazon_sagemaker.md) | `sagemaker` | `aws` | Uses Sagemaker to execute steps |
| [Vertex](./gcloud_vertexai.md) | `vertex` | `gcp` |  Uses Vertex AI to execute steps |
| [AzureML](./azureml.md) | `azureml` | `azure` |  Uses AzureML to execute steps |
| [Custom Implementation](./custom.md) | _custom_ | | Extend the step operator abstraction and provide your own implementation |

If you would like to see the available flavors of step operators, you can 
use the command:

```shell
zenml step-operator flavor list
```