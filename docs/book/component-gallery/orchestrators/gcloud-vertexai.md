---
description: How to orchestrate pipelines with Vertex AI
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


The Vertex orchestrator is an [orchestrator](./orchestrators.md) flavor provided
with the ZenML `gcp` integration that uses [Vertex AI](https://cloud.google.com/vertex-ai)
to run your pipelines.

{% hint style="warning" %}
This component is only meant to be used within the context of [remote ZenML deployment scenario](../../getting-started/deploying-zenml/deploying-zenml.md). Usage with a local ZenML deployment may lead to unexpected behavior!
{% endhint %}

## When to use it

You should use the Vertex orchestrator if:
* you're already using GCP.
* you're looking for a proven production-grade orchestrator.
* you're looking for a UI in which you can track your pipeline runs.
* you're looking for a managed solution for running your pipelines.
* you're looking for a serverless solution for running your pipelines.

## How to deploy it

In order to use a Vertex AI orchestrator, you need to first deploy [ZenML to the cloud](../../getting-started/deploying-zenml/deploying-zenml.md). It would be recommended to deploy ZenML in the same Google Cloud project as where the Vertex infrastructure is deployed, but it is not necessary to do so. You must ensure that you are [connected to the remote ZenML server](../../starter-guide/collaborate/zenml-deployment.md) before using this stack component.

The only other thing necessary to use the ZenML Vertex orchestrator is enabling Vertex relevant APIs on the Google Cloud project.

In order to quickly enable APIs, and create other resources necessary for to use this integration, you can also consider using the [Vertex AI stack recipe](https://github.com/zenml-io/mlops-stacks/tree/main/vertex-ai), which helps you set up the infrastructure with one click.

## How to use it

To use the Vertex orchestrator, we need:

* The ZenML `gcp` integration installed. If you haven't done so, run 
    ```shell
    zenml integration install gcp
    ```
* [Docker](https://www.docker.com) installed and running.
* A [remote artifact store](../artifact-stores/artifact-stores.md) as part of 
your stack.
* A [remote container registry](../container-registries/container-registries.md) 
as part of your stack.
* The GCP project ID and location in which you want to run your Vertex 
AI pipelines.
* The pipeline client environment needs permissions to create a job in Vertex Pipelines,
e.g. the `Vertex AI User` role: https://cloud.google.com/vertex-ai/docs/general/access-control#aiplatform.user
* To run on a schedule, the client environment also needs permissions to create a Google Cloud
Function (e.g. with the [`cloudfunctions.serviceAgent Role`](https://cloud.google.com/functions/docs/concepts/iam))
and to create a Google Cloud Scheduler (e.g. with the
[Cloud Scheduler Job Runner Role](https://cloud.google.com/iam/docs/understanding-roles)). Additionally, it needs
the [Storage Object Creator Role](https://cloud.google.com/storage/docs/access-control/iam-roles)
to be able to write the pipeline JSON file to the artifact store directly.

We can then register the orchestrator and use it in our active stack:
```shell
zenml orchestrator register <ORCHESTRATOR_NAME> \
    --flavor=vertex \
    --project=<PROJECT_ID> \
    --location=<GCP_LOCATION>

# Register and activate a stack with the new orchestrator
zenml stack register <STACK_NAME> -o <ORCHESTRATOR_NAME> ... --set
```

{% hint style="info" %}
ZenML will build a Docker image called `<CONTAINER_REGISTRY_URI>/zenml:<PIPELINE_NAME>`
which includes your code and use it to run your pipeline steps in Vertex AI. 
Check out [this page](../../advanced-guide/pipelines/containerization.md)
if you want to learn more about how ZenML builds these images and
how you can customize them.
{% endhint %}

You can now run any ZenML pipeline using the Vertex orchestrator:
```shell
python file_that_runs_a_zenml_pipeline.py
```

### Run pipelines on a schedule

The Vertex Pipelines orchestrator supports running pipelines on a schedule, using
logic resembling the [official approach recommended by GCP](https://cloud.google.com/vertex-ai/docs/pipelines/schedule-cloud-scheduler).

ZenML utilizes the [Cloud Scheduler](https://cloud.google.com/scheduler) and
[Cloud Functions](https://cloud.google.com/functions) services to enable scheduling
on Vertex Pipelines. The following is the sequence of events that happen when running
a pipeline on Vertex with a schedule:

* Docker image is created and pushed (see above [containerization](../../advanced-guide/pipelines/containerization.md)).
* The Vertex AI pipeline JSON file is copied to the [Artifact Store](../../component-gallery/artifact-stores/artifact-stores.md) specified in your [Stack](../../starter-guide/stacks/stacks.md)
* Cloud Function is created that creates the Vertex Pipeline job when triggered.
* Cloud Scheduler job is created that triggers the Cloud Function on the defined schedule.

Therefore, to run on a schedule, the client environment needs permissions to create a Google Cloud
Function (e.g. with the [`cloudfunctions.serviceAgent` Role](https://cloud.google.com/functions/docs/concepts/iam))
and to create a Google Cloud Scheduler (e.g. with the
[Cloud Scheduler Job Runner Role](https://cloud.google.com/iam/docs/understanding-roles)).
Additionally, it needs
the [Storage Object Creator Role](https://cloud.google.com/storage/docs/access-control/iam-roles)
to be able to write the pipeline JSON file to the artifact store directly.

Once your have these permissions set in your local GCP CLI, here is how to create a scheduled
Vertex pipeline in ZenML:

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
The Vertex orchestrator only supports the `cron_expression` parameter in the `Schedule` object,
and will ignore all other parameters supplied to define the schedule.
{% endhint %}

#### How to delete a scheduled pipeline

Note that ZenML only gets involved to schedule a run, but maintaining the
lifecycle of the schedule is the responsibility of the
user.

In order to cancel a scheduled Vertex pipeline, you need to manually delete the
generated Google Cloud Function, along with the Cloud Scheduler job that schedules
it (via the UI or the CLI).

### Additional configuration

For additional configuration of the Vertex orchestrator, you can pass
`VertexOrchestratorSettings` which allows you to configure (among others) the following attributes:

* `pod_settings`: Node selectors, affinity and tolerations to apply to the Kubernetes Pods running
your pipline. These can be either specified using the Kubernetes model objects or as dictionaries.

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

Check out the
[API docs](https://apidocs.zenml.io/latest/integration_code_docs/integrations-gcp/#zenml.integrations.gcp.flavors.vertex_orchestrator_flavor.VertexOrchestratorSettings)
for a full list of available attributes and [this docs page](../..//advanced-guide/pipelines/settings.md)
for more information on how to specify settings.

A concrete example of using the Vertex orchestrator can be found 
[here](https://github.com/zenml-io/zenml/tree/main/examples/vertex_ai_orchestration).

For more information and a full list of configurable attributes of the Vertex 
orchestrator, check out the [API Docs](https://apidocs.zenml.io/latest/integration_code_docs/integrations-gcp/#zenml.integrations.gcp.orchestrators.vertex_orchestrator.VertexOrchestrator).

### Enabling CUDA for GPU-backed hardware

Note that if you wish to use this orchestrator to run steps on a GPU, you will
need to follow [the instructions on this page](../../advanced-guide/pipelines/gpu-hardware.md) to ensure that it works. It
requires adding some extra settings customization and is essential to enable
CUDA for the GPU to give its full acceleration.
