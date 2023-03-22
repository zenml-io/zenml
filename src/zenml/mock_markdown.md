### Additional configuration

For additional configuration of the Weights & Biases experiment tracker, you can pass
`WandbExperimentTrackerSettings` to overwrite the [wandb.Settings](https://github.com/wandb/client/blob/master/wandb/sdk/wandb_settings.py#L353) or pass additional tags for your
runs:

```python
import wandb
from zenml.integrations.wandb.flavors.wandb_experiment_tracker_flavor import WandbExperimentTrackerSettings

wandb_settings = WandbExperimentTrackerSettings(
    settings=wandb.Settings(magic=True),
    tags=["some_tag"]
)

@step(
    experiment_tracker="<WANDB_TRACKER_STACK_COMPONENT_NAME>",
    settings={
        "experiment_tracker.wandb": wandb_settings
    }
)
def my_step(
        x_test: np.ndarray,
        y_test: np.ndarray,
        model: tf.keras.Model,
) -> float:
    """Everything in this step is auto-logged"""
    ...
```

Doing the above auto-magically logs all the data, metrics, and results within
the step, no further action required!

Check out the
[API docs](https://apidocs.zenml.io/latest/integration_code_docs/integrations-wandb/#zenml.integrations.wandb.flavors.wandb_experiment_tracker_flavor.WandbExperimentTrackerSettings)
for a full list of available attributes and [this docs page](../..//advanced-guide/pipelines/settings.md)
for more information on how to specify settings.

You can also check out our examples pages for working examples that use the
Weights & Biases Experiment Tracker in their stacks:

- [Track Experiments with Weights & Biases](https://github.com/zenml-io/zenml/tree/main/examples/wandb_tracking)
