---
description: >-
  How platform admins configure resource descriptors, pools, classes, target
  bindings, policies, and grants in ZenML Pro.
---
# Admin guide

This guide is for platform admins who operate ZenML Pro resource pools. Admins
define the resource vocabulary, map that vocabulary to real infrastructure,
and decide which users, teams, projects, pipelines, and workloads may consume
the shared capacity.

Resource pool administration is API-driven. The examples on this page are
request bodies for these Resource Manager REST API endpoints:

| Operation | Endpoint |
| --- | --- |
| Create a resource descriptor | `POST /v1/resources` |
| Create a resource pool, including its classes and target bindings | `POST /v1/resource-pools` |
| Create a policy and its grants | `POST /v1/resource-policies` |
| Update an existing object | `PATCH` the corresponding resource, pool, or policy endpoint |

The API resolves resource descriptors and pools by UUID or exact name. The
examples use names where that makes the configuration easier to read.

## Before you start

You need:

* A workspace with resource pools enabled. See
  [Enable Resource Pools](deploy-workspace-resource-pools.md).
* Stack components that will run pooled workloads, usually orchestrators and
  step operators.
* Service connectors if ZenML needs credentials to access the infrastructure.
* A resource model that matches reality: Kubernetes node pools, cloud machine
  types, GPU partitions, license pools, or shared storage classes.

The examples below use a GKE cluster with two GPU node pools. The same API
structure applies to other Kubernetes providers and to non-Kubernetes capacity.

## Step 1: Build the resource vocabulary

Use `POST /v1/resources` to create resource descriptors. Stock descriptors are
available for `CPU`, `memory`, and `GPU`. Add custom descriptors for
hardware-specific resources or platform constraints.

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

For example, this descriptor represents H200 GPUs installed in one or more
Kubernetes node pools:

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

A descriptor can also represent non-compute capacity. This example describes a
pool of floating license seats:

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

### Units and multipliers

A unit gives admins and workload authors a convenient way to express integer
quantities of the same resource at different scales. Its `multiplier` converts
that unit to the descriptor's base unit:

```text
base quantity = quantity * multiplier
```

At least one unit must have `multiplier: 1`; that is the base unit. Every
multiplier must be a positive integer, and unit names must be unique within the
descriptor. If a class, grant, or request omits `unit`, Resource Manager treats
the quantity as already expressed in base units.

The stock `CPU` descriptor illustrates why this is useful. Its base unit is
`mCPU`, and one `CPU` equals 1,000 `mCPU`:

```json
{
  "name": "CPU",
  "kind": "cpu",
  "units": [
    {"name": "mCPU", "multiplier": 1},
    {"name": "CPU", "multiplier": 1000}
  ]
}
```

A class quantity of 64 `CPU` and a request for 500 `mCPU` are therefore
compared as 64,000 and 500 base units. Units make fractional CPU values
representable without allowing fractional API quantities.

You can define several units for a custom resource in the same way. For
example, use MiB as the base unit for Kubernetes ephemeral storage while
allowing capacity and requests to use GiB or TiB:

```json
{
  "name": "scratch-storage",
  "kind": "storage",
  "description": "Local ephemeral storage on training nodes",
  "units": [
    {"name": "MiB", "multiplier": 1},
    {"name": "GiB", "multiplier": 1024},
    {"name": "TiB", "multiplier": 1048576}
  ]
}
```

The same descriptor can then be used with different units at each API layer:

```json
{
  "class_resource": {
    "resource": "scratch-storage",
    "quantity": 2,
    "unit": "TiB"
  },
  "grant_resource": {
    "resource": "scratch-storage",
    "reserved": 256,
    "limit": 1024,
    "unit": "GiB",
    "missing_action": "omit"
  },
  "request_demand": {
    "resource": "scratch-storage",
    "quantity": 524288,
    "unit": "MiB"
  }
}
```

Here, the class contains 2 TiB, the policy reserves 256 GiB and permits up to
1 TiB, and the example request asks for 512 GiB. Resource Manager converts all
three values to MiB before comparing them.

## Step 2: Create a resource pool

Use `POST /v1/resource-pools` to create the pool and configure:

| Configuration area | What it controls |
| --- | --- |
| Name and description | Human-readable identity |
| Rank | Which pool wins when multiple pools can satisfy the same request |
| Accounting mode | Whether Resource Manager enforces allocation (`authoritative`), gives hints (`advisory`), or only governs routing (`governance`) |
| Concurrency limit | Optional pool-wide cap on active requests |
| Target bindings | Which runtime target subjects the pool governs |
| Classes | Resource bundles available inside the pool |
| Attributes | Metadata used by pool selectors and operations |

