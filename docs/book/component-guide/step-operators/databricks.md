---
description: Executing individual steps on Databricks.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Databricks

[Databricks](https://www.databricks.com/) is a unified data and AI platform that is often used for large-scale data processing, feature engineering, and model training. ZenML's Databricks step operator allows you to execute individual steps on Databricks while keeping the rest of the pipeline on your active orchestrator.

### When to use it

You should use the Databricks step operator if:

* one or more steps in your pipeline should run on Databricks instead of the environment provided by your orchestrator.
* you're already using Databricks for Spark-based data processing, distributed workloads, or training jobs.
* you want to keep selective execution on Databricks without moving the entire pipeline to the [Databricks orchestrator](../orchestrators/databricks.md).

{% hint style="info" %}
Use the Databricks **step operator** if only selected steps should run on Databricks. Use the Databricks **orchestrator** if you want Databricks to orchestrate the full pipeline.
{% endhint %}

### How it works

The Databricks step operator uses the same wheel-based execution model as the Databricks orchestrator:

1. ZenML packages your project code into a Python wheel.
2. ZenML uploads that wheel to your Databricks workspace.
3. ZenML submits a one-time Databricks job run for the selected step.
4. Databricks installs the wheel and executes the ZenML step entrypoint remotely.

This lets you offload a single step to Databricks without changing how the rest of your pipeline runs.

{% hint style="info" %}
The step operator uploads wheels under `/Workspace/Shared/.zenml` and removes the step-specific wheel directory after the Databricks run completes successfully. If a run fails or is canceled, the wheel directory is retained for debugging and can be removed manually from the same workspace path.
{% endhint %}

### How to use it

To use the Databricks step operator, first install the Databricks integration:

```shell
zenml integration install databricks
```

You also need:

* an active Databricks workspace
* Databricks credentials with permission to submit jobs
* a remote artifact store in your ZenML stack

Then register the step operator:

```shell
zenml step-operator register databricks_step_operator \
    --flavor=databricks \
    --host="https://xxxxx.x.azuredatabricks.net" \
    --client_id={{databricks.client_id}} \
    --client_secret={{databricks.client_secret}}
```

Add it to your stack:

```shell
zenml stack register databricks_stack -s databricks_step_operator ... --set
```

Once the step operator is part of your active stack, you can use it on individual steps:

```python
from zenml import step


@step(step_operator="databricks_step_operator")
def trainer(...) -> ...:
    ...
```

### Additional configuration

The Databricks step operator reuses the Databricks execution settings used by the Databricks orchestrator. You can configure Spark version, worker count, node types, autoscaling, Spark configuration, Spark environment variables, cluster policy, init scripts, and Docker image settings. Init scripts must use DBFS paths that start with `dbfs:/`. If you configure Docker registry authentication, provide both `docker_image_username` and `docker_image_password`.

```python
from zenml.integrations.databricks.flavors.databricks_step_operator_flavor import (
    DatabricksStepOperatorSettings,
)

databricks_settings = DatabricksStepOperatorSettings(
    spark_version="15.3.x-scala2.12",
    num_workers=3,
    node_type_id="Standard_D4s_v5",
    policy_id=POLICY_ID,
    spark_conf={},
    spark_env_vars={},
    init_scripts=["dbfs:/scripts/install_dependencies.sh"],
)
```

Use `num_workers` for fixed-size clusters. For autoscaling clusters, omit `num_workers` and set `autoscale`, for example `autoscale=(2, 3)`.

You can specify these settings on steps that should run on Databricks:

```python
from zenml import step


@step(
    step_operator="databricks_step_operator",
    settings={
        "step_operator": databricks_settings,
    },
)
def databricks_step(...) -> ...:
    ...
```

{% hint style="info" %}
The Databricks step operator submits one-time Databricks runs (`jobs.submit`) rather than persistent Databricks Jobs (`jobs.create`). Fields that only apply to persistent Jobs — `schedule_timezone`, `job_tags`, `max_concurrent_runs`, `max_retries`, `min_retry_interval_millis`, and `retry_on_timeout` — therefore live on `DatabricksOrchestratorSettings` and are not exposed on the step operator.
{% endhint %}

{% hint style="warning" %}
Generic ZenML `resource_settings` are not translated to Databricks cluster sizing. Use the Databricks-specific step operator settings instead.
{% endhint %}

### Stack requirements

Unlike image-based step operators, the Databricks step operator does not require a container registry or image builder. It does require a remote artifact store so that both your orchestrator environment and Databricks can access artifacts.

### Databricks UI

Submitted step runs are visible in Databricks. ZenML also stores Databricks run metadata on the step run so you can correlate ZenML execution with Databricks execution.

#### Enabling CUDA for GPU-backed hardware

If you plan to use GPU-enabled Databricks clusters, make sure your step environment and dependencies are configured accordingly. You can find general CUDA guidance in the [distributed training guide](https://docs.zenml.io/user-guides/tutorial/distributed-training/).

Check out the [SDK docs](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-databricks.html#zenml.integrations.databricks) for the full Databricks integration API surface.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
