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
| AzureML | ✅ | Integration with Azure monitoring, authentication via service connectors |  |
| Databricks | ✅ | Integration with Databricks workspace | Basic scheduling capabilities only |
| HyperAI | ✅ | Simplified scheduling | Limited frequency control options |
| Kubeflow | ✅ | Full cron support, UI management, catchup functionality | Only supports cron expressions (no interval-based scheduling) |
| Kubernetes | ✅ | Uses Kubernetes CronJobs | Only supports cron expressions; no built-in pause/resume functionality |
| Local | ❌ | Not applicable | No scheduling support at all |
| Local Docker | ❌ | Not applicable | No scheduling support at all |
| SageMaker | ✅ | AWS integration, CloudWatch monitoring |  |
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

3. Set up monitoring for your scheduled pipeline runs using hooks:

   ```python
   from zenml.hooks import alerter_success_hook, alerter_failure_hook
   from zenml import pipeline, step
   
   # Define step with alerter hooks
   @step(on_failure=alerter_failure_hook, on_success=alerter_success_hook)
   def monitored_step():
       # Your step logic here
       pass
   
   # Your pipeline with the monitored step
   @pipeline()
   def my_scheduled_pipeline():
       monitored_step()
       # Other pipeline steps
   ```
   
   This assumes you've already registered an alerter (e.g. Slack or Discord) in your active stack.

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
from zenml.hooks import alerter_failure_hook
from zenml import pipeline, step

# Configure alerting for scheduled pipelines using hooks
# Apply the failure hook to critical steps
@step(on_failure=alerter_failure_hook)
def critical_pipeline_step():
    # Your step logic here
    pass

# Your pipeline with alerting on failure
@pipeline()
def my_scheduled_pipeline():
    critical_pipeline_step()
    # Other pipeline steps
    
# Alternatively, you can use the alerter directly in a step
@step
def alert_step(message: str):
    from zenml.client import Client
    
    # Get the active alerter from the stack
    alerter = Client().active_stack.alerter
    
    # Post a custom message with pipeline details
    alerter.post(f"SCHEDULED PIPELINE ALERT: {message}")
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

While ZenML's built-in scheduling is powerful, there are scenarios where alternative approaches provide better flexibility, control, or integration with existing systems. This section explores these alternatives with practical implementation examples.

### 5.1 External schedulers

Cloud providers offer native scheduling services that can trigger ZenML pipelines through HTTP endpoints or serverless functions. These solutions provide robust scheduling with extensive monitoring and failure handling.

#### Creating a ZenML pipeline runner script

First, create a script that can be invoked externally to run your pipeline:

```python
# run_pipeline.py
import os
import sys
import json
from zenml.client import Client

def run_pipeline(pipeline_name, params=None):
    """Run a ZenML pipeline by name with optional parameters.
    
    Args:
        pipeline_name: Name of the registered pipeline to run
        params: Dictionary of parameters to pass to the pipeline
    """
    try:
        # Connect to ZenML
        client = Client()
        print(f"Connected to ZenML server at {client.zen_store.url}")
        
        # Get the pipeline by name
        pipeline = client.get_pipeline_by_name(pipeline_name)
        if not pipeline:
            raise ValueError(f"Pipeline '{pipeline_name}' not found")
        
        # Run the pipeline
        print(f"Running pipeline '{pipeline_name}'...")
        if params:
            pipeline_instance = pipeline(params)
        else:
            pipeline_instance = pipeline()
            
        pipeline_run = pipeline_instance.run()
        print(f"Pipeline run started: {pipeline_run.id}")
        return pipeline_run.id
        
    except Exception as e:
        print(f"Error running pipeline: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Parse command line arguments or environment variables
    if len(sys.argv) > 1:
        pipeline_name = sys.argv[1]
        params = json.loads(sys.argv[2]) if len(sys.argv) > 2 else None
    else:
        pipeline_name = os.environ.get("PIPELINE_NAME")
        params_str = os.environ.get("PIPELINE_PARAMS")
        params = json.loads(params_str) if params_str else None
    
    if not pipeline_name:
        print("Error: Pipeline name not provided")
        print("Usage: python run_pipeline.py <pipeline_name> '<json_params>'")
        sys.exit(1)
    
    run_pipeline(pipeline_name, params)
```

#### Using Google Cloud Scheduler with Cloud Run

1. **Create a Cloud Run service**:

