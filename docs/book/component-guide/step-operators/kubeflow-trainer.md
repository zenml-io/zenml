---
description: Executing distributed training steps with Kubeflow Trainer v2.
---

# Kubeflow Trainer

ZenML's Kubeflow Trainer step operator runs individual steps as Kubeflow Trainer v2 `TrainJob` resources.

This is the preferred cluster-native interface for multi-node training on Kubernetes when you want to keep the usual ZenML pipeline/step authoring style.

## When to use it

You should use the Kubeflow Trainer step operator if:

- you run on Kubernetes with Kubeflow Trainer v2 CRDs installed,
- your training step needs multiple nodes and/or multiple GPUs,
- you want distributed training while keeping ZenML lifecycle handling in one place.

## Prerequisites

- ZenML `kubeflow` integration installed:

```shell
zenml integration install kubeflow
```

- A Kubernetes cluster with Kubeflow Trainer v2 installed.
- A remote artifact store in your active stack.
- A container registry and image builder in your active stack.

## Register and use the step operator

Register the step operator:

```shell
zenml step-operator register kubeflow_trainer_op \
  --flavor kubeflow_trainer \
  --runtime_ref_name pytorch-ddp
```

Add it to your stack:

```shell
zenml stack update -s kubeflow_trainer_op
```

Use it in a step:

```python
from zenml import step
from zenml.config import ResourceSettings
from zenml.integrations.kubeflow.flavors import KubeflowTrainerStepOperatorSettings

trainer_settings = KubeflowTrainerStepOperatorSettings(
    runtime_ref_name="pytorch-ddp",
    num_nodes=2,
    num_proc_per_node=2,
    poll_interval_seconds=5,
)

@step(
    step_operator=True,
    settings={
        "resources": ResourceSettings(gpu_count=2, cpu_count=8, memory="32GiB"),
        "step_operator": trainer_settings,
    },
)
def train_step(...):
    ...
```

With the example above, Trainer requests 2 nodes and each node requests 2 GPUs from `ResourceSettings`.

## Decorator sugar: `run_with_trainer`

If you prefer an Accelerate-style decorator:

```python
from zenml import step
from zenml.integrations.kubeflow.steps import run_with_trainer

@run_with_trainer(
    runtime_ref_name="pytorch-ddp",
    num_nodes=2,
    num_proc_per_node=2,
)
@step
def train_step(...):
    ...
```

The decorator enables step-operator execution for the step and injects `KubeflowTrainerStepOperatorSettings` for you.

## Distributed environment compatibility

Kubeflow Trainer runtimes can expose distributed metadata via `PET_*`
environment variables. ZenML normalizes these values to standard PyTorch
distributed variables (`RANK`, `WORLD_SIZE`, `MASTER_ADDR`, `MASTER_PORT`,
`LOCAL_RANK`) before user step code runs.

This lets steps that call `torch.distributed.init_process_group(...)` work out
of the box with Trainer v2 runtimes while preserving any explicit torch env
variables you already set in your runtime or step configuration.

## Configuration

Configurable fields (via step operator config or `KubeflowTrainerStepOperatorSettings`):

- `runtime_ref_name`
- `runtime_ref_kind`
- `runtime_ref_api_group`
- `num_nodes`
- `num_proc_per_node`
- `trainer_overrides`
- `trainer_env`
- `pod_template_overrides`
- `poll_interval_seconds`
- `timeout_seconds`
- `delete_trainjob_after_completion`
- `kubernetes_namespace`
- `incluster`
- `kubernetes_context`
- `image`

For backwards compatibility, `ml_policy` and `pod_template_override` are still
accepted and mapped into `spec.trainer`, but they are deprecated in favor of
`num_proc_per_node`, `trainer_overrides`, and `pod_template_overrides`.
