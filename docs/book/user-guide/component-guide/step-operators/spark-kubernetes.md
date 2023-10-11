---
description: Executing individual steps on Spark
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Spark

The `spark` integration brings two different step operators:

* **Step Operator**: The `SparkStepOperator` serves as the base class for all the Spark-related step operators.
* **Step Operator**: The `KubernetesSparkStepOperator` is responsible for launching ZenML steps as Spark applications
  with Kubernetes as a cluster manager.

### Step Operators: `SparkStepOperator`

A summarized version of the implementation can be summarized in two parts. First, the configuration:

```python
from typing import Optional, Dict, Any
from zenml.step_operators import BaseStepOperatorConfig


class SparkStepOperatorConfig(BaseStepOperatorConfig):
    """Spark step operator config.

    Attributes:
        master: is the master URL for the cluster. You might see different
            schemes for different cluster managers which are supported by Spark
            like Mesos, YARN, or Kubernetes. Within the context of this PR,
            the implementation supports Kubernetes as a cluster manager.
        deploy_mode: can either be 'cluster' (default) or 'client' and it
            decides where the driver node of the application will run.
        submit_kwargs: is the JSON string of a dict, which will be used
            to define additional params if required (Spark has quite a
            lot of different parameters, so including them, all in the step
            operator was not implemented).
    """

    master: str
    deploy_mode: str = "cluster"
    submit_kwargs: Optional[Dict[str, Any]] = None
```

and then the implementation:

```python
from typing import List
from pyspark.conf import SparkConf

from zenml.step_operators import BaseStepOperator


class SparkStepOperator(BaseStepOperator):
    """Base class for all Spark-related step operators."""

    def _resource_configuration(
            self,
            spark_config: SparkConf,
            resource_configuration: "ResourceSettings",
    ) -> None:
        """Configures Spark to handle the resource configuration."""

    def _backend_configuration(
            self,
            spark_config: SparkConf,
            step_config: "StepConfiguration",
    ) -> None:
        """Configures Spark to handle backends like YARN, Mesos or Kubernetes."""

    def _io_configuration(
            self,
            spark_config: SparkConf
    ) -> None:
        """Configures Spark to handle different input/output sources."""

    def _additional_configuration(
            self,
            spark_config: SparkConf
    ) -> None:
        """Appends the user-defined configuration parameters."""

    def _launch_spark_job(
            self,
            spark_config: SparkConf,
            entrypoint_command: List[str]
    ) -> None:
        """Generates and executes a spark-submit command."""

    def launch(
            self,
            info: "StepRunInfo",
            entrypoint_command: List[str],
    ) -> None:
        """Launches the step on Spark."""
```

Under the base configuration, you will see the main configuration parameters:

* `master` is the master URL for the cluster where Spark will run. You might see different schemes for this URL with
  varying cluster managers such as Mesos, YARN, or Kubernetes.
* `deploy_mode` can either be 'cluster' (default) or 'client' and it decides where the driver node of the application
  will run.
* `submit_args` is the JSON string of a dictionary, which will be used to define additional parameters if required (
  Spark has a wide variety of parameters, thus including them all in a single class was deemed unnecessary.).

In addition to this configuration, the `launch` method of the step operator gets additional configuration parameters
from the `DockerSettings` and `ResourceSettings`. As a result, the overall configuration happens in 4 base methods:

* `_resource_configuration` translates the ZenML `ResourceSettings` object to Spark's own resource configuration.
* `_backend_configuration` is responsible for cluster-manager-specific configuration.
* `_io_configuration` is a critical method. Even though we have materializers, Spark might require additional packages
  and configuration to work with a specific filesystem. This method is used as an interface to provide this
  configuration.
* `_additional_configuration` takes the `submit_args`, converts, and appends them to the overall configuration.

Once the configuration is completed, `_launch_spark_job` comes into play. This takes the completed configuration and
runs a Spark job on the given `master` URL with the specified `deploy_mode`. By default, this is achieved by creating
and executing a `spark-submit` command.

#### Warning

In its first iteration, the pre-configuration with `_io_configuration` method is only effective when it is paired with
an `S3ArtifactStore` (which has an authentication secret). When used with other artifact store flavors, you might be
required to provide additional configuration through the `submit_args`.