```python
# app.py - Flask API to trigger ZenML pipeline
from flask import Flask, request, jsonify
import os
from run_pipeline import run_pipeline

app = Flask(__name__)

@app.route("/run-pipeline", methods=["POST"])
def trigger_pipeline():
    data = request.json
    
    # Extract pipeline info
    pipeline_name = data.get("pipeline_name")
    pipeline_params = data.get("params", {})
    
    if not pipeline_name:
        return jsonify({"error": "Missing pipeline_name"}), 400
    
    # Authenticate (use more robust auth in production)
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}), 401
    
    # Run the pipeline
    try:
        run_id = run_pipeline(pipeline_name, pipeline_params)
        return jsonify({
            "status": "success", 
            "message": f"Pipeline {pipeline_name} triggered",
            "run_id": run_id
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
```

2. **Deploy to Cloud Run**:

```bash
# Build and deploy the service
gcloud builds submit --tag gcr.io/YOUR_PROJECT/zenml-pipeline-runner
gcloud run deploy zenml-pipeline-runner \
  --image gcr.io/YOUR_PROJECT/zenml-pipeline-runner \
  --platform managed \
  --allow-unauthenticated
```

3. **Create a Cloud Scheduler job**:

```bash
# Create a Cloud Scheduler job to trigger daily at 9 AM
gcloud scheduler jobs create http daily-training-pipeline \
  --schedule="0 9 * * *" \
  --uri="https://zenml-pipeline-runner-HASH.a.run.app/run-pipeline" \
  --http-method=POST \
  --headers="Authorization=Bearer $(gcloud auth print-identity-token)" \
  --message-body='{
      "pipeline_name": "training_pipeline",
      "params": {
          "training_data_path": "gs://your-bucket/data",
          "model_version": "v3",
          "hyperparameters": {"learning_rate": 0.01}
      }
  }'
```

#### Using AWS EventBridge with Lambda

1. **Create a Lambda function**:

```python
# lambda_function.py
import os
import json
from run_pipeline import run_pipeline

def lambda_handler(event, context):
    """AWS Lambda handler to run a ZenML pipeline.
    
    Event format:
    {
        "pipeline_name": "training_pipeline",
        "params": {
            "data_version": "latest",
            "hyperparameters": {"batch_size": 64}
        }
    }
    """
    try:
        # Set up ZenML connection using environment variables
        # These would be configured in the Lambda environment
        
        # Extract pipeline info
        pipeline_name = event.get("pipeline_name")
        params = event.get("params", {})
        
        if not pipeline_name:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing pipeline_name"})
            }
        
        # Run the pipeline
        run_id = run_pipeline(pipeline_name, params)
        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": "success",
                "message": f"Pipeline {pipeline_name} triggered",
                "run_id": run_id
            })
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
```

2. **Create an EventBridge rule**:

```bash
# Create a scheduled rule (using AWS CLI)
aws events put-rule \
  --name daily-model-training \
  --schedule-expression "cron(0 9 * * ? *)" \
  --state ENABLED

# Add Lambda as target
aws events put-targets \
  --rule daily-model-training \
  --targets '[{
      "Id": "1", 
      "Arn": "arn:aws:lambda:region:account-id:function:zenml-pipeline-runner",
      "Input": "{\"pipeline_name\":\"training_pipeline\",\"params\":{\"data_version\":\"latest\"}}"
  }]'
```

#### Simple cron job with error handling

For basic scheduling on a VM or server:

```bash
#!/bin/bash
# run_zenml_pipeline.sh - Add to crontab
set -e

# Environment setup
export ZENML_SERVER_URL="https://your-zenml-server"
export ZENML_API_KEY="your-api-key"
export PYTHONPATH=/path/to/project

# Configuration
PIPELINE_NAME="daily_training_pipeline"
LOG_FILE="/var/log/zenml_pipeline_runs.log"
ALERT_EMAIL="alerts@your-company.com"

# Run the pipeline and log output
cd /path/to/project
echo "=== Pipeline run started: $(date) ===" >> $LOG_FILE
if python -m run_pipeline $PIPELINE_NAME '{"version": "prod"}'; then
    echo "Pipeline executed successfully" >> $LOG_FILE
else
    echo "Pipeline execution failed with status $?" >> $LOG_FILE
    # Send an alert email
    echo "ZenML pipeline $PIPELINE_NAME failed. See $LOG_FILE for details" | \
      mail -s "ZenML Pipeline Failure" $ALERT_EMAIL
fi
echo "=== Pipeline run completed: $(date) ===" >> $LOG_FILE
```

