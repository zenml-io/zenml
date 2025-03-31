---
description: Use tags to organize and categorize entities in ZenML.
---

# Tags in ZenML

Tags are a powerful feature in ZenML that allow you to organize, categorize, and filter various entities within your ML workflow. By applying descriptive tags to artifacts, pipeline runs, models, and other entities, you can improve discoverability and streamline your workflow.

![Tags are visible in the ZenML Dashboard](../../.gitbook/assets/tags-in-dashboard.png)

## Tagging Different Entities

ZenML supports tagging for various entities within the system. Let's explore how to tag each of them.

### Artifacts and Artifact Versions

Artifacts represent data produced by pipeline steps, and tags help organize these data objects:

#### Tagging Artifacts

```python
from zenml import add_tags

# Tag using artifact name or ID
add_tags(tags=["production", "dataset"], artifact="my_artifact_name_or_id")

# Or via CLI
# zenml artifacts update my_artifact -t production -t dataset
```

#### Tagging Artifact Versions

```python
from zenml import step, ArtifactConfig, add_tags
import pandas as pd
from typing import Annotated

# Method 1: Using ArtifactConfig when defining a step
@step
def data_loader() -> (
    Annotated[pd.DataFrame, ArtifactConfig(name="iris_data", tags=["raw", "cleaned"])]
):
    # Your code here
    return df

# Method 2: Using add_tags within a step
@step
def process_data(data: pd.DataFrame) -> pd.DataFrame:
    # Process data
    processed_data = data.copy()
    
    # Tag the output artifact (for a step with a single output)
    add_tags(tags=["processed", "v1"], infer_artifact=True)
    
    return processed_data

# Method 3: For steps with multiple outputs, specify the output name
@step
def split_data(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    # Split data
    train = data.sample(frac=0.8)
    test = data.drop(train.index)
    
    # Tag specific outputs
    add_tags(tags=["training"], artifact_name="output_0", infer_artifact=True)
    add_tags(tags=["testing"], artifact_name="output_1", infer_artifact=True)
    
    return train, test

# Method 4: Tag an artifact version manually by version info
add_tags(tags=["final"], artifact_name="iris_data", artifact_version="2023-06-15")

# Method 5: Tag using the artifact version UUID
add_tags(tags=["validated"], artifact_version_id="a1b2c3d4-e5f6-7890-a1b2-c3d4e5f67890")
```

### Pipelines and Pipeline Runs

Tagging pipelines and runs helps organize your ML workflows and experiments:

#### Tagging Pipelines

```python
from zenml import pipeline, add_tags

# Tag an existing pipeline
add_tags(tags=["production", "v2"], pipeline="training_pipeline")

# Or define tags when creating a pipeline
@pipeline(tags=["experimental"])
def my_pipeline():
    # Pipeline steps here
    pass
```

#### Tagging Pipeline Runs

```python
from zenml import pipeline, step, add_tags

# Method 1: Tag a pipeline run on creation
@pipeline(tags=["batch_run", "daily"])
def training_pipeline():
    # Pipeline steps
    pass

# Method 2: Tag within a step (automatically tags the current run)
@step
def evaluation_step():
    # Evaluate model
    accuracy = 0.92
    
    # Add tags based on results
    if accuracy > 0.9:
        add_tags(tags=["high_accuracy"])
    
    return accuracy

# Method 3: Tag an existing run by ID
add_tags(tags=["archived"], run="run_name_or_id")
```

### Models and Model Versions

Tags are especially useful for organizing model versions in your model registry:

```python
from zenml.models import Model
from zenml.client import Client

# Method 1: Tag when creating a model version
model = Model(
    name="iris_classifier",
    version="1.0.0",
    tags=["production", "sklearn", "logistic-regression"],
)

# Method 2: Tag when registering models
Client().create_model(
    name="iris_classifier",
    tags=["classification", "iris-dataset"],
)

# Method 3: Tag model versions separately
Client().create_model_version(
    model_name_or_id="iris_classifier",
    name="2.0.0",
    tags=["candidate", "experiment-42"],
)

# Method 4: Update tags on existing models (CLI approach)
# zenml model update iris_classifier --tag "production-ready"
# zenml model version update iris_classifier 2.0.0 --tag "approved"
```

### Run Templates

For repeatable workflows, you can tag run templates:

```python
from zenml import add_tags

# Tag a run template
add_tags(tags=["daily_training", "approved"], run_template="template_name_or_id")
```

## Advanced Tag Features

ZenML offers advanced tagging capabilities to help manage complex workflows.

### Exclusive Tags

Exclusive tags are a special type of tag that can be associated with only one entity of a specific type at a time within a certain scope. When you apply an exclusive tag to a new entity, it's automatically removed from any previous entity of the same type that had this tag.

The exclusivity applies within these scopes:
- One pipeline run per pipeline
- One run template per pipeline
- One artifact version per artifact

