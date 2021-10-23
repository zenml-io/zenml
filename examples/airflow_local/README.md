# Get in production with Airflow
ZenML pipelines can be executed natively as Airflow DAGs. This brings together the power of the Airflow 
orchestration with the ML-specific benefits of ZenML pipelines. Each ZenML step can be run as an Airflow 
[`PythonOperator`](https://airflow.apache.org/docs/apache-airflow/stable/howto/operator/python.html), and 
executes Airflow natively. We will use the MNIST dataset again (pull it from a Mock API).

Note that this tutorial installs and deploys Airflow locally on your machine, but in a production setting that part might be already done. 
Please read the other airflow tutorials that cover that case.

## Pre-requisites
In order to run this example, you need to install and initialize ZenML and Airflow.

### Installation
```bash
# install CLI
pip install zenml apache-airflow tensorflow

# pull example
zenml example pull airflow_local
cd zenml_examples/airflow_local

# initialize
git init
zenml init
```

### Create a new Airflow Stack
```bash
zenml orchestrator register airflow_orchestrator airflow
zenml stack register airflow_stack \
    -m local_metadata_store \
    -a local_artifact_store \
    -o airflow_orchestrator
zenml stack set airflow_stack
```

### Trigger the airflow DAG
Now you would be able to see the `mnist` dag in your browser at [localhost](http://0.0.0.0:8080/) (you will be asked to login with 
the credentials in the `standalone_admin_password.txt` file). Trigger it via the UI or run the 
following script:

```bash
python trigger_dag.py
```

You would now be able to see the executed dag [here](http://0.0.0.0:8080/tree?dag_id=mnist)

### Clean up
In order to clean up, delete the remaining zenml references.

```shell
rm -rf zenml_examples
```
