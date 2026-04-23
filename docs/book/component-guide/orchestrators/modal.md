---
description: Orchestrating your pipelines on Modal's serverless compute.
---

# Modal Orchestrator

[Modal](https://modal.com) is a serverless compute platform with fast container start-up and per-second billing. ZenML's Modal orchestrator runs each step of your pipeline in its own ephemeral Modal sandbox.

If you only need remote execution for a subset of steps, use the [Modal step operator](../step-operators/modal.md) instead.

### When to use it

You should use the Modal orchestrator if:

* You want your entire pipeline to run on serverless compute without managing any infrastructure yourself.
* You need fast cold starts and per-second billing for pipelines with uneven resource needs.
* You want to specify hardware requirements (CPU, GPU type, memory) per step.
* You have access to Modal.

### How to deploy it

To use the Modal orchestrator:

* [Sign up for a Modal account](https://modal.com/signup) if you haven't already.
* Install the Modal CLI by running `pip install modal` (or `zenml integration install modal`) and authenticate by running `modal setup` in your terminal.

### How to use it

To use the Modal orchestrator, we need:

* The ZenML `modal` integration installed. If you haven't done so, run

  ```shell
  zenml integration install modal
  ```
* A remote artifact store as part of your stack. Steps run in separate Modal sandboxes and need a shared artifact store to pass data between them. Any cloud artifact store supported by ZenML will work with Modal.
* A remote container registry as part of your stack. Modal pulls the step images from this registry, so a local registry will not work.
* An image builder in your stack (the `local` image builder is fine when you have Docker installed locally; the `kaniko` image builder works if you don't).

We can then register the orchestrator and update the active stack:

```shell
zenml orchestrator register <ORCHESTRATOR_NAME> --flavor=modal
zenml stack update -o <ORCHESTRATOR_NAME> ...
```

Any ZenML pipeline run on this stack will then execute on Modal:

```shell
python file_that_runs_a_zenml_pipeline.py
```

{% hint style="info" %}
ZenML builds a Docker image containing your code and pushes it to the configured container registry; Modal pulls that image into each step sandbox. See [Customize Docker builds](https://docs.zenml.io/how-to/customize-docker-builds) to control how the image is built.
{% endhint %}

#### Additional configuration

Use `ModalOrchestratorSettings` to tune Modal-specific behavior and `ResourceSettings` to request CPU, GPU, and memory per step:

```python
from zenml import pipeline, step
from zenml.config import ResourceSettings
from zenml.integrations.modal.flavors import ModalOrchestratorSettings


modal_settings = ModalOrchestratorSettings(gpu="A100")
resource_settings = ResourceSettings(cpu=2, memory="32GB")


@step(
    settings={
        "orchestrator": modal_settings,
        "resources": resource_settings,
    }
)
def trainer(...) -> ...:
    """Train a model on an A100 with 2 CPUs and 32GB of memory."""


@pipeline
def my_pipeline():
    trainer()
```

The settings can also be applied at the pipeline level; per-step settings override pipeline-level defaults.

`region` and `cloud` are only honored on Modal Enterprise/Team plans. Prefer looser settings when you can — see the [Modal region selection docs](https://modal.com/docs/guide/region-selection) for valid combinations, and the [Modal GPU docs](https://modal.com/docs/guide/gpu) for supported GPU types. A full list of available settings lives in the [ZenML SDK docs](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-modal.html).

{% hint style="info" %}
`ResourceSettings.cpu` accepts a single integer — a soft minimum number of physical cores that Modal guarantees. Actual usage may be higher, and CPU cores/hour sets a minimum price; see the [Modal pricing page](https://modal.com/pricing).
{% endhint %}

#### Enabling CUDA for GPU-backed hardware

If a step needs a GPU, follow [the GPU setup guide](https://docs.zenml.io/user-guides/tutorial/distributed-training/) to ensure CUDA is wired through correctly.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