Use `authoritative` unless your infrastructure scheduler should remain the
source of truth. `governance` is suitable with schedulers such as Kueue or
Run:ai that handle allocation and preemption themselves. `advisory` is an
advanced middle ground.

A minimal pool can be created first and populated with classes in the same
request or a later `PATCH`:

```json
{
  "name": "prod-eu-gpu",
  "description": "GPU node pools in the production EU Kubernetes cluster",
  "rank": 100,
  "accounting_mode": "authoritative",
  "concurrency_limit": 40,
  "attributes": {
    "provider": "gcp",
    "region": "europe-west4",
    "cluster": "prod-eu"
  }
}
```

### Target bindings

Target bindings describe how requests enter the infrastructure governed by the
pool. Each entry contains a `target_selector` that is matched against the
root-first target subject chains on a resource request. A pool is considered
only when at least one binding matches.

For ZenML pipeline steps, bind the pool to the stack component that launches
the workload, usually an orchestrator or step operator. This example binds one
Kubernetes step operator:

```json
{
  "target_bindings": [
    {
      "target_selector": {
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
      }
    }
  ]
}
```

A pool used by several Kubernetes execution components can combine bindings
with `any`:

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
                "subject_id": "<kubernetes-orchestrator-id>"
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
                "subject_type": "component",
                "subject_id": "<kubernetes-step-operator-id>"
              }
            }
          }
        ]
      }
    }
  ]
}
```

Direct external workloads can instead carry a service connector as a target
subject. In that case, a target binding may select the connector. A target
binding only routes requests; it does not configure or replace connector
credentials.

See [Core concepts - Subject selectors](resource-pools-core-concepts.md#subject-selectors)
for the complete root-first scope convention.

## Step 3: Add classes as resource bundles

Classes are resource bundles. Model the shape your infrastructure actually
offers instead of creating a separate class for every resource. For example,
an H200 Kubernetes node pool should usually bundle its aggregate H200 GPU, CPU,
and memory capacity in one class.

Configure each class in the `classes` list of a pool create or update request:

| Configuration area | What it controls |
| --- | --- |
| Class name | Pool-local label, such as `h200-reserved` |
| Rank | Preference among classes; higher ranks are tried first |
| Reclaimable | Whether capacity is safe from external reclaim: `never`, `coordinated`, or `unsafe` |
| Concurrency limit | Optional cap on active requests in the class |
| Resources | One or more descriptor quantities in the bundle |
| Component target settings | Stack component settings applied when the class wins |
| Attributes | Metadata used by class selectors and operators |

Use finite quantities for resources you want Resource Manager to limit at the
class level. Mark an unlimited resource with `"quantity": null`. Unlimited
means there is no pool-class capacity ceiling for that resource; the resource
can still be allocated and tracked, and policies can impose reservations and
limits later.

The following complete pool payload models two Kubernetes node pools:

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
              "node_selectors": {
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
      "reclaimable": "unsafe",
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
              "node_selectors": {
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
  "attributes": {
    "provider": "gcp",
    "region": "europe-west4",
    "cluster": "prod-eu"
  }
}
```

Each class represents one GKE node pool. Its resource quantities are the sum
of the resources Resource Manager may allocate across all nodes in that node
pool, not the shape of one node. If `h200-reserved` consists of two nodes with
four GPUs, 64 CPU cores, and 512 GiB of memory each, its class totals are 8
GPUs, 128 CPUs, and 1,024 GiB.

The two reclaim modes reflect how the underlying capacity behaves:

* `h200-reserved` uses `never` because the nodes are stable capacity that
  Resource Manager should not expect the infrastructure to revoke.
* `a10-burst` uses `unsafe` because shared burst capacity may disappear without
  a coordinated drain. In authoritative mode, only requests with
  `reclaim_tolerance: "any"` are eligible for this class. Use it for
  interruption-tolerant workloads such as checkpointed training or retryable
  batch steps, not workloads that must run continuously for a long period.

CPU and memory are unlimited in `a10-burst` because this example tracks and
passes their allocations to Kubernetes when they are requested or defaulted,
without making Resource Manager the capacity authority for them. Set finite
totals instead if Resource Manager must prevent CPU or memory over-allocation.

The component target settings connect an abstract class selection to the real
node pool. When `h200-reserved` wins, ZenML merges the `pod_settings` into the
selected Kubernetes component settings. The `node_selectors` field causes
Kubernetes to place the pod on nodes labeled with that GKE node pool, and the
toleration lets the pod be scheduled onto nodes protected by the matching
`dedicated=h200:NoSchedule` taint. The burst class injects its own node selector
instead. Resource quantities admitted by Resource Manager are also reflected
in the Kubernetes pod resource requests.