Add to crontab:
```
# Run daily at 3 AM
0 3 * * * /path/to/run_zenml_pipeline.sh
```

### 5.2 CI/CD-based scheduling

CI/CD systems offer powerful scheduling with built-in support for versioning, logging, and notifications. Here's how to implement robust scheduled pipelines using common CI/CD platforms.

#### GitHub Actions with matrix configurations

This example runs different pipeline configurations based on the day of the week:

```yaml
# .github/workflows/scheduled-pipelines.yml
name: Scheduled ZenML Pipelines

on:
  schedule:
    # Run every weekday at 9:00 UTC
    - cron: '0 9 * * 1-5'
    # Run weekend batch job at 12:00 UTC
    - cron: '0 12 * * 0,6'
  
  # Allow manual triggering
  workflow_dispatch:
    inputs:
      pipeline_name:
        description: 'Pipeline to run'
        required: true
        default: 'training_pipeline'
        type: choice
        options:
          - training_pipeline
          - feature_engineering_pipeline
          - evaluation_pipeline
      environment:
        description: 'Target environment'
        default: 'staging'
        type: choice
        options:
          - dev
          - staging
          - production

jobs:
  determine_pipeline:
    runs-on: ubuntu-latest
    outputs:
      matrix: ${{ steps.set-matrix.outputs.matrix }}
    steps:
      - id: set-matrix
        run: |
          # Determine day of week (0=Sunday, 6=Saturday)
          DOW=$(date +%u)
          
          # Weekday: Run feature engineering and incremental training
          if [[ $DOW -le 5 ]]; then
            echo "matrix={\"pipeline\":[\"feature_engineering\",\"incremental_training\"],\"environment\":[\"production\"]}" >> $GITHUB_OUTPUT
          # Weekend: Run full training with more data
          else
            echo "matrix={\"pipeline\":[\"full_training\"],\"environment\":[\"production\"]}" >> $GITHUB_OUTPUT
          fi
          
          # If manually triggered, override the matrix
          if [[ "${{ github.event_name }}" == "workflow_dispatch" ]]; then
            echo "matrix={\"pipeline\":[\"${{ github.event.inputs.pipeline_name }}\"],\"environment\":[\"${{ github.event.inputs.environment }}\"]}" >> $GITHUB_OUTPUT
          fi

  run_pipeline:
    needs: determine_pipeline
    runs-on: ubuntu-latest
    strategy:
      matrix: ${{ fromJson(needs.determine_pipeline.outputs.matrix) }}
      fail-fast: false
    
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
          
      - name: Configure ZenML
        run: |
          # Configure ZenML based on environment
          echo "Setting up ZenML for ${{ matrix.environment }}"
          if [[ "${{ matrix.environment }}" == "production" ]]; then
            zenml connect --url ${{ secrets.ZENML_PROD_URL }} --api-key ${{ secrets.ZENML_PROD_API_KEY }}
            zenml stack set production_stack
          else
            zenml connect --url ${{ secrets.ZENML_STAGING_URL }} --api-key ${{ secrets.ZENML_STAGING_API_KEY }}
            zenml stack set staging_stack
          fi
      
      - name: Run Pipeline
        id: run-pipeline
        run: |
          # Run the appropriate pipeline
          echo "Running ${{ matrix.pipeline }} pipeline in ${{ matrix.environment }}"
          
          # Set pipeline-specific parameters
          PARAMS='{}'
          if [[ "${{ matrix.pipeline }}" == "full_training" ]]; then
            PARAMS='{"data_version": "full", "epochs": 100}'
          elif [[ "${{ matrix.pipeline }}" == "incremental_training" ]]; then
            PARAMS='{"data_version": "incremental", "epochs": 20}'
          fi
          
          # Run and capture the output
          RUN_OUTPUT=$(python run_pipeline.py ${{ matrix.pipeline }} "$PARAMS")
          echo "run_output=$RUN_OUTPUT" >> $GITHUB_OUTPUT
          
      - name: Notify on failure
        if: failure()
        uses: actions/github-script@v6
        with:
          script: |
            const message = `⚠️ Pipeline ${{ matrix.pipeline }} failed in ${{ matrix.environment }}.`;
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: `Pipeline failure: ${{ matrix.pipeline }}`,
              body: message + `\n\nSee logs: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}`
            });
```

#### GitLab CI with environment variables and templates

