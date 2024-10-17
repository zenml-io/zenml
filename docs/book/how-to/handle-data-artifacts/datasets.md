---
description: Learn about how to manage big data with ZenML.
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

class CSVDatasetMaterializer(BaseMaterializer):
    ASSOCIATED_TYPES = (CSVDataset,)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.DATA

    def load(self, data_type: Type[CSVDataset]) -> CSVDataset:
        with fileio.open(os.path.join(self.uri, "metadata.json"), "r") as f:
            metadata = json.load(f)
        return CSVDataset(metadata["data_path"])

    def save(self, dataset: CSVDataset) -> None:
        metadata = {"data_path": dataset.data_path}
        with fileio.open(os.path.join(self.uri, "metadata.json"), "w") as f:
            json.dump(metadata, f)
        if dataset.df is not None:
            dataset.df.to_csv(dataset.data_path, index=False)

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

@step
def extract_data_local(data_path: str = "data/raw_data.csv") -> CSVDataset:
    return CSVDataset(data_path)

@step
def extract_data_remote(table_id: str) -> BigQueryDataset:
    return BigQueryDataset(table_id)

@step
def transform_csv(dataset: CSVDataset) -> Annotated[CSVDataset, "transformed_dataset"]:
    df = dataset.read_data()
    # Transform data
    transformed_df = df.copy()  # Apply transformations here
    return CSVDataset("tmp/transformed_data.csv", df=transformed_df)

@step
def transform_bq(dataset: BigQueryDataset) -> Annotated[BigQueryDataset, "transformed_dataset"]:
    df = dataset.read_data()
    # Transform data
    transformed_df = df.copy()  # Apply transformations here
    return BigQueryDataset(table_id="project.dataset.transformed_table", df=transformed_df)

@pipeline
def etl_pipeline(mode: str = "develop"):
    if mode == "develop":
        raw_data = extract_data_local()
        transformed_data = transform_csv(raw_data)
    else:
        raw_data = extract_data_remote(table_id="project.dataset.raw_table")
        transformed_data = transform_bq(raw_data)
```

## Best Practices for Designing Flexible and Maintainable Pipelines

1. **Use a common base class**: The `Dataset` base class allows for consistent handling of different data sources.

2. **Leverage type annotations**: Clearly specify input and output types for each step to improve code readability and catch errors early.

3. **Design for flexibility**: Use pipeline parameters to control flow and select appropriate steps based on the execution environment or requirements.

4. **Create specialized steps**: Implement separate steps for different dataset types to handle specific processing requirements while keeping your code modular.

5. **Modular step design**: Focus on specific tasks (e.g., extract, transform) that can work with different dataset types to promote code reuse and ease of maintenance.

By following these practices and utilizing custom Dataset classes and Materializers, you can create ZenML pipelines that efficiently handle complex data flows and multiple data sources. For strategies on scaling your data processing as your datasets grow larger, refer to [scaling strategies for big data](manage-big-data.md).