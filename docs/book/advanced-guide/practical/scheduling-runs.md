---
description: Schedule runs to add automation to your pipelines
---

In the world of MLOps, scheduling orchestration jobs is an important aspect of automating the processes involved in deploying and maintaining machine learning (ML) models in production environments. Scheduling orchestration jobs allows you to automate tasks such as training and evaluating ML models, deploying models to production, or running periodic checks to ensure that the models are functioning as expected. This can help ensure that your ML pipelines are executed at the right time and in the right order, and can save you time and effort by eliminating the need to manually trigger these tasks.

ZenML pipelines can also be used for scheduling orchestration jobs, but there are some limitations to consider. ZenML-powered orchestrators only support scheduling in certain orchestrators and setup (see below for details on what works and what doesn't), as they require something running in the background to trigger the pipeline runs. Despite these limitations, using scheduling with ZenML can be a useful way to automate your MLOps workflow and save time and effort.

# How to schedule a pipeline run

ZenML's scheduling functionality rests on the use of a `Schedule` object that
you pass in when calling `pipeline.run()`. There are two ways to create a
schedule with the `Schedule` object:

You could write a cron expression to describe the pipeline schedule in terms
that would be comprehensible as [a cron job](https://en.wikipedia.org/wiki/Cron). For example, if you wanted your pipeline to run at 14:05 on Wednesdays, you could use the following:

```python
from zenml.config.schedule import Schedule

schedule = Schedule(cron_expression="5 14 * * 3")
pipeline.run(schedule=schedule)
```

Alternatively, you could manually specify start and end times and the interval between runs. For example, if you wanted your pipeline to run once every 30 minutes starting right now, you could use the following:

```python
from zenml.config.schedule import Schedule

schedule = Schedule(start_time=datetime.now(), interval_second=1800)
pipeline.run(schedule=schedule)
```

You can also optionally specify an `end_time` for the schedule if you want it not
to run after a certain moment. Similarly, the boolean `catchup` parameter can be
used to specify whether a recurring run should catch up (i.e. backfill pipeline
runs) if it is behind schedule, if you paused the schedule, for example.

# How to stop or pause a scheduled run

The way pipelines are scheduled depends on the orchestrator you are using. For example, if you are using Kubeflow, you can use the Kubeflow UI to stop or pause a scheduled run. If you are using Airflow, you can use the Airflow UI to do the same. However, the exact steps for stopping or pausing a scheduled run may vary depending on the orchestrator you are using. We recommend consulting the documentation for your orchestrator to learn the current method for stopping or pausing a scheduled run.

# Supported Orchestrators

| Orchestrator | Scheduling Support |
| ------------ | ------------------ |
| LocalOrchestrator | ⛔️ |
| LocalDockerOrchestrator | ⛔️ |
| KubernetesOrchestrator | ✅ |
| KubeflowOrchestrator | ✅ |
| VertexOrchestrator | ✅ |
| TektonOrchestrator | ⛔️ |
| AirflowOrchestrator | ✅ |
| GiHubActionsOrchestrator | ✅ |
