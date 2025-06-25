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

### Quick Start (5 minutes)

```bash
# 1. Install Modal integration
zenml integration install modal

# 2. Setup Modal authentication
modal setup

# 3. Register orchestrator and run
zenml orchestrator register modal_orch --flavor=modal --synchronous=true
zenml stack update -o modal_orch
python my_pipeline.py
```

### Full Setup Requirements

To use the Modal orchestrator, you need:

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

| Feature | Modal Step Operator | Modal Orchestrator |
|---------|-------------------|-------------------|
| **Execution Scope** | Individual steps only | Entire pipeline |
| **Orchestration** | Local ZenML | Remote Modal |
| **Resource Flexibility** | Per-step resources | Pipeline-wide resources |
| **Cost Model** | Pay per step execution | Pay per pipeline execution |
| **Setup Complexity** | Simple | Requires remote ZenML |
| **Best For** | Hybrid workflows, selective GPU usage | Full cloud execution, production |

**Quick Decision Guide**:
- **Use Step Operator**: Need GPUs for only some steps, have local data dependencies, want hybrid local/cloud workflow
- **Use Orchestrator**: Want full cloud execution, production deployment, consistent resource requirements
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
   - `execution_mode` - Execution strategy: "pipeline" (default) or "per_step"
   - `max_parallelism` - Maximum concurrent steps (for "per_step" mode)
   - `timeout` - Maximum execution time in seconds
   - `synchronous` - Wait for completion (True) or fire-and-forget (False)

{% hint style="info" %}
**GPU Configuration**: Use `ResourceSettings.gpu_count` to specify how many GPUs you need, and `ModalOrchestratorSettings.gpu` to specify what type of GPU. Modal will combine these automatically (e.g., `gpu_count=2` + `gpu="A100"` becomes `"A100:2"`).
{% endhint %}

### Configuration Examples

**Simple Configuration (Recommended):**

```python
from zenml.integrations.modal.flavors.modal_orchestrator_flavor import (
    ModalOrchestratorSettings
)

# Simple GPU pipeline
@pipeline(
    settings={
        "orchestrator": ModalOrchestratorSettings(gpu="A100")
    }
)
def my_gpu_pipeline():
    # Your pipeline steps here
    ...
```

**Advanced Configuration:**

```python
from zenml.integrations.modal.flavors.modal_orchestrator_flavor import (
    ModalOrchestratorSettings
)
from zenml.config import ResourceSettings

# Configure Modal-specific settings
modal_settings = ModalOrchestratorSettings(
    gpu="A100",                     # GPU type (optional)
    region="us-east-1",             # Preferred region
    cloud="aws",                    # Cloud provider
    modal_environment="production", # Modal environment name
    execution_mode="pipeline",      # "pipeline" (default) or "per_step"
    max_parallelism=3,              # Max concurrent steps (per_step mode)
    timeout=3600,                   # 1 hour timeout
    synchronous=True,               # Wait for completion
)

# Configure hardware resources (quantities)
resource_settings = ResourceSettings(
    cpu_count=16,                   # Number of CPU cores
    memory="32GB",                  # 32GB RAM
    gpu_count=1                     # Number of GPUs
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
**Resource Configuration by Execution Mode**:

**Pipeline Mode**: All steps share the same resources configured at the pipeline level. Configure resources at the `@pipeline` level for best results.

**Per-Step Mode**: Each step can have its own resource configuration! You can mix different GPUs, CPU, and memory settings across steps. Pipeline-level settings serve as defaults that individual steps can override.

**Resource Fallback Behavior**: If no pipeline-level resource settings are provided, the orchestrator will automatically use the highest resource requirements found across all steps in the pipeline.
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

### Execution Modes

The Modal orchestrator supports two execution modes:

#### Pipeline Mode (Default - Recommended)

```python
modal_settings = ModalOrchestratorSettings(
    execution_mode="pipeline",  # Execute entire pipeline in one sandbox
    gpu="A100"
)
```

**Benefits:**
- **Fastest execution**: Entire pipeline runs in single sandbox
- **Cost-effective**: Minimal overhead and resource usage
- **Simple**: All steps share same environment and resources

**Best for:** Most ML pipelines, production workloads, cost optimization

#### Per-Step Mode (Advanced)

```python
modal_settings = ModalOrchestratorSettings(
    execution_mode="per_step",  # Execute each step in separate sandbox
    max_parallelism=3,          # Run up to 3 steps concurrently
    gpu="T4"                    # Default GPU for steps (can be overridden per step)
)
```

**Benefits:**
- **Granular control**: Each step runs in isolated sandbox with its own resources
- **Parallel execution**: Steps can run concurrently based on dependencies  
- **Step-specific resources**: Each step can have different CPU, memory, GPU configurations
- **Resource optimization**: Use expensive GPUs only for steps that need them

**Best for:** Complex pipelines with varying resource needs, debugging individual steps, cost optimization

**Per-Step Resource Configuration:**
In per-step mode, you can configure different resources for each step, enabling powerful resource optimization:

```python
@pipeline(
    settings={
        "orchestrator": ModalOrchestratorSettings(
            execution_mode="per_step",
            max_parallelism=2,
            gpu="T4"  # Default GPU for steps
        )
    }
)
def mixed_resource_pipeline():
    # Light preprocessing - no GPU needed
    preprocess_data()
    
    # Heavy training - needs A100 GPU
    train_model()
    
    # Evaluation - T4 GPU sufficient
    evaluate_model()

