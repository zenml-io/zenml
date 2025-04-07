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

| Materializer | Handled Data Types | Storage Format |
|--------------|-------------------|----------------|
| BuiltInMaterializer | `bool`, `float`, `int`, `str`, `None` | `.json` |
| BytesInMaterializer | `bytes` | `.txt` |
| BuiltInContainerMaterializer | `dict`, `list`, `set`, `tuple` | Directory |
| NumpyMaterializer | `np.ndarray` | `.npy` |
| PandasMaterializer | `pd.DataFrame`, `pd.Series` | `.csv` (or `.gzip` if `parquet` is installed) |
| PydanticMaterializer | `pydantic.BaseModel` | `.json` |
| ServiceMaterializer | `zenml.services.service.BaseService` | `.json` |
| StructuredStringMaterializer | `zenml.types.CSVString`, `zenml.types.HTMLString`, `zenml.types.MarkdownString` | `.csv` / `.html` / `.md` (depending on type) |

ZenML also provides a CloudpickleMaterializer that can handle any object by saving it with [cloudpickle](https://github.com/cloudpipe/cloudpickle). However, this is not production-ready because the resulting artifacts cannot be loaded when running with a different Python version. For production use, you should implement a custom materializer for your specific data types.

### Integration-Specific Materializers

When you install ZenML integrations, additional materializers become available:

| Integration | Materializer | Handled Data Types |
|-------------|--------------|-------------------|
| bentoml | BentoMaterializer | `bentoml.Bento` |
| deepchecks | DeepchecksResultMateriailzer | `deepchecks.CheckResult`, `deepchecks.SuiteResult` |
| evidently | EvidentlyProfileMaterializer | `evidently.Profile` |
| great_expectations | GreatExpectationsMaterializer | `great_expectations.ExpectationSuite`, `great_expectations.CheckpointResult` |
| huggingface | HFDatasetMaterializer | `datasets.Dataset`, `datasets.DatasetDict` |
| huggingface | HFPTModelMaterializer | `transformers.PreTrainedModel` |
| huggingface | HFTFModelMaterializer | `transformers.TFPreTrainedModel` |
| huggingface | HFTokenizerMaterializer | `transformers.PreTrainedTokenizerBase` |
| pytorch | PyTorchModuleMaterializer | `torch.Module` |
| tensorflow | KerasMaterializer | `tf.keras.Model` |
| tensorflow | TensorflowDatasetMaterializer | `tf.Dataset` |

> **Note**: When using Docker-based orchestrators, you must specify the appropriate integrations in your `DockerSettings` to ensure the materializers are available inside the container.

## Creating Custom Materializers

When working with custom data types, you'll need to create materializers to handle them. Here's how:

### 1. Define Your Materializer Class

Create a new class that inherits from `BaseMaterializer`:

```python
import os
from typing import Type, Any, Dict
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.enums import ArtifactType, VisualizationType
from zenml.metadata.metadata_types import MetadataType

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

### Metadata Extraction

The `extract_metadata()` method allows you to extract key information about your artifact for indexing and searching. This metadata will be displayed alongside the artifact in the dashboard.

### Temporary Files

If you need a temporary directory while processing artifacts, use the `get_temporary_directory()` helper:

```python
with self.get_temporary_directory() as temp_dir:
    # Process files in the temporary directory
    # Files will be automatically cleaned up
```

## Example: A Complete Materializer

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