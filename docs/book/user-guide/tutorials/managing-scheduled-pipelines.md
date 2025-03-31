---
description: How to create, manage, and troubleshoot scheduled pipeline executions across different orchestrators
---

# Managing Pipeline Schedules in ZenML

## Introduction

This guide covers how to implement and manage scheduled pipeline executions in ZenML. You'll learn about the relationship between ZenML schedules and underlying orchestrator schedules, which orchestrators support scheduling, and how to effectively manage your pipeline schedules across different environments.

## 1. Understanding scheduling in ZenML

### 1.1 How scheduling works in ZenML

ZenML doesn't implement its own scheduler but acts as a wrapper around the scheduling capabilities of supported orchestrators. When you create a schedule:

```python
from zenml.config.schedule import Schedule
from zenml import pipeline
from datetime import datetime

@pipeline()
def my_pipeline():
    # Pipeline steps...

# Option 1: Using cron expressions (recommended for precise control)
schedule = Schedule(cron_expression="0 9 * * *")  # Run daily at 9 AM

# Option 2: Using interval-based scheduling
schedule = Schedule(
    start_time=datetime.now(), 
    interval_second=3600  # Run every hour
)

# Attach the schedule to your pipeline
my_pipeline = my_pipeline.with_options(schedule=schedule)
my_pipeline()  # Creates and registers the scheduled pipeline
```

When you execute this code, ZenML:
1. Translates your schedule definition to the orchestrator's native format
2. Registers the schedule with the orchestrator's scheduling system
3. Records the schedule in the ZenML metadata store

The orchestrator then takes over responsibility for executing the pipeline according to the schedule. You can view your schedules using the CLI:

```bash
zenml pipeline schedule list
```

**Important limitations to understand:**
- ZenML only initiates schedule creation; the orchestrator manages the actual execution
- Each time you run a pipeline with a schedule, a new schedule is created
- Schedule updates and deletion typically require interacting directly with the orchestrator
- Environment variables and context are captured at creation time

### 1.2 Orchestrator support for scheduling

The table below summarizes scheduling support across ZenML orchestrators:

| Orchestrator | Support | Key Features | Limitations |
|--------------|---------|--------------|------------|
| Airflow | ✅ | Complex cron expressions, catchup/backfill, comprehensive monitoring | Requires Airflow knowledge for management |
| AzureML | ✅ | Integration with Azure monitoring, authentication via service connectors | Limited schedule visibility in ZenML |
| Databricks | ✅ | Integration with Databricks workspace | Requires Databricks account access for management |
| HyperAI | ✅ | Simplified scheduling | Basic scheduling capabilities |
| Kubeflow | ✅ | Full cron support, UI management, catchup functionality | Schedules persist in Kubeflow even if deleted from ZenML |
| Kubernetes | ✅ | Uses Kubernetes CronJobs | Basic scheduling, requires Kubernetes knowledge |
| Local | ❌ | Not applicable | No scheduling support |
| Local Docker | ❌ | Not applicable | No scheduling support |
| SageMaker | ✅ | AWS integration, CloudWatch monitoring | AWS-specific authentication requirements |
| SkypilotVM | ❌ | Not applicable | No scheduling support |
| Tekton | ❌ | Not applicable | No scheduling support |
| Vertex AI | ✅ | GCP integration, detailed execution logs | Requires GCP console for detailed management |

**Choosing the right orchestrator for scheduling:**

- **For GCP users**: Vertex AI provides seamless integration with GCP services
- **For AWS users**: SageMaker offers native AWS ecosystem integration
- **For Azure users**: AzureML integrates well with Azure services 
- **For complex scheduling**: Airflow offers the most powerful scheduling capabilities
- **For Kubernetes environments**: Kubeflow or native Kubernetes orchestrator

Consider your monitoring needs, infrastructure, and team expertise when selecting an orchestrator. If you need to access schedule execution logs or make schedule adjustments, you'll typically need to interact directly with the orchestrator-specific interfaces rather than through ZenML.

## 2. Creating scheduled pipelines

### 2.1 Advanced Schedule Creation Options 

Building on the basic scheduling approach outlined in section 1, let's explore more advanced scheduling options and patterns you can use with ZenML:

#### Verifying and Managing Schedules with CLI

After creating a schedule, you can manage it using the CLI:

```bash
# List all schedules
zenml pipeline schedule list

# Delete a specific schedule
zenml pipeline schedule delete <SCHEDULE_NAME_OR_ID>
```

#### Advanced Scheduling Patterns

ZenML supports several powerful scheduling patterns through its Schedule class:

