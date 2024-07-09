---
description: Logging and visualizing experiments with Comet.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


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

{% tab title="ZenML Secret (Recommended)" %}
This method requires you to [configure a ZenML secret](../../getting-started/deploying-zenml/manage-the-deployed-services/secret-management.md) to store the Comet tracking service credentials securely.

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
Read more about [ZenML Secrets](../../getting-started/deploying-zenml/manage-the-deployed-services/secret-management.md) in the ZenML documentation.
{% endhint %}
{% endtab %}
{% endtabs %}

For more up-to-date information on the Comet Experiment Tracker implementation and its configuration, you can have a look at [the SDK docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-comet/#zenml.integrations.comet.experiment\_trackers.comet\_experiment\_tracker).

### How do you use it?

To be able to log information from a ZenML pipeline step using the Comet Experiment Tracker component in the active stack, you need to enable an experiment tracker using the `@step` decorator. Then use Comet logging capabilities as you would normally do, e.g.:

```python
from zenml.client import Client

experiment_tracker = Client().active_stack.experiment_tracker

@step(experiment_tracker=experiment_tracker.name)
def my_step():
    ...
    experiment_tracker.log_metrics({"my_metric": 42})
    experiment_tracker.log_params({"my_param": "hello"})
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

#### Additional configuration

For additional configuration of the Comet experiment tracker, you can pass `CometExperimentTrackerSettings` to provide additional tags for your experiments:

```
from zenml.integrations.comet.flavors.comet_experiment_tracker_flavor import CometExperimentTrackerSettings

comet_settings = CometExperimentTrackerSettings(
    tags=["some_tag"]
)

@step(
    experiment_tracker="<COMET_TRACKER_STACK_COMPONENT_NAME>",
    settings={
        "experiment_tracker.comet": comet_settings
    }
)
def my_step():
    ...
```

Check out the [SDK docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-comet/#zenml.integrations.comet.flavors.comet\_experiment\_tracker\_flavor.CometExperimentTrackerSettings) for a full list of available attributes and [this docs page](../../how-to/use-configuration-files/runtime-configuration.md) for more information on how to specify settings.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