For a cloud machine inventory, use the same pattern: one class can represent
the aggregate allocatable resources of an AWS EC2 Auto Scaling group or an
Azure VM Scale Set, with class attributes identifying the machine family,
region, and purchase model.

### Topology limitation and fixed-node workaround

{% hint style="warning" %}
Resource Manager is not currently topology-aware. It accounts for the total
resources declared by a class, but it does not know how those resources are
distributed across the individual Kubernetes nodes, virtual machines, or
instances behind that class. This limitation can cause resource fragmentation.
A future update is planned to introduce topology-aware resource management.
{% endhint %}

For example, suppose a Kubernetes node pool has two nodes with four GPUs each.
After two workloads consume three GPUs on each node, the class has two GPUs
free in total. Resource Manager sees enough aggregate capacity for another
two-GPU workload, but Kubernetes cannot place that workload because neither
node has two GPUs available. Similar fragmentation can happen when a request's
CPU, memory, and GPU requirements do not coexist on any single machine even
though their totals fit the class.

For infrastructure that does not scale dynamically, an admin can avoid this
aggregate accounting problem by representing every machine as a separate
class. This workaround is suitable when:

* Nodes or VMs are always running and autoscaling is disabled.
* The set of machines and their allocatable resources are known in advance.
* Each machine has a stable label that component target settings can select.

The following fragment represents four fixed Kubernetes nodes from two
hardware families. Each node has its own class, per-node resource quantities,
and a `node_selectors` value that sends the selected workload to that exact
node:

```json
{
  "classes": [
    {
      "class": "h200-node-01",
      "rank": 100,
      "reclaimable": "never",
      "resources": [
        {"resource": "h200", "quantity": 4, "unit": "GPU"},
        {"resource": "CPU", "quantity": 64, "unit": "CPU"},
        {"resource": "memory", "quantity": 512, "unit": "GiB"}
      ],
      "target_settings": [
        {
          "target_type": "component",
          "settings": {
            "pod_settings": {
              "node_selectors": {
                "zenml.io/resource-node": "h200-node-01"
              }
            }
          }
        }
      ],
      "attributes": {
        "machine_family": "h200",
        "node": "h200-node-01"
      }
    },
    {
      "class": "h200-node-02",
      "rank": 100,
      "reclaimable": "never",
      "resources": [
        {"resource": "h200", "quantity": 4, "unit": "GPU"},
        {"resource": "CPU", "quantity": 64, "unit": "CPU"},
        {"resource": "memory", "quantity": 512, "unit": "GiB"}
      ],
      "target_settings": [
        {
          "target_type": "component",
          "settings": {
            "pod_settings": {
              "node_selectors": {
                "zenml.io/resource-node": "h200-node-02"
              }
            }
          }
        }
      ],
      "attributes": {
        "machine_family": "h200",
        "node": "h200-node-02"
      }
    },
    {
      "class": "a10-node-01",
      "rank": 50,
      "reclaimable": "never",
      "resources": [
        {"resource": "GPU", "quantity": 4, "unit": "GPU"},
        {"resource": "CPU", "quantity": 32, "unit": "CPU"},
        {"resource": "memory", "quantity": 128, "unit": "GiB"}
      ],
      "target_settings": [
        {
          "target_type": "component",
          "settings": {
            "pod_settings": {
              "node_selectors": {
                "zenml.io/resource-node": "a10-node-01"
              }
            }
          }
        }
      ],
      "attributes": {
        "machine_family": "a10",
        "node": "a10-node-01"
      }
    },
    {
      "class": "a10-node-02",
      "rank": 50,
      "reclaimable": "never",
      "resources": [
        {"resource": "GPU", "quantity": 4, "unit": "GPU"},
        {"resource": "CPU", "quantity": 32, "unit": "CPU"},
        {"resource": "memory", "quantity": 128, "unit": "GiB"}
      ],
      "target_settings": [
        {
          "target_type": "component",
          "settings": {
            "pod_settings": {
              "node_selectors": {
                "zenml.io/resource-node": "a10-node-02"
              }
            }
          }
        }
      ],
      "attributes": {
        "machine_family": "a10",
        "node": "a10-node-02"
      }
    }
  ]
}
```

Apply the corresponding `zenml.io/resource-node` label to exactly one
Kubernetes node for each class. You can use another stable, unique label or
`kubernetes.io/hostname` instead. When Resource Manager selects a class, the
node selector pins the pod to the machine whose capacity that class represents,
so capacity cannot be combined incorrectly across nodes.

Policies that use explicit grants must have a grant for every per-node class
they may select. Keep the configured class quantities and labels synchronized
with the real machines. Do not use this workaround for autoscaled node pools,
VM scale sets, or Auto Scaling groups whose instance identities or counts can
change; their per-node class inventory would quickly become stale.