**1. Cron Expressions for Complex Schedules**

For advanced timing needs, cron expressions provide precise scheduling control:

```python
# Run at 3:30 AM on the first day of each month
Schedule(cron_expression="30 3 1 * *")

# Run at 2:15 PM on weekdays
Schedule(cron_expression="15 14 * * 1-5")

# Run every 6 hours
Schedule(cron_expression="0 */6 * * *")

# Run at 9 AM on Mondays and Wednesdays
Schedule(cron_expression="0 9 * * 1,3")
```

**2. Run-Once Scheduling**

For one-time future execution:

```python
from datetime import datetime, timedelta

# Run once at a specific time in the future
Schedule(run_once_start_time=datetime.now() + timedelta(days=1))
```

**3. Time-Limited Scheduling**

For schedules that should only run during a specific window:

```python
# Run every day at 9 AM, but only for the next 30 days
Schedule(
    cron_expression="0 9 * * *",
    start_time=datetime.now(),
    end_time=datetime.now() + timedelta(days=30)
)
```

**4. Controlled Backfilling with Catchup**

Control whether missed schedule intervals should be executed:

```python
# If schedule is paused and then resumed, this will execute all missed runs
Schedule(
    cron_expression="0 * * * *",  # Hourly
    catchup=True
)

# If schedule is paused and then resumed, this will only run on the next interval
Schedule(
    cron_expression="0 * * * *",
    catchup=False  # Skip any missed executions
)
```

#### Schedule Naming and Management Best Practices

1. **Use semantic naming**: Create descriptive names that indicate purpose, frequency and environment:
   ```python
   Schedule(
       name="daily-model-training-prod", 
       cron_expression="0 3 * * *"
   )
   ```

2. **Set explicit timezones**: For teams across different locations, use timezone-aware datetime objects:
   ```python
   import pytz
   
   # Run at 9 AM UTC, regardless of local timezone
   Schedule(
       start_time=datetime.now(pytz.UTC),
       interval_second=timedelta(days=1)
   )
   ```

3. **Document your schedules**: Maintain an inventory of schedules, especially in production environments.

4. **Test with shorter intervals**: Validate schedule behavior with brief intervals in development before deploying to production.

5. **Clean up unused schedules**: Regularly audit and remove unused schedules to prevent clutter and unexpected runs:
   ```bash
   # List all schedules to find unused ones
   zenml pipeline schedule list
   
   # Delete schedules you no longer need
   zenml pipeline schedule delete <SCHEDULE_NAME_OR_ID>
   ```

### 2.2 Orchestrator-specific schedule creation

Different orchestrators implement scheduling in their own way, and ZenML adapts your schedule configuration to match each orchestrator's capabilities. Here are orchestrator-specific considerations to be aware of:

#### 2.2.1 Kubeflow schedules

Kubeflow implements schedules as recurring runs. When you create a scheduled pipeline with Kubeflow:

```python
from zenml.integrations.kubeflow.flavors.kubeflow_orchestrator_flavor import (
    KubeflowOrchestratorSettings
)

# Optional: Configure additional Kubeflow-specific settings
kubeflow_settings = KubeflowOrchestratorSettings(
    user_namespace="my-namespace",  # Namespace to run the schedule in
)

@pipeline(settings={"orchestrator": kubeflow_settings})
def my_kubeflow_pipeline():
    # Pipeline steps...

# Create schedule as usual
schedule = Schedule(cron_expression="0 9 * * *")
scheduled_pipeline = my_kubeflow_pipeline.with_options(schedule=schedule)
scheduled_pipeline()
```

**Implementation details:**
- Kubeflow handles schedule creation through its recurring run API
- The schedule is visible in both ZenML and the Kubeflow UI
- Schedule deletion through ZenML doesn't always completely remove the schedule from Kubeflow

#### 2.2.2 Vertex AI schedules

Vertex AI has robust native scheduling support. When creating a scheduled pipeline with Vertex AI:

```python
from zenml.integrations.gcp.flavors.vertex_orchestrator_flavor import (
    VertexOrchestratorSettings
)

# Optional: Add Vertex-specific settings
vertex_settings = VertexOrchestratorSettings(
    labels={"environment": "production"}  # Custom labels for the job
)

@pipeline(settings={"orchestrator": vertex_settings})
def my_vertex_pipeline():
    # Pipeline steps...

# Create a schedule with start and end times
schedule = Schedule(
    cron_expression="0 9 * * *",
    start_time=datetime.now(),
    end_time=datetime.now() + timedelta(days=30)
)
scheduled_pipeline = my_vertex_pipeline.with_options(schedule=schedule)
scheduled_pipeline()
```

