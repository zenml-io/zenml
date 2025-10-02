---
description: Understanding and creating materializers to handle custom data types in ZenML pipelines
---

# Materializers

Materializers are a core concept in ZenML that enable the serialization, storage, and retrieval of artifacts in your ML pipelines. This guide explains how materializers work and how to create custom materializers for your specific data types.

## What Are Materializers?

A materializer is a class that defines how a particular data type is:

- **Serialized**: Converted from Python objects to a storable format
- **Saved**: Written to the artifact store
- **Loaded**: Read from the artifact store
- **Deserialized**: Converted back to Python objects
- **Visualized**: Displayed in the ZenML dashboard
- **Analyzed**: Metadata extraction for tracking and search

Materializers act as the bridge between your Python code and the underlying storage system, ensuring that any artifact can be saved, loaded, and visualized correctly, regardless of the data type.

## Built-In Materializers

ZenML includes built-in materializers for many common data types:

### Core Materializers

<table data-full-width="true"><thead><tr><th>Materializer</th><th>Handled Data Types</th><th>Storage Format</th></tr></thead><tbody><tr><td><a href="https://sdkdocs.zenml.io/latest/core_code_docs/core-materializers.html#zenml.materializers.built_in_materializer">BuiltInMaterializer</a></td><td><code>bool</code>, <code>float</code>, <code>int</code>, <code>str</code>, <code>None</code></td><td><code>.json</code></td></tr><tr><td><a href="https://sdkdocs.zenml.io/latest/core_code_docs/core-materializers.html#zenml.materializers.built_in_materializer">BytesInMaterializer</a></td><td><code>bytes</code></td><td><code>.txt</code></td></tr><tr><td><a href="https://sdkdocs.zenml.io/latest/core_code_docs/core-materializers.html#zenml.materializers.built_in_materializer">BuiltInContainerMaterializer</a></td><td><code>dict</code>, <code>list</code>, <code>set</code>, <code>tuple</code></td><td>Directory</td></tr><tr><td><a href="https://sdkdocs.zenml.io/latest/core_code_docs/core-materializers.html#zenml.materializers.numpy_materializer">NumpyMaterializer</a></td><td><code>np.ndarray</code></td><td><code>.npy</code></td></tr><tr><td><a href="https://sdkdocs.zenml.io/latest/core_code_docs/core-materializers.html#zenml.materializers.pandas_materializer">PandasMaterializer</a></td><td><code>pd.DataFrame</code>, <code>pd.Series</code></td><td><code>.csv</code> (or <code>.gzip</code> if <code>parquet</code> is installed)</td></tr><tr><td><a href="https://sdkdocs.zenml.io/latest/core_code_docs/core-materializers.html#zenml.materializers.pydantic_materializer">PydanticMaterializer</a></td><td><code>pydantic.BaseModel</code></td><td><code>.json</code></td></tr><tr><td><a href="https://sdkdocs.zenml.io/latest/core_code_docs/core-materializers.html#zenml.materializers.service_materializer">ServiceMaterializer</a></td><td><code>zenml.services.service.BaseService</code></td><td><code>.json</code></td></tr><tr><td><a href="https://sdkdocs.zenml.io/latest/core_code_docs/core-materializers.html#zenml.materializers.structured_string_materializer">StructuredStringMaterializer</a></td><td><code>zenml.types.CSVString</code>, <code>zenml.types.HTMLString</code>, <code>zenml.types.MarkdownString</code></td><td><code>.csv</code> / <code>.html</code> / <code>.md</code> (depending on type)</td></tr></tbody></table>

