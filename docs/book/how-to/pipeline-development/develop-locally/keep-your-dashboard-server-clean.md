---
description: Learn how to keep your pipeline runs clean during development.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Keep your dashboard and server clean

When developing pipelines, it's common to run and debug them multiple times. To
avoid cluttering the server with these development runs, ZenML provides several
options:

## Run locally

One of the easiest ways to avoid cluttering a shared server / dashboard is to
disconnect your client from the remote server and simply spin up a local server:

```bash
zenml login --local
```

Note that there are some limitations to this approach, particularly if you want
to use remote infrastructure, but if there are local runs that you can do
without the need for remote infrastructure, this can be a quick and easy way to
keep things clean. When you're ready to reconnect to the server to continue with
your shared runs, you can simply run `zenml login <remote-url>` again.

## Pipeline Runs

### Unlisted Runs

Pipeline runs can be created without being explicitly associated with a pipeline by passing the `unlisted` parameter when running a pipeline:

```python
pipeline_instance.run(unlisted=True)
```

Unlisted runs are not displayed on the pipeline's page in the dashboard (though
they *are* displayed in the pipeline run section), keeping the pipeline's
history clean and focused on the pipelines that matter most.

### Deleting Pipeline Runs

If you want to delete a specific pipeline run, you can use a script like this:

```bash
zenml pipeline runs delete <PIPELINE_RUN_NAME_OR_ID>
```

If you want to delete all pipeline runs in the last 24 hours, for example, you
could run a script like this:

```
#!/usr/bin/env python3

import datetime
from zenml.client import Client

def delete_recent_pipeline_runs():
    # Initialize ZenML client
    zc = Client()
    
    # Calculate the timestamp for 24 hours ago
    twenty_four_hours_ago = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
    
    # Format the timestamp as required by ZenML
    time_filter = twenty_four_hours_ago.strftime("%Y-%m-%d %H:%M:%S")
    
    # Get the list of pipeline runs created in the last 24 hours
    recent_runs = zc.list_pipeline_runs(created=f"gt:{time_filter}")
    
    # Delete each run
    for run in recent_runs:
        print(f"Deleting run: {run.id} (Created: {run.body.created})")
        zc.delete_pipeline_run(run.id)
    
    print(f"Deleted {len(recent_runs)} pipeline runs.")

if __name__ == "__main__":
    delete_recent_pipeline_runs()
```

For different time ranges you can update this as appropriate.

## Pipelines

### Deleting Pipelines

Pipelines that are no longer needed can be deleted using the command:

```bash
zenml pipeline delete <PIPELINE_ID_OR_NAME>
```

This allows you to start fresh with a new pipeline, removing all previous runs
associated with the deleted pipeline. This is a slightly more drastic approach,
but it can sometimes be useful to keep the development environment clean.

## Unique Pipeline Names

Pipelines can be given unique names each time they are run to uniquely identify them. This helps differentiate between multiple iterations of the same pipeline during development.

By default ZenML generates names automatically based on the current date and
time, but you can pass in a `run_name` when defining the pipeline:

```python
training_pipeline = training_pipeline.with_options(
    run_name="custom_pipeline_run_name"
)
training_pipeline()
```

Note that pipeline names must be unique. For more information on this feature,
see the [documentation on naming pipeline runs](../../pipeline-development/build-pipelines/name-your-pipeline-and-runs.md).

## Models

Models are something that you have to explicitly register or pass in as you
define your pipeline, so to run a pipeline without it being attached to a model
is fairly straightforward: simply don't do the things specified in our
[documentation on registering
models](../../model-management-metrics/model-control-plane/register-a-model.md).

In order to delete a model or a specific model version, you can use the CLI or
Python SDK to accomplish this. As an example, to delete all versions of a model,
you can use:

```bash
zenml model delete <MODEL_NAME>
```

See the full documentation on [how to delete models](../../model-management-metrics/model-control-plane/delete-a-model.md).

## Artifacts

### Pruning artifacts

If you want to delete artifacts that are no longer referenced by any pipeline
runs, you can use the following CLI command:

```bash
zenml artifact prune
```

By default, this method deletes artifacts physically from the underlying artifact store AND also the entry in the database. You can control this behavior by using the `--only-artifact` and `--only-metadata` flags.

For more information, see the [documentation for this artifact pruning feature](../../data-artifact-management/handle-data-artifacts/delete-an-artifact.md).

## Cleaning your environment

As a more drastic measure, the `zenml clean` command can be used to start from
scratch on your local machine. This will:

- delete all pipelines, pipeline runs and associated metadata
- delete all artifacts

There is also a `--local` flag that you can set if you want to delete local
files relating to the active stack. Note that `zenml clean` does not delete
artifacts and pipelines on the server; it only deletes the local data and metadata.

By utilizing these options, you can maintain a clean and organized pipeline
dashboard, focusing on the runs that matter most for your project.
<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


