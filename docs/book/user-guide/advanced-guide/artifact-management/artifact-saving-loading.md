---
description: Saving and loading artifacts manually.
---

# Artifact saving and loading

Whenever you run a ZenML pipeline, all outputs of your steps are automatically saved as artifacts into your artifact store and subsequent steps automatically load them in again. For most use cases, this is the recommended way of saving or loading artifacts. However, there are a few exceptions that are enabled by the following advanced concepts:
- Using [External Artifacts](#external-artifacts), you can pass existing artifacts from other pipeline runs into your steps. You can also use them to pass complex Python objects that were not loaded by any other steps of your pipeline.
- You can also [save and load artifacts manually](#saving-and-loading-artifacts-manually) without defining them as inputs or outputs of your pipeline steps. This is primarily useful for creating and inspecting ZenML artifacts outside of your pipeline runs, e.g., if parts of your ML workflow are still done manually in Jupyter notebooks or the like.

## External Artifacts

External artifacts can be used to pass values to steps that are neither JSON serializable nor produced by an upstream step:

```python
import numpy as np
from zenml import ExternalArtifact, pipeline, step

@step
def trainer(data: np.ndarray) -> ...:
    ...

@pipeline
def my_pipeline():
    trainer(data=ExternalArtifact(np.array([1, 2, 3])))
```

You can also use an `ExternalArtifact` to pass an artifact stored in the ZenML 
database. Search can be performed in one of the following two ways:
- By providing an artifact ID.
- By providing an artifact name and version. If no version is provided,
    the latest version of that artifact will be used.

```python
from uuid import UUID

# Fetch by ID
artifact = ExternalArtifact(id=UUID("3a92ae32-a764-4420-98ba-07da8f742b76"))

# Fetch by name alone - uses latest version of this artifact
artifact = ExternalArtifact(name="my_artifact")

# Fetch by name and version
artifact = ExternalArtifact(name="my_artifact", version="my_version")
```

Optionally, you can configure the `ExternalArtifact` to use a custom [materializer](../artifact-management/handle-custom-data-types.md) for your data or disable artifact metadata and visualizations. Check out the [SDK docs](https://sdkdocs.zenml.io/latest/core\_code\_docs/core-steps/#zenml.artifacts.external\_artifact.ExternalArtifact) for all available options.

{% hint style="info" %}
Using an `ExternalArtifact` with input data for your step automatically disables caching for the step.
{% endhint %}

<details>

<summary>See it in action with the E2E example</summary>

*To set up the local environment used below, follow the recommendations from the
[Project templates](../../starter-guide/using-project-templates.md#advanced-guide).*

In [`pipelines/batch_inference.py`](../../../../../examples/e2e/pipelines/batch_inference.py), you can find an example using the `ExternalArtifact` concept to
share Artifacts produced by a training pipeline inside a batch inference pipeline.

On the ETL stage pipeline, developers can pass a `sklearn.Pipeline` fitted during training for feature preprocessing and apply it to transform inference input features.
With this, we ensure that the exact same feature preprocessor used during training will be used during inference.

```python
    ########## ETL stage  ##########
    df_inference, target = data_loader(is_inference=True)
    df_inference = inference_data_preprocessor(
        dataset_inf=df_inference,
        preprocess_pipeline=ExternalArtifact(
            name="preprocess_pipeline",
            pipeline_name=MetaConfig.pipeline_name_training,
        ),
        target=target,
    )
```

On the DataQuality stage pipeline, developers can pass `pd.DataFrame` used as a training dataset to be used as a reference dataset versus the current inference one to apply Evidently and get DataQuality report back.
With this, we ensure that the exact same training dataset used during the training phase will be used to compare with the inference dataset here.

```python
    ########## DataQuality stage  ##########
    report, _ = evidently_report_step(
        reference_dataset=ExternalArtifact(
            name="dataset_trn",
            pipeline_name=MetaConfig.pipeline_name_training,
        ),
        comparison_dataset=df_inference,
        ignored_cols=["target"],
        metrics=[
            EvidentlyMetricConfig.metric("DataQualityPreset"),
        ],
    )
```

</details>


## Saving and Loading Artifacts Manually

You can save and load ZenML artifacts manually by using the `zenml.save_artifact()` and `zenml.load_artifact()` util functions:

```python
import numpy as np
import zenml

x = np.ndarray([1, 2, 3])
zenml.save_artifact(x, name="my_numpy_array")
x = zenml.load_artifact("my_numpy_array")
```

{% hint style="info" %}
It is also possible to use these functions inside your ZenML steps. However, it is usually cleaner to return the artifacts as outputs of your step to save them, or to use [External Artifacts](#external-artifacts) to load them instead.
{% endhint %}

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