```yaml
# .gitlab-ci.yml
stages:
  - validate
  - run_pipeline

# Variables for all jobs
variables:
  ZENML_VERSION: "0.40.0"

# Template for running pipelines
.pipeline_template: &pipeline_template
  image: python:3.9
  before_script:
    - pip install zenml==$ZENML_VERSION
    - pip install -r requirements.txt
    - zenml connect --url $ZENML_SERVER_URL --api-key $ZENML_API_KEY
    - zenml stack set $ZENML_STACK_NAME
  script:
    - python run_pipeline.py $PIPELINE_NAME "$PIPELINE_PARAMS"
  after_script:
    - echo "Pipeline run completed at $(date)"

# Validation job
validate_configuration:
  stage: validate
  image: python:3.9
  script:
    - pip install zenml==$ZENML_VERSION
    - zenml connect --url $ZENML_SERVER_URL --api_key $ZENML_API_KEY
    - zenml stack list
    - echo "Configuration validated"
  rules:
    - if: $CI_PIPELINE_SOURCE == "schedule"

# Define specific pipeline jobs
daily_feature_engineering:
  <<: *pipeline_template
  stage: run_pipeline
  variables:
    PIPELINE_NAME: "feature_engineering_pipeline"
    PIPELINE_PARAMS: '{"date": "'$(date -I)'", "features": ["user", "item", "category"]}'
  rules:
    - if: $CI_PIPELINE_SOURCE == "schedule"
      when: manual
      allow_failure: true
  resource_group: feature_engineering
  tags:
    - ml-runner

daily_training:
  <<: *pipeline_template
  stage: run_pipeline
  variables:
    PIPELINE_NAME: "training_pipeline"
    PIPELINE_PARAMS: '{"mode": "incremental"}'
  rules:
    - if: $CI_PIPELINE_SOURCE == "schedule"
  resource_group: training
  tags:
    - gpu-runner
  retry:
    max: 2
    when:
      - runner_system_failure
```

To schedule in GitLab UI:
1. Go to CI/CD > Schedules
2. Create a new schedule
3. Set the pipeline you want to run and the cron schedule
4. Add any specific variables for that schedule

#### Advanced Jenkins pipeline with parallel stages

```groovy
// Jenkinsfile with parallel stages and parameter handling
def runParams

pipeline {
    triggers {
        // Run at 9:00 AM on weekdays
        cron('0 9 * * 1-5')
    }
    
    parameters {
        choice(name: 'ENVIRONMENT', choices: ['dev', 'staging', 'prod'], description: 'Target environment')
        choice(name: 'PIPELINE_TYPE', choices: ['feature_engineering', 'training', 'evaluation'], description: 'Pipeline to run')
        text(name: 'PIPELINE_PARAMS', defaultValue: '{}', description: 'Pipeline parameters as JSON')
    }
    
    agent none
    
    stages {
        stage('Initialize') {
            agent { label 'master' }
            steps {
                script {
                    // Use parameters from manual trigger or set defaults for scheduled runs
                    if (currentBuild.getBuildCauses('hudson.triggers.TimerTrigger$TimerTriggerCause').size() > 0) {
                        runParams = [
                            environment: 'prod',
                            pipelineType: 'training',
                            pipelineParams: '{"mode": "incremental", "features": ["all"]}'
                        ]
                        echo "Scheduled run - using default parameters"
                    } else {
                        runParams = [
                            environment: params.ENVIRONMENT,
                            pipelineType: params.PIPELINE_TYPE,
                            pipelineParams: params.PIPELINE_PARAMS
                        ]
                        echo "Manual run - using provided parameters"
                    }
                    
                    echo "Running ${runParams.pipelineType} pipeline in ${runParams.environment}"
                }
            }
        }
        
        stage('Run Pipelines') {
            parallel {
                stage('Run ZenML Pipeline') {
                    agent {
                        docker {
                            image 'python:3.9'
                            args '-v /var/jenkins_home/zenml:/root/.config/zenml'
                        }
                    }
                    steps {
                        // Install dependencies 
                        sh 'pip install zenml'
                        sh 'pip install -r requirements.txt'
                        
                        // Configure ZenML
                        withCredentials([string(credentialsId: "${runParams.environment}_zenml_url", variable: 'ZENML_URL'),
                                         string(credentialsId: "${runParams.environment}_zenml_api_key", variable: 'ZENML_API_KEY')]) {
                            sh 'zenml connect --url $ZENML_URL --api-key $ZENML_API_KEY'
                            sh "zenml stack set ${runParams.environment}_stack"
                        }
                        
                        // Run the pipeline
                        sh "python run_pipeline.py ${runParams.pipelineType}_pipeline '${runParams.pipelineParams}'"
                    }
                }
                
                stage('Monitor Resources') {
                    agent { label 'master' }
                    steps {
                        // Monitor system resources during pipeline execution
                        sh 'mkdir -p monitoring'
                        sh 'top -b -n 60 -d 60 > monitoring/top_output.txt &'
                        sh 'vmstat 60 60 > monitoring/vmstat_output.txt &'
                        sh 'sleep 3600' // Allow monitoring to run for max 1 hour
                    }
                }
            }
        }
    }
    
    post {
        always {
            node('master') {
                // Archive monitoring data
                archiveArtifacts artifacts: 'monitoring/*.txt', allowEmptyArchive: true
            }
        }
        success {
            echo "Pipeline completed successfully"
            // Additional success actions
        }
        failure {
            echo "Pipeline failed"
            // Send notifications
            mail to: 'team@example.com',
                 subject: "Failed Pipeline: ${runParams.pipelineType}",
                 body: "Pipeline ${runParams.pipelineType} failed in ${runParams.environment}. See ${BUILD_URL}"
        }
    }
}
```