**Implementation details:**
- Vertex AI schedules are created using the Vertex AI SDK's PipelineJob.create_schedule() method
- Vertex AI supports start and end times for schedules
- Scheduled pipelines are visible in the Google Cloud Console
- The workload service account used by the Vertex orchestrator needs proper permissions

#### 2.2.3 Airflow schedules

Airflow has sophisticated scheduling capabilities but requires special attention when creating schedules:

```python
from zenml.integrations.airflow.flavors.airflow_orchestrator_flavor import (
    AirflowOrchestratorSettings
)

# Optional: Configure Airflow-specific settings
airflow_settings = AirflowOrchestratorSettings(
    operator="docker"  # Use DockerOperator
)

@pipeline(settings={"orchestrator": airflow_settings})
def my_airflow_pipeline():
    # Pipeline steps...

# Important: Start time for Airflow must be in the past
schedule = Schedule(
    start_time=datetime.now() - timedelta(hours=1),  # MUST be in the past
    interval_second=timedelta(minutes=30),
    catchup=False
)
scheduled_pipeline = my_airflow_pipeline.with_options(schedule=schedule)
scheduled_pipeline()
```

**Implementation details:**
- Airflow requires start times to be in the past
- Schedules are implemented as native Airflow DAG schedules
- The catchup parameter is particularly important for Airflow as it determines if missed runs should be executed
- For local Airflow deployments, the DAG file needs to be properly deployed to the Airflow DAGs folder

#### 2.2.4 Other orchestrators

ZenML supports scheduling on other orchestrators as well, each with their own specific implementation:

- **Kubernetes**: Uses Kubernetes CronJobs for scheduling
- **SageMaker**: Leverages AWS EventBridge for scheduling
- **Azure ML**: Uses the Azure ML SDK's scheduling capabilities
- **Databricks**: Utilizes Databricks Jobs scheduling

When using any of these orchestrators, the basic ZenML syntax for scheduling remains the same, but you should check the orchestrator's documentation for specific limitations or requirements.

```python
# The basic pattern works for all supported orchestrators
schedule = Schedule(cron_expression="0 9 * * *")
scheduled_pipeline = my_pipeline.with_options(schedule=schedule)
scheduled_pipeline()
```

For unsupported orchestrators (like Local and LocalDocker), attempting to create a schedule will result in an error.

## 3. Managing existing schedules

Once you've created pipeline schedules, ongoing management becomes crucial - especially in production environments. This section covers how to view, monitor, update, and delete your schedules across different orchestrators.

### 3.1 Viewing and monitoring schedules

#### Listing schedules with ZenML CLI

The primary way to view your schedules is through the ZenML CLI:

```bash
# List all schedules
zenml pipeline schedule list

# Filter schedules by pipeline name
zenml pipeline schedule list --pipeline_id my_pipeline_id
```

The CLI output shows basic information about each schedule, including:
- Schedule name
- Pipeline name
- Cron expression or interval
- Start time
- End time
- Catchup status

#### Checking schedule status and history

To monitor the execution history of your scheduled pipelines, you can:

1. View the pipeline runs associated with the schedule:

   ```bash
   # List pipeline runs, which will include scheduled runs
   zenml pipeline runs list --pipeline_name my_pipeline
   ```

2. Check the orchestrator's native UI for detailed execution information:
   - **Kubeflow**: Check the Kubeflow Pipelines UI under the Recurring Runs section
   - **Vertex AI**: Use the Google Cloud Console to view Pipeline execution history
   - **Airflow**: Check the Airflow UI for DAG run history

3. Set up monitoring for your scheduled pipeline runs:

   ```python
   from zenml.integrations.slack.alerters import SlackAlerter
   
   # Example: Set up a Slack alerter for run completion
   @pipeline(
      settings={
         "alerter": {
            "slack_alerter": SlackAlerter(
               webhook_url="https://hooks.slack.com/services/XXX/YYY/ZZZ",
               alert_on_success=True,
               alert_on_failure=True
            )
         }
      }
   )
   def my_scheduled_pipeline():
       # Pipeline steps
   ```

### 3.2 Updating schedules

#### The challenge with schedule updates

One important limitation of ZenML's scheduling system is that **schedules cannot be directly updated after creation**. This is because schedules are implemented at the orchestrator level, and each orchestrator has different capabilities for updating schedules.

The current recommended workflow for "updating" a schedule is:

1. Delete the existing schedule
2. Create a new schedule with the desired configuration

