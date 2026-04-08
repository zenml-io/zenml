---
description: >-
  How preemption works in ZenML Pro.
---
# How Preemption Works

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
