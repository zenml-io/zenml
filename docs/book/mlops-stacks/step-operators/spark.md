---
description: How to execute individual steps on Spark
---

The `spark` integration brings two different step operators for our users to use:

- **Step Operator**: The `SparkStepOperator` serves as the base class for all 
the Spark-related step operators.
- **Step Operator**: The `KubernetesSparkStepOperator` is responsible for 
launching ZenML steps as Spark applications with Kubernetes as a 
cluster manager.

## When to use it

You should use the Spark step operator:
* when you are dealing with large amounts of data.
* when you are designing a step which can benefit from distributed computing 
paradigms in terms of time and resources.

## How to deploy it

The `KubernetesSparkStepOperator` requires a Kubernetes cluster in order to run.
There are many ways to deploy a Kubernetes cluster using different cloud 
providers or on your custom infrastructure, and we can't possibly cover 
all of them, but you can check out our 
[spark example](https://github.com/zenml-io/zenml/tree/main/examples/spark_distributed_programming) 
to see how we deployed it on AWS.

## How to use it

In order to use the `KubernetesSparkStepOperator`, you need:
* the ZenML `spark` integration. If you haven't installed it already, run 
    ```shell
    zenml integration install spark
    ```
  
* [Docker](https://www.docker.com) installed and running.
* A [remote artifact store](../artifact-stores/artifact-stores.md) as part of 
your stack.
* A [remote metadata store](../metadata-stores/metadata-stores.md) as part of 
your stack.
* A [remote container registry](../container-registries/container-registries.md)
as part of your stack.
* A [remote secrets manager](../secrets-managers/secrets-managers.md) as part of your
stack.
* A Kubernetes cluster [deployed](#how-to-deploy-it).

We can then register the step operator and use it in our active stack:

```shell
zenml step-operator register <NAME> \
	--flavor=spark-kubernetes \
	--master=k8s://<API_SERVER_ENDPOINT> \
	--namespace=<KUBERNETES_NAMESPACE> \
	--service_account=<KUBERNETES_SERVICE_ACCOUNT> \
	--docker_parent_image=<BASE_IMAGE_NAME>
```

Once you added the step operator to your active stack, you can use it to
execute individual steps of your pipeline by specifying it in the `@step` decorator as follows:
```python
from zenml.steps import step

@step(custom_step_operator=<NAME>)
def preprocess(...) -> ...:
    """Preprocess your dataset."""
    # This step will be executed with Spark on Kubernetes.
```

A concrete example of using the AzureML step operator can be found 
[here](https://github.com/zenml-io/zenml/tree/main/examples/spark_distributed_programming).