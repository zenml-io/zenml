---
description: Model datasets using simple abstractions.
---

# Custom Dataset Classes and Complex Data Flows in ZenML

As machine learning projects grow in complexity, you often need to work with various data sources and manage intricate data flows. This chapter explores how to use custom Dataset classes and Materializers in ZenML to handle these challenges efficiently. For strategies on scaling your data processing for larger datasets, refer to [scaling strategies for big data](manage-big-data.md).

## Introduction to Custom Dataset Classes

Custom Dataset classes in ZenML provide a way to encapsulate data loading, processing, and saving logic for different data sources. They're particularly useful when:

1. Working with multiple data sources (e.g., CSV files, databases, cloud storage)
2. Dealing with complex data structures that require special handling
3. Implementing custom data processing or transformation logic

## Implementing Dataset Classes for Different Data Sources

Let's create a base Dataset class and implement it for CSV and BigQuery data sources:

```python
from abc import ABC, abstractmethod
import pandas as pd
from google.cloud import bigquery
from typing import Optional

class Dataset(ABC):
    @abstractmethod
    def read_data(self) -> pd.DataFrame:
        pass

class CSVDataset(Dataset):
    def __init__(self, data_path: str, df: Optional[pd.DataFrame] = None):
        self.data_path = data_path
        self.df = df

    def read_data(self) -> pd.DataFrame:
        if self.df is None:
            self.df = pd.read_csv(self.data_path)
        return self.df

class BigQueryDataset(Dataset):
    def __init__(
        self,
        table_id: str,
        df: Optional[pd.DataFrame] = None,
        project: Optional[str] = None,
    ):
        self.table_id = table_id
        self.project = project
        self.df = df
        self.client = bigquery.Client(project=self.project)

    def read_data(self) -> pd.DataFrame:
        query = f"SELECT * FROM `{self.table_id}`"
        self.df = self.client.query(query).to_dataframe()
        return self.df

    def write_data(self) -> None:
        job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
        job = self.client.load_table_from_dataframe(self.df, self.table_id, job_config=job_config)
        job.result()
```

## Creating Custom Materializers

[Materializers](./handle-custom-data-types.md) in ZenML handle the serialization and deserialization of artifacts. Custom Materializers are essential for working with custom Dataset classes:

```python
from typing import Type
from zenml.materializers import BaseMaterializer
from zenml.io import fileio
from zenml.enums import ArtifactType
import json
import os
import tempfile
import pandas as pd


class CSVDatasetMaterializer(BaseMaterializer):
    ASSOCIATED_TYPES = (CSVDataset,)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.DATA

    def load(self, data_type: Type[CSVDataset]) -> CSVDataset:
        # Create a temporary file to store the CSV data
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
            # Copy the CSV file from the artifact store to the temporary location
            with fileio.open(os.path.join(self.uri, "data.csv"), "rb") as source_file:
                temp_file.write(source_file.read())
            
            temp_path = temp_file.name

        # Create and return the CSVDataset
        dataset = CSVDataset(temp_path)
        dataset.read_data()
        return dataset

    def save(self, dataset: CSVDataset) -> None:
        # Ensure we have data to save
        df = dataset.read_data()

        # Save the dataframe to a temporary CSV file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
            df.to_csv(temp_file.name, index=False)
            temp_path = temp_file.name

        # Copy the temporary file to the artifact store
        with open(temp_path, "rb") as source_file:
            with fileio.open(os.path.join(self.uri, "data.csv"), "wb") as target_file:
                target_file.write(source_file.read())

        # Clean up the temporary file
        os.remove(temp_path)

class BigQueryDatasetMaterializer(BaseMaterializer):
    ASSOCIATED_TYPES = (BigQueryDataset,)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.DATA

    def load(self, data_type: Type[BigQueryDataset]) -> BigQueryDataset:
        with fileio.open(os.path.join(self.uri, "metadata.json"), "r") as f:
            metadata = json.load(f)
        dataset = BigQueryDataset(
            table_id=metadata["table_id"],
            project=metadata["project"],
        )
        dataset.read_data()
        return dataset

    def save(self, bq_dataset: BigQueryDataset) -> None:
        metadata = {
            "table_id": bq_dataset.table_id,
            "project": bq_dataset.project,
        }
        with fileio.open(os.path.join(self.uri, "metadata.json"), "w") as f:
            json.dump(metadata, f)
        if bq_dataset.df is not None:
            bq_dataset.write_data()
```