### 5.3 Comparing scheduling approaches

Each scheduling approach has distinct advantages for different use cases:

| Aspect | ZenML Native | Cloud Provider Schedulers | CI/CD Schedulers |
|--------|-------------|--------------------------|-----------------|
| Setup complexity | Low | Medium | Medium |
| Infrastructure control | Limited | High | Medium |
| Failure handling | Orchestrator-dependent | Advanced (retries, DLQ) | Good (retry policies) |
| Monitoring | Basic | Comprehensive | Detailed |
| Alerting | Via alerters | Native integrations | Built-in |
| Cost | Varies by orchestrator | Typically low | CI minutes/credits |
| Version control | Limited | Manual | Built-in |
| Pipeline parameters | Fixed at creation | Flexible | Flexible |

**Guidelines for choosing a scheduling approach:**

1. **Use ZenML native scheduling when:**
   - You want the simplest setup
   - Orchestrator capabilities are sufficient
   - You're already using a specific orchestrator
   
2. **Use cloud provider schedulers when:**
   - You need fine-grained control over execution
   - You want advanced retry and error handling
   - Cost optimization is important
   - You have complex authentication requirements
   
3. **Use CI/CD schedulers when:**
   - You want tight version control integration
   - You need to coordinate multiple pipeline runs
   - Development team is already familiar with CI/CD
   - You want detailed run history and logs

## 6. Troubleshooting schedule issues

Even with careful setup, scheduled pipelines can encounter issues. This section provides practical debugging approaches and solutions to common scheduling problems.

### 6.1 Common schedule problems and solutions

#### 1. Missing executions

When a pipeline doesn't run at the scheduled time, follow this diagnostic workflow:

```python
# diagnostic_scheduler.py - Script to diagnose schedule issues
from zenml.client import Client
import datetime
import json
import sys
import subprocess
import os

def diagnose_schedule(schedule_name_or_id):
    """Diagnose issues with a specific schedule."""
    client = Client()
    
    # Get the schedule
    try:
        schedule = client.get_schedule(schedule_name_or_id)
        print(f"✓ Found schedule: {schedule.name}")
    except Exception as e:
        print(f"✗ Schedule not found in ZenML: {e}")
        return
    
    # Check recent runs
    pipeline_name = schedule.pipeline_name
    print(f"\nChecking runs for pipeline '{pipeline_name}'...")
    
    # Get recent runs (last 24 hours)
    now = datetime.datetime.now(datetime.timezone.utc)
    yesterday = now - datetime.timedelta(days=1)
    
    runs = client.list_pipeline_runs(
        pipeline_name_or_id=pipeline_name,
        sort_by="created",
        descending=True,
        size=10
    )
    
    recent_runs = [run for run in runs.items if run.creation_time > yesterday]
    print(f"Found {len(recent_runs)} runs in the last 24 hours")
    
    # Check orchestration details
    orchestrator = client.active_stack.orchestrator
    orchestrator_type = orchestrator.__class__.__name__
    print(f"\nOrchestrator type: {orchestrator_type}")
    
    # Orchestrator-specific diagnostics
    if "KubeflowOrchestrator" in orchestrator_type:
        diagnose_kubeflow_schedule(schedule)
    elif "VertexOrchestrator" in orchestrator_type:
        diagnose_vertex_schedule(schedule)
    elif "AirflowOrchestrator" in orchestrator_type:
        diagnose_airflow_schedule(schedule)
    
    # Check system environment
    print("\nChecking environment variables...")
    required_vars = [
        "ZENML_SERVER_URL", 
        "ZENML_API_KEY", 
        # Add orchestrator-specific environment variables
    ]
    
    for var in required_vars:
        if var in os.environ:
            print(f"✓ {var}: Set")
        else:
            print(f"✗ {var}: Not set")
    
    # Provide next steps
    print("\nRecommended next steps:")
    if len(recent_runs) == 0:
        print("- Try running the pipeline manually to verify it works")
        print("- Check orchestrator logs for errors")
        print("- Verify service account permissions")
    else:
        print("- Compare manual run configuration with scheduled run")
        print("- Check for resource constraints at scheduled time")
        print("- Verify the schedule hasn't been paused in the orchestrator")

def diagnose_kubeflow_schedule(schedule):
    """Kubeflow-specific diagnostics."""
    try:
        # Execute kubectl command to check recurring runs
        cmd = ["kubectl", "get", "recurringruns", "-n", "kubeflow"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("\nKubeflow recurring runs:")
            print(result.stdout)
            
            # Check if our schedule exists
            if schedule.name in result.stdout:
                print(f"✓ Schedule '{schedule.name}' found in Kubeflow")
            else:
                print(f"✗ Schedule '{schedule.name}' not found in Kubeflow")
        else:
            print(f"✗ Failed to query Kubeflow: {result.stderr}")
    except Exception as e:
        print(f"Error checking Kubeflow: {e}")

# Add similar functions for other orchestrators
# ...

if __name__ == "__main__":
    if len(sys.argv) > 1:
        diagnose_schedule(sys.argv[1])
    else:
        print("Usage: python diagnostic_scheduler.py <schedule_name_or_id>")
```

**Common causes and solutions:**

| Problem | Diagnosis | Solution |
|---------|-----------|----------|
| Orchestrator failure | Check orchestrator status dashboard | Restart orchestrator services |
| Authentication issues | Verify service account tokens in secrets store | Rotate credentials, update secrets |
| Resource constraints | Check resource quotas | Increase capacity or optimize resource usage |
| Schedule disabled | Check orchestrator UI for paused schedules | Enable the schedule in orchestrator UI |
| Network connectivity | Check network logs for connectivity issues | Fix firewall or network configuration |

#### 2. Authentication failures

When scheduled pipelines fail due to authentication issues:

```python
# Create a script to verify authentication for your orchestrator

# For Vertex AI example:
from google.cloud import aiplatform
import subprocess
import json

def verify_vertex_auth():
    """Verify Vertex AI authentication works."""
    try:
        # Initialize the Vertex AI client
        aiplatform.init()
        
        # List pipeline job schedules
        schedules = aiplatform.PipelineJobSchedule.list()
        
        print(f"✓ Authentication successful - found {len(schedules)} schedules")
        return True
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        
        # Get more detailed error information
        import google.auth
        try:
            _, project = google.auth.default()
            print(f"Default project: {project}")
        except Exception as auth_e:
            print(f"Failed to get default credentials: {auth_e}")
            
        return False

# Add a function to verify service account permissions
def check_service_account_permissions(sa_email, project_id):
    """Check service account has necessary permissions."""
    required_roles = [
        "roles/aiplatform.user",
        "roles/storage.objectAdmin"
    ]
    
    cmd = [
        "gcloud", "projects", "get-iam-policy", project_id,
        "--format=json", "--filter", f"bindings.members:serviceAccount:{sa_email}"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            policy = json.loads(result.stdout)
            
            # Check for each required role
            found_roles = []
            for binding in policy.get("bindings", []):
                if f"serviceAccount:{sa_email}" in binding.get("members", []):
                    found_roles.append(binding.get("role"))
            
            # Report findings
            print(f"Service account: {sa_email}")
            print("Required roles:")
            for role in required_roles:
                if role in found_roles:
                    print(f"  ✓ {role}")
                else:
                    print(f"  ✗ {role} - MISSING")
        else:
            print(f"Failed to get IAM policy: {result.stderr}")
    except Exception as e:
        print(f"Error checking permissions: {e}")
```

#### 3. Resource constraints

To detect and address resource-related failures:

```python
# For Kubernetes-based orchestrators:
import subprocess

def check_cluster_resources():
    """Check Kubernetes cluster resources."""
    try:
        # Check node resources
        cmd = ["kubectl", "describe", "nodes"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Parse CPU and memory allocations
            output = result.stdout
            
            # Simple parsing for demonstration
            import re
            
            # Look for resource pressure
            pressure_indicators = [
                "MemoryPressure",
                "DiskPressure", 
                "PIDPressure"
            ]
            
            for indicator in pressure_indicators:
                if re.search(f"{indicator}\\s+False", output):
                    print(f"✓ No {indicator}")
                else:
                    print(f"✗ Possible {indicator} detected")
            
            # Check for pods that couldn't be scheduled
            cmd = ["kubectl", "get", "pods", "--all-namespaces", "--field-selector=status.phase=Pending"]
            pod_result = subprocess.run(cmd, capture_output=True, text=True)
            
            if "No resources found" in pod_result.stdout:
                print("✓ No pending pods found")
            else:
                print(f"✗ Found pending pods that might indicate resource constraints:")
                print(pod_result.stdout)
                
        else:
            print(f"Failed to query nodes: {result.stderr}")
    except Exception as e:
        print(f"Error checking cluster resources: {e}")
```

#### 4. Configuration drift

Detect and fix configuration drift with a synchronization script:

```python
from zenml.client import Client
from zenml.config.schedule import Schedule

def sync_schedule_config(schedule_name, recreate=False):
    """Synchronize schedule configuration with latest pipeline code."""
    client = Client()
    
    try:
        # Get the schedule
        schedule = client.get_schedule(schedule_name)
        pipeline_name = schedule.pipeline_name
        
        print(f"Schedule: {schedule.name}")
        print(f"Pipeline: {pipeline_name}")
        
        if recreate:
            # Delete the old schedule
            client.delete_schedule(schedule.id)
            print(f"✓ Deleted old schedule: {schedule.name}")
            
            # Get the pipeline
            pipeline = client.get_pipeline_by_name(pipeline_name)
            if not pipeline:
                print(f"✗ Pipeline not found: {pipeline_name}")
                return
                
            # Create new schedule with same parameters
            new_schedule_params = {
                "name": schedule.name,
                "cron_expression": schedule.cron_expression,
                "start_time": schedule.start_time,
                "end_time": schedule.end_time,
                "catchup": schedule.catchup
            }
            
            # Filter out None values
            new_schedule_params = {k: v for k, v in new_schedule_params.items() if v is not None}
            
            from zenml.config.schedule import Schedule
            new_schedule = Schedule(**new_schedule_params)
            
            # Run the pipeline with the new schedule
            pipeline_instance = pipeline().with_options(schedule=new_schedule)
            run = pipeline_instance.run()
            
            print(f"✓ Created new schedule with same parameters")
            print(f"  Pipeline run ID: {run.id}")
        else:
            print("Dry run mode - not recreating schedule")
            print("Run with --recreate flag to recreate the schedule")
    except Exception as e:
        print(f"Error synchronizing schedule: {e}")
```

### 6.2 Advanced debugging strategies

For persistent or complex scheduling issues, implement these advanced debugging approaches:

#### Systematic schedule validation

Create a validation script that performs a comprehensive check of all schedules:

```python
from zenml.client import Client
import datetime
from croniter import croniter

def validate_all_schedules():
    """Validate all schedules and their orchestrator counterparts."""
    client = Client()
    schedules = client.list_schedules()
    
    print(f"Found {len(schedules)} schedules in ZenML")
    
    valid_count = 0
    invalid_count = 0
    
    for schedule in schedules:
        print(f"\nValidating schedule: {schedule.name}")
        
        # Check basic properties
        valid = True
        
        # 1. Check if pipeline exists
        try:
            pipeline = client.get_pipeline_by_name(schedule.pipeline_name)
            if pipeline:
                print(f"✓ Pipeline exists: {schedule.pipeline_name}")
            else:
                print(f"✗ Pipeline not found: {schedule.pipeline_name}")
                valid = False
        except Exception:
            print(f"✗ Error getting pipeline: {schedule.pipeline_name}")
            valid = False
        
        # 2. Check if the cron expression is valid
        if schedule.cron_expression:
            try:
                from croniter import croniter
                if croniter.is_valid(schedule.cron_expression):
                    print(f"✓ Valid cron expression: {schedule.cron_expression}")
                else:
                    print(f"✗ Invalid cron expression: {schedule.cron_expression}")
                    valid = False
            except ImportError:
                print("- Skipping cron validation (croniter not installed)")
        
        # 3. Check for orchestrator-specific issues
        # This would be customized based on your orchestrator
        
        # 4. Check recent runs (last 7 days)
        now = datetime.datetime.now(datetime.timezone.utc)
        week_ago = now - datetime.timedelta(days=7)
        
        runs = client.list_pipeline_runs(
            pipeline_name_or_id=schedule.pipeline_name,
            sort_by="created",
            descending=True
        )
        
        recent_runs = [run for run in runs.items if run.creation_time > week_ago]
        if recent_runs:
            print(f"✓ Has {len(recent_runs)} runs in the past week")
        else:
            print(f"! No runs in the past week - possible issue")
            # Don't mark invalid because it might be a new schedule or low frequency
        
        if valid:
            valid_count += 1
        else:
            invalid_count += 1
    
    print(f"\nValidation complete:")
    print(f"  Valid schedules: {valid_count}")
    print(f"  Invalid schedules: {invalid_count}")
```

