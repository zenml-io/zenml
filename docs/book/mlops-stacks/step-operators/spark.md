---
description: How to execute individual steps on Spark
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


The `spark` integration brings two different step operators:

- **Step Operator**: The `SparkStepOperator` serves as the base class for all 
the Spark-related step operators.
- **Step Operator**: The `KubernetesSparkStepOperator` is responsible for 
launching ZenML steps as Spark applications with Kubernetes as a 
cluster manager.

## Step Operators: `SparkStepOperator`

A summarized version of the implementation looks as follows:

```python
class SparkStepOperator(BaseStepOperator):
    """Base class for all Spark-related step operators."""
		
		# Instance parameters
    master: str
    deploy_mode: str = "cluster"
    submit_kwargs: Optional[Dict[str, Any]] = None

    def _resource_configuration(
        self,
        spark_config: SparkConf,
        resource_configuration: "ResourceConfiguration",
    ) -> None:
				"""Configures Spark to handle the resource configuration."""

    def _backend_configuration(
        self,
        spark_config: SparkConf,
        docker_configuration: "DockerConfiguration",
        pipeline_name: str,
    ) -> None:
        """Configures Spark to handle backends like YARN, Mesos, Kubernetes."""

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
        self, spark_config: SparkConf, entrypoint_command: List[str]
    ) -> None:
        """Generates and executes a spark-submit command."""

    def launch(
        self,
        pipeline_name: str,
        run_name: str,
        docker_configuration: "DockerConfiguration",
        entrypoint_command: List[str],
        resource_configuration: "ResourceConfiguration",
    ) -> None:
        """Launches the step on Spark."""
```

Under the base class, the first thing you will spot is the instance parameters: 

- `master` is the master URL for the cluster where Spark will run. You might 
see different schemes for this URL with varying cluster managers such as 
Mesos, YARN, or Kubernetes.
- `deploy_mode` can either be 'cluster' (default) or 'client' and it decides 
where the driver node of the application will run.
- `submit_args` is the JSON string of a dictionary, which will be used to 
define additional params if required (Spark has a wide variety of parameters, 
thus including them all in a single class was deemed unnecessary.).

In addition to these parameters, the `launch` method of the step operator 
gets additional configuration parameters from the `DockerConfiguration` and 
`ResourceConfiguration`. As a result, the overall configuration happens in 4 
base methods:

- `_resource_configuration` translates the ZenML `ResourceConfiguration` object 
to Spark's own resource configuration.
- `_backend_configuration` is responsible for cluster-manager-specific 
configuration.
- `_io_configuration` is a critical method. Even though we have materializers, 
Spark might require additional packages and configuration to work with a 
specific filesystem. This method is used as an interface to provide this 
configuration.
- `_additional_configuration` takes the `submit_args`, converts, and appends 
them to the overall configuration.

Once the configuration is completed, `_launch_spark_job` comes into play. 
This takes the completed configuration and runs a Spark job on the given 
`master` URL with the specified `deploy_mode`. By default, this is achieved 
by creating and executing a `spark-submit` command.

### Warning

In its first iteration, the pre-configuration with `_io_configuration` method 
is only effective when it is paired with an `S3ArtifactStore` (which has an 
authentication secret). When used with other artifact store flavors, you might 
be required to provide additional configuration through the `submit_args`.

## Stack Component: `KubernetesSparkStepOperator`

The `KubernetesSparkStepOperator` is implemented by subclassing the 
base `SparkStepOperator` and the `PipelineDockerImageBuilder`. While 
`SparkStepOperator` will provide us a base to start with and the 
`PipelineDockerImageBuilder` will give this class the functionality to build 
and push the required docker images. 

```python
class KubernetesSparkStepOperator(
    SparkStepOperator, PipelineDockerImageBuilder
):
		"""Step operator which runs Steps with Spark on Kubernetes."""
    # Parameters for Kubernetes
    namespace: Optional[str] = None
    service_account: Optional[str] = None

    def _backend_configuration(
        self,
        spark_config: SparkConf,
        docker_configuration: "DockerConfiguration",
        pipeline_name: str,
    ) -> None:
        """Configures Spark to run on Kubernetes."""
        # Build and push the image
        image_name = self.build_and_push_docker_image(...)

        # Adjust the spark configuration
        spark_config.set("spark.kubernetes.container.image", image_name)
        ...
```

For Kubernetes, there are also some additional important parameters:

- `namespace` is the namespace under which the driver and executor 
pods will run.
- `service_account` is the service account that will be used by 
various Spark components (to create and watch the pods).
- `docker_parent_image` (which originally comes from the 
`PipelineDockerImageBuilder` base class) indicates the name of a base image 
that has Spark enabled.

Additionally, the `_backend_configuration` method is adjusted to handle the 
Kubernetes-specific configuration.

## When to use it

You should use the Spark step operator:
* when you are dealing with large amounts of data.
* when you are designing a step which can benefit from distributed computing 
paradigms in terms of time and resources.

## How to deploy it

The `KubernetesSparkStepOperator` requires a Kubernetes cluster in order to run.
There are many ways to deploy a Kubernetes cluster using different cloud 
providers or on your custom infrastructure, and we can't possibly cover 
all of them, but you can check out the 
[spark example](https://github.com/zenml-io/zenml/tree/main/examples/spark_distributed_programming) 
to see how it is deployed on AWS.

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

A concrete example of using the Spark step operator can be found 
[here](https://github.com/zenml-io/zenml/tree/main/examples/spark_distributed_programming).