---
description: >-
  How resource pool reconciliation, queueing, preemption, and lease management
  work in ZenML Pro.
---
# Resource Pool Reconciliation

This page explains what happens after a resource request exists: how the
reconciler allocates capacity, when work is preempted, and how leases keep
allocations honest while steps and external clients run.

For definitions, see [Core concepts](resource-pools-core-concepts.md). For
author-facing settings, see [User guide](resource-pools-user-guide.md).

## Overview

ZenML separates request recording from scheduling:

1. The workspace API records resource requests (from pipeline steps or external
   clients).
2. A background reconciler process reads pool state, orders the queue, grants
   allocations, initiates preemption, and expires stale leases.
3. The step launcher and step heartbeats poll request status and renew leases
   for pipeline workloads.

There is no push callback from the reconciler into running pods. Pipeline
steps learn about preemption through the heartbeat path.

```mermaid
sequenceDiagram
    participant Step as Step launcher
    participant WS as Workspace
    participant Rec as Reconciler
    participant HB as Step heartbeat

    Step->>WS: Step ready; resource request created
    Rec->>Rec: Queue / allocate / preempt
    loop Until allocated or terminal
        Step->>WS: Poll / renew request
        WS-->>Step: pending or allocated
    end
    Step->>Step: Launch step
    loop While running
        HB->>WS: Heartbeat + renew lease
        WS-->>HB: keep running or stop
    end
    Step->>WS: Step completes; release
    Rec->>Rec: Free capacity
```

## Runtime flow for pipeline steps

1. Request creation — For eligible dynamic steps, the server builds demands from
   `ResourceSettings`, sets `reclaim_tolerance`, and links the request to the
   step run. The resource requester is the step operator if the step uses one,
   otherwise the orchestrator.
2. Queuing — If capacity is not available, status stays `pending`. The request
   may appear in one or more pool queues until one pool can grant all demands.
3. Client wait — The step launcher polls the request (with exponential backoff)
   until it is `allocated`, rejected, preempted, cancelled, or expired, or
   until `allocation_wait_timeout_seconds` elapses.
4. Launch — On `allocated`, the launcher renews the lease for
   `initialization_lease_seconds`, publishes the step as running, and starts
   execution with allocation component settings merged into the stack config.
5. Heartbeat — While the step runs, each heartbeat renews the lease and checks
   request status. Terminal or preempting statuses stop the step.
6. Deallocation — When the step completes, capacity is released. Crashes and
   lease expiry are safety nets if release does not happen promptly.

{% hint style="warning" %}
If a component has policies on multiple pools, the same logical request may
queue in several pools, but at most one pool owns the active allocation. ZenML
never splits one step's demands across pools.

Every pool that might win must include capacity and policy grants for all
resources the step requests. A GPU-only pool cannot satisfy a step that also
requests CPU, memory, or a `step_run` slot.
{% endhint %}

## Queue ordering

Within each pool, the reconciler orders pending requests roughly as follows:

1. Priority-lane requests first
2. Requests that fit entirely in unused reserved share
3. Higher policy priority
4. Earlier enqueue time (FIFO tie-break)

Scheduling is not real-time — expect seconds to minutes depending on
reconciler cadence and load. Urgent work is modeled through priority and
reserved capacity, not sub-second dispatch. When more jobs arrive than there
are GPUs—for example ten sweeps on a four-GPU pool—the first allocations
proceed and the rest wait in order until slots open.

## Allocation rules

Allocation is all-or-nothing: every demand in the request must be satisfiable
from the same pool, subject, and policy path in one transaction.

Before granting, the reconciler checks:

- Matching policy and grant for each demand (or grantless admission against pool capacity)
- Exact grant `class_name` when the selected capacity class is policy-gated
- Grant `limit` and reserved rules for `reclaim_tolerance: none`
- Free capacity in each required `(resource, class)` bucket
- Class rank when the request does not pin a class

{% hint style="warning" %}
There is no unbounded fallback for `CPU`, `memory`, or `step run`. Each demand
must match a resource in the pool and be admitted through a grant (or through a
grantless policy that exposes the full pool). Missing pool capacity or a grant
that omits a demanded resource causes rejection.

For `reclaim_tolerance: none`, each demand must fit within the grant's
`reserved` amount. Zero reserved for a demanded resource rejects the request
immediately.

Administrators cannot over-reserve a pool class through policies. For each
pool, resource, and class, the configured policy `reserved` totals must fit
inside the matching pool capacity before those policies can be saved.
{% endhint %}

If raw capacity is insufficient, the reconciler may attempt preemption before
leaving the request pending.

## How preemption works

Preemption runs only when a pending request cannot be granted and eligible
victims exist.

### Who can be stopped

Only allocations whose requests have reclaim tolerance above `none` are
candidates. Production steps with `reclaim_tolerance: none` (or legacy
`preemptible=False`) are never chosen as victims.