## Step 4: Attach policies

Use `POST /v1/resource-policies` to attach an access policy to a pool. A policy
answers “who may use this pool, when may they use it, at what priority, and
which runtime settings apply?” Add class-specific reservations and limits as
grants in Step 5.

Configure these policy fields:

| Configuration area | What it controls |
| --- | --- |
| Pool | Pool UUID or exact name to which the policy applies |
| Subjects | Who gets access, expressed as a `subject_selector` |
| Time | Optional one-time, scheduled, or recurring access windows for the entire selector or individual selector branches |
| Preemption group | Optional selector that prevents related requests from preempting one another |
| Priority or priority lane | Contention ordering |
| Concurrency limit | Optional policy-wide active request cap |
| Component target settings | Policy-level stack component settings applied only when this policy admits a request |

The following fragment shows the policy-level configuration for one team. Add
the intended `grants` from Step 5 before sending the create request. If you
omit `grants`, the API creates a grantless policy with access to every matching
class, as described under [Grantless policies](#grantless-policies).

```json
{
  "pool": "prod-eu-gpu",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "team",
      "subject_id": "<ml-platform-team-id>"
    }
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
  ]
}
```

### Subjects

The `subject_selector` controls which request identities may use the policy.
Common subjects include workspaces, projects, pipelines, user accounts,
service accounts, and teams. Scope selectors are root-first; for example, a
project is selected through its organization and workspace chain.

Select one user account with a single selector:

```json
{
  "subject_selector": {
    "subject_type": "account",
    "subject_id": "<user-account-id>"
  }
}
```

Use `all` to require both the user account and a particular project. Requests
must carry subject chains that satisfy both branches, so the same account is
not admitted when it runs a pipeline in another project:

```json
{
  "subject_selector": {
    "all": [
      {
        "subject_type": "account",
        "subject_id": "<user-account-id>"
      },
      {
        "subject_type": "organization",
        "subject_id": "<org-id>",
        "contains": {
          "subject_type": "workspace",
          "subject_id": "<workspace-id>",
          "contains": {
            "subject_type": "project",
            "subject_id": "<project-id>"
          }
        }
      }
    ]
  }
}
```

Use `any` when either a user or a team should qualify:

```json
{
  "subject_selector": {
    "any": [
      {
        "subject_type": "account",
        "subject_id": "<user-account-id>"
      },
      {
        "subject_type": "organization",
        "subject_id": "<org-id>",
        "contains": {
          "subject_type": "team",
          "subject_id": "<research-team-id>"
        }
      }
    ]
  }
}
```

Stack components are valid policy subjects too. For example, select all
requests carrying one Kubernetes step operator with the same
organization-to-workspace-to-component chain used for a pool target binding.
Use a component as a policy subject only when access should be coupled to that
component; normally the component belongs in the pool target binding and the
policy selects a user, team, project, or pipeline.

### Time

Add `time_selector` to the root `subject_selector` to gate the entire policy.
Add it to individual entries inside `all` or `any` to give those branches
different windows. A time selector contains exactly one of `one_time`,
`schedule`, or `cycle`:

* `one_time` is one concrete interval with an inclusive start and exclusive
  end.
* `schedule` repeats a local clock window on selected weekdays, month days,
  weeks of a month, or months. Empty calendar filters mean every value in that
  dimension.
* `cycle` defines an anchored interval in each daily, weekly, monthly, or
  yearly cycle and is useful for windows that span multiple days.

This global schedule limits every branch of a policy to weekday business hours
in Berlin:

```json
{
  "subject_selector": {
    "any": [
      {
        "subject_type": "organization",
        "subject_id": "<org-id>",
        "contains": {
          "subject_type": "team",
          "subject_id": "<research-team-id>"
        }
      },
      {
        "subject_type": "account",
        "subject_id": "<platform-admin-account-id>"
      }
    ],
    "time_selector": {
      "schedule": {
        "timezone": "Europe/Berlin",
        "start_time": "08:00:00",
        "end_time": "18:00:00",
        "days_of_week": ["mon", "tue", "wed", "thu", "fri"]
      }
    }
  }
}
```

For branch-specific time, place `time_selector` on each entry. Here the
research team gets a one-time benchmarking window, while the platform account
gets a weekly weekend maintenance cycle:

```json
{
  "subject_selector": {
    "any": [
      {
        "subject_type": "organization",
        "subject_id": "<org-id>",
        "contains": {
          "subject_type": "team",
          "subject_id": "<research-team-id>"
        },
        "time_selector": {
          "one_time": {
            "start": "2026-10-01T08:00:00+02:00",
            "end": "2026-10-03T18:00:00+02:00"
          }
        }
      },
      {
        "subject_type": "account",
        "subject_id": "<platform-admin-account-id>",
        "time_selector": {
          "cycle": {
            "timezone": "Europe/Berlin",
            "frequency": "weekly",
            "start": {
              "day_of_week": "sat",
              "time": "00:00:00"
            },
            "end": {
              "day_of_week": "mon",
              "time": "00:00:00"
            }
          }
        }
      }
    ]
  }
}
```

Use IANA timezone names such as `Europe/Berlin`. Offset-aware timestamps are
recommended for one-time windows. If their timestamps are local and omit an
offset, the `timezone` field is required.

### Preemption groups

A preemption group identifies related requests that must not preempt one
another. Resource Manager applies the selector to both the waiting request and
candidate victim requests. If they resolve to the same matched subject path,
the active request is protected from that waiting request.

ZenML sets the fallback preemption group on each pipeline-step request to its
current pipeline run. As a result, steps belonging to the same pipeline run do
not preempt one another by default.

A policy-level `preemption_group` overrides that fallback for requests admitted
through the policy. Select the pipeline when no runs of the same pipeline
should preempt one another, even when they are different pipeline runs:

```json
{
  "preemption_group": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "workspace",
      "subject_id": "<workspace-id>",
      "contains": {
        "subject_type": "project",
        "subject_id": "<project-id>",
        "contains": {
          "subject_type": "pipeline",
          "subject_id": "<production-training-pipeline-id>"
        }
      }
    }
  }
}
```

With this selector, a new high-priority run of the production training
pipeline queues instead of reclaiming capacity from an older run of the same
pipeline. It may still preempt eligible lower-priority work from other
pipelines. Choose a broader project or team selector only if every matching
request in that scope should be mutually protected.

### Priority and priority lane

`priority` is a non-negative ordering value; higher-priority policies are
considered before lower-priority policies during contention. Use ordinary
priorities to express relative importance, such as 100 for production
training and 20 for experiments.

Set `priority_lane: true` only for critical workloads that need Resource
Manager's reserved maximum priority. When it is true, omit `priority` from the
payload. A priority-lane policy can reclaim lower-priority work that opted into
compatible reclaim behavior, but it does not bypass target bindings, subject
matching, grants, class matching, concurrency limits, or authoritative
capacity checks.

For example, a production inference controller can use a priority lane while a
research team uses an ordinary priority:

```json
{
  "production_inference": {
    "priority_lane": true
  },
  "research_training": {
    "priority": 20,
    "priority_lane": false
  }
}
```

### Component target settings

Policy `target_settings` contain stack component settings that are used only
when that policy actually matches and admits the request. They are useful for
policy-specific infrastructure configuration that does not belong to the node
pool class itself. For example, add a Kubernetes label for cost attribution:

```json
{
  "target_settings": [
    {
      "target_type": "component",
      "settings": {
        "pod_settings": {
          "labels": {
            "cost-center": "computer-vision",
            "workload-tier": "production"
          }
        }
      }
    }
  ]
}
```

Resource Manager recursively merges component settings from the selected pool
route, class, capacity entry, policy, and grant, with the more specific layer
taking precedence. ZenML then validates the merged settings against the
selected stack component configuration and uses them when it creates the
infrastructure workload. A request admitted through another policy does not
receive these policy settings.

## Step 5: Add grants to policies

Add `grants` to a policy when you need class-specific access, reservations,
limits, defaults for omitted resources, or grant-level concurrency caps. Each
grant names exactly one pool class and describes how that policy may consume
the resources bundled in the class.

| Grant field | What it controls |
| --- | --- |
| `class` | Pool class admitted by the grant |
| `capacity_entries` | Optional named inventory entries within that class; omit to allow all entries |
| `resources` | Per-resource reservation, limit, unit, and missing-demand behavior |
| `concurrency_limit` | Optional cap on active requests using this grant |
| `target_settings` | Component settings applied only when this grant is selected |

The following complete policy reserves part of the H200 class for the ML
platform team, caps its maximum use, and supplies CPU and memory defaults:

```json
{
  "pool": "prod-eu-gpu",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "team",
      "subject_id": "<ml-platform-team-id>"
    }
  },
  "preemption_group": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "workspace",
      "subject_id": "<workspace-id>",
      "contains": {
        "subject_type": "project"
      }
    }
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

### Reservations and limits

For each grant resource:

* `reserved` is the share protected for non-reclaimable requests admitted by
  that policy. It defaults to 0 and must not exceed the resource's `limit`.
* `limit` is the maximum active quantity the grant may consume. `limit: null`
  follows the class resource quantity, which is itself unlimited when the class
  uses `quantity: null`.
* `unit` applies to `reserved`, `limit`, and `default_value`. Resource Manager
  converts values to the descriptor's base unit before comparing them.

Across all policies on the same pool, reservations for a given finite
class-resource pair may add up to the class quantity but must not exceed it. If
`h200-reserved` contains 8 GPUs, valid reservations might be 4 GPUs for
production, 2 for evaluation, and 2 for research. A further reservation is
rejected until an existing reservation is reduced or the class capacity is
increased. Reservations do not need to consume the full class quantity; any
unreserved capacity remains available for policies that can burst above their
reservation up to their limit.

For unlimited class resources there is no finite class ceiling against which
the total reservation can be checked. Use explicit grant limits whenever a
policy still needs a bounded share of that resource.

### Missing-demand actions

`missing_action` decides what happens when the grant contains a resource that
the incoming request did not ask for:

| Action | Admission and infrastructure effect |
| --- | --- |
| `reject` | This grant cannot admit the request. No allocation or infrastructure workload is created through this route. |
| `default` | Resource Manager allocates `default_value`, and ZenML includes that allocation in the resource settings sent to the orchestrator or step operator. |
| `omit` | Resource Manager creates no allocation for the omitted resource, and ZenML omits it from the resource settings derived from the allocation. |

Use `reject` on a GPU grant resource to reserve a policy for GPU-consuming
steps:

```json
{
  "resource": "h200",
  "reserved": 2,
  "limit": 8,
  "unit": "GPU",
  "missing_action": "reject"
}
```

A step with a GPU demand can match this rule. A preprocessing step that asks
only for CPU and memory cannot use this grant, even if the policy subject
selector matches. This prevents non-GPU work from occupying the H200 policy's
capacity route.

Use `default` when every admitted Kubernetes pod should receive a baseline
request even if the step author omitted it:

```json
[
  {
    "resource": "CPU",
    "reserved": 0,
    "limit": 128,
    "unit": "CPU",
    "missing_action": "default",
    "default_value": 2
  },
  {
    "resource": "memory",
    "reserved": 0,
    "limit": 1024,
    "unit": "GiB",
    "missing_action": "default",
    "default_value": 8
  }
]
```

If a step asks for GPUs but omits CPU and memory, Resource Manager accounts for
2 CPUs and 8 GiB and ZenML includes those values in the Kubernetes pod resource
requests. This avoids an effectively unconstrained pod from reaching the
cluster.

Use `omit` when the resource exists in the class and may be tracked when
explicitly requested, but is neither mandatory nor assigned a default:

```json
{
  "resource": "memory",
  "reserved": 0,
  "limit": 1024,
  "unit": "GiB",
  "missing_action": "omit"
}
```

An explicit memory demand is allocated and included in the Kubernetes pod
resource requests. If the request does not mention memory, this rule adds no
memory allocation and therefore no allocation-derived memory setting to the
infrastructure configuration. Independently configured component defaults may
still apply.

If a request does demand a class resource that is absent from the grant's
`resources` list, the grant cannot admit it. Include every resource that steps
may explicitly request through that class.

### Grantless policies

Use `"grants": []` when a trusted subject should access every matching class
resource in the pool without per-grant reservations or limits. The effective
reservation is 0 and the effective limit follows each class resource quantity.

```json
{
  "pool": "prod-eu-gpu",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "account",
      "subject_id": "<inference-service-account-id>",
      "attributes": {
        "is_service_account": true
      }
    }
  },
  "priority_lane": true,
  "concurrency_limit": 20,
  "grants": []
}
```

Grantless access still respects pool target bindings, class matching,
pool/class/policy concurrency limits, reclaim compatibility, and capacity
checks in authoritative mode. Use it deliberately; a grantless policy does not
provide the per-team isolation of explicit reservations and limits.

## Step 6: Use selectors intentionally

Pool target selectors and policy subject selectors match the subjects attached
to resource requests. The same subject can appear at different scopes, so
write selectors root-first.

| Selector location | Common subject choices |
| --- | --- |
| Pool target bindings | Stack components and, for direct external requests, service connectors |
| Policies | Workspaces, projects, pipelines, user accounts, service accounts, and teams |

Avoid overly broad policies on scarce resources unless the pool is meant to be
shared by everyone. Prefer a broad target binding, such as one step operator,
and narrower policy subjects, such as one team or project.

## Step 7: Operate pools

Resource Manager accounts for capacity and coordinates request lifecycle
changes. It does not directly delete Kubernetes pods, stop VMs, or terminate
other external workloads. Operating a pool therefore requires checking both
the Resource Manager ledger and the infrastructure that consumes it.

### Monitor capacity, allocations, and queues

Use these reads for day-to-day operations:

| Question | Route |
| --- | --- |
| What capacity is occupied, reported as running, or queued? | `GET /v1/resource-pools/{pool_id}` and inspect `ledger.occupied`, `ledger.used`, and `ledger.queue_length` |
| Which active records consume the pool? | `GET /v1/resource-pools/{pool_id}/allocations` |
| What is waiting for this pool? | `GET /v1/resource-pools/{pool_id}/queue` |
| What happened previously? | `GET /v1/resource-pools/{pool_id}/allocations?active_only=false` |
| What is the complete request state? | `GET /v1/resource-requests/{request_id}` |
| Through which pools and policies is one request queued? | `GET /v1/resource-requests/{request_id}/queue-memberships` |
| Which requests match an operational filter? | `GET /v1/resource-requests?status=pending&pool=<pool-id-or-name>` |
| Which policies configure the pool? | `GET /v1/resource-policies?pool=<pool-id-or-name>` |

`ledger.occupied` sums all allocations that have not yet been released.
`ledger.used` is the subset whose owner has reported `runtime_state: running`.
The difference is useful for finding allocations that are queued in an
external runtime, still starting, idle, or no longer sending accurate runtime
state.

The pool allocation route returns active allocations by default. Each record
identifies the request, capacity entry, resource, class, quantity, admitting
policy and grant, allocation priority, and preemption state. The queue route
returns the request, policy, priority snapshot, and enqueue time for every
membership. A single pending request can have more than one queue membership
when multiple admission routes remain viable.

For example, inspect the active ledger and queue for one pool:

```shell
curl --request GET \
  --url "${RESOURCE_MANAGER_URL}/v1/resource-pools/${POOL_ID}/allocations" \
  --header "Authorization: Bearer ${RESOURCE_MANAGER_TOKEN}"

