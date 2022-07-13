---
description: Log and visualize extended pipeline run information with MLflow
---

The MLflow Experiment Tracker is an [Experiment Tracker](./overview.md) flavor
provided with the MLflow ZenML integration that uses [the MLflow tracking service](https://mlflow.org/docs/latest/tracking.html) to log and visualize information from your pipeline steps (e.g. models, parameters,
metrics).

## When would you want to use it?

[MLflow Tracking](https://www.mlflow.org/docs/latest/tracking.html) is a very
popular tool that you would normally use in the iterative ML experimentation
phase to track and visualize experiment results. That doesn't mean that it
cannot be repurposed to track and visualize the results produced by your
automated pipeline runs, as you make the transition towards a more production
oriented workflow.

You should use the MLflow Experiment Tracker:
* if you have already been using MLflow to track experiment results for your
project and would like to continue doing so as you are incorporating MLOps
workflows and best practices in your project through ZenML.
* if you are looking for a more visually interactive way of navigating the
results produced from your ZenML pipeline runs (e.g. models, metrics, datasets)
* if you or your team already have a shared MLFlow Tracking service deployed
somewhere on-premise or in the cloud, and you would like to connect ZenML to it
to share the artifacts and metrics logged by your pipelines

You should consider one of the other [Experiment Tracker flavors](./overview.md#experiment-tracker-flavors)
if you have never worked with MLflow before and would rather use another
experiment tracking tool that you are more familiar with.

## How do you deploy it?


The MLflow Experiment Tracker flavor is provided by the MLflow ZenML
integration, you need to install it on your local machine to be able to register
an MLflow Experiment Tracker and add it to your stack:

```shell
zenml integration install mlflow -y
```

The MLflow Experiment Tracker can be configured to accommodate the following
[MLflow deployment scenarios](https://mlflow.org/docs/latest/tracking.html#how-runs-and-artifacts-are-recorded):

* [Scenario 1](https://mlflow.org/docs/latest/tracking.html#scenario-1-mlflow-on-localhost):
This scenario requires that you use a [local Artifact Store](../artifact_stores/local.md)
alongside the MLflow Experiment Tracker in your ZenML stack. The local Artifact
Store comes with limitations regarding what other types of components you can
use in the same stack. This scenario should only be used to run ZenML locally
and is not suitable for collaborative and production settings. No parameters
need to be supplied when configuring the MLflow Experiment Tracker, e.g:

```shell
# Register the MLflow experiment tracker
zenml experiment-tracker register mlflow_experiment_tracker --flavor=mlflow

# Register and set a stack with the new experiment tracker
zenml stack register custom_stack -e mlflow_experiment_tracker ... --set
```

* [Scenario 5](https://mlflow.org/docs/latest/tracking.html#scenario-5-mlflow-tracking-server-enabled-with-proxied-artifact-storage-access):
This scenario assumes that you have already deployed an MLflow Tracking Server
enabled with proxied artifact storage access. There is no restriction regarding
what other types of components it can be combined with. This option requires
[authentication related parameters](#authentication-methods) to be configured
for the MLflow Experiment Tracker.

### Authentication Methods

You need to configure the following credentials for authentication to a remote
MLflow tracking server:

* `tracking_uri`: The URL pointing to the MLflow tracking server.
* `tracking_username`: Username for authenticating with the MLflow tracking
server. 
* `tracking_password`: Password for authenticating with the MLflow tracking
server. 
* `tracking_token`: Token for authenticating with the MLflow tracking server.
* `tracking_insecure_tls`: Set to skip verifying the MLflow tracking server SSL
certificate.
    
Either `tracking_token` or `tracking_username` and `tracking_password` must be
specified.

{% tabs %}
{% tab title="Basic Authentication" %}

This option configures the credentials for the MLflow tracking service directly
as stack component attributes.

{% hint style="warning" %}
This is not recommended for production settings as the credentials won't be
stored securely and will be clearly visible in the stack configuration.
{% endhint %}

```shell
# Register the MLflow experiment tracker
zenml experiment-tracker register mlflow_experiment_tracker --flavor=mlflow \ 
    --tracking_uri=<URI> --tracking_token=<token>

# Register and set a stack with the new experiment tracker
zenml stack register custom_stack -e mlflow_experiment_tracker ... --set
```
{% endtab %}

{% tab title="Secrets Manager (Recommended)" %}

This method requires you to include a [Secrets Manager](../secrets_managers/overview.md)
in your stack and configure a ZenML secret to store the MLflow tracking service
credentials securely.

{% hint style="warning" %}
**This method is not yet supported!**

We are actively working on adding Secrets Manager support to the MLflow
Experiment Tracker.
{% endhint %}
{% endtab %}
{% endtabs %}

For more, up-to-date information on the MLflow Experiment Tracker implementation
and its configuration, you can have a look at [the API docs](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.mlflow.experiment_trackers.mlflow_experiment_tracker).

## How do you use it?

To be able to log information from a ZenML pipeline step using the MLflow
Experiment Tracker component in the active stack, you need to use the
`enable_mlflow` step decorator on all pipeline steps where you plan on doing
that. Then use MLFlow's logging or auto-logging capabilities as you would
normally do, e.g.:

```python
from zenml.integrations.mlflow.mlflow_step_decorator import enable_mlflow
import mlflow

# Define the step and enable mlflow - order of decorators is important here
@enable_mlflow
@step
def tf_trainer(
    x_train: np.ndarray,
    y_train: np.ndarray,
) -> tf.keras.Model:
    """Train a neural net from scratch to recognize MNIST digits return our
    model or the learner"""
    
    # compile model

    mlflow.tensorflow.autolog()
    
    # train model

    # log additional information to MLflow explicitly if needed

    mlflow.log_param(...)
    mlflow.log_metric(...)
    mlflow.log_artifact(...)

    return model
```

The `enable_mlflow` decorator accepts additional parameters. An especially
useful argument is `nested=True`. When supplied, it will log the parameters,
metrics and artifacts of each step into nested runs, e.g.:

```python
from zenml.integrations.mlflow.mlflow_step_decorator import enable_mlflow
import mlflow

@enable_mlflow(nested=True)
@step
def step_one(
    data: np.ndarray,
) -> np.ndarray:
    ...

@enable_mlflow(nested=True)
@step
def step_two(
    data: np.ndarray,
) -> np.ndarray:
    ...
```

You can also check out our examples pages for working examples that use the
MLflow Experiment Tracker in their stacks:

- [Track Experiments with MLflow](https://github.com/zenml-io/zenml/tree/main/examples/mlflow_tracking)
