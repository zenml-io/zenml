---
description: Run distributed training with Hugging Face's Accelerate library in ZenML pipelines.
---

# Distributed training with 🤗 Accelerate

There are several reasons why you might want to scale your machine learning pipelines to utilize distributed training, such as leveraging multiple GPUs or training across multiple nodes. ZenML now integrates with [Hugging Face's Accelerate library](https://github.com/huggingface/accelerate) to make this process seamless and efficient.

## Use 🤗 Accelerate in your steps

Some steps in your machine learning pipeline, particularly training steps, can benefit from distributed execution. You can now use the `run_with_accelerate` decorator to enable this:

```python
from zenml import step, pipeline
from zenml.integrations.huggingface.steps import run_with_accelerate

@run_with_accelerate(num_processes=4, multi_gpu=True)
@step
def training_step(some_param: int, ...):
    # your training code is below
    ...

@pipeline
def training_pipeline(some_param: int, ...):
    training_step(some_param, ...)
```

The `run_with_accelerate` decorator wraps your step, enabling it to run with Accelerate's distributed training capabilities. It accepts arguments available to `accelerate launch` CLI command.

{% hint style="info" %}
For a complete list of available arguments and more details, refer to the [Accelerate CLI documentation](https://huggingface.co/docs/accelerate/en/package_reference/cli#accelerate-launch).
{% endhint %}

### Configuration

The `run_with_accelerate` decorator accepts various arguments to configure your distributed training environment. Some common arguments include:

- `num_processes`: The number of processes to use for distributed training.
- `cpu`: Whether to force training on CPU.
- `multi_gpu`: Whether to launch distributed GPU training.
- `mixed_precision`: Mixed precision training mode ('no', 'fp16', or 'bf16').

### Important Usage Notes

1. The `run_with_accelerate` decorator can only be used directly on steps using the '@' syntax. Using it as a function inside the pipeline definition is not allowed.

2. Accelerated steps do not support positional arguments. Use keyword arguments when calling your steps.

3. If `run_with_accelerate` is misused, it will raise a `RuntimeError` with a helpful message explaining the correct usage.

{% hint style="info" %}
To see a full example where Accelerate is used within a ZenML pipeline, check out our [llm-lora-finetuning](https://github.com/zenml-io/zenml-projects/blob/main/llm-lora-finetuning/README.md) project which leverages the distributed training functionalities while finetuning an LLM.
{% endhint %}

## Ensure your container is Accelerate-ready

To run steps with Accelerate, it's crucial to have the necessary dependencies installed in the environment. This section will guide you on how to configure your environment to utilize Accelerate effectively.

{% hint style="warning" %}
Note that these configuration changes are **required** for Accelerate to function properly. If you don't update the settings, your steps might run, but they will not leverage distributed training capabilities.
{% endhint %}

All steps using Accelerate will be executed within a containerized environment. Therefore, you need to make two amendments to your Docker settings for the relevant steps:

### 1. Specify a CUDA-enabled parent image in your `DockerSettings`

For complete details, refer to the [containerization page](../../infrastructure-deployment/customize-docker-builds/README.md). Here's an example using a CUDA-enabled PyTorch image:

```python
from zenml import pipeline
from zenml.config import DockerSettings

docker_settings = DockerSettings(parent_image="pytorch/pytorch:1.12.1-cuda11.3-cudnn8-runtime")

@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```

### 2. Add Accelerate as explicit pip requirements

Ensure that Accelerate is installed in your container:

```python
from zenml.config import DockerSettings
from zenml import pipeline

docker_settings = DockerSettings(
    parent_image="pytorch/pytorch:1.12.1-cuda11.3-cudnn8-runtime",
    requirements=["accelerate", "torchvision"]
)

@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```

## Train across multiple GPUs

ZenML's Accelerate integration supports training your models with multiple GPUs on a single node or across multiple nodes. This is particularly useful for large datasets or complex models that benefit from parallelization.

In practice, using Accelerate with multiple GPUs involves:

- Wrapping your training step with the `run_with_accelerate` function in your pipeline definition
- Configuring the appropriate Accelerate arguments (e.g., `num_processes`, `multi_gpu`)
- Ensuring your training code is compatible with distributed training (Accelerate handles most of this automatically)

{% hint style="info" %}
If you're new to distributed training or encountering issues, please [connect with us on Slack](https://zenml.io/slack) and we'll be happy to assist you.
{% endhint %}

By leveraging the Accelerate integration in ZenML, you can easily scale your training processes and make the most of your available hardware resources, all while maintaining the structure and benefits of your ZenML pipelines.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
