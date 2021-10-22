---
description: Reading from a continuously changing datasource
---

If you want to see the code for this chapter of the guide, head over to the [GitHub](https://github.com/zenml-io/zenml/tree/main/examples/low_level_guide/chapter_6.py).

# Chapter 6: Import data from a dynamic data source

Until now, we've been reading from a static data importer step because we are at the experimentation phase of the ML workflow. Now as we head towards production, we want to switch over to a non-static, dynamic data importer step:

This could be anything like:

* A database/data warehouse that updates regularly (SQL databases, BigQuery, Snowflake)
* A data lake (S3 Buckets/Azure Blob Storage/GCP Storage)
* An API which allows you to query the latest data.

## Read from a dynamic datasource

Let's also slightly change our pipeline to add our new step. For this guide, we have set up a [public BigQuery table]() that simulates a real world setting of reading from a production database. The data in the public BigQuery table is just MNIST data but new data is added every day.

```python
from google.cloud import bigquery
import numpy as np
from zenml.steps import step
from zenml.steps.step_output import Output


@step
def dynamic_importer() -> Output(
    X_train=np.ndarray, y_train=np.ndarray, X_test=np.ndarray, y_test=np.ndarray
):
    
    bqclient = bigquery.Client()
    
    # Download query results.
    query_string = """
    SELECT
    CONCAT(
        'https://stackoverflow.com/questions/',
        CAST(id as STRING)) as url,
    view_count
    FROM `zenml-core.mnist.mnist_data`
    WHERE timestamp like '%google-bigquery%'
    ORDER BY view_count DESC
    """
    
    dataframe = (
        bqclient.query(query_string)
        .result()
        .to_dataframe(
            # Optionally, explicitly request to use the BigQuery Storage API. As of
            # google-cloud-bigquery version 1.26.0 and above, the BigQuery Storage
            # API is used by default.
            create_bqstorage_client=True,
        )
    )
    return dataframe[], 
```

And then change the pipeline run as follows:

```python
scikit_p = mnist_pipeline(
    importer=dynamic_importer(),
    normalizer=normalize_mnist(),
    trainer=sklearn_trainer(),
    evaluator=sklearn_evaluator(),
)
```

## Run
You can run this as follows:

```python
python chapter_6.py
```

## Inspect 

Even if our data originally lives in BigQuery, we have now downloaded it and versioned locally as we ran this pipeline. So we can fetch it and inspect it:

```python
from zenml.core.repo import Repository

repo = Repository()
p = repo.get_pipeline(pipeline_name="load_and_normalize_pipeline")
runs = p.get_runs()
print(f"Pipeline `load_and_normalize_pipeline` has {len(runs)} run(s)")
run = runs[-1]
print(f"The run you just made has {len(run.steps)} steps.")
step = run.get_step('normalize_mnist')
print(f"The `normalizer` step has {len(step.outputs)} output artifacts.")
for i, o in enumerate(step.outputs):
    arr = o.read(None)
    print(f"Output {i} is an array with shape: {arr.shape}")
```

You will get the following output:

```bash
Pipeline `load_and_normalize_pipeline` has 1 run(s)
The run you just made has 2 steps.
The `normalizer` step has 2 output artifacts.
Output 0 is an array with shape: (60000, 28, 28)
Output 1 is an array with shape: (10000, 28, 28)
```

This show's that the data shape is the same as we had from the previous runs!

{% hint style="info" %}
In the near future, ZenML will help you automatically detect drift and schema changes across pipeline runs, to make your pipelines even more robust! Keep an eye out on this space and future releases!
{% endhint %}