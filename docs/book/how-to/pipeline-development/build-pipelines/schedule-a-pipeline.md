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

| Orchestrator                                                                     | Scheduling Support |
|----------------------------------------------------------------------------------|--------------------|
| [AirflowOrchestrator](../../../component-guide/orchestrators/airflow.md)            | ✅                 |
| [AzureMLOrchestrator](../../../component-guide/orchestrators/azureml.md)            | ✅                 |
| [DatabricksOrchestrator](../../../component-guide/orchestrators/databricks.md)      | ✅                 |
| [HyperAIOrchestrator](../../component-guide/orchestrators/hyperai.md)            | ✅                 |
| [KubeflowOrchestrator](../../../component-guide/orchestrators/kubeflow.md)          | ✅                 |
| [KubernetesOrchestrator](../../../component-guide/orchestrators/kubernetes.md)      | ✅                 |
| [LocalOrchestrator](../../../component-guide/orchestrators/local.md)                | ⛔️                 |
| [LocalDockerOrchestrator](../../../component-guide/orchestrators/local-docker.md)   | ⛔️                 |
| [SagemakerOrchestrator](../../../component-guide/orchestrators/sagemaker.md)        | ⛔️                 |
| [SkypilotAWSOrchestrator](../../../component-guide/orchestrators/skypilot-vm.md)    | ⛔️                 |
| [SkypilotAzureOrchestrator](../../../component-guide/orchestrators/skypilot-vm.md)  | ⛔️                 |
| [SkypilotGCPOrchestrator](../../../component-guide/orchestrators/skypilot-vm.md)    | ⛔️                 |
| [SkypilotLambdaOrchestrator](../../../component-guide/orchestrators/skypilot-vm.md) | ⛔️                 |
| [TektonOrchestrator](../../../component-guide/orchestrators/tekton.md)              | ⛔️                 |
| [VertexOrchestrator](../../../component-guide/orchestrators/vertex.md)              | ✅                 |


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
Check out our [SDK docs](https://sdkdocs.zenml.io/latest/core\_code\_docs/core-config/#zenml.config.schedule.Schedule) to learn more about the different scheduling options.
{% endhint %}

### Pause/Stop a schedule

The way pipelines are scheduled depends on the orchestrator you are using. For example, if you are using Kubeflow, you can use the Kubeflow UI to stop or pause a scheduled run. However, the exact steps for stopping or pausing a scheduled run may vary depending on the orchestrator you are using. We recommend consulting the documentation for your orchestrator to learn the current method for stopping or pausing a scheduled run.

{% hint style="warning" %}
Note that ZenML only gets involved to schedule a run, but maintaining the lifecycle of the schedule (as explained above) is the responsibility of the user. If you run a pipeline containing a schedule two times, two scheduled pipelines (with different/unique names) will be created.
{% endhint %}


***

### See Also:

<table data-view="cards">
    <thead>
    <tr>
        <th></th>
        <th></th>
        <th></th>
        <th data-hidden data-card-target data-type="content-ref"></th>
    </tr>
    </thead>
    <tbody>
    <tr>
        <td>Schedules rely on remote orchestrators, learn about those here</td>
        <td></td>
        <td></td>
        <td><a href="../../../component-guide/orchestrators/orchestrators.md">orchestrators.md</a></td>
    </tr>
    </tbody>
</table>

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
