---
description: Orchestrating your pipelines to run on Airflow.
---

# Airflow Orchestrator

ZenML pipelines can be executed natively as [Airflow](https://airflow.apache.org/) 
DAGs. This brings together the power of the Airflow orchestration with the 
ML-specific benefits of ZenML pipelines. Each ZenML step runs in a separate 
Docker container which is scheduled and started using Airflow.

{% hint style="warning" %}
If you're going to use a remote deployment of Airflow, you'll also need
a [remote ZenML deployment](../../getting-started/deploying-zenml/README.md).
{% endhint %}

### When to use it

You should use the Airflow orchestrator if

* you're looking for a proven production-grade orchestrator.
* you're already using Airflow.
* you want to run your pipelines locally.
* you're willing to deploy and maintain Airflow.

### How to deploy it

The Airflow orchestrator can be used to run pipelines locally as well as remotely. In the local case, no additional
setup is necessary.

There are many options to use a deployed Airflow server:

* Use [the ZenML GCP Terraform module](../../how-to/infrastructure-deployment/stack-deployment/deploy-a-cloud-stack-with-terraform.md)
  which includes a [Google Cloud Composer](https://cloud.google.com/composer) component.
* Use a managed deployment of Airflow such as [Google Cloud Composer](https://cloud.google.com/composer)
  , [Amazon MWAA](https://aws.amazon.com/managed-workflows-for-apache-airflow/),
  or [Astronomer](https://www.astronomer.io/).
* Deploy Airflow manually. Check out the
  official [Airflow docs](https://airflow.apache.org/docs/apache-airflow/stable/production-deployment.html) for more
  information.

If you're not using the ZenML GCP Terraform module to deploy Airflow, there are some additional Python
packages that you'll need to install in the Python environment of your Airflow server:

* `pydantic~=2.7.1`: The Airflow DAG files that ZenML creates for you require Pydantic to parse and validate
  configuration files.
* `apache-airflow-providers-docker` or `apache-airflow-providers-cncf-kubernetes`, depending on which Airflow operator
  you'll be using to run your pipeline steps. Check out [this section](airflow.md#using-different-airflow-operators) for
  more information on supported operators.

### How to use it

To use the Airflow orchestrator, we need:

* The ZenML `airflow` integration installed. If you haven't done so, run

  ```shell
  zenml integration install airflow
  ```
* [Docker](https://docs.docker.com/get-docker/) installed and running.
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
Due to dependency conflicts, we need to install the Python packages to start a local Airflow server
in a separate Python environment.

```bash
# Create a fresh virtual environment in which we install the Airflow server dependencies
python -m venv airflow_server_environment
source airflow_server_environment/bin/activate

# Install the Airflow server dependencies
pip install "apache-airflow==2.4.0" "apache-airflow-providers-docker<3.8.0" "pydantic~=2.7.1"
```

Before starting the local Airflow server, we can set a few environment variables to configure it:
* `AIRFLOW_HOME`: This variable defines the location where the Airflow server stores its database and configuration
   files. The default value is `~/airflow`.
* `AIRFLOW__CORE__DAGS_FOLDER`: This variable defines the location where the Airflow server looks for DAG files. The
   default value is `<AIRFLOW_HOME>/dags`.
* `AIRFLOW__SCHEDULER__DAG_DIR_LIST_INTERVAL`: This variable controls how often the Airflow scheduler checks for new or
   updated DAGs. By default, the scheduler will check for new DAGs every 30 seconds. This variable can be used to
   increase or decrease the frequency of the checks, depending on the specific needs of your pipeline.

{% hint style="warning" %}
When running this on MacOS, you might need to set the `no_proxy` environment variable to prevent crashes due to a bug
in Airflow (see [this page](https://github.com/apache/airflow/issues/28487) for more information):

```bash
export no_proxy=*
```
{% endhint %}

We can now start the local Airflow server by running the following command:
```bash
# Switch to the Python environment that has Airflow installed before running this command
airflow standalone
```

This command will start up an Airflow server on your local machine. During the startup, it will print a username and
password which you can use to log in to the Airflow UI [here](http://0.0.0.0:8080).

We can now switch back the Python environment in which ZenML is installed and run a pipeline:
```shell
# Switch to the Python environment that has ZenML installed before running this command
python file_that_runs_a_zenml_pipeline.py
```

This call will produce a `.zip` file containing a representation of your ZenML pipeline for Airflow.
The location of this `.zip` file will be in the logs of the command above. We now need to copy this file
to the Airflow DAGs directory, from where the local Airflow server will load it and run your pipeline
(It might take a few seconds until the pipeline shows up in the Airflow UI).
To figure out the DAGs directory, we can run `airflow config get-value core DAGS_FOLDER` while having our
Python environment with the Airflow installation active.

To make this process easier, we can configure our ZenML Airflow orchestrator to automatically copy the `.zip` file
to this directory for us. To do so, run the following command:
```bash
# Switch to the Python environment that has ZenML installed before running this command
zenml orchestrator update --dag_output_dir=<AIRFLOW_DAG_DIRECTORY>
```

Now that we've set this up, running a pipeline in Airflow is as simple as just running the Python file:
```shell
# Switch to the Python environment that has ZenML installed before running this command
python file_that_runs_a_zenml_pipeline.py
```
{% endtab %}

{% tab title="Remote" %}
When using the Airflow orchestrator with a remote deployment, you'll additionally need:

* A remote ZenML server deployed to the cloud. See
  the [deployment guide](../../getting-started/deploying-zenml/README.md) 
  for more information.
* A deployed Airflow server. See the [deployment section](airflow.md#how-to-deploy-it) for more information.
* A [remote artifact store](../artifact-stores/artifact-stores.md) as part of your stack.
* A [remote container registry](../container-registries/container-registries.md) as part of your stack.

In the remote case, the Airflow orchestrator works differently than other ZenML orchestrators. Executing a python file
which runs a pipeline by calling `pipeline.run()` will not actually run the pipeline, but instead will create a `.zip`
file containing an Airflow representation of your ZenML pipeline. In one additional step, you need to make sure this zip
file ends up in
the [DAGs directory](https://airflow.apache.org/docs/apache-airflow/stable/concepts/overview.html#architecture-overview)
of your Airflow deployment.
{% endtab %}
{% endtabs %}

{% hint style="info" %}
ZenML will build a Docker image called `<CONTAINER_REGISTRY_URI>/zenml:<PIPELINE_NAME>` which includes your code and use
it to run your pipeline steps in Airflow. Check
out [this page](/docs/book/how-to/customize-docker-builds/README.md) if you want to learn
more about how ZenML builds these images and how you can customize them.
{% endhint %}

#### Scheduling

You can [schedule pipeline runs](../../how-to/pipeline-development/build-pipelines/schedule-a-pipeline.md)
on Airflow similarly to other orchestrators. However, note that 
**Airflow schedules always need to be set in the past**, e.g.,:

```python
from datetime import datetime, timedelta

from zenml.pipelines import Schedule

scheduled_pipeline = fashion_mnist_pipeline.with_options(
    schedule=Schedule(
        start_time=datetime.now() - timedelta(hours=1),  # start in the past
        end_time=datetime.now() + timedelta(hours=1),
        interval_second=timedelta(minutes=15),  # run every 15 minutes
        catchup=False,
    )
)
scheduled_pipeline()
```

#### Airflow UI

Airflow comes with its own UI that you can use to find further details about your pipeline runs, such as the logs of
your steps. For local Airflow, you can find the Airflow UI at [http://localhost:8080](http://localhost:8080) by default.

{% hint style="info" %}
If you cannot see the Airflow UI credentials in the console, you can find the
password in `<AIRFLOW_HOME>/standalone_admin_password.txt`. `AIRFLOW_HOME` will usually be `~/airflow` unless you've
manually configured it with the `AIRFLOW_HOME` environment variable.
You can always run `airflow info` to figure out the directory for the active environment.

The username will always be `admin`.
{% endhint %}

#### Additional configuration

For additional configuration of the Airflow orchestrator, you can pass `AirflowOrchestratorSettings` when defining or
running your pipeline. Check out
the [SDK docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-airflow/#zenml.integrations.airflow.flavors.airflow\_orchestrator\_flavor.AirflowOrchestratorSettings)
for a full list of available attributes and [this docs page](/docs/book/how-to/pipeline-development/use-configuration-files/README.md) for
more information on how to specify settings.

#### Enabling CUDA for GPU-backed hardware

Note that if you wish to use this orchestrator to run steps on a GPU, you will need to
follow [the instructions on this page](/docs/book/how-to/pipeline-development/training-with-gpus/README.md) to ensure that it
works. It requires adding some extra settings customization and is essential to enable CUDA for the GPU to give its full
acceleration.

#### Using different Airflow operators

Airflow operators specify how a step in your pipeline gets executed. As ZenML relies on Docker images to run pipeline
steps, only operators that support executing a Docker image work in combination with ZenML. Airflow comes with two
operators that support this:

* the `DockerOperator` runs the Docker images for executing your pipeline steps on the same machine that your Airflow
  server is running on. For this to work, the server environment needs to have the `apache-airflow-providers-docker`
  package installed.
* the `KubernetesPodOperator` runs the Docker image on a pod in the Kubernetes cluster that the Airflow server is
  deployed to. For this to work, the server environment needs to have the `apache-airflow-providers-cncf-kubernetes`
  package installed.

You can specify which operator to use and additional arguments to it as follows:

```python
from zenml import pipeline, step
from zenml.integrations.airflow.flavors.airflow_orchestrator_flavor import AirflowOrchestratorSettings

airflow_settings = AirflowOrchestratorSettings(
    operator="docker",  # or "kubernetes_pod"
    # Dictionary of arguments to pass to the operator __init__ method
    operator_args={}
)

# Using the operator for a single step
@step(settings={"orchestrator": airflow_settings})
def my_step(...):


# Using the operator for all steps in your pipeline
@pipeline(settings={"orchestrator": airflow_settings})
def my_pipeline(...):
```

**Custom operators**

If you want to use any other operator to run your steps, you can specify the `operator` in your `AirflowSettings` as a
path to the python operator class:

```python
from zenml.integrations.airflow.flavors.airflow_orchestrator_flavor import AirflowOrchestratorSettings

airflow_settings = AirflowOrchestratorSettings(
    # This could also be a reference to one of your custom classes.
    # e.g. `my_module.MyCustomOperatorClass` as long as the class
    # is importable in your Airflow server environment
    operator="airflow.providers.docker.operators.docker.DockerOperator",
    # Dictionary of arguments to pass to the operator __init__ method
    operator_args={}
)
```

**Custom DAG generator file**

To run a pipeline in Airflow, ZenML creates a Zip archive that contains two files:

* A JSON configuration file that the orchestrator creates. This file contains all the information required to create the
  Airflow DAG to run the pipeline.
* A Python file that reads this configuration file and actually creates the Airflow DAG. We call this file
  the `DAG generator` and you can find the
  implementation [here](https://github.com/zenml-io/zenml/blob/main/src/zenml/integrations/airflow/orchestrators/dag\_generator.py)
  .

If you need more control over how the Airflow DAG is generated, you can provide a custom DAG generator file using the
setting `custom_dag_generator`. This setting will need to reference a Python module that can be imported into your
active Python environment. It will additionally need to contain the same classes (`DagConfiguration`
and `TaskConfiguration`) and constants (`ENV_ZENML_AIRFLOW_RUN_ID`, `ENV_ZENML_LOCAL_STORES_PATH` and `CONFIG_FILENAME`)
as
the [original module](https://github.com/zenml-io/zenml/blob/main/src/zenml/integrations/airflow/orchestrators/dag\_generator.py)
. For this reason, we suggest starting by copying the original and modifying it according to your needs.

Check out our docs on how to apply settings to your
pipelines [here](/docs/book/how-to/pipeline-development/use-configuration-files/README.md).

For more information and a full list of configurable attributes of the Airflow orchestrator, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-airflow/#zenml.integrations.airflow.orchestrators.airflow_orchestrator.AirflowOrchestrator) .

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>