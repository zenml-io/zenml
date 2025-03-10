---
description: Use tags to organize tags in ZenML.
---

# Organizing data with tags

Organizing and categorizing your machine learning artifacts and models can
streamline your workflow and enhance discoverability. ZenML enables the use of
tags as a flexible tool to classify and filter your ML assets. 

![Tags are visible in the ZenML Dashboard](../../../.gitbook/assets/tags-in-dashboard.png)

## Tagging different entities

### Assigning tags to artifacts

You can tag artifact versions by using the `add_tags` utility function:

```python
from zenml import add_tags

add_tags(tags=["my_tag"], artifact="my_artifact_name_or_id")
```

Alternatively, you can tag an artifact by using CLI as well:

```bash
zenml artifacts update my_artifact -t my_tag
```

### Assigning tags to artifact versions

In order to tag an artifact through the Python SDK, you can use either use
the `ArtifactConfig` object:

```python
from zenml import step, ArtifactConfig

@step
def data_loader() -> (
    Annotated[pd.DataFrame, ArtifactConfig(name="my_output", tags=["my_tag"])]
):
    ...
```

or the `add_tags` utility function:

```python
from zenml import add_tags

# Automatic tagging to an artifact version within a step execution
## A step with a single output
add_tags(tags=["my_tag"], infer_artifact=True)
## A step with multiple outputs (need to specify the output name)
add_tags(tags=["my_tag"], artifact_name="my_output", infer_artifact=True)

# Manual tagging to an artifact version (can happen in a step or outside of it)
## By specifying the artifact name and version
add_tags(tags=["my_tag"], artifact_name="my_output", artifact_version="v1")
## By specifying the artifact version ID
add_tags(tags=["my_tag"], artifact_version_id="artifact_version_uuid")
```

Moreover, you can tag an artifact version by using the CLI:

```bash
# Tag the artifact version
zenml artifacts versions update iris_dataset raw_2023 -t sklearn
```

{% hint style="info" %}
In the upcoming chapters, you will also learn how to use [an cascade tag](#cascade-tags) to tag an artifact version as well.
{% endhint %}

### Assigning tags to pipelines

Assigning tags to pipelines is only possible through the Python SDK and you can use the `add_tags` utility function:

```python
from zenml import add_tags

add_tags(tags=["my_tag"], pipeline="pipeline_name_or_id")
```

### Assigning tags to runs

To assign tags to a pipeline run in ZenML, you can use the `add_tags` utility function:

```python
from zenml import add_tags

# Manual tagging to a run
add_tags(tags=["my_tag"], run="run_name_or_id")
```

Alternatively, you can use the same function within a step without 
specifying any arguments, which will automatically tag the run:

```python
from zenml import step

@step
def my_step():
    add_tags(tags=["my_tag"])
```

You can also use the pipeline decorator to tag the run:

```python
from zenml import pipeline

@pipeline(tags=["my_tag"])
def my_pipeline():
    ...
```

### Assigning tags to models and model versions

When creating a model version using the `Model` object, you can specify tags as key-value pairs that will be attached to the model version upon creation.

{% hint style="warning" %}
During pipeline run a model can be also implicitly created (if not exists), in such cases it will not get the `tags` from the `Model` class.
{% endhint %}

```python
from zenml.models import Model

# Create a model version with tags
model = Model(
    name="iris_classifier",
    version="1.0.0",
    tags=["experiment", "v1", "classification-task"],
)

# Use this tagged model in your steps and pipelines as needed
@pipeline(model=model)
def my_pipeline(...):
    ...
```

You can also assign tags when creating or updating models with the Python SDK:

```python
from zenml.models import Model
from zenml.client import Client

# Create or register a new model with tags
Client().create_model(
    name="iris_logistic_regression",
    tags=["classification", "iris-dataset"],
)

# Create or register a new model version also with tags
Client().create_model_version(
    model_name_or_id="iris_logistic_regression",
    name="2",
    tags=["version-1", "experiment-42"],
)
```

To add tags to existing models and their versions using the ZenML CLI, you can use the following commands:

```shell
# Tag an existing model
zenml model update iris_logistic_regression --tag "classification"

# Tag a specific model version
zenml model version update iris_logistic_regression 2 --tag "experiment3"
```

### Assigning tags to run templates

Assigning tags to run templates is only possible through the Python SDK and you can use the `add_tags` utility function:

```python
from zenml import add_tags

add_tags(tags=["my_tag"], run_template="run_template_name_or_id")
```

## Advanced Usage

ZenML provides several advanced tagging features to help you better organize and manage your ML assets.

### Exclusive Tags

Exclusive tags are special tags that can be associated with only one instance of a specific entity type within a certain scope at a time. When you apply an exclusive tag to a new entity, it's automatically removed from any previous entity of the same type that had this tag. Exclusive tags can be used with:

- One pipeline run per pipeline
- One run template per pipeline
- One artifact version per artifact

The recommended way to create exclusive tags is using the `Tag` object:

```python
from zenml import pipeline, Tag

@pipeline(tags=["not_an_exclusive_tag", Tag("an_exclusive_tag", exclusive=True)])
def my_pipeline():
    ...
```

Alternatively, you can also create an exclusive tag separately and use it later:

```python
from zenml.client import Client

Client().create_tag(name="an_exclusive_tag", exclusive=True)

@pipeline(tags=["an_exclusive_tag"])
def my_pipeline():
    ...
```

{% hint style="warning" %}
The `exclusive` parameter belongs to the configuration of the tag and this information is stored in the backend. This means, that it will not lose its `exclusive` functionality even if it is being used without the explicit `exclusive=True` parameter in future calls.
{% endhint %}

### Cascade Tags

Cascade tags allow you to associate a tag from a pipeline with all artifact versions created during its execution. 

```python
from zenml import pipeline, Tag

@pipeline(tags=["normal_tag", Tag("cascade_tag", cascade=True)])
def my_pipeline():
    ...
```

When this pipeline runs, the `cascade_tag` will be automatically applied to all artifact versions created during the pipeline execution.

{% hint style="warning" %}
Unlike the `exclusive` parameter, the `cascade` parameter is a runtime configuration and does not get stored with the `tag` object. This means that the tag will **not** have its `cascade` functionality if it is not used with the `cascade=True` parameter in future calls.
{% endhint %}

### Filtering

ZenML allows you to filter taggable objects using multiple tag conditions:

```python
from zenml import add_tags

from zenml.client import Client

# Add tags to a pipeline
add_tags(tags=["one", "two", "three"], pipeline="my_pipeline")

# Will return `my_pipeline`
Client().list_pipelines(tags=["contains:wo", "startswith:t", "equals:three"])

# Will not return `my_pipeline`
Client().list_pipelines(tags=["contains:wo", "startswith:t", "equals:four"])
```

The example above shows how you can use multiple tag conditions to filter an entity. In ZenML, the default logical operator is `AND`, which means that the entity will be returned only if there is at least one tag that matches all the conditions.

### Removing Tags

Similar to the `add_tags` utility function, you can use the `remove_tags` utility function to remove tags from an entity.

```python
from zenml.utils.tag_utils import remove_tags

# Remove tags from a pipeline
remove_tags(tags=["one", "two"], pipeline="my_pipeline")

# Remove tags from an artifact
remove_tags(tags=["three"], artifact="my_artifact")
```

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
