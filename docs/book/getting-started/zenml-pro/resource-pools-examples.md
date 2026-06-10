---
description: >-
  End-to-end ZenML Pro resource pool examples rooted in real workload scenarios:
  admin configuration, author ResourceSettings, and reconciler outcomes.
---
# Resource pool examples (workbook)

Read this page like a short course. Each section is one scenario drawn from
common platform requirements: shared GPUs, protected production training,
inference reclaim, evening job queues, and multi-cluster placement.

Every section shows three layers:

1. Admin — pool, classes, policies (UI JSON unless noted)
2. Author — `ResourceSettings` on a step
3. Outcome — what the reconciler does

Assumptions unless stated otherwise:

* Pipelines are dynamic.
* One step run at a time per example unless the story is about contention.
* Admin JSON shapes match what you configure in the ZenML Pro UI.
* CLI examples use flat capacity and map to a single `default` class.


{% hint style="info" %}
Resource pools apply only to dynamic pipelines. Static pipelines do not create
resource requests or wait for allocation.
{% endhint %}

{% hint style="warning" %}
Admin pitfalls that cause author-facing rejections:

* GPU-only pools or policies — also model `CPU`, `memory`, and `step run`.
* Grants that omit a resource the step requests — rejected even when the pool is idle.
* Grants that try to reserve more than the pool's capacity for the same resource and class.
* `reclaim_tolerance: none` without matching reserved grants — rejected immediately.
* Multiple pools on one component — one pool wins; every candidate pool must cover all demands.

There is no unbounded fallback for CPU, memory, or step slots.
{% endhint %}

For definitions see [Core concepts](resource-pools-core-concepts.md). For
preemption and leases see [Reconciliation process](resource-pools-reconciliation.md).

---

## Primer: from ResourceSettings to demands

```python
from zenml.config import ResourceSettings

ResourceSettings(
    gpu_count=2,
    cpu_count=4,
    memory="16GiB",
)
```

ZenML converts this into demands on the resource request:

| Source | Demand | Example |
| --- | --- | --- |
| `gpu_count` | `kind: gpu`, quantity 2 | Matches `GPU` descriptor |
| `cpu_count` | `kind: cpu`, quantity 4, unit `CPU` | Matches `CPU` descriptor |
| `memory` | `kind: memory`, quantity 16, unit `GiB` | Matches `memory` descriptor |
| Server (isolated step) | `kind: step_run`, quantity 1 | Throttle concurrent steps |

Typed fields use kind. Custom entries in `resources` use descriptor name.

---

## 1. Quick start: one shared GPU pool (CLI)

Teams that share one GPU pool without manual booking can bootstrap with a single
default capacity class and a simple component policy.

### Admin

```shell
zenml resource-pool create team-gpus \
  --capacity '{"GPU": 8}' \
  --description "Shared team GPUs"

zenml resource-pool attach-policy team-gpus ml-k8s-orch \
  --component-type orchestrator \
  --priority 10 \
  --reserved '{"GPU": 4}' \
  --limit '{"GPU": 8}'
```

Under the hood: one `default` class per resource, `reclaimable: never`.

### Author

```python
from zenml import step
from zenml.config import ResourceSettings

@step(
    settings={
        "resources": ResourceSettings(gpu_count=2),
    }
)
def train() -> None:
    ...
```

### Outcome

Request demands `kind: gpu`, quantity 2. Reconciler allocates from `team-gpus`
through `ml-k8s-orch`'s policy. If two GPUs are free, step runs immediately;
otherwise status `pending` until release.

---

## 2. Production reserved vs experiment burst

Keep production on reserved capacity while experiments use adhoc capacity
opportunistically, without preemption between the two tiers.

### Admin (UI)

Pool with reserved and adhoc classes:

```json
{
  "name": "datacenter-gpus",
  "capacity": [
    {
      "resource": "GPU",
      "class": "reserved",
      "quantity": 8,
      "rank": 100,
      "reclaimable": "never"
    },
    {
      "resource": "GPU",
      "class": "adhoc",
      "quantity": 8,
      "rank": 50,
      "reclaimable": "never"
    }
  ]
}
```

