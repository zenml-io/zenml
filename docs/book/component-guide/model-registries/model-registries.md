---
icon: table-rows
description: Tracking and managing ML models.
---

# Model Registries

Model registries are centralized storage solutions for managing and tracking machine learning models across various stages of development and deployment. They help track the different versions and configurations of each model and enable reproducibility. By storing metadata such as version, configuration, and metrics, model registries help streamline the management of trained models. In ZenML, model registries are Stack Components that allow for the easy retrieval, loading, and deployment of trained models. They also provide information on the pipeline in which the model was trained and how to reproduce it.

### Model Registry Concepts and Terminology

ZenML provides a unified abstraction for model registries through which it is possible to handle and manage the concepts of model groups, versions, and stages in a consistent manner regardless of the underlying registry tool or platform being used. The following concepts are useful to be aware of for this abstraction:

* **RegisteredModel**: A logical grouping of models that can be used to track different versions of a model. It holds information about the model, such as its name, description, and tags, and can be created by the user or automatically created by the model registry when a new model is logged.
* **RegistryModelVersion**: A specific version of a model identified by a unique version number or string. It holds information about the model, such as its name, description, tags, and metrics, and a reference to the model artifact logged to the model registry. In ZenML, it also holds a reference to the pipeline name, pipeline run ID, and step name. Each model version is associated with a model registration.
* **ModelVersionStage**: A model version stage is a state in that a model version can be. It can be one of the following: `None`, `Staging`, `Production`, `Archived`. The model version stage is used to track the lifecycle of a model version. For example, a model version can be in the `Staging` stage while it is being tested and then moved to the `Production` stage once it is ready for deployment.

### When to use it

ZenML provides a built-in mechanism for storing and versioning pipeline artifacts through its mandatory Artifact Store. While this is a powerful way to manage artifacts programmatically, it can be challenging to use without a visual interface.

Model registries, on the other hand, offer a visual way to manage and track model metadata, particularly when using a remote orchestrator. They make it easy to retrieve and load models from storage, thanks to built-in integrations. A model registry is an excellent choice for interacting with all the models in your pipeline and managing their state in a centralized way.

Using a model registry in your stack is particularly useful if you want to interact with all the logged models in your pipeline, or if you need to manage the state of your models in a centralized way and make it easy to retrieve, load, and deploy these models.

### How model registries fit into the ZenML stack

Here is an architecture diagram that shows how a model registry fits into the overall story of a remote stack.

![Model Registries](../../.gitbook/assets/Remote-with-model-registry.png)

#### Model Registry Flavors

Model Registries are optional stack components provided by integrations:

| Model Registry                     | Flavor   | Integration | Notes                                      |
| ---------------------------------- | -------- | ----------- | ------------------------------------------ |
| [MLflow](mlflow.md)                | `mlflow` | `mlflow`    | Add MLflow as Model Registry to your stack |
| [Custom Implementation](custom.md) | _custom_ |             | _custom_                                   |

If you would like to see the available flavors of Model Registry, you can use the command:

```shell
zenml model-registry flavor list
```

### How to use it

Model registries are an optional component in the ZenML stack that is tied to the experiment tracker. This means that a model registry can only be used if you are also using an experiment tracker. If you're not using an experiment tracker, you can still store your models in ZenML, but you will need to manually retrieve model artifacts from the artifact store. More information on this can be found in the [documentation on the fetching runs](broken-reference).

To use model registries, you first need to register a model registry in your stack with the same flavor as your experiment tracker. Then, you can register your trained model in the model registry using one of three methods:

* (1) using the built-in step in the pipeline.
* (2) using the ZenML CLI to register the model from the command line.
* (3) registering the model from the model registry UI. Finally, you can use the model registry to retrieve and load your models for deployment or further experimentation.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
