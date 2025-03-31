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
| Airflow | ✅ | Complex cron expressions, catchup/backfill, comprehensive monitoring | Requires Airflow DAG modifications for schedule changes |
| AzureML | ✅ | Integration with Azure monitoring, authentication via service connectors | Limited schedule visibility in ZenML |
| Databricks | ✅ | Integration with Databricks workspace | Basic scheduling capabilities only |
| HyperAI | ✅ | Simplified scheduling | Limited frequency control options |
| Kubeflow | ✅ | Full cron support, UI management, catchup functionality | Only supports cron expressions (no interval-based scheduling); schedules persist in Kubeflow even if deleted from ZenML |
| Kubernetes | ✅ | Uses Kubernetes CronJobs | Only supports cron expressions; no built-in pause/resume functionality |
| Local | ❌ | Not applicable | No scheduling support at all |
| Local Docker | ❌ | Not applicable | No scheduling support at all |
| SageMaker | ✅ | AWS integration, CloudWatch monitoring | Requires AWS console for detailed management |
| SkypilotVM | ❌ | Not applicable | No scheduling support at all |
| Tekton | ❌ | Not applicable | No scheduling support at all |
| Vertex AI | ✅ | GCP integration, detailed execution logs | No explicit pause/resume functionality in ZenML |

**Note:** ZenML doesn't currently support updating or deleting orchestrator schedules directly through its API - these operations typically require interacting with the orchestrator's native tools. See section 3 for details on managing existing schedules.

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

### 3.4 Orchestrator-specific management

For more advanced schedule management, you'll need to interact directly with each orchestrator's native API. This section provides detailed examples for the most common orchestrators.

#### 3.4.1 Vertex AI schedule management

Vertex AI provides powerful APIs for managing pipeline schedules:

```python
from google.cloud import aiplatform
from zenml.client import Client

def manage_vertex_schedules():
    """Comprehensive Vertex AI schedule management."""
    # Initialize clients
    zenml_client = Client()
    aiplatform.init(project="your-project-id", location="your-region")
    
    # List all ZenML schedules
    zenml_schedules = zenml_client.list_schedules()
    
    # Process each ZenML schedule
    for zenml_schedule in zenml_schedules:
        # Find the corresponding Vertex AI schedule
        vertex_filter = f'display_name="{zenml_schedule.name}"'
        vertex_schedules = aiplatform.PipelineJobSchedule.list(
            filter=vertex_filter,
            order_by='create_time desc'
        )
        
        # Work with the Vertex schedules
        if vertex_schedules:
            for vertex_schedule in vertex_schedules:
                print(f"Found Vertex schedule: {vertex_schedule.display_name}")
                
                # Example operations:
                
                # 1. Pause a schedule
                # vertex_schedule.pause()
                
                # 2. Resume a paused schedule
                # vertex_schedule.resume()
                
                # 3. Get schedule details
                print(f"  Schedule ID: {vertex_schedule.name}")
                print(f"  Cron: {vertex_schedule.cron}")
                print(f"  State: {vertex_schedule.state}")
                
                # 4. Get execution history
                executions = vertex_schedule.list_executions()
                print(f"  Total executions: {len(executions)}")
```

The Vertex AI PipelineJobSchedule API provides these key capabilities:
- Pausing and resuming schedules
- Querying execution history
- Retrieving detailed status information
- Modifying schedule parameters (though recreation is safer)

#### 3.4.2 Kubeflow schedule management

Kubeflow Pipelines requires the KFP SDK for schedule management:

