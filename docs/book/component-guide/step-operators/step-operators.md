---
icon: arrow-progress
description: Executing individual steps in specialized environments.
---

# Step Operators

The step operator enables the execution of individual pipeline steps in specialized runtime environments that are optimized for certain workloads. These specialized environments can give your steps access to resources like GPUs or distributed processing frameworks like [Spark](https://spark.apache.org/).

{% hint style="info" %}
**Comparison to orchestrators:** The [orchestrator](../orchestrators/orchestrators.md) is a mandatory stack component that is responsible for executing all steps of a pipeline in the correct order and providing additional features such as scheduling pipeline runs. The step operator on the other hand is used to only execute individual steps of the pipeline in a separate environment in case the environment provided by the orchestrator is not feasible.
{% endhint %}

### When to use it

A step operator should be used if one or more steps of a pipeline require resources that are not available in the runtime environments provided by the [orchestrator](../orchestrators/orchestrators.md). An example would be a step that trains a computer vision model and requires a GPU to run in a reasonable time, combined with a [Kubeflow orchestrator](../orchestrators/kubeflow.md) running on a Kubernetes cluster that does not contain any GPU nodes. In that case, it makes sense to include a step operator like [SageMaker](sagemaker.md), [Vertex](vertex.md), or [AzureML](azureml.md) to execute the training step with a GPU.

### Step Operator Flavors

Step operators to execute steps on one of the big cloud providers are provided by the following ZenML integrations:

| Step Operator                      | Flavor       | Integration  | Notes                                                                    |
| ---------------------------------- | ------------ | ------------ | ------------------------------------------------------------------------ |
| [SageMaker](sagemaker.md)          | `sagemaker`  | `aws`        | Uses SageMaker to execute steps                                          |
| [Vertex](vertex.md)                | `vertex`     | `gcp`        | Uses Vertex AI to execute steps                                          |
| [AzureML](azureml.md)              | `azureml`    | `azure`      | Uses AzureML to execute steps                                            |
| [Kubernetes](kubernetes.md)        | `kubernetes` | `kubernetes` | Uses Kubernetes Pods to execute steps                                    |
| [Spark](spark-kubernetes.md)       | `spark`      | `spark`      | Uses Spark on Kubernetes to execute steps in a distributed manner        |
| [Custom Implementation](custom.md) | _custom_     |              | Extend the step operator abstraction and provide your own implementation |

If you would like to see the available flavors of step operators, you can use the command:

```shell
zenml step-operator flavor list
```

### How to use it

You don't need to directly interact with any ZenML step operator in your code. As long as the step operator that you want to use is part of your active [ZenML stack](broken-reference), you can simply specify it in the `@step` decorator of your step.

```python
from zenml import step


@step(step_operator= <STEP_OPERATOR_NAME>)
def my_step(...) -> ...:
    ...
```

#### Specifying per-step resources

If your steps require additional hardware resources, you can specify them on your steps as described [here](broken-reference).

#### Enabling CUDA for GPU-backed hardware

Note that if you wish to use step operators to run steps on a GPU, you will need to follow [the instructions on this page](broken-reference) to ensure that it works. It requires adding some extra settings customization and is essential to enable CUDA for the GPU to give its full acceleration.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