### Victim ordering

Among eligible victims in the same pool:

1. Lower policy priority first
2. Allocations borrowing reserved capacity needed by the waiter (reclaim),
   even when priorities are equal or the victim's priority is higher
3. Stable tie-breakers (allocation time, request id)

`limit` on a grant caps how much a subject may hold; it does not pick victims.

### Priority-lane interactions

- Normal-priority requests cannot preempt priority-lane allocations
- Priority-lane requests may preempt lower-priority reclaimable allocations
- Priority-lane requests do not preempt other priority-lane requests

### After preemption

1. Victim request → `preempting`, with `preemption_initiated_by_id` set
2. Step heartbeat moves the step toward cancellation
3. Capacity returns when the victim releases, expires, or finishes cancelling
4. Waiter grants; victim may re-queue via step retry if configured

Graceful checkpoint preemption (signal → checkpoint → resume) is not provided
by the platform today. Authors rely on application checkpoints and step retries.

Production jobs with `reclaim_tolerance: none` are never chosen as preemption
victims. Only workloads that accept coordinated or any reclaim can be
displaced to make room for higher-priority work.

## Lease management

A lease is a time-bound claim on allocated capacity. Lease metadata lives on
the resource request (`lease_expires_at`, `renewed_at`).

### Why leases exist

Pools track virtual capacity. Leases ensure capacity returns when:

- A step crashes without a clean shutdown
- An external client disappears
- A network partition prevents renewal
- A run is abandoned while still `allocated`

Without leases, a single stuck allocation could block the pool indefinitely.

### Pipeline steps: launcher polling

Before the step runs, the step launcher loops:

- Poll request status through renew calls (which also extend the lease while
  waiting in `pending`)
- Respect `allocation_wait_timeout_seconds`
- Fail fast on `rejected`, `cancelled`, `preempting`, `preempted`, `expired`

After allocation, the launcher sets an initial lease through
`initialization_lease_seconds` so short startup delays do not drop the grant.

### Pipeline steps: heartbeat renewal

While an isolated step with heartbeat enabled executes, the step heartbeat is
the renewal and status channel:

- Updates the step heartbeat timestamp
- Renews the resource request lease (extends `lease_expires_at`, roughly three
  times the heartbeat interval)
- Reads request status
- Returns stop/cancel when status is `preempting`, `preempted`, `cancelled`,
  `rejected`, `released`, or `expired`

Inline dynamic steps do not receive a running lease — effective
`reclaim_tolerance: none`, capacity held until the step completes.

Isolated steps with heartbeat disabled do not renew leases during execution.
That is only valid with `reclaim_tolerance: none`.

Preemptible isolated steps (`coordinated` or `any`) must have heartbeat
enabled. Validation fails at run creation otherwise.

### External workloads: explicit renew

External clients must call `POST /api/v1/resource_requests/{id}/renew` on a
schedule. There is no heartbeat integration for non-pipeline requests.

### When leases expire

If `lease_expires_at` passes without renewal:

| Previous status | Becomes | Capacity |
| --- | --- | --- |
| `allocated` or `preempting` | `expired` | Released |
| `pending` | `cancelled` | N/A (was not allocated) |

The reconciler rebuilds queues and may grant waiting work in a later pass.
Renewal on an already terminal request returns the terminal row unchanged —
capacity is not silently resurrected.

### What admins should communicate

Tell teams that long-running steps depend on heartbeat connectivity to the
workspace. Extended workspace outages can cause lease expiry and preemption
even when cluster pods still appear running.

## Policy scenarios (quick reference)

| Pattern | Admin setup | Author setting | Runtime behavior |
| --- | --- | --- | --- |
| Fair share + burst | Reserved + limit on grant | Default or `coordinated` | Uses reserved first, may burst to limit |
| Production vs experiments | Higher priority + reserved grant | `none` on production | Production never victim; experiments preemptible |
| External reclaim | Priority-lane account policy | N/A (external API) | External request preempts pipeline borrow |
| Queue transparency | Same pool, multiple policies | Any | UI / CLI show `status_reason` |

## Terminal states and release

Active allocations must not remain on terminal requests. Capacity frees on:

- Normal step completion (`POST .../release` from the request owner)
- `POST .../terminate` from operators or admins
- Preemption completing (`preempting` → release path)
- Lease expiry
- Policy or pool teardown (admin configuration change)

Inspect stuck pools with `zenml resource-pool requests` and the UI occupancy
views before deleting requests manually.

## See also

* [Core concepts](resource-pools-core-concepts.md) — reclaim tolerance, classes, statuses
* [User guide](resource-pools-user-guide.md) — timeouts and author settings
* [External workloads](resource-pools-external-workloads.md) — renew and terminate API
* [Examples](resource-pools-examples.md) — preemption and queue scenarios
* [Resource pools](resource-pools.md) — overview
