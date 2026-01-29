---
description: Orchestrating your pipelines to run on Vertex AI.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Google Cloud VertexAI Orchestrator

[Vertex AI Pipelines](https://cloud.google.com/vertex-ai/docs/pipelines/introduction) is a serverless ML workflow tool running on the Google Cloud Platform. It is an easy way to quickly run your code in a production-ready, repeatable cloud orchestrator that requires minimal setup without provisioning and paying for standby compute.

{% hint style="warning" %}
This component is only meant to be used within the context of a [remote ZenML deployment scenario](https://docs.zenml.io/getting-started/deploying-zenml/). Usage with a local ZenML deployment may lead to unexpected behavior!
{% endhint %}

## When to use it

You should use the Vertex orchestrator if:

* you're already using GCP.
* you're looking for a proven production-grade orchestrator.
* you're looking for a UI in which you can track your pipeline runs.
* you're looking for a managed solution for running your pipelines.
* you're looking for a serverless solution for running your pipelines.

## How to deploy it

{% hint style="info" %}
Would you like to skip ahead and deploy a full ZenML cloud stack already, including a Vertex AI orchestrator? Check out the[in-browser stack deployment wizard](https://docs.zenml.io/how-to/infrastructure-deployment/stack-deployment/deploy-a-cloud-stack), the [stack registration wizard](https://docs.zenml.io/how-to/infrastructure-deployment/stack-deployment/register-a-cloud-stack), or [the ZenML GCP Terraform module](https://docs.zenml.io/how-to/infrastructure-deployment/stack-deployment/deploy-a-cloud-stack-with-terraform) for a shortcut on how to deploy & register this stack component.
{% endhint %}

In order to use a Vertex AI orchestrator, you need to first deploy [ZenML to the cloud](https://docs.zenml.io/getting-started/deploying-zenml/). It would be recommended to deploy ZenML in the same Google Cloud project as where the Vertex infrastructure is deployed, but it is not necessary to do so. You must ensure that you are connected to the remote ZenML server before using this stack component.

The only other thing necessary to use the ZenML Vertex orchestrator is enabling Vertex-relevant APIs on the Google Cloud project.

## How to use it

To use the Vertex orchestrator, we need:

*   The ZenML `gcp` integration installed. If you haven't done so, run

    ```shell
    zenml integration install gcp
    ```
* [Docker](https://www.docker.com) installed and running.
* A [remote artifact store](https://docs.zenml.io/stacks/artifact-stores/) as part of your stack.
* A [remote container registry](https://docs.zenml.io/stacks/container-registries/) as part of your stack.
* [GCP credentials with proper permissions](vertex.md#gcp-credentials-and-permissions)
* The GCP project ID and location in which you want to run your Vertex AI pipelines.

### GCP credentials and permissions

This part is without doubt the most involved part of using the Vertex orchestrator. In order to run pipelines on Vertex AI, you need to have a GCP user account and/or one or more GCP service accounts set up with proper permissions, depending on whether you wish to practice [the principle of least privilege](https://cloud.google.com/iam/docs/using-iam-securely) and distribute permissions across multiple service accounts.

You also have three different options to provide credentials to the orchestrator:

* use the [`gcloud` CLI](https://cloud.google.com/sdk/gcloud) to authenticate locally with GCP
* configure the orchestrator to use a [service account key file](https://cloud.google.com/iam/docs/creating-managing-service-account-keys) to authenticate with GCP by setting the `service_account_path` parameter in the orchestrator configuration.
* (recommended) configure [a GCP Service Connector](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/gcp-service-connector) with GCP credentials and then link the Vertex AI Orchestrator stack component to the Service Connector.

This section [explains the different components and GCP resources](vertex.md#vertex-ai-pipeline-components) involved in running a Vertex AI pipeline and what permissions they need, then provides instructions for three different configuration use-cases:

1. [use the local `gcloud` CLI configured with your GCP user account](vertex.md#configuration-use-case-local-gcloud-cli-with-user-account), including the ability to schedule pipelines
2. [use a GCP Service Connector and a single service account](vertex.md#configuration-use-case-gcp-service-connector-with-single-service-account) with all permissions, including the ability to schedule pipelines
3. [use a GCP Service Connector and multiple service accounts](vertex.md#configuration-use-case-gcp-service-connector-with-different-service-accounts) for different permissions, including the ability to schedule pipelines

#### Vertex AI pipeline components

To understand what accounts you need to provision and why, let's look at the different components of the Vertex orchestrator:

1. _the ZenML client environment_ is the environment where you run the ZenML code responsible for building the pipeline Docker image and submitting the pipeline to Vertex AI, among other things. This is usually your local machine or some other environment used to automate running pipelines, like a CI/CD job. This environment needs to be able to authenticate with GCP and needs to have the necessary permissions to create a job in Vertex Pipelines, (e.g. [the `Vertex AI User` role](https://cloud.google.com/vertex-ai/docs/general/access-control#aiplatform.user)). If you are planning to [run pipelines on a schedule](vertex.md#run-pipelines-on-a-schedule), _the ZenML client environment_ also needs additional permissions:
   * the [`Storage Object Creator Role`](https://cloud.google.com/iam/docs/understanding-roles#storage.objectCreator) to be able to write the pipeline JSON file to the artifact store directly (NOTE: not needed if the Artifact Store is configured with credentials or is linked to Service Connector)
2. _the Vertex AI pipeline environment_ is the GCP environment in which the pipeline steps themselves are running in GCP. The Vertex AI pipeline runs in the context of a GCP service account which we'll call here _the workload service account_. _The workload service account_ can be explicitly configured in the orchestrator configuration via the `workload_service_account` parameter. If it is omitted, the orchestrator will use [the Compute Engine default service account](https://cloud.google.com/compute/docs/access/service-accounts#default_service_account) for the GCP project in which the pipeline is running. This service account needs to have the following permissions:
   * permissions to run a Vertex AI pipeline, (e.g. [the `Vertex AI Service Agent` role](https://cloud.google.com/vertex-ai/docs/general/access-control#aiplatform.serviceAgent)).

As you can see, there can be dedicated service accounts involved in running a Vertex AI pipeline. That's two service accounts if you also use a service account to authenticate to GCP in _the ZenML client environment_. However, you can keep it simple and use the same service account everywhere.

#### Configuration use-case: local `gcloud` CLI with user account

This configuration use-case assumes you have configured the [`gcloud` CLI](https://cloud.google.com/sdk/gcloud) to authenticate locally with your GCP account (i.e. by running `gcloud auth login`). It also assumes the following:

* your GCP account has permissions to create a job in Vertex Pipelines, (e.g. [the `Vertex AI User` role](https://cloud.google.com/vertex-ai/docs/general/access-control#aiplatform.user)).
* [the Compute Engine default service account](https://cloud.google.com/compute/docs/access/service-accounts#default_service_account) for the GCP project in which the pipeline is running is updated with additional permissions required to run a Vertex AI pipeline, (e.g. [the `Vertex AI Service Agent` role](https://cloud.google.com/vertex-ai/docs/general/access-control#aiplatform.serviceAgent)).

This is the easiest way to configure the Vertex AI Orchestrator, but it has the following drawbacks:

* the setup is not portable on other machines and reproducible by other users.
* it uses the Compute Engine default service account, which is not recommended, given that it has a lot of permissions by default and is used by many other GCP services.

We can then register the orchestrator as follows:

```shell
zenml orchestrator register <ORCHESTRATOR_NAME> \
    --flavor=vertex \
    --project=<PROJECT_ID> \
    --location=<GCP_LOCATION> \
    --synchronous=true
```

#### Configuration use-case: GCP Service Connector with single service account

This use-case assumes you have already configured a GCP service account with the following permissions:

* permissions to create a job in Vertex Pipelines, (e.g. [the `Vertex AI User` role](https://cloud.google.com/vertex-ai/docs/general/access-control#aiplatform.user)).
* permissions to run a Vertex AI pipeline, (e.g. [the `Vertex AI Service Agent` role](https://cloud.google.com/vertex-ai/docs/general/access-control#aiplatform.serviceAgent)).
* the [Storage Object Creator Role](https://cloud.google.com/iam/docs/understanding-roles#storage.objectCreator) to be able to write the pipeline JSON file to the artifact store directly.

It also assumes you have already created a service account key for this service account and downloaded it to your local machine (e.g. in a `connectors-vertex-ai.json` file). This is not recommended if you are conscious about security. The principle of least privilege is not applied here and the environment in which the pipeline steps are running has many permissions that it doesn't need.

```shell
zenml service-connector register <CONNECTOR_NAME> --type gcp --auth-method=service-account --project_id=<PROJECT_ID> --service_account_json=@connectors-vertex-ai.json --resource-type gcp-generic

zenml orchestrator register <ORCHESTRATOR_NAME> \
    --flavor=vertex \
    --location=<GCP_LOCATION> \
    --synchronous=true \
    --workload_service_account=<SERVICE_ACCOUNT_NAME>@<PROJECT_NAME>.iam.gserviceaccount.com 
    
zenml orchestrator connect <ORCHESTRATOR_NAME> --connector <CONNECTOR_NAME>
```

#### Configuration use-case: GCP Service Connector with different service accounts

This setup applies the principle of least privilege by using different service accounts with the minimum of permissions needed for [the different components involved in running a Vertex AI pipeline](vertex.md#vertex-ai-pipeline-components). It also uses a GCP Service Connector to make the setup portable and reproducible. This configuration is a best-in-class setup that you would normally use in production, but it requires a lot more work to prepare.

{% hint style="info" %}
This setup involves creating and configuring several GCP service accounts, which is a lot of work and can be error prone. If you don't really need the added security, you can use [the GCP Service Connector with a single service account](vertex.md#configuration-use-case-gcp-service-connector-with-single-service-account) instead.
{% endhint %}

The following GCP service accounts are needed:

1. a "client" service account that has the following permissions:
   * permissions to create a job in Vertex Pipelines, (e.g. [the `Vertex AI User` role](https://cloud.google.com/vertex-ai/docs/general/access-control#aiplatform.user)).
   * permissions to create a Google Cloud Function (e.g. with the [`Cloud Functions Developer Role`](https://cloud.google.com/functions/docs/reference/iam/roles#cloudfunctions.developer)).
   * the [Storage Object Creator Role](https://cloud.google.com/iam/docs/understanding-roles#storage.objectCreator) to be able to write the pipeline JSON file to the artifact store directly (NOTE: not needed if the Artifact Store is configured with credentials or is linked to Service Connector).
2. a "workload" service account that has permissions to run a Vertex AI pipeline, (e.g. [the `Vertex AI Service Agent` role](https://cloud.google.com/vertex-ai/docs/general/access-control#aiplatform.serviceAgent)).

{% hint style="info" %}
**Alternative: Custom Roles for Maximum Security** 

For even more granular control, you can create custom roles instead of using the predefined roles:

**Client Service Account Custom Permissions:**
- `aiplatform.pipelineJobs.create`
- `aiplatform.pipelineJobs.get` 
- `aiplatform.pipelineJobs.list`
- `cloudfunctions.functions.create`
- `storage.objects.create` (for artifact store access)

**Workload Service Account Custom Permissions:**
- `aiplatform.customJobs.create`
- `aiplatform.customJobs.get`
- `aiplatform.customJobs.list`
- `storage.objects.get`
- `storage.objects.create`

This provides the absolute minimum permissions required for Vertex AI pipeline operations.
{% endhint %}

A key is also needed for the "client" service account. You can create a key for this service account and download it to your local machine (e.g. in a `connectors-vertex-ai-client.json` file).

With all the service accounts and the key ready, we can register [the GCP Service Connector](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/gcp-service-connector) and Vertex AI orchestrator as follows:

```shell
zenml service-connector register <CONNECTOR_NAME> --type gcp --auth-method=service-account --project_id=<PROJECT_ID> --service_account_json=@connectors-vertex-ai-client.json --resource-type gcp-generic

zenml orchestrator register <ORCHESTRATOR_NAME> \
    --flavor=vertex \
    --location=<GCP_LOCATION> \
    --synchronous=true \
    --workload_service_account=<WORKLOAD_SERVICE_ACCOUNT_NAME>@<PROJECT_NAME>.iam.gserviceaccount.com 

zenml orchestrator connect <ORCHESTRATOR_NAME> --connector <CONNECTOR_NAME>
```

### Configuring the stack

With the orchestrator registered, we can use it in our active stack:

```shell
# Register and activate a stack with the new orchestrator
zenml stack register <STACK_NAME> -o <ORCHESTRATOR_NAME> ... --set
```

{% hint style="info" %}
ZenML will build a Docker image called `<CONTAINER_REGISTRY_URI>/zenml:<PIPELINE_NAME>` which includes your code and use it to run your pipeline steps in Vertex AI. Check out [this page](https://docs.zenml.io/how-to/customize-docker-builds/) if you want to learn more about how ZenML builds these images and how you can customize them.
{% endhint %}

You can now run any ZenML pipeline using the Vertex orchestrator:

```shell
python file_that_runs_a_zenml_pipeline.py
```

### Vertex UI

Vertex comes with its own UI that you can use to find further details about your pipeline runs, such as the logs of your steps.

![Vertex UI](../../.gitbook/assets/VertexUI.png)

For any runs executed on Vertex, you can get the URL to the Vertex UI in Python using the following code snippet:

```python
from zenml.client import Client

pipeline_run = Client().get_pipeline_run("<PIPELINE_RUN_NAME>")
orchestrator_url = pipeline_run.run_metadata["orchestrator_url"]
```

### Run pipelines on a schedule

The Vertex Pipelines orchestrator supports running pipelines on a schedule using its [native scheduling capability](https://cloud.google.com/vertex-ai/docs/pipelines/schedule-pipeline-run).

**How to schedule a pipeline**

```python
from datetime import datetime, timedelta

from zenml import pipeline
from zenml.config.schedule import Schedule

@pipeline
def first_pipeline():
    ...

# Run a pipeline every 5th minute
first_pipeline = first_pipeline.with_options(
    schedule=Schedule(
        cron_expression="*/5 * * * *"
    )
)
first_pipeline()

@pipeline
def second_pipeline():
    ...

# Run a pipeline every hour
# starting in one day from now and ending in three days from now
second_pipeline = second_pipeline.with_options(
    schedule=Schedule(
        cron_expression="0 * * * *",
        start_time=datetime.now() + timedelta(days=1),
        end_time=datetime.now() + timedelta(days=3),
    )
)
second_pipeline()
```

{% hint style="warning" %}
The Vertex orchestrator only supports the `cron_expression`, `start_time` (optional) and `end_time` (optional) parameters in the `Schedule` object, and will ignore all other parameters supplied to define the schedule.
{% endhint %}

The `start_time` and `end_time` timestamp parameters are both optional and are to be specified in local time. They define the time window in which the pipeline runs will be triggered. If they are not specified, the pipeline will run indefinitely.

The `cron_expression` parameter [supports timezones](https://cloud.google.com/vertex-ai/docs/reference/rest/v1beta1/projects.locations.schedules). For example, the expression `TZ=Europe/Paris 0 10 * * *` will trigger runs at 10:00 in the Europe/Paris timezone.

**How to update/delete a scheduled pipeline**

Note that ZenML only gets involved to schedule a run, but maintaining the lifecycle of the schedule is the responsibility of the user.

In order to cancel a scheduled Vertex pipeline, you need to manually delete the schedule in VertexAI (via the UI or the CLI). Here is an example (WARNING: Will delete all schedules if you run this):

```python
from google.cloud import aiplatform
from zenml.client import Client

def delete_all_schedules():
    # Initialize ZenML client
    zenml_client = Client()
    # Get all ZenML schedules
    zenml_schedules = zenml_client.list_schedules()
    
    if not zenml_schedules:
        print("No ZenML schedules to delete.")
        return
    
    print(f"\nFound {len(zenml_schedules)} ZenML schedules to process...\n")
    
    # Process each ZenML schedule
    for zenml_schedule in zenml_schedules:
        schedule_name = zenml_schedule.name
        print(f"Processing ZenML schedule: {schedule_name}")
        
        try:
            # First delete the corresponding Vertex AI schedule
            vertex_filter = f'display_name="{schedule_name}"'
            vertex_schedules = aiplatform.PipelineJobSchedule.list(
                filter=vertex_filter,
                order_by='create_time desc',
                location='europe-west1'
            )
            
            if vertex_schedules:
                print(f"  Found {len(vertex_schedules)} matching Vertex schedules")
                for vertex_schedule in vertex_schedules:
                    try:
                        vertex_schedule.delete()
                        print(f"  ✓ Deleted Vertex schedule: {vertex_schedule.display_name}")
                    except Exception as e:
                        print(f"  ✗ Failed to delete Vertex schedule {vertex_schedule.display_name}: {e}")
            else:
                print(f"  No matching Vertex schedules found for {schedule_name}")
            
            # Then delete the ZenML schedule
            zenml_client.delete_schedule(zenml_schedule.id)
            print(f"  ✓ Deleted ZenML schedule: {schedule_name}")
            
        except Exception as e:
            print(f"  ✗ Failed to process {schedule_name}: {e}")
    
    print("\nSchedule cleanup completed!")

if __name__ == "__main__":
    delete_all_schedules()
```

### Additional configuration

For additional configuration of the Vertex orchestrator, you can pass `VertexOrchestratorSettings` which allows you to configure labels for your Vertex Pipeline jobs or specify which GPU to use.

```python
from zenml.integrations.gcp.flavors.vertex_orchestrator_flavor import (
   VertexOrchestratorSettings
)

vertex_settings = VertexOrchestratorSettings(labels={"key": "value"})
```

If your pipelines steps have certain hardware requirements, you can specify them as `ResourceSettings`:

```python
from zenml.config import ResourceSettings

resource_settings = ResourceSettings(cpu_count=8, memory="16GB")
```

To run your pipeline (or some steps of it) on a GPU, you will need to set both a node selector and the GPU count as follows:

```python
from zenml import step, pipeline

from zenml.config import ResourceSettings
from zenml.integrations.gcp.flavors.vertex_orchestrator_flavor import (
    VertexOrchestratorSettings
)

vertex_settings = VertexOrchestratorSettings(
    pod_settings={
        "node_selectors": {
            "cloud.google.com/gke-accelerator": "NVIDIA_TESLA_A100"
        },
    }
)
resource_settings = ResourceSettings(gpu_count=1)

# Either specify settings on step-level
@step(
    settings={
        "orchestrator": vertex_settings,
        "resources": resource_settings,
    }
)
def my_step():
    ...

# OR specify on pipeline-level
@pipeline(
    settings={
        "orchestrator": vertex_settings,
        "resources": resource_settings,
    }
)
def my_pipeline():
    ...
```

You can find available accelerator types [here](https://cloud.google.com/vertex-ai/docs/training/configure-compute#specifying_gpus).

### Using Custom Job Parameters

For more advanced hardware configuration, you can use `VertexCustomJobParameters` to customize each step's execution environment. This allows you to specify detailed requirements like boot disk size, accelerator type, machine type, and more without needing a separate step operator.

```python
from zenml.integrations.gcp.vertex_custom_job_parameters import (
    VertexCustomJobParameters,
)
from zenml import step, pipeline
from zenml.integrations.gcp.flavors.vertex_orchestrator_flavor import (
    VertexOrchestratorSettings
)

# Create settings with a larger boot disk (1TB)
large_disk_settings = VertexOrchestratorSettings(
    custom_job_parameters=VertexCustomJobParameters(
        boot_disk_size_gb=1000,  # 1TB disk
        boot_disk_type="pd-standard",  # Standard persistent disk (cheaper)
        machine_type="n1-standard-8"
    )
)

# Create settings with GPU acceleration
gpu_settings = VertexOrchestratorSettings(
    custom_job_parameters=VertexCustomJobParameters(
        accelerator_type="NVIDIA_TESLA_A100",
        accelerator_count=1,
        machine_type="n1-standard-8",
        boot_disk_size_gb=200  # Larger disk for GPU workloads
    )
)

# Step that needs a large disk but no GPU
@step(settings={"orchestrator": large_disk_settings})
def data_processing_step():
    # Process large datasets that require a lot of disk space
    ...

# Step that needs GPU acceleration
@step(settings={"orchestrator": gpu_settings})
def training_step():
    # Train ML model using GPU
    ...

# Define pipeline that uses both steps
@pipeline()
def my_pipeline():
    data = data_processing_step()
    model = training_step(data)
    ...
```

You can also specify these parameters at pipeline level to apply them to all steps:

```python
@pipeline(
    settings={
        "orchestrator": VertexOrchestratorSettings(
            custom_job_parameters=VertexCustomJobParameters(
                boot_disk_size_gb=500,  # 500GB disk for all steps
                machine_type="n1-standard-4"
            )
        )
    }
)
def my_pipeline():
    ...
```

The `VertexCustomJobParameters` supports the following common configuration options:

| Parameter | Description |
|-----------|-------------|
| boot_disk_size_gb | Size of the boot disk in GB (default: 100) |
| boot_disk_type | Type of disk ("pd-standard", "pd-ssd", etc.) |
| machine_type | Machine type for computation (e.g., "n1-standard-4") |
| accelerator_type | Type of accelerator (e.g., "NVIDIA_TESLA_T4", "NVIDIA_TESLA_A100") |
| accelerator_count | Number of accelerators to attach |
| service_account | Service account to use for the job |
| persistent_resource_id | ID of persistent resource for faster job startup |

#### Advanced Custom Job Parameters

For advanced scenarios, you can use `additional_training_job_args` to pass additional parameters directly to the underlying Google Cloud Pipeline Components library:

```python
@step(
    settings={
        "orchestrator": VertexOrchestratorSettings(
            custom_job_parameters=VertexCustomJobParameters(
                machine_type="n1-standard-8",
                # Advanced parameters passed directly to create_custom_training_job_from_component
                additional_training_job_args={
                    "timeout": "86400s",  # 24 hour timeout
                    "network": "projects/12345/global/networks/my-vpc",
                    "enable_web_access": True,
                    "reserved_ip_ranges": ["192.168.0.0/16"],
                    "base_output_directory": "gs://my-bucket/outputs",
                    "labels": {"team": "ml-research", "project": "image-classification"}
                }
            )
        )
    }
)
def my_advanced_step():
    ...
```

These advanced parameters are passed directly to the Google Cloud Pipeline Components library's [`create_custom_training_job_from_component`](https://google-cloud-pipeline-components.readthedocs.io/en/google-cloud-pipeline-components-2.19.0/api/v1/custom_job.html#v1.custom_job.create_custom_training_job_from_component) function. This approach lets you access new features of the Google API without requiring ZenML updates.

{% hint style="warning" %}
If you specify parameters in `additional_training_job_args` that are also defined as explicit attributes (like `machine_type` or `boot_disk_size_gb`), the values in `additional_training_job_args` will override the explicit values. For example:

```python
VertexCustomJobParameters(
    machine_type="n1-standard-4",  # This will be overridden
    additional_training_job_args={
        "machine_type": "n1-standard-16"  # This takes precedence
    }
)
```

The resulting machine type will be "n1-standard-16". When this happens, ZenML will log a warning at runtime to alert you of the parameter override, which helps avoid confusion about which configuration values are actually being used.
{% endhint %}

{% hint style="info" %}
When using `custom_job_parameters`, ZenML automatically applies certain configurations from your orchestrator:

- **Network Configuration**: If you've set `network` in your Vertex orchestrator configuration, it will be automatically applied to all custom jobs unless you explicitly override it in `additional_training_job_args`.

- **Encryption Specification**: If you've set `encryption_spec_key_name` in your orchestrator configuration, it will be applied to custom jobs for consistent encryption.

- **Service Account**: For non-persistent resource jobs, if no service account is specified in the custom job parameters, the `workload_service_account` from the orchestrator configuration will be used.

This inheritance mechanism ensures consistent configuration across your pipeline steps, maintaining connectivity to GCP resources (like databases), security settings, and compute resources without requiring manual specification for each step.
{% endhint %}

For a complete list of parameters supported by the underlying function, refer to the [Google Pipeline Components SDK V1 docs](https://google-cloud-pipeline-components.readthedocs.io/en/google-cloud-pipeline-components-2.19.0/api/v1/custom_job.html#v1.custom_job.create_custom_training_job_from_component).

Note that when using custom job parameters with `persistent_resource_id`, you must always specify a `service_account` as well.

{% hint style="info" %}
The `additional_training_job_args` field provides future-proofing for your ZenML pipelines. If Google adds new parameters to their API, you can immediately use them without waiting for ZenML updates. This is especially useful for accessing new hardware configurations, networking features, or security settings as they become available.
{% endhint %}

### Enabling CUDA for GPU-backed hardware

Note that if you wish to use this orchestrator to run steps on a GPU, you will need to follow [the instructions on this page](https://docs.zenml.io/user-guides/tutorial/distributed-training/) to ensure that it works. It requires adding some extra settings customization and is essential to enable CUDA for the GPU to give its full acceleration.

### Using Persistent Resources for Faster Development

When developing ML pipelines that use Vertex AI, the startup time for each step can be significant since Vertex needs to provision new compute resources for each run. To speed up development iterations, you can use Vertex AI's [Persistent Resources](https://cloud.google.com/vertex-ai/docs/training/persistent-resource-overview) feature, which keeps compute resources warm between runs.

To use persistent resources with the Vertex orchestrator, you first need to create a persistent resource using the GCP Cloud UI, or by [following instructions in the GCP docs](https://cloud.google.com/vertex-ai/docs/training/persistent-resource-create). Next, you'll need to configure your orchestrator to run on the persistent resource. This can be done either through the dashboard or CLI in which case it applies to all pipelines that will be run using this orchestrator, or dynamically in code for a specific pipeline or even just single steps.

{% hint style="warning" %}
Note that a service account with permissions to access the persistent resource is mandatory, so make sure to always include it in the configuration:
{% endhint %}

#### Configure the orchestrator using the CLI

```bash
# You can also use `zenml orchestrator update`
zenml orchestrator register <NAME> -f vertex --custom_job_parameters='{"persistent_resource_id": "<PERSISTENT_RESOURCE_ID>", "service_account": "<SERVICE_ACCOUNT_NAME>", "machine_type": "n1-standard-4", "boot_disk_type": "pd-standard"}'
```

#### Configure the orchestrator using the dashboard

Navigate to the `Stacks` section in your ZenML dashboard and either create a new Vertex orchestrator or update an existing one. During the creation/update, set the persistent resource ID and other values in the `custom_job_parameters` attribute.

#### Configure the orchestrator dynamically in code

```python
from zenml.integrations.gcp.vertex_custom_job_parameters import (
    VertexCustomJobParameters,
)
from zenml.integrations.gcp.flavors.vertex_orchestrator_flavor import (
    VertexOrchestratorSettings
)

# Configure for the pipeline which applies to all steps
@pipeline(
    settings={
        "orchestrator": VertexOrchestratorSettings(
            custom_job_parameters=VertexCustomJobParameters(
                persistent_resource_id="<PERSISTENT_RESOURCE_ID>",
                service_account="<SERVICE_ACCOUNT_NAME>",
                machine_type="n1-standard-4",
                boot_disk_type="pd-standard"
            )
        )
    }
)
def my_pipeline():
    ...


# Configure for a single step
@step(
    settings={
        "orchestrator": VertexOrchestratorSettings(
            custom_job_parameters=VertexCustomJobParameters(
                persistent_resource_id="<PERSISTENT_RESOURCE_ID>",
                service_account="<SERVICE_ACCOUNT_NAME>",
                machine_type="n1-standard-4",
                boot_disk_type="pd-standard"
            )
        )
    }
)
def my_step():
    ...
```

If you need to explicitly specify that no persistent resource should be used, set `persistent_resource_id` to an empty string:

```python
@step(
    settings={
        "orchestrator": VertexOrchestratorSettings(
            custom_job_parameters=VertexCustomJobParameters(
                persistent_resource_id="",  # Explicitly not using a persistent resource
                boot_disk_size_gb=1000,  # Set a large disk
                machine_type="n1-standard-8"
            )
        )
    }
)
def my_step():
    ...
```

Using a persistent resource is particularly useful when you're developing locally and want to iterate quickly on steps that need cloud resources. The startup time of the job can be extremely quick.

{% hint style="warning" %}
When using persistent resources (`persistent_resource_id` specified), you **must** always include a `service_account`. Conversely, when explicitly setting `persistent_resource_id=""` to avoid using persistent resources, ZenML will automatically set the service account to an empty string to avoid Vertex API errors - so don't set the service account in this case.
{% endhint %}

{% hint style="warning" %}
Remember that persistent resources continue to incur costs as long as they're running, even when idle. Make sure to monitor your usage and configure appropriate idle timeout periods.
{% endhint %}
