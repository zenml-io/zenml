---
description: >-
  Fair GPU and compute sharing for AI/ML teams: dependable production capacity,
  shared pools, idle reuse, and workspace-level quotas—then pools, ResourceSettings,
  policies, queuing, and preemption in ZenML Pro.
icon: layer-group
---

# Resource pools

{% hint style="info" %}
Resource pools are part of ZenML's paid features. For availability and plans,
see the [pricing page](https://www.zenml.io/pricing).
{% endhint %}

If you run AI or ML work in a shared environment, you have probably seen the
same problems: jobs fighting over GPUs, surprise slowdowns when another team
launches a big run, or expensive hardware sitting idle while someone waits in a
queue. Resource pools are ZenML Pro’s answer. They are aimed at
*platform and team leaders* who need clear rules, and at *practitioners* who
just want their steps to get the right compute without babysitting the cluster.

Here are typical situations this feature is built for:

**“Our production jobs must finish—no surprises.”**  
You have training, fine-tuning, or inference that cannot vanish because someone
else submitted a heavier workload. You want a clear agreement: this stack or
this team gets a dependable slice of capacity, and critical steps are not stopped
to make room for ad hoc work.

**“We share one pool of GPUs across many teams.”**  
You need one place that describes how much capacity exists, who may use it, and
what happens when everyone wants it at once—without maintaining a separate
spreadsheet or manual booking process for every pipeline.

**“We paid for the hardware—we should use it when it’s free.”**  
When one group is quiet, you want other teams to use spare capacity so machines
do not sit empty. You also want the original team to get their capacity back when
they return, without a long negotiation or a cluster reconfiguration every
time.

**“Engineers describe needs; ops maps them to reality.”**  
Pipeline authors say what each step requires (GPUs, memory, and so on). Platform
or DevOps ties those stacks to the right shared capacity. The same pipeline code
can run in different environment or stages without hard-coding cluster details.

**“We need to ration more than just GPUs.”**  
Alongside standard compute, you may need to track things like licenses, special
hardware, or how many pipeline steps may run at once. Pools let you treat those
as countable resources under the same workspace-level model, as long as your
organization agrees on names and units.

None of this replaces your orchestrator or cloud provider—it coordinates
demand so teams see fair queuing, optional sharing of idle capacity, and explicit
rules for critical versus best-effort work. When you are ready for how ZenML
models that behavior, continue with [Introduction to capacity management](#introduction-to-capacity-management)
and [Core concepts](#core-concepts).

## Introduction to capacity management

ZenML Pro resource pooling separates three concerns: what capacity exists, what
each pipeline step asks for, and which stack components may draw from which pools under
which rules. The subsections below describe the strategy; [Core concepts](#core-concepts)
then defines terms and mechanics precisely.

### Supply: resource pools

On one side, **resource pools** describe resources that are available and
consumable when pipeline steps run. They often include standard compute—GPUs,
CPUs, and RAM—that orchestrators understand and that map to real infrastructure,
but pools are not limited to that. Teams can define **custom resource keys** as a
convention between whoever operates the platform and whoever writes pipelines:
capabilities, access to external services or tools, licenses, or any other
scarce thing you want to schedule in integer units. The same resource key names
must appear in pool capacity and in step requests for the convention to work.
This is the contract between the platform and the users.

The number of **parallel step runs** is also modeled as a resource today so
concurrency can be capped alongside GPU or CPU demand.
A pool can hold **multiple resource types at once** (for example GPUs and a
`step_run` slot). 

**Who defines pools:** the role that owns infrastructure access—IT ops,
platform engineering, DevOps, or similar — defines and maintains resource pools
at workspace scope so every team in that workspace shares the same catalog
of named capacity.

### Demand: `ResourceSettings` on steps

On the other side, **pipeline steps** declare what they need through
`ResourceSettings`. That is typically the ML engineer, AI engineer, or data
engineer annotating each step with GPUs, CPUs, memory, and optionally the same
custom keys the admins put in pools. Authors can align requests with published
pool capacity and follow whatever naming convention the platform agreed on for
non-standard resources.

Steps also declare whether or not they are **preemptible**. Preemption is the
ability to stop a running step run before it completes, to free up resources for
other steps demanding them with a higher priority. Steps that are preemptible
are not guaranteed to complete if they go outside of their reserved capacity.

That is the product-level tradeoff: **preemptible** steps may access more of the
pool — including capacity that others are not using right now — but another
workload can force them off the machine if priorities and policies require it,
so they can fail early when contention is high. **Non-preemptible** steps opt
into a smaller, dependable slice: they only consume what resources are reserved
for them, so they are not evicted for pool reasons, at the cost of not using the
“burst” capacity above that reservation.

### The link: subject policies

**Subject policies** connect pools to execution. A policy binds a **stack
component** — today an orchestrator or step operator — to a pool and states what
subset of that pool’s resources that component may use. Steps stay decoupled
from a specific pool name: resolution uses the component in the active stack,
so the same step definition can behave differently in different environments
without code changes.

Policies are usually owned by the same platform or admin function, but ML
teams can share ownership where it makes sense. Each policy carries **priority**,
**reserved** amounts per key, and optionally **limits**:

* **Reservation** answers “what pool share is accounted exclusively to this component”
  and is the only capacity that **non-preemptible** steps may rely on: they
  cannot use the gap between reserved and limit.
* **Limits** (and the pool’s own maximum) bound how many resources **preemptible** work
  can take when spare capacity exists; without a limit, the effective ceiling is
  what the pool still has free. A higher limit does not raise the ceiling for
  non-preemptible requests; you need to raise **reserved** if those jobs need more per step.

When thinking about subject policies, it's helpful to understand that multiple
steps in the same run or even in different runs will share the resources defined
in the same subject policy if they run on the same stack component. So they will compete for the same reserved resources. If they go outside of their reserved capacity, they will also compete with other stack components that access the same pool.

Together, pools plus policies plus step annotations implement a **shared,
prioritized, optionally elastic** scheduling story: strict guarantees where
needed, elastic sharing where teams accept preemption risk.

The sections below explain how queues, borrowing, and preemption implement
that model in ZenML Pro.

## Core concepts

### Pools

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

### Policies

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

### Resource requests

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

## Examples: what happens to step runs

The walkthroughs below use small, round numbers and fictional teams. They
assume **dynamic** pipelines so the client normally waits on allocation (see the
hint under [Resource requests](#resource-requests)). CLI snippets illustrate
pools and policies; steps use `ResourceSettings` as in
[Declaring demand](#declaring-demand-resourcesettings-on-steps).

### From `ResourceSettings` to the resource request

Say a step declares:

```python
ResourceSettings(
    gpu_count=2,
    cpu_count=4,
    memory="16GiB",
    pool_resources={"tensorrt_sessions": 1},
    preemptible=True,
)
```

ZenML turns that into a single **resource request** attached to the step run.
Roughly, the keys and amounts are:

| Where it comes from | Request key | How the amount is derived | Request value (step above) |
| --- | --- | --- | --- |
| `gpu_count` | `gpu` | Same as `gpu_count` | **2** |
| `cpu_count` | `mcpu` | `ceil(cpu_count * 1000)` (milli-CPU) | `mcpu`: **4000** |
| `memory` | `memory_mb` | Memory amount converted to megabytes | **17180** (for `"16GiB"`) |
| `pool_resources` | (your names) | Copied as-is, merged with the typed fields above | **1** |
| Server | `step_run` | Always `1` per step (concurrency slot) | **1** |

A pool row is needed for **bounded** keys such as `gpu` and `tensorrt_sessions`.
If you omit `mcpu`, `memory_mb`, or `step_run` from the pool definition, those
dimensions default to **unbounded** at the pool layer (see the hints under
[Resource requests](#resource-requests)).

### Example 1 — No contention (one step running at a time)



**Pool** `datacenter-gpus` with capacity `{"gpu": 8}`.

**Policy** on orchestrator `team-ml-orch`: reserved `{"gpu": 4}`, limit
`{"gpu": 8}`, priority `10`.

This example assumes that no two steps are running at the same time, for the sake of simplicity.

**Preemptible step** with `ResourceSettings(gpu_count=6, preemptible=True)`. The pool
is empty: the step is **allocated** immediately. It will use four GPUs counted
against the team’s **reserved** share and two that are **borrowed** from
still-free pool capacity.

**Non-preemptible step** with `ResourceSettings(gpu_count=2, preemptible=False)`. This step is
also **allocated** given that `2 ≤ reserved` on the policy.

**Non-preemptible step** with `ResourceSettings(gpu_count=6, preemptible=False)`. The request is **rejected** immediately because the request exceeds the policy reserved amount
for `gpu` and non-preemptible work can only use their reserved capacity.


### Example 1b — Unbounded defaults for CPU, memory, and step slots

ZenML Pro treats **`mcpu`** (from `ResourceSettings.cpu_count`), **`memory_mb`**
(from `memory`), and **`step_run`** (implicit concurrency) as unbounded at the
pool layer when the pool has no row for that key. What the subject policy lists for the same keys then decides
whether reserved / limit rules still apply. **`gpu`** and custom `pool_resources` keys are not in that special set: with no pool row, their effective total is zero and requests fail.

**Neither pool nor policy mention CPU, memory, or step_run**  
Pool `{"gpu": 4}` only. Policy only `gpu` (reserved `2`, limit `4`).

Step with `ResourceSettings(gpu_count=1, cpu_count=32, memory="64GiB", preemptible=False)`.

The server still records `mcpu`, `memory_mb`, and `step_run` on the request.
Because the pool omits those keys, they are **unbounded** there. Because the
policy omits them too, their effective **reserved** side is also **unbounded** for
this pattern, so **non-preemptible** is not rejected on CPU / memory /
concurrency—only **`gpu`** is gated. If `gpu_count` fits the policy, the request
**proceeds**; CPU and memory remain informational for the orchestrator unless you
add pool rows later.

**Pool still omits CPU; policy starts metering milli-CPU**  
Same pool `{"gpu": 4}` with **no** `mcpu` row (still unbounded at the pool). Policy
now includes `mcpu` explicitly, for example reserved `4000`, limit `32000`
(think roughly four cores and thirty-two cores worth of milli-CPU). A
**non-preemptible** step with `cpu_count=2` maps to `mcpu` **2000**, which is ≤
reserved **4000** → OK together with a valid `gpu` ask. `cpu_count=8` → `mcpu`
**8000** > reserved **4000** → **rejected** even though the pool never defined
`mcpu`: the **policy** row is enough to enforce reservation. **Preemptible** steps
can use the headroom up to **limit** (and pool free capacity) on that key.

**Pool lists CPU; policy omits `mcpu`**  
Pool `{"gpu": 4, "mcpu": 8000}`. Policy still only `gpu`. For `mcpu`, the pool
total is **finite**, so a missing policy row means **reserved defaults to zero**
and **limit** falls back to the pool total (**8000**). A **preemptible** step with
`cpu_count=4` (`mcpu` **4000**) can enqueue and borrow under the limit. A
**non-preemptible** step with any positive `cpu_count` is **rejected**: positive
`mcpu` with **zero** reserved fails the same rule as a forgotten bounded custom
key. Fix: add `mcpu` to the policy (and usually `memory_mb` / `step_run` if you
modeled them on the pool), or remove `mcpu` from the pool if you wanted the
fully unbounded-default behavior.

**Optional rows for memory and concurrency**  
The same rules apply to **`memory_mb`** and **`step_run`**: omit them on both
pool and policy for “do not quota here,” add them on the **pool** when you want
hard capacity, and add them on the **policy** when each stack component needs
reserved / limit semantics (including non-preemptible floors).

**Bounded keys are unchanged**  
If the step uses `pool_resources={"tensorrt_sessions": 1}`, the pool must still
declare `tensorrt_sessions` (and the policy should define it for
non-preemptible). Unbounded defaults **do not** apply to that key—only to
`mcpu`, `memory_mb`, and `step_run`.

### Example 1c — When things fail (too much GPU, over limit, non-preemptible)

These are separate one-off mistakes; all end with a **rejected** resource
request (dynamic runs fail fast with an error—nothing sits in the queue).

**Too much for the pool**  
Pool capacity `{"gpu": 8}`. Policy allows up to the pool. A preemptible step sets
`gpu_count=10`. The requested amount exceeds the **pool total** for `gpu`, so
the request never joins the queue and is **rejected**.

**More than the policy limit (even if the pool is empty)**  
Same pool `{"gpu": 8}`, but the team policy sets limit `{"gpu": 4}` (reserved
`2`). A step asks for `gpu_count=6`. Six exceeds the component **limit** for
that key, so the request is **rejected** even though eight GPUs exist in the
pool.

**Non-preemptible with no usable reservation**  
Pool `{"gpu": 8}`. The policy lists `gpu` with reserved `4` and limit `8`, but
the step author sets `preemptible=False` and `gpu_count=5`. Non-preemptible requests
must satisfy `requested ≤ reserved` per key, so **five** is **rejected** while
**four** would be accepted.

**Non-preemptible and the policy forgets a bounded key**  
Pool `{"gpu": 8, "tensorrt_sessions": 2}`. The policy only defines `gpu`
(reserved `2`, limit `8`) and omits `tensorrt_sessions`. For a missing policy
row, **reserved** defaults to **zero** on that key. A step uses
`pool_resources={"tensorrt_sessions": 1}` with `preemptible=False`. Asking for a
positive `tensorrt_sessions` amount with **zero** reserved is **rejected**. Fix:
add `tensorrt_sessions` to the policy with enough **reserved** for
non-preemptible use, or make the step preemptible if borrowing is acceptable.

### Example 2 — Same priority, two teams, not enough GPUs to go around

**Pool** `shared` with `{"gpu": 8}`.

**Team Red** and **Team Blue** each have an orchestrator policy on `shared` with
**priority `10`**, reserved `4`, limit `8` (different components, same numbers).

Several Red and Blue steps are **preemptible** and each wants **2 GPUs**. When
the pool cannot satisfy everyone at once, requests **wait in the pool’s queue**.
Among items with the **same policy priority**, ordering favors **older** pending
requests (FIFO-style). The allocator also **prefers a request that still fits
entirely in its unused reserved slice** over one that would have to **borrow**
when both are waiting—so a team that still has “room” in its reservation is not
stuck behind another team that is already bursting, if the next grant can be
served from that reserved headroom.

**Outcome:** steps start as GPUs free up; no one is preempted until a **higher**
priority waiter or reclaim logic forces it (covered next).

### Example 3 — Different priorities under pressure

**Pool** `{"gpu": 8}`.

* **Sandbox** orchestrator: priority **`10`**, reserved `4`, limit `8`,
  preemptible experiments using **6 GPUs** (borrowed burst).
* **Prod** orchestrator: priority **`100`**, reserved `2`, limit `8`.

**Case A — Prod needs GPUs and Sandbox is elastic:** Prod submits a **preemptible**
step with `gpu_count=4`. The pool cannot fit four more GPUs without reclaiming
space. The reconciler may **preempt** Sandbox’s preemptible runs (lower policy
priority) so Prod can proceed.

**Case B — Prod is non-preemptible:** Prod uses `preemptible=False` and
`gpu_count=2`. Prod’s request may only use **reserved** GPUs for that key. If
another **non-preemptible** job on the same Prod stack component already holds
the two reserved GPUs, this step **waits**—it will not borrow Sandbox’s burst.
Raising **reserved**, finishing the other job, or using preemptible Prod work
changes the outcome.

### Example 4 — Multiple policies, multiple pools, multiple keys

**4a — Two pools as prioritized paths (same request shape)**  
Attach two policies to the **same** orchestrator:

* Policy A → pool `eu-west-gpu`, priority **`20`**
* Policy B → pool `eu-north-gpu`, priority **`10`**

Both pools declare enough `gpu` (and any other keys your steps request) that the
**entire** resource request passes each pool’s checks. A step with `gpu_count=1`
creates **one** resource request, which is **enqueued in every eligible pool**.
Only **one** pool may **win** the allocation: a request can have at most one
active allocation. When the server tries to allocate, it prefers the **higher
policy priority** first, so **`eu-west`** is consulted before **`eu-north`**.
Whichever pool grants first “owns” that allocation; the other queue row is
removed as stale. Use this pattern for **primary / fallback** or **regional**
capacity, not for splitting one step across unrelated quota systems.

**4b — Several keys in one pool**  
Define `{"gpu": 16, "step_run": 20}` on a single pool and policies with reserved /
limit rows for **both** keys if you want to cap **GPUs** and **concurrent steps**
together. Each running step consumes `gpu` from `gpu_count` **and** one
`step_run`; both must be available before the step leaves the queue.

**4c — Why you usually do not split keys across pools for one step**  
Eligibility is evaluated **per pool** against **every** key on the request. If a
step asks for `gpu` **and** `tensorrt_sessions`, a pool that only defines `gpu`
still sees the other key as **zero capacity** and will **not** enqueue that
request. Model **all** scarce dimensions you care about on **one** pool (or give
every pool the same key set) so the bundle can be accepted.

## Runtime flow (orchestration)

1. Request creation: For eligible runs, the server derives requested
   resources from the step’s `ResourceSettings` (see below), adds `step_run: 1`,
   and stores `preemptible` from the same settings. The resource requester
   is the stack’s step operator if the step uses one, otherwise the
   orchestrator.
2. Queuing: If capacity is not available immediately, the step can remain
   queued until the reconciler allocates it.
3. Client wait: For dynamic pipelines, the step launcher polls the
   resource request until it is allocated (with backoff). If the request is
   rejected, preempted, or cancelled, the client surfaces an error.
   When allocation succeeds, the step is published as running and execution
   proceeds.
4. Preemption: If the job at the front of the queue still cannot be granted,
   the reconciler may stop other *preemptible* runs in that pool to free units
   (see [How preemption works](#how-preemption-works)). Non-preemptible runs
   are never stopped this way. They are also constrained so each request’s
   per-key demand is **≤ policy reserved** for that key—even when **limit** is
   higher—so they never rely on borrowed capacity that could clash with other
   non-preemptible use on the same component.

`StepRunner` does not duplicate this logic; pooling is enforced at scheduling
and server side, with the launcher blocking until allocation when required.

## How preemption works

**When.** Preemption runs only when the next queued request for a pool cannot be
allocated—there is not enough free capacity, or a policy rule blocks the
grant. The reconciler may then mark selected *already running* requests as
preempted, which cancels those step runs and returns their units to the pool.

**Who can be stopped.** Only steps with `preemptible=True` (the default in
`ResourceSettings`) are candidates. `preemptible=False` means “never pick this
run as the one to kill.”

**Who gets stopped first (simple picture).**

1. Among preemptible runs in the same pool, **lower policy priority** is
   considered before higher priority. If the waiting job’s priority is *strictly
   higher* than a victim’s, that victim can be preempted to make room, as long
   as freeing it actually fixes the shortage.
2. **Reserved** adds a second idea: *reclaim*. If the waiting component still
   has unused **reserved** headroom on this pool (reserved minus what it is
   already using here), the system may preempt preemptible runs that are using
   **borrowed** capacity—even when those runs have the same or higher priority
   than the waiter. Intuition: your reserved share is “yours to fill”; if
   someone else is on the spare capacity you could have used under your
   reservation, they can be moved out of the way.
3. **Limit** does not pick victims. It only caps how much a component may hold;
   if the waiting request itself is over its own limit, killing other jobs will
   not fix that—you need a higher limit or a smaller request.

Victims are ordered by ascending policy priority, then by allocation time as a
tie-break; see the resource pool reconciler in ZenML Pro for the exact ordering.

### Step-level: `preemptible`

| Setting | Effect |
| --- | --- |
| `preemptible=True` (default) | This run may be preempted to help another request. |
| `preemptible=False` | This run is never preempted. Each requested amount per pool key must be ≤ that key’s **reserved** on the policy; **limit** above reserved does not increase what a non-preemptible step may request. |

Policies do not override `preemptible`; they only affect ordering and reclaim
among runs that are allowed to be preempted.

### After preemption

Affected runs move toward cancelled; a later reconciler pass can grant the
waiting request. Clients may see failed or preempted steps depending on retries
and pipeline configuration.

## Configuring pools and policies

### Dashboard

ZenML Pro provides UI to:

* Create and edit pools (capacity per key, descriptions).
* Attach policies to orchestrators and step operators (priority, reserved,
  limit).
* Inspect utilization: occupied capacity, active allocations, and queued
  requests.

{% hint style="info" %}
Screenshots for the pool management and pipeline-run resource views will be
added here.
{% endhint %}

### CLI

Pools:

```bash
# Create a pool (capacity as JSON or YAML)
zenml resource-pool create training-gpus \
  --capacity '{"gpu": 8}'

zenml resource-pool describe training-gpus
zenml resource-pool list
zenml resource-pool update training-gpus --capacity '{"gpu": 4}'
zenml resource-pool delete training-gpus
```

Policies (attach a component to a pool; default component type is orchestrator,
use `-t step_operator` for step operators):

```bash
zenml resource-pool attach-policy training-gpus my-k8s-orch \
  --priority 10 \
  --reserved '{"gpu": 4}' \
  --limit '{"gpu": 8}'

zenml resource-pool list-policies training-gpus
zenml resource-pool detach-policy training-gpus my-k8s-orch
```

Queued and active requests for a pool:

```bash
zenml resource-pool requests training-gpus --view all
```

Individual resource requests:

```bash
zenml resource-request list
zenml resource-request describe <REQUEST_ID>
zenml resource-request delete <REQUEST_ID>
```

## Declaring demand: `ResourceSettings` on steps

Use `@step` settings to describe what the step wants from pools (and from the
underlying orchestrator). Relevant fields:

* `gpu_count`, `cpu_count`, `memory`: map to `gpu`, `mcpu`, and `memory_mb` in
  the request (see [step configuration](https://docs.zenml.io/how-to/steps-pipelines/configuration)
  in the OSS docs).
* `pool_resources`: optional map for extra keys or to set `gpu` / `mcpu` /
  `memory_mb` explicitly; typed fields override the same keys in the map.
* `preemptible` (default `True`): if true, the workload may be preempted
  when another request needs capacity; if false, the step cannot be evicted and
  each resource key requested must stay within the policy **reserved** amount
  for that key (not the higher **limit**).

Example:

```python
from zenml import step
from zenml.config import ResourceSettings


@step(
    settings={
        "resources": ResourceSettings(
            gpu_count=2,
            cpu_count=4,
            memory="16GiB",
            preemptible=False,
        )
    }
)
def train() -> None:
    ...
```

If `ResourceSettings` is empty, the server does not add discretionary GPU/
CPU/memory keys; the implicit `step_run` slot may still be requested for
eligible steps.

## Policy scenarios (how reserved, limit, and preemptible interact)

For the problems these patterns solve in everyday terms, see
[What this feature is for](#what-this-feature-is-for).

* Fair share plus burst: set **reserved** to the slice you want to account as
  “yours” and **limit** to the most that stack may ever hold. **Preemptible**
  steps can **borrow** idle capacity between reserved and limit (and up to the
  pool) when the pool has room. **Non-preemptible** steps only use up to
  **reserved** per requested key, regardless of a higher limit.
* Production vs experiments: higher **priority** on production policies;
  experimental steps stay **preemptible** so production can take capacity or
  reclaim borrowed slack when it needs its reservation.
* Non-preemptible training: set `preemptible=False` and size **reserved** so
  each step’s per-key request (for example `gpu_count`) is ≤ reserved for that
  key. **Limit** can be higher for preemptible burst on the same policy, but it
  does not raise the ceiling for non-preemptible requests; raise **reserved**
  if those jobs need more per step. The reconciler also blocks non-preemptible
  grants that would sit on borrowed capacity in ways that conflict with other
  non-preemptible use on the component.
* Several pools for one component: multiple policies with different
  **priority** values; higher priority is preferred when queuing and allocating,
  subject to each pool’s **limit**.

For preemption rules (priority vs reclaim), see
[How preemption works](#how-preemption-works).

## Observability in the UI

Alongside the pool admin screen, the pipeline run view surfaces which
resources were requested, allocated, or queued for steps in the run,
so teams can correlate ZenML state with cluster or cloud dashboards.

## See also

* [Workspaces](./workspaces.md) — pools are scoped to the workspace.
* [Teams](./teams.md) — organizational context for who owns which stacks and
  policies.
* ZenML OSS: [step and pipeline configuration](https://docs.zenml.io/how-to/steps-pipelines/configuration).