```python
from kfp.client import Client as KFPClient

def manage_kubeflow_schedules(host="https://your-kubeflow-host", namespace="kubeflow"):
    """Comprehensive Kubeflow schedule management."""
    # Connect to Kubeflow
    client = KFPClient(host=host)
    
    # List all experiments
    experiments = client.list_experiments(namespace=namespace)
    
    for experiment in experiments.experiments:
        print(f"Checking experiment: {experiment.name}")
        
        # List recurring runs for this experiment
        recurring_runs = client.list_recurring_runs(
            experiment_id=experiment.id,
            page_size=100
        )
        
        for run in recurring_runs.recurring_runs:
            print(f"  Found recurring run: {run.name}")
            
            # Example operations:
            
            # 1. Enable a recurring run
            # client.recurring_runs.enable(run.id)
            
            # 2. Disable a recurring run
            # client.recurring_runs.disable(run.id)
            
            # 3. Get recurring run details
            print(f"    Status: {run.status}")
            print(f"    Cron: {run.cron_schedule}")
            
            # 4. List run history
            run_history = client.list_runs(
                experiment_id=experiment.id,
                filter=f'pipeline_id="{run.pipeline_id}"'
            )
            print(f"    Total runs: {len(run_history.runs)}")
```

Kubeflow provides these management capabilities:
- Enabling and disabling recurring runs
- Viewing run history 
- Accessing detailed status information
- Managing experiment-level grouping

#### 3.4.3 Airflow schedule management

Airflow offers several interfaces for schedule management:

**Using the Airflow CLI:**
```bash
# Pause a DAG
airflow dags pause your_dag_id

# Unpause a DAG
airflow dags unpause your_dag_id

# List all DAGs
airflow dags list

# Trigger a DAG run manually
airflow dags trigger your_dag_id
```

**Using the Airflow REST API:**
```python
import requests
import json
import base64

def manage_airflow_schedules(airflow_host="http://localhost:8080"):
    """Comprehensive Airflow schedule management via REST API."""
    # Authentication (replace with your actual auth method)
    username = "admin"
    password = "admin"
    auth_header = {
        'Authorization': f'Basic {base64.b64encode(f"{username}:{password}".encode()).decode()}'
    }
    
    # List all DAGs
    response = requests.get(
        f"{airflow_host}/api/v1/dags",
        headers=auth_header
    )
    dags = json.loads(response.text)["dags"]
    
    for dag in dags:
        print(f"Found DAG: {dag['dag_id']}")
        
        # Example operations:
        
        # 1. Check if DAG is paused
        is_paused = dag["is_paused"]
        print(f"  Is paused: {is_paused}")
        
        # 2. Pause a DAG
        if not is_paused:
            # requests.patch(
            #     f"{airflow_host}/api/v1/dags/{dag['dag_id']}",
            #     json={"is_paused": True},
            #     headers=auth_header
            # )
            pass
        
        # 3. Get DAG runs
        runs_response = requests.get(
            f"{airflow_host}/api/v1/dags/{dag['dag_id']}/dagRuns",
            headers=auth_header
        )
        runs = json.loads(runs_response.text)["dag_runs"]
        print(f"  Total runs: {len(runs)}")
```

Airflow provides these schedule management capabilities:
- Pausing and unpausing DAGs
- Viewing execution history
- Triggering manual runs
- Detailed logging and monitoring

### 3.5 Cleaning up orphaned schedules

One common challenge with ZenML's orchestrator-agnostic scheduling is the potential for "orphaned" schedules - schedules that exist in the orchestrator but are no longer tracked by ZenML. This section covers how to identify and clean up these orphaned schedules.

#### 3.5.1 Identifying orphaned schedules

An orphaned schedule can occur when:
- A ZenML schedule is deleted but the orchestrator schedule remains
- A failure occurs during schedule creation, leaving the orchestrator schedule but no ZenML record
- ZenML database migration or restoration is performed without orchestrator synchronization

To identify orphaned schedules:

1. **List all ZenML schedules**:
   ```python
   from zenml.client import Client
   zenml_schedules = Client().list_schedules()
   zenml_schedule_names = [s.name for s in zenml_schedules]
   ```

2. **List all orchestrator schedules** (example for Vertex AI):
   ```python
   from google.cloud import aiplatform
   
   vertex_schedules = aiplatform.PipelineJobSchedule.list(location="your-region")
   vertex_schedule_names = [s.display_name for s in vertex_schedules]
   ```

3. **Find orphaned schedules**:
   ```python
   # Schedules that exist in the orchestrator but not in ZenML
   orphaned_schedules = [name for name in vertex_schedule_names 
                         if name not in zenml_schedule_names]
   print(f"Found {len(orphaned_schedules)} orphaned schedules")
   ```

