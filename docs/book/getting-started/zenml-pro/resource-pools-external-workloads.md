---
description: >-
  How workloads outside ZenML pipelines claim, renew, and release shared pool
  capacity through service accounts and direct resource requests.
---
# External workloads

An external workload is any process that uses shared infrastructure but does not
run as a ZenML pipeline step — for example an inference autoscaler, a manual
`kubectl run` job, or another platform's pods on the same GPU nodes.

ZenML can still track and prioritize that capacity through direct resource
requests authenticated as a service account. Pipeline authors continue to use
`ResourceSettings`; external integrators use the workspace API.

When inference load rises at peak hours, external workloads can reclaim GPUs
that pipeline jobs held for overnight eval work—without manual coordination
between teams.

## How it fits the pool model

External workloads use the same request → queue → allocate → lease → release
lifecycle as pipeline steps. The difference is who creates the request:

| | Pipeline step | External workload |
| --- | --- | --- |
| Subject | Stack component (orchestrator / step operator) | Authenticated user or service account |
| Request creation | Automatic from `ResourceSettings` | Client calls workspace API |
| Lease renewal | Step heartbeat (automatic) | Client calls renew endpoint |
| Release | Step completion / preemption | Client calls terminate or lease expiry |

ZenML never exposes a separate public "resource manager" API. All calls go
through the workspace facade (`/api/v1/resource_requests`).

## Setup (admin)

### 1. Create a service account

Create a service account in your organization with permission to create and
renew resource requests. See [Service accounts](./service-accounts.md).

### 2. Define node-scoped pools

Model each tracked node (or node pool) as a pool with attributes external
clients can select. Configure in the UI:

```json
{
  "name": "prod-eu-node-b",
  "attributes": {
    "kubernetes_cluster": "prod-eu",
    "kubernetes_node": "node-b",
    "gpu_profile": "h200"
  },
  "capacity": [
    {
      "resource": "h200",
      "class": "reserved",
      "quantity": 8,
      "rank": 100,
      "reclaimable": "never"
    }
  ]
}
```

### 3. Attach a priority-lane policy