Production policy (high priority, reserved grant):

```json
{
  "pool": "datacenter-gpus",
  "component_id": "<prod-orch-uuid>",
  "priority": 100,
  "grants": [
    {
      "resource": "GPU",
      "class_name": "reserved",
      "reserved": 4,
      "limit": 4
    }
  ]
}
```

Sandbox policy (low priority, adhoc only):

```json
{
  "pool": "datacenter-gpus",
  "component_id": "<sandbox-orch-uuid>",
  "priority": 10,
  "grants": [
    {
      "resource": "GPU",
      "class_name": "adhoc",
      "reserved": 0,
      "limit": 8
    }
  ]
}
```

### Author — production

```python
from zenml.enums import ResourceRequestReclaimTolerance

@step(
    settings={
        "resources": ResourceSettings(
            gpu_count=2,
            gpu_class="reserved",
            reclaim_tolerance=ResourceRequestReclaimTolerance.NONE,
        )
    }
)
def production_train() -> None:
    ...
```

### Author — experiment

```python
@step(
    settings={
        "resources": ResourceSettings(gpu_count=2),
    }
)
def eval_job() -> None:
    ...
```

### Outcomes

| Case | Result |
| --- | --- |
| Production, 2 GPUs free in reserved | Allocated from `reserved` class |
| Production, reserved full | `pending` — never borrows adhoc |
| Experiment, adhoc free | Allocated from `adhoc` |
| Experiment while production holds reserved | Runs in adhoc only; not a victim while production uses `none` tolerance |

---

## 3. Two teams, same priority, not enough GPUs

When demand exceeds supply at equal priority, jobs wait in a fair queue rather
than failing or competing outside the pool.

### Admin (UI)

Pool: 8 `GPU` in one `default` class (or use CLI from section 1).

Two policies at priority 10, each with a `GPU/default` grant using
`reserved: 4`, `limit: 8` on different orchestrators. The pool has 8 GPUs, so
the two reservations exactly fill the reservable capacity for that class.

### Author (both teams)

```python
@step(settings={"resources": ResourceSettings(gpu_count=2)})
def train() -> None:
    ...
```

### Outcome

Four concurrent steps fit (8 GPUs). A fifth request → `pending`. Reconciler
orders by reserved-fit, then priority, then FIFO. As steps complete, queued
steps allocate without manual intervention.

---

## 4. Higher priority wins; lower may be preempted

This pattern implements priority-aware scheduling within one cluster: higher-
priority work proceeds first and may reclaim capacity from lower-priority jobs
that accept it.

### Admin (UI)

Use an 8-GPU pool with one `default` class. Production policy priority 100
uses a `GPU/default` grant with `reserved: 4`, `limit: 4`. Sandbox policy
priority 10 uses a `GPU/default` grant with `reserved: 0`, `limit: 8`.

### Flow

1. Sandbox step holds 6 GPUs (`reclaim_tolerance` default `any` on isolated step).
2. Production submits needing 4 GPUs; its reserved share has headroom but raw
   class capacity is tight.
3. Reconciler preempts sandbox victims (lower priority, reclaimable).
4. Production allocates; sandbox re-queues if retries configured.

### Outcome

Production proceeds. Sandbox sees `preempting` → retry or failure without
retries. UI shows `preemption_initiated_by_id` on victim request.

---

## 5. Declare H200; platform picks the cluster

Authors request a hardware class by descriptor name; ZenML routes the step to a
pool and operator that expose matching capacity.

### Admin (UI)

Descriptor (`kind: "gpu"` so `gpu_count` applies):

```json
{
  "name": "h200",
  "kind": "gpu",
  "attributes": {"vram_gb": 141, "vendor": "nvidia"}
}
```

Pool (aggregate across clusters):

```json
{
  "name": "org-h200-gpus",
  "capacity": [
    {
      "resource": "h200",
      "class": "reserved",
      "quantity": 24,
      "rank": 100,
      "reclaimable": "never"
    }
  ]
}
```

