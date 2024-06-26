---
description: Logging and visualizing experiments with MLflow.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# MLflow

The MLflow Experiment Tracker is an [Experiment Tracker](./experiment-trackers.md) flavor provided with the MLflow ZenML integration that uses [the MLflow tracking service](https://mlflow.org/docs/latest/tracking.html) to log and visualize information from your pipeline steps (e.g. models, parameters, metrics).

## When would you want to use it?

[MLflow Tracking](https://www.mlflow.org/docs/latest/tracking.html) is a very popular tool that you would normally use in the iterative ML experimentation phase to track and visualize experiment results. That doesn't mean that it cannot be repurposed to track and visualize the results produced by your automated pipeline runs, as you make the transition toward a more production-oriented workflow.

You should use the MLflow Experiment Tracker:

* if you have already been using MLflow to track experiment results for your project and would like to continue doing so as you are incorporating MLOps workflows and best practices in your project through ZenML.
* if you are looking for a more visually interactive way of navigating the results produced from your ZenML pipeline runs (e.g. models, metrics, datasets)
* if you or your team already have a shared MLflow Tracking service deployed somewhere on-premise or in the cloud, and you would like to connect ZenML to it to share the artifacts and metrics logged by your pipelines

You should consider one of the other [Experiment Tracker flavors](./experiment-trackers.md#experiment-tracker-flavors) if you have never worked with MLflow before and would rather use another experiment tracking tool that you are more familiar with.

## How do you deploy it?

The MLflow Experiment Tracker flavor is provided by the MLflow ZenML integration, you need to install it on your local machine to be able to register an MLflow Experiment Tracker and add it to your stack:

```shell
zenml integration install mlflow -y
```

The MLflow Experiment Tracker can be configured to accommodate the following [MLflow deployment scenarios](https://mlflow.org/docs/latest/tracking.html#how-runs-and-artifacts-are-recorded):

* [Scenario 1](https://mlflow.org/docs/latest/tracking.html#scenario-1-mlflow-on-localhost): This scenario requires that you use a [local Artifact Store](../artifact-stores/local.md) alongside the MLflow Experiment Tracker in your ZenML stack. The local Artifact Store comes with limitations regarding what other types of components you can use in the same stack. This scenario should only be used to run ZenML locally and is not suitable for collaborative and production settings. No parameters need to be supplied when configuring the MLflow Experiment Tracker, e.g:

```shell
# Register the MLflow experiment tracker
zenml experiment-tracker register mlflow_experiment_tracker --flavor=mlflow

# Register and set a stack with the new experiment tracker
zenml stack register custom_stack -e mlflow_experiment_tracker ... --set
```

* [Scenario 5](https://mlflow.org/docs/latest/tracking.html#scenario-5-mlflow-tracking-server-enabled-with-proxied-artifact-storage-access): This scenario assumes that you have already deployed an MLflow Tracking Server enabled with proxied artifact storage access. There is no restriction regarding what other types of components it can be combined with. This option requires [authentication-related parameters](mlflow.md#authentication-methods) to be configured for the MLflow Experiment Tracker.

{% hint style="warning" %}
Due to a [critical severity vulnerability](https://github.com/advisories/GHSA-xg73-94fp-g449) found in older versions of MLflow, we recommend using MLflow version 2.2.1 or higher.
{% endhint %}

* [Databricks scenario](https://www.databricks.com/product/managed-mlflow): This scenario assumes that you have a Databricks workspace, and you want to use the managed MLflow Tracking server it provides. This option requires [authentication-related parameters](mlflow.md#authentication-methods) to be configured for the MLflow Experiment Tracker.

### Infrastructure Deployment

The MLflow Experiment Tracker can be deployed directly from the ZenML CLI:

```shell
# optionally assigning an existing bucket to the MLflow Experiment Tracker
zenml experiment-tracker deploy mlflow_tracker --flavor=mlflow -x mlflow_bucket=gs://my_bucket --provider=<YOUR_PROVIDER>
```

You can pass other configurations specific to the stack components as key-value arguments. If you don't provide a name, a random one is generated for you. For more information about how to work use the CLI for this, please refer to the [dedicated documentation section](../../how-to/stack-deployment/README.md).

### Authentication Methods

You need to configure the following credentials for authentication to a remote MLflow tracking server:

* `tracking_uri`: The URL pointing to the MLflow tracking server. If using an MLflow Tracking Server managed by Databricks, then the value of this attribute should be `"databricks"`.
* `tracking_username`: Username for authenticating with the MLflow tracking server.
* `tracking_password`: Password for authenticating with the MLflow tracking server.
* `tracking_token` (in place of `tracking_username` and `tracking_password`): Token for authenticating with the MLflow tracking server.
* `tracking_insecure_tls` (optional): Set to skip verifying the MLflow tracking server SSL certificate.
* `databricks_host`: The host of the Databricks workspace with the MLflow-managed server to connect to. This is only required if the `tracking_uri` value is set to `"databricks"`. More information: [Access the MLflow tracking server from outside Databricks](https://docs.databricks.com/applications/mlflow/access-hosted-tracking-server.html)

Either `tracking_token` or `tracking_username` and `tracking_password` must be specified.

{% tabs %}
{% tab title="Basic Authentication" %}
This option configures the credentials for the MLflow tracking service directly as stack component attributes.

{% hint style="warning" %}
This is not recommended for production settings as the credentials won't be stored securely and will be clearly visible in the stack configuration.
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

{% tab title="ZenML Secret (Recommended)" %}
This method requires you to [configure a ZenML secret](../../how-to/interact-with-secrets.md) to store the MLflow tracking service credentials securely.

You can create the secret using the `zenml secret create` command:

```shell
# Create a secret called `mlflow_secret` with key-value pairs for the
# username and password to authenticate with the MLflow tracking server
zenml secret create mlflow_secret \
    --username=<USERNAME> \
    --password=<PASSWORD>
```

Once the secret is created, you can use it to configure the MLflow Experiment Tracker:

```shell
# Reference the username and password in our experiment tracker component
zenml experiment-tracker register mlflow \
    --flavor=mlflow \
    --tracking_username={{mlflow_secret.username}} \
    --tracking_password={{mlflow_secret.password}} \
    ...
```

{% hint style="info" %}
Read more about [ZenML Secrets](../../how-to/interact-with-secrets.md) in the ZenML documentation.
{% endhint %}
{% endtab %}
{% endtabs %}

For more, up-to-date information on the MLflow Experiment Tracker implementation and its configuration, you can have a look at [the SDK docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-mlflow/#zenml.integrations.mlflow.experiment\_trackers.mlflow\_experiment\_tracker) .

## How do you use it?

To be able to log information from a ZenML pipeline step using the MLflow Experiment Tracker component in the active stack, you need to enable an experiment tracker using the `@step` decorator. Then use MLflow's logging or auto-logging capabilities as you would normally do, e.g.:

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

{% hint style="info" %}
Instead of hardcoding an experiment tracker name, you can also use the [Client](../../reference/python-client.md) to dynamically use the experiment tracker of your active stack:

```python
from zenml.client import Client

experiment_tracker = Client().active_stack.experiment_tracker

@step(experiment_tracker=experiment_tracker.name)
def tf_trainer(...):
    ...
```
{% endhint %}

### MLflow UI

MLflow comes with its own UI that you can use to find further details about your tracked experiments.

You can find the URL of the MLflow experiment linked to a specific ZenML run via the metadata of the step in which the experiment tracker was used:

```python
from zenml.client import Client

last_run = client.get_pipeline("<PIPELINE_NAME>").last_run
trainer_step = last_run.get_step("<STEP_NAME>")
tracking_url = trainer_step.run_metadata["experiment_tracker_url"].value
print(tracking_url)
```

This will be the URL of the corresponding experiment in your deployed MLflow instance, or a link to the corresponding mlflow experiment file if you are using local MLflow.

{% hint style="info" %}
If you are using local MLflow, you can use the `mlflow ui` command to start MLflow at [`localhost:5000`](http://localhost:5000/) where you can then explore the UI in your browser.

```bash
mlflow ui --backend-store-uri <TRACKING_URL>
```
{% endhint %}

### Additional configuration

For additional configuration of the MLflow experiment tracker, you can pass `MLFlowExperimentTrackerSettings` to create nested runs or add additional tags to your MLflow runs:

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

Check out the [SDK docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-mlflow/#zenml.integrations.mlflow.flavors.mlflow\_experiment\_tracker\_flavor.MLFlowExperimentTrackerSettings) for a full list of available attributes and [this docs page](../../how-to/use-configuration-files/runtime-configuration.md) for more information on how to specify settings.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
