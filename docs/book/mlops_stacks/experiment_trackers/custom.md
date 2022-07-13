---
description: Extend ZenML to implement a custom Experiment Tracker
---

{% hint style="warning" %}
**Base abstraction in progress!**

We are actively working on the base abstraction for the Experiment Tracker,
which  will be available soon. As a result, their extension is not recommended at
the moment. When you are selecting an Experiment Tracker for your stack, you can
use  one of [the existing flavors](./overview.md#experiment-tracker-flavors).

If you need to implement your own Experiment Tracker flavor, you can still do so,
but keep in mind that you may have to refactor it when the base abstraction
is released.
{% endhint %}

{% hint style="warning" %}
Before reading this chapter, make sure that you are familiar with the 
concept of [stacks, stack components and their flavors](../advanced-guide/stacks-components-flavors.md).  
{% endhint %}

## Build your own custom experiment tracker

If you want to implement your own custom Experiment Tracker, you can follow the
following steps:

1. Create a class which inherits from [the `BaseExperimentTracker` class](https://apidocs.zenml.io/latest/api_docs/experiment_trackers/#zenml.experiment_trackers.base_experiment_tracker.BaseExperimentTracker).
2. Define the `FLAVOR` class variable.

Once you are done with the implementation, you can register it through the CLI 
as:

```shell
zenml experiment-tracker flavor register <THE-SOURCE-PATH-OF-YOUR-EXPERIMENT-TRACKER>
```

ZenML includes a range of Experiment Tracker implementations provided by
specific integration modules. You can use them as examples of how you can extend
the [base Experiment Tracker class](https://apidocs.zenml.io/latest/api_docs/experiment_trackers/#zenml.experiment_trackers.base_experiment_tracker.BaseExperimentTracker)
to implement your own custom Experiment Tracker:

|                                                                                                                                                                                   | Flavor   | Integration |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|-------------|
| [MLFlowExperimentTracker](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.mlflow.experiment_trackers.mlflow_experiment_tracker.MLFlowExperimentTracker) | mlflow   | mlflow      |
| [WandbExperimentTracker](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.wandb.experiment_trackers.wandb_experiment_tracker.WandbExperimentTracker)     | wandb    | wandb       |