### Stack Component: `KubernetesSparkStepOperator`

The `KubernetesSparkStepOperator` is implemented by subclassing the base `SparkStepOperator` and uses
the `PipelineDockerImageBuilder` class to build and push the required docker images.

```python
from typing import Optional

from zenml.integrations.spark.step_operators.spark_step_operator import (
    SparkStepOperatorConfig
)


class KubernetesSparkStepOperatorConfig(SparkStepOperatorConfig):
    """Config for the Kubernetes Spark step operator."""

    namespace: Optional[str] = None
    service_account: Optional[str] = None
```

```python
from pyspark.conf import SparkConf

from zenml.utils.pipeline_docker_image_builder import PipelineDockerImageBuilder
from zenml.integrations.spark.step_operators.spark_step_operator import (
    SparkStepOperator
)


class KubernetesSparkStepOperator(SparkStepOperator):
    """Step operator which runs Steps with Spark on Kubernetes."""

    def _backend_configuration(
            self,
            spark_config: SparkConf,
            step_config: "StepConfiguration",
    ) -> None:
        """Configures Spark to run on Kubernetes."""
        # Build and push the image
        docker_image_builder = PipelineDockerImageBuilder()
        image_name = docker_image_builder.build_and_push_docker_image(...)

        # Adjust the spark configuration
        spark_config.set("spark.kubernetes.container.image", image_name)
        ...
```

For Kubernetes, there are also some additional important configuration parameters:

* `namespace` is the namespace under which the driver and executor pods will run.
* `service_account` is the service account that will be used by various Spark components (to create and watch the pods).

Additionally, the `_backend_configuration` method is adjusted to handle the Kubernetes-specific configuration.

### When to use it

You should use the Spark step operator:

* when you are dealing with large amounts of data.
* when you are designing a step that can benefit from distributed computing paradigms in terms of time and resources.

### How to deploy it

The `KubernetesSparkStepOperator` requires a Kubernetes cluster in order to run. There are many ways to deploy a
Kubernetes cluster using different cloud providers or on your custom infrastructure, and we can't possibly cover all of
them, but you can check out
the [spark example](https://github.com/zenml-io/zenml/tree/main/examples/spark\_distributed\_programming) to see how it
is deployed on AWS.

### How to use it

In order to use the `KubernetesSparkStepOperator`, you need:

* the ZenML `spark` integration. If you haven't installed it already, run

  ```shell
  zenml integration install spark
  ```
* [Docker](https://www.docker.com) installed and running.
* A [remote artifact store](../artifact-stores/artifact-stores.md) as part of your stack.
* A [remote container registry](../container-registries/container-registries.md) as part of your stack.
* A Kubernetes cluster [deployed](spark-kubernetes.md#how-to-deploy-it).

We can then register the step operator and use it in our active stack:

```shell
zenml step-operator register <NAME> \
	--flavor=spark-kubernetes \
	--master=k8s://<API_SERVER_ENDPOINT> \
	--namespace=<KUBERNETES_NAMESPACE> \
	--service_account=<KUBERNETES_SERVICE_ACCOUNT>
```

Once you added the step operator to your active stack, you can use it to execute individual steps of your pipeline by
specifying it in the `@step` decorator as follows:

```python
from zenml import step


@step(step_operator= <NAME>)
def preprocess(...) -> ...:
    """Preprocess your dataset."""
    # This step will be executed with Spark on Kubernetes.
```

#### Additional configuration

For additional configuration of the Spark step operator, you can pass `SparkStepOperatorSettings` when defining or
running your pipeline. Check out
the [API docs](https://apidocs.zenml.io/latest/integration\_code\_docs/integrations-spark/#zenml.integrations.spark.flavors.spark\_step\_operator\_flavor.SparkStepOperatorSettings)
for a full list of available attributes and [this docs page](/docs/book/user-guide/advanced-guide/configure-steps-pipelines.md) for
more information on how to specify settings.

A concrete example of using the Spark step operator can be
found [here](https://github.com/zenml-io/zenml/tree/main/examples/spark\_distributed\_programming).

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
