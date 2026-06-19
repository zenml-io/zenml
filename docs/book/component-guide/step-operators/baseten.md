---
description: Executing individual steps as Baseten training jobs, including multi-node distributed training.
---

# Baseten Step Operator

[Baseten](https://www.baseten.co/) provides on-demand H100/H200 (and more) GPU capacity through
its Training product. The ZenML Baseten step operator runs selected steps of your pipeline as
Baseten training jobs, so the rest of the pipeline can run anywhere (locally, on Kubernetes,
or any other orchestrator) while GPU-heavy steps execute on Baseten.

It supports both:

* **single-node execution** for a regular `@step` (full ZenML features: inputs, outputs,
  artifacts, logs), and
* **multi-node distributed training** for a [`CommandStep`](https://docs.zenml.io/how-to/steps-pipelines/command_steps),
  where Baseten provisions `node_count` identical nodes and your command (e.g. `torchrun`)
  owns the distributed launch.

## When to use it

Use the Baseten step operator if:

* you need H100/H200 (and more) GPUs for specific steps but want to keep your existing
  orchestrator and [remote artifact store](https://docs.zenml.io/stacks/artifact-stores/), or
* you want multi-node distributed training without managing a cluster — Baseten provisions and
  tears down the nodes per job.

## How to deploy it

You need a [Baseten account](https://www.baseten.co/) and an API key (create one in your
Baseten workspace settings).

### Baseten account requirements

Two execution modes depend on **organization-level entitlements** that may need to be enabled by
Baseten support for your account:

| Mode | Requires | Symptom if not enabled |
|---|---|---|
| Single-node regular `@step` | **Custom base images** | Job creation fails with `Custom base images not supported for your organization` |
| Multi-node (`node_count > 1`) | **Multi-node instance types** | Job creation fails with a `400 Bad Request` |

This is because a regular `@step` runs the ZenML entrypoint, so its container must contain `zenml`,
your code and dependencies — that is a *custom image*. A [`CommandStep`](https://docs.zenml.io/how-to/steps-pipelines/command_steps),
by contrast, is an opaque command that can run on a **stock public image** (with `skip_build=True`),
which any Baseten organization can pull — so the single-node `CommandStep` path works out of the
box. If you plan to run regular `@step`s or multi-node jobs, ask Baseten to enable the
corresponding entitlement first. These are Baseten account gates, not ZenML limitations — the
operator builds, submits, polls, cancels and records metadata for every mode regardless.

## How to use it

To use the Baseten step operator, you need:

* the ZenML `baseten` integration installed:

  ```shell
  zenml integration install baseten
  ```

* a [remote artifact store](https://docs.zenml.io/stacks/artifact-stores/) as part of your
  stack (steps run remotely and write artifacts over the network),
* a [remote container registry](https://docs.zenml.io/stacks/container-registries/) and an
  [image builder](https://docs.zenml.io/stacks/image-builders/) as part of your stack, so the
  step image can be built and pulled by Baseten.

Register the step operator and add it to your stack:

```shell
zenml step-operator register baseten_operator \
    --flavor=baseten \
    --api_key=<YOUR_BASETEN_API_KEY> \
    --project=zenml-training

zenml stack register baseten_stack \
    -s baseten_operator \
    -a <REMOTE_ARTIFACT_STORE> \
    -c <REMOTE_CONTAINER_REGISTRY> \
    -i <IMAGE_BUILDER> \
    --set
```

If your step image lives in a private registry, store the registry credentials
(`username:password`) as a Baseten secret and reference it on the step operator with
`--registry_auth_secret=<BASETEN_SECRET_NAME>`.

### Single-node steps

Point any step at the operator and request a GPU via `ResourceSettings`:

```python
from zenml import step, pipeline
from zenml.config import ResourceSettings
from zenml.integrations.baseten.flavors import BasetenStepOperatorSettings


@step(
    step_operator="baseten_operator",
    settings={
        "step_operator": BasetenStepOperatorSettings(accelerator="H100"),
        "resources": ResourceSettings(gpu_count=1),
    },
)
def train() -> None:
    ...


@pipeline
def my_pipeline() -> None:
    train()
```

The `accelerator` type (`H100` or `H200`) is a step operator setting; the number of GPUs per
node comes from `ResourceSettings.gpu_count`.

### Multi-node distributed training

Multi-node runs the same container on every node, so a regular step would duplicate its
artifacts, outputs and logs. Multi-node is therefore only allowed for a
[`CommandStep`](https://docs.zenml.io/how-to/steps-pipelines/command_steps), which ZenML treats
as an opaque command and never runs its machinery inside. Set `node_count > 1` and let your
command own the distributed launch.

Baseten injects these environment variables on every node, which you wire into `torchrun`:

| Variable | Meaning |
|---|---|
| `BT_GROUP_SIZE` | number of nodes |
| `BT_NODE_RANK` | rank of this node (0 = leader) |
| `BT_LEADER_ADDR` | address of the leader node |
| `BT_NUM_GPUS` | GPUs per node |

```python
from zenml import CommandStep, pipeline
from zenml.config import ResourceSettings
from zenml.integrations.baseten.flavors import BasetenStepOperatorSettings

train = CommandStep(
    command=[
        "bash",
        "-lc",
        "torchrun --nnodes=$BT_GROUP_SIZE --node-rank=$BT_NODE_RANK "
        "--master-addr=$BT_LEADER_ADDR --master-port=29500 "
        "--nproc-per-node=$BT_NUM_GPUS train.py",
    ],
    step_operator="baseten_operator",
    settings={
        "step_operator": BasetenStepOperatorSettings(
            accelerator="H200", node_count=4
        ),
        "resources": ResourceSettings(gpu_count=8),
    },
)


@pipeline(dynamic=True)
def training_pipeline() -> None:
    train()
```

The image must already contain your training code and dependencies. A regular step submitted
with `node_count > 1` is rejected with a clear error.

### Passing secrets

Sensitive environment variables are never inlined into the job config. Store your own secrets
(API tokens, credentials) as Baseten secrets and map them with the `secrets` setting — the value
is referenced rather than inlined:

```python
BasetenStepOperatorSettings(
    secrets={"HF_TOKEN": "hf-access-token"},
)
```

The ZenML store API token (which regular steps need to call back to the server) is handled
automatically: the operator upserts it into a managed Baseten secret named
`zenml-store-api-token-<operator-id>` on each run and references that, so the token never lands
in the inlined job config. You can override this by mapping the token name explicitly in
`secrets`. Command steps never talk to the ZenML server, so the token is dropped for them
entirely.

### Caching and checkpointing

Baseten can [persist a training cache](https://docs.baseten.co/training/loading) so datasets and
model weights downloaded by a job survive across jobs (avoiding re-downloads), and it can manage
checkpoint storage. Both are **disabled by default** and opt-in through settings:

```python
BasetenStepOperatorSettings(
    accelerator="H100",
    enable_cache=True,                  # mount the persistent training cache (off by default)
    cache_enable_legacy_hf_mount=True,  # also reuse the default Hugging Face cache path
    cache_require_affinity=False,       # allow running across different GPU types
    enable_checkpointing=True,          # persist checkpoints written to $BT_CHECKPOINT_DIR (off by default)
)
```

When `enable_cache` is on, write your downloads (e.g. `HF_HOME`, dataset staging) into the cache so
subsequent runs reuse them. `cache_enable_legacy_hf_mount` additionally mounts the legacy Hugging
Face cache location (handy for libraries that download to the default HF path), and
`cache_require_affinity` (default `True`) controls whether the job must land on nodes that already
hold the cache — set it `False` to let the same project run across different GPU types. When
`enable_checkpointing` is on, write checkpoints to the Baseten checkpoint directory exposed as
`$BT_CHECKPOINT_DIR`.

For more information and a full list of configurable attributes, check out the
[SDK docs](https://sdkdocs.zenml.io/latest/).

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
