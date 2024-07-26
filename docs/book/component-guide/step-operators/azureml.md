---
description: Executing individual steps in AzureML.
---

# AzureML

[AzureML](https://azure.microsoft.com/en-us/products/machine-learning/) offers specialized compute instances to run your training jobs and has a comprehensive UI to track and manage your models and logs. ZenML's AzureML step operator allows you to submit individual steps to be run on AzureML compute instances.

### When to use it

You should use the AzureML step operator if:

* one or more steps of your pipeline require computing resources (CPU, GPU, memory) that are not provided by your orchestrator.
* you have access to AzureML. If you're using a different cloud provider, take a look at the [SageMaker](sagemaker.md) or [Vertex](vertex.md) step operators.

### How to deploy it

* Create a `Machine learning` [resource on Azure](https://docs.microsoft.com/en-us/azure/machine-learning/quickstart-create-resources) .
* Once your resource is created, you can head over to the `Azure Machine Learning Studio` and [create a compute cluster](https://docs.microsoft.com/en-us/azure/machine-learning/quickstart-create-resources#cluster) to run your pipelines.
* Create an `environment` for your pipelines. Follow [this guide](https://docs.microsoft.com/en-us/azure/machine-learning/how-to-manage-environments-in-studio) to set one up.
* (Optional) Create a [Service Principal](https://docs.microsoft.com/en-us/azure/developer/java/sdk/identity-service-principal-auth) for authentication. This is required if you intend to run your pipelines with a remote orchestrator.

### How to use it

To use the AzureML step operator, we need:

*   The ZenML `azure` integration installed. If you haven't done so, run

    ```shell
    zenml integration install azure
    ```
* An AzureML compute cluster and environment. See the [deployment section](azureml.md#how-to-deploy-it) for detailed instructions.
* A [remote artifact store](../artifact-stores/artifact-stores.md) as part of your stack. This is needed so that both your orchestration environment and AzureML can read and write step artifacts. Check out the documentation page of the artifact store you want to use for more information on how to set that up and configure authentication for it.

We can then register the step operator and use it in our active stack:

```shell
zenml step-operator register <NAME> \
    --flavor=azureml \
    --subscription_id=<AZURE_SUBSCRIPTION_ID> \
    --resource_group=<AZURE_RESOURCE_GROUP> \
    --workspace_name=<AZURE_WORKSPACE_NAME> \
    --compute_target_name=<AZURE_COMPUTE_TARGET_NAME> \
    --environment_name=<AZURE_ENVIRONMENT_NAME> \
# only pass these if using Service Principal Authentication
#   --tenant_id=<TENANT_ID> \
#   --service_principal_id=<SERVICE_PRINCIPAL_ID> \
#   --service_principal_password=<SERVICE_PRINCIPAL_PASSWORD> \

# Add the step operator to the active stack
zenml stack update -s <NAME>
```

Once you added the step operator to your active stack, you can use it to execute individual steps of your pipeline by specifying it in the `@step` decorator as follows:

```python
from zenml import step


@step(step_operator=<NAME>)
def trainer(...) -> ...:
    """Train a model."""
    # This step will be executed in AzureML.
```

{% hint style="info" %}
ZenML will build a Docker image called `<CONTAINER_REGISTRY_URI>/zenml:<PIPELINE_NAME>` which includes your code and use it to run your steps in AzureML. Check out [this page](../../how-to/customize-docker-builds/README.md) if you want to learn more about how ZenML builds these images and how you can customize them.
{% endhint %}

#### Additional configuration

For additional configuration of the AzureML step operator, you can pass `AzureMLStepOperatorSettings` when defining or running your pipeline. Check out the [SDK docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-azure/#zenml.integrations.azure.flavors.azureml\_step\_operator\_flavor.AzureMLStepOperatorSettings) for a full list of available attributes and [this docs page](../../how-to/use-configuration-files/runtime-configuration.md) for more information on how to specify settings.

For more information and a full list of configurable attributes of the AzureML step operator, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-azure/#zenml.integrations.azure.step\_operators.azureml\_step\_operator.AzureMLStepOperator) .

#### Enabling CUDA for GPU-backed hardware

Note that if you wish to use this step operator to run steps on a GPU, you will need to follow [the instructions on this page](../../how-to/training-with-gpus/training-with-gpus.md) to ensure that it works. It requires adding some extra settings customization and is essential to enable CUDA for the GPU to give its full acceleration.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
