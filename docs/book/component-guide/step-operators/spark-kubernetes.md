---
description: Executing individual steps on Spark
---

# Spark

The `spark` integration brings two different step operators:

* **Step Operator**: The `SparkStepOperator` serves as the base class for all the Spark-related step operators.
* **Step Operator**: The `KubernetesSparkStepOperator` is responsible for launching ZenML steps as Spark applications with Kubernetes as a cluster manager.

## Step Operators: `SparkStepOperator`

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

* `master` is the master URL for the cluster where Spark will run. You might see different schemes for this URL with varying cluster managers such as Mesos, YARN, or Kubernetes.
* `deploy_mode` can either be 'cluster' (default) or 'client' and it decides where the driver node of the application will run.
* `submit_args` is the JSON string of a dictionary, which will be used to define additional parameters if required ( Spark has a wide variety of parameters, thus including them all in a single class was deemed unnecessary.).

In addition to this configuration, the `launch` method of the step operator gets additional configuration parameters from the `DockerSettings` and `ResourceSettings`. As a result, the overall configuration happens in 4 base methods:

* `_resource_configuration` translates the ZenML `ResourceSettings` object to Spark's own resource configuration.
* `_backend_configuration` is responsible for cluster-manager-specific configuration.
* `_io_configuration` is a critical method. Even though we have materializers, Spark might require additional packages and configuration to work with a specific filesystem. This method is used as an interface to provide this configuration.
* `_additional_configuration` takes the `submit_args`, converts, and appends them to the overall configuration.

Once the configuration is completed, `_launch_spark_job` comes into play. This takes the completed configuration and runs a Spark job on the given `master` URL with the specified `deploy_mode`. By default, this is achieved by creating and executing a `spark-submit` command.

### Warning

In its first iteration, the pre-configuration with `_io_configuration` method is only effective when it is paired with an `S3ArtifactStore` (which has an authentication secret). When used with other artifact store flavors, you might be required to provide additional configuration through the `submit_args`.

## Stack Component: `KubernetesSparkStepOperator`

The `KubernetesSparkStepOperator` is implemented by subclassing the base `SparkStepOperator` and uses the `PipelineDockerImageBuilder` class to build and push the required Docker images.

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

## When to use it

You should use the Spark step operator:

* when you are dealing with large amounts of data.
* when you are designing a step that can benefit from distributed computing paradigms in terms of time and resources.

## How to deploy it

To use the `KubernetesSparkStepOperator` you will need to setup a few things first:

