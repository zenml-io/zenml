---
description: >-
  Precise definitions for ZenML Pro resource pools, subject policies, and
  resource requests.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}

# Core concepts

This page defines **pools**, **policies**, and **requests** for ZenML Pro.

## Pools

A **resource pool** is a named shared bucket. For each resource key (for
example `gpu`), you set how many units exist in the pool. Policies on that
pool further split that capacity among orchestrators and step operators.

Steps and pools use the same keys and integer amounts. Typical keys are:

| Key | Meaning |
| --- | --- |
| `gpu` | GPU count (requested by steps through `ResourceSettings.gpu_count`) |
| `mcpu` | Milli-CPU (requested by steps through `ResourceSettings.cpu_count * 1000`, rounded up) |
| `memory_mb` | Memory in megabytes (requested by steps through `ResourceSettings.memory`) |
| `step_run` | One concurrent step run (added automatically by the server for each step) |

Custom keys (for example `tpu`) can be set with `pool_resources` on the step.

### CLI: pools

```bash
# Create a pool (capacity as JSON or YAML)
zenml resource-pool create training-gpus \
  --capacity '{"gpu": 8, "step_run": 32}' \
  --description "Shared training GPUs for the workspace"

# List pools with occupied vs total capacity
zenml resource-pool list

# Inspect one pool (name, ID prefix, or full ID)
zenml resource-pool describe training-gpus

# Shrink or grow capacity (0 removes a key from the pool)
zenml resource-pool update training-gpus --capacity '{"gpu": 4}'

# Remove a pool (use -y to skip confirmation)
zenml resource-pool delete training-gpus --yes
```

## Policies

A **policy** connects one stack component—the orchestrator or step operator that
acts as the *resource requester* for a step—to one pool. Think of three knobs
per resource key:

* **Reserved** — How much of the pool you *label* as belonging to this component
for accounting. Usage up to that amount counts as *in share*; anything above it
(while the pool still has free units) is *borrowed* idle capacity. Reserved is
not a separate pile of hardware: it is the share used to decide who is “in
their rights” versus who is on spare capacity. Across all policies on the same
pool, reserved totals per key cannot exceed the pool capacity. Reserved must
also be ≤ that policy’s limit for the same key.

* **Limit** — The hard ceiling on how much this component may hold from the pool
at once for that key. Grants never go above the limit, even if the pool is
empty. For **preemptible** workloads, the space between reserved and limit is
where borrowing can happen (subject to pool free capacity). Non-preemptible
work does not use that band: each requested amount per key must be **≤
reserved**, and a higher **limit** does not raise that ceiling (limit still caps
preemptible burst and total use).

* **Priority** — A number; higher means that component’s requests are preferred in
the queue. When the reconciler must **preempt** someone, it looks at **lower**
priority preemptible runs first as victims (see below).

