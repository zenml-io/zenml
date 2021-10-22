---
description: Deploy pipelines to production
---

If you want to see the code for this chapter of the guide, head over to the [GitHub](https://github.com/zenml-io/zenml/tree/main/examples/low_level_guide/chapter_6.py).

# Chapter 6: Deploy pipelines to production

When developing ML models, your pipelines will, at first, most probably live in your machine with a local [Stack](../../core-concepts.md). However, at a certain point when you are finished with its design, you might want to transition to a more production-ready setting, and deploy the pipeline to a more robust environment.

We might also take the chance to edit the first step of our pipeline from reading static data to reading data from a continuously updating source of data.


## Install and configure Airflow

This part is optional, and it would depend on your pre-existing production setting. For example, for this guide we chose to deploy and install Airflow from scratch and set it to work with a local `DAG_FOLDER`, however you might want to use a manage Airflow instance like [Cloud Composer](https://cloud.google.com/composer) or [Astronomer](https://astronomer.io/) and change the `DAG_FOLDER` accordingly.

To install Airflow, please follow the [awesome official guide](https://airflow.apache.org/docs/apache-airflow/stable/start/local.html). Its just a pip install really.

## Read from a dynamic datasource

Let's also slightly change our pipeline. Until now, we've been reading from a static data importer step because we are at the experimentation phase of the ML workflow. Now in production, we want to switch over to a non-static, dynamic data importer step:

```python
from google.cloud import bigquery
import numpy as np
import tensorflow as tf
from sklearn.base import ClassifierMixin
from sklearn.linear_model import LogisticRegression

from zenml.pipelines import pipeline
from zenml.steps import step
from zenml.steps.step_output import Output


@step
def importer_mnist() -> Output(
    X_train=np.ndarray, y_train=np.ndarray, X_test=np.ndarray, y_test=np.ndarray
):
    """Download the MNIST data and store it as an artifact"""
    (X_train, y_train), (
        X_test,
        y_test,
    ) = tf.keras.datasets.mnist.load_data()
    return X_train, y_train, X_test, y_test

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
    FROM `bigquery-public-data.stackoverflow.posts_questions`
    WHERE tags like '%google-bigquery%'
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
scikit_p = dynamic_importer(
    importer=importer_mnist(),
    normalizer=normalize_mnist(),
    trainer=sklearn_trainer(),
    evaluator=sklearn_evaluator(),
)
```
## Creating an Airflow Stack

A [Stack](../../core-concepts.md) is the configuration of the surrounding infrastructure where ZenML pipelines are run and managed. For now the stack consists of:

* A metadata store: To store metadata like parameters and artifact URIs
* An artifact store: To store interim data step output.
* An orchestrator: A service that actually kicks off and runs each step of the pipeline.

When you did `zenml init` at the start of this guide, a default `local_stack` was created with local version of all of these. In order to see the stack you can check it out in the command line:

```shell
zenml stack list
```

Output:
```bash
STACKS:
key          stack_type    metadata_store_name    artifact_store_name    orchestrator_name
-----------  ------------  ---------------------  ---------------------  -------------------
local_stack  base          local_metadata_store   local_artifact_store   local_orchestrator
```

Let's stick with the `local_metadata_store` and a `local_artifact_store` for now and create an Airflow orchestrator and stack.

```shell
zenml orchestrator register airflow_orchestrator airflow
zenml stack register airflow_stack \
    -m local_metadata_store \
    -a local_artifact_store \
    -o airflow_orchestrator
```

Output:
```bash
Orchestrator `airflow_orchestrator` successfully registered!
Stack `airflow_stack` successfully registered!
```

This does the following:
* Changes AIRFLOW_HOME and DAG_HOME to point to the ZenML repo instead.
* Sets the `airflow_stack` to be the active stack, so essentially all pipelines will now be run on Airflow. So with just a few commands we transitioned to a production-ready setup!

{% hint style="warning" %}
In the real-world we would also switch to something like a MySQL-based metadata store and a Azure/GCP/S3-based artifact store. We have just skipped that part to keep everything in one machine to make it a bit easier to run this guide.
{% endhint %}




We now have a continuously training ML pipeline training on new data every day. All the pipelines will be tracked in your production [Stack's metadata store](../../core-concepts.md), the interim artifacts will be stored in the [Artifact Store](../../core-concepts.md), and the scheduling and orchestration is being handled by the [orchestrator](../../core-concepts.md), in this case Airflow.

# Conclusion

If you made it this far, congratulations! You're one step closer to being production-ready with your ML workflows!

## Coming soon

There are lot's more things you do in production that you might consider adding to your workflows:

* Adding a step to automatically deploy the models to a REST endpoint.
* Setting up a drift detection and validation step to test models before deploying.
* Creating a batch inference pipeline to get predictions.

ZenML will help with all of these and above -> Watch out for future releases and the next extension of this guide coming soon!