* **Remote ZenML server:** See the [deployment guide](../../getting-started/deploying-zenml/README.md) for more information.
* **Kubernetes cluster:** There are many ways to deploy a Kubernetes cluster using different cloud providers or on your custom infrastructure. For AWS, you can follow the [Spark EKS Setup Guide](spark-kubernetes.md#spark-eks-setup-guide) below.

### Spark EKS Setup Guide

The following guide will walk you through how to spin up and configure a [Amazon Elastic Kubernetes Service](https://aws.amazon.com/eks/) with Spark on it:

#### EKS Kubernetes Cluster

* Follow [this guide](https://docs.aws.amazon.com/eks/latest/userguide/service\_IAM\_role.html#create-service-role) to create an Amazon EKS cluster role.
* Follow [this guide](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html#create-worker-node-role) to create an Amazon EC2 node role.
* Go to the [IAM website](https://console.aws.amazon.com/iam), and select `Roles` to edit both roles.
* Attach the `AmazonRDSFullAccess` and `AmazonS3FullAccess` policies to both roles.
* Go to the [EKS website](https://console.aws.amazon.com/eks).
* Make sure the correct region is selected on the top right.
* Click on `Add cluster` and select `Create`.
* Enter a name and select the **cluster role** for `Cluster service role`.
* Keep the default values for the networking and logging steps and create the cluster.
* Note down the cluster name and the API server endpoint:

```bash
EKS_CLUSTER_NAME=<EKS_CLUSTER_NAME>
EKS_API_SERVER_ENDPOINT=<API_SERVER_ENDPOINT>
```

* After the cluster is created, select it and click on `Add node group` in the `Compute` tab.
* Enter a name and select the **node role**.
* For the instance type, we recommend `t3a.xlarge`, as it provides up to 4 vCPUs and 16 GB of memory.

#### Docker image for the Spark drivers and executors

When you want to run your steps on a Kubernetes cluster, Spark will require you to choose a base image for the driver and executor pods. Normally, for this purpose, you can either use one of the base images in [Spark’s dockerhub](https://hub.docker.com/r/apache/spark-py/tags) or create an image using the [docker-image-tool](https://spark.apache.org/docs/latest/running-on-kubernetes.html#docker-images) which will use your own Spark installation and build an image.

When using Spark in EKS, you need to use the latter and utilize the `docker-image-tool`. However, before the build process, you also need to download the following packages

* [`hadoop-aws` = 3.3.1](https://mvnrepository.com/artifact/org.apache.hadoop/hadoop-aws/3.3.1)
* [`aws-java-sdk-bundle` = 1.12.150](https://mvnrepository.com/artifact/com.amazonaws/aws-java-sdk-bundle/1.12.150)

and put them in the `jars` folder within your Spark installation. Once that is set up, you can build the image as follows:

```bash
cd $SPARK_HOME # If this empty for you then you need to set the SPARK_HOME variable which points to your Spark installation

SPARK_IMAGE_TAG=<SPARK_IMAGE_TAG>

./bin/docker-image-tool.sh -t $SPARK_IMAGE_TAG -p kubernetes/dockerfiles/spark/bindings/python/Dockerfile -u 0 build

BASE_IMAGE_NAME=spark-py:$SPARK_IMAGE_TAG
```

If you are working on an M1 Mac, you will need to build the image for the amd64 architecture, by using the prefix `-X` on the previous command. For example:

```bash
./bin/docker-image-tool.sh -X -t $SPARK_IMAGE_TAG -p kubernetes/dockerfiles/spark/bindings/python/Dockerfile -u 0 build
```

#### Configuring RBAC

Additionally, you may need to create the several resources in Kubernetes in order to give Spark access to edit/manage your driver executor pods.

To do so, create a file called `rbac.yaml` with the following content:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: spark-namespace
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: spark-service-account
  namespace: spark-namespace
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: spark-role
  namespace: spark-namespace
subjects:
  - kind: ServiceAccount
    name: spark-service-account
    namespace: spark-namespace
roleRef:
  kind: ClusterRole
  name: edit
  apiGroup: rbac.authorization.k8s.io
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}

```

And then execute the following command to create the resources:

```bash
aws eks --region=$REGION update-kubeconfig --name=$EKS_CLUSTER_NAME

kubectl create -f rbac.yaml
```

Lastly, note down the **namespace** and the name of the **service account** since you will need them when registering the stack component in the next step.

## How to use it

To use the `KubernetesSparkStepOperator`, you need:

*   the ZenML `spark` integration. If you haven't installed it already, run

    ```shell
    zenml integration install spark
    ```
* [Docker](https://www.docker.com) installed and running.
* A [remote artifact store](../artifact-stores/artifact-stores.md) as part of your stack.
* A [remote container registry](../container-registries/container-registries.md) as part of your stack.
* A Kubernetes cluster [deployed](spark-kubernetes.md#how-to-deploy-it).

We can then register the step operator and use it in our active stack:

```bash
zenml step-operator register spark_step_operator \
	--flavor=spark-kubernetes \
	--master=k8s://$EKS_API_SERVER_ENDPOINT \
	--namespace=<SPARK_KUBERNETES_NAMESPACE> \
	--service_account=<SPARK_KUBERNETES_SERVICE_ACCOUNT>
```

```bash
# Register the stack
zenml stack register spark_stack \
    -o default \
    -s spark_step_operator \
    -a spark_artifact_store \
    -c spark_container_registry \
    -i local_builder \
    --set
```

Once you added the step operator to your active stack, you can use it to execute individual steps of your pipeline by specifying it in the `@step` decorator as follows:

```python
from zenml import step


@step(step_operator=<STEP_OPERATOR_NAME>)
def step_on_spark(...) -> ...:
    """Some step that should run with Spark on Kubernetes."""
    ...
```

After successfully running any step with a `KubernetesSparkStepOperator`, you should be able to see that a Spark driver pod was created in your cluster for each pipeline step when running `kubectl get pods -n $KUBERNETES_NAMESPACE`.

{% hint style="info" %}
Instead of hardcoding a step operator name, you can also use the [Client](../../reference/python-client.md) to dynamically use the step operator of your active stack:

```python
from zenml.client import Client

step_operator = Client().active_stack.step_operator

@step(step_operator=step_operator.name)
def step_on_spark(...) -> ...:
    ...
```
{% endhint %}

### Additional configuration

For additional configuration of the Spark step operator, you can pass `SparkStepOperatorSettings` when defining or running your pipeline. Check out the [SDK docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-spark/#zenml.integrations.spark.flavors.spark\_step\_operator\_flavor.SparkStepOperatorSettings) for a full list of available attributes and [this docs page](../../how-to/pipeline-development/use-configuration-files/runtime-configuration.md) for more information on how to specify settings.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
