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

{% hint style="info" %}
Would you like to skip ahead and deploy a full ZenML cloud stack already,
including an AzureML step operator? Check out the [in-browser stack deployment wizard](../../how-to/infrastructure-deployment/stack-deployment/deploy-a-cloud-stack.md),
the [stack registration wizard](../../how-to/infrastructure-deployment/stack-deployment/register-a-cloud-stack.md),
or [the ZenML Azure Terraform module](../../how-to/infrastructure-deployment/stack-deployment/deploy-a-cloud-stack-with-terraform.md)
for a shortcut on how to deploy & register this stack component.
{% endhint %}

* Create a `Machine learning` [workspace on Azure](https://docs.microsoft.com/en-us/azure/machine-learning/quickstart-create-resources). This should include an Azure container registry and an Azure storage account that will be used as part of your stack.
* (Optional) Once your resource is created, you can head over to the `Azure Machine Learning Studio` and [create a compute instance or cluster](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-create-compute-instance?view=azureml-api-2&tabs=python) to run your pipelines. If omitted, the AzureML step operator will use the serverless compute target or will provision a new compute target on the fly, depending on the settings used to configure the step operator.
* (Optional) Create a [Service Principal](https://docs.microsoft.com/en-us/azure/developer/java/sdk/identity-service-principal-auth) for authentication. This is required if you intend to use a service connector to authenticate your step operator.

### How to use it

To use the AzureML step operator, we need:

*   The ZenML `azure` integration installed. If you haven't done so, run

    ```shell
    zenml integration install azure
    ```
* [Docker](https://www.docker.com) installed and running.
* An [Azure container registry](../container-registries/azure.md) as part of your stack. Take a look [here](../container-registries/azure.md#how-to-deploy-it) for a guide on how to set that up.
* An [Azure artifact store](../artifact-stores/azure.md) as part of your stack. This is needed so that both your orchestration environment and AzureML can read and write step artifacts. Take a look [here](../container-registries/azure.md#how-to-deploy-it) for a guide on how to set that up.
* An AzureML workspace and an optional compute cluster. Note that the AzureML workspace can share the Azure container registry and Azure storage account that are required above. See the [deployment section](azureml.md#how-to-deploy-it) for detailed instructions.

There are two ways you can authenticate your step operator to be able to run steps on Azure:

{% tabs %}
{% tab title="Authentication via Service Connector" %}
The recommended way to authenticate your AzureML step operator is by registering or using an existing [Azure Service Connector](../../how-to/infrastructure-deployment/auth-management/azure-service-connector.md) and connecting it to your AzureML step operator. The credentials configured for the connector must have permissions to create and manage AzureML jobs (e.g. [the `AzureML Data Scientist` and `AzureML Compute Operator` managed roles](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-assign-roles?view=azureml-api-2&tabs=team-lead)). The AzureML step operator uses the `azure-generic` resource type, so make sure to configure the connector accordingly:

```shell
zenml service-connector register <CONNECTOR_NAME> --type azure -i
zenml step-operator register <STEP_OPERATOR_NAME> \
    --flavor=azureml \
    --subscription_id=<AZURE_SUBSCRIPTION_ID> \
    --resource_group=<AZURE_RESOURCE_GROUP> \
    --workspace_name=<AZURE_WORKSPACE_NAME> \
#   --compute_target_name=<AZURE_COMPUTE_TARGET_NAME> # optionally specify an existing compute target

zenml step-operator connect <STEP_OPERATOR_NAME> --connector <CONNECTOR_NAME>
zenml stack register <STACK_NAME> -s <STEP_OPERATOR_NAME> ... --set
```
{% endtab %}

{% tab title="Implicit Authentication" %}
If you don't connect your step operator to a service connector:

* If using a [local orchestrator](../orchestrators/local.md): ZenML will try to implicitly authenticate to Azure via the local [Azure CLI configuration](https://learn.microsoft.com/en-us/cli/azure/authenticate-azure-cli-interactively). Make sure the Azure CLI has permissions to create and manage AzureML jobs (e.g. [the `AzureML Data Scientist` and `AzureML Compute Operator` managed roles](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-assign-roles?view=azureml-api-2&tabs=team-lead)).
* If using a remote orchestrator: the remote environment in which the orchestrator runs needs to be able to implicitly authenticate to Azure and have permissions to create and manage AzureML jobs. This is only possible if the orchestrator is also running in Azure and uses a form of implicit workload authentication like a service role. If this is not the case, you will need to use a service connector.

```shell
zenml step-operator register <NAME> \
    --flavor=azureml \
    --subscription_id=<AZURE_SUBSCRIPTION_ID> \
    --resource_group=<AZURE_RESOURCE_GROUP> \
    --workspace_name=<AZURE_WORKSPACE_NAME> \
#   --compute_target_name=<AZURE_COMPUTE_TARGET_NAME> # optionally specify an existing compute target

zenml stack register <STACK_NAME> -s <STEP_OPERATOR_NAME> ... --set
```
{% endtab %}
{% endtabs %}

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

The ZenML AzureML step operator comes with a dedicated class called 
`AzureMLStepOperatorSettings` for configuring its settings and it controls
the compute resources used for step execution in AzureML.

Currently, it supports three different modes of operation.

1. Serverless Compute (Default)
- Set `mode` to `serverless`.
- Other parameters are ignored.

2. Compute Instance
- Set `mode` to `compute-instance`.
- Requires a `compute_name`.
  - If a compute instance with the same name exists, it uses the existing 
  compute instance and ignores other parameters.
  - If a compute instance with the same name doesn't exist, it creates a 
  new compute instance with the `compute_name`. For this process, you can 
  specify `compute_size` and `idle_type_before_shutdown_minutes`.

3. Compute Cluster
- Set `mode` to `compute-cluster`.
- Requires a `compute_name`.
  - If a compute cluster with the same name exists, it uses existing cluster, 
  ignores other parameters.
  - If a compute cluster with the same name doesn't exist, it creates a new 
  compute cluster. Additional parameters can be used for configuring this 
  process.

Here is an example how you can use the `AzureMLStepOperatorSettings` to define 
a compute instance:

```python
from zenml.integrations.azure.flavors import AzureMLStepOperatorSettings

azureml_settings = AzureMLStepOperatorSettings(
    mode="compute-instance",
    compute_name="MyComputeInstance",
    compute_size="Standard_NC6s_v3",
)

@step(
   settings={
       "step_operator": azureml_settings
   }
)
def my_azureml_step():
    # YOUR STEP CODE
    ...
```

You can check out the [AzureMLStepOperatorSettings SDK docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-azure/#zenml.integrations.azure.flavors.azureml\_step\_operator\_flavor.AzureMLStepOperatorSettings) for a full list of available attributes and [this docs page](../../how-to/pipeline-development/use-configuration-files/runtime-configuration.md) for more information on how to specify settings.

#### Enabling CUDA for GPU-backed hardware

Note that if you wish to use this step operator to run steps on a GPU, you will need to follow [the instructions on this page](../../how-to/pipeline-development/training-with-gpus/README.md) to ensure that it works. It requires adding some extra settings customization and is essential to enable CUDA for the GPU to give its full acceleration.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
