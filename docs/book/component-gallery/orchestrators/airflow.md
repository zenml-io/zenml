---
description: How to orchestrate pipelines with Airflow
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


The Airflow orchestrator is an [orchestrator](./orchestrators.md) flavor 
provided with the ZenML `airflow` integration that uses 
[Airflow](https://airflow.apache.org/) to run your pipelines.

## When to use it

You should use the Airflow orchestrator if
* you're already using Airflow
* you want to run your pipelines locally with a more production-ready setup 
than the [local orchestrator](./local.md)

If you're looking to run your pipelines in the cloud, take a look at other
[orchestrator flavors](./orchestrators.md#orchestrator-flavors).

{% hint style="info" %}

We're currently reworking the Airflow orchestrator to make sure it works
not only locally but also with Airflow instances deployed on cloud 
infrastructure.

{% endhint %}

## How to deploy it

The Airflow orchestrator works without any additional infrastructure setup.

## How to use it

To use the Airflow orchestrator, we need:
* The ZenML `airflow` integration installed. If you haven't done so, run 
    ```shell
    zenml integration install airflow
    ```

We can then register the orchestrator and use it in our active stack:
```shell
zenml orchestrator register <NAME> \
    --flavor=airflow

# Add the orchestrator to the active stack
zenml stack update -o <NAME>
```

Once the orchestrator is part of the active stack, we can provision all 
required local resources by running:

```shell
zenml stack up
```

This command will start up an Airflow server on your local machine
that's running in the same Python environment that you used to
provision it. When it is finished, it will print a 
username and password which you can use to log in to the Airflow UI
[here](http://0.0.0.0:8080).


You can now run any ZenML pipeline using the Airflow orchestrator:
```shell
python file_that_runs_a_zenml_pipeline.py
```

A concrete example of using the Airflow orchestrator can be found 
[here](https://github.com/zenml-io/zenml/tree/main/examples/airflow_orchestration).

For more information and a full list of configurable attributes of the Airflow 
orchestrator, check out the [API Docs](https://apidocs.zenml.io/latest/api_docs/integration_code_docs/integrations-airflow/#zenml.integrations.airflow.orchestrators.airflow_orchestrator.AirflowOrchestrator).

### Enabling CUDA for GPU-backed hardware

Note that if you wish to use this orchestrator to run steps on a GPU, you will
need to follow [the instructions on this page](../../advanced-guide/pipelines/gpu-hardware.md) to ensure that it works. It
requires adding some extra settings customization and is essential to enable
CUDA for the GPU to give its full acceleration.
