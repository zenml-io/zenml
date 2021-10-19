# Get in production with Airflow
ZenML pipelines can be executed natively as Airflow DAGs. This brings together the power of the Airflow 
orchestration with the ML-specific benefits of ZenML pipelines. Each ZenML step can be run as an Airflow 
[`PythonOperator`](https://airflow.apache.org/docs/apache-airflow/stable/howto/operator/python.html), and 
executes Airflow natively.

## Pre-requisites
In order to run this example, you need to install and initialize ZenML:

### Installation
```bash
# install CLI
pip install zenml apache-airflow tensorflow
```

### Set up airflow
Setting up airflow locally is quite simple, and there is a handy guide available 
[here](https://airflow.apache.org/docs/apache-airflow/stable/start/local.html). 
We will assume in this example that Airflow has been set up with the following settings:

Airflow home is at `~/airflow`:
```
export AIRFLOW_HOME=~/airflow
```

In the `~/airflow/airflow.cfg`:
```
dags_folder = ~/airflow/dags/
dag_discovery_safe_mode = False
```

### Initialize zenml at the Airflow DAGs folder root:
```bash
cd ~/airflow/dags
git init
zenml init
```

### Create a new Airflow Stack
```bash
zenml orchestrator register airflow_orchestrator airflow
zenml stack set airflow_stack
```

### Copy the runner script to the Airflow dag folder:
```bash
cd ~
git clone https://github.com/zenml-io/zenml.git
cp -r zenml/examples/airflow/run.py ~/airflow/dags/zenml_mnist.py
```

### Run the project
Now we're ready. Open up airflow with the following commands:

```bash
airflow scheduler
```
And in another terminal
```bash
airflow webserver --port 8080
```

### Trigger the airflow DAG
Now you would be able to see the `mnist` dag in your browser at [localhost](http://0.0.0.0:8080/) (you might be asked to login with 
the credentials you set up when you installed Airflow). Unpause it, and trigger it via the UI or run the 
following script:

```bash
python ~/zenml/examples/airflow/trigger_dag.py
```

You would now be able to see the executed dag [here](http://0.0.0.0:8080/tree?dag_id=mnist)

### Clean up
In order to clean up, in the root of your repo, delete the remaining zenml and airflow references.

```python
rm -rf ~/airflow
rm -rf ~/zenml
```
