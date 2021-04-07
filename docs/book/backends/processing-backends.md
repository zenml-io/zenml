# Processing Backends

Some pipelines just need more - processing power, parallelism, permissions, you name it.

A common scenario on large datasets is distributed processing, e.g. via Apache Beam, Google Dataflow, Apache Spark, or other frameworks. In line with our integration-driven design philosophy, ZenML makes it easy to to distribute certain `Steps` in a pipeline \(e.g. in cases where large datasets are involved\). All `Steps` within a pipeline take as input a `ProcessingBackend`.

## Overview

The pattern to add a backend to a step is always the same:

```python
backend = ...  # define the backend you want to use
pipeline.add_step(
    Step(...).with_backend(backend)
)
```

## Supported Processing Backends

ZenML is built on Apache Beam. You can simple use the `ProcessingBaseBackend`, or extend ZenML with your own, custom backend.+

For convenience, ZenML supports a steadily growing number of processing backends out of the box:

### Google Dataflow

ZenML natively supports [Google Cloud Dataflow](https://cloud.google.com/dataflow) out of the box \(as it's built on Apache Beam\).

**Prequisites:**

* [Enable billing](https://cloud.google.com/billing/docs/how-to/modify-project#enable_billing_for_a_project) in your Google Cloud Platform project.
* [Make sure you have permissions](https://cloud.google.com/dataflow/docs/concepts/access-control) to launch dataflow jobs, whether through service account or default credentials.

**Usage:**

```python
# Define the processing backend
processing_backend = ProcessingDataFlowBackend(
    project=GCP_PROJECT,
    staging_location=os.path.join(GCP_BUCKET, 'dataflow_processing/staging'),
)

# Reference the processing backend in steps
# Add a split
training_pipeline.add_split(
    RandomSplit(...).with_backend(
        processing_backend)
)

# Add a preprocessing unit
training_pipeline.add_preprocesser(
    StandardPreprocesser(...).with_backend(processing_backend)
)
```

