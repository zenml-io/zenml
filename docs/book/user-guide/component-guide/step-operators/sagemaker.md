---
description: Executing individual steps in SageMaker.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Amazon SageMaker

The SageMaker step operator is a [step operator](step-operators.md) flavor provided with the ZenML `aws` integration
that uses [SageMaker](https://aws.amazon.com/sagemaker/) to execute individual steps of ZenML pipelines.

### When to use it

You should use the SageMaker step operator if:

* one or more steps of your pipeline require computing resources (CPU, GPU, memory) that are not provided by your
  orchestrator.
* you have access to SageMaker. If you're using a different cloud provider, take a look at the [Vertex](vertex.md)
  or [AzureML](azureml.md) step operators.

### How to deploy it

* Create a role in the IAM console that you want the jobs running in SageMaker to assume. This role should at least have
  the `AmazonS3FullAccess` and `AmazonSageMakerFullAccess` policies applied.
  Check [here](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-roles.html#sagemaker-roles-create-execution-role)
  for a guide on how to set up this role.

#### Infrastructure Deployment

A Sagemaker step operator can be deployed directly from the ZenML CLI:

```shell
zenml orchestrator deploy sagemaker_step_operator --flavor=sagemaker ...
```

You can pass other configurations specific to the stack components as key-value arguments. If you don't provide a name,
a random one is generated for you. For more information about how to work use the CLI for this, please refer to the
dedicated documentation section.

### How to use it

To use the SageMaker step operator, we need:

* The ZenML `aws` integration installed. If you haven't done so, run

  ```shell
  zenml integration install aws
  ```
* [Docker](https://www.docker.com) installed and running.
* An IAM role with the correct permissions. See the [deployment section](sagemaker.md#how-to-deploy-it) for detailed
  instructions.
* An [AWS container registry](../container-registries/aws.md) as part of our stack. Take a
  look [here](../container-registries/aws.md#how-to-deploy-it) for a guide on how to set that up.
* A [remote artifact store](../artifact-stores/artifact-stores.md) as part of your stack. This is needed so that both
  your orchestration environment and SageMaker can read and write step artifacts. Check out the documentation page of
  the artifact store you want to use for more information on how to set that up and configure authentication for it.
* If using a [local orchestrator](../orchestrators/local.md): The `aws` cli set up and authenticated. Make sure you have
  the permissions to create and manage SageMaker runs.
* If using a remote orchestrator: The environment in which the orchestrator runs its containers needs to be able to
  assume the IAM role specified when registering the SageMaker step operator.
* An instance type that we want to execute our steps on.
  See [here](https://docs.aws.amazon.com/sagemaker/latest/dg/notebooks-available-instance-types.html) for a list of
  available instance types.
* (Optional) An experiment that is used to group SageMaker runs.
  Check [this guide](https://docs.aws.amazon.com/sagemaker/latest/dg/experiments-create.html) to see how to create an
  experiment.

We can then register the step operator and use it in our active stack:

```shell
zenml step-operator register <NAME> \
    --flavor=sagemaker \
    --role=<SAGEMAKER_ROLE> \
    --instance_type=<INSTANCE_TYPE> \
#   --experiment_name=<EXPERIMENT_NAME> # optionally specify an experiment to assign this run to

# Add the step operator to the active stack
zenml stack update -s <NAME>
```

Once you added the step operator to your active stack, you can use it to execute individual steps of your pipeline by
specifying it in the `@step` decorator as follows:

```python
from zenml import step


@step(step_operator= <NAME>)
def trainer(...) -> ...:
    """Train a model."""
    # This step will be executed in SageMaker.
```

{% hint style="info" %}
ZenML will build a Docker image called `<CONTAINER_REGISTRY_URI>/zenml:<PIPELINE_NAME>` which includes your code and use
it to run your steps in SageMaker. Check
out [this page](/docs/book/user-guide/advanced-guide/containerize-your-pipeline.md) if you want to learn
more about how ZenML builds these images and how you can customize them.
{% endhint %}

#### Additional configuration

For additional configuration of the SageMaker step operator, you can pass `SagemakerStepOperatorSettings` when defining
or running your pipeline. Check out
the [API docs](https://apidocs.zenml.io/latest/integration\_code\_docs/integrations-aws/#zenml.integrations.aws.flavors.sagemaker\_step\_operator\_flavor.SagemakerStepOperatorSettings)
for a full list of available attributes and [this docs page](/docs/book/user-guide/advanced-guide/configure-steps-pipelines.md) for
more information on how to specify settings.

A concrete example of using the SageMaker step operator can be
found [here](https://github.com/zenml-io/zenml/tree/main/examples/step\_operator\_remote\_training).

For more information and a full list of configurable attributes of the SageMaker step operator, check out
the [API Docs](https://apidocs.zenml.io/latest/integration\_code\_docs/integrations-aws/#zenml.integrations.aws.step\_operators.sagemaker\_step\_operator.SagemakerStepOperator)
.

#### Enabling CUDA for GPU-backed hardware

Note that if you wish to use this step operator to run steps on a GPU, you will need to
follow [the instructions on this page](/docs/book/user-guide/advanced-guide/scale-compute-to-the-cloud.md) to ensure that it
works. It requires adding some extra settings customization and is essential to enable CUDA for the GPU to give its full
acceleration.
