---
description: Understand and adjust how ZenML versions your data.
---

# Data artifact management with ZenML

Data sits at the heart of every machine learning workflow. Managing and versioning this data correctly is essential for reproducibility and traceability within your ML pipelines. ZenML takes a proactive approach to data versioning, ensuring that every artifact—be it data, models, or evaluations—is automatically tracked and versioned upon pipeline execution.

![Walkthrough of ZenML Artifact Control Plane (Dashboard available only on ZenML Cloud)](../../.gitbook/assets/dcp_walkthrough.gif)

This guide will delve into artifact versioning and management, showing you how to efficiently name, organize, and utilize your data with the ZenML framework.

## Managing artifacts produced by ZenML pipelines

Artifacts, the outputs of your steps and pipelines, are automatically versioned and stored in the artifact store. Configuring these artifacts is pivotal for transparent and efficient pipeline development.

### Giving names to your artifacts

Assigning custom names to your artifacts can greatly enhance their discoverability and manageability. As best practice, utilize the `Annotated` object within your steps to give precise, human-readable names to outputs:

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
Unspecified artifact outputs default to a naming pattern of `{pipeline_name}::{step_name}::output`. For visual exploration in the ZenML dashboard, it's best practice to give significant outputs clear custom names.
{% endhint %}

Artifacts named `iris_dataset` can then be found swiftly using various ZenML interfaces:

{% tabs %}
{% tab title="OSS (CLI)" %}

To list artifacts: `zenml artifacts list`

{% endtab %}
{% tab title="Cloud (Dashboard)" %}

The ZenML Cloud dashboard offers advanced visualization features for artifact exploration.

<figure><img src="../../.gitbook/assets/dcp_artifacts_list.png" alt=""><figcaption><p>ZenML Artifact Control Plane.</p></figcaption></figure>

{% hint style="info" %}
To prevent visual clutter, only artifacts with custom names are displayed in
the ZenML dashboard by default. Thus, make sure to assign names to your most
important artifacts that you would like to explore visually.
{% endhint %}

{% endtab %}
{% endtabs %}

### Versioning artifacts intentionally

ZenML automatically versions all created artifacts using auto-incremented
numbering. I.e., if you have defined a step creating an artifact named
`iris_dataset` as shown above, the first execution of the step will
create an artifact with this name and version "1", the second execution will
create version "2" and so on.

