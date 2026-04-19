---
description: >-
  Step-by-step ZenML Pro resource pool examples: pool JSON, policy JSON,
  ResourceSettings, and outcomes for new users.
---
# Resource pool examples (workbook)

Read this page like a short course: each section is one self-contained scenario.
You will always see three things—the pool (shared capacity), the policy (how one
orchestrator or step operator may use that pool), and the step
(`ResourceSettings`). Then we spell out what the server does.

**Assumptions unless stated otherwise:**

* Steps are preemptible by default if you omit `preemptible=False`.
* One step run at a time when we say “no other work is running,” so you can
  focus on a single decision.
* Every key in a policy’s `reserved` and `limit` must exist on the pool’s
  capacity. You cannot meter a resource in policy that the pool does not
  define.
* If one orchestrator or step operator has policies to several pools, the step
  still receives at most one allocation from one pool. The whole request must be
  eligible on that pool; resources are not split across pools for a single step.

For definitions of reserved, limit, and priority, see
[Core concepts](resource-pools-core-concepts.md). Preemption-ordering
documentation is forthcoming.

## Primer: from `ResourceSettings` to the resource request

Say a step declares:

```python
from zenml.config import ResourceSettings

ResourceSettings(
    gpu_count=2,
    cpu_count=4,
    memory="16GiB",
    pool_resources={"tensorrt_sessions": 1},
    preemptible=True,
)
```

ZenML turns that into one resource request. Roughly:

| Source | Request key | How the amount is derived | Example value |
| --- | --- | --- | --- |
| `gpu_count` | `gpu` | Same as `gpu_count` | 2 |
| `cpu_count` | `mcpu` | `ceil(cpu_count * 1000)` | 4000 |
| `memory` | `memory_mb` | Converted to megabytes | 17180 (for `"16GiB"`) |
| `pool_resources` | (your names) | Copied as-is, merged with typed fields | 1 |
| Server | `step_run` | Always 1 per step | 1 |

The pool must define capacity for bounded keys such as `gpu` and
`tensorrt_sessions`. If the pool has no row for `mcpu`, `memory_mb`, or
`step_run`, that dimension is unbounded at the pool layer (see the examples
below). For everything else, a missing pool row means zero capacity. If you want
a policy to set `reserved` / `limit` on a key, that key must appear on the pool
first—policy keys are always a subset of pool keys.

---

## Warm-up: one pool, one policy, only GPUs

### Preemptible step borrows past reserved

**Story:** The team has four GPUs “labeled” for them, but the pool is empty.
They ask for six GPUs and allow preemption. They may borrow two idle GPUs.

**Pool**

```json
{
  "name": "datacenter-gpus",
  "capacity": {
    "gpu": 8
  }
}
```

**Policy** (orchestrator `team-ml-orch` attached to this pool)

```json
{
  "pool": "datacenter-gpus",
  "component": "team-ml-orch",
  "component_type": "orchestrator",
  "priority": 10,
  "reserved": {
    "gpu": 4
  },
  "limit": {
    "gpu": 8
  }
}
```

**Step**

```python
from zenml import step
from zenml.config import ResourceSettings


@step(
    settings={
        "resources": ResourceSettings(
            gpu_count=6,
            preemptible=True,
        )
    }
)
def train() -> None:
    ...
```

**Outcome:** Allocated immediately (no queue). Four GPUs count against the
policy reserved share; two are borrowed from free pool capacity (between
reserved and limit, and pool must still have free units).

---

### Non-preemptible step stays inside reserved

**Story:** Same pool and policy. Production wants two GPUs and opts out of
preemption. Two is within the four-GPU reservation.

**Pool**

```json
{
  "name": "datacenter-gpus",
  "capacity": {
    "gpu": 8
  }
}
```

**Policy**

```json
{
  "pool": "datacenter-gpus",
  "component": "team-ml-orch",
  "component_type": "orchestrator",
  "priority": 10,
  "reserved": {
    "gpu": 4
  },
  "limit": {
    "gpu": 8
  }
}
```

**Step**

```python
@step(
    settings={
        "resources": ResourceSettings(
            gpu_count=2,
            preemptible=False,
        )
    }
)
def production_train() -> None:
    ...
```

