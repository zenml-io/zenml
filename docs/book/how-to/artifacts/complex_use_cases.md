---
description: >-
  Advanced patterns and solutions for handling complex data scenarios in ZenML pipelines.
---

# Complex Artifact Use Cases

In real-world ML projects, you'll often encounter data scenarios that go beyond basic artifact management. This guide covers advanced patterns for handling complex data flows, large datasets, custom data types, and specialized workflows.

## Custom Dataset Classes

### Why Use Custom Dataset Classes?

When working with various data sources or complex data flows, creating dedicated dataset classes provides several benefits:

- **Abstraction**: Hide complexity of data loading and processing
- **Consistency**: Standardize data access patterns across your pipeline
- **Modularity**: Swap data sources without changing pipeline logic
- **Type safety**: Improve code quality and documentation

### Implementation Example

Here's how to implement a custom dataset class:

```python
from typing import Dict, List, Optional, Any
import pandas as pd
from zenml.steps import BaseParameters, step

class DatasetParameters(BaseParameters):
    """Parameters for dataset configuration."""
    source_type: str
    path_or_query: str
    filters: Optional[Dict[str, Any]] = None

class Dataset:
    """Base Dataset class for handling different data sources."""
    def __init__(self, params: DatasetParameters):
        self.params = params
        self._data = None
    
    @property
    def data(self) -> pd.DataFrame:
        """Load data lazily and return as DataFrame."""
        if self._data is None:
            self._data = self._load_data()
        return self._data
    
    def _load_data(self) -> pd.DataFrame:
        """Implement in subclasses."""
        raise NotImplementedError

class CSVDataset(Dataset):
    """Dataset implementation for CSV files."""
    def _load_data(self) -> pd.DataFrame:
        filters = self.params.filters or {}
        df = pd.read_csv(self.params.path_or_query)
        
        # Apply filters if any
        for column, value in filters.items():
            if column in df.columns:
                df = df[df[column] == value]
                
        return df

class BigQueryDataset(Dataset):
    """Dataset implementation for BigQuery."""
    def _load_data(self) -> pd.DataFrame:
        from google.cloud import bigquery
        
        client = bigquery.Client()
        query = self.params.path_or_query
        df = client.query(query).to_dataframe()
        
        # Apply filters if any
        filters = self.params.filters or {}
        for column, value in filters.items():
            if column in df.columns:
                df = df[df[column] == value]
                
        return df

@step
def create_dataset(params: DatasetParameters) -> Dataset:
    """Create a dataset based on parameters."""
    if params.source_type.lower() == "csv":
        return CSVDataset(params)
    elif params.source_type.lower() == "bigquery":
        return BigQueryDataset(params)
    else:
        raise ValueError(f"Unsupported source type: {params.source_type}")

@step
def process_dataset(dataset: Dataset) -> pd.DataFrame:
    """Process a dataset and return the processed data."""
    # Access data through the dataset interface
    df = dataset.data
    
    # Perform processing
    # ...
    
    return df
```

### Custom Materializers for Datasets

For custom dataset classes, you'll need custom materializers:

```python
from zenml.materializers.base_materializer import BaseMaterializer

class DatasetMaterializer(BaseMaterializer):
    """Materializer for Dataset objects."""
    
    ASSOCIATED_TYPES = (Dataset, CSVDataset, BigQueryDataset)
    
    def load(self, data_type):
        """Load dataset from artifact store."""
        # Load parameters
        params_path = self.artifact_path / "params.json"
        with open(params_path, "r") as f:
            import json
            params_dict = json.load(f)
        
        # Reconstruct parameters
        from zenml.utils import source_utils
        params_class = source_utils.load_class(params_dict["class_path"])
        params = params_class(**params_dict["config"])
        
        # Create dataset instance
        if params.source_type.lower() == "csv":
            return CSVDataset(params)
        elif params.source_type.lower() == "bigquery":
            return BigQueryDataset(params)
        else:
            raise ValueError(f"Unsupported source type: {params.source_type}")
    
    def save(self, dataset: Dataset):
        """Save dataset to artifact store."""
        # Save parameters
        params_path = self.artifact_path / "params.json"
        from zenml.utils import source_utils
        import json
        
        params_dict = {
            "class_path": source_utils.get_class_path(dataset.params.__class__),
            "config": dataset.params.dict()
        }
        
        with open(params_path, "w") as f:
            json.dump(params_dict, f)
```

### Best Practices for Dataset Patterns

1. **Design for flexibility**: Use a common base class with specialized implementations
2. **Create specialized steps**: Building steps around dataset concepts
3. **Maintain modularity**: Design pipeline steps to handle any dataset implementation
4. **Implement proper serialization**: Create custom materializers for datasets

## Managing Large Datasets

When working with large datasets that might not fit in memory, ZenML offers several approaches:

### Streaming Data Processing

Process data in chunks to avoid memory issues:

```python
@step
def process_large_dataset(data_path: str) -> pd.DataFrame:
    # Initialize an empty DataFrame for results
    results = []
    
    # Process in chunks
    chunk_size = 10000
    for chunk in pd.read_csv(data_path, chunksize=chunk_size):
        # Process chunk
        processed_chunk = process_chunk(chunk)
        results.append(processed_chunk)
    
    # Combine results
    return pd.concat(results, ignore_index=True)
```

### Using References Instead of Data

Pass file paths or database connections instead of actual data:

```python
@step
def data_reference_step() -> str:
    # Return a reference to data instead of the data itself
    return "s3://my-bucket/large-dataset.parquet"

@step
def process_with_reference(data_path: str) -> Dict[str, float]:
    # Process data using the reference
    import pyarrow.parquet as pq
    table = pq.read_table(data_path)
    
    # Calculate metrics without loading entire dataset
    metrics = calculate_metrics(table)
    return metrics
```

### Custom Materializers for Large Data

Implement custom materializers that handle large datasets efficiently:

```python
from zenml.materializers.base_materializer import BaseMaterializer
import pyarrow as pa
import pyarrow.parquet as pq

class ParquetDatasetMaterializer(BaseMaterializer):
    """Materializer that handles large datasets via Parquet files."""
    
    ASSOCIATED_TYPES = (pa.Table,)
    
    def load(self, data_type):
        """Load data from Parquet."""
        parquet_path = self.artifact_path / "data.parquet"
        return pq.read_table(parquet_path)
    
    def save(self, data: pa.Table):
        """Save data as Parquet."""
        parquet_path = self.artifact_path / "data.parquet"
        pq.write_table(data, parquet_path)
```

### Remote Compute for Large Data

Utilize remote compute environments with sufficient resources:

```python
@step(resources={"cpu": 8, "memory": "32GB"})
def process_large_dataset(data_path: str) -> pd.DataFrame:
    # This step will run on a machine with the specified resources
    df = pd.read_parquet(data_path)
    # Process data
    return processed_df
```

## Unmaterialized Artifacts

For cases where you need to avoid saving large intermediate results:

```python
@step(enable_cache=False)
def generate_large_intermediate() -> pd.DataFrame:
    # This data won't be persisted if used in a pipeline with enable_cache=False
    return very_large_dataframe

@pipeline(enable_cache=False)
def my_pipeline():
    data = generate_large_intermediate()
    # Use data in subsequent steps
```

## Passing Artifacts Between Pipelines

To share artifacts across pipelines:

```python
from zenml.client import Client

# Pipeline 1: Create and save artifact
@step
def create_model() -> Any:
    return trained_model

@pipeline
def training_pipeline():
    create_model()

# Run the first pipeline
training_run = training_pipeline()

# Pipeline 2: Use artifact from Pipeline 1
@step
def load_model(model_id: str) -> Any:
    # Get the artifact from a previous run
    client = Client()
    artifact = client.get_artifact(model_id)
    return artifact.load()

@step
def make_predictions(model: Any, data: pd.DataFrame) -> np.ndarray:
    return model.predict(data)

@pipeline
def inference_pipeline(model_id: str):
    model = load_model(model_id)
    data = load_data()
    predictions = make_predictions(model, data)

# Get model artifact ID from first pipeline
client = Client()
run = client.get_pipeline_run(training_run.id)
model_artifact = run.get_step("create_model").outputs.get("output")
model_id = model_artifact.id

# Run the second pipeline with the model artifact ID
inference_pipeline(model_id=model_id)
```

## Registering Existing Data as Artifacts

For integrating pre-existing data into your ZenML workflow:

```python
from zenml.client import Client

# Register existing data as an artifact
client = Client()
artifact = client.register_artifact(
    name="pretrained_model",
    data="path/to/pretrained_model.pkl",
)

# Use the registered artifact in a pipeline
@step
def use_registered_model(model_id: str) -> Any:
    client = Client()
    artifact = client.get_artifact(model_id)
    return artifact.load()

@pipeline
def inference_pipeline(model_id: str):
    model = use_registered_model(model_id)
    # Use model for inference

# Run the pipeline with the registered artifact ID
inference_pipeline(model_id=artifact.id)
```

## Advanced Dataset Management

### Versioned Datasets

Managing dataset versions:

```python
@step
def get_dataset_version(version: str) -> Dataset:
    client = Client()
    # Get a specific version of a dataset
    dataset_artifact = client.get_artifact_version("my_dataset", version)
    return dataset_artifact.load()
```

### Multi-source Data Pipelines

Handling data from multiple sources:

```python
@step
def combine_datasets(
    user_data: pd.DataFrame,
    product_data: pd.DataFrame,
    transaction_data: pd.DataFrame
) -> pd.DataFrame:
    # Join datasets from different sources
    merged_data = user_data.merge(
        transaction_data, on="user_id"
    ).merge(
        product_data, on="product_id"
    )
    return merged_data
```

## Conclusion

These advanced patterns enable you to handle complex data scenarios in your ML pipelines. By leveraging ZenML's flexibility and extensibility, you can create robust, efficient, and scalable workflows that accommodate the unique requirements of your projects.

For more information on artifact management in ZenML, see the [Artifacts](./artifacts.md) and [Visualizations](./visualizations.md) pages. 