While ZenML handles artifact versioning automatically, you have the option to specify custom versions using the [`ArtifactConfig`](https://sdkdocs.zenml.io/latest/core_code_docs/core-model/#zenml.model.artifact_config.DataArtifactConfig). This may come into play during critical runs like production releases.


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
Since custom versions cannot be duplicated, the above step can only be run once successfully. To avoid altering your code frequently, consider using a [YAML Config](../advanced-guide/pipelining-features/configure-steps-pipelines.md) for artifact versioning.
{% endhint %}

After execution, `iris_dataset` and its version `raw_2023` can be seen using:

{% tabs %}
{% tab title="OSS (CLI)" %}

To list versions: `zenml artifacts versions list`

{% endtab %}
{% tab title="Cloud (Dashboard)" %}

The Cloud dashboard visualizes version history for your review.

<figure><img src="../../.gitbook/assets/dcp_artifacts_versions_list.png" alt=""><figcaption><p>ZenML Data Versions List.</p></figcaption></figure>

{% endtab %}
{% endtabs %}

### Visualizing Artifacts

![Visualizing artifacts](../../.gitbook/assets/intro_dashboard_details.png)

ZenML automatically saves visualizations for many common data types, allowing you to view them in the ZenML dashboard. This provides an intuitive way to explore and understand the artifacts generated by your ML pipelines, making it easier to identify patterns, trends, and potential issues in your data and models.

When you ran your `training_pipeline` above, you will see some visualizations already created for your artifacts. Explore them in the dashboard!

See the [artifact visualization docs](../advanced-guide/data-management/visualize-artifacts.md) for more information on how add your own visualizations for your artifacts!

### Passing artifacts to a downstream pipeline

You don't always want to start your pipeline with a step that produces an artifact. Often times, you want to consume artifacts in other ways.

#### Consuming external artifacts within a pipeline

The `ExternalArtifact` class can be used to initialize an artifact within ZenML with any arbitary data type.

For example, let's say you have a snowflake query that produces a dataframe, or a CSV file that you need to read. External artifacts can be used for this, to pass values to steps that are neither JSON serializable nor produced by an upstream step:

```python
import numpy as np
from zenml import ExternalArtifact, pipeline, step

@step
def print_data(data: np.ndarray):
    print(data)

@pipeline
def printing_pipeline():
    # One can also pass data directly into the ExternalArtifact
    # to create a new artifact on the fly
    data = ExternalArtifact(value=np.array([0]))

    print_data(data=data)


if __name__ == "__main__":
    printing_pipeline()
```

Optionally, you can configure the `ExternalArtifact` to use a custom [materializer](../advanced-guide/data-management/handle-custom-data-types.md) for your data or disable artifact metadata and visualizations. Check out the [SDK docs](https://sdkdocs.zenml.io/latest/core_code_docs/core-artifacts/#zenml.artifacts.external_artifact.ExternalArtifact) for all available options.

#### Consuming artifacts produced by other pipelines

Often times, there is a need to consume an artifact downstream after producing it in an upstream pipeline or step. Again, using `ExternalArtifact`, you can pass existing artifacts from other pipeline runs into your steps:

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

## Managing artifacts **not** produced by ZenML pipelines

Sometimes, artifacts can be produced completely outside of ZenML. A good example of this the predictions produced by a deployed model.

```python
# A model is deployed, running in a FastAPI container
# Let's use the ZenML client to fetch the latest model and make predictions

from zenml.client import Client
from zenml import save_artifact

# In this case, we are fetching the model directly from the latest run
last_run = Client().get_pipeline("training_pipeline").last_run
model = last_run.steps["svc_trainer"].outputs["trained_model"].load()

# Lets make a prediction
prediction = model.predict([[1, 1, 1, 1]])

# We now store this prediction in ZenML as an artifact
# This will create a new artifact version
save_artifact(prediction, name="iris_predictions")
```

You can also load any artifact stored within ZenML using the `load_artifact` method:

```python
# Loads the latest version
load_artifact("iris_predictions")
```

{% hint style="info" %}
`load_artifact` is simply short-hand for the following Client call:

```python
from zenml.client import Client

client = Client()
client.get_artifact("iris_predictions").load()
```
{% endhint %}

Even if an artifact is created externally, it can be treated like any other artifact produced by
ZenML steps - with all the functionalities described above!

## Assigning tags to your artifacts

If you want to tag the artifact versions of a step or pipeline that is executed
repeatedly, you can use the `tags` property of `ArtifactConfig` to assign an arbitrary number of tags to the created artifacts:

{% tabs %}
{% tab title="Python SDK" %}

```python
from zenml import step, ArtifactConfig

@step
def training_data_loader() -> (
    Annotated[pd.DataFrame, ArtifactConfig(tags=["sklearn", "pre-training"])]
):
    ...
```

{% endtab %}
{% tab title="CLI" %}
You can use the `zenml artifacts` CLI to add tags:

```shell
# Tag the artifact
zenml artifacts update iris_dataset -t sklearn

# Tag the artiact version
zenml artifacts versions update iris_dataset raw_2023 -t sklearn
```

{% endtab %}
{% endtabs %}

This will assign tags "sklearn" and "pre-training" to all artifacts created by
this step, which can later be used to filter and organize these artifacts.

To learn more about artifacts, please refer to the [Advanced section on artifact management](../advanced-guide/data-management/).
For now, let's keep going on understanding major ZenML concepts!


## Code Example

This section combines all the code from this section into one simple script that you can use easily:

<details>

<summary>Code Example of this Section</summary>


```python
from typing import Optional, Tuple
from typing_extensions import Annotated

import numpy as np
from sklearn.base import ClassifierMixin
from sklearn.datasets import load_digits
from sklearn.svm import SVC
import zenml
from zenml import ArtifactConfig, ExternalArtifact, pipeline, step


@step
def versioned_data_loader_step() -> (
    Annotated[
        Tuple[np.ndarray, np.ndarray],
        ArtifactConfig(
            name="my_dataset",
            tags=["digits", "computer vision", "classification"],
        ),
    ]
):
    """Loads the digits dataset as a tuple of flattened numpy arrays."""
    digits = load_digits()
    return (digits.images.reshape((len(digits.images), -1)), digits.target)


@step
def model_finetuner_step(
    model: ClassifierMixin, dataset: Tuple[np.ndarray, np.ndarray]
) -> Annotated[
    ClassifierMixin, ArtifactConfig(name="my_model", tags=["SVC", "trained"])
]:
    """Finetunes a given model on a given dataset."""
    model.fit(dataset[0], dataset[1])
    return model


@pipeline
def model_finetuning_pipeline(
    dataset_version: Optional[str] = None,
    model_version: Optional[str] = None,
):
    # Either load a previous version of "my_dataset" or create a new one
    if dataset_version:
        dataset = ExternalArtifact(name="my_dataset", version=dataset_version)
    else:
        dataset = versioned_data_loader_step()

    # Load the model to finetune
    # If no version is specified, the latest version of "my_model" is used
    model = ExternalArtifact(name="my_model", version=model_version)

    # Finetune the model
    # This automatically creates a new version of "my_model"
    model_finetuner_step(model=model, dataset=dataset)


def main():
    # Save an untrained model as first version of "my_model"
    untrained_model = SVC(gamma=0.001)
    zenml.save_artifact(
        untrained_model, name="my_model", version="1", tags=["SVC", "untrained"]
    )

    # Create a first version of "my_dataset" and train the model on it
    model_finetuning_pipeline()

    # Finetune the latest model on an older version of the dataset
    model_finetuning_pipeline(dataset_version="1")

    # Run inference with the latest model on an older version of the dataset
    latest_trained_model = zenml.load_artifact("my_model")
    old_dataset = zenml.load_artifact("my_dataset", version="1")
    latest_trained_model.predict(old_dataset[0])

if __name__ == "__main__":
    main()
```

This would create the following pipeline run DAGs:

#### Run 1:

<figure><img src="../../.gitbook/assets/artifact_management_1.png" alt=""><figcaption><p>Create a first version of my_dataset</p></figcaption></figure>

#### Run 2:

<figure><img src="../../.gitbook/assets/artifact_management_2.png" alt=""><figcaption><p>Uses a second version of my_dataset</p></figcaption></figure>

</details>

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>