This makes exclusive tags particularly valuable for tracking the "current" or "latest" state of your ML assets.

```python
from zenml import pipeline, Tag
from zenml.client import Client

# Method 1: Create an exclusive tag when using it
@pipeline(tags=[Tag("latest", exclusive=True), "experiment"])
def my_pipeline():
    # Pipeline steps
    pass

# Method 2: Create an exclusive tag explicitly
Client().create_tag(name="production", exclusive=True)

# This tag will now behave as exclusive even when used without the Tag class
@pipeline(tags=["production"])
def production_pipeline():
    # Pipeline steps
    pass
```

#### How Exclusive Tags Work

When an exclusive tag is applied to an entity, ZenML:
1. Identifies all entities of the same type that currently have this tag
2. Removes the tag from those entities
3. Applies the tag to the new entity

This happens automatically and atomically, ensuring that at any given time, only one entity of each type has the exclusive tag.

```python
# Create an exclusive tag
Client().create_tag(name="champion", exclusive=True)

# Tag the first model version
Client().create_model_version(
    model_name_or_id="iris_classifier",
    name="1.0.0",
    tags=["champion"]  # This model is now the champion
)

# Later, tag a new model version
Client().create_model_version(
    model_name_or_id="iris_classifier",
    name="2.0.0",
    tags=["champion"]  # This model is now the champion, and the tag is removed from v1.0.0
)
```

#### Use Cases for Exclusive Tags

Exclusive tags are particularly useful for:

1. **Model Management**:
   - `champion`: Mark the current best model in production
   - `challenger`: Indicate the model being evaluated for potential deployment
   - `latest`: Always point to the most recent version

2. **Pipeline Management**:
   - `production`: Identify the production version of a pipeline
   - `active`: Mark the currently active pipeline configuration

3. **Experiment Tracking**:
   - `baseline`: Track your current baseline for comparison
   - `best_accuracy`: Always point to the experiment with best performance

4. **Workflow States**:
   - `reviewed`: Mark the most recently reviewed artifact
   - `approved`: Indicate the currently approved version

#### Combining Exclusive Tags with Regular Tags

Exclusive tags work best when combined with regular tags to create a comprehensive tagging system:

```python
# A model version with both exclusive and regular tags
model = Model(
    name="fraud_detector",
    version="3.2.1",
    tags=[
        Tag("production", exclusive=True),  # Only one production model
        "xgboost",                          # Model architecture (non-exclusive)
        "fraud-detection",                  # Task type (non-exclusive)
        "2023-07-training"                  # Training cohort (non-exclusive)
    ]
)
```

{% hint style="warning" %}
The `exclusive` parameter belongs to the configuration of the tag and this information is stored in the backend. This means that it will not lose its `exclusive` functionality even if it is being used without the explicit `exclusive=True` parameter in future calls.
{% endhint %}

### Cascade Tags

Cascade tags automatically propagate from a pipeline to all artifact versions created during its execution:

```python
from zenml import pipeline, Tag, step

@pipeline(tags=[Tag("experiment_42", cascade=True), "training"])
def experiment_pipeline():
    # All artifacts created in this pipeline will also get the "experiment_42" tag
    data = data_loader()
    model = train_model(data)
    metrics = evaluate_model(model, data)
```

Cascade tags are useful for:
- Grouping all artifacts from a specific experiment
- Tracking data lineage across pipeline runs
- Associating artifacts with specific projects or initiatives

### Filtering with Tags

Tags enable powerful filtering capabilities for finding and retrieving entities:

```python
from zenml.client import Client

# Simple tag filtering
production_models = Client().list_models(tags=["production"])

# Complex tag filtering with conditions
experiments = Client().list_runs(
    tags=[
        "contains:experiment",  # Tags containing "experiment"
        "startswith:v2",        # Tags starting with "v2"
        "equals:high_accuracy"  # Tags exactly matching "high_accuracy"
    ]
)

# Find all artifact versions with a specific tag
validated_data = Client().list_artifact_versions(tags=["validated"])
```

## Best Practices for Tagging

To make the most of ZenML's tagging system:

1. **Develop a consistent tagging strategy** across your team or organization
2. **Use hierarchical tags** for better organization (e.g., "data:raw", "data:processed")
3. **Create tag conventions** for specific purposes:
   - Status tags: "draft", "review", "approved", "deprecated"
   - Environment tags: "dev", "staging", "production"
   - Performance tags: "high_accuracy", "low_latency"
4. **Combine exclusive and cascade tags** to create powerful workflows
5. **Consider automation** by adding tagging logic directly in your pipeline steps

## Conclusion

Tags in ZenML provide a flexible and powerful way to organize your ML assets. By effectively using tags, you can improve discoverability, streamline workflows, and better manage the lifecycle of your ML projects. 