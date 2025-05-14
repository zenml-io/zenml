---
description: Managing ML models throughout their lifecycle with ZenML
icon: rectangle-history
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Models

Machine learning models are at the heart of any ML workflow. ZenML provides comprehensive model management capabilities through its Model Control Plane, allowing you to track, version, promote, and share models across your ML pipelines.

{% hint style="info" %}
The ZenML Model Control Plane is a [ZenML Pro](https://zenml.io/pro) feature. While the Python functions for creating and interacting with models are available in the open-source version, the visual dashboard for exploring and managing models is only available in ZenML Pro. Please [sign up here](https://cloud.zenml.io) to get access to the full model management experience.
{% endhint %}

This guide covers all aspects of working with models in ZenML, from basic concepts to advanced usage patterns.

## Understanding Models in ZenML

### What is a ZenML Model?

A ZenML Model is an entity that groups together related resources:

* Pipelines that train, evaluate, or deploy the model
* Artifacts like datasets, model weights, and predictions
* Metadata including metrics, parameters, and business information

Think of a ZenML Model as a container that organizes all the components related to a specific ML use case or business problem. This extends beyond just the model weights or parameters - it represents the entire ML product.

{% hint style="info" %}
A ZenML Model is different from a "technical model" (the actual ML model files with weights and parameters). The technical model is just one artifact that can be associated with a ZenML Model, alongside training data, predictions, and other resources.
{% endhint %}

### The Model Control Plane

The Model Control Plane is ZenML's unified interface for managing models throughout their lifecycle. It allows you to:

* Register and version models
* Associate pipelines and artifacts with models
* Track lineage and dependencies
* Manage model promotions through stages (staging, production, etc.)
* Exchange data between pipelines using models

{% hint style="info" %}
While all Model Control Plane functionality is accessible programmatically through the Python SDK in both OSS and Pro versions, the visual dashboard shown below is only available in ZenML Pro.
{% endhint %}

![Model Control Plane Overview in ZenML Pro Dashboard](<../../.gitbook/assets/dcp_walkthrough.gif>)

## Working with Models

### Registering a Model

You can register models in several ways:

#### Using the Python SDK

```python
from zenml import Model
from zenml.client import Client

Client().create_model(
    name="iris_classifier",
    license="Apache 2.0",
    description="Classification model for the Iris dataset",
    tags=["classification", "sklearn", "iris"],
)
```

#### Using the CLI

```bash
zenml model register iris_classifier --license="Apache 2.0" --description="Classification model for the Iris dataset"
```

#### Using a Pipeline

The most common approach is to register a model implicitly as part of a pipeline:

```python
from zenml import pipeline, Model

@pipeline(
    model=Model(
        name="iris_classifier",
        description="Classification model for the Iris dataset",
        tags=["classification", "sklearn"]
    )
)
def training_pipeline():
    # Pipeline implementation...
```

### Model Versioning

Each time you run a pipeline with a model configuration, a new model version is created. You can:

#### Explicitly Name Versions

```python
from zenml import Model, pipeline

@pipeline(
    model=Model(
        name="iris_classifier", 
        version="1.0.5"
    )
)
def training_pipeline():
    # Pipeline implementation...
```

#### Use Templated Naming

```python
from zenml import Model, pipeline

@pipeline(
    model=Model(
        name="iris_classifier", 
        version="run-{run.id[:8]}"
    )
)
def training_pipeline():
    # Pipeline implementation...
```

### Linking Artifacts to Models

Artifacts produced during pipeline runs can be linked to models to establish lineage and enable reuse:

```python
from zenml import step, Model
from zenml.artifacts.utils import save_artifact
import pandas as pd
from typing_extensions import Annotated
from zenml.artifacts.artifact_config import ArtifactConfig

@step(model=Model(name="MyModel", version="1.2.42"))
def trainer(
    trn_dataset: pd.DataFrame,
) -> Annotated[ClassifierMixin, ArtifactConfig("trained_model")]:
    # Train the model
    model = RandomForestClassifier().fit(trn_dataset)
    
    # Save intermediate checkpoint
    for epoch in range(10):
        model = train_epoch(model, trn_dataset)
        # Save intermediate artifact
        save_artifact(
            f"model_checkpoint_{epoch}", 
            model,
            is_model_artifact=True,
        )
    
    return model
```

### Model Promotion

Model stages represent the progression of models through their lifecycle. ZenML supports the following stages:

* `staging`: Ready for final validation before production
* `production`: Currently deployed in a production environment
* `latest`: The most recent version (virtual stage)
* `archived`: No longer in use

You can promote models to different stages:

```python
from zenml import Model
from zenml.enums import ModelStages

# Promote a specific model version to production
model = Model(name="iris_classifier", version="1.2.3")
model.set_stage(stage=ModelStages.PRODUCTION)

# Find latest model and promote to staging
latest_model = Model(name="iris_classifier", version=ModelStages.LATEST)
latest_model.set_stage(stage=ModelStages.STAGING)
```

## Using Models Across Pipelines

One of the most powerful features of ZenML's Model Control Plane is the ability to share artifacts between pipelines through models.

### Pattern: Model-Mediated Artifact Exchange

This pattern allows pipelines to exchange data without knowing the specific artifact IDs:

```python
from typing_extensions import Annotated
from zenml import get_pipeline_context, pipeline, Model
from zenml.enums import ModelStages
import pandas as pd
from sklearn.base import ClassifierMixin

@step
def predict(
    model: ClassifierMixin,
    data: pd.DataFrame,
) -> Annotated[pd.Series, "predictions"]:
    """Make predictions using a trained model."""
    predictions = pd.Series(model.predict(data))
    return predictions

@pipeline(
    model=Model(
        name="iris_classifier",
        # Reference the production version
        version=ModelStages.PRODUCTION,
    ),
)
def inference_pipeline():
    """Run inference using the production model."""
    # Get the model from the pipeline context
    model = get_pipeline_context().model
    
    # Load inference data
    inference_data = load_data()
    
    # Run prediction using the trained model artifact
    predict(
        model=model.get_model_artifact("trained_model"),
        data=inference_data,
    )
```

This pattern enables clean separation between training and inference pipelines while maintaining a clear relationship between them.

## Tracking Metrics and Metadata

ZenML allows you to attach metadata to models, which is crucial for tracking performance, understanding training conditions, and making promotion decisions.

{% hint style="info" %}
While metadata tracking is available in both OSS and Pro versions through the Python SDK, visualizing and exploring model metrics through a dashboard interface is only available in ZenML Pro.
{% endhint %}

### Logging Model Metadata

```python
from zenml import step, log_metadata, get_step_context

@step
def evaluate_model(model, test_data):
    """Evaluate the model and log metrics."""
    predictions = model.predict(test_data)
    accuracy = calculate_accuracy(predictions, test_data.target)
    precision = calculate_precision(predictions, test_data.target)
    recall = calculate_recall(predictions, test_data.target)
    
    # Log metrics to the model
    log_metadata(
        metadata={
            "evaluation_metrics": {
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall
            }
        },
        infer_model=True,  # Attaches to the model in the current step context
    )
```

### Fetching Model Metadata

You can retrieve logged metadata for analysis or decision-making:

```python
from zenml.client import Client

# Get a specific model version
model = Client().get_model_version("iris_classifier", "1.2.3")

# Access metadata
metrics = model.run_metadata["evaluation_metrics"].value
print(f"Model accuracy: {metrics['accuracy']}")
```

## Deleting Models

When a model is no longer needed, you can delete it or specific versions:

### Deleting All Versions of a Model

```python
from zenml.client import Client

# Using the Python SDK
Client().delete_model("iris_classifier")

# Or using the CLI
# zenml model delete iris_classifier
```

### Deleting a Specific Version

```python
from zenml.client import Client

# Using the Python SDK
Client().delete_model_version("model_version_id")

# Or using the CLI
# zenml model version delete <MODEL_VERSION_NAME>
```

## Best Practices

* **Consistent Naming**: Use consistent naming conventions for models and versions
* **Rich Metadata**: Log comprehensive metadata to provide context for each model version
* **Promotion Strategy**: Develop a clear strategy for promoting models through stages
* **Model Association**: Associate pipelines with models to maintain lineage and enable artifact sharing
* **Versioning Strategy**: Choose between explicit versioning and template-based versioning based on your needs

## Conclusion

The Model Control Plane in ZenML provides a comprehensive solution for managing models throughout their lifecycle. By properly registering, versioning, linking artifacts, and tracking metadata, you can create a transparent and reproducible workflow for your ML projects.

{% hint style="info" %}
**OSS vs Pro Feature Summary:**
* **ZenML OSS:** Includes all the programmatic (Python SDK) model features described in this guide
* **ZenML Pro:** Adds visual model dashboard, advanced model exploration, comprehensive metrics visualization, and integrated model lineage views
{% endhint %}

Whether you're working on a simple classification model or a complex production ML system, ZenML's model management capabilities help you organize your resources and maintain clarity in your ML processes.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
