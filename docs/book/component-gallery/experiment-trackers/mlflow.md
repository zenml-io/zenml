---
description: How to log and visualize experiments with MLflow
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


The MLflow Experiment Tracker is an [Experiment Tracker](./experiment-trackers.md) 
flavor provided with the MLflow ZenML integration that uses 
[the MLflow tracking service](https://mlflow.org/docs/latest/tracking.html) 
to log and visualize information from your pipeline steps (e.g. models, 
parameters, metrics).

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
* if you or your team already have a shared MLflow Tracking service deployed
somewhere on-premise or in the cloud, and you would like to connect ZenML to it
to share the artifacts and metrics logged by your pipelines

You should consider one of the other [Experiment Tracker flavors](./experiment-trackers.md#experiment-tracker-flavors)
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
This scenario requires that you use a [local Artifact Store](../artifact-stores/local.md)
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

* [Databricks scenario](https://www.databricks.com/product/managed-mlflow):
This scenario assumes that you have a Databricks workspace, and you want to
use the managed MLflow Tracking server it provides. This option requires
[authentication related parameters](#authentication-methods) to be configured
for the MLflow Experiment Tracker.

### Authentication Methods

You need to configure the following credentials for authentication to a remote
MLflow tracking server:

* `tracking_uri`: The URL pointing to the MLflow tracking server. If using
an MLflow Tracking Server managed by Databricks, then the value of this
attribute should be `"databricks"`.
* `tracking_username`: Username for authenticating with the MLflow tracking
server. 
* `tracking_password`: Password for authenticating with the MLflow tracking
server. 
* `tracking_token` (in place of `tracking_username` and `tracking_password`): 
Token for authenticating with the MLflow tracking server.
* `tracking_insecure_tls` (optional): Set to skip verifying the MLflow tracking server SSL
certificate.
* `databricks_host`: The host of the Databricks workspace with the MLflow managed
server to connect to. This is only required if `tracking_uri` value is set to
`"databricks"`. More information:
[Access the MLflow tracking server from outside Databricks](https://docs.databricks.com/applications/mlflow/access-hosted-tracking-server.html)
    
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

# You can also register it like this:
# zenml experiment-tracker register mlflow_experiment_tracker --flavor=mlflow \ 
#    --tracking_uri=<URI> --tracking_username=<USERNAME> --tracking_password=<PASSWORD>

# Register and set a stack with the new experiment tracker
zenml stack register custom_stack -e mlflow_experiment_tracker ... --set
```
{% endtab %}

{% tab title="Secrets Manager (Recommended)" %}

This method requires you to include a [Secrets Manager](../secrets-managers/secrets-managers.md)
in your stack and configure a ZenML secret to store the MLflow tracking service
credentials securely.

You can register the secret using the `zenml secret register` command:

```shell 
# Register a secret called `mlflow_secret` with key-value pairs for the
# username and password to authenticate with the MLflow tracking server
zenml secrets-manager secret register mlflow_secret \
    --username=<USERNAME> \
    --password=<PASSWORD>
```

Once the secret is registered, you can use it to configure the MLflow Experiment
Tracker:

```shell
# Reference the username and password in our experiment tracker component
zenml experiment-tracker register mlflow \
    --flavor=mlflow \
    --tracking_username={{mlflow_secret.username}} \
    --tracking_password={{mlflow_secret.password}} \
    ...
```

{% hint style="info" %}
Read more about [Secrets Manager](../secrets-managers/secrets-managers.md) and
[Secrets](../secrets-managers/secrets.md) in the ZenML documentation.
For more practical examples of how to use the Secrets Manager, check out the
[Secrets management practical guide](../../advanced-guide/practical/secrets-management.md).
{% endhint %}
{% endtab %}
{% endtabs %}

For more, up-to-date information on the MLflow Experiment Tracker implementation
and its configuration, you can have a look at [the API docs](https://apidocs.zenml.io/latest/integration_code_docs/integrations-mlflow/#zenml.integrations.mlflow.experiment_trackers.mlflow_experiment_tracker).

## How do you use it?

To be able to log information from a ZenML pipeline step using the MLflow
Experiment Tracker component in the active stack, you need to enable an
experiment tracker using the `@step` decorator. Then use MLflow's logging
or auto-logging capabilities as you would normally do, e.g.:

```python
import mlflow

@step(experiment_tracker="<MLFLOW_TRACKER_STACK_COMPONENT_NAME>")
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

### Additional configuration

For additional configuration of the MLflow experiment tracker, you can pass
`MLFlowExperimentTrackerSettings` to create nested runs or add additional tags
to your MLflow runs:

```python
import mlflow
from zenml.integrations.mlflow.flavors.mlflow_experiment_tracker_flavor import MLFlowExperimentTrackerSettings

mlflow_settings = MLFlowExperimentTrackerSettings(
    nested=True,
    tags={"key": "value"}
)

@step(
    experiment_tracker="<MLFLOW_TRACKER_STACK_COMPONENT_NAME>",
    settings={
        "experiment_tracker.mlflow": mlflow_settings
    }
)
def step_one(
    data: np.ndarray,
) -> np.ndarray:
    ...
```

Check out the
[API docs](https://apidocs.zenml.io/latest/integration_code_docs/integrations-mlflow/#zenml.integrations.mlflow.flavors.mlflow_experiment_tracker_flavor.MLFlowExperimentTrackerSettings)
for a full list of available attributes and [this docs page](../..//advanced-guide/pipelines/settings.md)
for more information on how to specify settings.

You can also check out our examples pages for working examples that use the
MLflow Experiment Tracker in their stacks:

- [Track Experiments with MLflow](https://github.com/zenml-io/zenml/tree/main/examples/mlflow_tracking)
