# 🏃 Run pipelines in production with Airflow

ZenML pipelines can be executed natively as Airflow DAGs. This brings together
the power of the Airflow orchestration with the ML-specific benefits of ZenML
pipelines. Each ZenML step runs in a separate Docker container which is
scheduled and started using Airflow. This example trains a simple PyTorch model
on the Fashion MNIST data set.

# 🖥 Run it locally

## ⏩ SuperQuick `airflow_orchestration` run

If you're really in a hurry and just want to see this example pipeline run
without wanting to fiddle around with all the individual installation and
configuration steps, just run the following:

```shell
zenml example run airflow_orchestration
```

## 👣 Step-by-Step

### 📄 Prerequisites

In order to run this example, you need to have [Docker](https://docs.docker.com/get-docker/)
installed to build images that run your pipeline in containers.

Next, we will install ZenML, get the code for this example and initialize a
ZenML repository:

```bash
# install CLI
pip install "zenml[server]"

# install ZenML integrations
zenml integration install airflow pytorch
pip install apache-airflow-providers-docker torchvision

# pull example
zenml example pull airflow_orchestration
cd zenml_examples/airflow_orchestration

# Initialize ZenML repo
zenml init
```


## 🖥 Run it locally

First, let's begin by spinning up a local ZenServer to enable dashboard access:

```bash
# Start a local ZenServer
zenml up
```

### 🥞 Create a new Airflow Stack

Next step is to create the local airflow stack:

```bash
# Register the local airflow orchestrator
zenml orchestrator register local_airflow --flavor=airflow

# Register the stack
zenml stack register local_airflow \
    -o local_airflow \
    -a default \
    --set
```

### 🏁️ Starting up Airflow

ZenML takes care of configuring Airflow, all we need to do is run:

```bash
zenml stack up
```

This will bootstrap Airflow, start up all the necessary components and run them
in the background. When the setup is finished, it will print username and
password for the Airflow webserver to the console.

WARNING: If you can't find the password on the console, you
can navigate to the
`<GLOBAL_CONFIG_DIR>/airflow/<ORCHESTRATOR_UUID>/standalone_admin_password.txt`
file. The username will always be `admin`.

- `GLOBAL_CONFIG_DIR` will depend on your OS.
  Run `python -c "from zenml.config.global_config import GlobalConfiguration; print(GlobalConfiguration().config_directory)"`
  to get the path for your machine.
- `ORCHESTRATOR_UUID` will be the unique ID of the Airflow orchestrator. There
  will be only one
  folder here, so you can just navigate to the one that is present.

### 📆 Run or schedule the Airflow DAG

```bash
python run.py
```

Sometimes you don't want to run your pipeline only once, instead you want to
schedule them with a predefined frequency.
To schedule the DAG to run every 15 minutes for the next hour, simply
open `run.py` and uncomment the lines at the
end of the file.

After a few seconds, you should be able to see the pipeline run in
the [ZenML dashboard](http://localhost:8237/pipelines/all-runs) or the
[Airflow UI](http://localhost:8080/home).

### 🧽 Clean up

In order to clean up, tear down the Airflow stack and delete the remaining ZenML
references.

```shell
zenml stack down --force
rm -rf zenml_examples
```

## ☁️ Run the same pipeline on a remote Airflow deployment

### 📄 Additional pre-requisites

* A remote ZenML server deployed to the cloud. See the 
[deployment guide](https://docs.zenml.io/platform-guide/set-up-your-mlops-platform/deploy-zenml) for
more information.
* A deployed Airflow server. See the 
[deployment section](https://docs.zenml.io/user-guide/component-guide/orchestrators/airflow#how-to-deploy-it)
for more information.
* A [remote artifact store](https://docs.zenml.io/user-guide/component-guide/artifact-stores)
as part of your stack.
* A [remote container registry](https://docs.zenml.io/user-guide/component-guide/container-registries)
as part of your stack.

```bash
# Connect to your remote ZenML deployment
zenml connect --url=<REMOTE_ZENML_URL>

# Register a remote Airflow orchestrator
zenml orchestrator register remote_airflow \
  --flavor=airflow \
  --local=False

# Pass the names of your remote artifact store and container registry
# when registering the stack here
zenml stack register remote_airflow \
    -o remote_airflow \
    -a <REMOTE_ARTIFACT_STORE_NAME> \
    -c <REMOTE_CONTAINER_REGISTRY_NAME> \
    --set
```

Check out ZenML [stack recipes](https://github.com/zenml-io/mlops-stacks)
if you're looking for an easy way to deploy all these components!

### 📆 Run or schedule the Airflow DAG

In the remote case, the Airflow orchestrator works different from other ZenML
orchestrators. Calling `python run.py` will not actually run the pipeline, 
but instead will create a `.zip` file containing an Airflow representation 
of your ZenML pipeline. In one additional step, you need to make sure this 
zip file ends up in the [DAGs directory](https://airflow.apache.org/docs/apache-airflow/stable/concepts/overview.html#architecture-overview)
of your Airflow deployment.

# 📜 Learn more

If you want to learn more about orchestrators in general or about how to build
your orchestrators in ZenML check out our [docs](https://docs.zenml.io/user-guide/component-guide/orchestrators).