curl --request GET \
  --url "${RESOURCE_MANAGER_URL}/v1/resource-pools/${POOL_ID}/queue" \
  --header "Authorization: Bearer ${RESOURCE_MANAGER_TOKEN}"
```

List endpoints return wrappers with `items` and `total`; resource-request lists
also include `index`, `max_size`, and `total_pages`. Request filters include
`status` (repeat it to select several statuses), `pool`, `subject_id`,
`reclaim_tolerance`, `preemption_initiated_by_id`, and caller metadata in the
form `metadata[key]=value`.

For example, this query finds pending requests created for one external job:

```shell
curl --get \
  --url "${RESOURCE_MANAGER_URL}/v1/resource-requests" \
  --header "Authorization: Bearer ${RESOURCE_MANAGER_TOKEN}" \
  --data-urlencode "status=pending" \
  --data-urlencode "pool=prod-eu-gpu" \
  --data-urlencode "metadata[external_job_id]=batch-2048"
```

### Diagnose requests that remain pending

A pending request is not necessarily stuck. It may be waiting for finite
capacity, a concurrency slot, reserved capacity held for another policy, or a
lower-priority allocation to finish or acknowledge preemption. Use this order
to diagnose it:

1. Read the request and confirm its `pool_id`, demands, `queued_at`, lease,
   policy-backed queue entries, and current `status_reason`.
2. Read its queue memberships. Compare their `priority`, `policy_id`, and
   `enqueued_at` with other entries in each pool queue.
3. Read active pool allocations. Compare their resources and classes with the
   waiting demands, and check `allocation_priority`, `preemption_state`,
   `admitted_by_policy_id`, and `resolved_grant_id`.
4. Re-read the pool and policies to check class capacity, target bindings,
   grant reservations and limits, and pool, class, policy, or grant concurrency
   limits.
5. Check the infrastructure. An allocation reported as occupied but not
   running may represent a workload that is still starting, an idle holder, or
   an owner that stopped heartbeating without a lease.

If the request is `rejected`, inspect `status_reason`; if it is
`no_matching_pool`, correct its subjects or the pool target bindings. Neither
state can be repaired in place. Submit a new request after correcting the
configuration. A `no_matching_pool` create response is ephemeral and will not
appear in later list calls.

Pending requests with no lease remain queued until admitted or cancelled. If
the owner is gone, cancel the request with the termination endpoint below so
its queue entries can be removed during reconciliation.

### Terminate or cancel requests

The Resource Manager API calls the administrative revoke/deallocation action
**termination**:

```text
POST /v1/resource-requests/{request_id}/terminate
```

The endpoint accepts `force` and an optional operator-facing `reason`. Use a
user-backed administrator credential with access to the request.

Start with a soft termination when the request allows coordinated or unsafe
reclaim:

```shell
curl --request POST \
  --url "${RESOURCE_MANAGER_URL}/v1/resource-requests/${REQUEST_ID}/terminate" \
  --header "Authorization: Bearer ${RESOURCE_MANAGER_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{
    "force": false,
    "reason": "Draining the node pool for maintenance."
  }'
