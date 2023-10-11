---
description: Track your ML experiments
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


## Experiment Tracking

When training models, you often need to run hundreds of experiments with
different types of models and different hyperparameters to find what works best.
Keeping track of every experiment and how each design decision affected the
model performance is hardly feasible without additional tools. That is why
experiment trackers like [TensorBoard](https://www.tensorflow.org/tensorboard/),
[Weights & Biases](https://wandb.com/), or [MLflow](https://mlflow.org/) are
often one of the first contact points ML practitioners have with MLOps as they
progress through their ML journey. In addition, these tools are invaluable for
larger ML teams, as they allow them to share experiment results and collaborate
during experimentation.

Since there are many excellent experiment tracking tools, we should aim to prevent vendor lock-in by writing modular ML code that allows us to switch between different tools easily. That is precisely what ZenML does for us.

## MLflow Experiment Tracking

[MLflow](https://mlflow.org/) is an amazing open-source MLOps platform that provides powerful tools to handle various ML lifecycle steps, such as experiment tracking, code packaging, model deployment, and more.

To integrate the MLFlow experiment tracker into our previously defined ZenML
pipeline, we can use MLflow's `mlflow.sklearn.autolog()` feature to automatically log all relevant attributes and metrics of our model to
MLflow. By adding the [appropriate settings](../../component-gallery/experiment-trackers/mlflow.md) on top of the function, ZenML then
automatically initializes MLflow and takes care of the rest for us.

To run our MLflow pipelines with ZenML, we first need to add MLflow
into our ZenML MLOps stack. We first register a new experiment tracker with
ZenML.

```shell
# Register the MLflow experiment tracker
zenml experiment-tracker register mlflow_tracker --flavor=mlflow
```

## Alternative Tool: Weights & Biases

Of course, MLflow is not the only tool you can use for experiment tracking. We
could achieve the same with another experiment tracking tool: [Weights &
Biases](https://wandb.ai/). (You will need a Weights & Biases account, which
you can set up for free [here](https://wandb.ai/login?signup=true).)

In order to register your new experiment tracker, you then need to define the
three variables below to authorize yourself in W&B and to tell ZenML which
entity/project you want to log to:

- `WANDB_API_KEY`: your API key, which you can retrieve at [https://wandb.ai/authorize](https://wandb.ai/authorize). Make sure never to share this key (in particular, make sure to remove the key before pushing this notebook to any public Git repositories!).
- `WANDB_ENTITY`: the entity (team or user) that owns the project you want to log to. If you are using W&B alone, just use your username here.
- `WANDB_PROJECT`: the name of the W&B project you want to log to. If you have never used W&B before or want to start a new project, simply type the new project name here, e.g., "zenbytes".

```shell
WANDB_API_KEY = None  # TODO: replace this with your W&B API key
WANDB_ENTITY = None  # TODO: replace this with your W&B entity name
WANDB_PROJECT = "zenbytes"  # TODO: replace this with your W&B project name (if you want to log to a specific project)

# Register the W&B experiment tracker
zenml experiment-tracker register wandb_tracker --flavor=wandb --api_key={WANDB_API_KEY} --entity={WANDB_ENTITY} --project_name={WANDB_PROJECT}

# Create a new MLOps stack with W&B experiment tracker in it & make it the active stack
zenml stack register wandb_stack -m default -a default -o default -e wandb_tracker --set
```

The main difference to the MLflow example before is that W&B has no sklearn
autolog functionality. Instead, we need to call `wandb.log(...)` for each value we
want to log to Weights & Biases.

Note that even though Weights & Biases is used in different steps within a pipeline, ZenML
handles initializing everything and ensures that the experiment name is the same as
the pipeline name and that the experiment run name is the same as the pipeline
run name. This establishes a lineage between pipelines in ZenML and experiments
in wandb.

For a more detailed example of how to use Weights & Biases experiment tracking
in your ZenML pipeline, see [the ZenML wandb_tracking
example](https://github.com/zenml-io/zenml/tree/main/examples/wandb_tracking).

{% hint style="info" %}
To read a more detailed guide about how Experiment Trackers function in ZenML,
[click here](../../component-gallery/experiment-trackers/experiment-trackers.md).
{% endhint %}