@step(
    settings={
        "resources": ResourceSettings(cpu_count=2, memory="4GB")  # CPU-only step
    }
)
def preprocess_data():
    # Light CPU work - no GPU, saves costs
    pass

@step(
    settings={
        "orchestrator": ModalOrchestratorSettings(gpu="A100"),  # Override to A100
        "resources": ResourceSettings(gpu_count=1, memory="32GB")
    }
)
def train_model():
    # Heavy training with A100 GPU and 32GB RAM
    pass

@step(
    settings={
        "resources": ResourceSettings(gpu_count=1, memory="16GB")  # Uses pipeline default T4
    }
)
def evaluate_model():
    # Evaluation with T4 GPU and 16GB RAM
    pass
```

**Key Benefits of Per-Step Resource Configuration:**
- **Cost optimization**: Use expensive GPUs (A100, H100) only for steps that need them
- **Resource efficiency**: Match CPU/memory to actual step requirements  
- **Parallel execution**: Steps with different resources can run concurrently
- **Flexibility**: Each step gets exactly the resources it needs

### Sandbox Architecture

The Modal orchestrator uses a simplified sandbox-based architecture:

- **Persistent apps per pipeline**: Each pipeline gets its own Modal app that stays alive
- **Dynamic sandboxes for execution**: Each pipeline run creates fresh sandboxes for complete isolation
- **Built-in output streaming**: Modal automatically handles log streaming and output capture
- **Maximum flexibility**: Sandboxes can execute arbitrary commands and provide better isolation

This architecture provides optimal benefits:
- **Simplicity**: No complex app deployment or time window management
- **Flexibility**: Sandboxes offer more dynamic execution capabilities
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

**Examples of GPU configurations:**

```python
# Simple GPU pipeline (recommended)
@pipeline(
    settings={
        "orchestrator": ModalOrchestratorSettings(
            gpu="A100",
            execution_mode="pipeline"  # Default: entire pipeline in one sandbox
        ),
        "resources": ResourceSettings(gpu_count=1)
    }
)
def simple_gpu_pipeline():
    # All steps run in same sandbox with 1x A100 GPU
    step_one()
    step_two()

# Per-step execution with multiple GPUs
@pipeline(
    settings={
        "orchestrator": ModalOrchestratorSettings(
            gpu="A100",
            execution_mode="per_step",  # Each step in separate sandbox
            max_parallelism=2           # Run up to 2 steps concurrently
        ),
        "resources": ResourceSettings(gpu_count=4)
    }
)
def multi_gpu_pipeline():
    # Each step runs in separate sandbox with 4x A100 GPUs
    training_step()     # Sandbox 1: 4x A100
    evaluation_step()   # Sandbox 2: 4x A100 (can run in parallel)
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

### Cost Optimization

{% hint style="warning" %}
**Understanding Modal Costs**

**Execution Model**:
- **Pay-per-use**: You only pay when sandboxes are actively running
- **No idle costs**: Persistent apps don't incur costs when not executing
- **Resource-based pricing**: Cost depends on CPU, memory, and GPU usage

