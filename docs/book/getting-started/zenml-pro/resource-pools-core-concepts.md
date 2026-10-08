---
description: >-
  Definitions for ZenML Pro resource descriptors, pools, classes, policies,
  requests, selectors, and leases.
---
# Core concepts

This page defines the building blocks of ZenML Pro resource pools. For
step-by-step setup, see the [Admin guide](resource-pools-admin-guide.md) and
[User guide](resource-pools-user-guide.md).

{% hint style="info" %}
Resource pools apply only to [dynamic pipelines](https://docs.zenml.io/how-to/steps-pipelines/dynamic_pipelines).
Static pipelines do not create resource requests or wait for pool allocation.
{% endhint %}

## Resource descriptors

A resource descriptor is an entry in the resource vocabulary. It describes what
can be requested or accounted for. It does not say how much capacity exists or
who may use it.

| Field | Meaning |
| --- | --- |
| `name` | Stable descriptor identifier used by pool classes, grants, and exact resource demands |
| `kind` | Type label used by kind-based demands. The built-in kinds `cpu`, `memory`, and `gpu` are the convention used by `ResourceSettings`; custom kinds such as `license` are for explicit custom demands. |
| `description` | Optional human-readable explanation |
| `attributes` | Optional key/value metadata used for filtering and documentation |
| `units` | Optional unit catalog, each with `name` and integer `multiplier` |

Stock descriptors are:

| Name | Kind | Units |
| --- | --- | --- |
| `CPU` | `cpu` | `mCPU`, `CPU` |
| `memory` | `memory` | `B`, `KB`, `KiB`, `MB`, `MiB`, `GB`, `GiB`, `TB`, `TiB` |
| `GPU` | `gpu` | `GPU` |

### Built-in kinds and `ResourceSettings`

The descriptor `kind` is how the built-in `ResourceSettings` fields connect to
Resource Manager descriptors. ZenML does not require authors to know descriptor
names for basic compute resources. Instead, it emits demands by built-in kind:

| ResourceSettings field | Built-in demand kind | Typical descriptor names |
| --- | --- | --- |
| `cpu_count` | `cpu` | `CPU`, custom CPU flavors |
| `memory` | `memory` | `memory`, custom memory pools |
| `gpu_count` | `gpu` | `GPU`, `h200`, `a10g`, custom accelerator descriptors |

Use these built-in kinds for every flavor of CPU, memory, or GPU that should
match the corresponding typed `ResourceSettings` field. For example, an H200
descriptor named `h200` should use `kind: "gpu"`; a larger CPU pool descriptor
should use `kind: "cpu"`; and a special memory-backed resource that should
satisfy `ResourceSettings(memory=...)` should use `kind: "memory"`.

Use a custom kind, such as `license`, only when the resource should not be
matched by the basic CPU, memory, or GPU fields. Authors request those
resources explicitly through `ResourceSettings.resources`.

Admins can add descriptors such as `h200`, `a10g`, `training-license`, or
`shared-storage`. The H200 example below uses `kind: "gpu"` so
`ResourceSettings(gpu_count=...)` can match it.

```json
{
  "name": "h200",
  "kind": "gpu",
  "description": "NVIDIA H200 accelerator",
  "attributes": {
    "vendor": "nvidia",
    "model": "H200",
    "vram_gb": 141
  },
  "units": [
    {"name": "GPU", "multiplier": 1}
  ]
}
```

## Pools

A resource pool is a named scheduling and accounting boundary. It has:

| Field | Meaning |
| --- | --- |
| `name` | Pool identifier |
| `description` | Optional explanation |
| `rank` | Preference when more than one pool can admit the same request; higher ranks win first |
| `accounting_mode` | How strongly Resource Manager enforces allocation decisions |
| `concurrency_limit` | Optional maximum number of active requests in the pool |
| `target_bindings` | Subject selectors that describe which runtime targets this pool governs |
| `classes` | Pool-local resource bundles |
| `target_settings` | UI-supported settings merged into selected targets |
| `attributes` | Optional metadata for filtering and pool selectors |

The UI exposes pools under **Organization Settings > Resource Pools** and
**Workspace Settings > Resource Pools**.

### Accounting modes

Most examples use `authoritative`.

| Mode | Meaning |
| --- | --- |
| `authoritative` | Resource Manager controls allocation, queueing, limits, reservations, concurrency caps, and preemption. Use this when the infrastructure scheduler does not already provide the required fairness and conflict handling. |
| `advisory` | Resource Manager computes accounting pressure and ordering hints, but infrastructure may still admit work. Treat this as advanced and experimental. |
| `governance` | Policies decide governance and target routing, but allocation and preemption are left to infrastructure-level schedulers such as Kueue, Run:ai, or similar systems. |

## Pool classes

A pool class is a pool-local resource bundle. This is the most important model
change: classes are not one-resource buckets. They usually represent the shape
of real infrastructure, such as a Kubernetes node pool or cloud machine type.

Example class:

```json
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
            "cloud.google.com/gke-accelerator": "nvidia-h200"
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
    "region": "eu-west-1"
  }
}
```

Class fields:

| Field | Meaning |
| --- | --- |
| `class` | Pool-local class label |
| `resources` | One or more descriptor quantities bundled together |
| `rank` | Preference among matching classes; higher ranks are tried first |
| `reclaimable` | External or Resource Manager reclaim behavior: `never`, `coordinated`, or `unsafe` |
| `concurrency_limit` | Optional maximum number of active requests in this class |
| `target_settings` | UI-supported target settings applied when this class is selected |
| `attributes` | Optional metadata for class selectors |

A class resource with `"quantity": null` is unlimited at the pool-class level.
It is still selected and accounted for, so it remains visible for traceability.
Policy grants can still add reservations and limits for that resource.

## Target bindings and target settings

Target bindings decide which runtime targets a pool governs. In the UI, these
are usually stack components, especially orchestrators and step operators. A
service connector can also appear as a target subject when the pool is tied to
authentication for the infrastructure.

Target settings are merged into the target chosen for a winning allocation. The
UI currently exposes:

| Location | UI-supported target settings |
| --- | --- |
| Pool | Component settings, service connector settings |
| Class | Component settings, service connector settings |
| Policy | Component settings |
| Grant | Component settings |

Settings are merged in order from broader to narrower scope: pool route, class,
policy, then grant. More specific settings can override the same keys from
broader settings.

## Subject selectors

Resource Manager subject selectors are hierarchical filters. They match the
root-first subject chains attached to resource requests. When you write JSON
directly against the Resource Manager API, use the same scope convention the
ZenML client uses.

Selector node:

```json
{
  "subject_type": "organization",
  "subject_id": "<org-id>",
  "attributes": {},
  "metadata": {},
  "contains": {
    "subject_type": "workspace",
    "subject_id": "<workspace-id>"
  }
}
```

Boolean selector expression:

```json
{
  "any": [
    {"subject_type": "team", "subject_id": "<team-id>"},
    {"subject_type": "account", "subject_id": "<user-account-id>"}
  ]
}
```

Use `any` when one selected subject should match. Use `all` when a request must
carry all selected subject chains. Use `not` for exclusion. Policy subject
selectors may also include time selectors through the UI.

### Scope convention

Common request subjects are shaped like this:

| Subject kind | Request subject chain |
| --- | --- |
| Organization | `organization` |
| Workspace | `organization -> workspace` |
| Project | `organization -> workspace -> project` |
| Pipeline | `organization -> workspace -> project -> pipeline` |
| Pipeline run | `organization -> workspace -> project -> pipeline_run` |
| Step run | `organization -> workspace -> project -> pipeline_run -> step_run` |
| Stack component | `organization -> workspace -> component` |
| Service connector | `organization -> workspace -> service_connector` |
| User account | `account` |
| Service account | `organization -> account` |
| Team | `organization -> team` |

The `step_run` entry above is a subject type used to identify requests. It is
not a resource descriptor or resource demand.

Example selector for one step operator target:

```json
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
}
```

Example policy selector for any project in a workspace:

```json
{
  "subject_type": "organization",
  "subject_id": "<org-id>",
  "contains": {
    "subject_type": "workspace",
    "subject_id": "<workspace-id>",
    "contains": {
      "subject_type": "project"
    }
  }
}
```

Example policy selector for a team or a service account:

```json
{
  "any": [
    {
      "subject_type": "organization",
      "subject_id": "<org-id>",
      "contains": {
        "subject_type": "team",
        "subject_id": "<team-id>"
      }
    },
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
}
```

## Policies and grants

A policy attaches access rules to one pool. The policy subject selector answers
"who may use this pool?" Typical policy subjects are workspaces, projects,
pipelines, accounts, teams, and service accounts.

Policy fields:

| Field | Meaning |
| --- | --- |
| `pool` | Pool ID or exact pool name |
| `subject_selector` | Subject selector or boolean selector expression |
| `preemption_group` | Optional selector used to avoid preempting related work |
| `priority` | Higher values win contention; omit when `priority_lane` is true |
| `priority_lane` | Maximum internal priority for critical policies |
| `concurrency_limit` | Optional maximum number of active requests admitted by this policy |
| `grants` | Optional per-class grant list |
| `target_settings` | Policy-level component settings |

A priority-lane policy gets the maximum internal priority. It can preempt
lower-priority reclaimable work, but it still needs a pool, matching class
resources, and capacity according to the pool accounting mode.

### Grant-based policies

A grant references exactly one class in the pool. Inside that class, each grant
resource can reserve capacity, limit active usage, and decide what happens when
a request omits that resource.

```json
{
  "class": "h200-reserved",
  "concurrency_limit": 4,
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
```

Grant resource fields:

| Field | Meaning |
| --- | --- |
| `resource` | Descriptor ID or name in the class bundle |
| `reserved` | Guaranteed share for non-reclaimable work |
| `limit` | Maximum active usage for this policy grant; `null` means follow the class resource quantity |
| `unit` | Unit for `reserved`, `limit`, and `default_value` |
| `missing_action` | `omit`, `default`, or `reject` when a request does not include this resource |
| `default_value` | Quantity to allocate when `missing_action` is `default` |

If a request asks for a resource that is present in the class but missing from
the grant, that grant cannot admit the request. If the grant includes a
resource that the request omits, `missing_action` controls whether the grant
ignores it, rejects the request, or allocates a default.

### Grantless policies

A policy with `"grants": []` admits matching subjects to every matching class
in the pool. Each class resource has reservation 0 and an effective limit equal
to the class resource quantity. Unlimited class resources remain unlimited at
the pool-class level.

Grantless policies are useful for trusted critical workloads, external
workloads that need the full node shape, or simple governance where you do not
need per-team reservations. They still respect pool/class concurrency limits,
pool target bindings, class matching, accounting mode, and reclaimability.

## Resource requests

When a dynamic step is ready to launch, ZenML creates a resource request. The
request contains subjects and demands. External clients may create the same API
shape directly.

Demand fields:

| Field | Meaning |
| --- | --- |
| `resource` | Exact descriptor ID or name |
| `kind` | Match any descriptor with this kind |
| `quantity` | Positive quantity |
| `unit` | Optional unit |
| `class` | Optional exact pool class |
| `resource_selector` | Optional selector over descriptor attributes |
| `class_selector` | Optional selector over class attributes |

`ResourceSettings` produces these common demands:

| Step setting | Demand |
| --- | --- |
| `gpu_count` | `kind: "gpu"`, quantity from `gpu_count`, optional `class` from `gpu_class` |
| `cpu_count` | `kind: "cpu"`, unit `CPU` |
| `memory` | `kind: "memory"`, unit from the memory suffix such as `GiB` |
| `resources` | Custom descriptor demands by name, kind, or selector |

Example runtime request:

```json
{
  "subjects": [
    {
      "subject_type": "organization",
      "subject_id": "<org-id>",
      "child": {
        "subject_type": "workspace",
        "subject_id": "<workspace-id>",
        "child": {
          "subject_type": "component",
          "subject_id": "<step-operator-id>",
          "attributes": {
            "component_type": "step_operator"
          }
        }
      }
    }
  ],
  "demands": [
    {"kind": "gpu", "quantity": 2, "class": "h200-reserved"},
    {"kind": "cpu", "quantity": 8, "unit": "CPU"},
    {"kind": "memory", "quantity": 64, "unit": "GiB"}
  ],
  "reclaim_tolerance": "none",
  "allocation_wait_timeout_seconds": 1800,
  "metadata": {
    "workload": "nightly-training"
  }
}
```

## Reclaim tolerance

Each request carries `reclaim_tolerance`:

| Value | Meaning | Compatible class `reclaimable` |
| --- | --- | --- |
| `none` | Do not interrupt this request for pool reasons | `never`; in authoritative mode it must fit reserved grant share for grant-based policies, or matching class capacity for grantless policies |
| `coordinated` | The workload can be stopped and retried cleanly | `never`, `coordinated` |
| `any` | Best-effort work; may use unsafe classes | `never`, `coordinated`, `unsafe` |

Legacy `preemptible=False` maps to `none`; `preemptible=True` maps to
`coordinated`. Prefer `reclaim_tolerance` for new code.

## Request statuses

| Status | Meaning |
| --- | --- |
| `pending` | Admitted and queued, waiting for allocation |
| `allocated` | Capacity granted and leased |
| `preempting` | Reconciler asked the owner to stop so capacity can be reclaimed |
| `preempted` | Request was stopped by preemption |
| `rejected` | No policy/class/grant path can satisfy the request |
| `cancelled` | Request was cancelled before allocation |
| `released` | Work finished and capacity was returned |
| `expired` | Lease expired while allocated |

Inspect resource requests in the UI or with `zenml resource-request list` and
`zenml resource-request describe <request-id>`.