```python
# Delete the existing schedule
from zenml.client import Client
Client().delete_schedule("my-schedule")

# Create a new schedule with updated parameters
from zenml.config.schedule import Schedule
updated_schedule = Schedule(
    name="my-schedule",  # Use the same name for continuity
    cron_expression="0 9 * * *"  # Updated schedule parameters
)
my_pipeline = my_pipeline.with_options(schedule=updated_schedule)
my_pipeline()
```

#### Why direct orchestrator interaction is often needed

For more advanced schedule management, you'll often need to interact directly with the orchestrator:

1. **Schedule pausing**: ZenML doesn't provide a way to pause schedules - you need to use the orchestrator's native tools
2. **Complex updates**: Some orchestrators allow updating schedules without recreating them
3. **Schedule monitoring**: Detailed execution information is available in the orchestrator's UI

#### Update patterns for different orchestrators

**Kubeflow**:
```python
from kfp.client import Client as KFPClient

# Connect to Kubeflow
client = KFPClient(host="https://your-kubeflow-host")

# Get the recurring run ID (you'll need to query this based on name)
recurring_run_id = "your-recurring-run-id"

# Enable or disable the recurring run
client.recurring_runs.enable(recurring_run_id)
client.recurring_runs.disable(recurring_run_id)
```

**Vertex AI**:
```python
from google.cloud import aiplatform

# List schedules
vertex_schedules = aiplatform.PipelineJobSchedule.list(
    filter=f'display_name="your-schedule-name"',
    location="your-region"
)

# Pause/unpause schedule
if vertex_schedules:
    schedule = vertex_schedules[0]
    schedule.pause()  # or schedule.resume()
```

**Airflow**:
```bash
# Using the Airflow CLI
airflow dags pause your_dag_id
airflow dags unpause your_dag_id
```

### 3.3 Deleting schedules

#### ZenML schedule deletion

To delete a schedule using the ZenML CLI:

```bash
# List schedules to find the name or ID
zenml pipeline schedule list

# Delete a schedule by name or ID
zenml pipeline schedule delete your-schedule-name
```

Using the Python SDK:

```python
from zenml.client import Client

# Delete by name or ID
Client().delete_schedule("your-schedule-name")
```

#### Why orchestrator schedules may remain

When you delete a schedule through ZenML, the database record is removed, but the underlying orchestrator schedule might persist depending on the implementation. This is because:

1. Some orchestrators don't provide APIs for deleting schedules
2. ZenML prioritizes a unified interface over orchestrator-specific cleanup
3. Connection or permission issues may prevent orchestrator-level deletion

This can lead to "orphaned" schedules that continue to run in the orchestrator but are no longer tracked by ZenML.

#### Direct deletion from orchestrators

To ensure complete cleanup, you should delete schedules both from ZenML and directly from the orchestrator:

**Kubeflow**:
```python
from kfp.client import Client as KFPClient

# Connect to Kubeflow
client = KFPClient(host="https://your-kubeflow-host")

# List all recurring runs matching a name pattern
recurring_runs = client.list_recurring_runs(
    experiment_id="your-experiment-id",
    page_size=100
)

# Delete matching recurring runs
for run in recurring_runs:
    if run.name == "your-schedule-name":
        client.delete_recurring_run(run.id)
```

**Vertex AI**:
```python
from google.cloud import aiplatform

# List schedules
vertex_schedules = aiplatform.PipelineJobSchedule.list(
    filter=f'display_name="your-schedule-name"',
    location="your-region"
)

# Delete schedules
for schedule in vertex_schedules:
    schedule.delete()
```

**Airflow**:
You can delete the generated DAG file from the Airflow DAGs directory, or you may need to use the Airflow API to delete the DAG depending on your Airflow setup.

#### Complete cleanup process

For a thorough cleanup, follow these steps:

1. Delete the schedule from ZenML:
   ```bash
   zenml pipeline schedule delete your-schedule-name
   ```

2. Delete the schedule from the orchestrator using the appropriate method

3. Verify deletion by checking both ZenML and the orchestrator:
   ```bash
   # Check ZenML
   zenml pipeline schedule list
   
   # Check the orchestrator using its native tools
   ```

4. (Optional) Clean up any artifacts or logs associated with the scheduled runs

## 4. Direct interaction with orchestrator schedules

### 4.1 Vertex AI schedule management

- Using the Vertex AI SDK
- Listing Vertex schedules
- Updating schedule parameters
- Complete example for Vertex schedule management:

