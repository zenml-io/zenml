---
description: A step-by-step tutorial on how to create, update, and delete scheduled pipelines in ZenML
---

# Managing Scheduled Pipelines in ZenML: A Cookbook

This cookbook demonstrates how to work with scheduled pipelines in ZenML through a practical example. We'll create a simple data processing pipeline that runs on a schedule, update its configuration, and finally clean up by deleting the schedule.

## How Scheduling Works in ZenML

ZenML doesn't implement its own scheduler but acts as a wrapper around the scheduling capabilities of supported orchestrators like Vertex AI, Airflow, Kubeflow, and others. When you create a schedule, ZenML:

1. Translates your schedule definition to the orchestrator's native format
2. Registers the schedule with the orchestrator's scheduling system
3. Records the schedule in the ZenML metadata store

The orchestrator then takes over responsibility for executing the pipeline according to the schedule.

## Prerequisites

Before starting this tutorial, make sure you have:

1. ZenML installed and configured
2. A supported orchestrator (we'll use Vertex AI in this example)
3. Basic understanding of ZenML pipelines and steps

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

### Best Practice: Use Descriptive Schedule Names

When creating schedules, follow a consistent naming pattern to better organize them:

```python
# Example of a well-named schedule
schedule = Schedule(
    name="daily-feature-engineering-prod-v1",
    cron_expression="0 4 * * *"
)
```

Include the frequency, purpose, environment, and version in your schedule names.

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

# Get details of a specific schedule
zenml pipeline schedule get daily-data-processing
```

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

For critical pipelines, add alerting to notify you of failures:

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

This assumes you've registered an alerter (like Slack or Discord) in your active stack.

## Step 6: Clean Up

Finally, let's clean up by deleting our schedule:

```python
# Delete the schedule
client.delete_schedule("daily-data-processing")

# Verify deletion
schedules = client.list_schedules()
if not any(s.name == "daily-data-processing" for s in schedules):
    print("Schedule deleted successfully!")
else:
    print("Schedule still exists!")
```

## Advanced Scheduling Patterns

ZenML supports several powerful scheduling patterns:

### Running at Specific Times

```python
# Run at 3:30 AM on the first day of each month
Schedule(cron_expression="30 3 1 * *")

# Run at 2:15 PM on weekdays
Schedule(cron_expression="15 14 * * 1-5")

# Run every 6 hours
Schedule(cron_expression="0 */6 * * *")
```

### Time-Limited Scheduling

```python
# Run every day at 9 AM, but only for the next 30 days
Schedule(
    cron_expression="0 9 * * *",
    start_time=datetime.now(),
    end_time=datetime.now() + timedelta(days=30)
)
```

### Run-Once Scheduling 

```python
# Run once at a specific time in the future
Schedule(run_once_start_time=datetime.now() + timedelta(days=1))
```

## Common Issues and Solutions

While working with scheduled pipelines, you might encounter these common issues:

1. **Schedule not running at expected time**
   - Check if the cron expression is correct
   - Verify the orchestrator's timezone settings
   - Ensure the orchestrator service is running

2. **Authentication errors**
   - Verify your orchestrator credentials
   - Check service account permissions
   - Ensure API keys are valid

3. **Resource constraints**
   - Monitor orchestrator resource usage
   - Check for quota limits
   - Verify resource allocation

4. **Orphaned schedules**
   - Schedules might remain in the orchestrator when deleted from ZenML
   - Clean up schedules from both ZenML and the orchestrator directly

## Next Steps

Now that you understand the basics of managing scheduled pipelines, you can:

1. Create more complex schedules using different cron expressions
2. Set up monitoring and alerting for your scheduled pipelines
3. Implement error handling and retry logic
4. Add parameters to your scheduled pipelines

For more information, check out the [ZenML documentation](https://docs.zenml.io) and your orchestrator's specific documentation.
