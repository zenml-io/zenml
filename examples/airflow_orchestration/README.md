# 🏃 Run pipeline in production with Airflow

ZenML pipelines can be executed natively as Airflow DAGs. This brings together
the power of the Airflow orchestration with the ML-specific benefits of ZenML
pipelines. Each ZenML step can be run as an Airflow
[`PythonOperator`](https://airflow.apache.org/docs/apache-airflow/stable/howto/operator/python.html),
and executes Airflow natively. We will use the MNIST dataset again (pull it from
a Mock API).

Note that this tutorial installs and deploys Airflow locally on your machine,
but in a production setting that part might be already done. Please read the
other airflow tutorials that cover that case.

# 🖥 Run it locally

## ⏩ SuperQuick `airflow_local` run

If you're really in a hurry, and you want just to see this example pipeline run,
without wanting to fiddle around with all the individual installation and
configuration steps, just run the following:

```shell
zenml example run airflow_orchestration
```


## 👣 Step-by-Step
### 📄 Prerequisites 

In order to run this example, you need to install and initialize ZenML and
Airflow.

```bash
# install CLI
pip install zenml

# install ZenML integrations
zenml integration install airflow sklearn

# pull example
zenml example pull airflow_orchestration
cd zenml_examples/airflow_orchestration

# Initialize ZenML repo
zenml init
```

### 🥞 Create a new Airflow Stack

```bash
zenml orchestrator register airflow_orchestrator --type airflow
zenml stack register airflow_stack \
    -m local_metadata_store \
    -a local_artifact_store \
    -o airflow_orchestrator
zenml stack set airflow_stack
```

### 🏁️ Starting up Airflow

ZenML takes care of configuring Airflow, all we need to do is run:

```bash
zenml stack up
```

This will bootstrap Airflow, start up all the necessary components and run them
in the background. When the setup is finished, it will print username and
password for the Airflow webserver to the console.

{% hint style="warning" %} If you can't find the password on the console, you
can navigate to the
`APP_DIR / airflow / airflow_root / STACK_UUID / standalone_admin_password.txt`
file. The username will always be `admin`.

- APP_DIR will depend on your os. See which path corresponds to your OS
  [here](https://click.palletsprojects.com/en/8.0.x/api/#click.get_app_dir).
- STACK_UUID will be the unique id of the airflow_stack. There will be only one
  folder here, so you can just navigate to the one that is present.
  {% endhint %}

### 📆 Schedule the airflow DAG

To schedule the DAG, simply run:

```bash
python run_schedule.py
```

After a few seconds, you should be able to see the executed dag
[here](http://0.0.0.0:8080/tree?dag_id=mnist_pipeline)

### 🧽 Clean up

In order to clean up, tear down the Airflow stack and delete the remaining ZenML
references.

```shell
zenml stack down --force
rm -rf zenml_examples
```

# 📜 Learn more

Our docs regarding the airflow orchestrator integration can be found [here](TODO: Link to docs).

If you want to learn more about orchestrators in general or about how to build your own orchestrators in zenml
check out our [docs](TODO: Link to docs)