**Outcome:** Allocated (assuming no other contention). Non-preemptible work must
satisfy requested ≤ reserved per key; `2 ≤ 4` passes.

---

### Non-preemptible step beyond reserved

**Story:** Same pool and policy. Production asks for six GPUs but refuses
preemption. Non-preemptible work cannot use the “borrow” band above reserved.

**Pool**

```json
{
  "name": "datacenter-gpus",
  "capacity": {
    "gpu": 8
  }
}
```

**Policy**

```json
{
  "pool": "datacenter-gpus",
  "component": "team-ml-orch",
  "component_type": "orchestrator",
  "priority": 10,
  "reserved": {
    "gpu": 4
  },
  "limit": {
    "gpu": 8
  }
}
```

**Step**

```python
@step(
    settings={
        "resources": ResourceSettings(
            gpu_count=6,
            preemptible=False,
        )
    }
)
def too_large_production_train() -> None:
    ...
```

**Outcome:** Rejected immediately (dynamic run fails fast). Six exceeds reserved
(4) for `gpu`; non-preemptible requests cannot borrow up to limit.

---

## CPU, memory, and step slots: unbounded vs metered

### GPU-only pool—CPU and memory not quota’d

**Story:** You only modeled GPUs on the pool and policy. The step still sends
`mcpu` and `memory_mb` on the request, but those keys are unbounded at the pool
layer when omitted, and this policy omits them too—so they do not block
non-preemptible work.

**Pool**

```json
{
  "name": "training",
  "capacity": {
    "gpu": 4
  }
}
```

**Policy**

```json
{
  "pool": "training",
  "component": "k8s-orch",
  "component_type": "orchestrator",
  "priority": 10,
  "reserved": {
    "gpu": 2
  },
  "limit": {
    "gpu": 4
  }
}
```

**Step**

```python
@step(
    settings={
        "resources": ResourceSettings(
            gpu_count=1,
            cpu_count=32,
            memory="64GiB",
            preemptible=False,
        )
    }
)
def hungry_but_ok_on_gpu() -> None:
    ...
```

**Outcome:** Allocated if nothing else is wrong. Only `gpu` is gated here;
`mcpu` / `memory_mb` / `step_run` are not limited by pool or policy in this
pattern. CPU and memory remain informational unless you add rows later.

---

### Non-preemptible CPU inside policy reserved

**Story:** You cap milli-CPU on the pool, then split it with reserved / limit
on the policy. Non-preemptible CPU demand must fit reserved per key.

**Pool**

```json
{
  "name": "training",
  "capacity": {
    "gpu": 4,
    "mcpu": 32000
  }
}
```

**Policy**

```json
{
  "pool": "training",
  "component": "k8s-orch",
  "component_type": "orchestrator",
  "priority": 10,
  "reserved": {
    "gpu": 2,
    "mcpu": 4000
  },
  "limit": {
    "gpu": 4,
    "mcpu": 32000
  }
}
```

**Step**

```python
@step(
    settings={
        "resources": ResourceSettings(
            gpu_count=1,
            cpu_count=2,
            preemptible=False,
        )
    }
)
def fits_reserved_cpu() -> None:
    ...
```

**Outcome:** Allocated. `cpu_count=2` → `mcpu` 2000 ≤ reserved 4000, and `gpu` is
valid.

---

### Non-preemptible CPU over policy reserved

**Pool**

```json
{
  "name": "training",
  "capacity": {
    "gpu": 4,
    "mcpu": 32000
  }
}
```

**Policy**

```json
{
  "pool": "training",
  "component": "k8s-orch",
  "component_type": "orchestrator",
  "priority": 10,
  "reserved": {
    "gpu": 2,
    "mcpu": 4000
  },
  "limit": {
    "gpu": 4,
    "mcpu": 32000
  }
}
```

**Step**

```python
@step(
    settings={
        "resources": ResourceSettings(
            gpu_count=1,
            cpu_count=8,
            preemptible=False,
        )
    }
)
def exceeds_reserved_cpu() -> None:
    ...
```

**Outcome:** Rejected. `cpu_count=8` → `mcpu` 8000 > reserved 4000;
non-preemptible work cannot borrow toward limit on `mcpu`.

