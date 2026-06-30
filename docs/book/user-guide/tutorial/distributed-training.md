---
icon: microchip-ai
description: Train ZenML pipelines on GPUs and scale out with 🤗 Accelerate.
---

# Train with GPUs and Accelerate

Need more compute than your laptop can offer?  This tutorial shows how to:

1. **Request GPU resources** for individual steps.
2. Build a **CUDA‑enabled container image** so the GPU is actually visible.
3. Reset the CUDA cache between steps (optional but handy for memory‑heavy jobs).
4. Scale to *multiple* GPUs or nodes with the [🤗 Accelerate](https://github.com/huggingface/accelerate) integration.
5. Go **multi-node** by wrapping a distributed launcher (TorchX, Ray) in a `CommandStep`.

---

## 1 Request extra resources for a step

If your orchestrator supports it you can reserve CPU, GPU and RAM directly on a ZenML `@step`:

```python
from zenml import step
from zenml.config import ResourceSettings

@step(settings={
    "resources": ResourceSettings(cpu_count=8, gpu_count=2, memory="16GB")
})
def training_step(...):
    ...  # heavy training logic
```

👉 Check your orchestrator's docs; some (e.g. SkyPilot) expose dedicated settings instead of `ResourceSettings`.

{% hint style="info" %}
If your orchestrator can't satisfy these requirements, consider off‑loading the step to a dedicated [step operator](https://docs.zenml.io/stacks/step-operators).
{% endhint %}

---

## 2 Build a CUDA‑enabled container image

Requesting a GPU is not enough—your Docker image needs the CUDA runtime, too.

```python
from zenml import pipeline
from zenml.config import DockerSettings

docker = DockerSettings(
    parent_image="pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime",
    python_package_installer_args={"system": None},
    requirements=["zenml", "torchvision"]
)

@pipeline(settings={"docker": docker})
def my_gpu_pipeline(...):
    ...
```

Use the official CUDA images for TensorFlow/PyTorch or the pre‑built ones offered by AWS, GCP or Azure.

---

### Optional – clear the CUDA cache

If you squeeze every last MB out of the GPU consider clearing the cache at the beginning of each step:

```python
import gc, torch

def cleanup_memory():
    while gc.collect():
        torch.cuda.empty_cache()
```

Call `cleanup_memory()` at the start of your GPU steps.

---

## 3 Multi‑GPU / multi‑node training with 🤗 Accelerate

ZenML integrates with the Hugging Face Accelerate launcher.  Wrap your *training* step with `run_with_accelerate` to fan it out over multiple GPUs or machines:

```python
from zenml import step, pipeline
from zenml.integrations.huggingface.steps import run_with_accelerate

@run_with_accelerate(num_processes=4, multi_gpu=True)
@step
def training_step(...):
    ...  # your distributed training code

@pipeline
def dist_pipeline(...):
    training_step(...)
```

Common arguments:

- `num_processes`: total processes to launch (one per GPU)
- `multi_gpu=True`: enable multi‑GPU mode
- `cpu=True`: force CPU training
- `mixed_precision` : `"fp16"` / `"bf16"` / `"no"`

{% hint style="warning" %}
Accelerate‑decorated steps must be called with **keyword** arguments and cannot be wrapped a second time inside the pipeline definition.
{% endhint %}

### Prepare the container

Use the same CUDA image as above **plus** add Accelerate to the requirements:

```python
DockerSettings(
    parent_image="pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime",
    python_package_installer_args={"system": None},
    requirements=["zenml", "accelerate", "torchvision"]
)
```

---

## 4 Distributed training across processes and nodes

Section 3 (Accelerate) already fans a single step out over the GPUs on one machine. More generally there are two cases, and they call for different tools:

- **Single node, multiple GPUs** → a native step (your own multiprocessing, or the Accelerate integration), or a `CommandStep` running `torchrun`. No external launcher or gang scheduler needed.
- **Multiple nodes** → wrap a distributed *launcher* in a [`CommandStep`](../../how-to/steps-pipelines/command_steps.md): ZenML owns the run, the launcher owns the worker processes.

### Single node, multiple GPUs

For several GPUs on **one** machine you don't need an external launcher or a gang scheduler — every process lives in the step's own container. There are three patterns, and all three work today; pick whichever fits how you already train.

**1. A native step that spawns the processes itself.** ZenML supports multi-process training out of the box — request the GPUs with `ResourceSettings` and let your code start one process per GPU (for example `torch.multiprocessing.spawn`, setting up DDP inside). No extra libraries, and you keep ZenML's input/output and log tracking.

```python
import torch.distributed as dist
import torch.multiprocessing as mp

from zenml import pipeline, step
from zenml.config import ResourceSettings

def _worker(rank: int, world_size: int) -> None:
    dist.init_process_group("nccl", rank=rank, world_size=world_size)
    # ... your DDP training ...
    dist.destroy_process_group()

@step(
    runtime="isolated",  # run in its own container with the GPUs, not inline
    settings={"resources": ResourceSettings(gpu_count=4)},
)
def train() -> None:
    mp.spawn(_worker, args=(4,), nprocs=4)  # one process per GPU

@pipeline(dynamic=True)
def training() -> None:
    train()
```

`runtime="isolated"` tells the orchestrator to run the step in a fresh container (sized for the GPUs it requests) instead of inline in the orchestration process — which is what you want for a heavy training step. It's a dynamic-pipeline feature, so the pipeline is `dynamic=True`. The isolated container uses the pipeline image, so make sure that image carries CUDA and torch (see section 2).

**2. The Accelerate integration.** If you'd rather not wire up the process group yourself, decorate the step with `run_with_accelerate` (see section 3) and it handles the fan-out:

```python
from zenml import step
from zenml.config import ResourceSettings
from zenml.integrations.huggingface.steps import run_with_accelerate

@run_with_accelerate(num_processes=4, multi_gpu=True)
@step(settings={"resources": ResourceSettings(gpu_count=4)})
def train(...):
    ...  # your training code
```

**3. A `CommandStep` running `torchrun`.** If you already drive training with `torchrun` (or any launcher CLI), wrap it in a command step. The launcher and its workers share the one container, so a single image carries `zenml` + `torch` + `train.py`:

```python
from zenml import CommandStep, pipeline
from zenml.config import DockerSettings, ResourceSettings

train = CommandStep(
    command=["torchrun", "--standalone", "--nproc-per-node=4", "train.py"],
    step_operator="gmi-k8s",
    settings={
        "docker": DockerSettings(
            parent_image="pytorch/pytorch:2.4.0-cuda12.1-cudnn9-runtime",
            requirements=["zenml"],
        ),
        "resources": ResourceSettings(gpu_count=4),
    },
)

@pipeline(dynamic=True, depends_on=[train])
def training() -> None:
    train()
```

The trade-off: patterns 1 and 2 keep ZenML's artifact and log tracking; pattern 3 treats training as an opaque command (logs land in the backend, no inputs/outputs) but lets you reuse an existing `torchrun` entrypoint unchanged. The same vanilla `train.py` shown below works with pattern 3.

### Multiple nodes — wrap a launcher in a `CommandStep`

Once training spans more than one machine, the cleanest approach is to let a dedicated launcher own the worker gang and let ZenML own the run.

#### Why a launcher (and not ZenML) starts the workers

`torch.distributed` / `torchrun` only *coordinate* ranks through a rendezvous — they assign `RANK`, `WORLD_SIZE` and `LOCAL_RANK` and wire the processes together. They do **not** provision machines or start processes on other nodes. Something has to launch N worker processes across N nodes that can all reach the rendezvous endpoint — a launcher that provisions and gang-schedules them: TorchX, Ray, Slurm, and so on.

ZenML doesn't reimplement that. Instead it gives you a clean seam:

- A `CommandStep` runs an **opaque command** in a container on a step operator.
- Point that command at the launcher. The launcher schedules and starts the worker gang.
- ZenML records the run and tracks the *launcher* process through the step operator's `submit`/`get_status`/`cancel` lifecycle. The launcher pod blocks until the whole job finishes, so the ZenML step succeeds or fails with the job.

The skeleton is always the same — only the command changes:

```python
from zenml import CommandStep, pipeline
from zenml.config import DockerSettings

train = CommandStep(
    command=[...launcher CLI...],          # TorchX / Ray
    step_operator="<your-step-operator>",  # where the launcher itself runs
    settings={"docker": DockerSettings(requirements=["<launcher-package>"])},
)

# A command step runs on a step operator. In a dynamic pipeline, only steps
# named in depends_on get their own image built — list it here so ZenML builds
# an image with the launcher installed (otherwise the step falls back to the
# orchestrator image). dynamic=True also unlocks resource pools.
@pipeline(dynamic=True, depends_on=[train])
def training() -> None:
    train()
```

#### Pick a launcher

| Launcher | Starts workers on | Needs | Best when |
|----------|-------------------|-------|-----------|
| **TorchX** (`dist.ddp`) | Kubernetes, Slurm, local | [Volcano](https://volcano.sh) for gang scheduling on K8s | Multi-node on bare Kubernetes with plain `torch.distributed` |
| **Ray** (`ray job submit`) | A Ray cluster / KubeRay | A running Ray cluster | You already run Ray; Ray Train sets up `torch.distributed` for you |

#### Worked example: TorchX + Volcano on Kubernetes

Your training script is **vanilla `torch.distributed`** — it reads the rank/world-size that the launcher injects and contains nothing ZenML- or launcher-specific:

```python
# train.py
import os
import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP

def main() -> None:
    dist.init_process_group("nccl")                 # rendezvous via env vars
    local_rank = int(os.environ["LOCAL_RANK"])
    torch.cuda.set_device(local_rank)

    model = DDP(MyModel().cuda(local_rank), device_ids=[local_rank])
    # ... your normal training loop ...

    dist.destroy_process_group()

if __name__ == "__main__":
    main()
```

The pipeline wraps `torchx run` in a `CommandStep`. TorchX's `dist.ddp` builtin uses torchelastic and gang-schedules the workers on Volcano:

```python
# pipeline.py
from zenml import CommandStep, pipeline
from zenml.config import DockerSettings
from zenml.integrations.kubernetes.flavors import KubernetesStepOperatorSettings

NNODES, NPROC = 2, 8  # 2 nodes x 8 GPUs

train = CommandStep(
    command=[
        "torchx", "run", "-s", "kubernetes", "-cfg", "queue=default",
        "--wait", "--log",
        "dist.ddp", "-j", f"{NNODES}x{NPROC}", "--gpu", str(NPROC),
        "--image", "<registry>/ddp-worker:latest",  # the CUDA worker image
        "--script", "train.py", "--env", "EPOCHS=5",
    ],
    step_operator="gmi-k8s",
    settings={
        # ZenML builds a slim launcher image (its base + zenml + torchx).
        "docker": DockerSettings(requirements=["torchx"]),
        "step_operator": KubernetesStepOperatorSettings(
            service_account_name="torchx-launcher"
        ),
    },
)

@pipeline(dynamic=True, depends_on=[train])
def training() -> None:
    train()

if __name__ == "__main__":
    training()
```

You only hand-build the **worker** image (CUDA + torch + your script — no `zenml` needed, workers aren't ZenML steps):

```dockerfile
# worker image -> <registry>/ddp-worker:latest
FROM pytorch/pytorch:2.4.0-cuda12.1-cudnn9-runtime
WORKDIR /app
COPY train.py .
```

#### The same pattern with Ray

Only the command changes. With **Ray** (submitting to an existing cluster, letting Ray Train own `torch.distributed`):

```python
train = CommandStep(
    command=["ray", "job", "submit", "--address", "http://ray-head:8265",
             "--", "python", "train_ray.py"],
    step_operator="gmi-k8s",
    settings={"docker": DockerSettings(requirements=["ray[client]"])},
)
```

#### Things to keep in mind

- **List the command step in `depends_on`.** A command step runs on a step operator, and in a dynamic pipeline only the steps named in `depends_on` get a dedicated image built — otherwise the step falls back to the orchestrator image and won't have the launcher installed. `@pipeline(dynamic=True, depends_on=[train])` builds the right image; `dynamic=True` also unlocks [resource pools](../../getting-started/zenml-pro/resource-pools.md). (Regular steps like the single-node examples above don't need `depends_on` — they use the pipeline image.)
- **The image must carry the launcher (and `zenml`).** The `CommandStep` runs through ZenML's entrypoint on the step operator, so the launcher image needs both `zenml` and the launcher package. Either let ZenML install them with `requirements=[...]` (as above), or bake your own image and use `DockerSettings(skip_build=True, parent_image=...)` — a custom `parent_image` must already contain `zenml`. The *worker* image (passed to the launcher, e.g. `--image`) only needs your training stack, not `zenml`.
- **Logs live in the launcher's backend.** Command-step logs are not tracked by ZenML — worker logs stay where the launcher puts them (pod logs, the Ray dashboard, etc.). See the [command steps limitations](../../how-to/steps-pipelines/command_steps.md).
- **Two capacity managers, two jobs.** The launcher's gang scheduler (e.g. Volcano) reserves the *worker* capacity all-or-nothing; ZenML resource pools (if you use them) govern the *launcher* step. They don't overlap.

---

## 5 Troubleshooting & Tips

| Problem | Quick fix |
|---------|-----------|
| *GPU is unused* | Verify CUDA toolkit inside container (`nvcc --version`), check driver compatibility |
| *OOM even after cache reset* | Reduce batch size, use gradient accumulation, or request more GPU memory |
| *Accelerate hangs* | Make sure ports are open between nodes; pass `main_process_port` explicitly |

Need help?  Join us on [Slack](https://zenml.io/slack).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