#### 3.5.2 Complete cleanup implementation

Here's a complete implementation for finding and cleaning up orphaned schedules in Vertex AI:

```python
from google.cloud import aiplatform
from zenml.client import Client

def cleanup_all_schedules(delete_zenml=True, delete_vertex=True, location="your-region"):
    """Comprehensive schedule cleanup for both ZenML and Vertex AI.
    
    Args:
        delete_zenml: Whether to delete ZenML schedules
        delete_vertex: Whether to delete Vertex schedules
        location: GCP region for Vertex AI
    """
    # Initialize clients
    zenml_client = Client()
    aiplatform.init(location=location)
    
    # Get all ZenML schedules
    zenml_schedules = zenml_client.list_schedules()
    
    if not zenml_schedules:
        print("No ZenML schedules found.")
    else:
        print(f"\nFound {len(zenml_schedules)} ZenML schedules\n")
    
    # Track successes and failures
    succeeded = []
    failed = []
    
    # Process each ZenML schedule
    for zenml_schedule in zenml_schedules:
        schedule_name = zenml_schedule.name
        print(f"Processing ZenML schedule: {schedule_name}")
        
        # Step 1: Find and delete Vertex AI schedules if requested
        if delete_vertex:
            try:
                vertex_filter = f'display_name="{schedule_name}"'
                vertex_schedules = aiplatform.PipelineJobSchedule.list(
                    filter=vertex_filter,
                    order_by='create_time desc'
                )
                
                if vertex_schedules:
                    print(f"  Found {len(vertex_schedules)} matching Vertex schedules")
                    for vertex_schedule in vertex_schedules:
                        try:
                            vertex_schedule.delete()
                            print(f"  ✓ Deleted Vertex schedule: {vertex_schedule.display_name}")
                        except Exception as e:
                            print(f"  ✗ Failed to delete Vertex schedule: {e}")
                            failed.append(f"{schedule_name} (Vertex)")
                else:
                    print(f"  No matching Vertex schedules found")
            except Exception as e:
                print(f"  ✗ Error accessing Vertex AI: {e}")
                failed.append(f"{schedule_name} (Vertex API)")
        
        # Step 2: Delete the ZenML schedule if requested
        if delete_zenml:
            try:
                zenml_client.delete_schedule(zenml_schedule.id)
                print(f"  ✓ Deleted ZenML schedule: {schedule_name}")
                succeeded.append(f"{schedule_name} (ZenML)")
            except Exception as e:
                print(f"  ✗ Failed to delete ZenML schedule: {e}")
                failed.append(f"{schedule_name} (ZenML)")
    
    # Step 3: Find orphaned Vertex schedules
    print("\nChecking for orphaned Vertex schedules...")
    zenml_schedule_names = [s.name for s in zenml_schedules]
    try:
        all_vertex_schedules = aiplatform.PipelineJobSchedule.list(location=location)
        
        orphaned_schedules = []
        for vs in all_vertex_schedules:
            if vs.display_name not in zenml_schedule_names:
                orphaned_schedules.append(vs)
        
        if orphaned_schedules:
            print(f"Found {len(orphaned_schedules)} orphaned Vertex schedules")
            
            # Delete orphaned schedules if requested
            if delete_vertex:
                for vs in orphaned_schedules:
                    try:
                        vs.delete()
                        print(f"  ✓ Deleted orphaned Vertex schedule: {vs.display_name}")
                        succeeded.append(f"{vs.display_name} (Orphaned Vertex)")
                    except Exception as e:
                        print(f"  ✗ Failed to delete orphaned Vertex schedule: {e}")
                        failed.append(f"{vs.display_name} (Orphaned Vertex)")
        else:
            print("No orphaned Vertex schedules found.")
    except Exception as e:
        print(f"Error checking for orphaned schedules: {e}")
    
    # Summary
    print("\nCleanup Summary:")
    print(f"  Successfully processed: {len(succeeded)}")
    print(f"  Failed to process: {len(failed)}")
    if failed:
        print("\nFailed schedules:")
        for f in failed:
            print(f"  - {f}")
    
    print("\nSchedule cleanup completed!")
```