**Execution Mode Impact**:
- **Pipeline mode**: Most cost-effective - single sandbox for entire pipeline
- **Per-step mode**: Higher overhead - separate sandbox per step, but enables parallelism

**Cost Examples (approximate)**:
```python
# Cost-effective: Pipeline mode
# Single A100 GPU for 30-minute pipeline = ~$0.80
ModalOrchestratorSettings(execution_mode="pipeline", gpu="A100")

# Higher cost: Per-step mode
# A100 GPU per step (5 steps × 6 min each) = ~$0.80
# But steps can run in parallel, reducing total time
ModalOrchestratorSettings(execution_mode="per_step", gpu="A100")
```

**Cost Optimization Strategies**:
- **Use pipeline mode** for most workloads (fastest, cheapest)
- **Right-size resources**: Don't use A100s for simple preprocessing
- **Optimize pipeline execution time** to reduce sandbox runtime
- **Choose efficient regions** close to your data sources
- **Set appropriate timeouts** to avoid runaway costs

Monitor your Modal dashboard to track sandbox execution time and resource usage.
{% endhint %}


## Best practices

1. **Start with pipeline mode**: The default `pipeline` execution mode runs your entire pipeline in one sandbox, minimizing overhead and cost. Switch to `per_step` only if you need granular control.

2. **Separate resource and orchestrator settings**: Use `ResourceSettings` for hardware (CPU, memory, GPU count) and `ModalOrchestratorSettings` for Modal-specific configurations (GPU type, region, etc.).

3. **Configure appropriate timeouts**: Set realistic timeouts for your workloads:
   ```python
   modal_settings = ModalOrchestratorSettings(
       timeout=7200,  # 2 hours
       execution_mode="pipeline"  # Recommended for most cases
   )
   ```

4. **Choose execution mode based on needs**:
   - **Pipeline mode**: For production, cost optimization, simple workflows
   - **Per-step mode**: For debugging, heterogeneous resources, or parallel execution

5. **Use appropriate GPU types**: Match GPU types to your workload requirements:
   - `T4`: Inference, light training, cost-sensitive workloads
   - `A100`: Large model training, high-performance computing
   - `H100`: Latest generation, maximum performance

6. **Optimize for your execution mode**:
   - **Pipeline mode**: Optimize total pipeline runtime
   - **Per-step mode**: Set appropriate `max_parallelism` (typically 2-4)

7. **Monitor resource usage**: Use Modal's dashboard to track your resource consumption and optimize accordingly.

8. **Environment separation**: Use separate Modal environments (`dev`, `staging`, `prod`) for different deployment stages.

## Troubleshooting

### Common issues

1. **Authentication errors**:
   ```bash
   # Verify Modal setup
   modal auth show
   
   # Re-authenticate if needed
   modal setup
   ```
   
2. **Image build failures**:
   - Check Docker registry credentials in your ZenML stack
   - Verify your Docker daemon is running
   - Ensure base image compatibility with Modal's environment

3. **Resource allocation errors**:
   ```
   Error: No capacity for requested GPU type
   ```
   **Solution**: Try different regions or GPU types, or reduce `max_parallelism` in per-step mode

4. **Pipeline timeouts**:
   ```python
   # Increase timeout for long-running pipelines
   ModalOrchestratorSettings(timeout=14400)  # 4 hours
   ```

5. **Per-step mode issues**:
   - **Too many concurrent steps**: Reduce `max_parallelism`
   - **Resource conflicts**: Ensure adequate quota for parallel execution
   - **Step dependencies**: Verify your pipeline DAG allows for parallelism

### Performance troubleshooting

**Slow execution in per-step mode**:
- Reduce `max_parallelism` to avoid resource contention
- Consider switching to `pipeline` mode for better performance
- Check Modal dashboard for sandbox startup times

**Memory issues**:
- Increase memory allocation in `ResourceSettings`
- For pipeline mode: ensure total memory covers all steps
- For per-step mode: configure per-step memory requirements

### Getting help

- Check the [Modal documentation](https://modal.com/docs) for platform-specific issues
- Monitor your sandboxes in the [Modal dashboard](https://modal.com/apps)
- Use `zenml logs` to view detailed pipeline execution logs
- Check ZenML step operator docs for [hybrid workflows](../step-operators/modal.md)

For more information and a full list of configurable attributes of the Modal orchestrator, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-modal.html#zenml.integrations.modal.orchestrators).