ZenML also provides a CloudpickleMaterializer that can handle any object by saving it with [cloudpickle](https://github.com/cloudpipe/cloudpickle). However, this is not production-ready because the resulting artifacts cannot be loaded when running with a different Python version. For production use, you should implement a custom materializer for your specific data types.

### Integration-Specific Materializers

When you install ZenML integrations, additional materializers become available:

<table data-full-width="true"><thead><tr><th width="199.5">Integration</th><th width="271">Materializer</th><th width="390">Handled Data Types</th><th>Storage Format</th></tr></thead><tbody><tr><td>bentoml</td><td><a href="https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-bentoml.html#zenml.integrations.bentoml">BentoMaterializer</a></td><td><code>bentoml.Bento</code></td><td><code>.bento</code></td></tr><tr><td>deepchecks</td><td><a href="https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-deepchecks.html#zenml.integrations.deepchecks">DeepchecksResultMateriailzer</a></td><td><code>deepchecks.CheckResult</code>, <code>deepchecks.SuiteResult</code></td><td><code>.json</code></td></tr><tr><td>evidently</td><td><a href="https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-evidently.html#zenml.integrations.evidently">EvidentlyProfileMaterializer</a></td><td><code>evidently.Profile</code></td><td><code>.json</code></td></tr><tr><td>great_expectations</td><td><a href="https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-great_expectations.html#zenml.integrations.great_expectations">GreatExpectationsMaterializer</a></td><td><code>great_expectations.ExpectationSuite</code>, <code>great_expectations.CheckpointResult</code></td><td><code>.json</code></td></tr><tr><td>huggingface</td><td><a href="https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-huggingface.html#zenml.integrations.huggingface">HFDatasetMaterializer</a></td><td><code>datasets.Dataset</code>, <code>datasets.DatasetDict</code></td><td>Directory</td></tr><tr><td>huggingface</td><td><a href="https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-huggingface.html#zenml.integrations.huggingface">HFPTModelMaterializer</a></td><td><code>transformers.PreTrainedModel</code></td><td>Directory</td></tr><tr><td>huggingface</td><td><a href="https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-huggingface.html#zenml.integrations.huggingface">HFTFModelMaterializer</a></td><td><code>transformers.TFPreTrainedModel</code></td><td>Directory</td></tr><tr><td>huggingface</td><td><a href="https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-huggingface.html#zenml.integrations.huggingface">HFTokenizerMaterializer</a></td><td><code>transformers.PreTrainedTokenizerBase</code></td><td>Directory</td></tr><tr><td>lightgbm</td><td><a href="https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-lightgbm.html#zenml.integrations.lightgbm">LightGBMBoosterMaterializer</a></td><td><code>lgbm.Booster</code></td><td><code>.txt</code></td></tr><tr><td>lightgbm</td><td><a href="https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-lightgbm.html#zenml.integrations.lightgbm">LightGBMDatasetMaterializer</a></td><td><code>lgbm.Dataset</code></td><td><code>.binary</code></td></tr><tr><td>neural_prophet</td><td><a href="https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-neural_prophet.html#zenml.integrations.neural_prophet">NeuralProphetMaterializer</a></td><td><code>NeuralProphet</code></td><td><code>.pt</code></td></tr><tr><td>pillow</td><td><a href="https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-pillow.html#zenml.integrations.pillow">PillowImageMaterializer</a></td><td><code>Pillow.Image</code></td><td><code>.PNG</code></td></tr><tr><td>polars</td><td><a href="https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-polars.html#zenml.integrations.polars">PolarsMaterializer</a></td><td><code>pl.DataFrame</code>, <code>pl.Series</code></td><td><code>.parquet</code></td></tr><tr><td>pycaret</td><td><a href="https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-pycaret.html#zenml.integrations.pycaret">PyCaretMaterializer</a></td><td>Any <code>sklearn</code>, <code>xgboost</code>, <code>lightgbm</code> or <code>catboost</code> model</td><td><code>.pkl</code></td></tr><tr><td>pytorch</td><td><a href="https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-pytorch.html#zenml.integrations.pytorch">PyTorchDataLoaderMaterializer</a></td><td><code>torch.Dataset</code>, <code>torch.DataLoader</code></td><td><code>.pt</code></td></tr><tr><td>pytorch</td><td><a href="https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-pytorch.html#zenml.integrations.pytorch">PyTorchModuleMaterializer</a></td><td><code>torch.Module</code></td><td><code>.pt</code></td></tr><tr><td>scipy</td><td><a href="https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-scipy.html#zenml.integrations.scipy">SparseMaterializer</a></td><td><code>scipy.spmatrix</code></td><td><code>.npz</code></td></tr><tr><td>spark</td><td><a href="https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-spark.html#zenml.integrations.spark">SparkDataFrameMaterializer</a></td><td><code>pyspark.DataFrame</code></td><td><code>.parquet</code></td></tr><tr><td>spark</td><td><a href="https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-spark.html#zenml.integrations.spark">SparkModelMaterializer</a></td><td><code>pyspark.Transformer</code></td><td><code>pyspark.Estimator</code></td></tr><tr><td>tensorflow</td><td><a href="https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-tensorflow.html#zenml.integrations.tensorflow">KerasMaterializer</a></td><td><code>tf.keras.Model</code></td><td>Directory</td></tr><tr><td>tensorflow</td><td><a href="https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-tensorflow.html#zenml.integrations.tensorflow">TensorflowDatasetMaterializer</a></td><td><code>tf.Dataset</code></td><td>Directory</td></tr><tr><td>whylogs</td><td><a href="https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-whylogs.html#zenml.integrations.whylogs">WhylogsMaterializer</a></td><td><code>whylogs.DatasetProfileView</code></td><td><code>.pb</code></td></tr><tr><td>xgboost</td><td><a href="https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-xgboost.html#zenml.integrations.xgboost">XgboostBoosterMaterializer</a></td><td><code>xgb.Booster</code></td><td><code>.json</code></td></tr><tr><td>xgboost</td><td><a href="https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-xgboost.html#zenml.integrations.xgboost">XgboostDMatrixMaterializer</a></td><td><code>xgb.DMatrix</code></td><td><code>.binary</code></td></tr></tbody></table>

> **Note**: When using Docker-based orchestrators, you must specify the appropriate integrations in your `DockerSettings` to ensure the materializers are available inside the container.

## Creating Custom Materializers

When working with custom data types, you'll need to create materializers to handle them. Here's how:

### 1. Define Your Materializer Class

Create a new class that inherits from `BaseMaterializer`:

```python
import os
import json
from typing import Type, Any, Dict
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.enums import ArtifactType, VisualizationType
from zenml.metadata.metadata_types import MetadataType

# Assume MyClass is your custom class defined elsewhere
# from mymodule import MyClass

class MyClassMaterializer(BaseMaterializer):
    """Materializer for MyClass objects."""
    
    # List the data types this materializer can handle
    ASSOCIATED_TYPES = (MyClass,)
    
    # Define what type of artifact this is (usually DATA or MODEL)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.DATA
    
    def load(self, data_type: Type[Any]) -> MyClass:
        """Load MyClass from storage."""
        # Implementation here
        filepath = os.path.join(self.uri, "data.json")
        with self.artifact_store.open(filepath, "r") as f:
            data = json.load(f)
        
        # Create and return an instance of MyClass
        return MyClass(**data)
    
    def save(self, data: MyClass) -> None:
        """Save MyClass to storage."""
        # Implementation here
        filepath = os.path.join(self.uri, "data.json")
        with self.artifact_store.open(filepath, "w") as f:
            json.dump(data.to_dict(), f)
    
    def save_visualizations(self, data: MyClass) -> Dict[str, VisualizationType]:
        """Generate visualizations for the dashboard."""
        # Optional - generate visualizations
        vis_path = os.path.join(self.uri, "visualization.html")
        with self.artifact_store.open(vis_path, "w") as f:
            f.write(data.to_html())
        
        return {vis_path: VisualizationType.HTML}
    
    def extract_metadata(self, data: MyClass) -> Dict[str, MetadataType]:
        """Extract metadata for tracking."""
        # Optional - extract metadata
        return {
            "name": data.name,
            "created_at": data.created_at,
            "num_records": len(data.records)
        }
```

### 2. Using Your Custom Materializer

Once you've defined the materializer, you can use it in your pipeline:

```python
from zenml import step, pipeline
# from mymodule import MyClass, MyClassMaterializer

@step(output_materializers=MyClassMaterializer)
def create_my_class() -> MyClass:
    """Create an instance of MyClass."""
    return MyClass(name="test", records=[1, 2, 3])

@step
def use_my_class(my_obj: MyClass) -> None:
    """Use the MyClass instance."""
    print(f"Name: {my_obj.name}, Records: {my_obj.records}")

@pipeline
def custom_pipeline():
    data = create_my_class()
    use_my_class(data)
```

### 3. Multiple Outputs with Different Materializers

When a step has multiple outputs that need different materializers:

```python
from typing import Tuple, Annotated

@step(output_materializers={
    "obj1": MyClass1Materializer,
    "obj2": MyClass2Materializer
})
def create_objects() -> Tuple[
    Annotated[MyClass1, "obj1"],
    Annotated[MyClass2, "obj2"]
]:
    """Create instances of different classes."""
    return MyClass1(), MyClass2()
```

### 4. Registering a Materializer Globally

You can register a materializer globally to override the default materializer for a specific type:

```python
from zenml.materializers.materializer_registry import materializer_registry
from zenml.materializers.base_materializer import BaseMaterializer
import pandas as pd

# Create a custom pandas materializer
class FastPandasMaterializer(BaseMaterializer):
    # Implementation here
    ...

# Register it for pandas DataFrames globally
materializer_registry.register_and_overwrite_type(
    key=pd.DataFrame, 
    type_=FastPandasMaterializer
)
```

## Materializer Implementation Details

When implementing a custom materializer, consider these aspects:

### Handling Storage

The `self.uri` property contains the path to the directory where your artifact should be stored. Use this path to create files or subdirectories for your data.

When reading or writing files, always use `self.artifact_store.open()` rather than direct file I/O to ensure compatibility with different artifact stores (local filesystem, cloud storage, etc.).

### Visualization Support

The `save_visualizations()` method allows you to create visualizations that will be shown in the ZenML dashboard. You can return multiple visualizations of different types:

- `VisualizationType.HTML`: Embedded HTML content
- `VisualizationType.MARKDOWN`: Markdown content
- `VisualizationType.IMAGE`: Image files
- `VisualizationType.CSV`: CSV tables

##### Configuring Visualizations

Some materializers support configuration via environment variables to customize their visualization behavior. For example:

- `ZENML_PANDAS_SAMPLE_ROWS`: Controls the number of rows shown in sample visualizations created by the `PandasMaterializer`. Default is 10 rows.

### Metadata Extraction

The `extract_metadata()` method allows you to extract key information about your artifact for indexing and searching. This metadata will be displayed alongside the artifact in the dashboard.

### Temporary Files

If you need a temporary directory while processing artifacts, use the `get_temporary_directory()` helper:

```python
with self.get_temporary_directory() as temp_dir:
    # Process files in the temporary directory
    # Files will be automatically cleaned up
```

### Example: A Complete Materializer

Here's a complete example of a custom materializer for a simple class:

```python
import os
import json
from typing import Type, Any, Dict
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.enums import ArtifactType

class MyObj:
    def __init__(self, name: str):
        self.name = name
    
    def to_dict(self):
        return {"name": self.name}
    
    @classmethod
    def from_dict(cls, data):
        return cls(name=data["name"])

class MyMaterializer(BaseMaterializer):
    """Materializer for MyObj objects."""
    
    ASSOCIATED_TYPES = (MyObj,)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.DATA
    
    def load(self, data_type: Type[Any]) -> MyObj:
        """Load MyObj from storage."""
        filepath = os.path.join(self.uri, "data.json")
        with self.artifact_store.open(filepath, "r") as f:
            data = json.load(f)
        
        return MyObj.from_dict(data)
    
    def save(self, data: MyObj) -> None:
        """Save MyObj to storage."""
        filepath = os.path.join(self.uri, "data.json")
        with self.artifact_store.open(filepath, "w") as f:
            json.dump(data.to_dict(), f)

# Usage in a pipeline
@step(output_materializers=MyMaterializer)
def create_my_obj() -> MyObj:
    return MyObj(name="my_object")

@step
def use_my_obj(my_obj: MyObj) -> None:
    print(f"Object name: {my_obj.name}")

@pipeline
def my_pipeline():
    obj = create_my_obj()
    use_my_obj(obj)
```

## Unmaterialized artifacts

Whenever you pass artifacts as outputs from one pipeline step to other steps as inputs, the corresponding materializer for the respective data type defines how this artifact is first serialized and written to the artifact store, and then deserialized and read in the next step.handle-custom-data-types. However, there are instances where you might **not** want to materialize an artifact in a step, but rather use a reference to it instead. This is where skipping materialization comes in.

{% hint style="warning" %}
Skipping materialization might have unintended consequences for downstream tasks that rely on materialized artifacts. Only skip materialization if there is no other way to do what you want to do.
{% endhint %}

#### How to skip materialization

While materializers should in most cases be used to control how artifacts are returned and consumed from pipeline steps, you might sometimes need to have a completely unmaterialized artifact in a step, e.g., if you need to know the exact path to where your artifact is stored.

An unmaterialized artifact is a [`zenml.materializers.UnmaterializedArtifact`](https://sdkdocs.zenml.io/latest/core_code_docs/core-artifacts.html#zenml.artifacts.unmaterialized_artifact). Among others, it has a property `uri` that points to the unique path in the artifact store where the artifact is persisted. One can use an unmaterialized artifact by specifying `UnmaterializedArtifact` as the type in the step:

```python
from zenml.artifacts.unmaterialized_artifact import UnmaterializedArtifact
from zenml import step

@step
def my_step(my_artifact: UnmaterializedArtifact):  # rather than pd.DataFrame
    pass
```

The following shows an example of how unmaterialized artifacts can be used in the steps of a pipeline. The pipeline we define will look like this:

```shell
s1 -> s3 
s2 -> s4
```

`s1` and `s2` produce identical artifacts, however `s3` consumes materialized artifacts while `s4` consumes unmaterialized artifacts. `s4` can now use the `dict_.uri` and `list_.uri` paths directly rather than their materialized counterparts.

```python
from typing import Annotated
from typing import Dict, List, Tuple

from zenml.artifacts.unmaterialized_artifact import UnmaterializedArtifact
from zenml import pipeline, step


@step
def step_1() -> Tuple[
    Annotated[Dict[str, str], "dict_"],
    Annotated[List[str], "list_"],
]:
    return {"some": "data"}, []


@step
def step_2() -> Tuple[
    Annotated[Dict[str, str], "dict_"],
    Annotated[List[str], "list_"],
]:
    return {"some": "data"}, []


@step
def step_3(dict_: Dict, list_: List) -> None:
    assert isinstance(dict_, dict)
    assert isinstance(list_, list)


@step
def step_4(
        dict_: UnmaterializedArtifact,
        list_: UnmaterializedArtifact,
) -> None:
    print(dict_.uri)
    print(list_.uri)


@pipeline
def example_pipeline():
    step_3(*step_1())
    step_4(*step_2())


example_pipeline()
```

You can see another example of using an `UnmaterializedArtifact` when triggering a [pipeline from another](../snapshots/snapshots.md#advanced-usage-running-snapshots-from-other-pipelines).

## Best Practices

When working with materializers:

1. **Prefer structured formats** over pickle or other binary formats for better cross-environment compatibility.

2. **Test your materializer** with different artifact stores (local, S3, etc.) to ensure it works consistently.

3. **Consider versioning** if your data structure might change over time.

4. **Create visualizations** to help users understand your artifacts in the dashboard.

5. **Extract useful metadata** to make artifacts easier to find and understand.

6. **Be explicit** about materializer assignments for clarity, even if ZenML can detect them automatically.

7. **Avoid using the CloudpickleMaterializer** in production as it's not reliable across different Python versions.

## Conclusion

Materializers are a powerful part of ZenML's artifact system, enabling proper storage and handling of any data type. By creating custom materializers for your specific data structures, you ensure that your ML pipelines are robust, efficient, and can handle any data type required by your workflows. 