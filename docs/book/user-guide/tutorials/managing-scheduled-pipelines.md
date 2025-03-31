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

### 2.1 Basic schedule creation

- Creating schedules via the ZenML CLI
- Schedule creation with the Python SDK
- Cron expressions and schedule intervals
- Schedule naming and management best practices

### 2.2 Orchestrator-specific schedule creation

### 2.2.1 Kubeflow schedules

- Setting up Kubeflow schedules
- Cron expression format
- Resource configuration
- Limitations and considerations

### 2.2.2 Vertex AI schedules

- Creating schedules on Vertex AI
- Schedule configuration options
- Authentication and permissions
- Monitoring Vertex schedules

### 2.2.3 Airflow schedules

- Implementing Airflow schedules
- DAG configuration
- Schedule parameters
- Airflow-specific features

### 2.2.4 Other orchestrators

- Schedule support in other orchestrators
- Limitations and workarounds
- Future schedule support roadmap

## 3. Managing existing schedules

### 3.1 Viewing and monitoring schedules

- Listing schedules with ZenML CLI
- Viewing schedules in the dashboard
- Checking schedule status
- Monitoring schedule execution history

### 3.2 Updating schedules

- The challenge with schedule updates
- Why direct orchestrator interaction is often needed
- Update patterns for different orchestrators
- Best practices for schedule maintenance

### 3.3 Deleting schedules

- ZenML schedule deletion
- Why orchestrator schedules may remain
- Direct deletion from orchestratorsoh sorry
- Complete cleanup process

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
