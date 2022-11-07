---
description: How to orchestrate pipelines with Airflow
---

The Airflow orchestrator is an [orchestrator](./orchestrators.md) flavor 
provided with the ZenML `airflow` integration that uses 
[Airflow](https://airflow.apache.org/) to run your pipelines.

{% hint style="warning" %}
If you're going to use a remote deployment of Airflow, you'll also need a[remote ZenML deployment](../../getting-started/deploying-zenml/deploying-zenml.md).
{% endhint %}

## When to use it

You should use the Airflow orchestrator if
* you're looking for a proven production-grade orchestrator.
* you're already using Airflow
* you want to run your pipelines locally.
* you're willing to deploy and maintain Airflow.

## How to deploy it

The Airflow orchestrator can be used to run pipelines locally as well as remotely.
In the local case, no additional setup is necessary.

There are many options to deploy Airflow and we'll only cover a few here.
Check out the official [Airflow docs](https://airflow.apache.org/docs/apache-airflow/stable/production-deployment.html) for more information.

{% tabs %}
{% tab title="Cloud composer" %}

{% endtab %}
{% endtabs %}
## How to use it

To use the Airflow orchestrator, we need:
* The ZenML `airflow` integration installed. If you haven't done so, run 
    ```shell
    zenml integration install airflow
    ```
* The orchestrator registered and part of our active stack:
```shell
zenml orchestrator register <NAME> \
    --flavor=airflow

# Add the orchestrator to the active stack
zenml stack update -o <NAME>
```

{% tabs %}
{% tab title="Local" %}

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

{% endtab %}

{% tab title="Remote" %}

When using the Airflow orchestrator with a remote deployment, you'll additionally 
need:
* A remote ZenML server deployed to the cloud. See the [deployment guide](../../getting-started/deploying-zenml/deploying-zenml.md) for more information.
* A deployed Airflow server. See the [deployment section](#how-to-deploy-it) 
for more information.
* A [remote artifact store](../artifact-stores/artifact-stores.md) as part of 
your stack.
* A [remote container registry](../container-registries/container-registries.md) 
as part of your stack.

{% endtab %}
{% endtabs %}


{% hint style="info" %}
ZenML will build a Docker image called `<CONTAINER_REGISTRY_URI>/zenml:<PIPELINE_NAME>`
which includes your code and use it to run your pipeline steps in Airflow. 
Check out [this page](../../advanced-guide/pipelines/containerization.md)
if you want to learn more about how ZenML builds these images and how you can 
customize them.
{% endhint %}

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
