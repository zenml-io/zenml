---
description: >-
  How external workloads use ZenML Pro resource pools through service accounts,
  direct Resource Manager requests, and priority-lane policies.
---
# External workloads

External workloads are jobs that consume the same infrastructure as ZenML
pipelines but are not launched as ZenML steps. Examples include online
inference services, batch jobs managed by another scheduler, or emergency
capacity reservations driven by an internal platform service.

Resource pools can govern those workloads when they create Resource Manager
resource requests with the same subject and demand conventions as ZenML steps.

## Common pattern

1. Create a ZenML Pro service account for the external system.
2. Configure a resource pool in the UI with classes that represent the real
   infrastructure bundle the workload consumes.
3. Attach a policy for the service account. Use priority lane only for
   workloads that must outrank normal pipeline work.
4. The external service creates, renews, and releases Resource Manager resource
   requests while it holds capacity. Include a service-account subject for the
   policy and a target subject, such as a service connector, for the pool
   target binding.

## Policy for an external service

For an inference service that needs to reclaim an H200 node pool during peak
traffic, use a service-account policy. A grantless policy is often appropriate
when the service should access the full matching class bundle.

```json
{
  "pool": "prod-eu-gpu",
  "subject_selector": {
    "any": [
      {
        "subject_type": "organization",
        "subject_id": "<org-id>",
        "contains": {
          "subject_type": "account",
          "subject_id": "<service-account-id>",
          "attributes": {
            "is_service_account": true
          }
        }
      }
    ]
  },
  "preemption_group": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "account",
      "subject_id": "<service-account-id>",
      "attributes": {
        "is_service_account": true
      }
    }
  },
  "priority_lane": true,
  "concurrency_limit": 8,
  "grants": []
}
```

`priority_lane: true` gives the policy the maximum Resource Manager priority.
In authoritative mode, it can reclaim lower-priority work that opted into
reclaim. It still respects pool target bindings, class matching, class
capacity, and concurrency limits.

Use grant-based policies instead when the external service should receive only
a slice of the pool:

```json
{
  "pool": "prod-eu-gpu",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "account",
      "subject_id": "<service-account-id>",
      "attributes": {
        "is_service_account": true
      }
    }
  },
  "priority": 200,
  "priority_lane": false,
  "grants": [
    {
      "class": "h200-reserved",
      "resources": [
        {
          "resource": "h200",
          "reserved": 2,
          "limit": 4,
          "unit": "GPU",
          "missing_action": "reject"
        },
        {
          "resource": "CPU",
          "reserved": 16,
          "limit": 64,
          "unit": "CPU",
          "missing_action": "default",
          "default_value": 8
        },
        {
          "resource": "memory",
          "reserved": 128,
          "limit": 512,
          "unit": "GiB",
          "missing_action": "default",
          "default_value": 64
        }
      ]
    }
  ]
}
```

## Direct request shape

Direct callers create runtime requests with subjects and demands. The service
account subject should follow the same root-first convention used by ZenML:
`organization -> account`.

```json
{
  "subjects": [
    {
      "subject_type": "organization",
      "subject_id": "<org-id>",
      "child": {
        "subject_type": "account",
        "subject_id": "<service-account-id>",
        "attributes": {
          "is_service_account": true,
          "name": "inference-capacity-controller"
        }
      }
    },
    {
      "subject_type": "organization",
      "subject_id": "<org-id>",
      "child": {
        "subject_type": "workspace",
        "subject_id": "<workspace-id>",
        "child": {
          "subject_type": "service_connector",
          "subject_id": "<connector-id>",
          "attributes": {
            "connector_type": "gcp",
            "effective_resource_type": "kubernetes-cluster",
            "effective_resource_id": "prod-eu"
          }
        }
      }
    }
  ],
  "pool": "prod-eu-gpu",
  "demands": [
    {
      "resource": "h200",
      "quantity": 4,
      "unit": "GPU",
      "class": "h200-reserved"
    },
    {
      "resource": "CPU",
      "quantity": 48,
      "unit": "CPU",
      "class": "h200-reserved"
    },
    {
      "resource": "memory",
      "quantity": 384,
      "unit": "GiB",
      "class": "h200-reserved"
    }
  ],
  "reclaim_tolerance": "none",
  "lease_expires_at": "2026-07-23T18:30:00Z",
  "metadata": {
    "workload": "online-inference",
    "service": "recommendations"
  }
}
```

If the request is admitted, Resource Manager returns an allocated or pending
request. The external service must renew the lease while it holds capacity and
release the request when the workload no longer needs it.

## Pool selectors

External systems can use `pool` for an exact pool name or `pool_selector` to
target pools by attributes. Pool selectors are useful when you model one pool
per node, cluster, region, or machine-type family.

```json
{
  "pool_selector": {
    "all": [
      {"equals": {"cluster": "prod-eu"}},
      {"equals": {"node_pool": "h200-reserved"}}
    ]
  },
  "demands": [
    {"kind": "gpu", "quantity": 2, "class": "h200-reserved"}
  ]
}
```

## Reclaim behavior

External workloads typically use one of two patterns:

| Pattern | Policy | Request reclaim tolerance |
| --- | --- | --- |
| Critical service reclaiming shared hardware | Priority lane, often grantless | `none` |
| Opportunistic external batch work | Normal priority, grant-based limits | `coordinated` or `any` |

In authoritative pools, priority-lane work can preempt lower-priority requests
only when those requests are eligible for reclaim. It does not preempt other
priority-lane work at the same priority.

In governance pools, Resource Manager records governance decisions and target
settings, but allocation and preemption are expected to happen in the external
infrastructure scheduler.

## Target settings

External workloads may rely on pool or class target settings for service
connector selection. The UI currently exposes service connector settings at the
pool and class levels:

```json
{
  "target_type": "service_connector",
  "settings": {
    "connector_id": "<connector-id>",
    "resource_type": "kubernetes-cluster",
    "resource_id": "prod-eu"
  }
}
```

Component target settings are also available at pool, class, policy, and grant
levels when ZenML will launch work through a stack component.

## Operational tips

* Use service accounts for external systems, not personal user accounts.
* Keep direct request subjects scoped exactly like ZenML subjects so policies
  match predictably.
* Renew leases before they expire; otherwise Resource Manager returns capacity
  to the pool.
* Release requests as soon as the external workload is done.
* Reserve priority lane for workloads that genuinely need maximum priority.
* Include CPU and memory in class bundles when the external workload consumes
  them, even if GPU is the scarce resource.

## See also

* [Admin guide](resource-pools-admin-guide.md) - configure service-account
  policies.
* [Core concepts](resource-pools-core-concepts.md) - selector and request
  conventions.
* [Reconciliation process](resource-pools-reconciliation.md) - priority,
  preemption, and leases.
* [Examples](resource-pools-examples.md) - external inference example.