## Managing Complexity in Pipelines with Multiple Data Sources

When working with multiple data sources, it's crucial to design flexible pipelines that can handle different scenarios. Here's an example of how to structure a pipeline that works with both CSV and BigQuery datasets:

```python
from zenml import step, pipeline
from typing_extensions import Annotated

@step(output_materializer=CSVDatasetMaterializer)
def extract_data_local(data_path: str = "data/raw_data.csv") -> CSVDataset:
    return CSVDataset(data_path)

@step(output_materializer=BigQueryDatasetMaterializer)
def extract_data_remote(table_id: str) -> BigQueryDataset:
    return BigQueryDataset(table_id)

@step
def transform(dataset: Dataset) -> pd.DataFrame
    df = dataset.read_data()
    # Transform data
    transformed_df = df.copy()  # Apply transformations here
    return transformed_df

@pipeline
def etl_pipeline(mode: str = "develop"):
    if mode == "develop":
        raw_data = extract_data_local()
    else:
        raw_data = extract_data_remote(table_id="project.dataset.raw_table")

    transformed_data = transform(raw_data)
```

## Best Practices for Designing Flexible and Maintainable Pipelines

When working with custom Dataset classes in ZenML pipelines, it's crucial to design your pipelines
to accommodate various data sources and processing requirements.

Here are some best practices to ensure your pipelines remain flexible and maintainable:

1. **Use a common base class**: The `Dataset` base class allows for consistent handling of different data sources within your pipeline steps. This abstraction enables you to swap out data sources without changing the overall pipeline structure.

```python
@step
def process_data(dataset: Dataset) -> pd.DataFrame:
    data = dataset.read_data()
    # Process data...
    return processed_data
```

2. **Create specialized steps to load the right dataset**: Implement separate steps to load different datasets, while keeping underlying steps standardized.

```python
@step
def load_csv_data() -> CSVDataset:
    # CSV-specific processing
    pass

@step
def load_bigquery_data() -> BigQueryDataset:
    # BigQuery-specific processing
    pass

@step
def common_processing_step(dataset: Dataset) -> pd.DataFrame:
    # Loads the base dataset, does not know concrete type
    pass
```

3. **Implement flexible pipelines**: Design your pipelines to adapt to different data sources or processing requirements. You can use configuration parameters or conditional logic to determine which steps to execute.

```python
@pipeline
def flexible_data_pipeline(data_source: str):
    if data_source == "csv":
        dataset = load_csv_data()
    elif data_source == "bigquery":
        dataset = load_bigquery_data()
    
    final_result = common_processing_step(dataset)
    return final_result
```

4. **Modular step design**: Focus on creating steps that perform specific tasks (e.g., data loading, transformation, analysis) that can work with different dataset types. This promotes code reuse and ease of maintenance.

```python
@step
def transform_data(dataset: Dataset) -> pd.DataFrame:
    data = dataset.read_data()
    # Common transformation logic
    return transformed_data

@step
def analyze_data(data: pd.DataFrame) -> pd.DataFrame:
    # Common analysis logic
    return analysis_result
```

By following these practices, you can create ZenML pipelines that efficiently handle complex data flows and multiple data sources while remaining adaptable to changing requirements. This approach allows you to leverage the power of custom Dataset classes throughout your machine learning workflows, ensuring consistency and flexibility as your projects evolve.

For strategies on scaling your data processing as your datasets grow larger, refer to [scaling strategies for big data](manage-big-data.md).