Policies attach the same pool to multiple step operators (`eu-west-gpu-op`,
`eu-north-gpu-op`) with different priorities or reserved splits.

Component settings on the class map each operator to its node selectors (see
[Admin guide](resource-pools-admin-guide.md)).

### Author

Preferred — typed fields match any `gpu`-kind descriptor (including `h200`):

```python
@step(
    step_operator=["eu-west-gpu-op", "eu-north-gpu-op"],
    settings={
        "resources": ResourceSettings(
            gpu_count=1,
            gpu_class="reserved",
        )
    },
)
def train() -> None:
    ...
```

When several `gpu`-kind descriptors exist and the author must pin a specific
one, use the descriptor name in `resources`:

```python
ResourceSettings(resources={"h200": 1}, gpu_class="reserved")
```

### Outcome

Request lists candidate step operators. Reconciler picks an eligible operator
with policy access and free `h200` / `reserved` capacity. Author does not
select cluster or region in code. Step run metadata shows which operator won.

---

## 6. Per-node pools and Kubernetes placement

When capacity spans several Kubernetes nodes, separate pools with placement
settings let you target individual nodes or node groups.

### Admin (UI)

Two pools:

```json
[
  {
    "name": "node-a-gpus",
    "attributes": {"kubernetes_node": "node-a"},
    "capacity": [
      {
        "resource": "h200",
        "class": "reserved",
        "quantity": 8,
        "rank": 100,
        "reclaimable": "never",
        "component_settings": [
          {
            "component_type": "step_operator",
            "flavor": "kubernetes",
            "settings": {
              "pod_settings": {
                "node_selectors": {"kubernetes.io/hostname": "node-a"}
              }
            }
          }
        ]
      }
    ]
  },
  {
    "name": "node-b-gpus",
    "attributes": {"kubernetes_node": "node-b"},
    "capacity": [
      {
        "resource": "h200",
        "class": "reserved",
        "quantity": 8,
        "rank": 100,
        "reclaimable": "never",
        "component_settings": [
          {
            "component_type": "step_operator",
            "flavor": "kubernetes",
            "settings": {
              "pod_settings": {
                "node_selectors": {"kubernetes.io/hostname": "node-b"}
              }
            }
          }
        ]
      }
    ]
  }
]
```

One step operator policy per pool, same component, different priorities if
primary/fallback.

### Author

```python
ResourceSettings(gpu_count=1, gpu_class="reserved")
```

### Outcome

Reconciler selects pool with free capacity and matching policy. Allocation
carries `component_settings` for that node. The step operator schedules the pod
with the configured node selector; GPU, CPU, and memory requests come from the
author's `ResourceSettings`.

---

## 7. Custom scarce resource (license)

The same pool model applies to scarce non-GPU resources—such as license seats—
when you define a custom descriptor and declare pool capacity for it.

### Admin (UI)

Descriptor `training-license`. Pool class `default` quantity 4. Policy grant
uses `class_name: "default"`, `reserved: 2`, and `limit: 4` for the
orchestrator.

### Author

```python
@step(
    settings={
        "resources": ResourceSettings(
            resources={"training-license": 1},
            reclaim_tolerance=ResourceRequestReclaimTolerance.NONE,
        )
    }
)
def licensed_train() -> None:
    ...
```

### Outcome

Demand uses `resource: "training-license"` by name. Non-reclaimable request must
fit grant reserved. Missing descriptor or grant → `rejected`.

---

## 8. Ten sweeps at 6pm — queue the rest

When one engineer submits many jobs at once, work beyond immediate capacity
waits in the pool queue until slots free up.

### Setup

Pool with 4 GPUs. Single policy. User launches ten dynamic runs, each step
`gpu_count=1`.

### Outcome

1. Four requests → `allocated` immediately.
2. Six → `pending`.
3. As each run finishes, next pending allocates.
4. Morning: all ten complete without manual release.

Inspect queue:

```shell
zenml resource-pool requests team-gpus --view queued
```

---

## 9. Why is my run queued?

