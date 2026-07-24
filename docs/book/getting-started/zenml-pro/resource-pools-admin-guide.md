---
description: >-
  How platform admins configure resource descriptors, pools, classes, target
  settings, policies, and grants in ZenML Pro.
---
# Admin guide

This guide is for platform admins who operate ZenML Pro resource pools. Admins
define the resource vocabulary, map that vocabulary to real infrastructure,
and decide which users, teams, projects, pipelines, and workloads may consume
the shared capacity.

Configure resource pools in the ZenML Pro UI:

* **Organization Settings > Resource Pools** for organization-scoped pools.
* **Workspace Settings > Resource Pools** for workspace-scoped pools.

The two locations use the same forms and concepts. The JSON snippets below use
the Resource Manager REST API shape exactly, so they are suitable as automation
references.

## Before you start

You need:

* A workspace with resource pools enabled. See
  [Enable Resource Pools](deploy-workspace-resource-pools.md).
* Stack components that will run pooled workloads, usually orchestrators and
  step operators.
* Service connectors if ZenML needs credentials to access the infrastructure.
* A resource model that matches reality: Kubernetes node pools, cloud machine
  types, GPU partitions, license pools, or shared storage classes.

## Step 1: Build the resource vocabulary

Open the Resource Pools page and use the resource descriptor section to review
or create descriptors. Stock descriptors are available for `CPU`, `memory`,
and `GPU`. Add custom descriptors for hardware-specific resources or platform
constraints.

Use descriptor `kind` carefully. The built-in kinds `cpu`, `memory`, and `gpu`
are how Resource Manager matches the typed `ResourceSettings` fields that
authors configure on steps:

* Use `kind: "gpu"` for every GPU-like descriptor, such as `GPU`, `h200`, or
  `a10g`, so typed `ResourceSettings(gpu_count=...)` demands can match them.
* Use `kind: "cpu"` for every CPU-like descriptor that should match
  `ResourceSettings(cpu_count=...)`.
* Use `kind: "memory"` for every memory-like descriptor that should match
  `ResourceSettings(memory=...)`.
* Use a custom kind such as `license` when authors should request the resource
  explicitly by name.

Example API payload for a custom H200 descriptor:

```json
{
  "name": "h200",
  "kind": "gpu",
  "description": "NVIDIA H200 GPU",
  "attributes": {
    "vendor": "nvidia",
    "model": "H200",
    "vram_gb": 141,
    "architecture": "hopper"
  },
  "units": [
    {"name": "GPU", "multiplier": 1}
  ]
}
```

Example API payload for a custom license descriptor:

```json
{
  "name": "training-license",
  "kind": "license",
  "description": "Floating training license seat",
  "attributes": {
    "vendor": "acme",
    "scope": "organization"
  },
  "units": [
    {"name": "seat", "multiplier": 1}
  ]
}
```

## Step 2: Create a resource pool

In the UI, click **Add resource pool**. Configure:

| UI area | What it controls |
| --- | --- |
| Name and description | Human-readable identity |
| Rank | Which pool wins when multiple pools can satisfy the same request |
| Accounting mode | Whether Resource Manager enforces allocation (`authoritative`), gives hints (`advisory`), or only governs routing (`governance`) |
| Concurrency limit | Optional pool-wide cap on active requests |
| Targets | Which runtime target subjects the pool governs |
| Classes | Resource bundles available inside the pool |
| Target settings | Component or service connector settings applied from the pool |
| Attributes | Metadata used by pool selectors and operations |

Use `authoritative` unless your infrastructure scheduler should remain the
source of truth. `governance` is suitable with schedulers such as Kueue or
Run:ai that handle allocation and preemption themselves. `advisory` is an
advanced middle ground.

### Target bindings

Targets describe how workloads enter the infrastructure. For pools, the main
targets are stack components and service connectors:

* Stack components, usually orchestrators or step operators, launch workloads.
* Service connectors provide authentication to infrastructure resources.

The Resource Manager API uses `target_bindings` with a `target_selector`.
Selectors must match the root-first subject chains attached to requests.

```json
{
  "target_bindings": [
    {
      "target_selector": {
        "any": [
          {
            "subject_type": "organization",
            "subject_id": "<org-id>",
            "contains": {
              "subject_type": "workspace",
              "subject_id": "<workspace-id>",
              "contains": {
                "subject_type": "component",
                "subject_id": "<step-operator-id>",
                "attributes": {
                  "component_type": "step_operator"
                }
              }
            }
          },
          {
            "subject_type": "organization",
            "subject_id": "<org-id>",
            "contains": {
              "subject_type": "workspace",
              "subject_id": "<workspace-id>",
              "contains": {
                "subject_type": "service_connector",
                "subject_id": "<connector-id>",
                "attributes": {
                  "connector_type": "gcp"
                }
              }
            }
          }
        ]
      }
    }
  ]
}
```