Grant the service account access with maximum priority so external reclaim
can preempt lower-priority ZenML pipeline runs when necessary. See
[Admin guide — Priority lane policies](resource-pools-admin-guide.md#priority-lane-policies)
for configuration details. Example:

```json
{
  "pool": "prod-eu-node-b",
  "account_id": "<external-workload-bridge-service-account-uuid>",
  "priority_lane": true,
  "grants": []
}
```

| Field | Meaning |
| --- | --- |
| `priority_lane: true` | Internal maximum priority; do not set `priority` |
| Empty `grants` | Grantless: may use all capacity declared in the pool |

{% hint style="warning" %}
Grantless does not bypass pool coverage. Each demand must match a resource
declared in the pool (reservation 0, limit equal to pool capacity). External
clients that only request GPUs still need a pool that declares `GPU` capacity;
pipeline-facing pools should also include `CPU`, `memory`, and `step run` when
those stacks run ZenML steps on the same component.
{% endhint %}

Priority-lane requests outrank normal pipeline policies. Two priority-lane
allocations have equal priority — one does not preempt another in the current
release.

## Direct resource request flow (integrator)

Authenticate as the service account (API key or token). The workspace derives
the account subject; you cannot impersonate another account.

### Create a request

`POST /api/v1/resource_requests`

Example payload — claim capacity on a specific node while a pod is running:

```json
{
  "demands": [
    {
      "resource": "h200",
      "class": "reserved",
      "quantity": 4,
      "unit": "GPU"
    }
  ],
  "pool_selector": {
    "equals": {
      "kubernetes_cluster": "prod-eu",
      "kubernetes_node": "node-b"
    }
  },
  "reclaim_tolerance": "none",
  "lease_expires_at": "2026-06-08T14:10:00Z",
  "metadata": {
    "workload_key": "k8s://prod-eu/inference/pods/eval-1",
    "kubernetes_namespace": "inference",
    "kubernetes_pod": "eval-1",
    "kubernetes_phase": "Running"
  }
}
```

Python SDK equivalent:

```python
from datetime import datetime, timezone

from zenml.client import Client
from zenml.enums import ResourceRequestReclaimTolerance
from zenml.models import ResourceRequestDemand, ResourceRequestRequest

client = Client()  # authenticated as the service account

request = client.create_resource_request(
    ResourceRequestRequest(
        demands=[
            ResourceRequestDemand(
                resource="h200",
                class_name="reserved",
                quantity=4,
                unit="GPU",
            )
        ],
        pool_selector={
            "equals": {
                "kubernetes_cluster": "prod-eu",
                "kubernetes_node": "node-b",
            }
        },
        reclaim_tolerance=ResourceRequestReclaimTolerance.NONE,
        lease_expires_at=datetime(2026, 6, 8, 14, 10, tzinfo=timezone.utc),
        metadata={
            "workload_key": "k8s://prod-eu/inference/pods/eval-1",
            "kubernetes_namespace": "inference",
            "kubernetes_pod": "eval-1",
        },
    )
)
```

Do not pass `component_ids` or `step_run_id` through this API — those fields
are reserved for pipeline-internal requests.

### Poll until allocated

`GET /api/v1/resource_requests/{request_id}`

Wait for `status: "allocated"`. While `pending`, the reconciler may preempt
lower-priority reclaimable ZenML allocations to free capacity.

### Renew while the workload runs

`POST /api/v1/resource_requests/{request_id}/renew`

```json
{
  "lease_expires_at": "2026-06-08T15:10:00Z"
}
```

Renew on a schedule while the external pod or process holds the GPUs. If the
lease expires, the reconciler releases capacity even if the workload is still
running on the cluster — keep renewals current.

Store-level access (used by integrations and tests):

```python
from zenml.models import ResourceRequestRenewalRequest

Client().zen_store.renew_resource_request(
    request.id,
    ResourceRequestRenewalRequest(lease_expires_at=new_expiry),
)
```

### Release when done

`POST /api/v1/resource_requests/{request_id}/release`

Call release when the pod succeeds, fails, or is deleted. Capacity returns
to the pool ledger after the reconciler finalizes active allocations.

Store-level access (used by integrations and tests):

```python
Client().zen_store.release_resource_request(request.id)
```

Use `POST .../terminate` only for operator or admin intervention (for example
forced preemption with an optional `force` flag and `reason`).

## Pending pods (broader selector)

When a pod is still unschedulable, a bridge component may request against a
broader pool selector (for example match `gpu_profile: h200` in the
cluster). After allocation, Kubernetes may schedule the pod; if it lands on a
different node than expected, release the broad request and create a new
precise request pinned to the actual node's pool.

## Effect on ZenML pipeline runs

When a priority-lane external request needs capacity:

1. The reconciler finds lower-priority reclaimable pipeline allocations in the
   same pool.
2. Victim requests move to `preempting`; step heartbeats stop those step runs.
3. Victim steps re-queue per their retry configuration if configured.
4. External request allocates; inference pods schedule.

Pipeline authors see preempted steps in the UI with a status reason. Admins
see pool occupancy and queue state in the resource management views.

## Kubernetes bridge pattern

A common pattern is a small watcher in your cluster that:

1. Observes opted-in pods (not ZenML-managed pipeline pods).
2. Maps `spec.nodeName` or scheduling constraints to pool attributes.
3. Creates, renews, and terminates resource requests through the ZenML API.

ZenML documents the API contract; you operate the watcher. If the watcher stops
renewing, leases expire and capacity returns to the pool — design the watcher
for reliability.

## See also

* [Admin guide](resource-pools-admin-guide.md) — pools, account policies, priority lanes
* [Core concepts](resource-pools-core-concepts.md) — grants, reclaim tolerance, leases
* [Reconciliation process](resource-pools-reconciliation.md) — preemption and lease expiry
* [Examples](resource-pools-examples.md) — external reclaim scenario
* [Service accounts](./service-accounts.md)