{% hint style="warning" %}
A single orchestrator or step operator may have **several policies** attached,
each pointing at a **different pool**. The server still treats each step as one
**resource request**. Eligibility and allocation are evaluated **per pool**
against the **full** set of requested keys: the step may be queued on more than
one pool, but at most **one** pool ends up owning the active allocation. ZenML
does **not** split a request across pools (for example GPUs from one pool and
`mcpu` from another). Every key in the request must be satisfiable from the
**same** pool and policy that wins. See
[Examples — Multiple pools and multi-key requests](resource-pools-examples.md#multiple-pools-and-multi-key-requests).
{% endhint %}

### CLI: policies

```bash
# Attach an orchestrator to a pool (default component type is orchestrator)
zenml resource-pool attach-policy training-gpus my-k8s-orch \
  --priority 10 \
  --reserved '{"gpu": 2}' \
  --limit '{"gpu": 4}'

# Same for a step operator stack component
zenml resource-pool attach-policy training-gpus my-remote-operator \
  --component-type step_operator \
  --priority 5 \
  --reserved '{"gpu": 2}' \
  --limit '{"gpu": 4}'

# List every policy on a pool
zenml resource-pool list-policies training-gpus

# List all pools a given orchestrator is attached to
zenml resource-pool list-policies --component my-k8s-orch

# Remove that component’s policy from the pool
zenml resource-pool detach-policy training-gpus my-k8s-orch
```

## Resource requests

For eligible runs, the server builds a **resource request** from the step’s
`ResourceSettings`, records whether the step is preemptible, and tracks status:
queued, allocated, rejected, preempted, or cancelled.

{% hint style="info" %}
Only dynamic pipelines participate in resource queuing and allocation
waiting: the server creates resource requests and the client blocks until
allocation when the snapshot is dynamic. Static pipelines do not use this
path today.
{% endhint %}

What users set in `ResourceSettings` becomes a server-side resource request (for
example `gpu_count` → `gpu`, `cpu_count` → `mcpu`, `memory` → `memory_mb`, plus
an implicit concurrent `step_run` slot). The pool must define capacity for each
key requested by the step, except for three built-in types: if the pool has no
row for `mcpu`, `memory_mb`, or the implicit `step_run` key, ZenML Pro treats that
dimension as **effectively unbounded** at the pool layer, so missing rows there
do not by themselves cause rejection. For every other key (including
`gpu` and custom keys from `pool_resources`), a missing pool row means zero
capacity: a positive request is rejected and the step run fails to start.

{% hint style="warning" %}
If the pool does define a key but the subject policy omits that key,
limits fall back to the pool total and reserved defaults to zero for bounded
keys. Non-preemptible steps must stay within their reserved capacity, so a
positive request for a key not defined in the policy is rejected.
{% endhint %}

### Step decorators: `ResourceSettings`

Declare demand on the step; the server turns it into the resource request when
the pipeline is **dynamic** and pooling applies to the stack.

**Typical GPU / CPU / memory (preemptible by default):**

```python
from zenml import step
from zenml.config import ResourceSettings


@step(
    settings={
        "resources": ResourceSettings(
            gpu_count=2,
            cpu_count=4,
            memory="16GiB",
        )
    }
)
def train() -> None:
    ...
```

**Non-preemptible (must stay within policy reserved per key):**

```python
@step(
    settings={
        "resources": ResourceSettings(
            gpu_count=1,
            preemptible=False,
        )
    }
)
def production_train() -> None:
    ...
```

**Custom pool keys** (must exist on the pool and policy when non-preemptible):

```python
@step(
    settings={
        "resources": ResourceSettings(
            gpu_count=1,
            pool_resources={"tensorrt_sessions": 1},
        )
    }
)
def infer() -> None:
    ...
```

Typed fields override the same keys if both appear in `pool_resources`. See
[step configuration](https://docs.zenml.io/how-to/steps-pipelines/configuration)
in the OSS docs for the full `ResourceSettings` model.

### CLI: resource requests

Requests are created when dynamic steps run; you **inspect** or **clean them up**
from the CLI (IDs come from list output or the dashboard).

```bash
# All resource requests visible to your user (see --help for filters)
zenml resource-request list

# Full detail for one request (status, resources, step run link)
zenml resource-request describe 01234567-89ab-cdef-0123-456789abcdef

# Drop a stuck or abandoned request (use with care)
zenml resource-request delete 01234567-89ab-cdef-0123-456789abcdef

# Requests tied to a specific pool: queued only, active only, or both
zenml resource-pool requests training-gpus --view queued
zenml resource-pool requests training-gpus --view active
zenml resource-pool requests training-gpus --view all
```

## See also

* [Resource pools](resource-pools.md) — overview and UX story
* [Examples](resource-pools-examples.md) — scenarios and outcomes
* [How preemption works](resource-pools-reconciliation.md#how-preemption-works) — behavior and ordering
* [Resource pool reconciliation](resource-pools-reconciliation.md) — runtime flow
