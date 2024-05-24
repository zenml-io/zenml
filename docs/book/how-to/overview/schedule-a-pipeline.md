---
description: Learn how to set, pause and stop a schedule for pipelines.
---

# Schedule a pipeline

{% hint style="info" %}
Schedules don't work for all orchestrators. Here is a list of all supported orchestrators.
{% endhint %}

| Orchestrator                                                                | Scheduling Support |
| --------------------------------------------------------------------------- | ------------------ |
| [LocalOrchestrator](../component-guide/orchestrators/local.md)              | ⛔️                 |
| [LocalDockerOrchestrator](../component-guide/orchestrators/local-docker.md) | ⛔️                 |
| [KubernetesOrchestrator](../component-guide/orchestrators/kubernetes.md)    | ✅                  |
| [KubeflowOrchestrator](../component-guide/orchestrators/kubeflow.md)        | ✅                  |
| [VertexOrchestrator](../component-guide/orchestrators/vertex.md)            | ✅                  |
| [TektonOrchestrator](../component-guide/orchestrators/tekton.md)            | ⛔️                 |
| [AirflowOrchestrator](../component-guide/orchestrators/airflow.md)          | ✅                  |

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