See [Core concepts - Subject selectors](resource-pools-core-concepts.md#subject-selectors)
for the full scope convention.

## Step 3: Add classes as resource bundles

Classes are resource bundles. Model the shape your infrastructure actually
offers instead of creating separate classes for each resource. For example,
an H200 Kubernetes node pool should usually bundle H200 GPUs, CPU, and memory
in the same class.

In the class form, configure:

| UI area | What it controls |
| --- | --- |
| Class name | Pool-local label, such as `h200-reserved` |
| Rank | Preference among classes; higher ranks are tried first |
| Reclaimable | Whether capacity is safe from external reclaim: `never`, `coordinated`, or `unsafe` |
| Concurrency limit | Optional cap on active requests in the class |
| Resources | One or more descriptor quantities in the bundle |
| Target settings | Component or service connector settings applied when the class wins |
| Attributes | Metadata used by class selectors and operators |

Use finite quantities for resources you want Resource Manager to limit at the
class level. Use unlimited quantity for resources you want to track without a
pool-class limit. Grants can still impose reservations and limits later.

Example pool with two believable Kubernetes node-pool classes:

```json
{
  "name": "prod-eu-gpu",
  "description": "Production GPU capacity in the EU Kubernetes cluster",
  "rank": 100,
  "accounting_mode": "authoritative",
  "concurrency_limit": 40,
  "target_bindings": [
    {
      "target_selector": {
        "any": [
          {
            "subject_type": "organization",
            "subject_id": "<org-id>",
            "contains": {
              "subject_type": "workspace",
              "subject_id": "<workspace-id>",
              "contains": {
                "subject_type": "component",
                "subject_id": "<step-operator-id>",
                "attributes": {
                  "component_type": "step_operator"
                }
              }
            }
          },
          {
            "subject_type": "organization",
            "subject_id": "<org-id>",
            "contains": {
              "subject_type": "workspace",
              "subject_id": "<workspace-id>",
              "contains": {
                "subject_type": "service_connector",
                "subject_id": "<connector-id>",
                "attributes": {
                  "connector_type": "gcp"
                }
              }
            }
          }
        ]
      }
    }
  ],
  "classes": [
    {
      "class": "h200-reserved",
      "rank": 100,
      "reclaimable": "never",
      "concurrency_limit": 8,
      "resources": [
        {"resource": "h200", "quantity": 8, "unit": "GPU"},
        {"resource": "CPU", "quantity": 128, "unit": "CPU"},
        {"resource": "memory", "quantity": 1024, "unit": "GiB"}
      ],
      "target_settings": [
        {
          "target_type": "component",
          "settings": {
            "pod_settings": {
              "node_selector": {
                "cloud.google.com/gke-nodepool": "h200-reserved"
              },
              "tolerations": [
                {
                  "key": "dedicated",
                  "operator": "Equal",
                  "value": "h200",
                  "effect": "NoSchedule"
                }
              ]
            }
          }
        }
      ],
      "attributes": {
        "accelerator": "h200",
        "purchase": "reserved"
      }
    },
    {
      "class": "a10-burst",
      "rank": 40,
      "reclaimable": "coordinated",
      "concurrency_limit": 20,
      "resources": [
        {"resource": "GPU", "quantity": 16, "unit": "GPU"},
        {"resource": "CPU", "quantity": null},
        {"resource": "memory", "quantity": null}
      ],
      "target_settings": [
        {
          "target_type": "component",
          "settings": {
            "pod_settings": {
              "node_selector": {
                "cloud.google.com/gke-nodepool": "a10-burst"
              }
            }
          }
        }
      ],
      "attributes": {
        "accelerator": "a10",
        "purchase": "shared-burst"
      }
    }
  ],
  "target_settings": [
    {
      "target_type": "service_connector",
      "settings": {
        "connector_id": "<connector-id>",
        "resource_type": "kubernetes-cluster",
        "resource_id": "prod-eu"
      }
    }
  ],
  "attributes": {
    "region": "eu-west-1",
    "cluster": "prod-eu"
  }
}
```

## Step 4: Attach policies

Open a pool detail page and attach a policy. Policies answer "who may use this
pool, with what priority, and under which limits?"

In the policy form, configure:

| UI area | What it controls |
| --- | --- |
| Subjects | Who gets access. Common subjects are workspaces, projects, pipelines, accounts, service accounts, and teams |
| Match mode | Whether any selected subject is enough or all must match |
| Time window | Optional one-time, schedule, or cycle policy window |
| Preemption group | Optional related-work selector that prevents self-preemption |
| Priority or priority lane | Contention ordering |
| Concurrency limit | Optional policy-wide active request cap |
| Component target settings | Policy-level settings merged into the selected component |
| Grants | Optional class-level reservations, limits, defaults, and grant concurrency limits |

### Grant-based policy

Use grants when you want reservations, per-team limits, defaults for omitted
resources, or grant-level concurrency caps.

```json
{
  "pool": "prod-eu-gpu",
  "subject_selector": {
    "any": [
      {
        "subject_type": "organization",
        "subject_id": "<org-id>",
        "contains": {
          "subject_type": "team",
          "subject_id": "<ml-platform-team-id>"
        }
      }
    ]
  },
  "priority": 100,
  "priority_lane": false,
  "concurrency_limit": 12,
  "target_settings": [
    {
      "target_type": "component",
      "settings": {
        "pod_settings": {
          "labels": {
            "zenml.io/resource-policy": "ml-platform-prod"
          }
        }
      }
    }
  ],
  "grants": [
    {
      "class": "h200-reserved",
      "concurrency_limit": 6,
      "resources": [
        {
          "resource": "h200",
          "reserved": 4,
          "limit": 8,
          "unit": "GPU",
          "missing_action": "reject"
        },
        {
          "resource": "CPU",
          "reserved": 32,
          "limit": 128,
          "unit": "CPU",
          "missing_action": "default",
          "default_value": 4
        },
        {
          "resource": "memory",
          "reserved": 256,
          "limit": 1024,
          "unit": "GiB",
          "missing_action": "default",
          "default_value": 16
        }
      ]
    }
  ]
}
```

Grant resource behavior:

* If a request demands a resource that is in the class but missing from the
  grant, the grant cannot admit it.
* `reserved` is the protected share for non-reclaimable work.
* `limit: null` means the limit follows the class resource quantity.
* `missing_action: "omit"` does not allocate an omitted resource.
* `missing_action: "default"` allocates `default_value` when the request omits
  the resource.
* `missing_action: "reject"` requires the request to mention the resource.

### Grantless policy

Use `grants: []` when the subject should access every matching class resource
in the pool without per-grant reservations or limits. The effective reservation
is 0 and the effective limit is the class resource quantity.

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
          "subject_id": "<external-inference-service-account-id>",
          "attributes": {
            "is_service_account": true
          }
        }
      }
    ]
  },
  "priority_lane": true,
  "concurrency_limit": 20,
  "grants": []
}
```

Priority lane gives the policy the maximum Resource Manager priority. It can
reclaim lower-priority work that opted into reclaim, but it does not bypass
pool target bindings, class matching, or capacity checks in authoritative mode.

## Step 5: Use selectors intentionally

Pool target selectors and policy subject selectors match the subjects attached
to resource requests. The same subject can appear at different scopes, so write
selectors root-first.

Recommended main story:

| Selector location | Common subject choices |
| --- | --- |
| Pool targets | Stack components and service connectors |
| Policies | Workspaces, projects, pipelines, user accounts, service accounts, and teams |

Avoid overly broad policies on scarce resources unless the pool is meant to be
shared by everyone. Prefer a broad target binding, such as one step operator,
and narrower policy subjects, such as one team or project.

## Step 6: Operate pools

Use the Resource Pools page and pool detail pages to inspect:

* Pool classes and their bundled resources.
* Policies attached to a pool.
* Grant reservations and limits.
* Active allocations and queued requests.
* Which pool, class, policy, and grant admitted a request.

The CLI can inspect resource requests:

```shell
zenml resource-request list --status pending
zenml resource-request list --pool-id <pool-id>
zenml resource-request describe <request-id>
```

Pool, descriptor, class, policy, grant, and allocation configuration is done
through the UI or the Resource Manager API, not the ZenML CLI.

## Checklist

Before handing a pool to users:

* Descriptors use stable names and kinds.
* Classes bundle resources the way infrastructure actually provides them.
* CPU and memory are included when they matter for scheduling or traceability.
* Unlimited class resources are intentional and documented for operators.
* Target bindings match the stack components or service connectors that will
  appear on runtime requests.
* Policies use the right subjects for access control.
* Grant-based policies include every class resource that requests may demand,
  or use `missing_action: "default"` where a default allocation is desired.
* Priority-lane policies are reserved for critical or external workloads that
  genuinely need maximum priority.
* Accounting mode is `authoritative` unless another scheduler owns allocation.

## See also

* [Core concepts](resource-pools-core-concepts.md) - definitions and selector
  conventions.
* [User guide](resource-pools-user-guide.md) - what pipeline authors configure.
* [External workloads](resource-pools-external-workloads.md) - direct Resource
  Manager requests and priority-lane patterns.
* [Examples](resource-pools-examples.md) - end-to-end scenarios.
* [Reconciliation process](resource-pools-reconciliation.md) - runtime behavior.