```python
from google.cloud import aiplatform
from zenml.client import Client

def manage_vertex_schedules():
    # Initialize clients
    zenml_client = Client()

    # List all ZenML schedules
    zenml_schedules = zenml_client.list_schedules()

    # Process each ZenML schedule
    for zenml_schedule in zenml_schedules:
        # Find the corresponding Vertex AI schedule
        vertex_filter = f'display_name="{zenml_schedule.name}"'
        vertex_schedules = aiplatform.PipelineJobSchedule.list(
            filter=vertex_filter,
            order_by='create_time desc',
            location="your-region"
        )

        # Work with the Vertex schedules
        if vertex_schedules:
            for vertex_schedule in vertex_schedules:
                # Perform operations (e.g., update or delete)
                print(f"Found Vertex schedule: {vertex_schedule.display_name}")

                # Example: Disable a schedule
                # vertex_schedule.delete()

```

### 4.2 Kubeflow schedule management

- Using the Kubeflow Pipelines SDK
- Listing Kubeflow schedules
- Updating and pausing schedules
- Complete example for Kubeflow schedule management

### 4.3 Airflow schedule management

- Using the Airflow API
- Managing DAGs and schedules
- Pausing and unpausing DAGs
- Complete example for Airflow schedule management

## 5. Cleaning up orphaned schedules

### 5.1 Identifying orphaned schedules

- Detecting disconnects between ZenML and orchestrator
- Audit strategies for schedule alignment
- Schedule naming conventions for easier tracking

### 5.2 Complete cleanup implementation

- Full implementation for Vertex AI cleanup:

```python
from google.cloud import aiplatform
from zenml.client import Client

def delete_all_schedules():
    # Initialize ZenML client
    zenml_client = Client()
    # Get all ZenML schedules
    zenml_schedules = zenml_client.list_schedules()

    if not zenml_schedules:
        print("No ZenML schedules to delete.")
        return

    print(f"\nFound {len(zenml_schedules)} ZenML schedules to process...\n")

    # Process each ZenML schedule
    for zenml_schedule in zenml_schedules:
        schedule_name = zenml_schedule.name
        print(f"Processing ZenML schedule: {schedule_name}")

        try:
            # First delete the corresponding Vertex AI schedule
            vertex_filter = f'display_name="{schedule_name}"'
            vertex_schedules = aiplatform.PipelineJobSchedule.list(
                filter=vertex_filter,
                order_by='create_time desc',
                location="your-region"
            )

            if vertex_schedules:
                print(f"  Found {len(vertex_schedules)} matching Vertex schedules")
                for vertex_schedule in vertex_schedules:
                    try:
                        vertex_schedule.delete()
                        print(f"  ✓ Deleted Vertex schedule: {vertex_schedule.display_name}")
                    except Exception as e:
                        print(f"  ✗ Failed to delete Vertex schedule {vertex_schedule.display_name}: {e}")
            else:
                print(f"  No matching Vertex schedules found for {schedule_name}")

            # Then delete the ZenML schedule
            zenml_client.delete_schedule(zenml_schedule.id)
            print(f"  ✓ Deleted ZenML schedule: {schedule_name}")

        except Exception as e:
            print(f"  ✗ Failed to process {schedule_name}: {e}")

    print("\nSchedule cleanup completed!")

```

- Equivalent implementations for other orchestrators
- Safety considerations when deleting schedules
- Backup strategies before cleanup

## 6. Schedule management best practices

### 6.1 Naming conventions

- Consistent naming for easier management
- Including environment information
- Version identifiers in schedule names
- Documentation practices

### 6.2 Schedule monitoring and alerting

- Setting up failure notifications
- Schedule execution logs
- Performance monitoring
- Cost tracking for scheduled runs

### 6.3 Managing schedule drift

- Why ZenML and orchestrator schedules might diverge
- Regular reconciliation processes
- Automated audit scripts
- Documentation and tracking

## 7. Alternatives to native scheduling

### 7.1 External schedulers

- Using cloud scheduler services (AWS EventBridge, Cloud Scheduler)
- Implementing cron jobs
- Container-based schedulers
- Implementation examples

### 7.2 CI/CD-based scheduling

- Using GitHub Actions for scheduling
- GitLab CI scheduled pipelines
- Jenkins scheduled jobs
- Complete implementation example

## 8. Troubleshooting schedule issues

### 8.1 Common schedule problems

- Missing or duplicate executions
- Authentication failures
- Resource constraints
- Configuration drift

### 8.2 Debugging strategies

- Log analysis techniques
- Schedule state verification
- ZenML vs orchestrator schedule comparison
- Reconciliation approaches

## Conclusion

- Summary of schedule management approaches
- Best practices recap
- Future improvements in ZenML scheduling
- Additional resources and references
