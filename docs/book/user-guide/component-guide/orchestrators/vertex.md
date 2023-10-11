---
description: Orchestrating your pipelines to run on Vertex AI.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Google Cloud VertexAI Orchestrator

The Vertex orchestrator is an [orchestrator](orchestrators.md) flavor provided with the ZenML `gcp` integration that
uses [Vertex AI](https://cloud.google.com/vertex-ai) to run your pipelines.

{% hint style="warning" %}
This component is only meant to be used within the context of
a [remote ZenML deployment scenario](/docs/book/platform-guide/set-up-your-mlops-platform/deploy-zenml/deploy-zenml.md). Usage with a
local ZenML deployment may lead to unexpected behavior!
{% endhint %}

## When to use it

You should use the Vertex orchestrator if:

* you're already using GCP.
* you're looking for a proven production-grade orchestrator.
* you're looking for a UI in which you can track your pipeline runs.
* you're looking for a managed solution for running your pipelines.
* you're looking for a serverless solution for running your pipelines.

## How to deploy it

In order to use a Vertex AI orchestrator, you need to first
deploy [ZenML to the cloud](/docs/book/platform-guide/set-up-your-mlops-platform/deploy-zenml/deploy-zenml.md). It would be
recommended to deploy ZenML in the same Google Cloud project as where the Vertex infrastructure is deployed, but it is
not necessary to do so. You must ensure that you are connected to the remote ZenML server before using this stack 
component.

The only other thing necessary to use the ZenML Vertex orchestrator is enabling Vertex-relevant APIs on the Google Cloud
project.

In order to quickly enable APIs, and create other resources necessary for using this integration, you can also consider
using the [Vertex AI stack recipe](https://github.com/zenml-io/mlops-stacks/tree/main/vertex-ai), which helps you set up
the infrastructure with one click.

## How to use it

To use the Vertex orchestrator, we need:

* The ZenML `gcp` integration installed. If you haven't done so, run

  ```shell
  zenml integration install gcp
  ```
* [Docker](https://www.docker.com) installed and running.
* A [remote artifact store](../artifact-stores/artifact-stores.md) as part of your stack.
* A [remote container registry](../container-registries/container-registries.md) as part of your stack.
* [GCP credentials with proper permissions](#gcp-credentials-and-permissions)
* The GCP project ID and location in which you want to run your Vertex AI pipelines.

### GCP credentials and permissions

This part is without doubt the most involved part of using the Vertex orchestrator. In order to run pipelines on Vertex AI,
you need to have a GCP user account and/or one or more GCP service accounts set up with proper permissions, depending on whether [you want to schedule pipelines](#run-pipelines-on-a-schedule) and depending on whether you wish to practice [the principle of least privilege](https://en.wikipedia.org/wiki/Principle_of_least_privilege) and distribute permissions across multiple service accounts.

You also have three different options to provide credentials to the orchestrator:

* use the [`gcloud` CLI](https://cloud.google.com/sdk/gcloud) to authenticate locally with GCP
* configure the orchestrator to use a [service account key file](https://cloud.google.com/iam/docs/creating-managing-service-account-keys) to authenticate with GCP by setting the `service_account_path` parameter in the orchestrator configuration.
* (recommended) configure [a GCP Service Connector](../../../platform-guide/set-up-your-mlops-platform/connect-zenml-to-infrastructure/gcp-service-connector.md) with GCP credentials and then link the Vertex AI Orchestrator stack component to the Service Connector.

This section [explains the different components and GCP resources](#vertex-ai-pipeline-components) involved in running a Vertex AI pipeline and what permissions they need, then provides instructions for three different configuration use-cases:

1. [use the local `gcloud` CLI configured with your GCP user account](#configuration-use-case-local-gcloud-cli-with-user-account), without the ability to schedule pipelines
2. [use a GCP Service Connector and a single service account](#configuration-use-case-gcp-service-connector-with-single-service-account) with all permissions, including the ability to schedule pipelines
3. [use a GCP Service Connector and multiple service accounts](#configuration-use-case-gcp-service-connector-with-different-service-accounts) for different permissions, including the ability to schedule pipelines

#### Vertex AI pipeline components

To understand what accounts you need to provision and why, let's look at the different components of the Vertex orchestrator:

1. *the ZenML client environment* is the environment where you run the ZenML code responsible for
building the pipeline Docker image and submitting the pipeline to Vertex AI, among other things. This is usually your local machine or some other environment used to automate running pipelines, like a CI/CD job. This environment
needs to be able to authenticate with GCP and needs to have the necessary permissions to create a job in Vertex Pipelines, (e.g. [the `Vertex AI User` role](https://cloud.google.com/vertex-ai/docs/general/access-control#aiplatform.user)). If you are planning to [run pipelines on a schedule](#run-pipelines-on-a-schedule), *the ZenML client environment* also needs additional permissions:

    * permissions to create a Google Cloud Function (e.g. with the [`Cloud Functions Developer Role`](https://cloud.google.com/functions/docs/reference/iam/roles#cloudfunctions.developer)).
    * permissions to create a Google Cloud Scheduler (e.g. with the [Cloud Scheduler Admin Role](https://cloud.google.com/iam/docs/understanding-roles#cloudscheduler.admin)).
    * the [`Storage Object Creator Role`](https://cloud.google.com/iam/docs/understanding-roles#storage.objectCreator) to be able to write the pipeline JSON file to the artifact store directly (NOTE: not needed if the Artifact Store is configured with credentials or is linked to Service Connector)

2. *the Vertex AI pipeline environment* is the GCP environment in which the pipeline steps themselves are running in GCP. The Vertex AI pipeline runs in the context of a GCP service account which we'll call here *the workload service account*.
*The workload service account* can be explicitly configured in the orchestrator configuration via the `workload_service_account` parameter. If it is omitted, the orchestrator will use [the Compute Engine default service account](https://cloud.google.com/compute/docs/access/service-accounts#default_service_account) for the GCP project in which the pipeline is running. This service account needs to have the following permissions:

    * permissions to run a Vertex AI pipeline, (e.g. [the `Vertex AI Service Agent` role](https://cloud.google.com/vertex-ai/docs/general/access-control#aiplatform.serviceAgent)).

3. *the scheduler Google Cloud Function* is a GCP resource that is used to trigger the pipeline on a schedule. This component is only needed if you intend on running Vertex AI pipelines on a schedule. The scheduler function runs in the context of a GCP service account which we'll call here *the function service account*. *The function service account* can be explicitly configured in the orchestrator configuration via the `function_service_account` parameter. If it is omitted, the orchestrator will use [the Compute Engine default service account](https://cloud.google.com/compute/docs/access/service-accounts#default_service_account) for the GCP project in which the pipeline is running. This service account needs to have the following permissions:

    * permissions to create a job in Vertex Pipelines, (e.g. [the `Vertex AI User` role](https://cloud.google.com/vertex-ai/docs/general/access-control#aiplatform.user)).

4. *the Google Cloud Scheduler* is a GCP resource that is used to trigger the pipeline on a schedule. This component is only needed if you intend on running Vertex AI pipelines on a schedule. The scheduler needs a GCP service account to authenticate to *the scheduler Google Cloud Function*. Let's call this service account *the scheduler service account*. *The scheduler service account* can be explicitly configured in the orchestrator configuration via the `scheduler_service_account` parameter. If it is omitted, the orchestrator will use the following, in order of precedence:

    * the service account used by *the ZenML client environment* credentials, if present.
    * the service account specified in the `function_service_account` parameter.
    * the service account specified in the `workload_service_account` parameter.

*The scheduler service account* must have the following permissions:

* permissions to trigger the scheduler function, (e.g. [the `Cloud Functions Invoker` role](https://cloud.google.com/functions/docs/reference/iam/roles#cloudfunctions.invoker) and [the `Cloud Run Invoker` role](https://cloud.google.com/run/docs/reference/iam/roles#standard-roles)).    
* the [Storage Object Viewer Role](https://cloud.google.com/iam/docs/understanding-roles#storage.objectViewer) to be able to read the pipeline JSON file from the artifact store.

As you can see, there can be as many as three different service accounts involved in running a Vertex AI pipeline. Four, if you also use a service account to authenticate to GCP in *the ZenML client environment*. However, you can keep it simple an use the same service account everywhere. 

#### Configuration use-case: local `gcloud` CLI with user account

This configuration use-case assumes you have configured the [`gcloud` CLI](https://cloud.google.com/sdk/gcloud) to authenticate locally with your GCP account (i.e. by running `gcloud auth login`). It also assumes the following:

* you are not planning to run pipelines on a schedule.
* your GCP account has permissions to create a job in Vertex Pipelines, (e.g. [the `Vertex AI User` role](https://cloud.google.com/vertex-ai/docs/general/access-control#aiplatform.user)).
* [the Compute Engine default service account](https://cloud.google.com/compute/docs/access/service-accounts#default_service_account) for the GCP project in which the pipeline is running is updated with additional permissions required to run a Vertex AI pipeline, (e.g. [the `Vertex AI Service Agent` role](https://cloud.google.com/vertex-ai/docs/general/access-control#aiplatform.serviceAgent)).

{% hint style="info" %}
This is the easiest way to configure the Vertex AI Orchestrator, but it has the following drawbacks:

* you can't run pipelines on a schedule.
* the setup is not portable on other machines and reproducible by other users.
* it uses the Compute Engine default service account, which is not recommended, given that it has a lot of permissions by default and is used by many other GCP services.
{% endhint %}

We can then register the orchestrator as follows:

```shell
zenml orchestrator register <ORCHESTRATOR_NAME> \
    --flavor=vertex \
    --project=<PROJECT_ID> \
    --location=<GCP_LOCATION> \
    --synchronous=true
```

#### Configuration use-case: GCP Service Connector with single service account

This configuration uses a single GCP service account that has all the permissions needed to run and/or schedule a Vertex AI pipeline. This configuration is useful if you want to run pipelines on a schedule, but don't want to use the Compute Engine default service account. Using [a Service Connector](../../../platform-guide/set-up-your-mlops-platform/connect-zenml-to-infrastructure.md) brings the added benefit of making your pipeline fully portable.

This use-case assumes you have already configured a GCP service account with the following permissions:

* permissions to create a job in Vertex Pipelines, (e.g. [the `Vertex AI User` role](https://cloud.google.com/vertex-ai/docs/general/access-control#aiplatform.user)).
* permissions to run a Vertex AI pipeline, (e.g. [the `Vertex AI Service Agent` role](https://cloud.google.com/vertex-ai/docs/general/access-control#aiplatform.serviceAgent)).
* permissions to create a Google Cloud Function (e.g. with the [`Cloud Functions Developer Role`](https://cloud.google.com/functions/docs/reference/iam/roles#cloudfunctions.developer)).
* the [Storage Object Creator Role](https://cloud.google.com/iam/docs/understanding-roles#storage.objectCreator) to be able to write the pipeline JSON file to the artifact store directly.
* permissions to trigger the scheduler function, (e.g. [the `Cloud Functions Invoker` role](https://cloud.google.com/functions/docs/reference/iam/roles#cloudfunctions.invoker) and [the `Cloud Run Invoker` role](https://cloud.google.com/run/docs/reference/iam/roles#standard-roles)).
* permissions to create a Google Cloud Scheduler job (e.g. with the [`Cloud Scheduler Admin Role`](https://cloud.google.com/scheduler/docs/quickstart#before_you_begin)).

It also assumes you have already created a service account key for this service account and downloaded it to your local machine (e.g. in a `connectors-vertex-ai-workload.json` file).

{% hint style="info" %}
This setup is portable and reproducible, but it throws all the permissions in a single service account, which is not recommended if you are conscious about security. The principle of least privilege is not applied here and the environment in which the pipeline steps are running has too many permissions that it doesn't need.
{% endhint %}

We can then register [the GCP Service Connector](../../../platform-guide/set-up-your-mlops-platform/connect-zenml-to-infrastructure/gcp-service-connector.md) and Vertex AI orchestrator as follows:

```shell
zenml service-connector register <CONNECTOR_NAME> --type gcp --auth-method=service-account --project_id=<PROJECT_ID> --service_account_json=@connectors-vertex-ai-workload.json --resource-type gcp-generic

zenml orchestrator register <ORCHESTRATOR_NAME> \
    --flavor=vertex \
    --location=<GCP_LOCATION> \
    --synchronous=true \
    --workload_service_account=<SERVICE_ACCOUNT_NAME>@<PROJECT_NAME>.iam.gserviceaccount.com \
    --function_service_account=<SERVICE_ACCOUNT_NAME>@<PROJECT_NAME>.iam.gserviceaccount.com \
    --scheduler_service_account=<SERVICE_ACCOUNT_NAME>@<PROJECT_NAME>.iam.gserviceaccount.com

zenml orchestrator connect <ORCHESTRATOR_NAME> --connector <CONNECTOR_NAME>
```
#### Configuration use-case: GCP Service Connector with different service accounts

This setup applies the principle of least privilege by using different service accounts with the minimum of permissions needed for [the different components involved in running a Vertex AI pipeline](#vertex-ai-pipeline-components). It also uses a GCP Service Connector to make the setup portable and reproducible. This configuration is a best-in-class setup that you would normally use in production, but it requires a lot more work to prepare.

{% hint style="info" %}
This setup involves creating and configuring several GCP service accounts, which is a lot of work and can be error prone. 
If you don't really need the added security, you can use [the GCP Service Connector with a single service account](#configuration-use-case-gcp-service-connector-with-single-service-account) instead.
{% endhint %}

The following GCP service accounts are needed:

1. a "client" service account that has the following permissions:
    * permissions to create a job in Vertex Pipelines, (e.g. [the `Vertex AI User` role](https://cloud.google.com/vertex-ai/docs/general/access-control#aiplatform.user)).
    * permissions to create a Google Cloud Function (e.g. with the [`Cloud Functions Developer Role`](https://cloud.google.com/functions/docs/reference/iam/roles#cloudfunctions.developer)).
    * permissions to create a Google Cloud Scheduler job (e.g. with the [`Cloud Scheduler Admin Role`](https://cloud.google.com/scheduler/docs/quickstart#before_you_begin)).
    * the [Storage Object Creator Role](https://cloud.google.com/iam/docs/understanding-roles#storage.objectCreator) to be able to write the pipeline JSON file to the artifact store directly (NOTE: not needed if the Artifact Store is configured with credentials or is linked to Service Connector).

2. a "workload" service account that has permissions to run a Vertex AI pipeline, (e.g. [the `Vertex AI Service Agent` role](https://cloud.google.com/vertex-ai/docs/general/access-control#aiplatform.serviceAgent)).

3. a "function" service account that has the following permissions:
    * permissions to create a job in Vertex Pipelines, (e.g. [the `Vertex AI User` role](https://cloud.google.com/vertex-ai/docs/general/access-control#aiplatform.user)).
    * the [Storage Object Viewer Role](https://cloud.google.com/iam/docs/understanding-roles#storage.objectViewer) to be able to read the pipeline JSON file from the artifact store.

The "client" service account also needs to be granted the `iam.serviceaccounts.actAs` permission on this service account (i.e. the "client" service account needs [the `Service Account User` role](https://cloud.google.com/iam/docs/service-account-permissions#user-role) on the "function" service account). Similarly, the "function" service account also needs to be granted the `iam.serviceaccounts.actAs` permission on the "workload" service account.

4. a "scheduler" service account that has permissions to trigger the scheduler function, (e.g. [the `Cloud Functions Invoker` role](https://cloud.google.com/functions/docs/reference/iam/roles#cloudfunctions.invoker) and [the `Cloud Run Invoker` role](https://cloud.google.com/run/docs/reference/iam/roles#standard-roles)). The "client" service account also needs to be granted the `iam.serviceaccounts.actAs` permission on this service account (i.e. the "client" service account needs [the `Service Account User` role](https://cloud.google.com/iam/docs/service-account-permissions#user-role) on the "scheduler" service account).

A key is also needed for the "client" service account. You can create a key for this service account and download it to your local machine (e.g. in a `connectors-vertex-ai-workload.json` file).

With all the service accounts and the key ready, we can register [the GCP Service Connector](../../../platform-guide/set-up-your-mlops-platform/connect-zenml-to-infrastructure/gcp-service-connector.md) and Vertex AI orchestrator as follows:

```shell
zenml service-connector register <CONNECTOR_NAME> --type gcp --auth-method=service-account --project_id=<PROJECT_ID> --service_account_json=@connectors-vertex-ai-workload.json --resource-type gcp-generic

zenml orchestrator register <ORCHESTRATOR_NAME> \
    --flavor=vertex \
    --location=<GCP_LOCATION> \
    --synchronous=true \
    --workload_service_account=<WORKLOAD_SERVICE_ACCOUNT_NAME>@<PROJECT_NAME>.iam.gserviceaccount.com \
    --function_service_account=<FUNCTION_SERVICE_ACCOUNT_NAME>@<PROJECT_NAME>.iam.gserviceaccount.com \
    --scheduler_service_account=<SCHEDULER_SERVICE_ACCOUNT_NAME>@<PROJECT_NAME>.iam.gserviceaccount.com

zenml orchestrator connect <ORCHESTRATOR_NAME> --connector <CONNECTOR_NAME>
```
### Configuring the stack

With the orchestrator registered, we can use it in our active stack:

```shell
# Register and activate a stack with the new orchestrator
zenml stack register <STACK_NAME> -o <ORCHESTRATOR_NAME> ... --set
```

{% hint style="info" %}
ZenML will build a Docker image called `<CONTAINER_REGISTRY_URI>/zenml:<PIPELINE_NAME>` which includes your code and use
it to run your pipeline steps in Vertex AI. Check
out [this page](/docs/book/user-guide/advanced-guide/containerize-your-pipeline.md) if you want to learn
more about how ZenML builds these images and how you can customize them.
{% endhint %}

You can now run any ZenML pipeline using the Vertex orchestrator:

```shell
python file_that_runs_a_zenml_pipeline.py
```

### Vertex UI

Vertex comes with its own UI that you can use to find further details about your pipeline runs, such as the logs of your
steps. For any runs executed on Vertex, you can get the URL to the Vertex UI in Python using the following code snippet:

```python
from zenml.post_execution import get_run

pipeline_run = get_run("<PIPELINE_RUN_NAME>")
orchestrator_url = deployer_step.metadata["orchestrator_url"].value
```

### Run pipelines on a schedule

The Vertex Pipelines orchestrator supports running pipelines on a schedule, using logic resembling
the [official approach recommended by GCP](https://cloud.google.com/vertex-ai/docs/pipelines/schedule-cloud-scheduler).

ZenML utilizes the [Cloud Scheduler](https://cloud.google.com/scheduler)
and [Cloud Functions](https://cloud.google.com/functions) services to enable scheduling on Vertex Pipelines. The
following is the sequence of events that happen when running a pipeline on Vertex with a schedule:

* A docker image is created and pushed (see
  above [containerization](/docs/book/user-guide/advanced-guide/containerize-your-pipeline.md)).
* The Vertex AI pipeline JSON file is copied to
  the [Artifact Store](../artifact-stores/artifact-stores.md) specified in
  your [Stack](/docs/book/user-guide/starter-guide/understand-stacks.md)
* Cloud Function is created that creates the Vertex Pipeline job when triggered.
* A Cloud Scheduler job is created that triggers the Cloud Function on the defined schedule.

Therefore, to run on a schedule, the client environment needs additional permissions and a GCP service account at least is required for the Cloud Scheduler job to be able to authenticate with the Cloud Function, as explained in the
[GCP credentials and permissions](#gcp-credentials-and-permissions) section.

**How to schedule a pipeline**

```python
from zenml.config.schedule import Schedule

# Run a pipeline every 5th minute
pipeline_instance.run(
    schedule=Schedule(
        cron_expression="*/5 * * * *"
    )
)
```

{% hint style="warning" %}
The Vertex orchestrator only supports the `cron_expression` parameter in the `Schedule` object, and will ignore all
other parameters supplied to define the schedule.
{% endhint %}

**How to delete a scheduled pipeline**

Note that ZenML only gets involved to schedule a run, but maintaining the lifecycle of the schedule is the
responsibility of the user.

In order to cancel a scheduled Vertex pipeline, you need to manually delete the generated Google Cloud Function, along
with the Cloud Scheduler job that schedules it (via the UI or the CLI).

### Additional configuration

For additional configuration of the Vertex orchestrator, you can pass `VertexOrchestratorSettings` which allows you to
configure (among others) the following attributes:

* `pod_settings`: Node selectors, affinity, and tolerations to apply to the Kubernetes Pods running your pipeline. These
  can be either specified using the Kubernetes model objects or as dictionaries.

```python
from zenml.integrations.gcp.flavors.vertex_orchestrator_flavor import VertexOrchestratorSettings
from kubernetes.client.models import V1Toleration

vertex_settings = VertexOrchestratorSettings(
    pod_settings={
        "affinity": {
            "nodeAffinity": {
                "requiredDuringSchedulingIgnoredDuringExecution": {
                    "nodeSelectorTerms": [
                        {
                            "matchExpressions": [
                                {
                                    "key": "node.kubernetes.io/name",
                                    "operator": "In",
                                    "values": ["my_powerful_node_group"],
                                }
                            ]
                        }
                    ]
                }
            }
        },
        "tolerations": [
            V1Toleration(
                key="node.kubernetes.io/name",
                operator="Equal",
                value="",
                effect="NoSchedule"
            )
        ]
    }
)


@pipeline(
    settings={
        "orchestrator.vertex": vertex_settings
    }
)


...
```

Check out
the [API docs](https://apidocs.zenml.io/latest/integration\_code\_docs/integrations-gcp/#zenml.integrations.gcp.flavors.vertex\_orchestrator\_flavor.VertexOrchestratorSettings)
for a full list of available attributes and [this docs page](/docs/book/user-guide/advanced-guide/configure-steps-pipelines.md) for
more information on how to specify settings.

A concrete example of using the Vertex orchestrator can be
found [here](https://github.com/zenml-io/zenml/tree/main/examples/vertex\_ai\_orchestration).

For more information and a full list of configurable attributes of the Vertex orchestrator, check out
the [API Docs](https://apidocs.zenml.io/latest/integration\_code\_docs/integrations-gcp/#zenml.integrations.gcp.orchestrators.vertex\_orchestrator.VertexOrchestrator)
.

### Enabling CUDA for GPU-backed hardware

Note that if you wish to use this orchestrator to run steps on a GPU, you will need to
follow [the instructions on this page](/docs/book/user-guide/advanced-guide/scale-compute-to-the-cloud.md) to ensure that it
works. It requires adding some extra settings customization and is essential to enable CUDA for the GPU to give its full
acceleration.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
