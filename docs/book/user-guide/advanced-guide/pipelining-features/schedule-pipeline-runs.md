---
description: Planning runs to add automation to your pipelines.
---

# Schedule pipeline runs

In the world of MLOps, scheduling orchestration jobs is an important aspect of automating the processes involved in deploying and maintaining machine learning (ML) models in production environments. Scheduling orchestration jobs allows you to automate tasks such as training and evaluating ML models, deploying models to production, or running periodic checks to ensure that the models are functioning as expected. This can help ensure that your ML pipelines are executed at the right time and in the right order, and can save you time and effort by eliminating the need to manually trigger these tasks.

ZenML pipelines can also be used for scheduling orchestration jobs, but there are some limitations to consider. ZenML-powered orchestrators only support scheduling in certain orchestrators and setups (see below for details on what works and what doesn't), as they require something running in the background to trigger the pipeline runs. Despite these limitations, using scheduling with ZenML can be a useful way to automate your MLOps workflow and save time and effort.

## Scheduling a pipeline run

ZenML's scheduling functionality rests on the use of a `Schedule` object that you pass in when calling `pipeline.run()`. There are two ways to create a schedule with the `Schedule` object, though whether one or both of these are supported depends on the specific orchestrator you're using. For example, our [Vertex Orchestrator](../../component-guide/orchestrators/vertex.md) only supports the cron expression method (see below).

You could write a cron expression to describe the pipeline schedule in terms that would be comprehensible as [a cron job](https://en.wikipedia.org/wiki/Cron). For example, if you wanted your pipeline to run at 14:05 on Wednesdays, you could use the following:

```python
from zenml.config.schedule import Schedule
from zenml import pipeline

@pipeline
def my_pipeline(...):
    ...

schedule = Schedule(cron_expression="5 14 * * 3")
my_pipeline = my_pipeline.with_options(schedule=schedule)
my_pipeline()
```

Alternatively, you could manually specify start and end times and the interval between runs. For example, if you wanted your pipeline to run once every 30 minutes starting right now, you could use the following:

```python
from zenml.config.schedule import Schedule
from zenml import pipeline

@pipeline
def my_pipeline(...):
    ...

schedule = Schedule(start_time=datetime.now(), interval_second=1800)
my_pipeline = my_pipeline.with_options(schedule=schedule)
my_pipeline()
```

You can specify an optional `end_time` for the schedule to prevent it from running after a certain time. The `catchup` parameter, which is a boolean, can be used to specify whether a recurring run should catch up (i.e. backfill pipeline runs) on missed runs if it has fallen behind schedule. This can happen, for example, if you paused the schedule.

In the context of scheduled cron or pipeline jobs, backfilling refers to running a missed job for a specific period in the past. For example, if a pipeline misses a scheduled run at 12:00 PM, backfilling can be used to run the pipeline for the 12:00 PM time slot, in order to collect the missing data. This helps ensure that the pipeline is up-to-date and that downstream jobs have the necessary data to run correctly. Backfilling is a useful technique for catching up on missed runs and filling in gaps in scheduled jobs and can help ensure that pipelines and cron schedules are running smoothly. Usually, if your pipeline handles backfill internally, you should turn catchup off to avoid duplicate backfill. Note that the `catchup` parameter enabling backfilling is not supported in all orchestrators.

{% hint style="warning" %}
Here's [a handy guide](https://medium.com/nerd-for-tech/airflow-catchup-backfill-demystified-355def1b6f92) in the context of Airflow.
{% endhint %}

### Supported orchestrators

| Orchestrator                                                                | Scheduling Support |
| --------------------------------------------------------------------------- | ------------------ |
| [LocalOrchestrator](../../component-guide/orchestrators/local.md)              | ⛔️                 |
| [LocalDockerOrchestrator](../../component-guide/orchestrators/local-docker.md) | ⛔️                 |
| [KubernetesOrchestrator](../../component-guide/orchestrators/kubernetes.md)    | ✅                  |
| [KubeflowOrchestrator](../../component-guide/orchestrators/kubeflow.md)        | ✅                  |
| [VertexOrchestrator](../../component-guide/orchestrators/vertex.md)            | ✅                  |
| [TektonOrchestrator](../../component-guide/orchestrators/tekton.md)            | ⛔️                 |
| [AirflowOrchestrator](../../component-guide/orchestrators/airflow.md)          | ✅                  |

{% hint style="info" %}
We maintain a public roadmap for ZenML, which you can find [here](https://zenml.io/roadmap). We welcome community contributions (see more [here](https://github.com/zenml-io/zenml/blob/main/CONTRIBUTING.md)) so if you want to enable scheduling for an unsupported orchestrator, please [do let us know](https://zenml.io/slack-invite)!
{% endhint %}

## Stopping/pausing a scheduled run

The way pipelines are scheduled depends on the orchestrator you are using. For example, if you are using Kubeflow, you can use the Kubeflow UI to stop or pause a scheduled run. If you are using Airflow, you can use the Airflow UI to do the same. However, the exact steps for stopping or pausing a scheduled run may vary depending on the orchestrator you are using. We recommend consulting the documentation for your orchestrator to learn the current method for stopping or pausing a scheduled run.

Note that ZenML only gets involved to schedule a run, but maintaining the lifecycle of the schedule (as explained above) is the responsibility of the user. If you run a pipeline containing a schedule two times, two scheduled pipelines (with different/unique names) will be created in whatever orchestrator you're using, so in that sense, it's on you to stop or pause the schedule as is appropriate.

## Tips for using schedules

Generally one of the steps in your pipeline will be loading dynamic data if you are going to schedule it. For example, if you are training a model on a daily basis, you will want to load the latest data from your data source. This is because the data will change over time.

In this case, you will also want to disable the cache for both pipeline and steps so that your pipeline actually runs afresh every time.

This is an example of such a step:

```python
# Various imports handled here

@step(enable_cache=False)
def staging_data_loader() -> Tuple[
    Annotated[pd.DataFrame, "X_train"],
    Annotated[pd.DataFrame, "X_test"],
    Annotated[pd.Series, "y_train"],
    Annotated[pd.Series, "y_test"],
]:
    """Load the static staging dataset."""
    X_train = download_dataframe(env="staging", df_name="X_train")
    X_test = download_dataframe(env="staging", df_name="X_test")
    y_train = download_dataframe(env="staging", df_name="y_train", df_type="series")
    y_test = download_dataframe(env="staging", df_name="y_test", df_type="series")

    return X_train, X_test, y_train, y_test
```

Note how the cache is disabled and that this step loads dynamic data.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
