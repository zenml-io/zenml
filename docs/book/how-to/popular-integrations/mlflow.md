---
description: Learn how to use the MLflow Experiment Tracker with ZenML.
---

# MLflow Experiment Tracker

The ZenML MLflow Experiment Tracker integration and stack component allows you to log and visualize information from your pipeline steps using MLflow, without having to write extra MLflow code.

## Prerequisites

To use the MLflow Experiment Tracker, you'll need:

- ZenML `mlflow` integration installed (`zenml integration install mlflow -y`)
- An MLflow deployment, either local (scenario 1) or remote with proxied artifact storage (scenario 5)

## Configuring the Experiment Tracker

There are two main MLflow deployment scenarios:

1. Local (scenario 1): Use a local artifact store, only suitable for running ZenML locally. No extra configuration needed.

```bash
zenml experiment-tracker register mlflow_experiment_tracker --flavor=mlflow
zenml stack register custom_stack -e mlflow_experiment_tracker ... --set
```

2. Remote with proxied artifact storage (scenario 5): Can be used with any stack components. Requires authentication configuration.

For remote, you'll need to configure authentication using one of:
- Basic authentication (not recommended for production)
- ZenML secrets (recommended)

To use ZenML secrets:

```bash
zenml secret create mlflow_secret \
   --username=<USERNAME> \
   --password=<PASSWORD>
   
zenml experiment-tracker register mlflow \
   --flavor=mlflow \
   --tracking_username={{mlflow_secret.username}} \
   --tracking_password={{mlflow_secret.password}} \
   ...
```

## Using the Experiment Tracker

To log information with MLflow in a pipeline step:

1. Enable the experiment tracker using the `@step` decorator 
2. Use MLflow's logging or auto-logging capabilities as usual

```python
import mlflow

@step(experiment_tracker="<MLFLOW_TRACKER_STACK_COMPONENT_NAME>")
def train_step(...):
   mlflow.tensorflow.autolog()
   
   mlflow.log_param(...)
   mlflow.log_metric(...)
   mlflow.log_artifact(...)
   
   ...
```

## Viewing Results

You can find the URL to the MLflow experiment for a ZenML run:

```python
last_run = client.get_pipeline("<PIPELINE_NAME>").last_run
trainer_step = last_run.get_step("<STEP_NAME>")
tracking_url = trainer_step.run_metadata["experiment_tracker_url"].value
```

This will link to your deployed MLflow instance UI, or the local MLflow experiment file.

## Additional Configuration

You can further configure the experiment tracker using `MLFlowExperimentTrackerSettings`:

```python
from zenml.integrations.mlflow.flavors.mlflow_experiment_tracker_flavor import MLFlowExperimentTrackerSettings

mlflow_settings = MLFlowExperimentTrackerSettings(
   nested=True,
   tags={"key": "value"}  
)

@step(
   experiment_tracker="<MLFLOW_TRACKER_STACK_COMPONENT_NAME>",
   settings={
       "experiment_tracker": mlflow_settings
   }  
)
```

For more details and advanced options, see the [full MLflow Experiment Tracker documentation](../../component-guide/experiment-trackers/mlflow.md).

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