Queue and rejection states include human-readable reasons so you can see why a
run is waiting or was denied.

### Situations

| `status_reason` (examples) | Meaning |
| --- | --- |
| Waiting for reserved capacity | Non-reclaimable ask; reserved slice full |
| Waiting for any capacity | Pool full for requested class |
| Waiting behind higher priority | Contention with higher-priority policy |
| Blocked by external reclaim | External priority-lane activity |

### Author action

```shell
zenml resource-request describe <request-id>
```

Check `status`, `status_reason`, `queued_at`, and linked step run in the UI.

No Slack ping to the admin required for basic queue weather.

---

## 10. Inference scales up; eval yields the GPU

When external inference scales up on shared nodes, priority-lane policies let it
reclaim capacity from opportunistic ZenML jobs.

### Admin (UI)

Per-node pool `prod-eu-node-b` (section 6). Priority-lane grantless policy for
`external-workload-bridge` service account.

### External client (night — eval borrowed capacity)

Service account creates request for 4 `h200` on `node-b` with lease renewals
while ZenML eval pods run on borrowed adhoc capacity.

### External client (9am — inference scales)

Watcher creates or renews priority-lane request needing 4 GPUs. Reconciler
preempts lower-priority ZenML allocations with `coordinated` or `any`
tolerance.

### ZenML eval step

Was running with default reclaim tolerance. Heartbeat sees `preempting` → step
cancels → retries if configured → `pending` until night when adhoc frees.

### Outcome

Inference schedules immediately. Eval returns automatically when capacity
reopens. Admin sees external request and preemption chain in UI.

See [External workloads](resource-pools-external-workloads.md) for API details.

---

## Multiple pools, one request

When one orchestrator or step operator is attached to pools in more than one
region or node group, each step still produces a single request. ZenML queues
it against every eligible pool and allocates from whichever can satisfy all
demands first.

{% hint style="warning" %}
Several policies on the same stack component mean several pools may try to
satisfy the same request, but only one pool can win. ZenML does not take GPUs
from one pool and CPU from another for one step.

Every pool and policy must include all resources authors might request —
`CPU`, `memory`, `step run`, GPUs, and custom descriptors — or that pool
cannot win even if it has spare GPUs.
{% endhint %}

### Admin (UI)

Primary pool `eu-west-gpus` and fallback `eu-north-gpus`. Both attach to the
same step operator. Each pool declares `GPU`, `CPU`, `memory`, and `step run`
capacity. Each policy grants all four resources (not GPU-only).

### Author

```python
@step(
    settings={
        "resources": ResourceSettings(
            gpu_count=2,
            cpu_count=8,
            memory="32GiB",
        )
    }
)
def train() -> None:
    ...
```

### Outcome

One request with gpu, cpu, memory, and step_run demands queues in both pools.
The reconciler picks the higher-priority policy's pool when both can satisfy
the full request. If `eu-north-gpus` only modeled `GPU`, it never wins this
step even when GPUs are idle there.

---

## Hard rejections (no queue)

### Request exceeds pool capacity

Author `gpu_count=10`, pool total 8 → `rejected` immediately.

### Request exceeds grant limit

Author `gpu_count=6`, policy limit 4 → `rejected` even if pool has 8 free.

### Non-reclaimable above reserved

Author `reclaim_tolerance: none`, `gpu_count=6`, grant reserved 4 → `rejected`.

### Demand not in pool or policy

Author requests CPU and memory; pool or grants only cover `GPU` → `rejected`
(no unbounded fallback for `CPU`, `memory`, or `step run`).

### Non-reclaimable with zero reserved

Author `reclaim_tolerance: none`, grant has `reserved: 0` for a demanded
resource → `rejected` immediately.

---

## See also

* [Resource pools](resource-pools.md) — overview
* [Admin guide](resource-pools-admin-guide.md) — configure pools and policies
* [User guide](resource-pools-user-guide.md) — ResourceSettings reference
* [How preemption works](resource-pools-reconciliation.md#how-preemption-works)
* [Step configuration](https://docs.zenml.io/how-to/steps-pipelines/configuration)
