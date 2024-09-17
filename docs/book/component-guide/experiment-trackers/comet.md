---
description: Logging and visualizing experiments with Comet.
---

# Comet

The Comet Experiment Tracker is an [Experiment Tracker](./experiment-trackers.md) flavor provided with the Comet ZenML integration that uses [the Comet experiment tracking platform](https://www.comet.com/site/products/ml-experiment-tracking/) to log and visualize information from your pipeline steps (e.g., models, parameters, metrics).

### When would you want to use it?

[Comet](https://www.comet.com/site/products/ml-experiment-tracking/) is a popular platform that you would normally use in the iterative ML experimentation phase to track and visualize experiment results. That doesn't mean that it cannot be repurposed to track and visualize the results produced by your automated pipeline runs, as you make the transition towards a more production-oriented workflow.

You should use the Comet Experiment Tracker:

* if you have already been using Comet to track experiment results for your project and would like to continue doing so as you are incorporating MLOps workflows and best practices in your project through ZenML.
* if you are looking for a more visually interactive way of navigating the results produced from your ZenML pipeline runs (e.g., models, metrics, datasets)
* if you would like to connect ZenML to Comet to share the artifacts and metrics logged by your pipelines with your team, organization, or external stakeholders

You should consider one of the other [Experiment Tracker flavors](./experiment-trackers.md#experiment-tracker-flavors) if you have never worked with Comet before and would rather use another experiment tracking tool that you are more familiar with.

### How do you deploy it?

The Comet Experiment Tracker flavor is provided by the Comet ZenML integration. You need to install it on your local machine to be able to register a Comet Experiment Tracker and add it to your stack:

```bash
zenml integration install comet -y
```

The Comet Experiment Tracker needs to be configured with the credentials required to connect to the Comet platform using one of the available authentication methods.

#### Authentication Methods

You need to configure the following credentials for authentication to the Comet platform:

* `api_key`: Mandatory API key token of your Comet account.
* `project_name`: The name of the project where you're sending the new experiment. If the project is not specified, the experiment is put in the default project associated with your API key.
* `workspace`: Optional. The name of the workspace where your project is located. If not specified, the default workspace associated with your API key will be used.

{% tabs %}

{% tab title="ZenML Secret (Recommended)" %}
This method requires you to [configure a ZenML secret](../../getting-started/deploying-zenml/secret-management.md) to store the Comet tracking service credentials securely.

You can create the secret using the `zenml secret create` command:

```bash
zenml secret create comet_secret \
    --workspace=<WORKSPACE> \
    --project_name=<PROJECT_NAME> \
    --api_key=<API_KEY>
```

Once the secret is created, you can use it to configure the Comet Experiment Tracker:

```bash
# Reference the workspace, project, and api-key in our experiment tracker component
zenml experiment-tracker register comet_tracker \
    --flavor=comet \
    --workspace={{comet_secret.workspace}} \
    --project_name={{comet_secret.project_name}} \
    --api_key={{comet_secret.api_key}}
    ...
```

{% hint style="info" %}
Read more about [ZenML Secrets](../../getting-started/deploying-zenml/secret-management.md) in the ZenML documentation.
{% endhint %}
{% endtab %}

{% tab title="Basic Authentication" %}
This option configures the credentials for the Comet platform directly as stack component attributes.

{% hint style="warning" %}
This is not recommended for production settings as the credentials won't be stored securely and will be clearly visible in the stack configuration.
{% endhint %}

```bash
# Register the Comet experiment tracker
zenml experiment-tracker register comet_experiment_tracker --flavor=comet \
    --workspace=<workspace> --project_name=<project_name> --api_key=<key>

# Register and set a stack with the new experiment tracker
zenml stack register custom_stack -e comet_experiment_tracker ... --set
```
{% endtab %}

{% endtabs %}

For more up-to-date information on the Comet Experiment Tracker implementation and its configuration, you can have a look at [the SDK docs](https://sdkdocs.zenml.io/0.66.0/integration_code_docs/integrations-comet/#zenml.integrations.comet.flavors.comet_experiment_tracker_flavor.CometExperimentTrackerConfig).

### How do you use it?

To be able to log information from a ZenML pipeline step using the Comet Experiment Tracker component in the active stack, you need to enable an experiment tracker using the `@step` decorator. Then use Comet logging capabilities as you would normally do, e.g.:

```python
from zenml.client import Client

experiment_tracker = Client().active_stack.experiment_tracker

@step(experiment_tracker=experiment_tracker.name)
def my_step():
    ...
    # go through some experiment tracker methods
    experiment_tracker.log_metrics({"my_metric": 42})
    experiment_tracker.log_params({"my_param": "hello"})

    # or use the Experiment object directly
    experiment_tracker.experiment.log_model(...)

    # or pass the Comet Experiment object into helper methods
    from comet_ml.integration.sklearn import log_model
    log_model(
        experiment=experiment_tracker.experiment,
        model_name="SVC",
        model=model,
    )
    ...
```

{% hint style="info" %}
Instead of hardcoding an experiment tracker name, you can also use the [Client](../../reference/python-client.md) to dynamically use the experiment tracker of your active stack, as shown in the example above.
{% endhint %}

### Comet UI

Comet comes with a web-based UI that you can use to find further details about your tracked experiments.

Every ZenML step that uses Comet should create a separate experiment which you can inspect in the Comet UI.

You can find the URL of the Comet experiment linked to a specific ZenML run via the metadata of the step in which the experiment tracker was used:

```python
from zenml.client import Client

last_run = client.get_pipeline("<PIPELINE_NAME>").last_run
trainer_step = last_run.get_step("<STEP_NAME>")
tracking_url = trainer_step.run_metadata["experiment_tracker_url"].value
print(tracking_url)
```

Alternatively, you can see an overview of all experiments at `https://www.comet.com/{WORKSPACE_NAME}/{PROJECT_NAME}/experiments/`.

{% hint style="info" %}
The naming convention of each Comet experiment is `{pipeline_run_name}_{step_name}` (e.g., `comet_example_pipeline-25_Apr_22-20_06_33_535737_my_step`), and each experiment will be tagged with both `pipeline_name` and `pipeline_run_name`, which you can use to group and filter experiments.
{% endhint %}

## Full Code Example

This section combines all the code from this section into one simple script that you can use to run easily:

<details>

<summary>Code Example of this Section</summary>

```python
from comet_ml.integration.sklearn import log_model

import numpy as np
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score
from typing import Tuple

from zenml import pipeline, step
from zenml.client import Client
from zenml.integrations.comet.flavors.comet_experiment_tracker_flavor import (
    CometExperimentTrackerSettings,
)
from zenml.integrations.comet.experiment_trackers import CometExperimentTracker

# Get the experiment tracker from the active stack
experiment_tracker: CometExperimentTracker = Client().active_stack.experiment_tracker


@step
def load_data() -> Tuple[np.ndarray, np.ndarray]:
    iris = load_iris()
    X = iris.data
    y = iris.target
    return X, y


@step
def preprocess_data(
    X: np.ndarray, y: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    return X_train_scaled, X_test_scaled, y_train, y_test


@step(experiment_tracker=experiment_tracker.name)
def train_model(X_train: np.ndarray, y_train: np.ndarray) -> SVC:
    model = SVC(kernel="rbf", C=1.0)
    model.fit(X_train, y_train)
    log_model(
        experiment=experiment_tracker.experiment,
        model_name="SVC",
        model=model,
    )
    return model


@step(experiment_tracker=experiment_tracker.name)
def evaluate_model(model: SVC, X_test: np.ndarray, y_test: np.ndarray) -> float:
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    # Log metrics using Comet
    experiment_tracker.log_metrics({"accuracy": accuracy})
    experiment_tracker.experiment.log_confusion_matrix(y_test, y_pred)
    return accuracy


@pipeline(enable_cache=False)
def iris_classification_pipeline():
    X, y = load_data()
    X_train, X_test, y_train, y_test = preprocess_data(X, y)
    model = train_model(X_train, y_train)
    accuracy = evaluate_model(model, X_test, y_test)


if __name__ == "__main__":
    # Configure Comet settings
    comet_settings = CometExperimentTrackerSettings(tags=["iris_classification", "svm"])

    # Run the pipeline
    last_run = iris_classification_pipeline.with_options(
        settings={"experiment_tracker": comet_settings}
    )()

    # Get the URLs for the trainer and evaluator steps
    trainer_step, evaluator_step = (
        last_run.steps["train_model"],
        last_run.steps["evaluate_model"],
    )
    trainer_url = trainer_step.run_metadata["experiment_tracker_url"].value
    evaluator_url = evaluator_step.run_metadata["experiment_tracker_url"].value
    print(f"URL for trainer step: {trainer_url}")
    print(f"URL for evaluator step: {evaluator_url}")
```

</details>

#### Additional configuration

For additional configuration of the Comet experiment tracker, you can pass `CometExperimentTrackerSettings` to provide additional tags for your experiments:

```python
from zenml.integrations.comet.flavors.comet_experiment_tracker_flavor import (
    CometExperimentTrackerSettings,
)

comet_settings = CometExperimentTrackerSettings(
    tags=["some_tag"],
    run_name="",
    settings={},
)

@step(
    experiment_tracker="<COMET_TRACKER_STACK_COMPONENT_NAME>",
    settings={
        "experiment_tracker": comet_settings
    }
)
def my_step():
    ...
```

Check out the [SDK docs](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-comet/#zenml.integrations.comet.flavors.comet_experiment_tracker_flavor.CometExperimentTrackerSettings) for a full list of available attributes and [this docs page](../../how-to/use-configuration-files/runtime-configuration.md) for more information on how to specify settings.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>