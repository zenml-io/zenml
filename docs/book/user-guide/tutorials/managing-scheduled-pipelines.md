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

![Output of `zenml pipeline schedule list`](../../.gitbook/assets/pipeline-schedules-list.png)

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
> ZenML's delete command never removes the underlying
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

> **Important**: You should also delete the schedule from the Vertex AI orchestrator to fully stop the scheduled runs. Here's how to delete Vertex AI schedules:

```python
from google.cloud import aiplatform

vertex_schedules = aiplatform.PipelineJobSchedule.list(
    filter='display_name="daily-data-processing"',
    location="us-central1" # insert your location here
)

# Delete matching schedules
for schedule in vertex_schedules:
    print(f"Deleting Vertex schedule: {schedule.display_name}")
    schedule.delete()
```

## Troubleshooting: Quick Fixes for Common Issues

Here are some practical fixes for issues you might encounter with your scheduled pipelines:

### Issue: Timezone Confusion with Scheduled Runs

A common issue with scheduled pipelines is timezone confusion. Here's how ZenML handles timezone information:

1. **If you provide a timezone-aware datetime**, ZenML will use it as is
2. **If you provide a datetime without timezone information**, ZenML assumes it's in your local timezone and converts it to UTC for storage and communication with orchestrators

For cloud orchestrators like Vertex AI, Kubeflow, and Airflow, schedules typically run in the orchestrator's timezone, which is usually UTC. This can lead to confusion if you expect a schedule to run at 9 AM in your local timezone but it runs at 9 AM UTC instead.

To ensure your schedule runs at the expected time:

```python
from datetime import datetime, timezone
import pytz
from zenml.config.schedule import Schedule

# Option 1: Explicitly use your local timezone (recommended)
local_tz = pytz.timezone('America/Los_Angeles')  # Replace with your timezone
local_time = local_tz.localize(datetime(2025, 1, 1, 9, 0))  # 9 AM in your timezone
schedule = Schedule(
    name="local-time-schedule",
    cron_expression="0 9 * * *",
    start_time=local_time  # ZenML will convert to UTC internally
)

# Option 2: Use UTC explicitly for clarity
utc_time = datetime(2025, 1, 1, 17, 0, tzinfo=timezone.utc)  # 5 PM UTC = 9 AM PST
schedule = Schedule(
    name="utc-time-schedule",
    cron_expression="0 17 * * *",  # Using UTC time in cron expression
    start_time=utc_time
)

# To verify how ZenML interprets your times:
from zenml.utils.time_utils import to_utc_timezone, to_local_tz
print(f"Schedule will start at: {schedule.start_time} (as stored by ZenML)")
print(f"In UTC that's: {to_utc_timezone(schedule.start_time)}")
print(f"In your local time that's: {to_local_tz(schedule.start_time)}")
```

Remember that cron expressions themselves don't have timezone information - they're interpreted in the timezone of the system executing them (which for cloud orchestrators is usually UTC).

### Issue: Schedule Doesn't Run at the Expected Time

If your pipeline doesn't run when scheduled:

```python
# Verify the cron expression with the croniter library
import datetime
from croniter import croniter

# Check if expression is valid
cron_expression = "0 9 * * *"
is_valid = croniter.is_valid(cron_expression)
print(f"Is cron expression valid? {is_valid}")

# Calculate the next run times to verify
base = datetime.datetime.now()
iter = croniter(cron_expression, base)
next_runs = [iter.get_next(datetime.datetime) for _ in range(3)]
print("Next 3 scheduled runs:")
for run_time in next_runs:
    print(f"  {run_time}")
```

For Vertex AI specifically, verify that your service account has the required permissions:
```bash
# Check permissions on your service account
gcloud projects get-iam-policy your-project-id \
  --filter="bindings.members:serviceAccount:your-service-account@your-project-id.iam.gserviceaccount.com"
```

### Issue: Orphaned Schedules in the Orchestrator

To clean up orphaned Vertex AI schedules:

```python
from google.cloud import aiplatform

# List all Vertex schedules
vertex_schedules = aiplatform.PipelineJobSchedule.list(
    filter='display_name="daily-data-processing"',
    location="us-central1" # insert your location here
)

# Delete orphaned schedules
for schedule in vertex_schedules:
    print(f"Deleting Vertex schedule: {schedule.display_name}")
    schedule.delete()
```

### Issue: Finding Failing Scheduled Runs

When scheduled runs fail silently:

```python
# Find failed runs in the last 24 hours
from zenml.client import Client
import datetime

client = Client()
yesterday = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)

# Get recent runs with status filtering
failed_runs = client.list_pipeline_runs(
    pipeline_name_or_id="daily_data_pipeline",
    sort_by="created",
    descending=True,
    size=10
)

# Print failed runs
print("Recent failed runs:")
for run in failed_runs.items:
    if run.status == "failed" and run.creation_time > yesterday:
        print(f"Run ID: {run.id}")
        print(f"Created at: {run.creation_time}")
        print(f"Status: {run.status}")
        print("---")
```

## Next Steps

Now that you understand the basics of managing scheduled pipelines, you can:

1. Create more complex schedules with various cron expressions for different business needs
2. Set up [monitoring and alerting](https://docs.zenml.io/stacks/alerters) to be notified when scheduled runs fail
3. Optimize resource allocation for your scheduled pipelines
4. Implement data-dependent scheduling where [pipelines trigger](https://docs.zenml.io/how-to/trigger-pipelines) based on data availability

For more advanced schedule management and monitoring techniques, check out the
[ZenML documentation](https://docs.zenml.io).
