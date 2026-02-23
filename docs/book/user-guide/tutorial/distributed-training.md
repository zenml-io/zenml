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

## 4 Troubleshooting & Tips

| Problem | Quick fix |
|---------|-----------|
| *GPU is unused* | Verify CUDA toolkit inside container (`nvcc --version`), check driver compatibility |
| *OOM even after cache reset* | Reduce batch size, use gradient accumulation, or request more GPU memory |
| *Accelerate hangs* | Make sure ports are open between nodes; pass `main_process_port` explicitly |

Need help?  Join us on [Slack](https://zenml.io/slack).