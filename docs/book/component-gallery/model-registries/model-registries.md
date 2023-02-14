---
description: How to track and manage ML models
---

Model registries are centralized storage solutions for managing and tracking
machine learning models across various stages of development and deployment.
They help track the different versions and configurations of each model and
enable reproducibility. By storing metadata such as version, configuration, and
metrics, model registries help streamline the management of trained models. In
ZenML, model registries are Stack Components that allow for easy retrieval,
loading, and deployment of trained models. They also provide information on the
pipeline in which the model was trained and how to reproduce it.

## Model Registry Concepts and Terminology

The following are some of the key concepts and terminology used in model
registries: 

* **ModelRegistration**: A model registration is a presentation of a model
    group or bucket of different versions of the same model. It is a logical
    grouping of models that can be used to track the different versions of a
    model. A model registration can be created by the user or automatically
    created by the model registry when a new model is logged. It helds 
    information about the model, such as its name, description, and tags that
    can be set for all versions of the model.

* **ModelVersion**: A model version is a specific version of a model. It is
    identified by a unique version number or string and can be associated with
    a specific pipeline run or expirement run in the context of an experiment 
    tracking system or tool. The model version holds information about the model, 
    such as its name, description, tags, and metrics. It also holds a reference 
    to the model artifact that was logged to the model registry. 
    In ZenML model version holds a reference to the zenml metadata such as the
    pipeline name, pipeline run id, and the step name.
    Its also worth noting that a model version have a model registration 
    associated with it. This is the model registration that the model version
    belongs to.

* **ModelVersionStage**: A model version stage is a state that a model version
    can be in. It can be one of the following: `None`, `Staging`, `Production`,
    `Archived`. The model version stage is used to track the
    lifecycle of a model version. For example, a model version can be in the
    `Staging` stage while it is being tested and then moved to the `Production`
    stage once it is ready for deployment.

All the model registry tools and services that ZenML integrates with have
their own way of managing model groups, versions, and stages. For that reason,
ZenML provides a unified abstraction for model registries using the previously
mentioned concepts and terminology. This allows ZenML to integrate with any
model registry tool or service in a consistent way.

## When to use it

ZenML already provides a way to store and version your pipeline artifacts by
means of the mandatory [Artifact Store](../artifact-stores/artifact-stores.md).
However, these ZenML mechanisms are meant to be used programmatically and can be
more difficult to work with without a visual interface.

Model registries offer a visual way to manage and track model metadata, which
is especially useful if you're using a remote orchestrator. They allow for easy
retrieval and loading of models from storage, thanks to built-in integrations.
A model registry is ideal for interacting with all the models in your pipeline
and managing their state in a centralized way.

You want to use a model registry in your stack if you want to interact with all
the logged models in your pipeline, or if you want to manage the state of your
models in a centralized way.

## How they model registries slot into the ZenML stack

Here is an architecture diagram that shows how experiment trackers fit into the 
overall story of a remote stack.

![Model Registries](../../assets/diagrams/Remote_with_model_registry.png)

### Model Registry Flavors

Model Registries are optional stack components provided by integrations:

| Model Registry                       | Flavor   | Integration   | Notes                                                                                           |
|--------------------------------------|----------|---------------|-------------------------------------------------------------------------------------------------|
| [MLflow](./mlflow.md)                | `mlflow` | `mlflow`      | Add MLflow as Model Registry to your stack                                                      | 
| [Custom Implementation](./custom.md) | _custom_ |               | _custom_                                                                                        | Extend the Model Registry abstraction and provide your own implementation |

If you would like to see the available flavors of Model Registry, you can 
use the command:

```shell
zenml model-registry flavor list
```

## How to use it

Model registries are an optional component in the ZenML stack that are tied to
the experiment tracker. This means that a model registry can only be used if you
are also using an experiment tracker. If you're not using an experiment tracker,
you can still store your models in ZenML, but you will need to manually retrieve
model artifacts from the artifact store. More information on this can be found
in the [Fetching pipelines](../../starter-guide/pipelines/fetching-pipelines.md)
documentation.

To use model registries, you first need to register a model registry in your
stack with the same flavor as your experiment tracker. Then, you can register
your trained model in the model registry using one of three methods:
* (1) using the built-in step in the pipeline.
* (2) using the ZenML CLI to register the model from the command line.
* (3) registering the model from the model registry UI. 
Finally, you can use the model registry to retrieve and load your models for
deployment or further experimentation.