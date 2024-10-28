---
description: Executing individual steps in SageMaker.
---

# Amazon SageMaker

[SageMaker](https://aws.amazon.com/sagemaker/) offers specialized compute instances to run your training jobs and has a comprehensive UI to track and manage your models and logs. ZenML's SageMaker step operator allows you to submit individual steps to be run on Sagemaker compute instances.

### When to use it

You should use the SageMaker step operator if:

* one or more steps of your pipeline require computing resources (CPU, GPU, memory) that are not provided by your orchestrator.
* you have access to SageMaker. If you're using a different cloud provider, take a look at the [Vertex](vertex.md) or [AzureML](azureml.md) step operators.

### How to deploy it

Create a role in the IAM console that you want the jobs running in SageMaker to assume. This role should at least have the `AmazonS3FullAccess` and `AmazonSageMakerFullAccess` policies applied. Check [here](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-roles.html#sagemaker-roles-create-execution-role) for a guide on how to set up this role.

### How to use it

To use the SageMaker step operator, we need:

*   The ZenML `aws` integration installed. If you haven't done so, run

    ```shell
    zenml integration install aws
    ```
* [Docker](https://www.docker.com) installed and running.
* An IAM role with the correct permissions. See the [deployment section](sagemaker.md#how-to-deploy-it) for detailed instructions.
* An [AWS container registry](../container-registries/aws.md) as part of our stack. Take a look [here](../container-registries/aws.md#how-to-deploy-it) for a guide on how to set that up.
* A [remote artifact store](../artifact-stores/artifact-stores.md) as part of your stack. This is needed so that both your orchestration environment and SageMaker can read and write step artifacts. Check out the documentation page of the artifact store you want to use for more information on how to set that up and configure authentication for it.
* An instance type that we want to execute our steps on. See [here](https://docs.aws.amazon.com/sagemaker/latest/dg/notebooks-available-instance-types.html) for a list of available instance types.
* (Optional) An experiment that is used to group SageMaker runs. Check [this guide](https://docs.aws.amazon.com/sagemaker/latest/dg/experiments-create.html) to see how to create an experiment.

There are two ways you can authenticate your orchestrator to AWS to be able to run steps on SageMaker:

{% tabs %}
{% tab title="Authentication via Service Connector" %}
The recommended way to authenticate your SageMaker step operator is by registering or using an existing [AWS Service Connector](../../how-to/auth-management/aws-service-connector.md) and connecting it to your SageMaker step operator. The credentials configured for the connector must have permissions to create and manage SageMaker runs (e.g. [the `AmazonSageMakerFullAccess` managed policy](https://docs.aws.amazon.com/sagemaker/latest/dg/security-iam-awsmanpol.html) permissions). The SageMaker step operator uses these `aws-generic` resource type, so make sure to configure the connector accordingly:

```shell
zenml service-connector register <CONNECTOR_NAME> --type aws -i
zenml step-operator register <STEP_OPERATOR_NAME> \
    --flavor=sagemaker \
    --role=<SAGEMAKER_ROLE> \
    --instance_type=<INSTANCE_TYPE> \
#   --experiment_name=<EXPERIMENT_NAME> # optionally specify an experiment to assign this run to

zenml step-operator connect <STEP_OPERATOR_NAME> --connector <CONNECTOR_NAME>
zenml stack register <STACK_NAME> -s <STEP_OPERATOR_NAME> ... --set
```
{% endtab %}

{% tab title="Implicit Authentication" %}
If you don't connect your step operator to a service connector:

* If using a [local orchestrator](../orchestrators/local.md): ZenML will try to implicitly authenticate to AWS via the `default` profile in your local [AWS configuration file](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html). Make sure this profile has permissions to create and manage SageMaker runs (e.g. [the `AmazonSageMakerFullAccess` managed policy](https://docs.aws.amazon.com/sagemaker/latest/dg/security-iam-awsmanpol.html) permissions).
* If using a remote orchestrator: the remote environment in which the orchestrator runs needs to be able to implicitly authenticate to AWS and assume the IAM role specified when registering the SageMaker step operator. This is only possible if the orchestrator is also running in AWS and uses a form of implicit workload authentication like the IAM role of an EC2 instance. If this is not the case, you will need to use a service connector.

```shell
zenml step-operator register <NAME> \
    --flavor=sagemaker \
    --role=<SAGEMAKER_ROLE> \
    --instance_type=<INSTANCE_TYPE> \
#   --experiment_name=<EXPERIMENT_NAME> # optionally specify an experiment to assign this run to

zenml stack register <STACK_NAME> -s <STEP_OPERATOR_NAME> ... --set
python run.py  # Authenticates with `default` profile in `~/.aws/config`
```
{% endtab %}
{% endtabs %}

Once you added the step operator to your active stack, you can use it to execute individual steps of your pipeline by specifying it in the `@step` decorator as follows:

```python
from zenml import step


@step(step_operator= <NAME>)
def trainer(...) -> ...:
    """Train a model."""
    # This step will be executed in SageMaker.
```

{% hint style="info" %}
ZenML will build a Docker image called `<CONTAINER_REGISTRY_URI>/zenml:<PIPELINE_NAME>` which includes your code and use it to run your steps in SageMaker. Check out [this page](../../how-to/customize-docker-builds/README.md) if you want to learn more about how ZenML builds these images and how you can customize them.
{% endhint %}

#### Additional configuration

For additional configuration of the SageMaker step operator, you can pass `SagemakerStepOperatorSettings` when defining or running your pipeline. Check out the [SDK docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-aws/#zenml.integrations.aws.flavors.sagemaker\_step\_operator\_flavor.SagemakerStepOperatorSettings) for a full list of available attributes and [this docs page](../../how-to/pipeline-development/use-configuration-files/runtime-configuration.md) for more information on how to specify settings.

For more information and a full list of configurable attributes of the SageMaker step operator, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-aws/#zenml.integrations.aws.step\_operators.sagemaker\_step\_operator.SagemakerStepOperator) .

#### Enabling CUDA for GPU-backed hardware

Note that if you wish to use this step operator to run steps on a GPU, you will need to follow [the instructions on this page](../../how-to/training-with-gpus/training-with-gpus.md) to ensure that it works. It requires adding some extra settings customization and is essential to enable CUDA for the GPU to give its full acceleration.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
