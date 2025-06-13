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

## When NOT to use it

The Modal orchestrator may not be the best choice if:

* **You need fine-grained step isolation**: Modal runs entire pipelines in single functions by default, which means all steps share the same resources and environment. For pipelines requiring different resource configurations per step, consider the [Modal step operator](../step-operators/modal.md) instead.

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
   - `execution_mode` - How to run the pipeline
   - `timeout`, `min_containers`, `max_containers` - Performance settings

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
    execution_mode="pipeline", # or "per_step"
    timeout=3600,              # 1 hour timeout
    min_containers=1,          # Keep warm containers
    max_containers=10,         # Scale up to 10 containers
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

### Execution modes

The Modal orchestrator supports two execution modes:

1. **`pipeline` (default)**: Runs the entire pipeline in a single Modal function for minimal overhead and cost efficiency. Steps execute sequentially with no cold starts or function call overhead between them.
2. **`per_step`**: Runs each step in a separate Modal function call for granular control and debugging. Better for pipelines where steps can run in parallel or have very different resource requirements.

{% hint style="info" %}
**Resource Sharing**: Both execution modes use the same Modal function with the same resource configuration (from pipeline-level settings). The difference is whether steps run sequentially in one function call (`pipeline`) or as separate function calls (`per_step`).
{% endhint %}

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
    environment="production",  # or "staging", "dev", etc.
    workspace="my-company"
)
```

### How it works: Modal Apps and Functions

{% hint style="info" %}
**Implementation Details**

The ZenML Modal orchestrator implements pipeline execution using Modal's app and function architecture:

**Modal App Deployment**: 
- ZenML creates a persistent Modal app with a unique name that includes a time window and build checksum
- The app stays deployed and available for a configurable time period (default: 2 hours)
- Apps are automatically reused within the time window if the Docker image hasn't changed
- This eliminates the overhead of redeploying apps for consecutive pipeline runs

**Function Execution**:
- Your pipeline runs inside Modal functions within the deployed app
- In `pipeline` mode (default): The entire pipeline executes in a single function call
- In `per_step` mode: Each step runs as a separate function call within the same app
- Functions can maintain warm containers between executions for faster startup

**Container Management**:
- Modal manages container lifecycle automatically based on your `min_containers` and `max_containers` settings
- Warm containers stay ready with your Docker image loaded and dependencies installed
- Cold containers are spun up on-demand when warm containers are unavailable
{% endhint %}

### Warm containers for faster execution

Modal orchestrator uses persistent apps with warm containers to minimize cold starts:

```python
modal_settings = ModalOrchestratorSettings(
    min_containers=2,    # Keep 2 containers warm
    max_containers=20,   # Scale up to 20 containers
)

@pipeline(
    settings={
        "orchestrator": modal_settings
    }
)
def my_pipeline():
    ...
```

This ensures your pipelines start executing immediately without waiting for container initialization.

{% hint style="warning" %}
**Cost Implications and Optimization**

Understanding Modal orchestrator costs helps optimize your spend:

**Container Costs**:
- **Warm containers** (`min_containers > 0`): You pay for idle time even when pipelines aren't running
- **Cold containers**: Only pay when actually executing, but incur startup time (~30-60 seconds)
- **GPU containers**: Significantly more expensive than CPU-only containers for idle time

**App Deployment Costs**:
- **App reuse**: No additional cost when reusing apps within the time window (default: 2 hours)
- **New deployments**: Small deployment overhead for each new app (new time window or changed Docker image)

**Execution Mode Costs**:
- **Pipeline mode**: Most cost-effective - single function call for entire pipeline
- **Per-step mode**: Higher cost due to multiple function calls, but better for debugging

**Cost Optimization Strategies**:
- **Development**: Use `min_containers=0` to avoid idle costs
- **Production (frequent)**: Use `min_containers=1-2` for pipelines running multiple times per hour
- **Production (infrequent)**: Use `min_containers=0` for pipelines running less than once per hour
- **GPU workloads**: Be especially careful with `min_containers` due to high GPU idle costs
- **Time windows**: Adjust `app_warming_window_hours` based on your pipeline frequency

Monitor your Modal dashboard to track container utilization and costs, then adjust settings accordingly.
{% endhint %}

### App reuse and warming windows

You can control how long Modal apps stay deployed and available for reuse:

```python
modal_settings = ModalOrchestratorSettings(
    app_warming_window_hours=4.0,  # Keep apps deployed for 4 hours
    min_containers=1,              # Keep 1 container warm
    max_containers=5               # Scale up to 5 containers
)

@pipeline(settings={"orchestrator": modal_settings})
def my_pipeline():
    # This pipeline will reuse the same Modal app if run within 4 hours
    # and the Docker image hasn't changed
    ...
```

**App Reuse Benefits**:
- **Faster execution**: No app deployment time for subsequent runs
- **Cost efficiency**: No repeated deployment overhead
- **Consistent environment**: Same app instance for related pipeline runs

**When apps are recreated**:
- After the warming window expires (default: 2 hours)
- When the Docker image changes (new dependencies, code changes)
- When resource requirements change significantly

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