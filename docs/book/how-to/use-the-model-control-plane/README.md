# 🪆 Use the Model Control Plane

A `Model` is simply an entity that groups pipelines, artifacts, metadata, and other crucial business data into a unified entity. Please note that one of the most common artifacts that is associated with a Model in ZenML is the so-called technical model, which is the actually model file/files that holds the weight and parameters of a machine learning training result. However, this is not the only artifact that is relevant; artifacts such as the training data and the predictions this model produces in production are also linked inside a ZenML Model. In this sense, a ZenML Model is a concept that more broadly encapsulates your ML products business logic.

Models are first-class citizens in ZenML and as such viewing and using them is unified and centralized in the ZenML API, client as well as on the [ZenML Cloud](https://zenml.io/cloud) dashboard.

A Model captures lineage information and more. Within a Model, different Model versions can be staged. For example, you can rely on your predictions at a specific stage, like `Production`, and decide whether the Model version should be promoted based on your business rules during training. Plus, accessing data from other Models and their versions is just as simple.

The Model Control Plane is how you manage your models through this unified interface. It allows you to combine the logic of your pipelines, artifacts and crucial business data along with the actual 'technical model'.

## Model versions

ZenML is already versioning your models and storing some metadata, but the Model Control Plane allows you more flexibility in terms of how you refer to and use the models. Moreover, you can now also associate them with stages and promote them to production, e.g. based on your business rules during training. You also have an interface that allows you to link these versions with non-technical artifacts and data, e.g. business data, datasets, or even stages in your process and workflow.

## Registering models

Registering models can be done in a number of ways depending on your specific needs. You can explicitly register models using the CLI or the Python SDK, or you can just allow ZenML to implicitly register your models as part of a pipeline run. (If you are using [ZenML Cloud](https://cloud.zenml.io/?utm\_source=docs\&utm\_medium=referral\_link\&utm\_campaign=cloud\_promotion\&utm\_content=signup\_link/) you already have access to [a dashboard interface that allows you to register models](../../user-guide/advanced-guide/data-management/model-control-plane-dashboard.md).)

### Explicit CLI registration

Registering models using the CLI is as straightforward as the following command:

```bash
zenml model register iris_logistic_regression --license=... --description=...
```

You can view some of the options of what can be passed into this command by running `zenml model register --help` but since you are using the CLI outside a pipeline run the arguments you can pass in are limited to non-runtime items. You can also associate tags with models at this point, for example, using the `--tag` option.

### Explicit dashboard registration

[ZenML Cloud](https://zenml.io/cloud) can register their models directly from the cloud dashboard interface.

<figure><img src="../../.gitbook/assets/mcp_model_register.png" alt="ZenML Cloud Register Model."><figcaption><p>Register a model on the [ZenML Cloud](https://zenml.io/cloud) dashboard</p></figcaption></figure>

### Explicit Python SDK registration

You can register a model using the Python SDK as follows:

```python
from zenml import Model
from zenml.client import Client

Client().create_model(
    name="iris_logistic_regression",
    license="Copyright (c) ZenML GmbH 2023",
    description="Logistic regression model trained on the Iris dataset.",
    tags=["regression", "sklearn", "iris"],
)
```

### Implicit registration by ZenML

The most common use case for registering models is to do so implicitly as part of a pipeline run. This is done by specifying a `Model` object as part of the `model` argument of the `@pipeline` decorator.

As an example, here we have a training pipeline which orchestrates the training of a model object, storing datasets and the model object itself as links within a newly created Model version. This integration is achieved by configuring the pipeline within a Model Context using `Model`. The name is specified, while other fields remain optional for this task.

```python
from zenml import pipeline
from zenml import Model

@pipeline(
    enable_cache=False,
    model=Model(
        name="demo",
        license="Apache",
        description="Show case Model Control Plane.",
    ),
)
def train_and_promote_model():
    ...
```

Running the training pipeline creates a new model version, all while maintaining a connection to the artifacts.
<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


