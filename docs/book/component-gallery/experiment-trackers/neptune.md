---
description: How to log and visualize experiments with neptune.ai
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


The Neptune Experiment Tracker is an [Experiment Tracker](./experiment-trackers.md)
flavor provided with the Neptune-ZenML integration that uses
[neptune.ai](https://neptune.ai/product/experiment-tracking)
to log and visualize information from your pipeline steps (e.g. models, parameters,
metrics).

## When would you want to use it?

[Neptune](https://neptune.ai/product/experiment-tracking) is a popular tool that
you would normally use in the iterative ML experimentation phase to track and
visualize experiment results or as a model registry for your production-ready
models. Neptune can also track and visualize the results produced by your
automated pipeline runs, as you make the transition towards a more production
oriented workflow.

You should use the Neptune Experiment Tracker:
* if you have already been using neptune.ai to track experiment results
for your project and would like to continue doing so as you are incorporating 
MLOps workflows and best practices in your project through ZenML.
* if you are looking for a more visually interactive way of navigating the
results produced from your ZenML pipeline runs (e.g. models, metrics, datasets)
* if you would like to connect ZenML to neptune.ai to share the artifacts
and metrics logged by your pipelines with your team, organization or external
stakeholders

You should consider one of the other [Experiment Tracker flavors](./experiment-trackers.md#experiment-tracker-flavors)
if you have never worked with neptune.ai before and would rather use
another experiment tracking tool that you are more familiar with.

## How do you deploy it?

The Neptune Experiment Tracker flavor is provided by the Neptune-ZenML
integration. You need to install it on your local machine to be able to register
the Neptune Experiment Tracker and add it to your stack:

```shell
zenml integration install neptune -y
```

The Neptune Experiment Tracker needs to be configured with the
credentials required to connect to Neptune using an API token.

### Authentication Methods

You need to configure the following credentials for authentication to
Neptune:

* `api_token`: [API key token](https://docs.neptune.ai/setup/setting_api_token) of your Neptune account. If left blank, Neptune will
attempt to retrieve it from your environment variables.
* `project`: The name of the project where you're sending the new run, in the form "workspace-name/project-name".
If the project is not specified, Neptune will attempt to retrieve it from your environment variables.


{% tabs %}
{% tab title="Basic Authentication" %}

This option configures the credentials for neptune.ai
directly as stack component attributes.

{% hint style="warning" %}
This is not recommended for production settings as the credentials won't be
stored securely and will be clearly visible in the stack configuration.
{% endhint %}

```shell
# Register the Neptune experiment tracker
zenml experiment-tracker register neptune_experiment_tracker --flavor=neptune \ 
    --project=<project_name> --api_token=<token>

# Register and set a stack with the new experiment tracker
zenml stack register custom_stack -e neptune_experiment_tracker ... --set
```
{% endtab %}

{% tab title="Secrets Manager (Recommended)" %}

This method requires you to include a [Secrets Manager](../secrets-managers/secrets-managers.md)
in your stack and configure a ZenML secret to store the Neptune tracking service
credentials securely.

You can register the secret using the `zenml secret register` command:

```shell 
zenml secrets-manager secret register neptune_secret \
    --project=<PROJECT>
    --api_token=<API_TOKEN>
```

Once the secret is registered, you can use it to configure the neptune Experiment
Tracker:

```shell
# Reference the project and api-token in our experiment tracker component
zenml experiment-tracker register neptune_secret \
    --flavor=neptune \
    --project={{neptune_secret.project}} \
    --api_token={{neptune_secret.api_token}}
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

For more, up-to-date information on the Neptune Experiment Tracker
implementation and its configuration, you can have a look at [the API docs](https://apidocs.zenml.io/latest/integration_code_docs/integrations-neptune/#zenml.integrations.neptune.experiment_trackers.neptune_experiment_tracker).

## How do you use it?

To log information from a ZenML pipeline step using the Neptune Experiment Tracker component in the active stack, you need to enable an
experiment tracker using the `@step` decorator. Then fetch the Neptune run object and use
logging capabilities as you would normally do. For example:

```python
import numpy as np

import tensorflow as tf

from neptune_tensorflow_keras import NeptuneCallback

from zenml.integrations.neptune.experiment_trackers.run_state import (
    get_neptune_run,
)
from zenml.steps import BaseParameters, step


class TrainerParameters(BaseParameters):
    """Trainer params"""

    epochs: int = 5
    lr: float = 0.001

@step(experiment_tracker="<NEPTUNE_TRACKER_STACK_COMPONENT_NAME>")
def tf_trainer(
    params: TrainerParameters,
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
) -> tf.keras.Model:
    
    ...
    neptune_run = get_neptune_run()
    model.fit(
        x_train,
        y_train,
        epochs=params.epochs,
        validation_data=(x_val, y_val),
        callbacks=[
            NeptuneCallback(run=neptune_run),
        ],
    )

    ...
```

### Additional configuration

You can pass a set of tags to the Neptune run by using the `NeptuneExperimentTrackerSettings` class, like in the example
below:

```python
import numpy as np

import tensorflow as tf

from zenml.steps import step
from zenml.integrations.neptune.experiment_trackers.run_state import (
    get_neptune_run,
)
from zenml.integrations.neptune.flavors import NeptuneExperimentTrackerSettings

neptune_settings = NeptuneExperimentTrackerSettings(tags={"keras", "mnist"})

@step(
    experiment_tracker="<NEPTUNE_TRACKER_STACK_COMPONENT_NAME>",
    settings={
        "experiment_tracker.neptune": neptune_settings
    }
)
def my_step(
        x_test: np.ndarray,
        y_test: np.ndarray,
        model: tf.keras.Model,
) -> float:
    """Log metadata to Neptune run"""
    neptune_run = get_neptune_run()
    ...
```

You can also check out our examples pages for working examples that use the
Neptune Experiment Tracker in their stacks:

- [Track Experiments with neptune.ai](https://github.com/zenml-io/zenml/tree/main/examples/neptune_tracking)
