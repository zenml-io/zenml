---
description: >-
  How pipeline authors request CPU, memory, and GPUs through ResourceSettings
  on dynamic pipeline steps in ZenML Pro.
---
# User guide

This guide is for pipeline authors — ML engineers and data scientists who run
dynamic pipelines and need GPUs, CPU, or memory without choosing clusters or
node pools.

Platform admins define pools and policies. You annotate steps; ZenML converts
your settings into resource requests, waits for allocation, and applies admin
runtime settings to the stack component that runs your step.

{% hint style="info" %}
Resource pools apply only to [dynamic pipelines](https://docs.zenml.io/how-to/steps-pipelines/dynamic_pipelines).
Set `dynamic=True` on the pipeline (or use dynamic step patterns). Static
pipelines do not queue or wait for pool allocation.
{% endhint %}

## Prerequisites

* Your pipeline is [dynamic](https://docs.zenml.io/how-to/steps-pipelines/dynamic_pipelines).
* Your stack's orchestrator or step operator has a resource policy on a pool
  (ask your platform admin).
* You run the pipeline on that stack.

## Request CPU, memory, and GPUs

Use typed fields on `ResourceSettings`. This is the recommended path for most
workloads.

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

| Setting | What you mean |
| --- | --- |
| `gpu_count` | Number of GPUs |
| `gpu_class` | Optional capacity class (for example `reserved`) when the pool defines multiple classes |
| `cpu_count` | Number of CPU cores |
| `memory` | RAM with unit suffix (`GiB`, `MiB`, …) |

You do not need to know descriptor names, pool names, or Kubernetes settings.

### Production jobs that must not be interrupted

Set reclaim tolerance to `none` so the step only uses guaranteed reserved
capacity and is never stopped for pool reasons.

Use `reclaim_tolerance: none` when a long-running production job must not be
interrupted by lower-priority pool activity.

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

Legacy input still works: `preemptible=False` is accepted and mapped to
`reclaim_tolerance: none`.

{% hint style="warning" %}
`reclaim_tolerance: none` only works when your stack's policy grants reserved
capacity for every resource the step requests (GPUs, CPU, memory, `step run`,
and any custom descriptors). If reserved is zero or the grant omits a resource,
the request is rejected — even when the pool has free capacity.
{% endhint %}

### Best-effort experiments

Omit `reclaim_tolerance` on isolated dynamic steps and ZenML defaults to
`any` — you may use burst capacity but can be interrupted when higher-priority
work needs GPUs.

```python
@step(
    settings={
        "resources": ResourceSettings(
            gpu_count=1,
            cpu_count=8,
            memory="32GiB",
        )
    }
)
def experiment() -> None:
    ...
```

To allow coordinated stop-and-retry without using unsafe spot capacity, set
`reclaim_tolerance=ResourceRequestReclaimTolerance.COORDINATED` explicitly
(or use legacy `preemptible=True`).

Configure step retries if you want automatic re-queue after preemption:

```python
from zenml import StepRetryConfig

@step(retry=StepRetryConfig(max_retries=2), ...)
def experiment() -> None:
    ...
```

## How your settings become resource requests

When a dynamic step is ready to launch, ZenML builds one resource request with
several demands:

{% hint style="warning" %}
Every demand in your request must be covered by the winning pool and policy.
There is no unbounded fallback for CPU, memory, or `step run`. If the pool or
grants omit a resource you requested, the step is rejected. Ask your admin to
include `CPU`, `memory`, and `step run` in every pool and policy on your stack.
{% endhint %}

- `gpu_count=2` → demand with `kind: "gpu"`, quantity 2 (plus `gpu_class` if set)
- `cpu_count=4` → demand with `kind: "cpu"`, quantity 4, unit `CPU`
- `memory="16GiB"` → demand with `kind: "memory"`, quantity 16, unit `GiB`
- Isolated steps also get an implicit `kind: "step_run"`, quantity 1 unless you
  already requested one

Basic resources resolve by kind — ZenML matches them to descriptors in the
catalog (`GPU`, `CPU`, `memory`) without you naming those descriptors.

Custom resources (licenses, TPUs you defined with the admin) use the
`resources` field by descriptor name:

```python
ResourceSettings(
    resources={"training-license": 1},
    reclaim_tolerance=ResourceRequestReclaimTolerance.NONE,
)
```

Do not mix the same resource through both typed fields and `resources` for
the same logical need.

## Leases, heartbeat, and reclaim tolerance

These three settings work together for isolated dynamic steps. Inline dynamic
steps follow a simpler path.

### Inline vs isolated

| | Inline dynamic step | Isolated dynamic step |
| --- | --- | --- |
| Where it runs | Orchestrator process (same thread) | Separate pod/job via step operator |
| Default `reclaim_tolerance` | `none` | `any` |
| Running lease | None | Yes, when heartbeat is enabled |
| Preemptible for pool reasons | No | Yes, when tolerance is `coordinated` or `any` |

Inline steps are treated as non-reclaimable: they do not get a running lease and
cannot use `coordinated` or `any` reclaim tolerance. If you need preemptible
burst capacity, configure the step to run isolated.

### Heartbeat and lease renewal

For isolated steps with heartbeat enabled (the default when a heartbeat threshold
is set on the step run):

1. While the request is `pending`, the step launcher polls and extends the lease
   so queue waits do not lose the place in line.
2. After allocation, the launcher sets an initial lease for
   `initialization_lease_seconds` while the step starts.
3. While the step runs, each heartbeat renews the lease (roughly three times the
   heartbeat interval) and reads request status. If the request moves to
   `preempting`, `preempted`, or another terminal status, the step stops.

If heartbeat is disabled on the step run, ZenML does not renew the resource
request lease during execution. That combination is only valid with
`reclaim_tolerance: none` — validation rejects `coordinated` or `any` when
heartbeat is off.

### How reclaim tolerance fits in

| `reclaim_tolerance` | Can be preempted? | Requires | Heartbeat |
| --- | --- | --- | --- |
| `none` | No | Reserved grant capacity | Optional |
| `coordinated` | Yes, with retry | Isolated runtime | Required |
| `any` | Yes, including unsafe classes | Isolated runtime | Required |

Production steps that must not be interrupted should use `none` and reserved
capacity. Best-effort experiments on isolated steps can omit `reclaim_tolerance`
(default `any`) and rely on heartbeat plus step retries after preemption.

See [Reconciliation process](resource-pools-reconciliation.md) for queueing,
preemption ordering, and lease expiry behavior.

## Waiting and startup timeouts

| Setting | Default | Meaning |
| --- | --- | --- |
| `allocation_wait_timeout_seconds` | 3600 | Max time to wait in queue for allocation |
| `initialization_lease_seconds` | 3600 | Initial lease after allocation while the isolated step starts (heartbeat takes over once running) |

These apply while the step launcher waits for pool capacity. They do not replace
heartbeat renewal for isolated reclaimable steps — see
[Leases, heartbeat, and reclaim tolerance](#leases-heartbeat-and-reclaim-tolerance)
above.

If the pool is busy, your step stays queued until capacity frees or the wait
timeout is reached.

When many jobs arrive at once and the pool is full, steps wait in the queue
automatically—you do not need to monitor each run individually.

## Inspecting your requests

### UI

The workspace UI shows resource requests linked to step runs: status, pool,
demands, and `status_reason` when queued, rejected, or stopped.

### CLI

```shell
zenml resource-request list --status pending
zenml resource-request describe <request-id>
zenml resource-pool requests <pool-name> --view queued
```

Always read `status_reason` alongside `status`—it carries the specific explanation
when ZenML has one.

### Request statuses

Every resource request moves through one of these states. Terminal states
(`rejected`, `preempted`, `cancelled`, `expired`, `released`) do not return to
`pending` on their own; a new run or a configured step retry creates a fresh
request.

| Status | Category | What it means for your step |
| --- | --- | --- |
| `pending` | In progress | The request is admitted and waiting in a pool queue. Your step stays `queued` until capacity is available or a terminal status ends the wait. |
| `allocated` | In progress | Capacity is reserved for this request. The step launcher proceeds (or the isolated step is running) and renews the lease while heartbeats are active. |
| `released` | Success | Capacity was returned normally—for example after the step finished and released its allocation. |
| `no_matching_policy` | Error | No policy on the pool matches your stack component or account. The request is not persisted; the step is not linked to a pool request and does not wait for capacity. Ask your admin to attach a policy. |
| `rejected` | Error | The request cannot be admitted under current pool and policy rules. The step fails immediately when the launcher reads this status. See [Common rejection reasons](#common-rejection-reasons) below. |
| `preempting` | Error (transitional) | A higher-priority request is reclaiming this allocation. On isolated steps with heartbeat, the next heartbeat moves the step to `cancelling` so it can exit gracefully. |
| `preempted` | Error | Preemption finished and capacity was taken back. The step stops. Configure [step retries](#best-effort-experiments) if you want automatic re-queue. |
| `cancelled` | Error | The request was withdrawn before or during execution. Common when a pipeline run is stopped, a pending request's lease expires, or an operator cancels the request. |
| `expired` | Error | An allocated request outlived its lease without renewal. Typical when an isolated step crashes, loses network access, or stops heartbeating while still holding capacity. |

**While `pending`:** the pool may be fully utilized, your policy's reserved
slice may be full, or higher-priority work may be ahead of you in the queue.
This is normal contention—not a misconfiguration—unless the wait exceeds
`allocation_wait_timeout_seconds`, in which case the step launcher raises an
error even though the request may still show `pending`.

**After `allocated`:** keep heartbeats enabled on isolated reclaimable steps.
If heartbeats stop, the lease eventually expires, the request moves to
`expired`, and capacity returns to the pool while your step may already have
failed for other reasons.

### Common rejection reasons

When `status` is `rejected`, `status_reason` usually points to a fixable
configuration mismatch between your step settings and what the admin defined.

| `status_reason` (typical text) | What it usually means | What to do |
| --- | --- | --- |
| `No resource policy matches any of the request subjects.` | The stack component (or account) has no policy on any pool. | Ask your admin to attach a policy to your orchestrator or step operator. |
| `No resource policy admitted this request.` | A policy exists but no grant path can satisfy every demand—for example quantity exceeds grant `limit`, a descriptor is missing from the pool, or a custom resource is undefined. | Reduce `gpu_count` / CPU / memory, or ask the admin to extend pool capacity and grants. |
| `No grant reserved share satisfies this request with reclaim_tolerance 'none'.` | You requested non-preemptible capacity but the policy has zero `reserved` for one or more demanded resources. | Use `reclaim_tolerance: coordinated` or `any` for burst work, or ask the admin to add reserved grants. |

Other rejections can appear when a demand references a resource or class the
pool does not declare—for example `gpu_class="reserved"` on a pool with only
adhoc capacity, or a step that requests CPU while the policy grant omits
`CPU`.

### Common pipeline failures

The table below separates misconfiguration (fix settings or ask the admin) from
operational circumstances (expected under contention or failure).

#### Configuration mistakes

| Situation | What you see | How to fix |
| --- | --- | --- |
| Production step with `reclaim_tolerance: none` but no reserved grants | `rejected` at submit time with reserved-share message | Ask admin for reserved grants, or lower reclaim tolerance for non-production runs |
| `gpu_count=4` when policy `limit` is 2 | `rejected` immediately | Lower the request or ask admin to raise the limit |
| Pool models GPUs only; step requests CPU and memory | `rejected` even when GPUs are idle | Ask admin to add `CPU`, `memory`, and `step run` to pool and policy |
| Step operator has no policy | `no_matching_policy` or step skips pool wait without a linked request | Admin attaches a policy on the correct component |
| Wrong `gpu_class` for the pool | `rejected` or indefinite `pending` on the wrong class | Match class names to what the admin defined, or omit `gpu_class` |

#### Operational circumstances

| Situation | What you see | What happens next |
| --- | --- | --- |
| Pool busy; four GPUs, ten sweep jobs | Steps stay `queued` (`pending`); `status_reason` may mention waiting for capacity or higher priority | Jobs start in queue order as slots free; increase `allocation_wait_timeout_seconds` if waits are legitimately long |
| Wait timeout exceeded while still `pending` | Step fails with allocation timeout error in logs | Re-run later or ask admin for more capacity; the request may still be `pending` until lease expiry |
| Preemptible eval job; production job needs GPUs | `preempting` then `preempted`; step moves to `cancelling` / `stopped` | With `StepRetryConfig`, ZenML re-queues a new request; without retries the step stays stopped |
| Preemption with retries exhausted | Step `failed` after last retry | Reduce contention, lower priority relative to production, or run during off-peak hours |
| External priority-lane reclaim on shared node | `preempting` during your run; reason references higher-priority request | Same as preemption—retries re-queue when configured |
| Isolated step crash or pod OOM | Step `failed`; request may become `expired` after lease TTL | Capacity returns to the pool; fix the step code or resource sizing and re-run |
| Network partition; heartbeats cannot renew lease | Request moves to `expired`; heartbeat may stop the step | Restore connectivity; design checkpoints and retries for long jobs |
| Pipeline run stopped while step is queued | Request `cancelled`; step `cancelled` | Expected when you or an operator stops the run |
| Pending queue wait without renewals (rare misconfig) | `cancelled` with `Lease expired while pending.` | Ensure the step launcher can reach the server during queue wait; contact support if it persists |

## What you do not configure

Leave these to platform admins:

* Resource descriptors and pool capacity classes
* Policies, priorities, and grants
* Kubernetes node selectors, taints, and tolerations (placement via component settings)
* External workload integrations

If your step needs a specific GPU class (for example H200 across
several clusters), ask the admin to define descriptors, pools, and step-operator
candidates — then use `gpu_count` / `gpu_class` or advanced `resources` selectors
once your organization documents the pattern.

## See also

* [Resource pools](resource-pools.md) — overview
* [Core concepts](resource-pools-core-concepts.md) — descriptors, classes, reclaim tolerance
* [Examples](resource-pools-examples.md) — scenarios with admin + author + outcome
* [Reconciliation process](resource-pools-reconciliation.md) — queueing, preemption, leases, heartbeats
* OSS docs: [step configuration](https://docs.zenml.io/how-to/steps-pipelines/configuration)
