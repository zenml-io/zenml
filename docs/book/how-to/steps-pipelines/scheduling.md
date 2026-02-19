---
description: Learn how to create, update, activate, deactivate, and delete schedules for pipelines.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Schedule a pipeline

{% hint style="info" %}
Schedules don't work for all orchestrators. Here is a list of all supported orchestrators.
{% endhint %}

| Orchestrator                                                                     | Scheduling Support | Supported Schedule Types     | Native Schedule Management |
|----------------------------------------------------------------------------------|--------------------|-------------------------------------------------|----------------------------|
| [AirflowOrchestrator](https://docs.zenml.io/stacks/orchestrators/airflow)            | ✅                 | Cron, Interval               | ⛔️                          |
| [AzureMLOrchestrator](https://docs.zenml.io/stacks/orchestrators/azureml)            | ✅                 | Cron, Interval               | ⛔️                          |
| [DatabricksOrchestrator](https://docs.zenml.io/stacks/orchestrators/databricks)      | ✅                 | Cron only                    | ⛔️                          |
| [HyperAIOrchestrator](https://docs.zenml.io/stacks/orchestrators/hyperai)            | ✅                 | Cron, One-time               | ⛔️                          |
| [KubeflowOrchestrator](https://docs.zenml.io/stacks/orchestrators/kubeflow)          | ✅                 | Cron, Interval               | ⛔️                          |
| [KubernetesOrchestrator](https://docs.zenml.io/stacks/orchestrators/kubernetes)      | ✅                 | Cron only                    | ✅                          |
| [LocalOrchestrator](https://docs.zenml.io/stacks/orchestrators/local)                | ⛔️                 | N/A                          | N/A                        |
| [LocalDockerOrchestrator](https://docs.zenml.io/stacks/orchestrators/local-docker)   | ⛔️                 | N/A                          | N/A                        |
| [SagemakerOrchestrator](https://docs.zenml.io/stacks/orchestrators/sagemaker)        | ✅                 | Cron, Interval, One-time     | ⛔️                          |
| [SkypilotAWSOrchestrator](https://docs.zenml.io/stacks/orchestrators/skypilot-vm)    | ⛔️                 | N/A                          | N/A                        |
| [SkypilotAzureOrchestrator](https://docs.zenml.io/stacks/orchestrators/skypilot-vm)  | ⛔️                 | N/A                          | N/A                        |
| [SkypilotGCPOrchestrator](https://docs.zenml.io/stacks/orchestrators/skypilot-vm)    | ⛔️                 | N/A                          | N/A                        |
| [SkypilotLambdaOrchestrator](https://docs.zenml.io/stacks/orchestrators/skypilot-vm) | ⛔️                 | N/A                          | N/A                        |
| [TektonOrchestrator](https://docs.zenml.io/stacks/orchestrators/tekton)              | ⛔️                 | N/A                          | N/A                        |
| [VertexOrchestrator](https://docs.zenml.io/stacks/orchestrators/vertex)              | ✅                 | Cron only                    | ⛔️                          |

{% hint style="info" %}
**Native Schedule Management** means the orchestrator supports updating and deleting schedules directly through ZenML commands. When supported, commands like `zenml pipeline schedule update` and `zenml pipeline schedule delete` will automatically update/delete the schedule on the orchestrator platform (e.g., Kubernetes CronJobs). For orchestrators without this support, you'll need to manually manage schedules on the orchestrator side.
{% endhint %}

Check out [our tutorial on
scheduling](https://docs.zenml.io/user-guides/tutorial/managing-scheduled-pipelines)
for a practical guide on how to schedule a pipeline.

### Set a schedule

```python
from zenml.config.schedule import Schedule
from zenml import pipeline
from datetime import datetime

@pipeline()
def my_pipeline(...):
    ...

# Use cron expressions
schedule = Schedule(cron_expression="5 14 * * 3")
# or alternatively use human-readable notations
schedule = Schedule(start_time=datetime.now(), interval_second=1800)

my_pipeline = my_pipeline.with_options(schedule=schedule)
my_pipeline()
```

{% hint style="info" %}
Check out our [SDK docs](https://sdkdocs.zenml.io/latest/core_code_docs/core-config.html#zenml.config.schedule) to learn more about the different scheduling options.
{% endhint %}

### Update a schedule

You can update your schedule's cron expression:
```bash
zenml pipeline schedule update <SCHEDULE_NAME_OR_ID> --cron-expression='* * * * *'
```

### Activate and deactivate a schedule

You can temporarily pause a schedule without deleting it using the deactivate command, and resume it later with activate:

```bash
# Pause a schedule (stops future executions)
zenml pipeline schedule deactivate <SCHEDULE_NAME_OR_ID>

# Resume a paused schedule
zenml pipeline schedule activate <SCHEDULE_NAME_OR_ID>
```

{% hint style="info" %}
For the Kubernetes orchestrator, activate/deactivate controls the CronJob's `suspend` field - this is a native Kubernetes feature that pauses schedule execution without removing the CronJob resource.
{% endhint %}

### Delete a schedule

Deleting a schedule archives it by default (soft delete), which preserves references in historical pipeline runs that were triggered by this schedule:

```bash
# Archive a schedule (soft delete - default behavior)
zenml pipeline schedule delete <SCHEDULE_NAME_OR_ID>

# Permanently delete a schedule and remove all references (hard delete)
zenml pipeline schedule delete <SCHEDULE_NAME_OR_ID> --hard
```

{% hint style="warning" %}
Using `--hard` permanently removes the schedule and any historical references to it. Pipeline runs that were triggered by this schedule will no longer show the schedule association.
{% endhint %}

### Orchestrator support for schedule management

The functionality of these commands changes depending on whether the orchestrator supports schedule updates/deletions (see the "Native Schedule Management" column in the table above):
- **Kubernetes orchestrator**: Fully supports native schedule management. Update and delete commands will modify/remove the actual CronJob on the cluster as well as the schedule information in ZenML.
- **Other schedulable orchestrators**: Only update/delete the schedule information stored in ZenML. The actual schedule on the orchestrator remains unchanged.

If the orchestrator **does not** support native schedule management, maintaining the lifecycle of the schedule on the orchestrator side is the responsibility of the user.
In these cases, we recommend the following steps:

1. Find schedule on ZenML
2. Match schedule on orchestrator side and delete
3. Delete schedule on ZenML
4. Re-run pipeline with new schedule

A concrete example can be found on the [GCP Vertex orchestrator](https://docs.zenml.io/stacks/orchestrators/vertex) docs, and this pattern can be adapted for other orchestrators as well.
