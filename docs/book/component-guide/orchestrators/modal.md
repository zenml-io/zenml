---
description: Orchestrating your pipelines to run in Modal Sandboxes.
---

# Modal Orchestrator

The Modal orchestrator runs ZenML pipelines on [Modal](https://modal.com) using Modal Sandboxes. A Modal Sandbox is a remote container process: ZenML builds a Docker image for your pipeline, pushes it to your stack's container registry, and asks Modal to start that image in Modal's cloud infrastructure.

{% hint style="info" %}
Everywhere on this page, "sandbox" refers to Modal's Sandbox compute primitive (`modal.Sandbox`) — a Modal product concept, not a ZenML stack component.
{% endhint %}

The important runtime story is:

1. You start a ZenML pipeline run from your machine or CI system.
2. ZenML submits one Modal **orchestration sandbox** for the pipeline run.
3. That orchestration sandbox starts and monitors the step sandboxes that actually run your step code.
4. Step artifacts are read from and written to your ZenML artifact store.
5. ZenML stores the Modal sandbox IDs in run metadata so the run can be monitored and stopped later.

This makes Modal useful when you want the whole pipeline, not just selected steps, to run away from your local machine while still using Modal's fast startup and resource selection.

{% hint style="warning" %}
This component is meant for stacks that use a ZenML server reachable from Modal. If your run depends on a local ZenML store or localhost-only services, the Modal sandbox will not be able to call back to your machine.
{% endhint %}

## When to use it

You should use the Modal orchestrator if:

* you want your entire ZenML pipeline to run on Modal instead of locally.
* your steps need Modal CPU, memory, GPU, cloud, or region settings.
* you want both static and dynamic ZenML pipelines to run on Modal.
* you already have remote ZenML stack components for artifacts, images, and code execution.

If you only want a few selected steps to run on Modal while the rest of the pipeline is orchestrated somewhere else, use the [Modal step operator](../step-operators/modal.md) instead.

## Requirements

To use the Modal orchestrator, you need:

* The ZenML `modal` integration installed:

  ```shell
  zenml integration install modal
  ```
* A [Modal account](https://modal.com/signup).
* Modal authentication configured either with `modal setup`, Modal environment variables, or the `token_id` and `token_secret` fields on the ZenML orchestrator component.
* Docker installed and running where ZenML builds images.
* A [remote artifact store](../artifact-stores/README.md). Modal cannot read artifacts from a local directory on your laptop.
* A [remote container registry](../container-registries/README.md). Modal pulls the Docker image from this registry.
* An [image builder](../image-builders/README.md) in your stack so ZenML can build the image that Modal runs.

The stack validator rejects local artifact stores, local container registries, and stack components that expose local filesystem paths. The failure case is concrete: the Modal sandbox starts in Modal's infrastructure, asks for `/Users/you/project/artifacts/...`, and that path only exists on your machine. A remote artifact store and remote registry avoid that problem.

{% hint style="warning" %}
Modal imports images from a registry as `linux/amd64` images. If you build locally on Apple Silicon, configure your ZenML Docker settings to build `linux/amd64` images before using Modal. See the Docker build warning in the [Modal step operator docs](../step-operators/modal.md) for an example configuration.
{% endhint %}

## How to use it

Register the orchestrator and add it to a stack with a remote artifact store, remote container registry, and image builder:

```shell
zenml orchestrator register <ORCHESTRATOR_NAME> --flavor=modal \
  --token_id=<MODAL_TOKEN_ID> \
  --token_secret=<MODAL_TOKEN_SECRET>

zenml stack register <STACK_NAME> \
  -o <ORCHESTRATOR_NAME> \
  -a <REMOTE_ARTIFACT_STORE> \
  -c <REMOTE_CONTAINER_REGISTRY> \
  -i <IMAGE_BUILDER> \
  ... \
  --set
```

If you already authenticated Modal with `modal setup`, or you provide Modal credentials through Modal's normal environment variables, you can omit `token_id` and `token_secret`. If you configure one of those fields on the orchestrator component, you must configure both.

Then run your pipeline as usual:

```shell
python run_pipeline.py
```

ZenML builds and pushes the image, submits the orchestration sandbox to Modal, and records the Modal sandbox metadata on the ZenML pipeline run.

## Static and dynamic pipeline behavior

For a **static pipeline**, ZenML submits one Modal orchestration sandbox. Inside that sandbox, ZenML follows the step dependency graph and starts one child Modal sandbox for each step once its upstream steps have completed. If a step can be loaded from cache, the controller records the cached step run instead of starting a new Modal sandbox for that step. Static Modal pipelines support all three ZenML execution modes: `FAIL_FAST`, `STOP_ON_FAILURE`, and `CONTINUE_ON_FAILURE`.

For a **dynamic pipeline**, ZenML submits one Modal orchestration sandbox that runs ZenML's dynamic pipeline entrypoint. Dynamic Modal pipelines still follow ZenML's current dynamic pipeline limitation: `CONTINUE_ON_FAILURE` behaves like `STOP_ON_FAILURE`, so after a dynamic step fails, ZenML does not keep launching later independent dynamic steps. Dynamic steps can run in two ways:

* Steps that need isolation run as child Modal sandboxes. This includes steps with step-level resource settings or step-level Docker settings that differ from the pipeline image. Steps that use a step operator are isolated too, but they run on that step operator's infrastructure instead of a child Modal sandbox.
* Steps that do not need isolation can run inside the dynamic orchestration sandbox process.

In both modes, ZenML stores the orchestration sandbox ID on the pipeline run and child sandbox IDs on step runs. These metadata entries are what ZenML uses later for status checks and stop requests.

## Configuring Modal authentication

The Modal orchestrator has optional `token_id` and `token_secret` fields. When both are configured, ZenML creates an explicit Modal SDK client from those credentials and passes that client to Modal SDK calls.

When they are not configured, ZenML does not pass an explicit client. Modal then uses its normal authentication behavior, for example credentials from `modal setup`, Modal environment variables, or `~/.modal.toml`.

ZenML also passes the short-lived ZenML server token needed by the runtime into Modal as a Modal Secret instead of a plain sandbox environment variable. Regular runtime environment variables are passed as normal sandbox environment variables.

## Configuring resources

Use `ModalOrchestratorSettings` together with ZenML `ResourceSettings` to select Modal resources:

```python
from zenml import pipeline, step
from zenml.config import ResourceSettings
from zenml.integrations.modal.flavors import ModalOrchestratorSettings

gpu_step_settings = ModalOrchestratorSettings(
    gpu="A100",           # GPU type, e.g. "T4" or "A100"
    # region="us-east-1", # optional; availability depends on your Modal plan
    # cloud="aws",        # optional; availability depends on your Modal plan
)

step_resources = ResourceSettings(
    cpu_count=2,
    memory="32GB",
    gpu_count=1,
)


@step(
    settings={
        "orchestrator": gpu_step_settings,
        "resources": step_resources,
    }
)
def train_model() -> None:
    ...


@pipeline
def training_pipeline() -> None:
    train_model()
```

Orchestrator-wide options such as `modal_environment`, `timeout`, and `synchronous` can be set in a `ModalOrchestratorSettings` object passed at the pipeline level when you need them.

{% hint style="warning" %}
Set GPU types at the step level, not the pipeline level. Pipeline-level orchestrator settings configure the orchestration sandbox and are inherited by every step, so a pipeline-level `gpu` attaches a GPU to all step sandboxes and to the controller — where it sits idle while you pay for it, unless your dynamic pipeline runs GPU step code inside the orchestration sandbox process.
{% endhint %}

The resource mapping is:

| ZenML setting | Modal sandbox setting |
| --- | --- |
| `ResourceSettings.cpu_count` | `cpu` |
| `ResourceSettings.memory` | `memory`, converted to MB and rounded up |
| `ResourceSettings.gpu_count` + `ModalOrchestratorSettings.gpu` | `gpu`, for example `"A100"` or `"A100:2"` |
| `ModalOrchestratorSettings.timeout` | `timeout` in seconds |
| `ModalOrchestratorSettings.cloud` | `cloud` |
| `ModalOrchestratorSettings.region` | `region` |

Important details:

* If `gpu_count > 0`, you must also set `ModalOrchestratorSettings.gpu`. ZenML needs the count and the Modal GPU type to build the Modal `gpu` argument.
* If `gpu` is set and `gpu_count` is omitted, Modal uses one GPU of that type.
* If `gpu` is set and `gpu_count=0`, ZenML runs on CPU and logs a warning that the GPU type was ignored.
* Pipeline-level resources apply to the orchestration sandbox.
* Static step-level resources apply to the child sandbox for that step.
* Dynamic step-level resources cause the step to run as an isolated child sandbox, and the resources apply to that child sandbox.

The `modal_environment` setting selects the Modal environment used for `modal.App.lookup(..., environment_name=...)`. It is separate from ZenML runtime environment variables.

## Synchronous and asynchronous runs

By default, `synchronous=True`. In that mode, the process that submitted the run waits until the Modal orchestration sandbox finishes. If the controller detects failed child step sandboxes, it exits with a non-zero code, and ZenML reports the run as failed to the submitting process.

If you set `synchronous=False`, ZenML submits the orchestration sandbox and returns after the sandbox has started successfully:

```python
from zenml.integrations.modal.flavors import ModalOrchestratorSettings

settings = {
    "orchestrator": ModalOrchestratorSettings(synchronous=False),
}
```

The pipeline still runs on Modal. You can monitor it from ZenML because the pipeline run metadata contains the Modal orchestration sandbox ID.

## Stopping runs

Stop behavior depends on the pipeline type and whether the stop is graceful or forceful.

For a graceful stop of a static Modal run, ZenML marks the pipeline run as `STOPPING`. The orchestration sandbox notices that status, stops scheduling new step sandboxes, lets already-running child sandboxes finish, and then publishes the final run status.

For a force stop of a static Modal run, ZenML terminates the Modal sandboxes it knows about:

1. ZenML refreshes the pipeline run metadata and reads known child sandbox IDs from step metadata and pipeline-run fallback metadata.
2. ZenML terminates each known child sandbox that is still running.
3. ZenML terminates the orchestration sandbox.
4. ZenML refreshes the run metadata once more and terminates any child sandbox IDs that appeared during cleanup.
5. If a sandbox has already finished, ZenML leaves it alone.

For dynamic Modal runs, graceful stop requests use the same termination flow as force stop requests. ZenML terminates known child sandboxes and the orchestration sandbox, refreshes run metadata, and then terminates any late child sandboxes that appeared while cleanup was running.

## Current v1 limitations

The first version of the Modal orchestrator has a few intentional limits:

* Scheduled pipelines are not supported yet. Static and dynamic submissions with schedules are rejected.
* The orchestrator does not handle step retries internally. ZenML's normal step retry behavior still applies.
* Client-side caching is disabled for the orchestrator component. The static controller can still reuse already-cached steps when the ZenML run logic marks a step as cached.
* Stop and status behavior depends on Modal sandbox IDs stored in ZenML metadata. If those IDs are missing, ZenML can only report the last known run or step status and may not be able to terminate already-started sandboxes.

For more details on the available settings, see the [Modal integration SDK docs](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-modal.html).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
