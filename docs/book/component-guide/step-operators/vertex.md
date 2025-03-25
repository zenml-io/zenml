---
description: Executing individual steps in Vertex AI.
---

# Google Cloud VertexAI

[Vertex AI](https://cloud.google.com/vertex-ai) offers specialized compute instances to run your training jobs and has a comprehensive UI to track and manage your models and logs. ZenML's Vertex AI step operator allows you to submit individual steps to be run on Vertex AI compute instances.

### When to use it

You should use the Vertex step operator if:

* one or more steps of your pipeline require computing resources (CPU, GPU, memory) that are not provided by your orchestrator.
* you have access to Vertex AI. If you're using a different cloud provider, take a look at the [SageMaker](sagemaker.md) or [AzureML](azureml.md) step operators.

### How to deploy it

* Enable Vertex AI [here](https://console.cloud.google.com/vertex-ai).
* Create a [service account](https://cloud.google.com/iam/docs/service-accounts) with the right permissions to create Vertex AI jobs (`roles/aiplatform.admin`) and push to the container registry (`roles/storage.admin`).

### How to use it

To use the Vertex step operator, we need:

*   The ZenML `gcp` integration installed. If you haven't done so, run

    ```shell
    zenml integration install gcp
    ```
* [Docker](https://www.docker.com) installed and running.
* Vertex AI enabled and a service account file. See the [deployment section](vertex.md#how-to-deploy-it) for detailed instructions.
* A [GCR container registry](https://docs.zenml.io/stacks/container-registries/gcp) as part of our stack.
* (Optional) A machine type that we want to execute our steps on (this defaults to `n1-standard-4`). See [here](https://cloud.google.com/vertex-ai/docs/training/configure-compute#machine-types) for a list of available machine types.
* A [remote artifact store](https://docs.zenml.io/stacks/artifact-stores/) as part of your stack. This is needed so that both your orchestration environment and VertexAI can read and write step artifacts. Check out the documentation page of the artifact store you want to use for more information on how to set that up and configure authentication for it.

You have three different options to provide GCP credentials to the step operator:

*   use the [`gcloud` CLI](https://cloud.google.com/sdk/gcloud) to authenticate locally with GCP. This only works in combination with the local orchestrator.

    ```shell
    gcloud auth login

    zenml step-operator register <STEP_OPERATOR_NAME> \
        --flavor=vertex \
        --project=<GCP_PROJECT> \
        --region=<REGION> \
    #   --machine_type=<MACHINE_TYPE> # optionally specify the type of machine to run on
    ```
*   configure the orchestrator to use a [service account key file](https://cloud.google.com/iam/docs/creating-managing-service-account-keys) to authenticate with GCP by setting the `service_account_path` parameter in the orchestrator configuration to point to a service account key file. This also works only in combination with the local orchestrator.

    ```shell
    zenml step-operator register <STEP_OPERATOR_NAME> \
        --flavor=vertex \
        --project=<GCP_PROJECT> \
        --region=<REGION> \
        --service_account_path=<SERVICE_ACCOUNT_PATH> \
    #   --machine_type=<MACHINE_TYPE> # optionally specify the type of machine to run on
    ```
*   (recommended) configure [a GCP Service Connector](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/gcp-service-connector) with GCP credentials coming from a [service account key file](https://cloud.google.com/iam/docs/creating-managing-service-account-keys) or the local `gcloud` CLI set up with user account credentials and then link the Vertex AI Step Operator stack component to the Service Connector. This option works with any orchestrator.

    ```shell
    zenml service-connector register <CONNECTOR_NAME> --type gcp --auth-method=service-account --project_id=<PROJECT_ID> --service_account_json=@<SERVICE_ACCOUNT_PATH> --resource-type gcp-generic

    # Or, as an alternative, you could use the GCP user account locally set up with gcloud
    # zenml service-connector register <CONNECTOR_NAME> --type gcp --resource-type gcp-generic --auto-configure

    zenml step-operator register <STEP_OPERATOR_NAME> \
        --flavor=vertex \
        --region=<REGION> \
    #   --machine_type=<MACHINE_TYPE> # optionally specify the type of machine to run on

    zenml step-operator connect <STEP_OPERATOR_NAME> --connector <CONNECTOR_NAME>
    ```

We can then use the registered step operator in our active stack:

```shell
# Add the step operator to the active stack
zenml stack update -s <NAME>
```

Once you added the step operator to your active stack, you can use it to execute individual steps of your pipeline by specifying it in the `@step` decorator as follows:

```python
from zenml import step


@step(step_operator=<NAME>)
def trainer(...) -> ...:
    """Train a model."""
    # This step will be executed in Vertex.
```

{% hint style="info" %}
ZenML will build a Docker image called `<CONTAINER_REGISTRY_URI>/zenml:<PIPELINE_NAME>` which includes your code and use it to run your steps in Vertex AI. Check out [this page](https://docs.zenml.io/how-to/customize-docker-builds/) if you want to learn more about how ZenML builds these images and how you can customize them.
{% endhint %}

#### Additional configuration

You can specify the service account, network and reserved IP ranges to use for the VertexAI `CustomJob` by passing the `service_account`, `network` and `reserved_ip_ranges` parameters to the `step-operator register` command:

```shell
    zenml step-operator register <STEP_OPERATOR_NAME> \
        --flavor=vertex \
        --project=<GCP_PROJECT> \
        --region=<REGION> \
        --service_account=<SERVICE_ACCOUNT> # optionally specify the service account to use for the VertexAI CustomJob
        --network=<NETWORK> # optionally specify the network to use for the VertexAI CustomJob
        --reserved_ip_ranges=<RESERVED_IP_RANGES> # optionally specify the reserved IP range to use for the VertexAI CustomJob
```

For additional configuration of the Vertex step operator, you can pass `VertexStepOperatorSettings` when defining or running your pipeline.

```python
from zenml import step
from zenml.integrations.gcp.flavors.vertex_step_operator_flavor import VertexStepOperatorSettings

@step(step_operator=<STEP_OPERATOR_NAME>, settings={"step_operator": VertexStepOperatorSettings(
    accelerator_type= "NVIDIA_TESLA_T4",  # see https://cloud.google.com/vertex-ai/docs/reference/rest/v1/MachineSpec#AcceleratorType
    accelerator_count = 1,
    machine_type = "n1-standard-2",       # see https://cloud.google.com/vertex-ai/docs/training/configure-compute#machine-types
    disk_type = "pd-ssd",                 # see https://cloud.google.com/vertex-ai/docs/training/configure-storage#disk-types
    disk_size_gb = 100,                   # see https://cloud.google.com/vertex-ai/docs/training/configure-storage#disk-size
)})
def trainer(...) -> ...:
    """Train a model."""
    # This step will be executed in Vertex.
```

Check out the [SDK docs](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-gcp.html#zenml.integrations.gcp) for a full list of available attributes and [this docs page](https://docs.zenml.io/how-to/pipeline-development/use-configuration-files/runtime-configuration) for more information on how to specify settings.

For more information and a full list of configurable attributes of the Vertex step operator, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-gcp.html#zenml.integrations.gcp) .

#### Enabling CUDA for GPU-backed hardware

Note that if you wish to use this step operator to run steps on a GPU, you will need to follow [the instructions on this page](https://docs.zenml.io/how-to/pipeline-development/training-with-gpus/) to ensure that it works. It requires adding some extra settings customization and is essential to enable CUDA for the GPU to give its full acceleration.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>

#### Using Persistent Resources for Faster Development

When developing ML pipelines that use Vertex AI, the startup time for each `CustomJob` can be significant since Vertex needs to provision new compute resources for each run. To speed up development iterations, you can use Vertex AI's [Persistent Resources](https://cloud.google.com/vertex-ai/docs/training/persistent-resource-overview) feature, which keeps compute resources warm between runs.

To use persistent resources with the Vertex step operator, you need to do the following:

**Step 1**: You create a persistent resource using the GCP Cloud UI, or by [following instructions in the GCP docs](https://cloud.google.com/vertex-ai/docs/training/persistent-resource-create).

**Step 2**: Make sure your step operator is properly configured. For example, you need to have a service account specified in your step operator configuration. This service account needs to have permissions to access the persistent resource.

```bash
# You can also use `zenml step-operator update`
zenml step-operator register <STEP_OPERATOR_NAME> -f vertex --service_account=<A_SERVICE_ACCOUNT_THAT_HAS_THE_RIGHT_PERMISSIONS_TO_ACCESS_PERSISTENT_STORAGE>
```

{% hint style="warning" %}
Please note that by default, ZenML step operators are registered with `boot_disk_type=pd-ssd` and persistent storages usually come with `boot_disk_type=pd-standard`. To avoid confusion, execute the following:

```shell
zenml step-operator update <STEP_OPERATOR_NAME> --boot_disk_type=pd-standard
```

Or ensure that your worker pool configuration in your persistent storage matches that of your ZenML step operator.
{% endhint %}

**Step 3**: Configure your code to use the persistent resource:

```python
from zenml.integrations.gcp.flavors.vertex_step_operator_flavor import VertexStepOperatorSettings

@step(step_operator=<STEP_OPERATOR_NAME>, settings={"step_operator": VertexStepOperatorSettings(
    persistent_resource_id="my-persistent-resource",  # specify your persistent resource ID
    machine_type="n1-standard-4",
    accelerator_type="NVIDIA_TESLA_T4",
    accelerator_count=1,
)})
def trainer(...) -> ...:
    """Train a model."""
    # This step will use the persistent resource and start faster
```

Using a persistent resource is particularly useful when you're developing locally and want to iterate quickly on steps that need cloud resources. The startup time of the job can be extremely quick.

{% hint style="warning" %}
Remember that persistent resources continue to incur costs as long as they're running, even when idle. Make sure to monitor your usage and configure appropriate idle timeout periods.
{% endhint %}
