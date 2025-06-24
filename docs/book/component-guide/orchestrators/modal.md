---
description: Orchestrating your pipelines to run on Modal's serverless cloud platform.
---

# Modal Orchestrator

Using the ZenML `modal` integration, you can orchestrate and scale your ML pipelines on [Modal's](https://modal.com/) serverless cloud platform with minimal setup and maximum efficiency.

The Modal orchestrator is designed for speed and cost-effectiveness, running entire pipelines using Modal sandboxes with persistent app architecture for maximum flexibility and efficiency.

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

## When NOT to use it

The Modal orchestrator may not be the best choice if:

* **You need fine-grained step isolation**: Modal orchestrator runs entire pipelines in single sandboxes, which means all steps share the same resources and environment. For pipelines requiring different resource configurations per step, consider the [Modal step operator](../step-operators/modal.md) instead.

* **You have strict data locality requirements**: Modal runs in specific cloud regions and may not be suitable if you need to keep data processing within specific geographic boundaries or on-premises.

* **You require very long-running pipelines**: While Modal supports up to 24-hour timeouts, extremely long-running batch jobs (days/weeks) might be better suited for other orchestrators.

* **You need complex workflow patterns**: Modal orchestrator is optimized for straightforward ML pipelines. If you need complex DAG patterns, conditional logic, or dynamic pipeline generation, other orchestrators might be more suitable.

* **Cost optimization for infrequent workloads**: While Modal is cost-effective for regular workloads, very infrequent pipelines (running once per month) might benefit from traditional infrastructure that doesn't incur per-execution overhead.

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
* Modal authenticated:
  ```shell
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
    --token-id=<MODAL_TOKEN_ID> \
    --token-secret=<MODAL_TOKEN_SECRET> \
    --workspace=<MODAL_WORKSPACE> \
    --synchronous=true

# Register and activate a stack with the new orchestrator
zenml stack register <STACK_NAME> -o <ORCHESTRATOR_NAME> ... --set
```

You can get your Modal token from the [Modal dashboard](https://modal.com/settings/tokens).

{% hint style="info" %}
ZenML will build a Docker image called `<CONTAINER_REGISTRY_URI>/zenml:<PIPELINE_NAME>` which includes your code and use it to run your pipeline steps in Modal functions. Check out [this page](https://docs.zenml.io/concepts/containerization) if you want to learn more about how ZenML builds these images and how you can customize them.
{% endhint %}

You can now run any ZenML pipeline using the Modal orchestrator:

```shell
python file_that_runs_a_zenml_pipeline.py
```

### Modal UI

Modal provides an excellent web interface where you can monitor your pipeline runs in real-time, view logs, and track resource usage.

You can access the Modal dashboard at [modal.com/apps](https://modal.com/apps) to see your running and completed functions.

### Configuration overview

{% hint style="info" %}
**Modal Orchestrator vs Step Operator**

ZenML offers both a [Modal orchestrator](modal.md) and a [Modal step operator](../step-operators/modal.md). Choose based on your needs:

- **Modal Orchestrator**: Runs entire pipelines on Modal's infrastructure. Best for complete pipeline execution with consistent resource requirements.
- **Modal Step Operator**: Runs individual steps on Modal while keeping orchestration local. Best for selectively running compute-intensive steps (like training) on Modal while keeping other steps local.

Use the orchestrator for full cloud execution, use the step operator for hybrid local/cloud workflows.
{% endhint %}

The Modal orchestrator uses two types of settings following ZenML's standard pattern:

1. **`ResourceSettings`** (standard ZenML) - for hardware resource quantities:
   - `cpu_count` - Number of CPU cores
   - `memory` - Memory allocation (e.g., "16GB")
   - `gpu_count` - Number of GPUs to allocate

2. **`ModalOrchestratorSettings`** (Modal-specific) - for Modal platform configuration:
   - `gpu` - GPU type specification (e.g., "T4", "A100", "H100")
   - `region` - Cloud region preference  
   - `cloud` - Cloud provider selection
   - `modal_environment` - Modal environment name (e.g., "main", "dev", "prod")
   - `timeout`, `min_containers`, `max_containers` - Performance settings
   - `synchronous` - Wait for completion (True) or fire-and-forget (False)

{% hint style="info" %}
**GPU Configuration**: Use `ResourceSettings.gpu_count` to specify how many GPUs you need, and `ModalOrchestratorSettings.gpu` to specify what type of GPU. Modal will combine these automatically (e.g., `gpu_count=2` + `gpu="A100"` becomes `"A100:2"`).
{% endhint %}

### Additional configuration

Here's how to configure both types of settings:

```python
from zenml.integrations.modal.flavors.modal_orchestrator_flavor import (
    ModalOrchestratorSettings
)
from zenml.config import ResourceSettings

# Configure Modal-specific settings
modal_settings = ModalOrchestratorSettings(
    gpu="A100",                # GPU type (optional)
    region="us-east-1",        # Preferred region
    cloud="aws",               # Cloud provider
    modal_environment="main",  # Modal environment name
    timeout=3600,              # 1 hour timeout
    min_containers=1,          # Keep warm containers
    max_containers=10,         # Scale up to 10 containers
    synchronous=True,          # Wait for completion
)

# Configure hardware resources (quantities)
resource_settings = ResourceSettings(
    cpu_count=16,              # Number of CPU cores
    memory="32GB",             # 32GB RAM
    gpu_count=1                # Number of GPUs (combined with gpu type below)
)

@pipeline(
    settings={
        "orchestrator": modal_settings,
        "resources": resource_settings
    }
)
def my_modal_pipeline():
    # Your pipeline steps here
    ...
```

### Resource configuration

{% hint style="info" %}
**Pipeline-Level Resources**: The Modal orchestrator uses pipeline-level resource settings to configure the Modal function for the entire pipeline. All steps share the same Modal function resources. Configure resources at the `@pipeline` level for best results.

**Resource Fallback Behavior**: If no pipeline-level resource settings are provided, the orchestrator will automatically use the highest resource requirements found across all steps in the pipeline. This ensures adequate resources for all steps while maintaining the single-function execution model.
{% endhint %}

You can configure pipeline-wide resource requirements using `ResourceSettings` for hardware resources and `ModalOrchestratorSettings` for Modal-specific configurations:

```python
from zenml.config import ResourceSettings
from zenml.integrations.modal.flavors.modal_orchestrator_flavor import (
    ModalOrchestratorSettings
)

# Configure resources at the pipeline level (recommended)
@pipeline(
    settings={
        "resources": ResourceSettings(
            cpu_count=16,
            memory="32GB", 
            gpu_count=1        # These resources apply to the entire pipeline
        ),
        "orchestrator": ModalOrchestratorSettings(
            gpu="A100",        # GPU type for the entire pipeline
            region="us-west-2"
        )
    }
)
def my_pipeline():
    first_step()   # Runs with pipeline resources: 16 CPU, 32GB RAM, 1x A100
    second_step()  # Runs with same resources: 16 CPU, 32GB RAM, 1x A100
    ...

@step
def first_step():
    # Uses pipeline-level resource configuration
    ...

@step
def second_step():
    # Uses same pipeline-level resource configuration
    ...
```

### Sandbox Architecture

The Modal orchestrator uses a simplified sandbox-based architecture:

- **Persistent apps per pipeline**: Each pipeline gets its own Modal app that stays alive
- **Dynamic sandboxes for execution**: Each pipeline run creates a fresh sandbox for complete isolation
- **Built-in output streaming**: Modal automatically handles log streaming and output capture
- **Maximum flexibility**: Sandboxes can execute arbitrary commands and provide better isolation

This architecture provides optimal benefits:
- **Simplicity**: No complex app deployment or time window management
- **Flexibility**: Sandboxes offer more dynamic execution capabilities than functions
- **Isolation**: Each run gets a completely fresh execution environment
- **Performance**: Persistent apps eliminate deployment overhead

### Base image requirements

{% hint style="info" %}
**Docker Image Customization**

ZenML will automatically build a Docker image that includes your code and dependencies, then use it to run your pipeline on Modal. The base image and dependencies you configure will determine what's available in your Modal execution environment.

Key considerations:
- **Base image**: Choose an appropriate base image for your workload (e.g., `python:3.9-slim`, `ubuntu:20.04`, or specialized ML images)
- **Dependencies**: Ensure all required packages are specified in your `requirements.txt` or Docker settings
- **System packages**: If you need system-level packages, configure them in your Docker settings
- **Environment variables**: Configure any necessary environment variables in your ZenML pipeline or Docker settings

Check out the [ZenML Docker customization guide](https://docs.zenml.io/how-to/customize-docker-builds) for detailed information on customizing your execution environment.
{% endhint %}

### Using GPUs

Modal makes it easy to use GPUs for your ML workloads. Use `ResourceSettings` to specify the number of GPUs and `ModalOrchestratorSettings` to specify the GPU type:

{% hint style="warning" %}
**Base Image Requirements for GPU Usage**

When using GPUs, ensure your base Docker image includes the appropriate CUDA runtime and drivers. Modal's GPU instances come with CUDA pre-installed, but your application dependencies (like PyTorch, TensorFlow) must be compatible with the CUDA version.

For optimal GPU performance:
- Use CUDA-compatible base images (e.g., `nvidia/cuda:11.8-runtime-ubuntu20.04`)
- Install GPU-compatible versions of ML frameworks in your Docker requirements
- Test your GPU setup locally before deploying to Modal

ZenML will use your base image configuration from the container registry, so ensure GPU compatibility is built into your image.
{% endhint %}

```python
from zenml.config import ResourceSettings
from zenml.integrations.modal.flavors.modal_orchestrator_flavor import (
    ModalOrchestratorSettings
)

@step(
    settings={
        "resources": ResourceSettings(
            gpu_count=1        # Number of GPUs to allocate
        ),
        "orchestrator": ModalOrchestratorSettings(
            gpu="A100",        # GPU type: "T4", "A10G", "A100", "H100"
            region="us-east-1"
        )
    }
)
def train_model():
    # Your GPU-accelerated training code
    # Modal will provision 1x A100 GPU (gpu_count=1 + gpu="A100")
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

**Examples of GPU configurations (applied to entire pipeline):**

```python
# Pipeline with GPU - configure on first step or pipeline level
@pipeline(
    settings={
        "resources": ResourceSettings(gpu_count=1),
        "orchestrator": ModalOrchestratorSettings(gpu="A100")
    }
)
def gpu_pipeline():
    # All steps in this pipeline will have access to 1x A100 GPU
    step_one()
    step_two()

# Multiple GPUs - configure at pipeline level
@pipeline(
    settings={
        "resources": ResourceSettings(gpu_count=4),
        "orchestrator": ModalOrchestratorSettings(gpu="A100")
    }
)
def multi_gpu_pipeline():
    # All steps in this pipeline will have access to 4x A100 GPUs
    training_step()
    evaluation_step()
```

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

{% hint style="info" %}
**Best Practice: Separate Stacks for Different Environments**

Consider creating separate ZenML stacks for different environments (development, staging, production), each configured with different Modal environments and workspaces. This provides better isolation and allows for different resource configurations per environment.

For example:
- **Development stack**: Uses Modal "dev" environment with smaller resource limits
- **Production stack**: Uses Modal "production" environment with production-grade resources and credentials

This approach helps prevent accidental deployment to production and allows for environment-specific configurations.
{% endhint %}

For production deployments, you can specify different Modal environments:

```python
modal_settings = ModalOrchestratorSettings(
    modal_environment="production",  # or "staging", "dev", etc.
    workspace="my-company"
)
```

### How it works: Persistent Apps + Dynamic Sandboxes

{% hint style="info" %}
**Simplified Architecture for Maximum Flexibility**

The ZenML Modal orchestrator uses a streamlined "Persistent Apps + Dynamic Sandboxes" architecture:

**Persistent Pipeline Apps**: 
- Each pipeline gets its own persistent Modal app (e.g., `zenml-pipeline-training-pipeline`)
- Apps stay alive across multiple runs using `modal.App.lookup(create_if_missing=True)`
- No complex time windows or deployment logic - truly persistent

**Dynamic Execution Sandboxes**:
- Each pipeline run creates a fresh Modal sandbox for complete isolation
- Sandboxes execute arbitrary commands with maximum flexibility
- Built-in output streaming via `modal.enable_output()`
- Fresh execution environment prevents any conflicts between runs

**Execution Flow**:
- Your entire pipeline runs in a single sandbox using `PipelineEntrypoint`
- Simple app lookup or creation, then sandbox execution
- Automatic log streaming and output capture
- Complete isolation between different pipeline runs

**Benefits**:
- **Simplicity**: No complex app deployment or reuse logic
- **Flexibility**: Sandboxes can execute any commands dynamically
- **Isolation**: Each run gets completely fresh execution context
- **Performance**: Persistent apps eliminate deployment overhead
{% endhint %}

### Fast execution with persistent apps

Modal orchestrator uses persistent apps to minimize startup overhead:

```python
modal_settings = ModalOrchestratorSettings(
    region="us-east-1",           # Preferred region
    cloud="aws",                  # Cloud provider  
    modal_environment="main",     # Modal environment
    timeout=3600,                 # 1 hour timeout
)

@pipeline(
    settings={
        "orchestrator": modal_settings
    }
)
def my_pipeline():
    ...
```

This ensures your pipelines start executing quickly by reusing persistent apps and creating fresh sandboxes for isolation.

{% hint style="warning" %}
**Cost Implications and Optimization**

Understanding Modal orchestrator costs with sandbox architecture:

**Execution Costs**:
- **Pay-per-use**: You only pay when sandboxes are actively running
- **No idle costs**: Persistent apps don't incur costs when not executing
- **Sandbox overhead**: Minimal - sandboxes start quickly on persistent apps

**Resource Optimization**:
- **GPU usage**: Only allocated during actual pipeline execution
- **Memory and CPU**: Charged only for sandbox execution time
- **Storage**: Docker images are cached across runs on persistent apps

**Cost Optimization Strategies**:
- **Efficient pipelines**: Optimize pipeline execution time to reduce costs
- **Right-size resources**: Use appropriate CPU/memory/GPU for your workload
- **Regional selection**: Choose regions close to your data sources
- **Timeout management**: Set appropriate timeouts to avoid runaway costs

Monitor your Modal dashboard to track sandbox execution time and resource usage for cost optimization.
{% endhint %}


## Best practices

1. **Use pipeline mode for production**: The default `pipeline` execution mode runs your entire pipeline in one function, minimizing overhead and cost.

2. **Separate resource and orchestrator settings**: Use `ResourceSettings` for hardware (CPU, memory, GPU count) and `ModalOrchestratorSettings` for Modal-specific configurations (GPU type, region, etc.).

3. **Configure appropriate timeouts**: Set realistic timeouts for your workloads:
   ```python
   modal_settings = ModalOrchestratorSettings(
       timeout=7200  # 2 hours
   )
   ```

4. **Choose the right region**: Select regions close to your data sources to minimize transfer costs and latency.

5. **Use appropriate GPU types**: Match GPU types to your workload requirements - don't use A100s for simple inference tasks.

6. **Monitor resource usage**: Use Modal's dashboard to track your resource consumption and optimize accordingly.

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