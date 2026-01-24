---
description: Orchestrating your pipelines to run on Run:AI clusters with fractional GPU support.
---

# Run:AI Orchestrator

[Run:AI](https://www.run.ai/) is an AI workload orchestration and management platform that enables efficient GPU resource sharing and allocation. The Run:AI orchestrator is an [orchestrator](./) flavor that allows you to easily deploy your ZenML pipelines on Run:AI clusters with support for fractional GPU allocation.

{% hint style="warning" %}
This component is only meant to be used within the context of a [remote ZenML deployment scenario](https://docs.zenml.io/getting-started/deploying-zenml/). Usage with a local ZenML deployment may lead to unexpected behavior!
{% endhint %}

### When to use it

You should use the Run:AI orchestrator if:

* you need to run ML workloads with fractional GPU allocation (e.g., 0.5 GPU per job).
* you're looking for efficient GPU resource sharing across multiple workloads.
* you're already using Run:AI for workload management.
* you want to leverage Run:AI's scheduling and resource management features.

### Key Features

* **Fractional GPU Support**: Allocate portions of a GPU (e.g., 0.25, 0.5, 0.75) to maximize resource utilization
* **Training Workloads**: Submit ZenML pipelines as Run:AI training workloads
* **Project-based Resource Management**: Workloads are organized by Run:AI projects with quota policies
* **SaaS and Self-hosted**: Works with both Run:AI SaaS and self-hosted deployments
* **Workload Monitoring**: Track pipeline execution status through Run:AI API

### Prerequisites

You will need to do the following to start using the Run:AI orchestrator:

* Have access to a Run:AI cluster (SaaS or self-hosted)
* Create a Run:AI project with sufficient resource quota
* Generate Run:AI API credentials (client ID and secret):
  * Navigate to Run:AI control plane → Settings → Applications
  * Create a new application to obtain client credentials
* Have a ZenML stack with:
  * A container registry (for storing pipeline images)
  * An artifact store (for storing pipeline outputs)
  * An image builder (for building pipeline containers)

## How it works

The Run:AI orchestrator works by submitting ZenML pipelines as Run:AI training workloads through the Run:AI API. For each pipeline run, it:

1. Builds a Docker image containing your pipeline code and dependencies
2. Submits a training workload to your specified Run:AI project
3. Configures compute resources (GPUs, CPUs, memory) based on your settings
4. Monitors the workload status and reports back to ZenML

The orchestrator uses the `runapy` Python client library to interact with the Run:AI control plane API, handling authentication, workload submission, and status monitoring automatically.

### Fractional GPU Allocation

One of the key benefits of Run:AI is fractional GPU support. You can configure this in your pipeline settings:

```python
from zenml.integrations.runai.flavors.runai_orchestrator_flavor import RunAIOrchestratorSettings

# Request half a GPU
settings = RunAIOrchestratorSettings(
    gpu_devices_request=1,
    gpu_portion_request=0.5,  # 0.5 = half GPU
    gpu_request_type="portion",
    cpu_core_request=2.0,
    cpu_memory_request="4G",
)

@pipeline(settings={"orchestrator": settings})
def my_pipeline():
    ...
```

## How to deploy it

### Step 1: Install the Run:AI integration

```shell
zenml integration install runai
# Or install with pip
pip install "zenml[runai]"
```

### Step 2: Register the Run:AI orchestrator

```shell
zenml orchestrator register <ORCHESTRATOR_NAME> \
    --flavor=runai \
    --client_id=<YOUR_CLIENT_ID> \
    --client_secret=<YOUR_CLIENT_SECRET> \
    --runai_base_url=<YOUR_RUNAI_URL> \
    --project_name=<YOUR_PROJECT_NAME>
```

For example, with a SaaS deployment:

```shell
zenml orchestrator register my_runai_orchestrator \
    --flavor=runai \
    --client_id=abc123 \
    --client_secret=secret456 \
    --runai_base_url=https://my-org.run.ai \
    --project_name=ml-team
```

### Step 3: Register and activate a stack with the orchestrator

```shell
zenml stack register <STACK_NAME> \
    -o <ORCHESTRATOR_NAME> \
    -a <ARTIFACT_STORE> \
    -c <CONTAINER_REGISTRY> \
    -i <IMAGE_BUILDER> \
    --set
```

## How to use it

Once you have registered the Run:AI orchestrator and added it to your active stack, you can run any ZenML pipeline using it:

```python
from zenml import pipeline, step

@step
def train_model() -> None:
    # Your training code here
    print("Training model on Run:AI!")

@pipeline
def training_pipeline():
    train_model()

if __name__ == "__main__":
    training_pipeline()
```

### Configuring GPU resources

You can configure GPU allocation at the pipeline or step level:

```python
from zenml.integrations.runai.flavors.runai_orchestrator_flavor import RunAIOrchestratorSettings

# Configure at pipeline level (applies to all steps)
@pipeline(
    settings={
        "orchestrator": RunAIOrchestratorSettings(
            gpu_devices_request=1,
            gpu_portion_request=0.5,  # Half GPU
            gpu_request_type="portion",
            cpu_core_request=2.0,
            cpu_memory_request="8G",
        )
    }
)
def my_pipeline():
    training_step()

# Or configure per step
@step(
    settings={
        "orchestrator": RunAIOrchestratorSettings(
            gpu_devices_request=2,  # 2 full GPUs
            gpu_request_type="device",
            cpu_core_request=4.0,
            cpu_memory_request="16G",
        )
    }
)
def heavy_training_step():
    # This step gets 2 full GPUs
    pass
```

### Configuration options

The Run:AI orchestrator supports the following configuration options:

#### Orchestrator Configuration (set during registration)

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `client_id` | str | Yes | Run:AI client ID for API authentication |
| `client_secret` | str | Yes | Run:AI client secret for API authentication |
| `runai_base_url` | str | Yes | Run:AI control plane URL (e.g., `https://org.run.ai`) |
| `project_name` | str | Yes | Run:AI project name for workload submission |
| `cluster_name` | str | No | Run:AI cluster name (uses first available if not specified) |
| `monitoring_interval` | float | No | Interval in seconds to poll workload status (default: 30) |
| `workload_timeout` | int | No | Maximum time in seconds for workload completion (no limit if not set) |

#### Step/Pipeline Settings

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `synchronous` | bool | True | Whether to wait for pipeline completion |
| `gpu_devices_request` | int | 1 | Number of GPUs to request |
| `gpu_portion_request` | float | 1.0 | Fractional GPU allocation (0.0-1.0) |
| `gpu_request_type` | str | "portion" | GPU allocation method: "portion" or "device" |
| `cpu_core_request` | float | 1.0 | Number of CPU cores to request |
| `cpu_memory_request` | str | "4G" | Memory to request (e.g., "4G", "512M", "8Gi") |
| `environment_variables` | dict | {} | Additional environment variables |
| `workload_type` | str | "training" | Workload type: "training" or "inference" (experimental) |

### Examples

#### Example 1: Training with fractional GPU

```python
from zenml import pipeline, step
from zenml.integrations.runai.flavors.runai_orchestrator_flavor import RunAIOrchestratorSettings

@step(
    settings={
        "orchestrator": RunAIOrchestratorSettings(
            gpu_portion_request=0.25,  # Quarter GPU
            gpu_request_type="portion",
            cpu_core_request=1.0,
            cpu_memory_request="4G",
        )
    }
)
def light_training():
    # Train a small model with 1/4 GPU
    pass

@pipeline
def efficient_pipeline():
    light_training()
```

#### Example 2: Heavy training with multiple GPUs

```python
@step(
    settings={
        "orchestrator": RunAIOrchestratorSettings(
            gpu_devices_request=4,  # 4 full GPUs
            gpu_request_type="device",
            cpu_core_request=16.0,
            cpu_memory_request="64G",
        )
    }
)
def distributed_training():
    # Train a large model with 4 full GPUs
    pass
```

#### Example 3: CPU-only workload

```python
@step(
    settings={
        "orchestrator": RunAIOrchestratorSettings(
            gpu_devices_request=0,  # No GPU
            cpu_core_request=8.0,
            cpu_memory_request="32G",
        )
    }
)
def data_preprocessing():
    # CPU-intensive data processing
    pass
```

### Troubleshooting

#### Common Issues

**Issue: "Project not found in Run:AI"**
- Ensure the project name exactly matches your Run:AI project
- Verify you have access to the project with your credentials

**Issue: "Failed to submit Run:AI workload"**
- Check that your client ID and secret are correct
- Verify your Run:AI base URL is accessible
- Ensure your project has sufficient resource quota

**Issue: "runapy package not found"**
- Install the Run:AI integration: `zenml integration install runai`

#### Viewing Logs

Run:AI workload logs can be viewed in the Run:AI control plane UI:
1. Navigate to your Run:AI control plane
2. Go to Workloads → Training
3. Find your pipeline workload and click to view logs

## Limitations

The current MVP implementation has the following limitations:

* **Step isolation**: All steps run in a single Run:AI workload (no per-step workload isolation)
* **Inference workloads**: Experimental support only
* **Service connectors**: Not yet integrated with ZenML service connectors
* **Advanced Run:AI features**: Node pools, gang scheduling not yet supported

These limitations will be addressed in future releases based on user feedback.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
