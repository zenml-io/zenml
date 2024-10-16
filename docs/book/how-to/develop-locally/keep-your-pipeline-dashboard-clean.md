---
description: Learn how to keep your pipeline runs clean during development.
---

# Keep your pipelines and dashboard clean

When developing pipelines, it's common to run and debug them multiple times. To avoid cluttering the server with these development runs, ZenML provides several options:

## Unlisted Runs

Pipeline runs can be created without being explicitly associated with a pipeline by passing the `unlisted` parameter when running a pipeline:

```python
pipeline_instance.run(unlisted=True)
```

Unlisted runs are not displayed on the pipeline's page in the dashboard, keeping the pipeline's history clean and focused on important runs.

## Deleting Pipelines

Pipelines can be deleted and recreated using the command:

```bash
zenml pipeline delete <PIPELINE_ID_OR_NAME>
```

This allows you to start fresh with a new pipeline, removing all previous runs
associated with the deleted pipeline. This is a slightly more drastic approach,
but it can sometimes be useful to keep the development environment clean.

## Unique Pipeline Names

Pipelines can be given unique names each time they are run to uniquely identify them. This helps differentiate between multiple iterations of the same pipeline during development.

By utilizing these options, you can maintain a clean and organized pipeline dashboard, focusing on the runs that matter most for your project.
