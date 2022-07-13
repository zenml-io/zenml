---
description: Orchestrate pipelines with Airflow
---

The Airflow orchestrator is an [orchestrator](./overview.md) flavor provided with
the ZenML `airflow` integration that uses [Airflow](https://airflow.apache.org/)
to run your pipelines.

## When to use it

You should use the Airflow orchestrator if:
* ...

## How to deploy it

...

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

TODO: explain how to run a pipeline

A concrete example of using the Airflow orchestrator can be found 
[here](https://github.com/zenml-io/zenml/tree/main/examples/airflow_orchestration).

For more information and a full list of configurable attributes of the Airflow orchestrator, check out the 
[API Docs](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.airflow.orchestrators.airflow_orchestrator.AirflowOrchestrator).