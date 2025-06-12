---
description: Orchestrating your pipelines to run on Modal's serverless cloud platform.
---

# Modal Orchestrator

Using the ZenML `modal` integration, you can orchestrate and scale your ML pipelines on [Modal's](https://modal.com/) serverless cloud platform with minimal setup and maximum efficiency.

The Modal orchestrator is designed for speed and cost-effectiveness, running entire pipelines in single serverless functions to minimize cold starts and optimize resource utilization.

{% hint style="warning" %}
This component is only meant to be used within the context of a [remote ZenML deployment scenario](https://docs.zenml.io/getting-started/deploying-zenml/). Usage with a local ZenML deployment may lead to unexpected behavior!
{% endhint %}

## When to use it

You should use the Modal orchestrator if:

* you want a serverless solution that scales to zero when not in use.
* you're looking for fast pipeline execution with minimal cold start overhead.
* you want cost-effective ML pipeline orchestration without managing infrastructure.
* you need easy access to GPUs and high-performance computing resources.
* you prefer a simple setup process without complex Kubernetes configurations.

## How to deploy it

The Modal orchestrator runs on Modal's cloud infrastructure, so you don't need to deploy or manage any servers. You just need:

1. A [Modal account](https://modal.com/) (free tier available)
2. Modal CLI installed and authenticated
3. A [remote ZenML deployment](https://docs.zenml.io/getting-started/deploying-zenml/) for production use

## How to use it

To use the Modal orchestrator, we need:

* The ZenML `modal` integration installed. If you haven't done so, run:
  ```shell
  zenml integration install modal
  ```
* [Docker](https://www.docker.com) installed and running.
* A [remote artifact store](../artifact-stores/README.md) as part of your stack.
* A [remote container registry](../container-registries/README.md) as part of your stack.
* Modal CLI installed and authenticated:
  ```shell
  pip install modal
  modal setup
  ```

### Setting up the orchestrator

You can register the orchestrator with or without explicit Modal credentials:

**Option 1: Using Modal CLI authentication (recommended for development)**

```shell
# Register the orchestrator (uses Modal CLI credentials)
zenml orchestrator register <ORCHESTRATOR_NAME> \
    --flavor=modal \
    --synchronous=true

# Register and activate a stack with the new orchestrator
zenml stack register <STACK_NAME> -o <ORCHESTRATOR_NAME> ... --set
```

**Option 2: Using Modal API token (recommended for production)**

```shell
# Register the orchestrator with explicit credentials
zenml orchestrator register <ORCHESTRATOR_NAME> \
    --flavor=modal \
    --token=<MODAL_TOKEN> \
    --workspace=<MODAL_WORKSPACE> \
    --synchronous=true

# Register and activate a stack with the new orchestrator
zenml stack register <STACK_NAME> -o <ORCHESTRATOR_NAME> ... --set
```

You can get your Modal token from the [Modal dashboard](https://modal.com/settings/tokens).

{% hint style="info" %}
ZenML will build a Docker image called `<CONTAINER_REGISTRY_URI>/zenml:<PIPELINE_NAME>` which includes your code and use it to run your pipeline steps in Modal functions. Check out [this page](https://docs.zenml.io/how-to/customize-docker-builds/) if you want to learn more about how ZenML builds these images and how you can customize them.
{% endhint %}

You can now run any ZenML pipeline using the Modal orchestrator:

```shell
python file_that_runs_a_zenml_pipeline.py
```

### Modal UI

Modal provides an excellent web interface where you can monitor your pipeline runs in real-time, view logs, and track resource usage.

You can access the Modal dashboard at [modal.com/apps](https://modal.com/apps) to see your running and completed functions.

### Additional configuration

For additional configuration of the Modal orchestrator, you can pass `ModalOrchestratorSettings` which allows you to configure resource requirements, execution modes, and cloud preferences:

```python
from zenml.integrations.modal.flavors.modal_orchestrator_flavor import (
    ModalOrchestratorSettings
)

modal_settings = ModalOrchestratorSettings(
    cpu_count=16,              # Number of CPU cores
    memory_mb=32768,           # 32GB RAM
    gpu="A100",                # GPU type (optional)
    region="us-east-1",        # Preferred region
    cloud="aws",               # Cloud provider
    execution_mode="pipeline", # or "per_step"
    timeout=3600,              # 1 hour timeout
    min_containers=1,          # Keep warm containers
    max_containers=10,         # Scale up to 10 containers
)

@pipeline(
    settings={
        "orchestrator": modal_settings
    }
)
def my_modal_pipeline():
    # Your pipeline steps here
    ...
```

### Resource configuration

You can specify different resource requirements for individual steps:

```python
from zenml.config import ResourceSettings

# Configure resources for a specific step
@step(
    settings={
        "resources": ResourceSettings(
            cpu_count=8,
            memory="16GB",
            gpu_count=1
        ),
        "orchestrator": ModalOrchestratorSettings(
            gpu="T4",
            region="us-west-2"
        )
    }
)
def gpu_training_step():
    # This step will run on a GPU
    ...

@step(
    settings={
        "resources": ResourceSettings(
            cpu_count=32,
            memory="64GB"
        )
    }
)
def cpu_intensive_step():
    # This step will run with high CPU/memory
    ...

@pipeline()
def my_pipeline():
    gpu_training_step()
    cpu_intensive_step()
```

### Execution modes

The Modal orchestrator supports two execution modes:

1. **`pipeline` (default)**: Runs the entire pipeline in a single Modal function for maximum speed and cost efficiency
2. **`per_step`**: Runs each step in a separate Modal function for granular control and debugging

```python
# Fast execution (default) - entire pipeline in one function
modal_settings = ModalOrchestratorSettings(
    execution_mode="pipeline"
)

# Granular execution - each step separate (useful for debugging)
modal_settings = ModalOrchestratorSettings(
    execution_mode="per_step"
)
```

### Using GPUs

Modal makes it easy to use GPUs for your ML workloads:

```python
@step(
    settings={
        "orchestrator": ModalOrchestratorSettings(
            gpu="A100",     # or "T4", "V100", etc.
            region="us-east-1"
        ),
        "resources": ResourceSettings(
            gpu_count=1
        )
    }
)
def train_model():
    # Your GPU-accelerated training code
    import torch
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    ...
```

Available GPU types include:
- `T4` - Cost-effective for inference and light training
- `A10G` - Balanced performance for training and inference  
- `A100` - High-performance for large model training
- `H100` - Latest generation for maximum performance

### Synchronous vs Asynchronous execution

You can choose whether to wait for pipeline completion or run asynchronously:

```python
# Wait for completion (default)
modal_settings = ModalOrchestratorSettings(
    synchronous=True
)

# Fire-and-forget execution
modal_settings = ModalOrchestratorSettings(
    synchronous=False
)
```

### Authentication with different environments

For production deployments, you can specify different Modal environments:

```python
modal_settings = ModalOrchestratorSettings(
    environment="production",  # or "staging", "dev", etc.
    workspace="my-company"
)
```

### Warm containers for faster execution

Modal orchestrator uses persistent apps with warm containers to minimize cold starts:

```python
modal_settings = ModalOrchestratorSettings(
    min_containers=2,    # Keep 2 containers warm
    max_containers=20,   # Scale up to 20 containers
)
```

This ensures your pipelines start executing immediately without waiting for container initialization.

## Best practices

1. **Use pipeline mode for production**: The default `pipeline` execution mode runs your entire pipeline in one function, minimizing overhead and cost.

2. **Configure appropriate timeouts**: Set realistic timeouts for your workloads:
   ```python
   modal_settings = ModalOrchestratorSettings(
       timeout=7200  # 2 hours
   )
   ```

3. **Choose the right region**: Select regions close to your data sources to minimize transfer costs and latency.

4. **Use appropriate GPU types**: Match GPU types to your workload requirements - don't use A100s for simple inference tasks.

5. **Monitor resource usage**: Use Modal's dashboard to track your resource consumption and optimize accordingly.

## Troubleshooting

### Common issues

1. **Authentication errors**: Ensure your Modal token is correctly configured and has the necessary permissions.

2. **Image build failures**: Check that your Docker registry credentials are properly configured in your ZenML stack.

3. **Resource limits**: If you hit resource limits, consider breaking large steps into smaller ones or requesting quota increases from Modal.

4. **Network timeouts**: For long-running steps, ensure your timeout settings are appropriate.

### Getting help

- Check the [Modal documentation](https://modal.com/docs) for platform-specific issues
- Monitor your functions in the [Modal dashboard](https://modal.com/apps)
- Use `zenml logs` to view detailed pipeline execution logs

For more information and a full list of configurable attributes of the Modal orchestrator, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-modal.html#zenml.integrations.modal.orchestrators).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>