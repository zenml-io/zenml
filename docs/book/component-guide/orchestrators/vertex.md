---
description: Orchestrating your pipelines to run on Vertex AI.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Google Cloud VertexAI Orchestrator

[Vertex AI Pipelines](https://cloud.google.com/vertex-ai/docs/pipelines/introduction) is a serverless ML workflow tool running on the Google Cloud Platform. It is an easy way to quickly run your code in a production-ready, repeatable cloud orchestrator that requires minimal setup without provisioning and paying for standby compute.

{% hint style="warning" %}
This component is only meant to be used within the context of a [remote ZenML deployment scenario](../../getting-started/deploying-zenml/README.md). Usage with a local ZenML deployment may lead to unexpected behavior!
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
Would you like to skip ahead and deploy a full ZenML cloud stack already,
including a Vertex AI orchestrator? Check out the
[in-browser stack deployment wizard](../../how-to/stack-deployment/deploy-a-cloud-stack.md),
the [stack registration wizard](../../how-to/stack-deployment/register-a-cloud-stack.md),
or [the ZenML GCP Terraform module](../../how-to/stack-deployment/deploy-a-cloud-stack-with-terraform.md)
for a shortcut on how to deploy & register this stack component.
{% endhint %}

In order to use a Vertex AI orchestrator, you need to first deploy [ZenML to the cloud](../../getting-started/deploying-zenml/README.md). It would be recommended to deploy ZenML in the same Google Cloud project as where the Vertex infrastructure is deployed, but it is not necessary to do so. You must ensure that you are connected to the remote ZenML server before using this stack component.

The only other thing necessary to use the ZenML Vertex orchestrator is enabling Vertex-relevant APIs on the Google Cloud project.

In order to quickly enable APIs, and create other resources necessary for using this integration, you can also consider using [mlstacks](https://mlstacks.zenml.io/vertex), which helps you set up the infrastructure with one click.

## How to use it

To use the Vertex orchestrator, we need:

*   The ZenML `gcp` integration installed. If you haven't done so, run

    ```shell
    zenml integration install gcp
    ```
* [Docker](https://www.docker.com) installed and running.
* A [remote artifact store](../artifact-stores/artifact-stores.md) as part of your stack.
* A [remote container registry](../container-registries/container-registries.md) as part of your stack.
* [GCP credentials with proper permissions](vertex.md#gcp-credentials-and-permissions)
* The GCP project ID and location in which you want to run your Vertex AI pipelines.

### GCP credentials and permissions

This part is without doubt the most involved part of using the Vertex orchestrator. In order to run pipelines on Vertex AI, you need to have a GCP user account and/or one or more GCP service accounts set up with proper permissions, depending on whether you wish to practice [the principle of least privilege](https://en.wikipedia.org/wiki/Principle\_of\_least\_privilege) and distribute permissions across multiple service accounts.

You also have three different options to provide credentials to the orchestrator:

* use the [`gcloud` CLI](https://cloud.google.com/sdk/gcloud) to authenticate locally with GCP
* configure the orchestrator to use a [service account key file](https://cloud.google.com/iam/docs/creating-managing-service-account-keys) to authenticate with GCP by setting the `service_account_path` parameter in the orchestrator configuration.
* (recommended) configure [a GCP Service Connector](../../how-to/auth-management/gcp-service-connector.md) with GCP credentials and then link the Vertex AI Orchestrator stack component to the Service Connector.

This section [explains the different components and GCP resources](vertex.md#vertex-ai-pipeline-components) involved in running a Vertex AI pipeline and what permissions they need, then provides instructions for three different configuration use-cases:

1. [use the local `gcloud` CLI configured with your GCP user account](vertex.md#configuration-use-case-local-gcloud-cli-with-user-account), including the ability to schedule pipelines
2. [use a GCP Service Connector and a single service account](vertex.md#configuration-use-case-gcp-service-connector-with-single-service-account) with all permissions, including the ability to schedule pipelines
3. [use a GCP Service Connector and multiple service accounts](vertex.md#configuration-use-case-gcp-service-connector-with-different-service-accounts) for different permissions, including the ability to schedule pipelines

#### Vertex AI pipeline components

To understand what accounts you need to provision and why, let's look at the different components of the Vertex orchestrator:

1. _the ZenML client environment_ is the environment where you run the ZenML code responsible for building the pipeline Docker image and submitting the pipeline to Vertex AI, among other things. This is usually your local machine or some other environment used to automate running pipelines, like a CI/CD job. This environment needs to be able to authenticate with GCP and needs to have the necessary permissions to create a job in Vertex Pipelines, (e.g. [the `Vertex AI User` role](https://cloud.google.com/vertex-ai/docs/general/access-control#aiplatform.user)). If you are planning to [run pipelines on a schedule](vertex.md#run-pipelines-on-a-schedule), _the ZenML client environment_ also needs additional permissions:
   * the [`Storage Object Creator Role`](https://cloud.google.com/iam/docs/understanding-roles#storage.objectCreator) to be able to write the pipeline JSON file to the artifact store directly (NOTE: not needed if the Artifact Store is configured with credentials or is linked to Service Connector)
2. _the Vertex AI pipeline environment_ is the GCP environment in which the pipeline steps themselves are running in GCP. The Vertex AI pipeline runs in the context of a GCP service account which we'll call here _the workload service account_. _The workload service account_ can be explicitly configured in the orchestrator configuration via the `workload_service_account` parameter. If it is omitted, the orchestrator will use [the Compute Engine default service account](https://cloud.google.com/compute/docs/access/service-accounts#default\_service\_account) for the GCP project in which the pipeline is running. This service account needs to have the following permissions:
   * permissions to run a Vertex AI pipeline, (e.g. [the `Vertex AI Service Agent` role](https://cloud.google.com/vertex-ai/docs/general/access-control#aiplatform.serviceAgent)).

As you can see, there can be dedicated service accounts involved in running a Vertex AI pipeline. That's two service accounts if you also use a service account to authenticate to GCP in _the ZenML client environment_. However, you can keep it simple and use the same service account everywhere.

#### Configuration use-case: local `gcloud` CLI with user account

This configuration use-case assumes you have configured the [`gcloud` CLI](https://cloud.google.com/sdk/gcloud) to authenticate locally with your GCP account (i.e. by running `gcloud auth login`). It also assumes the following:

* your GCP account has permissions to create a job in Vertex Pipelines, (e.g. [the `Vertex AI User` role](https://cloud.google.com/vertex-ai/docs/general/access-control#aiplatform.user)).
* [the Compute Engine default service account](https://cloud.google.com/compute/docs/access/service-accounts#default\_service\_account) for the GCP project in which the pipeline is running is updated with additional permissions required to run a Vertex AI pipeline, (e.g. [the `Vertex AI Service Agent` role](https://cloud.google.com/vertex-ai/docs/general/access-control#aiplatform.serviceAgent)).

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

It also assumes you have already created a service account key for this service account and downloaded it to your local machine (e.g. in a `connectors-vertex-ai-workload.json` file). This is not recommended if you are conscious about security. The principle of least privilege is not applied here and the environment in which the pipeline steps are running has many permissions that it doesn't need.

```shell
zenml service-connector register <CONNECTOR_NAME> --type gcp --auth-method=service-account --project_id=<PROJECT_ID> --service_account_json=@connectors-vertex-ai-workload.json --resource-type gcp-generic

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

A key is also needed for the "client" service account. You can create a key for this service account and download it to your local machine (e.g. in a `connectors-vertex-ai-workload.json` file).

With all the service accounts and the key ready, we can register [the GCP Service Connector](../../how-to/auth-management/gcp-service-connector.md) and Vertex AI orchestrator as follows:

```shell
zenml service-connector register <CONNECTOR_NAME> --type gcp --auth-method=service-account --project_id=<PROJECT_ID> --service_account_json=@connectors-vertex-ai-workload.json --resource-type gcp-generic

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
ZenML will build a Docker image called `<CONTAINER_REGISTRY_URI>/zenml:<PIPELINE_NAME>` which includes your code and use it to run your pipeline steps in Vertex AI. Check out [this page](../../how-to/customize-docker-builds/README.md) if you want to learn more about how ZenML builds these images and how you can customize them.
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
orchestrator_url = pipeline_run.run_metadata["orchestrator_url"].value
```

### Run pipelines on a schedule

The Vertex Pipelines orchestrator supports running pipelines on a schedule using its [native scheduling capability](https://cloud.google.com/vertex-ai/docs/pipelines/schedule-pipeline-run).

**How to schedule a pipeline**

```python
from zenml.config.schedule import Schedule

# Run a pipeline every 5th minute
pipeline_instance.run(
    schedule=Schedule(
        cron_expression="*/5 * * * *"
    )
)

# Run a pipeline every hour
# starting in one day from now and ending in three days from now
pipeline_instance.run(
    schedule=Schedule(
        cron_expression="0 * * * *"
        start_time=datetime.datetime.now() + datetime.timedelta(days=1),
        end_time=datetime.datetime.now() + datetime.timedelta(days=3),
    )
)
```

{% hint style="warning" %}
The Vertex orchestrator only supports the `cron_expression`, `start_time` (optional) and `end_time` (optional) parameters in the `Schedule` object, and will ignore all other parameters supplied to define the schedule.
{% endhint %}

The `start_time` and `end_time` timestamp parameters are both optional and are to be specified in local time. They define the time window in which the pipeline runs will be triggered. If they are not specified, the pipeline will run indefinitely.

The `cron_expression` parameter [supports timezones](https://cloud.google.com/vertex-ai/docs/reference/rest/v1beta1/projects.locations.schedules). For example, the expression `TZ=Europe/Paris 0 10 * * *` will trigger runs at 10:00 in the Europe/Paris timezone.

**How to delete a scheduled pipeline**

Note that ZenML only gets involved to schedule a run, but maintaining the lifecycle of the schedule is the responsibility of the user.

In order to cancel a scheduled Vertex pipeline, you need to manually delete the schedule in VertexAI (via the UI or the CLI).

### Additional configuration

For additional configuration of the Vertex orchestrator, you can pass `VertexOrchestratorSettings` which allows you to configure labels for your Vertex Pipeline jobs or specify which GPU to use.

```python
from zenml.integrations.gcp.flavors.vertex_orchestrator_flavor import VertexOrchestratorSettings
from kubernetes.client.models import V1Toleration

vertex_settings = VertexOrchestratorSettings(
    labels={"key": "value"}
)
```

If your pipelines steps have certain hardware requirements, you can specify them as `ResourceSettings`:

```python
resource_settings = ResourceSettings(cpu_count=8, memory="16GB")
```

To run your pipeline (or some steps of it) on a GPU, you will need to set both a node selector
and the gpu count as follows:
```python
vertex_settings = VertexOrchestratorSettings(
    pod_settings={
        "node_selectors": {
            "cloud.google.com/gke-accelerator": "NVIDIA_TESLA_A100"
        },
    }
)
resource_settings = ResourceSettings(gpu_count=1)
```
You can find available accelerator types [here](https://cloud.google.com/vertex-ai/docs/training/configure-compute#specifying_gpus).

These settings can then be specified on either pipeline-level or step-level:

```python
# Either specify on pipeline-level
@pipeline(
    settings={
        "orchestrator": vertex_settings,
        "resources": resource_settings,
    }
)
def my_pipeline():
    ...

# OR specify settings on step-level
@step(
    settings={
        "orchestrator": vertex_settings,
        "resources": resource_settings,
    }
)
def my_step():
    ...
```

Check out the [SDK docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-gcp/#zenml.integrations.gcp.flavors.vertex\_orchestrator\_flavor.VertexOrchestratorSettings) for a full list of available attributes and [this docs page](../../how-to/use-configuration-files/runtime-configuration.md) for more information on how to specify settings.

For more information and a full list of configurable attributes of the Vertex orchestrator, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-gcp/#zenml.integrations.gcp.orchestrators.vertex\_orchestrator.VertexOrchestrator) .

### Enabling CUDA for GPU-backed hardware

Note that if you wish to use this orchestrator to run steps on a GPU, you will need to follow [the instructions on this page](../../how-to/training-with-gpus/training-with-gpus.md) to ensure that it works. It requires adding some extra settings customization and is essential to enable CUDA for the GPU to give its full acceleration.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
