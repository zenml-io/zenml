---
description: Understand and adjust how ZenML versions your data.
---

# Data management with ZenML

Until now, we have been focusing on step and pipeline code and configuration. Now, we will shift our attention to another pillar of any ML system: *data*.

Whenever you run a ZenML pipeline, all output data of your steps are automatically versioned as artifacts into your artifact store and subsequent steps automatically load them in again. Each artifact that ZenML saves in your artifact store is assigned a name and is versioned automatically.

## Giving names to your artifacts

You can use the `Annotated` object to give your outputs unique names:

```python
from typing_extensions import Annotated
import pandas as pd
from sklearn.datasets import load_iris

from zenml import pipeline, step


@step
def training_data_loader() -> Annotated[pd.DataFrame, "iris_dataset"]:
    """Load the iris dataset as pandas dataframe."""
    iris = load_iris(as_frame=True)
    return iris


@pipeline
def feature_engineering_pipeline():
    training_data_loader()


if __name__ == "__main__":
    feature_engineering_pipeline()
```

{% hint style="info" %}
If you do not give your outputs custom names, the artifacts created by your
ZenML steps will be named `{pipeline_name}::{step_name}::output` or
`{pipeline_name}::{step_name}::output_{i}` by default.
{% endhint %}

Now you will be able to find the created artifact as `iris_dataset` in ZenML:

{% tabs %}
{% tab title="OSS (CLI)" %}

`zenml artifacts list` can be used to list of artifacts and their versions.

{% endtab %}
{% tab title="Cloud (Dashboard)" %}

The [ZenML Cloud](https://zenml.io/cloud) dashboard has additional capabilities, that include visualizing these artifacts in the dashboard.

<figure><img src=".gitbook/assets/intro_dashboard_details.png" alt="ZenML Dashboard Details View" width="80%"><figcaption></figcaption></figure>

{% hint style="info" %}
To prevent visual clutter, only artifacts with custom names are displayed in
the ZenML dashboard by default. Thus, make sure to assign names to your most
important artifacts that you would like to explore visually.
{% endhint %}

{% endtab %}
{% endtabs %}

For more advanced configuration of your artifacts, users must use the `ArtifactConfig` class, to modify the name, version, and other properties of the artifacts.

## Assign custom artifact versions

ZenML automatically versions all created artifacts using auto-incremented
numbering. I.e., if you have defined a step creating an artifact named
"my_custom_artifact" as shown above, the first execution of the step will
create an artifact with this name and version "1", the second execution will
create version "2" and so on.

If you would like to override the version assigned to an artifact, you can use
the `version` property of the `ArtifactConfig`, and add it your step:

```python
from zenml import step, ArtifactConfig

@step
def training_data_loader() -> (
    Annotated[
        pd.DataFrame, 
        # Add `ArtifactConfig` to control more properties of your artifact
        ArtifactConfig(
            name="iris_dataset", 
            version="raw_2023"
        ),
    ]
):
    ...
```

The next execution of this step will then create an artifact with the name
`iris_dataset` and version `raw_2023`. This is primarily useful if
you are making a particularly important pipeline run (such as a release) whose
artifacts you want to distinguish at a glance later.

{% hint style="warning" %}
You cannot create two artifacts with the same name and version, so rerunning a
step that specifies a manual artifact version will always fail. Therefore, it might make sense to control the artifact config via a [YAML Config](../advanced-guide/pipelining-features/configure-steps-pipelines.md) so as not to constantly edit your codebase.
{% endhint %}

Now you will be able to find the created artifact version within your `iris_dataset`:

{% tabs %}
{% tab title="OSS (CLI)" %}

`zenml artifacts versions list` can be used to list of artifacts and their versions.

{% endtab %}
{% tab title="Cloud (Dashboard)" %}

The [ZenML Cloud](https://zenml.io/cloud) dashboard has additional capabilities, that include visualizing these artifacts versions in the dashboard.

<figure><img src=".gitbook/assets/intro_dashboard_details.png" alt="ZenML Dashboard Details View" width="80%"><figcaption></figcaption></figure>

{% endtab %}
{% endtabs %}

## Consuming a versioned artifact into a pipeline

Often times, there is a need to consume an artifact downstream after producing it in an upstream pipeline or step. Using `External Artifacts`, you can pass existing artifacts from other pipeline runs into your steps. Search can be performed in one of the following ways:

```python
from uuid import UUID
import pandas as pd
from zenml import step, pipeline, ExternalArtifact


@step 
def trainer(dataset: pd.DataFrame):
    ...

@pipeline
def training_pipeline():
    # Fetch by ID
    dataset_artifact = ExternalArtifact(id=UUID("3a92ae32-a764-4420-98ba-07da8f742b76"))

    # Fetch by name alone - uses latest version of this artifact
    dataset_artifact = ExternalArtifact(name="iris_dataset")

    # Fetch by name and version
    dataset_artifact = ExternalArtifact(name="iris_dataset", version="raw_2023")

    # Pass into any step
    trainer(dataset=dataset_artifact)


if __name__ == "__main__":
    training_pipeline()
```

{% hint style="info" %}
Using an `ExternalArtifact` with input data for your step automatically disables caching for the step.
{% endhint %}

## Passing external data into ZenML

It is sometimes relevant to consume data that is not produced by ZenML upstream. For example, let's say you have a snowflake query that produces a dataframe, or a CSV file that you need to read.

External artifacts can be used for this, to pass values to steps that are neither JSON serializable nor produced by an upstream step:

```python
import numpy as np
from zenml import ExternalArtifact, pipeline, step

@step
def trainer(data: np.ndarray) -> ...:
    ...

@pipeline
def training_pipeline():
    trainer(data=ExternalArtifact(np.array([1, 2, 3])))
```

Optionally, you can configure the `ExternalArtifact` to use a custom [materializer](../advanced-guide/artifact-management/handle-custom-data-types.md) for your data or disable artifact metadata and visualizations. Check out the [SDK docs](https://sdkdocs.zenml.io/latest/core\_code\_docs/core-steps/#zenml.artifacts.external\_artifact.ExternalArtifact) for all available options.

## Assign tags to your artifacts

If you want to tag the artifact versions of a step or pipeline that is executed
repeatedly, you can use the `tags` property of `ArtifactConfig` to assign an arbitrary number of tags to the created artifacts:

```python
from zenml import step, ArtifactConfig

@step
def training_data_loader() -> (
    Annotated[pd.DataFrame, ArtifactConfig(tags=["sklearn", "pre-training"])]
):
    ...
```

This will assign tags "sklearn" and "pre-training" to all artifacts created by
this step, which can later be used to filter and organize these artifacts.

Or you can use the CLI to add tags:

```shell
# Tag the artifact
zenml artifacts update iris_dataset -t sklearn

# Tag the artiact version
zenml artifacts versions update iris_dataset raw_2023 -t sklearn
```

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