Similar implementations can be created for Kubeflow and Airflow, adapting to their specific APIs.

#### Safety considerations when deleting schedules

When cleaning up schedules, especially in production environments:

1. **Backup before deletion**: Record all schedule information before deletion
2. **Start with a dry run**: Set `delete_zenml=False, delete_vertex=False` to preview what would be deleted
3. **Delete in phases**: Delete orchestrator schedules first, then ZenML schedules
4. **Verify after deletion**: Confirm that schedules were actually removed
5. **Monitor pipeline runs**: Watch for unexpected pipeline runs after cleanup

## 4. Schedule management best practices

Effective management of pipeline schedules requires careful planning and standardized approaches, especially as the number of schedules grows.

### 4.1 Naming conventions

Following consistent naming patterns helps tremendously with schedule organization and troubleshooting:

```python
# Example of a well-named schedule
schedule = Schedule(
    name="daily-feature-engineering-prod-v2",
    cron_expression="0 4 * * *"
)
```

Recommended naming components:
- **Frequency**: Include how often the schedule runs (`hourly`, `daily`, `weekly`)
- **Purpose**: Describe the pipeline's function (`model-training`, `data-ingest`)
- **Environment**: Indicate the deployment context (`dev`, `staging`, `prod`)
- **Version**: Add version information when updating schedules (`v1`, `v2`)

For example: `hourly-data-ingest-prod-v1`

This pattern makes it easy to:
- Filter schedules by environment or purpose
- Track schedule versions and changes
- Understand the schedule's function at a glance
- Group related schedules together

### 4.2 Schedule monitoring and alerting

Successfully running scheduled pipelines requires robust monitoring to catch issues early:

```python
from zenml.integrations.slack.alerters import SlackAlerter
from zenml.integrations.discord.alerters import DiscordAlerter

# Configure alerting for scheduled pipelines
@pipeline(
    settings={
        "alerter": {
            "slack_alerter": SlackAlerter(
                webhook_url="https://hooks.slack.com/services/XXX/YYY/ZZZ",
                alert_on_success=False,
                alert_on_failure=True,
                message_prefix="SCHEDULED PIPELINE ALERT: "
            )
        }
    }
)
def my_scheduled_pipeline():
    # Pipeline steps
```

Key monitoring strategies:
1. **Failure notifications**: Configure alerters to notify teams about failures
2. **Execution logs**: Regularly review logs for scheduled runs
3. **Performance tracking**: Monitor execution times and resource usage
4. **Cost monitoring**: Track resources consumed by scheduled pipelines
5. **Run status dashboard**: Set up a dashboard showing all schedule executions

For critical pipelines, consider implementing custom monitoring solutions:

```python
from zenml.client import Client
import datetime

def audit_scheduled_runs():
    """Audit scheduled pipeline executions."""
    client = Client()
    schedules = client.list_schedules()
    
    # Check for each schedule
    for schedule in schedules:
        pipeline_name = schedule.pipeline_name
        
        # Get recent runs
        runs = client.list_pipeline_runs(
            pipeline_name_or_id=pipeline_name,
            sort_by="created",
            descending=True,
            size=10
        )
        
        # Check if the most recent run is older than expected
        if runs.items and schedule.cron_expression:
            latest_run = runs.items[0]
            run_time = latest_run.creation_time
            now = datetime.datetime.now(run_time.tzinfo)
            
            # Simple check for daily schedules (improve based on your cron pattern)
            if "* * *" in schedule.cron_expression and (now - run_time).days > 1:
                print(f"WARNING: Schedule {schedule.name} might have missed executions!")
                print(f"  Last run: {run_time}")
```

### 4.3 Managing schedule drift

Schedule drift occurs when the schedules tracked by ZenML no longer match those in the orchestrator. This can happen due to:

- Failed deletion operations
- Manual changes in the orchestrator
- System failures during schedule creation/deletion
- Database restores or migrations

To prevent and manage schedule drift:

1. **Regular audits**: Periodically reconcile ZenML schedules with orchestrator schedules:

```python
def audit_schedule_drift(location="your-region"):
    """Audit for drift between ZenML and Vertex AI schedules."""
    # Get ZenML schedules
    from zenml.client import Client
    zenml_schedules = Client().list_schedules()
    zenml_names = {s.name for s in zenml_schedules}
    
    # Get Vertex schedules
    from google.cloud import aiplatform
    vertex_schedules = aiplatform.PipelineJobSchedule.list(location=location)
    vertex_names = {vs.display_name for vs in vertex_schedules}
    
    # Find schedules that exist only in ZenML
    zenml_only = zenml_names - vertex_names
    if zenml_only:
        print(f"Found {len(zenml_only)} schedules in ZenML but not in Vertex:")
        for name in zenml_only:
            print(f"  - {name}")
    
    # Find schedules that exist only in Vertex
    vertex_only = vertex_names - zenml_names
    if vertex_only:
        print(f"Found {len(vertex_only)} schedules in Vertex but not in ZenML:")
        for name in vertex_only:
            print(f"  - {name}")
    
    # Compute drift percentage
    total_schedules = len(zenml_names.union(vertex_names))
    drift_count = len(zenml_only) + len(vertex_only)
    drift_percentage = (drift_count / total_schedules) * 100 if total_schedules else 0
    
    print(f"Schedule drift: {drift_percentage:.1f}%")
    
    return zenml_only, vertex_only
```

2. **Documentation**: Maintain a registry of all schedules, including orchestrator details
3. **Automated reconciliation**: Run recurring jobs to detect and fix drift
4. **Centralized management**: Use the tools in section 3.5 for complete schedule lifecycle management

## 5. Alternatives to native scheduling

While ZenML's built-in scheduling is powerful, you may want to consider alternative approaches in certain scenarios.

### 5.1 External schedulers

Cloud providers offer native scheduling services that can invoke ZenML pipelines:

**Google Cloud Scheduler**:
```bash
# Create a Cloud Scheduler job to trigger a pipeline using Cloud Run
gcloud scheduler jobs create http daily-pipeline-trigger \
  --schedule="0 9 * * *" \
  --uri="https://your-endpoint/run-pipeline" \
  --http-method=POST \
  --headers="Authorization=Bearer $(gcloud auth print-identity-token)" \
  --message-body='{"pipeline_name": "training_pipeline"}'
```

**AWS EventBridge**:
```bash
# Define an EventBridge schedule (using AWS CLI)
aws scheduler create-schedule \
  --name daily-pipeline-trigger \
  --schedule-expression "cron(0 9 * * ? *)" \
  --target '{"Arn": "arn:aws:lambda:region:account-id:function:run-zenml-pipeline", "Input": "{\"pipeline_name\": \"training_pipeline\"}"}'
```

**Simple cron job**:
```bash
# Schedule using traditional cron (Linux/MacOS)
# Add to crontab:
0 9 * * * cd /path/to/project && python -m run_pipeline.py
```

Benefits of external schedulers:
- Separation of scheduling from pipeline logic
- Greater control over retry policies and error handling
- Integration with existing monitoring systems
- Often more cost-effective for simple scheduling needs

### 5.2 CI/CD-based scheduling

Another popular approach is using CI/CD systems for pipeline scheduling:

**GitHub Actions**:
```yaml
# .github/workflows/scheduled-pipeline.yml
name: Run Daily Pipeline

on:
  schedule:
    # Run at 9:00 UTC every day
    - cron: '0 9 * * *'

jobs:
  run_pipeline:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
          
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install zenml
          pip install -r requirements.txt
          
      - name: Run ZenML pipeline
        run: python run_pipeline.py
        env:
          ZENML_SERVER_URL: ${{ secrets.ZENML_SERVER_URL }}
          ZENML_API_KEY: ${{ secrets.ZENML_API_KEY }}
```

**GitLab CI**:
```yaml
# .gitlab-ci.yml
daily_pipeline:
  image: python:3.9
  script:
    - pip install zenml
    - pip install -r requirements.txt
    - python run_pipeline.py
  only:
    - schedules
```