---

### Preemptible CPU burst with policy `mcpu` rows

**Pool** and **Policy:** same as *Non-preemptible CPU inside policy reserved*
(pool includes `gpu` and `mcpu`; policy sets both keys).

**Step**

```python
@step(
    settings={
        "resources": ResourceSettings(
            gpu_count=1,
            cpu_count=8,
            preemptible=True,
        )
    }
)
def preemptible_cpu_burst() -> None:
    ...
```

**Outcome:** May allocate using headroom up to limit on `mcpu` (and pool free
capacity), analogous to GPU borrowing.

---

### Preemptible when pool lists `mcpu` but policy omits it

**Story:** The pool caps total milli-CPU. With no `mcpu` on the policy, reserved
defaults to 0 and limit falls back to the pool total.

**Pool**

```json
{
  "name": "training",
  "capacity": {
    "gpu": 4,
    "mcpu": 8000
  }
}
```

**Policy** (only `gpu`)

```json
{
  "pool": "training",
  "component": "k8s-orch",
  "component_type": "orchestrator",
  "priority": 10,
  "reserved": {
    "gpu": 2
  },
  "limit": {
    "gpu": 4
  }
}
```

**Step**

```python
@step(
    settings={
        "resources": ResourceSettings(
            gpu_count=1,
            cpu_count=4,
            preemptible=True,
        )
    }
)
def preemptible_with_pool_mcpu() -> None:
    ...
```

**Outcome:** Allocated or queued then allocated when possible. `mcpu` 4000 ≤
effective limit 8000 (pool total).

---

### Non-preemptible when pool lists `mcpu` but policy omits it

**Pool** and **Policy:** same as the previous example.

**Step**

```python
@step(
    settings={
        "resources": ResourceSettings(
            gpu_count=1,
            cpu_count=1,
            preemptible=False,
        )
    }
)
def non_preemptible_positive_mcpu_zero_reserved() -> None:
    ...
```

**Outcome:** Rejected. Any positive `mcpu` with reserved 0 fails for
non-preemptible work. Fix: add `mcpu` to the policy with enough reserved, or
remove `mcpu` from the pool if you wanted fully unbounded CPU at the pool layer.

---

### Capping concurrent steps with `step_run`

**Story:** You want both GPUs and a ceiling on how many steps from this
orchestrator run at once. Each step always requests one `step_run`.

**Pool**

```json
{
  "name": "training",
  "capacity": {
    "gpu": 16,
    "step_run": 10
  }
}
```

**Policy**

```json
{
  "pool": "training",
  "component": "k8s-orch",
  "component_type": "orchestrator",
  "priority": 10,
  "reserved": {
    "gpu": 8,
    "step_run": 4
  },
  "limit": {
    "gpu": 16,
    "step_run": 4
  }
}
```

**Step**

```python
@step(
    settings={
        "resources": ResourceSettings(
            gpu_count=2,
            preemptible=True,
        )
    }
)
def train() -> None:
    ...
```

**Outcome:** The server grants only when both `gpu` and `step_run` have enough
free units. If GPUs are free but all `step_run` slots are taken, the request
waits in the queue.

---

## Custom keys from `pool_resources`

### Custom key fully configured

**Story:** You track a scarce license or device class with `pool_resources`.

**Pool**

```json
{
  "name": "inference",
  "capacity": {
    "gpu": 8,
    "tensorrt_sessions": 4
  }
}
```

**Policy**

```json
{
  "pool": "inference",
  "component": "gpu-step-op",
  "component_type": "step_operator",
  "priority": 10,
  "reserved": {
    "gpu": 2,
    "tensorrt_sessions": 2
  },
  "limit": {
    "gpu": 8,
    "tensorrt_sessions": 4
  }
}
```

**Step**

```python
@step(
    settings={
        "resources": ResourceSettings(
            gpu_count=1,
            pool_resources={"tensorrt_sessions": 1},
            preemptible=False,
        )
    }
)
def infer() -> None:
    ...
```

**Outcome:** Allocated when `1 ≤ reserved` for both `gpu` and
`tensorrt_sessions`. Unbounded defaults do not apply to custom keys—the pool
must list them.

---

### Custom key on pool but missing from policy

