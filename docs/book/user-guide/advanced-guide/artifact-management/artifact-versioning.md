---
description: Understand and adjust how ZenML versions your data.
---

# Artifact versioning and configuration

Each artifact that ZenML saves in your artifact store is assigned a name and
is versioned automatically. Using the `ArtifactConfig` class, you can annotate
your ZenML steps to modify the name, version, and other properties of the 
artifacts created by the step:

```python
from zenml import step, ArtifactConfig

@step
def my_step() -> Annotated[int, ArtifactConfig(name=..., version=..., ...)]:
    ...


@step
def my_multi_output_step() -> Tuple[
    Annotated[int, ArtifactConfig(...)],
    Annotated[int, ArtifactConfig(...)],
]:
    ...
```

## Assign custom artifact names

If you do not give your outputs custom names, the artifacts created by your
ZenML steps will be named `{pipeline_name}::{step_name}::output` or
`{pipeline_name}::{step_name}::output_{i}` by default:

```python
from zenml import pipeline, step

@step
def my_step() -> int:
    ...

@step
def my_multi_output_step() -> Tuple[int, int]
    ...

@pipeline
def my_pipeline():

    # Default artifact name will be `my_pipeline::my_step::output`
    my_step()

    # Default artifact names will be
    #   - `my_pipeline::my_multi_output_step::output_1`
    #   - `my_pipeline::my_multi_output_step::output_2`
    my_multi_output_step()
```

</details>


To give your artifacts custom names, use the `name` parameter of the
`ArtifactConfig` class:

```python
from zenml import step, ArtifactConfig

@step
def my_step() -> Annotated[int, ArtifactConfig(name="my_custom_name")]:
    ...
```

Now you will be able to find the created artifact as `my_custom_name` in your
ZenML dashboard.

{% hint style="info" %}
To prevent visual clutter, only artifacts with custom names are displayed in
the ZenML dashboard by default. Thus, make sure to assign names to your most
important artifacts that you would like to explore visually.
{% endhint %}

## Assign custom artifact versions

ZenML automatically versions all created artifacts using auto-incremented
numbering. I.e., if you have defined a step creating an artifact named
"my_custom_artifact" as shown above, the first execution of the step will
create an artifact with this name and version "1", the second execution will
create version "2" and so on.

If you would like to override the version assigned to an artifact, you can use
the `version` property of the `ArtifactConfig`:

```python
from zenml import step, ArtifactConfig

@step
def my_step() -> (
    Annotated[
        int, 
        ArtifactConfig(
            name="my_custom_name", 
            version="my_custom_version"
        ),
    ]
):
    ...
```

The next execution of this step will then create an artifact with the name
"my_custom_name" and version "my_custom_version". This is primarily useful if
you are making a particularly important pipeline run (such as a release) whose
artifacts you want to distinguish at a glance later.

{% hint style="warning" %}
You cannot create two artifacts with the same name and version, so rerunning a
step that specifies a manual artifact version will always fail.
{% endhint %}

## Assign tags to your artifacts

If you want to tag the artifacts of a step or pipeline that is executed
repeatedly, you can use the `tags` property of `ArtifactConfig` to assign an arbitrary number of tags to the created artifacts:

```python
from zenml import step, ArtifactConfig

@step
def my_step() -> (
    Annotated[int, ArtifactConfig(tags=["my_tag_1", "my_tag_2"])]
):
    ...
```

This will assign tags "my_tag_1" and "my_tag_2" to all artifacts created by
this step, which can later be used to filter for artifacts in the dashboard.

## Link artifacts to models

`ArtifactConfig` contains several other properties that you can set to modify
how artifacts are linked to models:
- `model_name`: The name of the model to link the artifact to.
- `model_version`: The version of the model to link the artifact to.
- `is_model_artifact`: Whether the artifact is a model artifact.
- `is_deployment_artifact`: Whether the artifact is a deployment artifact.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