```

The transition depends on the request's current status and reclaim tolerance:

| Current request | Soft termination (`force: false`) | Force termination (`force: true`) |
| --- | --- | --- |
| `pending` | Changes to `cancelled` | Changes to `cancelled` |
| `allocated`, tolerance `coordinated` or `any` | Changes to `preempting`; the owner must stop and release | Changes to `released` immediately |
| `allocated`, tolerance `none` | Rejected with HTTP 409 because the request opted out of normal preemption | Changes to `preempting`, bypassing the tolerance but still signaling the owner first |
| `preempting` | Remains `preempting` | Changes to `preempted` |
| Terminal | Returned unchanged | Returned unchanged |

When a request becomes `preempting`, its allocations are marked
`preemption_state: requested` and carry the reason. A ZenML-managed or external
owner should observe the signal, stop the workload, and call
`POST /v1/resource-requests/{request_id}/release`; that acknowledgement changes
the request to `preempted`.

Use force termination only after checking the infrastructure impact:

```shell
curl --request POST \
  --url "${RESOURCE_MANAGER_URL}/v1/resource-requests/${REQUEST_ID}/terminate" \
  --header "Authorization: Bearer ${RESOURCE_MANAGER_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{
    "force": true,
    "reason": "Workload owner did not acknowledge the drain deadline."
  }'