**Story:** Same pool capacity; policy only defines `gpu`.

**Pool**

```json
{
  "name": "inference",
  "capacity": {
    "gpu": 8,
    "tensorrt_sessions": 2
  }
}
```

**Policy**

```json
{
  "pool": "inference",
  "component": "gpu-step-op",
  "component_type": "step_operator",
  "priority": 10,
  "reserved": {
    "gpu": 2
  },
  "limit": {
    "gpu": 8
  }
}
```

**Step**

```python
@step(
    settings={
        "resources": ResourceSettings(
            gpu_count=1,
            pool_resources={"tensorrt_sessions": 1},
            preemptible=False,
        )
    }
)
def infer() -> None:
    ...
```

**Outcome:** Rejected. Missing policy row → reserved 0 for `tensorrt_sessions`;
non-preemptible cannot ask for a positive amount. Fix: add `tensorrt_sessions` to
the policy, or mark the step preemptible if borrowing is acceptable.

---

## Hard rejections (no queue)

### Request exceeds pool capacity

**Pool**

```json
{
  "name": "small",
  "capacity": {
    "gpu": 8
  }
}
```

**Policy**

```json
{
  "pool": "small",
  "component": "k8s-orch",
  "component_type": "orchestrator",
  "priority": 10,
  "reserved": {
    "gpu": 8
  },
  "limit": {
    "gpu": 8
  }
}
```

**Step**

```python
@step(
    settings={
        "resources": ResourceSettings(
            gpu_count=10,
            preemptible=True,
        )
    }
)
def too_big_for_planet() -> None:
    ...
```

**Outcome:** Rejected immediately. Ten exceeds the pool total for `gpu`; the
request does not join a queue.

---

### Request exceeds policy limit (pool could fit)

**Pool**

```json
{
  "name": "shared",
  "capacity": {
    "gpu": 8
  }
}
```

**Policy**

```json
{
  "pool": "shared",
  "component": "team-a-orch",
  "component_type": "orchestrator",
  "priority": 10,
  "reserved": {
    "gpu": 2
  },
  "limit": {
    "gpu": 4
  }
}
```

**Step**

```python
@step(
    settings={
        "resources": ResourceSettings(
            gpu_count=6,
            preemptible=True,
        )
    }
)
def over_team_limit() -> None:
    ...
```

**Outcome:** Rejected. Six exceeds this component’s limit (4) for `gpu`, even if
eight GPUs exist in the pool.

---

## Contention: queues and priorities

### Two teams, same priority, not enough GPUs

**Story:** Red and Blue orchestrators share one pool. Policies use the same
priority. Many preemptible steps each want 2 GPUs; the pool cannot satisfy
everyone at once.

**Pool**

```json
{
  "name": "shared",
  "capacity": {
    "gpu": 8
  }
}
```

**Policies**

```json
[
  {
    "pool": "shared",
    "component": "red-orch",
    "component_type": "orchestrator",
    "priority": 10,
    "reserved": {
      "gpu": 4
    },
    "limit": {
      "gpu": 8
    }
  },
  {
    "pool": "shared",
    "component": "blue-orch",
    "component_type": "orchestrator",
    "priority": 10,
    "reserved": {
      "gpu": 4
    },
    "limit": {
      "gpu": 8
    }
  }
]
```

**Step** (typical for either team)

```python
@step(
    settings={
        "resources": ResourceSettings(
            gpu_count=2,
            preemptible=True,
        )
    }
)
def train() -> None:
    ...
```

**Outcome:** Requests wait in the pool queue until GPUs free up. Among the same
policy priority, ordering tends to favor older waiters (FIFO-style). The
allocator also prefers a request that still fits entirely in its unused reserved
slice over one that must borrow when both are waiting—so a team with reservation
headroom is not stuck behind another team that is already bursting, if the next
grant can be served from that reserved slice. No preemption until a
higher-priority waiter or reclaim logic forces it.

---

### Higher priority wins; lower may be preempted

**Story:** Sandbox bursts with preemptible work. Production has higher policy
priority and needs GPUs when the pool is full.

**Pool**

```json
{
  "name": "shared",
  "capacity": {
    "gpu": 8
  }
}
```

