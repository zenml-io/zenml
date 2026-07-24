---
description: >-
  How pipeline authors request pooled resources with ResourceSettings and
  inspect Resource Manager requests.
---
# User guide

This guide is for pipeline authors. Platform admins configure descriptors,
pools, classes, and policies in the ZenML Pro UI. Authors express resource
intent on dynamic pipeline steps with `ResourceSettings`.

{% hint style="info" %}
Resource pools apply only to [dynamic pipelines](https://docs.zenml.io/how-to/steps-pipelines/dynamic_pipelines).
{% endhint %}

## What you configure

Most steps use the typed resource settings:

```python
from zenml import pipeline, step
from zenml.config import ResourceSettings


@step(
    settings={
        "resources": ResourceSettings(
            gpu_count=2,
            gpu_class="h200-reserved",
            cpu_count=8,
            memory="64GiB",
            reclaim_tolerance="none",
        )
    }
)
def train() -> None:
    ...


@pipeline(dynamic=True)
def training_pipeline() -> None:
    train()
```

| Setting | Meaning |
| --- | --- |
| `gpu_count` | Number of GPUs requested; becomes a demand with `kind: "gpu"` |
| `gpu_class` | Optional exact pool class, such as `h200-reserved` |
| `cpu_count` | CPU cores requested; becomes a demand with `kind: "cpu"` and unit `CPU` |
| `memory` | Memory requested, such as `64GiB`; becomes a demand with `kind: "memory"` |
| `resources` | Advanced custom resource demands by descriptor name, kind, or selector |
| `reclaim_tolerance` | Whether the step may be interrupted for pool reasons |
| `allocation_wait_timeout_seconds` | How long the launcher waits for allocation before failing |

ZenML creates the resource request when the dynamic step is ready to launch.
If capacity is available, the request is allocated and the step runs. If not,
the request stays queued. If no policy, class, or grant path can satisfy the
request, ZenML rejects it with a status reason.

## Demand translation

Typed settings translate into Resource Manager demands by kind:

| ResourceSettings field | Demand shape |
| --- | --- |
| `gpu_count=2` | `{"kind": "gpu", "quantity": 2}` |
| `gpu_count=2, gpu_class="h200-reserved"` | `{"kind": "gpu", "quantity": 2, "class": "h200-reserved"}` |
| `cpu_count=8` | `{"kind": "cpu", "quantity": 8, "unit": "CPU"}` |
| `memory="64GiB"` | `{"kind": "memory", "quantity": 64, "unit": "GiB"}` |

Pool classes may contain resource bundles, so a single class can satisfy GPU,
CPU, and memory together. If your step requests CPU or memory, the winning
class and policy must account for those resources too, unless the policy uses a
grantless access model.

## Custom resources

Use custom resources when your admin created descriptors outside the stock
CPU, memory, and GPU language. For example, a training license:

```python
from zenml.config import ResourceSettings
from zenml.models import ResourceRequestDemand

license_settings = ResourceSettings(
    resources=[
        ResourceRequestDemand(
            resource="training-license",
            quantity=1,
            unit="seat",
        )
    ],
)
```

Ask your admin for descriptor names, supported units, and class names. Typed
fields match descriptors by kind, while custom demands can use exact names.

## Reclaim tolerance

Reclaim tolerance tells ZenML whether your step may be interrupted when higher
priority work needs capacity.

| Value | Meaning | Typical use |
| --- | --- | --- |
| `none` | Do not interrupt this step for pool reasons | Production training or critical evaluation |
| `coordinated` | Step may be stopped and retried cleanly | Medium-priority experiments |
| `any` | Best effort; may use unsafe or externally reclaimable capacity | Sweeps and opportunistic runs |

Non-reclaimable requests can only run on classes with `reclaimable: "never"`.
For grant-based policies in authoritative mode, they must also fit the
reserved grant share. If they do not, the request is rejected instead of
waiting forever.

Legacy `preemptible=False` maps to `reclaim_tolerance="none"`;
`preemptible=True` maps to `"coordinated"`. Prefer `reclaim_tolerance` in new
code.

## Waiting for allocation

Use `allocation_wait_timeout_seconds` to control how long the launcher waits
for capacity:

```python
ResourceSettings(
    gpu_count=1,
    cpu_count=4,
    memory="32GiB",
    reclaim_tolerance="coordinated",
    allocation_wait_timeout_seconds=1800,
)
```

This timeout affects how long the step launcher waits. It does not change pool
capacity, policy priority, or grant limits.

## Inspect requests

The workspace UI shows resource requests linked to dynamic step runs, including
status, selected pool, selected class, queue state, and status reason.

The ZenML CLI can inspect resource requests:

```shell
zenml resource-request list --status pending
zenml resource-request list --pool-id <pool-id>
zenml resource-request list --step-run-id <step-run-id>
zenml resource-request describe <request-id>
```

Supported list filters include user, reclaim tolerance, component ID, step-run
ID, preemption initiator ID, status, pipeline-run ID, and pool ID.

## Statuses

| Status | What it means for your step |
| --- | --- |
| `pending` | The request is admitted and queued. The step waits for allocation. |
| `allocated` | Capacity was granted. The step can run with merged target settings. |
| `rejected` | The request cannot be satisfied by matching policies, classes, or grants. |
| `preempting` | ZenML is asking the step owner to stop so capacity can be reclaimed. |
| `preempted` | The step was stopped by resource-pool preemption. Configure retries if it should re-queue. |
| `cancelled` | The request was cancelled before allocation. |
| `released` | The step finished and capacity was returned. |
| `expired` | The allocated request stopped renewing its lease and capacity was returned. |

## Common issues

| Symptom | Likely cause | What to do |
| --- | --- | --- |
| `No resource policy admitted this request.` | No matching policy, no matching pool target, wrong class, or a grant omitted a demanded resource | Check stack component, team/project policy, `gpu_class`, and requested resources with your admin |
| `No grant reserved share satisfies this request with reclaim_tolerance 'none'.` | Non-reclaimable request exceeded grant reservations | Lower reclaim tolerance for best-effort work or ask for reserved grants |
| Step queues longer than expected | Capacity is occupied, a higher-priority queue is ahead, or a concurrency limit is reached | Inspect the request status reason and pool detail page |
| CPU or memory request rejected while GPUs look idle | The matching class or grant does not cover CPU or memory | Ask the admin to model CPU and memory in the class bundle or grant defaults |
| Wrong accelerator selected | `gpu_class` is too broad or missing, or descriptors share `kind: "gpu"` | Ask for the correct class name or descriptor selector |

## Working with admins

Share these details when asking for pool access:

* The stack component you run on, usually an orchestrator or step operator.
* The team, project, pipeline, or account that should receive access.
* GPU, CPU, memory, and custom resources your step requests.
* Whether the workload is production (`reclaim_tolerance="none"`) or
  best-effort (`"coordinated"` or `"any"`).
* Whether the step needs a specific class, such as `h200-reserved` or
  `a10-burst`.

## See also

* [Resource pools](resource-pools.md) - overview.
* [Core concepts](resource-pools-core-concepts.md) - descriptors, classes,
  policies, subjects, and requests.
* [Examples](resource-pools-examples.md) - scenarios with admin setup and
  author settings.
* [Reconciliation process](resource-pools-reconciliation.md) - queueing,
  preemption, leases, and accounting modes.