```

For `coordinated` and `any` allocations, force termination marks the request
`released` without waiting for owner acknowledgement. For a non-reclaimable
allocation (`reclaim_tolerance: none`), the first force call deliberately moves
it to `preempting`; after the workload is confirmed stopped, either let the
owner call `release` or send a second force call to complete it as
`preempted`.

Terminal status does not itself stop infrastructure. Before forcing completion,
stop or verify the workload through the Kubernetes, VM, or external scheduler
control plane. Otherwise Resource Manager may return the accounted capacity
while the old workload is still consuming it, allowing oversubscription.

Allocation rows are finalized asynchronously by reconciliation after a request
becomes terminal. Poll the pool's active allocations until the request no
longer appears before treating the capacity as available operationally.

### Clean up terminal request records

Deleting a request is optional record cleanup, not a deallocation mechanism.
Only terminal requests with no active allocations can be deleted:

```shell
curl --request DELETE \
  --url "${RESOURCE_MANAGER_URL}/v1/resource-requests/${REQUEST_ID}" \
  --header "Authorization: Bearer ${RESOURCE_MANAGER_TOKEN}"
```

If reconciliation has not yet finalized the allocations, deletion returns HTTP
409. Keep terminal records when they are useful for audit and incident
analysis.

The ZenML CLI can also inspect resource requests:

```shell
zenml resource-request list --status pending
zenml resource-request list --pool-id <pool-id>
zenml resource-request describe <request-id>
```

Descriptor, pool, class, policy, and grant configuration is done through the
Resource Manager API, not the ZenML CLI.

## Checklist

Before handing a pool to users:

* Descriptors use stable names and kinds.
* Descriptor unit catalogs have a multiplier-1 base unit, and all capacity and
  policy values use the intended units.
* Classes bundle aggregate resources the way infrastructure actually provides
  them.
* CPU and memory are included when they matter for scheduling or traceability.
* Unlimited class resources use `quantity: null` intentionally and are
  documented for operators.
* Target bindings match the stack components or service connectors that will
  appear on runtime requests.
* Classes use component target settings that route workloads to the intended
  Kubernetes node pools or equivalent infrastructure.
* Policies use the right subject combinations and time windows for access
  control.
* Preemption groups protect the intended pipeline run, pipeline, project, or
  other related scope without grouping unrelated workloads.
* Reservations across policies do not exceed finite class capacity after unit
  conversion.
* Grant-based policies include every class resource that requests may demand,
  and each missing-demand action is intentional.
* Priority-lane policies are reserved for critical workloads that genuinely
  need maximum priority.
* Accounting mode is `authoritative` unless another scheduler owns allocation.

## See also

* [Core concepts](resource-pools-core-concepts.md) - definitions and selector
  conventions.
* [User guide](resource-pools-user-guide.md) - what pipeline authors configure.
* [External workloads](resource-pools-external-workloads.md) - direct Resource
  Manager requests and priority-lane patterns.
* [Examples](resource-pools-examples.md) - end-to-end scenarios.
* [Reconciliation process](resource-pools-reconciliation.md) - runtime behavior.
