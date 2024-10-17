---
description: Learn about how to manage big data with ZenML.
---

# Scaling Strategies for Big Data in ZenML

As your machine learning projects grow, you'll often encounter datasets that challenge your existing data processing pipelines. This section explores strategies for scaling your ZenML pipelines to handle increasingly large datasets. For information on creating custom Dataset classes and managing complex data flows, refer to [custom dataset classes](datasets.md).

## Understanding Dataset Size Thresholds

Before diving into specific strategies, it's important to understand the general thresholds where different approaches become necessary:

1. **Small datasets (up to a few GB)**: These can typically be handled in-memory with standard pandas operations.
2. **Medium datasets (up to tens of GB)**: Require chunking or out-of-core processing techniques.
3. **Large datasets (hundreds of GB or more)**: Necessitate distributed processing frameworks.

## Strategies for Datasets up to a Few Gigabytes

For datasets that can still fit in memory but are becoming unwieldy, consider these optimizations:

1. **Use efficient data formats**: Switch from CSV to more efficient formats like Parquet:

```python
import pyarrow.parquet as pq

class ParquetDataset(Dataset):
    def __init__(self, data_path: str):
        self.data_path = data_path

    def read_data(self) -> pd.DataFrame:
        return pq.read_table(self.data_path).to_pandas()

    def write_data(self, df: pd.DataFrame):
        table = pa.Table.from_pandas(df)
        pq.write_table(table, self.data_path)
```

2. **Implement basic data sampling**: Add sampling methods to your Dataset classes:

```python
import random

class SampleableDataset(Dataset):
    def sample_data(self, fraction: float = 0.1) -> pd.DataFrame:
        df = self.read_data()
        return df.sample(frac=fraction)

@step
def analyze_sample(dataset: SampleableDataset) -> Dict[str, float]:
    sample = dataset.sample_data(fraction=0.1)
    # Perform analysis on the sample
    return {"mean": sample["value"].mean(), "std": sample["value"].std()}
```

3. **Optimize pandas operations**: Use efficient pandas and numpy operations to minimize memory usage:

```python
@step
def optimize_processing(df: pd.DataFrame) -> pd.DataFrame:
    # Use inplace operations where possible
    df['new_column'] = df['column1'] + df['column2']
    
    # Use numpy operations for speed
    df['mean_normalized'] = df['value'] - np.mean(df['value'])
    
    return df
```

## Handling Datasets up to Tens of Gigabytes

When your data no longer fits comfortably in memory, consider these strategies:

### Chunking for CSV Datasets

Implement chunking in your Dataset classes to process large files in manageable pieces:

```python
class ChunkedCSVDataset(Dataset):
    def __init__(self, data_path: str, chunk_size: int = 10000):
        self.data_path = data_path
        self.chunk_size = chunk_size

    def read_data(self):
        for chunk in pd.read_csv(self.data_path, chunksize=self.chunk_size):
            yield chunk

@step
def process_chunked_csv(dataset: ChunkedCSVDataset) -> pd.DataFrame:
    processed_chunks = []
    for chunk in dataset.read_data():
        processed_chunks.append(process_chunk(chunk))
    return pd.concat(processed_chunks)

def process_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    # Process each chunk here
    return chunk
```

### Leveraging Data Warehouses for Large Datasets

