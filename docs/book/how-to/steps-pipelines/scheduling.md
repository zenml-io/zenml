---
description: Learn how to set, pause and stop a schedule for pipelines.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Schedule a pipeline

{% hint style="info" %}
Schedules don't work for all orchestrators. Here is a list of all supported orchestrators.
{% endhint %}

| Orchestrator                                                                     | Scheduling Support | Supported Schedule Types                       |
|----------------------------------------------------------------------------------|--------------------|-------------------------------------------------|
| [AirflowOrchestrator](https://docs.zenml.io/stacks/orchestrators/airflow)            | ✅                 | Cron, Interval                                  |
| [AzureMLOrchestrator](https://docs.zenml.io/stacks/orchestrators/azureml)            | ✅                 | Cron, Interval                                  |
| [DatabricksOrchestrator](https://docs.zenml.io/stacks/orchestrators/databricks)      | ✅                 | Cron only                                       |
| [HyperAIOrchestrator](https://docs.zenml.io/stacks/orchestrators/hyperai)            | ✅                 | Cron, One-time                                  |
| [KubeflowOrchestrator](https://docs.zenml.io/stacks/orchestrators/kubeflow)          | ✅                 | Cron, Interval                                  |
| [KubernetesOrchestrator](https://docs.zenml.io/stacks/orchestrators/kubernetes)      | ✅                 | Cron only                                       |
| [LocalOrchestrator](https://docs.zenml.io/stacks/orchestrators/local)                | ⛔️                 | N/A                                             |
| [LocalDockerOrchestrator](https://docs.zenml.io/stacks/orchestrators/local-docker)   | ⛔️                 | N/A                                             |
| [SagemakerOrchestrator](https://docs.zenml.io/stacks/orchestrators/sagemaker)        | ✅                 | Cron, Interval, One-time                        |
| [SkypilotAWSOrchestrator](https://docs.zenml.io/stacks/orchestrators/skypilot-vm)    | ⛔️                 | N/A                                             |
| [SkypilotAzureOrchestrator](https://docs.zenml.io/stacks/orchestrators/skypilot-vm)  | ⛔️                 | N/A                                             |
| [SkypilotGCPOrchestrator](https://docs.zenml.io/stacks/orchestrators/skypilot-vm)    | ⛔️                 | N/A                                             |
| [SkypilotLambdaOrchestrator](https://docs.zenml.io/stacks/orchestrators/skypilot-vm) | ⛔️                 | N/A                                             |
| [TektonOrchestrator](https://docs.zenml.io/stacks/orchestrators/tekton)              | ⛔️                 | N/A                                             |
| [VertexOrchestrator](https://docs.zenml.io/stacks/orchestrators/vertex)              | ✅                 | Cron only                                       |

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

### Update/Pause/Stop a schedule

You can update or delete your schedules using the following CLI commands:
```bash
# Update the cron expression of the schedule
zenml pipeline schedule update <SCHEDULE_NAME_OR_ID> --cron-expression='* * * * *'

# Delete a schedule
zenml pipeline schedule delete <SCHEDULE_NAME_OR_ID>
```

The functionality of these commands changes depending on whether the orchestrator that is running the schedule
supports schedule updates/deletions:
- If the orchestrator supports it, this will update/delete the actual schedule as well as the schedule information stored in ZenML
- If the orchestrator does not support it, this will only update/delete the schedule information stored in ZenML

If the orchestrator **does not** support schedule management, maintaining the lifecycle of the schedule is the responsibility of the user.
In these cases, we recommend the following steps:

1. Find schedule on ZenML
2. Match schedule on orchestrator side and delete
3. Delete schedule on ZenML
4. Re-run pipeline with new schedule

A concrete example can be found on the [GCP Vertex orchestrator](https://docs.zenml.io/stacks/orchestrators/vertex) docs, and this pattern can be adapted for other orchestrators as well.