**Policies**

```json
[
  {
    "pool": "shared",
    "component": "sandbox-orch",
    "component_type": "orchestrator",
    "priority": 10,
    "reserved": {
      "gpu": 4
    },
    "limit": {
      "gpu": 8
    }
  },
  {
    "pool": "shared",
    "component": "prod-orch",
    "component_type": "orchestrator",
    "priority": 100,
    "reserved": {
      "gpu": 2
    },
    "limit": {
      "gpu": 8
    }
  }
]
```

**Sandbox** (already holding six GPUs, preemptible)

```python
@step(
    settings={
        "resources": ResourceSettings(
            gpu_count=6,
            preemptible=True,
        )
    }
)
def sandbox_experiment() -> None:
    ...
```

**Prod** (new, preemptible, needs four)

```python
@step(
    settings={
        "resources": ResourceSettings(
            gpu_count=4,
            preemptible=True,
        )
    }
)
def prod_train() -> None:
    ...
```

**Outcome:** If four GPUs cannot be granted without reclaiming space, the
reconciler may preempt Sandbox’s preemptible runs (lower policy priority) so Prod
can proceed (dedicated preemption-ordering documentation is forthcoming).

---

### Production non-preemptible waits on reserved only

**Story:** Prod uses `preemptible=False` and asks only for what is reserved. If
another non-preemptible job on the same stack component already holds the reserved
GPUs, this step does not borrow from Sandbox’s burst.

**Pool**

```json
{
  "name": "shared",
  "capacity": {
    "gpu": 8
  }
}
```

**Policies** (same as previous example: Sandbox priority 10, Prod priority 100)

**Prod step**

```python
@step(
    settings={
        "resources": ResourceSettings(
            gpu_count=2,
            preemptible=False,
        )
    }
)
def prod_sla_job() -> None:
    ...
```

**Outcome:** Waits in the queue if Prod’s reserved `gpu` (2) is already used by
other non-preemptible work on `prod-orch`. It will not take Sandbox’s borrowed
GPUs. Ways out: raise reserved for Prod, wait for the other job to finish, or
use preemptible Prod work if policy allows.

---

## Multiple pools and multi-key requests

{% hint style="warning" %}
Several policies on the same stack component mean several pools may try
to satisfy the same resource request, but only one pool can win.
Every key in the request must pass that pool’s checks; ZenML does not take
`gpu` from one pool and `mcpu` from another for one step.
{% endhint %}

### Two pools on one orchestrator—primary pool wins

**Story:** You attach two policies to the same orchestrator pointing at
different pools. The step still produces one resource request, enqueued in every
eligible pool; only one pool may win.

**Pools**

```json
[
  {
    "name": "eu-west-gpu",
    "capacity": {
      "gpu": 16
    }
  },
  {
    "name": "eu-north-gpu",
    "capacity": {
      "gpu": 16
    }
  }
]
```

**Policies**

```json
[
  {
    "pool": "eu-west-gpu",
    "component": "regional-orch",
    "component_type": "orchestrator",
    "priority": 20,
    "reserved": {
      "gpu": 8
    },
    "limit": {
      "gpu": 16
    }
  },
  {
    "pool": "eu-north-gpu",
    "component": "regional-orch",
    "component_type": "orchestrator",
    "priority": 10,
    "reserved": {
      "gpu": 8
    },
    "limit": {
      "gpu": 16
    }
  }
]
```

**Step**

```python
@step(
    settings={
        "resources": ResourceSettings(
            gpu_count=1,
            preemptible=True,
        )
    }
)
def train() -> None:
    ...
```

**Outcome:** The server tries higher policy priority first—eu-west before
eu-north. Whichever pool grants first owns the allocation; the other queue entry
is dropped as stale. Use this for primary/fallback or regional capacity, not for
splitting one step across unrelated quotas.

---

### One step must satisfy every key in each pool

**Story:** Eligibility is checked per pool against all keys on the request. If a
pool lacks a key the step needs, that pool treats it as zero capacity—the request
is not eligible there.

**Pool A** (GPUs only)

```json
{
  "name": "gpu-only",
  "capacity": {
    "gpu": 8
  }
}
```

**Pool B** (full bundle)