You can utilize data warehouses like [Google BigQuery](https://cloud.google.com/bigquery) for its distributed processing capabilities:

```python
@step
def process_big_query_data(dataset: BigQueryDataset) -> BigQueryDataset:
    client = bigquery.Client()
    query = f"""
    SELECT 
        column1, 
        AVG(column2) as avg_column2
    FROM 
        `{dataset.table_id}`
    GROUP BY 
        column1
    """
    result_table_id = f"{dataset.project}.{dataset.dataset}.processed_data"
    job_config = bigquery.QueryJobConfig(destination=result_table_id)
    query_job = client.query(query, job_config=job_config)
    query_job.result()  # Wait for the job to complete
    
    return BigQueryDataset(table_id=result_table_id)
```

## Approaches for Very Large Datasets (Hundreds of Gigabytes or More): Using Distributed Computing Frameworks in ZenML

When dealing with very large datasets, you may need to leverage distributed computing frameworks like Apache Spark or Ray. ZenML doesn't have built-in integrations for these frameworks, but you can use them directly within your pipeline steps. Here's how you can incorporate Spark and Ray into your ZenML pipelines:

### Using Apache Spark in ZenML

To use Spark within a ZenML pipeline, you simply need to initialize and use Spark within your step function:

```python
from pyspark.sql import SparkSession
from zenml import step, pipeline

@step
def process_with_spark(input_data: str) -> None:
    # Initialize Spark
    spark = SparkSession.builder.appName("ZenMLSparkStep").getOrCreate()
    
    # Read data
    df = spark.read.format("csv").option("header", "true").load(input_data)
    
    # Process data using Spark
    result = df.groupBy("column1").agg({"column2": "mean"})
    
    # Write results
    result.write.csv("output_path", header=True, mode="overwrite")
    
    # Stop the Spark session
    spark.stop()

@pipeline
def spark_pipeline(input_data: str):
    process_with_spark(input_data)

# Run the pipeline
spark_pipeline(input_data="path/to/your/data.csv")
```

Note that you'll need to have Spark installed in your environment and ensure that the necessary Spark dependencies are available when running your pipeline.

### Using Ray in ZenML

Similarly, to use Ray within a ZenML pipeline, you can initialize and use Ray directly within your step:

```python
import ray
from zenml import step, pipeline

@step
def process_with_ray(input_data: str) -> None:
    ray.init()

    @ray.remote
    def process_partition(partition):
        # Process a partition of the data
        return processed_partition

    # Load and split your data
    data = load_data(input_data)
    partitions = split_data(data)

    # Distribute processing across Ray cluster
    results = ray.get([process_partition.remote(part) for part in partitions])

    # Combine and save results
    combined_results = combine_results(results)
    save_results(combined_results, "output_path")

    ray.shutdown()

@pipeline
def ray_pipeline(input_data: str):
    process_with_ray(input_data)

# Run the pipeline
ray_pipeline(input_data="path/to/your/data.csv")
```

As with Spark, you'll need to have Ray installed in your environment and ensure that the necessary Ray dependencies are available when running your pipeline.

### Using Dask in ZenML

[Dask](https://docs.dask.org/en/stable/) is a flexible library for parallel computing in Python. It can be integrated into ZenML pipelines to handle large datasets and parallelize computations. Here's how you can use Dask within a ZenML pipeline:

```python
from zenml import step, pipeline
import dask.dataframe as dd
from zenml.materializers.base_materializer import BaseMaterializer
import os

class DaskDataFrameMaterializer(BaseMaterializer):
    ASSOCIATED_TYPES = (dd.DataFrame,)
    ASSOCIATED_ARTIFACT_TYPE = "dask_dataframe"

    def load(self, data_type):
        return dd.read_parquet(os.path.join(self.uri, "data.parquet"))

    def save(self, data):
        data.to_parquet(os.path.join(self.uri, "data.parquet"))

@step(output_materializers=DaskDataFrameMaterializer)
def create_dask_dataframe():
    df = dd.from_pandas(pd.DataFrame({'A': range(1000), 'B': range(1000, 2000)}), npartitions=4)
    return df

@step
def process_dask_dataframe(df: dd.DataFrame) -> dd.DataFrame:
    result = df.map_partitions(lambda x: x ** 2)
    return result

@step
def compute_result(df: dd.DataFrame) -> pd.DataFrame:
    return df.compute()

@pipeline
def dask_pipeline():
    df = create_dask_dataframe()
    processed = process_dask_dataframe(df)
    result = compute_result(processed)

# Run the pipeline
dask_pipeline()

```

In this example, we've created a custom `DaskDataFrameMaterializer` to handle Dask DataFrames. The pipeline creates a Dask DataFrame, processes it using Dask's distributed computing capabilities, and then computes the final result.

### Using Numba in ZenML

[Numba](https://numba.pydata.org/) is a just-in-time compiler for Python that can significantly speed up numerical Python code. Here's how you can integrate Numba into a ZenML pipeline:

```python
from zenml import step, pipeline
import numpy as np
from numba import jit
import os

@jit(nopython=True)
def numba_function(x):
    return x * x + 2 * x - 1

@step
def load_data() -> np.ndarray:
    return np.arange(1000000)

@step
def apply_numba_function(data: np.ndarray) -> np.ndarray:
    return numba_function(data)

@pipeline
def numba_pipeline():
    data = load_data()
    result = apply_numba_function(data)

# Run the pipeline
numba_pipeline()
```

The pipeline creates a Numba-accelerated function, applies it to a large NumPy array, and returns the result.

### Important Considerations

1. **Environment Setup**: Ensure that your execution environment (local or remote) has the necessary frameworks (Spark or Ray) installed.

2. **Resource Management**: When using these frameworks within ZenML steps, be mindful of resource allocation. The frameworks will manage their own resources, which needs to be coordinated with ZenML's orchestration.

3. **Error Handling**: Implement proper error handling and cleanup, especially for shutting down Spark sessions or Ray runtime.

4. **Data I/O**: Consider how data will be passed into and out of the distributed processing step. You might need to use intermediate storage (like cloud storage) for large datasets.

5. **Scaling**: While these frameworks allow for distributed processing, you'll need to ensure your infrastructure can support the scale of computation you're attempting.

By incorporating Spark or Ray directly into your ZenML steps, you can leverage the power of distributed computing for processing very large datasets while still benefiting from ZenML's pipeline management and versioning capabilities.

## Choosing the Right Scaling Strategy

When selecting a scaling strategy, consider:

1. **Dataset size**: Start with simpler strategies for smaller datasets and move to more complex solutions as your data grows.
2. **Processing complexity**: Simple aggregations might be handled by BigQuery, while complex ML preprocessing might require Spark or Ray.
3. **Infrastructure and resources**: Ensure you have the necessary compute resources for distributed processing.
4. **Update frequency**: Consider how often your data changes and how frequently you need to reprocess it.
5. **Team expertise**: Choose technologies that your team is comfortable with or can quickly learn.

Remember, it's often best to start simple and scale up as needed. ZenML's flexible architecture allows you to evolve your data processing strategies as your project grows.

By implementing these scaling strategies, you can extend your ZenML pipelines to handle datasets of any size, ensuring that your machine learning workflows remain efficient and manageable as your projects scale. For more information on creating custom Dataset classes and managing complex data flows, refer back to [custom dataset classes](datasets.md).