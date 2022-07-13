---
description: Orchestrate pipelines with Airflow
---

The Airflow orchestrator is an [orchestrator](./overview.md) flavor provided with
the ZenML `airflow` integration that uses [Airflow](https://airflow.apache.org/)
to run your pipelines.

## When to use it

You should use the Airflow orchestrator if
* you're already using Airflow
* you want to run your pipelines locally with a more production-ready setup 
than the [local orchestrator](./local.md)

If you're looking to run your pipelines in the cloud, take a look at other
[orchestrator flavors](./overview.md#orchestrator-flavors).

{% hint style="info" %}

We're currently reworking the Airflow orchestrator to make sure it works
not only locally but also with Airflow instances deployed on cloud infrastructure.

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

Once the orchestrator is part of the active stack, we can provision
all required local resources by running:

```shell
zenml stack up
```

This command will start up Airflow on your local machine and print a 
username and password which you can use to login to the Airflow UI
[here](http://0.0.0.0:8080).


You can now run any ZenML pipeline using the Airflow orchestrator:
```shell
python file_that_runs_a_zenml_pipeline.py
```

A concrete example of using the Airflow orchestrator can be found 
[here](https://github.com/zenml-io/zenml/tree/main/examples/airflow_orchestration).

For more information and a full list of configurable attributes of the Airflow orchestrator, check out the 
[API Docs](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.airflow.orchestrators.airflow_orchestrator.AirflowOrchestrator).