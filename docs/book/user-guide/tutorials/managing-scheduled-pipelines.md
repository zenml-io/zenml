---
description: A step-by-step tutorial on how to create, update, and delete scheduled pipelines in ZenML
---

# Managing Scheduled Pipelines in ZenML

This tutorial demonstrates how to work with scheduled pipelines in ZenML through a practical example. We'll create a simple data processing pipeline that runs on a schedule, update its configuration, and finally clean up by deleting the schedule.

## How Scheduling Works in ZenML

ZenML doesn't implement its own scheduler but acts as a wrapper around the scheduling capabilities of supported orchestrators like Vertex AI, Airflow, Kubeflow, and others. When you create a schedule, ZenML:

1. Translates your schedule definition to the orchestrator's native format
2. Registers the schedule with the orchestrator's scheduling system
3. Records the schedule in the ZenML metadata store

The orchestrator then takes over responsibility for executing the pipeline
according to the schedule.

{% hint style="info" %}
For our full reference documentation on schedules, see the [Schedule a Pipeline](https://docs.zenml.io/how-to/pipeline-development/build-pipelines/schedule-a-pipeline) page.
{% endhint %}

## Prerequisites

Before starting this tutorial, make sure you have:

1. ZenML installed and configured
2. A supported orchestrator (we'll use [Vertex AI](https://docs.zenml.io/stacks/orchestrators/vertex) in this example)
3. Basic understanding of [ZenML pipelines and steps](https://docs.zenml.io/getting-started/core-concepts)

## Step 1: Create a Simple Pipeline

First, let's create a basic pipeline that we'll schedule. This pipeline will simulate a daily data processing task.

```python
from zenml import pipeline, step
from datetime import datetime

@step
def process_data() -> str:
    """Simulate data processing step."""
    return f"Processed data at {datetime.now()}"

@step
def save_results(data: str) -> None:
    """Save processed results."""
    print(f"Saving results: {data}")

@pipeline
def daily_data_pipeline():
    """A simple pipeline that processes data daily."""
    data = process_data()
    save_results(data)
```

## Step 2: Create a Schedule

Now, let's create a schedule for our pipeline. We'll set it to run daily at 9 AM.

```python
from zenml.config.schedule import Schedule
from datetime import datetime

# Create a schedule that runs daily at 9 AM
schedule = Schedule(
    name="daily-data-processing",
    cron_expression="0 9 * * *"  # Run at 9 AM every day
)

# Attach the schedule to our pipeline
scheduled_pipeline = daily_data_pipeline.with_options(schedule=schedule)

# Run the pipeline to create the schedule
scheduled_pipeline()
```

Running the pipeline will create the schedule in the ZenML metadata store. as
well as the scheduled run in the orchestrator.

{% hint style="info" %}
**Best Practice: Use Descriptive Schedule Names**

When creating schedules, follow a consistent naming pattern to better organize them:

```python
# Example of a well-named schedule
schedule = Schedule(
    name="daily-feature-engineering-prod-v1",
    cron_expression="0 4 * * *"
)
```

Include the frequency, purpose, environment, and version in your schedule names.
{% endhint %}

## Step 3: Verify the Schedule

Let's check if our schedule was created successfully using both Python and the CLI:

```python
from zenml.client import Client

# Get the client
client = Client()

# List all schedules
schedules = client.list_schedules()

# Find our schedule
our_schedule = next(
    (s for s in schedules if s.name == "daily-data-processing"),
    None
)

if our_schedule:
    print(f"Schedule '{our_schedule.name}' created successfully!")
    print(f"Cron expression: {our_schedule.cron_expression}")
    print(f"Pipeline: {our_schedule.pipeline_name}")
else:
    print("Schedule not found!")
```

Using the CLI to verify:

```bash
# List all schedules
zenml pipeline schedule list

# Filter schedules by pipeline name
zenml pipeline schedule list --pipeline_id my_pipeline_id
```

Here's an example of what the CLI output might look like:

```shell
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━┯━━━━━━━━━━━━━━━━━┯━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━┓
┃              ID               │ NAME                          │ ACTIVE │ CRON_EXPRESSION │ START_TIME          │ END_TIME │ INTERVAL_SECOND │ CATCHUP │ RUN_ONCE_START_TIME ┃
┠───────────────────────────────┼───────────────────────────────┼────────┼─────────────────┼─────────────────────┼──────────┼─────────────────┼─────────┼─────────────────────┨
┃ 12345678-9abc-def0-1234-5678 │ daily-data-processing-2024_0  │ True   │ 0 9 * * *       │ None                │ None     │ None            │ False   │ None                ┃
┃            9abcdef0            │ 3_01-09_00_00_000000          │        │                 │                     │          │                 │         │                     ┃
┠───────────────────────────────┼───────────────────────────────┼────────┼─────────────────┼─────────────────────┼──────────┼─────────────────┼─────────┼─────────────────────┨
┃ 23456789-0abc-def1-2345-6789 │ hourly-data-sync-2024_03_01-  │ True   │ 0 * * * *       │ None                │ None     │ None            │ False   │ None                ┃
┃            0abcdef1            │ 10_00_00_000000               │        │                 │                     │          │                 │         │                     ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━┷━━━━━━━━━━━━━━━━━┷━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━┛
Page `(1/1)`, `2` items found for the applied filters.
```

## Step 3.1: Verify Schedule on GCP

To ensure the schedule was properly created in Vertex AI, we can verify it using the Google Cloud SDK:

```python
from google.cloud import aiplatform

# List all Vertex schedules
vertex_schedules = aiplatform.PipelineJobSchedule.list(
    filter=f'display_name="{schedule.name}"',
    location="us-central1"  # Replace with your Vertex AI region
)

our_vertex_schedule = next(
    (s for s in vertex_schedules if s.display_name == schedule_name), None
)

if our_vertex_schedule:
    print(
        f"Vertex AI schedule '{our_vertex_schedule.display_name}' created successfully!"
    )
    print(f"State: {our_vertex_schedule.state}")
    print(f"Cron expression: {our_vertex_schedule.cron}")
    print(
        f"Max concurrent run count: {our_vertex_schedule.max_concurrent_run_count}"
    )
else:
    print("Schedule not found in Vertex AI!")
```

{% hint style="warning" %}
Make sure to replace `us-central1` with your actual Vertex AI region. You can find your region in the Vertex AI settings or by checking the `location` parameter in your Vertex orchestrator configuration.
{% endhint %}

## Step 4: Update the Schedule

Sometimes we need to modify an existing schedule. Since ZenML doesn't support direct schedule updates, we'll need to delete the old schedule and create a new one.

```python
# First, delete the existing schedule
client.delete_schedule("daily-data-processing")

# Create a new schedule with updated parameters
new_schedule = Schedule(
    name="daily-data-processing",
    cron_expression="0 10 * * *"  # Changed to 10 AM
)

# Attach the new schedule to our pipeline
updated_pipeline = daily_data_pipeline.with_options(schedule=new_schedule)

# Run the pipeline to create the new schedule
updated_pipeline()
```

Using the CLI to delete a schedule:

```bash
# Delete a specific schedule
zenml pipeline schedule delete daily-data-processing

# rerun the pipeline to create the new schedule
python run.py # or whatever you named your script
```

> **Important**: When updating schedules, you should also delete the
> corresponding schedule in your orchestrator (Vertex AI in this example). You
> can do this through the Google Cloud Console or using the orchestrator's API
> (see below for code example).
> ZenML's delete command may not always completely remove the underlying
> orchestrator schedule.

## Step 4.1: Delete Schedule on GCP

To delete the schedule from Vertex AI, we can use the Google Cloud SDK:

```python
from google.cloud import aiplatform

# List all Vertex schedules
vertex_schedules = aiplatform.PipelineJobSchedule.list(
    filter=f'display_name="{schedule.name}"',
    location="us-central1"  # Replace with your Vertex AI region
)

# Find the schedule to delete
schedule_to_delete = next(
    (s for s in vertex_schedules if s.display_name == schedule.name), None
)

if schedule_to_delete:
    schedule_to_delete.delete()
    print(f"Schedule '{schedule.name}' deleted successfully from Vertex AI!")
else:
    print("Schedule not found in Vertex AI!")
```


## Step 5: Monitor Schedule Execution

Let's check the execution history of our scheduled pipeline:

```python
# Get recent pipeline runs
runs = client.list_pipeline_runs(
    pipeline_name_or_id="daily_data_pipeline",
    sort_by="created",
    descending=True,
    size=5
)

print("Recent pipeline runs:")
for run in runs.items:
    print(f"Run ID: {run.id}")
    print(f"Created at: {run.creation_time}")
    print(f"Status: {run.status}")
    print("---")
```

### Monitoring with Alerters

For critical pipelines, [add alerting](https://docs.zenml.io/stacks/alerters) to notify you of failures:

```python
from zenml.hooks import alerter_failure_hook
from zenml import pipeline, step

# Add failure alerting to critical steps
@step(on_failure=alerter_failure_hook)
def critical_step():
    # Step logic here
    pass

@pipeline()
def monitored_pipeline():
    critical_step()
    # Other steps
```

This assumes you've [registered an alerter](https://docs.zenml.io/stacks/alerters) (like Slack or Discord) in your active stack.

## Step 6: Clean Up

Finally, let's clean up by deleting our schedule:

```python
client.delete_schedule("daily-data-processing")

# Verify deletion
schedules = client.list_schedules()
if not any(s.name == "daily-data-processing" for s in schedules):
    print("Schedule deleted successfully from ZenML!")
else:
    print("Schedule still exists in ZenML!")
```
