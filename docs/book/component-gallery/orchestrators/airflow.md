---
description: How to orchestrate pipelines with Airflow
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


The Airflow orchestrator is an [orchestrator](./orchestrators.md) flavor 
provided with the ZenML `airflow` integration that uses 
[Airflow](https://airflow.apache.org/) to run your pipelines.

{% hint style="warning" %}
If you're going to use a remote deployment of Airflow, you'll also need a [remote ZenML deployment](../../getting-started/deploying-zenml/deploying-zenml.md).
{% endhint %}

## When to use it

You should use the Airflow orchestrator if
* you're looking for a proven production-grade orchestrator.
* you're already using Airflow.
* you want to run your pipelines locally.
* you're willing to deploy and maintain Airflow.

## How to deploy it

The Airflow orchestrator can be used to run pipelines locally as well as remotely.
In the local case, no additional setup is necessary.

There are many options to use a deployed Airflow server:
- Use one of [ZenML's Airflow stack recipes](https://github.com/zenml-io/mlops-stacks). This is the simplest solution to
get ZenML working with Airflow, as the recipe also takes care of additional steps such
as installing required Python dependencies in your Airflow server environment.
- Use a managed deployment of Airflow such as [Google Cloud Composer](https://cloud.google.com/composer), [Amazon MWAA](https://aws.amazon.com/managed-workflows-for-apache-airflow/) or [Astronomer](https://www.astronomer.io/).
- Deploy Airflow manually. Check out the official [Airflow docs](https://airflow.apache.org/docs/apache-airflow/stable/production-deployment.html) for more information.

If you're not using a stack recipe to deploy Airflow, there are some additional python packages that you'll need
to install in the Python environment of your Airflow server: 
- `pydantic~=1.9.2`: The Airflow DAG files that ZenML creates for you require Pydantic to parse and validate
configuration files.
- `apache-airflow-providers-docker` or `apache-airflow-providers-cncf-kubernetes`, depending on which Airflow operator you'll be using to run your pipeline steps. Check out [this section](#using-different-airflow-operators)
for more information on supported operators.

## How to use it

To use the Airflow orchestrator, we need:
* The ZenML `airflow` integration installed. If you haven't done so, run 
    ```shell
    zenml integration install airflow
    ```
* [Docker](https://www.docker.com) installed and running.
* The orchestrator registered and part of our active stack:
```shell
zenml orchestrator register <ORCHESTRATOR_NAME> \
    --flavor=airflow \
    --local=True  # set this to `False` if using a remote Airflow deployment

# Register and activate a stack with the new orchestrator
zenml stack register <STACK_NAME> -o <ORCHESTRATOR_NAME> ... --set
```

{% tabs %}
{% tab title="Local" %}

In the local case, we need to install one additional Python package
that is needed for the local Airflow server:
```bash
pip install apache-airflow-providers-docker
```

Once that is installed, we can start the local Airflow server by running:
```shell
zenml stack up
```

This command will start up an Airflow server on your local machine
that's running in the same Python environment that you used to
provision it. When it is finished, it will print a 
username and password which you can use to log in to the Airflow UI
[here](http://0.0.0.0:8080).

As long as you didn't configure any custom value for the `dag_output_dir`
attribute of your orchestrator, running a pipeline locally is as simple 
as calling:

```shell
python file_that_runs_a_zenml_pipeline.py
```

This call will produce a `.zip` file containing a representation of your ZenML
pipeline to the Airflow DAGs directory. From there, the local Airflow server
will load it and run your pipeline (It might take a few seconds until the pipeline
shows up in the Airflow UI).
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

In the remote case, the Airflow orchestrator works differently than other ZenML orchestrators.
Executing a python file which runs a pipeline by calling `pipeline.run()` will not actually run
the pipeline, but instead will create a `.zip` file containing an Airflow representation of your
ZenML pipeline. In one additional step, you need to make sure this zip file ends up in the
[DAGs directory](https://airflow.apache.org/docs/apache-airflow/stable/concepts/overview.html#architecture-overview) of your Airflow deployment.

{% endtab %}
{% endtabs %}

{% hint style="info" %}
ZenML will build a Docker image called `<CONTAINER_REGISTRY_URI>/zenml:<PIPELINE_NAME>`
which includes your code and use it to run your pipeline steps in Airflow. 
Check out [this page](../../advanced-guide/pipelines/containerization.md)
if you want to learn more about how ZenML builds these images and how you can 
customize them.
{% endhint %}

### Additional configuration

For additional configuration of the Airflow orchestrator, you can pass
`AirflowOrchestratorSettings` when defining or running your pipeline.
Check out the
[API docs](https://apidocs.zenml.io/latest/integration_code_docs/integrations-airflow/#zenml.integrations.airflow.flavors.airflow_orchestrator_flavor.AirflowOrchestratorSettings)
for a full list of available attributes and [this docs page](../..//advanced-guide/pipelines/settings.md)
for more information on how to specify settings.

### Enabling CUDA for GPU-backed hardware

Note that if you wish to use this orchestrator to run steps on a GPU, you will
need to follow [the instructions on this page](../../advanced-guide/pipelines/gpu-hardware.md) to ensure that it works. It
requires adding some extra settings customization and is essential to enable
CUDA for the GPU to give its full acceleration.

### Using different Airflow operators

Airflow operators specify how a step in your pipeline gets executed.
As ZenML relies on Docker images to run pipeline steps, only operators that support
executing a Docker image work in combination with ZenML. Airflow comes with two
operators that support this:
* the `DockerOperator` runs the Docker images for executing your pipeline steps
on the same machine that your Airflow server is running on. For this to work, the
server environment needs to have the `apache-airflow-providers-docker` package
installed. 
* the `KubernetesPodOperator` runs the Docker image on a pod in the Kubernetes
cluster that the Airflow server is deployed to. For this to work, the
server environment needs to have the `apache-airflow-providers-cncf-kubernetes` package
installed.

You can specify which operator to use and additional arguments to it as follows:
```python
from zenml.pipelines import pipeline
from zenml.steps import step
from zenml.integrations.airflow.flavors.airflow_orchestrator_flavor import AirflowOrchestratorSettings

airflow_settings = AirflowOrchestratorSettings(
    operator="docker"  # or "kubernetes_pod"
    # Dictionary of arguments to pass to the operator __init__ method
    operator_args={}
)


# Using the operator for a single step
@step(settings={"orchestrator.airflow": airflow_settings})
def my_step(...)


# Using the operator for all steps in your pipeline
@pipeline(settings={"orchestrator.airflow": airflow_settings})
def my_pipeline(...)
```

#### Custom operators

If you want to use any other operator to run your steps, you can specify
the `operator` in your `AirflowSettings` as a path to the python operator
class:
```python
from zenml.integrations.airflow.flavors.airflow_orchestrator_flavor import AirflowOrchestratorSettings

airflow_settings = AirflowOrchestratorSettings(
    # This could also be a reference to one of your custom classes.
    # e.g. `my_module.MyCustomOperatorClass` as long as the class
    # is importable in your Airflow server environment
    operator="airflow.providers.docker.operators.docker.DockerOperator"
    # Dictionary of arguments to pass to the operator __init__ method
    operator_args={}
)
```

#### Custom DAG generator file

To run a pipeline in Airflow, ZenML creates a Zip archive which contains two files:
* A Json configuration file that the orchestrator creates. This file contains all
the information required to create the Airflow DAG to run the pipeline.
* A Python file which reads this configuration file and actually creates the Airflow
DAG. We call this file the `DAG generator` and you can find the implementation
[here](https://github.com/zenml-io/zenml/blob/main/src/zenml/integrations/airflow/orchestrators/dag_generator.py).

If you need more control over how the Airflow DAG is generated, you can provide a
custom DAG generator file using the setting `custom_dag_generator`. This setting
will need to reference a Python module that can be imported in your active Python environment.
It will additionally need to contain the same classes (`DagConfiguration` and `TaskConfiguration`)
and constants (`ENV_ZENML_AIRFLOW_RUN_ID`, `ENV_ZENML_LOCAL_STORES_PATH` and `CONFIG_FILENAME`) as the
[original module](https://github.com/zenml-io/zenml/blob/main/src/zenml/integrations/airflow/orchestrators/dag_generator.py).
For this reason we suggest to start by copying the original and modifying it
according to your needs.

Check out our docs on how to apply settings to your pipelines [here](../../advanced-guide/pipelines/settings.md).


A concrete example of using the Airflow orchestrator can be found 
[here](https://github.com/zenml-io/zenml/tree/main/examples/airflow_orchestration).

For more information and a full list of configurable attributes of the Airflow 
orchestrator, check out the [API Docs](https://apidocs.zenml.io/latest/api_docs/integration_code_docs/integrations-airflow/#zenml.integrations.airflow.orchestrators.airflow_orchestrator.AirflowOrchestrator).