**Jenkins**:
```groovy
// Jenkinsfile with scheduling
pipeline {
    triggers {
        cron('0 9 * * *')
    }
    agent {
        docker {
            image 'python:3.9'
        }
    }
    stages {
        stage('Run ZenML Pipeline') {
            steps {
                sh 'pip install zenml'
                sh 'pip install -r requirements.txt'
                sh 'python run_pipeline.py'
            }
        }
    }
}
```

Benefits of CI/CD scheduling:
- Version control integration
- Detailed execution history
- Integration with deployment workflows
- Infrastructure-as-code approach to scheduling
- Multi-environment support (different schedules for dev/staging/prod)

## 6. Troubleshooting schedule issues

Even with careful setup, scheduled pipelines can encounter issues. This section covers common problems and resolution strategies.

### 6.1 Common schedule problems

**1. Missing executions**:
- **Symptom**: Pipeline doesn't run at the scheduled time
- **Possible causes**:
  - Orchestrator failure or outage
  - Authentication expired
  - Resource constraints 
  - Schedule paused or disabled
- **Resolution**:
  - Check orchestrator logs
  - Verify authentication credentials
  - Ensure sufficient resources are available
  - Check schedule status in the orchestrator

**2. Authentication failures**:
- **Symptom**: Pipeline fails with authentication errors
- **Possible causes**:
  - Expired service account token
  - Missing permissions
  - Secret store issues
- **Resolution**:
  - Rotate service account credentials
  - Check IAM permissions
  - Verify secret references

**3. Resource constraints**:
- **Symptom**: Scheduled pipelines fail during execution
- **Possible causes**:
  - Insufficient resources at scheduled time
  - Resource quota limits
  - Temporary infrastructure issues
- **Resolution**:
  - Increase resource quotas
  - Stagger schedule times to spread load
  - Configure auto-scaling where available

**4. Configuration drift**:
- **Symptom**: Pipeline runs with unexpected configuration
- **Possible causes**:
  - Pipeline code updated but schedule still uses old configuration
  - Environment variable changes
  - Dependency changes
- **Resolution**:
  - Update or recreate schedules when pipeline code changes
  - Use configuration versioning
  - Test schedule recreation regularly

### 6.2 Debugging strategies

When troubleshooting schedule issues, follow these steps:

**1. Verify the schedule exists**:
```bash
# Check in ZenML
zenml pipeline schedule list

# Check in orchestrator (example for Airflow)
airflow dags list
```

**2. Check execution logs**:
- ZenML pipeline runs:
  ```bash
  zenml pipeline runs list --pipeline_name your_pipeline
  ```
- Orchestrator-specific logs:
  - Vertex AI: Check Cloud Logging
  - Kubeflow: Check Kubeflow UI
  - Airflow: Check Airflow logs

**3. Validate configuration**:
- Ensure environment variables are set correctly
- Check that resource settings are appropriate
- Verify authentication is still valid

**4. Test manual execution**:
- Run the pipeline manually to confirm it works outside the schedule
- Compare the configuration of manual vs. scheduled runs

**5. Try with simplified pipeline**:
- Create a minimal test pipeline with the same schedule
- Use this to isolate scheduling issues from pipeline implementation issues

**6. Check for orchestrator-specific issues**:
- Vertex AI: Check quota and billing status
- Kubeflow: Check Kubernetes cluster health
- Airflow: Check worker status and DAG parsing errors

## Conclusion

Effective schedule management is crucial for production ML workflows. ZenML provides a unified interface for scheduling across different orchestrators, but understanding the underlying orchestrator behavior is essential for robust schedule management.

Key takeaways:
- Use consistent naming conventions and monitor your schedules
- Be aware of the limitations of each orchestrator's scheduling capabilities
- Clean up orphaned schedules regularly to prevent unexpected execution
- Consider alternative scheduling approaches for complex requirements
- Implement proper monitoring and alerting for critical pipelines

As ZenML continues to evolve, the scheduling capabilities will be enhanced with more direct control over schedule lifecycle management. Until then, the hybrid approach of using ZenML's abstraction with orchestrator-specific management provides the most complete solution.

For more information, refer to the official ZenML documentation on pipeline scheduling and the documentation for your specific orchestrator.
