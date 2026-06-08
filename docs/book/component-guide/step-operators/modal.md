---
description: Executing individual steps in Modal.
---

# Modal Step Operator

[Modal](https://modal.com) is a platform for running cloud infrastructure. It offers specialized compute instances to run your code and has a fast execution time, especially around building Docker images and provisioning hardware. ZenML's Modal step operator allows you to submit individual steps to be run on Modal compute instances.

### When to use it

You should use the Modal step operator if:

* You need fast execution time for steps that require computing resources (CPU, GPU, memory).
* You want to easily specify the exact hardware requirements (e.g., GPU type, CPU count, memory) for each step.
* You have access to Modal.

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
* An Image Builder in your stack. ZenML uses it to build the Docker image that
  runs on Modal.

The Modal step operator can use Modal authentication settings from the stack component configuration. If `token_id` and `token_secret` are configured on the step operator, ZenML creates an explicit Modal SDK client from those credentials and passes that client to Modal SDK calls. If these fields are not configured, ZenML passes no explicit client and Modal uses its normal authentication behavior, such as existing environment variables or `~/.modal.toml`.

ZenML step runtime environment variables, including values needed by the step to connect back to the ZenML server, are passed to the Modal sandbox when the step starts. They are not added to the Modal image definition. Modal authentication settings used to submit the sandbox, the Modal environment used for app lookup, and container registry credentials used to pull the image are handled separately.

We can then register the step operator:

```shell
zenml step-operator register <NAME> --flavor=modal \
  --token_id=<MODAL_TOKEN_ID> \
  --token_secret=<MODAL_TOKEN_SECRET>
zenml stack update -s <NAME> ...
```

Once you added the step operator to your active stack, you can use it to execute individual steps of your pipeline by specifying it in the `@step` decorator as follows:

```python
from zenml import step


@step(step_operator=True)
def trainer(...) -> ...:
    """Train a model."""
    # This step will be executed in Modal.
```

{% hint style="info" %}
ZenML will build a Docker image which includes your code and use it to run your steps in Modal. Check out [this page](https://docs.zenml.io/how-to/customize-docker-builds) if you want to learn more about how ZenML builds these images and how you can customize them.
{% endhint %}

{% hint style="warning" %}
Modal requires images imported from a registry to be built for `linux/amd64`. If you build locally on Apple Silicon, Docker may produce an `arm64` image by default, which Modal will reject during image import. Configure your Docker settings to build for `linux/amd64`, and prevent build reuse once while replacing any previously built `arm64` image:

```python
from zenml.config import DockerSettings
from zenml.config.docker_settings import DockerBuildConfig, DockerBuildOptions

amd64_build_config = DockerBuildConfig(
    build_options=DockerBuildOptions(platform="linux/amd64")
)

docker_settings = DockerSettings(
    # your existing Docker settings...
    parent_image_build_config=amd64_build_config,
    build_config=amd64_build_config,
    prevent_build_reuse=True,
)
```

If Docker still fails locally with a platform error while building a multi-stage image, make sure the local image builder uses the Docker CLI/BuildKit path instead of the Docker Python SDK path:

```shell
export DOCKER_BUILDKIT=1
zenml image-builder update <LOCAL_IMAGE_BUILDER_NAME> --use_subprocess_call=True
```

You can remove `prevent_build_reuse=True` again after ZenML has built and pushed a fresh `linux/amd64` image.
{% endhint %}

#### Additional configuration

You can specify the hardware requirements for each step using the
`ResourceSettings` class as described in our documentation on [resource settings](https://docs.zenml.io/user-guides/tutorial/distributed-training):

```python
from zenml import step
from zenml.config import ResourceSettings
from zenml.integrations.modal.flavors import ModalStepOperatorSettings

modal_settings = ModalStepOperatorSettings(
    gpu="A100",           # GPU type (e.g., "T4", "A100")
    # region="us-east-1", # optional, enterprise/team only
    # cloud="aws",        # optional, enterprise/team only
    # modal_environment="main",  # optional Modal environment name
    # timeout=86400,      # optional sandbox timeout in seconds
)

resource_settings = ResourceSettings(
    cpu_count=2,
    memory="32GB",
    # gpu_count=1,        # optional; if omitted and a GPU type is set, defaults to 1 GPU
)

@step(
    step_operator=True,   # or the specific name, e.g., step_operator="<NAME>"
    settings={
        "step_operator": modal_settings,
        "resources": resource_settings,
    },
)
def my_modal_step():
    ...
```

Important:
- If you request GPUs with `ResourceSettings.gpu_count > 0`, you must also specify a GPU type via `ModalStepOperatorSettings.gpu`; otherwise the run will fail with a validation error.
- If a GPU type is set but `gpu_count == 0`, ZenML treats the step as CPU-only and logs a warning that the GPU type is ignored.
- If `gpu_count` is omitted and a GPU type is set, Modal uses one GPU of that type.
- `cpu_count` is passed through from `ResourceSettings` to Modal. `memory` must be a string such as `"32GB"`, `"32768MB"`, or `"32GiB"`. ZenML converts it to decimal megabytes (`MB`) and rounds fractional MB values up before passing it to Modal.
- If the active container registry exposes credentials, ZenML passes them to Modal for image pulls. If no registry credentials are configured, Modal attempts to pull the image anonymously.

{% hint style="info" %}
Note that `cpu_count` specifies a soft minimum limit - Modal will guarantee at least this many physical cores, but the actual usage could be higher. The CPU cores/hour will also determine the minimum price paid for the compute resources.
{% endhint %}

This will run `my_modal_step` on a Modal instance with 1 A100 GPU, 2 CPUs, and
32GB of CPU memory.

Check out the [Modal docs](https://modal.com/docs/guide/gpu) for the
full list of supported GPU types and the [SDK
docs](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-modal.html)
for more details on the available settings.

The settings allow you to specify the Modal environment, region, and cloud provider. `modal_environment` selects the Modal environment used for the app lookup; ZenML passes it as `environment_name` to `modal.App.lookup(...)`. The sandbox then belongs to that app, while ZenML step runtime environment variables are still passed separately to the sandbox runtime with `env=...`. Region and cloud provider settings are only available for Modal Enterprise and Team plan customers.
Certain combinations of settings are not available. It is suggested to
err on the side of looser settings rather than more restrictive ones to avoid
pipeline execution failures. In the case of failures, however, Modal provides
detailed error messages that can help identify what is incompatible. See more in
the [Modal docs on region selection](https://modal.com/docs/guide/region-selection) for more
details.