```json
{
  "name": "gpu-and-trt",
  "capacity": {
    "gpu": 8,
    "tensorrt_sessions": 4
  }
}
```

**Policy** (example: only Pool B is attached, or imagine Pool A attached alone)

**Step**

```python
@step(
    settings={
        "resources": ResourceSettings(
            gpu_count=1,
            pool_resources={"tensorrt_sessions": 1},
            preemptible=True,
        )
    }
)
def infer() -> None:
    ...
```

**Outcome:** A pool with only `gpu` cannot satisfy `tensorrt_sessions`—that
dimension is zero there, so the request does not enqueue on that pool.

**Lesson:** Model every scarce bounded dimension you care about on one pool (or
ensure every candidate pool defines the same key set for those keys). The next
section shows how `mcpu` and `memory_mb` differ: omitting them on one pool keeps
that path eligible even when another pool meters them strictly.

---

### Two pools: higher-priority path meters CPU/RAM; GPU-only path still wins

**Story:** One orchestrator has two policies (same pattern as *Two pools on one
orchestrator—primary pool wins*). Pool B’s capacity and policy include `mcpu` and
`memory_mb`, with reserved amounts sized for small non-preemptible jobs. Pool A
only defines `gpu`; it does not list `mcpu` or `memory_mb`, so those dimensions
are unbounded at the pool layer and its policy does not reserve them. A
non-preemptible step asks for one GPU but more CPU and RAM than Pool B’s policy
allows. The higher-priority policy (Pool B) cannot grant that request; the
lower-priority policy (Pool A) can, because the request’s CPU and memory demand is
not quota’d on that path. The allocation is owned by Pool A.

**Pool A** (GPUs only—no `mcpu` or `memory_mb` on the pool)

```json
{
  "name": "gpu-only-fallback",
  "capacity": {
    "gpu": 8
  }
}
```

**Pool B** (GPUs plus metered CPU and memory)

```json
{
  "name": "metered-cpu-mem",
  "capacity": {
    "gpu": 8,
    "mcpu": 128000,
    "memory_mb": 524288
  }
}
```

**Policies** (same component, different priorities—B is preferred when both can
grant)

```json
[
  {
    "pool": "metered-cpu-mem",
    "component": "k8s-orch",
    "component_type": "orchestrator",
    "priority": 100,
    "reserved": {
      "gpu": 4,
      "mcpu": 4000,
      "memory_mb": 8192
    },
    "limit": {
      "gpu": 8,
      "mcpu": 64000,
      "memory_mb": 131072
    }
  },
  {
    "pool": "gpu-only-fallback",
    "component": "k8s-orch",
    "component_type": "orchestrator",
    "priority": 50,
    "reserved": {
      "gpu": 4
    },
    "limit": {
      "gpu": 8
    }
  }
]
```

**Step**

```python
@step(
    settings={
        "resources": ResourceSettings(
            gpu_count=1,
            cpu_count=8,
            memory="32GiB",
            preemptible=False,
        )
    }
)
def train() -> None:
    ...
```

**Outcome:** The request maps to roughly `mcpu` 8000 and tens of thousands of
`memory_mb` for `32GiB`. For non-preemptible work, each key must be ≤ policy
reserved on the path you use. Pool B’s policy reserves only `mcpu` 4000 and
`memory_mb` 8192, so that path cannot satisfy the step. Pool A’s policy has no
`mcpu` or `memory_mb` rows; with those keys absent from the pool, they are not
treated as zero capacity, so the step remains eligible there on `gpu` alone. The
reconciler allocates from Pool A and drops the competing queue row for Pool B.
If you want large non-preemptible jobs to stay on the metered pool, raise
reserved (and capacity) on Pool B for `mcpu` and `memory_mb`, or reduce demand in
`ResourceSettings`—otherwise the GPU-only policy acts as an escape hatch for
heavy CPU/RAM asks.

---

## See also

* [Resource pools](resource-pools.md) — overview
* [Core concepts](resource-pools-core-concepts.md) — pools, policies, requests
* How preemption works — preemption ordering (documentation forthcoming)
* [Step configuration](https://docs.zenml.io/how-to/steps-pipelines/configuration)
  — full `ResourceSettings` reference
