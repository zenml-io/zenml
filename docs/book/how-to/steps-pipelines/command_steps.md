---
description: Run arbitrary commands as pipeline steps
---

# Command Steps

A command step runs an arbitrary command as a step in your pipeline instead of a Python function. Use the `CommandStep` class to wrap any command, and add it to a pipeline like any other step:

```python
from zenml import CommandStep, pipeline

train = CommandStep(command=["python", "train.py"])
report = CommandStep(command=["bash", "-c", "echo 'done'"])

@pipeline(dynamic=True, enable_cache=False)
def my_pipeline() -> None:
    train()
    report()

if __name__ == "__main__":
    my_pipeline()
```

The command is whatever you would type in a shell, split into a list. The image just needs to contain the binary you invoke. Shell features like pipes and `&&` need an explicit shell, for example `["bash", "-c", "a | b"]`.

## Running a Python function

Instead of a command, you can pass a Python function. ZenML extracts the source code of the function and runs it with `python -c`:

```python
from zenml import CommandStep

def train() -> None:
    import json

    print(json.dumps({"status": "training"}))

train_step = CommandStep(command=train)
```

The extracted source code is the entire program, nothing around the function travels with it. This means the function must be self-contained:

- All imports must happen inside the function body. Module-level imports are not available.
- The function must not reference module-level variables, constants, or other functions.
- The function must not take any parameters, be decorated, or be defined inside another function.

ZenML rejects parameters, decorators, and references to enclosing functions when the step is created. The execution environment only needs a `python` binary on the `PATH`, ZenML does not have to be installed.

## Running without ZenML in the image (dynamic pipelines only)

A regular step runs your Python function inside the container, so the image has to contain `zenml`, your step code, and all of its dependencies. A command step does not. ZenML treats the command as a black box and never imports anything inside the container, so you can run an image that does not have `zenml` installed.

Point a command step at such an image with the existing Docker settings:

```python
from zenml import CommandStep
from zenml.config import DockerSettings

train = CommandStep(
    command=["python", "train.py"],
    step_operator="sagemaker",
    settings={
        "docker": DockerSettings(skip_build=True, parent_image="my-registry/train:latest")
    },
)
```

The image must be pullable by the execution backend and already carry your code and libraries.

## Where command steps run

A command step follows the same execution routing as any other step. It can run:

- On a **step operator**, in both static and dynamic pipelines.
- As an **isolated step** (dynamic pipelines only)
- **Locally as a subprocess** as an inline step (dynamic pipelines only)

A static pipeline without a step operator is rejected at compile time. Attach a step operator, or use a dynamic pipeline.

## Configuring a command step

A command step is a regular step. It takes the same options as any other step (step operator, settings, resources, retry, environment, secrets, and so on), either in the constructor or through `.with_options()` and `.configure()`:

```python
train = CommandStep(command=["python", "train.py"], step_operator="sagemaker")

@pipeline(dynamic=True)
def my_pipeline() -> None:
    train.with_options(environment={"EPOCHS": "10"}, secrets=["my_api_key"])()
```

Environment variables and secrets are passed to the command as environment variables. The step succeeds when the command exits with status `0` and fails on any non-zero exit. See [Configuration](configuration.md) for the full set of options and the difference between `.with_options()` and `.configure()`.

## Multi-node distributed training

For **multi-node** distributed training, a command step is the recommended launcher: point the command at a tool that owns the worker gang (TorchX, Ray) while ZenML owns the run. It's also one option for single-node multi-GPU (for example wrapping `torchrun`), though a native step works there too. See [Train with GPUs and Accelerate](../../user-guide/tutorial/distributed-training.md) for all the patterns and worked examples.

## Limitations

- Command steps do not support inputs and outputs.
- Your code is not downloaded into the execution environment.
- `get_step_context()`, metadata, visualizations, and tags are not available inside the command.
- Logs of command steps are not tracked by ZenML. They stay in the backend's native logging (for example CloudWatch or pod logs).
- Step hooks are not allowed.
- Steps in static pipelines without a step operator are not supported.
- Functions passed as commands must be self-contained (see [Running a Python function](#running-a-python-function)).
