---
description: How to log and visualize experiments with neptune.ai
---

The Neptune Experiment Tracker is an [Experiment Tracker](./experiment-trackers.md)
flavor provided with the Neptune-ZenML integration that uses
[the Neptune.ai experiment tracking platform](https://neptune.ai/product/experiment-tracking)
to log and visualize information from your pipeline steps (e.g. models, parameters,
metrics).

## When would you want to use it?

[Neptune.ai](https://neptune.ai/product/experiment-tracking) is a very
popular platform that you would normally use in the iterative ML experimentation
phase to track and visualize experiment results. That doesn't mean that it
cannot be repurposed to track and visualize the results produced by your
automated pipeline runs, as you make the transition towards a more production
oriented workflow.

You should use the Neptune.ai Experiment Tracker:
* if you have already been using Neptune.ai to track experiment results
for your project and would like to continue doing so as you are incorporating 
MLOps workflows and best practices in your project through ZenML.
* if you are looking for a more visually interactive way of navigating the
results produced from your ZenML pipeline runs (e.g. models, metrics, datasets)
* if you would like to connect ZenML to Neptune.ai to share the artifacts
and metrics logged by your pipelines with your team, organization or external
stakeholders

You should consider one of the other [Experiment Tracker flavors](./experiment-trackers.md#experiment-tracker-flavors)
if you have never worked with Neptune.ai before and would rather use
another experiment tracking tool that you are more familiar with.

## How do you deploy it?

The Neptune.ai Experiment Tracker flavor is provided by the MLflow ZenML
integration, you need to install it on your local machine to be able to register
a Weights & Biases Experiment Tracker and add it to your stack:

```shell
zenml integration install neptune -y
```

The Neptune.ai Experiment Tracker needs to be configured with the
credentials required to connect to the Neptune.ai platform using API-token.

### Authentication Methods

You need to configure the following credentials for authentication to the
Neptune.ai platform:

* `api_token`: API key token of your Neptune.ai account. If left blank, Neptune will
attempt to retrieve it from your environment variables.
* `project`: The name of the project where you're sending the new run. If
the project is not specified, Neptune will attempt to retrieve it from your environment variables.


{% tabs %}
{% tab title="Basic Authentication" %}

This option configures the credentials for the Weights & Biases platform
directly as stack component attributes.

{% hint style="warning" %}
This is not recommended for production settings as the credentials won't be
stored securely and will be clearly visible in the stack configuration.
{% endhint %}

```shell
# Register the Weights & Biases experiment tracker
zenml experiment-tracker register neptune_experiment_tracker --flavor=neptune \ 
    --project=<project_name> --api_token=<token>

# Register and set a stack with the new experiment tracker
zenml stack register custom_stack -e neptune_experiment_tracker ... --set
```
{% endtab %}

{% tab title="Secrets Manager (Recommended)" %}

This method requires you to include a [Secrets Manager](../secrets-managers/secrets-managers.md)
in your stack and configure a ZenML secret to store the Neptune.ai
credentials securely.

{% hint style="warning" %}
**This method is not yet supported!**

We are actively working on adding Secrets Manager support to the Neptune.ai
Experiment Tracker.
{% endhint %}
{% endtab %}
{% endtabs %}

For more, up-to-date information on the Neptune.ai Experiment Tracker
implementation and its configuration, you can have a look at [the API docs](https://apidocs.zenml.io/latest/integration_code_docs/integrations-wandb/#zenml.integrations.neptune.experiment_trackers.neptune_experiment_tracker).

## How do you use it?

To be able to log information from a ZenML pipeline step using the Neptune.ai Experiment Tracker component in the active stack, you need to enable an
experiment tracker using the `@step` decorator. Then fetch Neptune run object and use
logging capabilities as you would normally do, e.g.:

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

You can pass a set of tags to the neptune run by using the NeptuneExperimentTrackerSettings class like in the example
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
    """Log metadata to neptune run"""
    neptune_run = get_neptune_run()
    ...
```

You can also check out our examples pages for working examples that use the
Neptune.ai Experiment Tracker in their stacks:

- [Track Experiments with Neptune.ai](https://github.com/zenml-io/zenml/tree/main/examples/neptune_tracking)
