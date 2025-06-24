---
description: Executing individual steps in Modal.
---

# Modal Step Operator

[Modal](https://modal.com) is a platform for running cloud infrastructure. It offers specialized compute instances to run your code and has a fast execution time, especially around building Docker images and provisioning hardware. ZenML's Modal step operator allows you to submit individual steps to be run on Modal compute instances.

### When to use it

{% hint style="info" %}
**Modal Step Operator vs Orchestrator**

ZenML offers both a [Modal step operator](modal.md) and a [Modal orchestrator](../orchestrators/modal.md). Choose based on your needs:

- **Modal Step Operator**: Runs individual steps on Modal while keeping orchestration local. Best for selectively running compute-intensive steps (like training) on Modal while keeping other steps local.
- **Modal Orchestrator**: Runs entire pipelines on Modal's infrastructure. Best for complete pipeline execution with consistent resource requirements.

Use the step operator for hybrid local/cloud workflows, use the orchestrator for full cloud execution.
{% endhint %}

You should use the Modal step operator if:

* You want to run only specific compute-intensive steps (like training or inference) on Modal while keeping other steps local.
* You need different hardware requirements for different steps in your pipeline.
* You want to leverage Modal's fast execution and GPU access for select steps without moving your entire pipeline to the cloud.
* You have a hybrid workflow where some steps need to access local resources or data.

### When NOT to use it

The Modal step operator may not be the best choice if:

* **You want to run entire pipelines on Modal**: Use the [Modal orchestrator](../orchestrators/modal.md) instead for complete pipeline execution with better cost efficiency and reduced overhead.

* **You have simple, lightweight steps**: For steps that don't require significant compute resources, the overhead of running them on Modal may not be worth it.

* **You need very low latency**: The step operator introduces some overhead for individual step execution compared to running steps locally.

* **You have tight data locality requirements**: If your steps need to access large amounts of local data, transferring it to Modal for each step execution may be inefficient.

### How to deploy it

To use the Modal step operator:

* [Sign up for a Modal account](https://modal.com/signup) if you haven't already.
* Install the Modal CLI by running `pip install modal` (or `zenml integration install modal`) and authenticate by running `modal setup` in your terminal.

### How to use it

To use the Modal step operator, we need:

* The ZenML `modal` integration installed. If you haven't done so, run

  ```shell
  zenml integration install modal
  ```
* Docker installed and running.
* A cloud artifact store as part of your stack. This is needed so that both your
  orchestration environment and Modal can read and write step artifacts. Any
  cloud artifact store supported by ZenML will work with Modal.
* A cloud container registry as part of your stack. Any cloud container
  registry supported by ZenML will work with Modal.

We can then register the step operator:

**Option 1: Using Modal CLI authentication (recommended for development)**

```shell
# Register the step operator (uses Modal CLI credentials)
zenml step-operator register <NAME> --flavor=modal
zenml stack update -s <NAME> ...
```

**Option 2: Using Modal API token (recommended for production)**

```shell
# Register the step operator with explicit credentials
zenml step-operator register <NAME> \
    --flavor=modal \
    --token-id=<MODAL_TOKEN_ID> \
    --token-secret=<MODAL_TOKEN_SECRET> \
    --workspace=<MODAL_WORKSPACE> \
    --modal-environment=<MODAL_ENVIRONMENT>
zenml stack update -s <NAME> ...
```

You can get your Modal token from the [Modal dashboard](https://modal.com/settings/tokens).

Once you added the step operator to your active stack, you can use it to execute individual steps of your pipeline by specifying it in the `@step` decorator as follows:

```python
from zenml import step


@step(step_operator=<NAME>)
def trainer(...) -> ...:
    """Train a model."""
    # This step will be executed in Modal.
```

{% hint style="info" %}
ZenML will build a Docker image which includes your code and use it to run your steps in Modal. Check out [this page](https://docs.zenml.io/how-to/customize-docker-builds) if you want to learn more about how ZenML builds these images and how you can customize them.
{% endhint %}

#### Additional configuration

The Modal step operator uses two types of settings following ZenML's standard pattern:

1. **`ResourceSettings`** (standard ZenML) - for hardware resource quantities:
   - `cpu_count` - Number of CPU cores
   - `memory` - Memory allocation (e.g., "16GB")
   - `gpu_count` - Number of GPUs to allocate

2. **`ModalStepOperatorSettings`** (Modal-specific) - for Modal platform configuration:
   - `gpu` - GPU type specification (e.g., "T4", "A100", "H100")
   - `region` - Cloud region preference  
   - `cloud` - Cloud provider selection
   - `modal_environment` - Modal environment name
   - `timeout` - Maximum execution time in seconds

{% hint style="info" %}
**GPU Configuration**: Use `ResourceSettings.gpu_count` to specify how many GPUs you need, and `ModalStepOperatorSettings.gpu` to specify what type of GPU. Modal will combine these automatically (e.g., `gpu_count=2` + `gpu="A100"` becomes `"A100:2"`).
{% endhint %}

You can specify the hardware requirements for each step using the
`ResourceSettings` class as described in our documentation on [resource settings](https://docs.zenml.io/user-guides/tutorial/distributed-training):

```python
from zenml.config import ResourceSettings
from zenml.integrations.modal.flavors import ModalStepOperatorSettings

# Configure Modal-specific settings
modal_settings = ModalStepOperatorSettings(
    gpu="A100",                # GPU type (optional)
    region="us-east-1",       # Preferred region
    cloud="aws",              # Cloud provider
    modal_environment="production", # Modal environment
    timeout=3600,             # 1 hour timeout
)

# Configure hardware resources (quantities)
resource_settings = ResourceSettings(
    cpu_count=2,              # Number of CPU cores
    memory="32GB",            # 32GB RAM
    gpu_count=1               # Number of GPUs (combined with gpu type above)
)

@step(
    step_operator="modal", # or whatever name you used when registering the step operator
    settings={
        "step_operator": modal_settings,
        "resources": resource_settings
    }
)
def my_modal_step():
    # This step will run on Modal with 1x A100 GPU, 2 CPU cores, and 32GB RAM
    ...
```

{% hint style="info" %}
Note that the `cpu_count` parameter in `ResourceSettings` specifies a soft minimum limit - Modal will guarantee at least this many physical cores, but the actual usage could be higher. The CPU cores/hour will also determine the minimum price paid for the compute resources.

For example, with the configuration above (2 CPUs and 32GB memory), the minimum cost would be approximately $1.03 per hour ((0.135 * 2) + (0.024 * 32) = $1.03).
{% endhint %}

This will run `my_modal_step` on a Modal instance with 1 A100 GPU, 2 CPUs, and
32GB of CPU memory.

Check out the [Modal docs](https://modal.com/docs/reference/modal.gpu) for the
full list of supported GPU types and the [SDK
docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-modal/#zenml.integrations.modal.flavors.modal\_step\_operator\_flavor.ModalStepOperatorSettings)
for more details on the available settings.

### Authentication with different environments

{% hint style="info" %}
**Best Practice: Separate Step Operators for Different Environments**

Consider creating separate ZenML step operators for different environments (development, staging, production), each configured with different Modal environments and workspaces. This provides better isolation and allows for different resource configurations per environment.

For example:
- **Development step operator**: Uses Modal "dev" environment with smaller resource limits
- **Production step operator**: Uses Modal "production" environment with production-grade resources and credentials

This approach helps prevent accidental deployment to production and allows for environment-specific configurations.
{% endhint %}

For production deployments, you can specify different Modal environments and workspaces:

```python
modal_settings = ModalStepOperatorSettings(
    modal_environment="production",  # or "staging", "dev", etc.
    workspace="my-company",    # Modal workspace name
    gpu="A100",
    region="us-east-1",
    cloud="aws"
)
```

Or configure them when registering the step operator:

```shell
zenml step-operator register modal_prod \
    --flavor=modal \
    --token-id=<MODAL_TOKEN_ID> \
    --token-secret=<MODAL_TOKEN_SECRET> \
    --workspace="production-workspace" \
    --modal-environment="production"
```

### Resource configuration notes

The settings do allow you to specify the region and cloud provider, but these
settings are only available for Modal Enterprise and Team plan customers.
Moreover, certain combinations of settings are not available. It is suggested to
err on the side of looser settings rather than more restrictive ones to avoid
pipeline execution failures. In the case of failures, however, Modal provides
detailed error messages that can help identify what is incompatible. See more in
the [Modal docs on region selection](https://modal.com/docs/guide/region-selection) for more
details.

### Available GPU types

Modal supports various GPU types for different workloads:

- `T4` - Cost-effective for inference and light training
- `A10G` - Balanced performance for training and inference  
- `A100` - High-performance for large model training
- `H100` - Latest generation for maximum performance

**Examples of GPU configurations:**

```python
# Single GPU step
@step(
    settings={
        "step_operator": ModalStepOperatorSettings(gpu="A100"),
        "resources": ResourceSettings(gpu_count=1)
    }
)
def train_model():
    # Uses 1x A100 GPU
    ...

# Multiple GPU step
@step(
    settings={
        "step_operator": ModalStepOperatorSettings(gpu="A100"),
        "resources": ResourceSettings(gpu_count=4)
    }
)
def distributed_training():
    # Uses 4x A100 GPUs
    ...
```

### Base image requirements

{% hint style="info" %}
**Docker Image Customization**

ZenML will automatically build a Docker image that includes your code and dependencies, then use it to run your steps on Modal. The base image and dependencies you configure will determine what's available in your Modal execution environment.

Key considerations:
- **Base image**: Choose an appropriate base image for your workload (e.g., `python:3.9-slim`, `ubuntu:20.04`, or specialized ML images)
- **Dependencies**: Ensure all required packages are specified in your `requirements.txt` or Docker settings
- **System packages**: If you need system-level packages, configure them in your Docker settings
- **Environment variables**: Configure any necessary environment variables in your ZenML step or Docker settings

Check out the [ZenML Docker customization guide](https://docs.zenml.io/how-to/customize-docker-builds) for detailed information on customizing your execution environment.
{% endhint %}

{% hint style="warning" %}
**Base Image Requirements for GPU Usage**

When using GPUs, ensure your base Docker image includes the appropriate CUDA runtime and drivers. Modal's GPU instances come with CUDA pre-installed, but your application dependencies (like PyTorch, TensorFlow) must be compatible with the CUDA version.

For optimal GPU performance:
- Use CUDA-compatible base images (e.g., `nvidia/cuda:11.8-runtime-ubuntu20.04`)
- Install GPU-compatible versions of ML frameworks in your Docker requirements
- Test your GPU setup locally before deploying to Modal

ZenML will use your base image configuration from the container registry, so ensure GPU compatibility is built into your image.
{% endhint %}

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


