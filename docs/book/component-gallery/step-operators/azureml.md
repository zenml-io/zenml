---
description: How to execute individual steps in AzureML
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


The AzureML step operator is a [step operator](./step-operators.md) flavor 
provided with the ZenML `azure` integration that uses 
[AzureML](https://azure.microsoft.com/en-us/services/machine-learning/)
to execute individual steps of ZenML pipelines.

## When to use it

You should use the AzureML step operator if:
* one or more steps of your pipeline require computing resources 
(CPU, GPU, memory) that are not provided by your orchestrator.
* you have access to AzureML. If you're using a different cloud 
provider, take a look at the [SageMaker](./amazon-sagemaker.md) or 
[Vertex](./gcloud-vertexai.md) step operators.

## How to deploy it

* Create a `Machine learning` [resource on Azure](https://docs.microsoft.com/en-us/azure/machine-learning/quickstart-create-resources).
* Once your resource is created, you can head over to the `Azure Machine Learning Studio`
and [create a compute cluster](https://docs.microsoft.com/en-us/azure/machine-learning/quickstart-create-resources#cluster) to run your pipelines.
* Create an `environment` for your pipelines. Follow [this guide](https://docs.microsoft.com/en-us/azure/machine-learning/how-to-manage-environments-in-studio) to set one up.
* (Optional) Create a [Service Principal](https://docs.microsoft.com/en-us/azure/developer/java/sdk/identity-service-principal-auth) for authentication. This is required if
you intend to run your pipelines with a remote orchestrator.

## How to use it

To use the AzureML step operator, we need:
* The ZenML `azure` integration installed. If you haven't done so, run 
    ```shell
    zenml integration install azure
    ```
* An AzureML compute cluster and environment. See the [deployment section](#how-do-you-deploy-it)
for detailed instructions.
* A [remote artifact store](../artifact-stores/artifact-stores.md) as part of 
your stack. This is needed so that both your orchestration environment and 
AzureML can read and write step artifacts. Check out the documentation page of 
the artifact store you want to use for more information on how to set that up
and configure authentication for it.

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

Once you added the step operator to your active stack, you can use it to
execute individual steps of your pipeline by specifying it in the `@step` decorator as follows:
```python
from zenml.steps import step

@step(step_operator=<NAME>)
def trainer(...) -> ...:
    """Train a model."""
    # This step will be executed in AzureML.
```

{% hint style="info" %}
ZenML will build a Docker image called `<CONTAINER_REGISTRY_URI>/zenml:<PIPELINE_NAME>`
which includes your code and use it to run your steps in AzureML. Check out
[this page](../../advanced-guide/pipelines/containerization.md) if you want to 
learn more about how ZenML builds these images and how you can customize them.
{% endhint %}

A concrete example of using the AzureML step operator can be found 
[here](https://github.com/zenml-io/zenml/tree/main/examples/step_operator_remote_training).

For more information and a full list of configurable attributes of the AzureML 
step operator, check out the [API Docs](https://apidocs.zenml.io/latest/api_docs/integration_code_docs/integrations-azure/#zenml.integrations.azure.step_operators.azureml_step_operator.AzureMLStepOperator).

### Enabling CUDA for GPU-backed hardware

Note that if you wish to use this step operator to run steps on a GPU, you will
need to follow [the instructions on this page](../../advanced-guide/pipelines/gpu-hardware.md) to ensure that it works. It
requires adding some extra settings customization and is essential to enable
CUDA for the GPU to give its full acceleration.