#### Creating a test schedule suite

For testing schedule functionality across orchestrators:

```python
import time
import uuid
import datetime
from zenml.client import Client
from zenml.config.schedule import Schedule
from zenml import pipeline

def test_schedule_creation(orchestrator_name):
    """Test schedule creation, verification, and deletion for an orchestrator."""
    
    # Create a unique test pipeline
    @pipeline(name=f"test_schedule_pipeline_{uuid.uuid4().hex[:8]}")
    def test_pipeline():
        # Empty pipeline for testing
        pass
    
    # Create a test schedule (run in one minute)
    now = datetime.datetime.now(datetime.timezone.utc)
    run_time = now + datetime.timedelta(minutes=1)
    minute = run_time.minute
    hour = run_time.hour
    
    # Create a schedule to run once
    cron_expression = f"{minute} {hour} {run_time.day} {run_time.month} *"
    schedule = Schedule(name=f"test_schedule_{uuid.uuid4().hex[:8]}", 
                        cron_expression=cron_expression)
    
    try:
        # Run with the schedule
        client = Client()
        print(f"Testing scheduling for orchestrator: {orchestrator_name}")
        print(f"Creating schedule to run at: {run_time.strftime('%H:%M:%S')}")
        print(f"Cron expression: {cron_expression}")
        
        # Register the pipeline
        pipeline_instance = test_pipeline.with_options(schedule=schedule)
        run = pipeline_instance.run()
        
        print(f"✓ Schedule created: {schedule.name}")
        print(f"  Pipeline run ID: {run.id}")
        
        # Wait for the scheduled time plus a small buffer
        wait_time = (run_time - datetime.datetime.now(datetime.timezone.utc)).total_seconds() + 120
        print(f"Waiting {wait_time:.0f} seconds for scheduled run...")
        time.sleep(wait_time)
        
        # Check if the run happened
        runs = client.list_pipeline_runs(
            pipeline_name_or_id=test_pipeline.name,
            sort_by="created",
            descending=True
        )
        
        if len(runs.items) > 1:  # More than the initial run
            print(f"✓ Schedule executed successfully")
        else:
            print(f"✗ Schedule did not execute")
        
        # Clean up
        print("Cleaning up test resources...")
        client.delete_schedule(schedule.name)
        print(f"✓ Test schedule deleted")
        
    except Exception as e:
        print(f"Test failed: {e}")
```

#### Orchestrator-specific diagnostic commands

Here are some orchestrator-specific diagnostic commands to add to your troubleshooting toolkit:

**Kubeflow**:
```bash
# Check Kubeflow pipeline status
kubectl get workflows -n kubeflow
kubectl get recurringruns -n kubeflow
kubectl describe recurringrun <NAME> -n kubeflow
kubectl get pods -n kubeflow --sort-by=.metadata.creationTimestamp
```

**Vertex AI**:
```bash
# Check Vertex AI pipeline executions
gcloud ai pipeline-jobs list --region=us-central1 --filter="display_name:<PIPELINE_NAME>"
gcloud ai schedule list --region=us-central1 --filter="display_name:<SCHEDULE_NAME>"
```

**Airflow**:
```bash
# Check Airflow DAG status
airflow dags list
airflow dags show <DAG_ID>
airflow dags next-execution <DAG_ID>
airflow dags state <DAG_ID>
```

**Kubernetes**:
```bash
# Check Kubernetes CronJobs
kubectl get cronjobs
kubectl describe cronjob <NAME>
kubectl get jobs --sort-by=.metadata.creationTimestamp
```

By using these diagnostic tools and scripts, you can quickly identify and resolve common schedule issues, ensuring your pipeline schedules run reliably in production environments.

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
