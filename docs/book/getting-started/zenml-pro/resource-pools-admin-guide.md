---
description: >-
  How platform admins build the resource vocabulary, define pools and policies,
  and configure stack-component settings in ZenML Pro.
---
# Admin guide

This guide is for platform admins who operate ZenML Pro: you define the
resource language, declare pool capacity, attach policies, and wire stack
components to infrastructure.

Most admin tasks are done in the ZenML Pro UI. The CLI supports a simplified
flat pool and component-policy workflow for quick starts and automation. This
page shows both.

## Before you start

You need:

* A workspace with resource pools enabled (see
  [Enable Resource Pools](deploy-workspace-resource-pools.md)).
* Stack components (orchestrators and step operators) that will run pooled
  workloads.
* A clear picture of which resources are scarce (GPUs, licenses, concurrent
  step slots) and how you want to split capacity (reserved vs burst vs spot).

## Step 1: Build the resource vocabulary

Resource descriptors are the foundation. Every pool capacity entry, policy
grant, and custom step request refers to a descriptor by name or kind.

### Use default descriptors

Stock descriptors ship with every organization:

| Name | Kind | Units |
| --- | --- | --- |
| `CPU` | `cpu` | `mCPU`, `CPU` |
| `memory` | `memory` | `B`, `KiB`, `MiB`, `GiB`, … |
| `GPU` | `gpu` | `GPU` |
| `step run` | `step_run` | `step run` |

These four kinds are the unified default language for pipeline authors.
`ResourceSettings` typed fields (`cpu_count`, `memory`, `gpu_count`) always
produce demands with kinds `cpu`, `memory`, and `gpu`. ZenML adds a `step_run`
demand for isolated dynamic steps as a platform convention.

Authors can use those fields without knowing descriptor names. Pool capacity
and policy grants refer to descriptors by **name** (`GPU`, `CPU`, …). Match
the catalog spelling (`GPU`, not `gpu`, unless you defined a custom descriptor
with that exact name).

When you add custom CPU, memory, or GPU-like resources, set the descriptor
**kind** to `cpu`, `memory`, or `gpu` so they stay compatible with typed
`ResourceSettings`. A custom H200 descriptor with `kind: "gpu"` is satisfied
when an author sets `gpu_count=1`; pool capacity uses the descriptor name
(`h200`).

### Add custom descriptors

When you need hardware-specific or license resources, define a descriptor in
the UI. For GPU-like hardware, always use `kind: "gpu"` so authors can keep
using `gpu_count` and `gpu_class`. Use `cpu` or `memory` for custom variants
of those resources. Reserve other kinds (for example `license`) for resources
that truly cannot map to the default set — those require
`ResourceSettings.resources` by name; typed fields will not match them.

Example — H200 as a `gpu`-kind descriptor (recommended; works with `gpu_count`):

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

Example — a license with a non-default kind (authors must use
`ResourceSettings.resources`, not typed GPU/CPU fields):

```json
{
  "name": "training-license",
  "kind": "license",
  "description": "Floating training license seat",
  "units": [
    {"name": "seat", "multiplier": 1}
  ]
}
```

Configure resource descriptors in the ZenML Pro UI under resource management.
See [User guide](resource-pools-user-guide.md) for how authors request custom
resources by name.

### Descriptor units

The `units` field on a descriptor is optional. Define it when the same resource
can be counted in more than one way. Each entry has a `name` and a `multiplier`
relative to the descriptor's base unit.

| Descriptor | Example units | Why multiples help |
| --- | --- | --- |
| `CPU` | `mCPU` (×1), `CPU` (×1000) | Fine-grained milli-CPU accounting or whole cores |
| `memory` | `B`, `KiB`, `MiB`, `GiB`, … | Pool capacity and step requests can use the suffix the author chose |
| `GPU`, `step run` | single unit each | One countable thing per slot |

When a demand, pool capacity row, or policy grant includes a `unit`, ZenML
converts quantities using the descriptor's unit catalog. Typed `ResourceSettings`
fields pick sensible defaults (`cpu_count` → unit `CPU`, `memory="16GiB"` → unit
`GiB`). Custom descriptors with one unit (for example `{"name": "GPU", "multiplier": 1}`)
can omit the catalog unless you expect multiple counting schemes.

## Step 2: Define resource pools

A pool declares how much capacity exists, split into classes.

### CLI quick start (single default class)

For a simple shared GPU bucket, the CLI accepts a flat map. Each key becomes one
capacity class named `default` with `rank: 0` and `reclaimable: never`.

```shell
zenml resource-pool create org-gpu-pool \
  --capacity '{"GPU": 16}' \
  --description "Organization GPU pool"
```

Attach a component policy:

```shell
zenml resource-pool attach-policy org-gpu-pool prod-k8s-orch \
  --component-type orchestrator \
  --priority 100 \
  --reserved '{"GPU": 8}' \
  --limit '{"GPU": 16}'
```

This is enough for teams that only need one capacity bucket per resource. For
reserved vs adhoc split, per-node pools, or reclaim risk, use the UI (below).

{% hint style="warning" %}
A GPU-only CLI capacity map is not enough for real pipeline steps. Also add
`CPU`, `memory`, and `step run` to the pool (UI or SDK) and mirror them in
policy grants. Otherwise steps that set `cpu_count`, `memory`, or implicit
`step_run` demands are rejected even when GPUs are free.
{% endhint %}

### Full pool model (UI)

Configure pools with multiple capacity classes in the ZenML Pro UI. The example
below suits a team with dedicated H200 nodes plus shared burst capacity:
production training stays on reserved capacity while experiments use adhoc
capacity when it is available.

```json
{
  "name": "org-gpu-pool",
  "description": "Shared H200 capacity across training clusters",
  "capacity": [
    {
      "resource": "h200",
      "class": "reserved",
      "quantity": 16,
      "rank": 100,
      "reclaimable": "never",
      "attributes": {
        "tier": "tier-a-gpu",
        "cost_profile": "already_paid"
      }
    },
    {
      "resource": "h200",
      "class": "adhoc",
      "quantity": 8,
      "rank": 50,
      "reclaimable": "never",
      "attributes": {
        "tier": "tier-a-gpu",
        "cost_profile": "shared_burst"
      }
    },
    {
      "resource": "h200",
      "class": "spot",
      "quantity": 4,
      "rank": 10,
      "reclaimable": "unsafe",
      "attributes": {
        "tier": "tier-a-gpu",
        "cost_profile": "spot"
      }
    }
  ]
}
```

How to read this as an admin:

- `rank` — which class the reconciler prefers when a request does not pin a
  class (higher first). Put contract capacity (`reserved`) above burst (`adhoc`)
  and spot.
- `reclaimable` — how interruptible this bucket is from outside ZenML or from
  coordinated preemption. Do not encode dollar cost here; use `attributes` for
  display and matching only.
- `attributes` — labels authors or selectors can target (for example
  `tier: tier-a-gpu`).

### One pool per Kubernetes node

When external inference runs on specific nodes and must reclaim capacity that
pipeline jobs borrowed overnight, model each node (or node pool) as its own
pool with selector-visible attributes:

```json
{
  "name": "prod-eu-node-a",
  "attributes": {
    "kubernetes_cluster": "prod-eu",
    "kubernetes_node": "node-a",
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

Repeat for `node-b`, `node-c`, and so on. External workload integrations target
pools through these attributes (see
[External workloads](resource-pools-external-workloads.md)).

## Step 3: Component settings on capacity classes

When an allocation wins a specific class, ZenML merges component settings from
that class onto the selected stack component. Use this for placement — for
example Kubernetes node selectors and tolerations — not for CPU, memory, or GPU
resource requests. The orchestrator or step operator adds those from the
author's `ResourceSettings` on top of the merged `pod_settings`.

Configure `component_settings` on capacity classes in the UI. Example for a
Kubernetes step operator on the `h200` / `reserved` class:

```json
{
  "resource": "h200",
  "class": "reserved",
  "component_settings": [
    {
      "component_type": "step_operator",
      "flavor": "kubernetes",
      "settings": {
        "pod_settings": {
          "node_selectors": {
            "accelerator": "h200",
            "capacity": "reserved"
          },
          "tolerations": [
            {
              "key": "accelerator",
              "operator": "Equal",
              "value": "h200",
              "effect": "NoSchedule"
            }
          ]
        }
      }
    }
  ]
}
```

Settings from the allocation override conflicting user step settings for the
fields they set. Authors cannot weaken placement requirements enforced by the
admin configuration.

## Step 4: Define policies

Policies connect a subject — a stack component or a user/service account — to a
pool. Most policies use **grants**: one line per descriptor that caps how much
capacity the subject may hold (`reserved`, `limit`) and which capacity classes
apply.

A **grantless** policy sets `grants: []` (no grant rows). The subject may
consume any free capacity in the pool that matches the request's demands. There
are no per-resource `reserved` or `limit` slices on the policy itself;
contention is governed by pool capacity, policy priority, and the reconciler
queue. Grantless admission still requires every demand to match a resource
declared in the pool — it does not invent capacity the pool does not expose.

Grantless policies are typical for per-node pools and external workloads where
the integrator owns the whole machine. Pipeline step operators usually use
explicit grants so teams get reserved slices and hard ceilings. See
[Core concepts — Policies](resource-pools-core-concepts.md#policies-and-subjects).
For maximum-priority admission and preemption, see
[Priority lane policies](#priority-lane-policies) below.

### Grants (grant-based policies)

{% hint style="warning" %}
These rules apply when the policy has one or more grant lines. Grantless
policies skip per-resource grants; see above.

Every grant line covers one descriptor by name. If a step requests a resource
your grants do not include (including `CPU`, `memory`, or `step run`), the
request is rejected — even when the pool has spare capacity.

Requests with `reclaim_tolerance: none` must fit each grant's `reserved`
amount. Zero reserved or a missing grant for a demanded resource causes
immediate rejection.
{% endhint %}

### Component policies (pipeline workloads)

For orchestrators and step operators, attach a policy in the UI or use the CLI
for the simple `default`-class case (see CLI quick start above).

Full policy shape (UI) — production training team on reserved and adhoc H200:

```json
{
  "pool": "org-gpu-pool",
  "component_id": "<prod-k8s-step-operator-uuid>",
  "priority": 100,
  "grants": [
    {
      "resource": "h200",
      "classes": ["reserved"],
      "reserved": 8,
      "limit": 8
    },
    {
      "resource": "h200",
      "classes": ["adhoc"],
      "reserved": 0,
      "limit": 8
    }
  ]
}
```

Experimental team at lower priority, adhoc only:

```json
{
  "pool": "org-gpu-pool",
  "component_id": "<sandbox-k8s-step-operator-uuid>",
  "priority": 10,
  "grants": [
    {
      "resource": "h200",
      "classes": ["adhoc"],
      "reserved": 0,
      "limit": 8
    }
  ]
}
```

This pattern keeps production training on a high-priority policy with reserved
grants, while the sandbox team uses adhoc capacity at lower priority with
coordinated reclaim tolerance on steps—so experiments do not displace
production runs.

### Account policies (users and service accounts)

Account policies bind a workspace user or service account to a pool. Use them
when workloads create direct resource requests through the workspace API rather
than through a stack component — for example an inference autoscaler or another
platform's jobs on shared GPU nodes. Configure in the UI (the CLI does not
support account policies today).

Set `account_id` instead of `component_id`. Otherwise the same grant rules
apply: grant lines cap capacity per descriptor, or use `grants: []` for
grantless admission (see Step 4 introduction). Set `priority` for normal
contention ordering unless the subject needs the priority lane (see below).

Example — service account with a capped adhoc GPU slice at medium priority:

```json
{
  "pool": "prod-eu-node-b",
  "account_id": "<batch-job-service-account-uuid>",
  "priority": 50,
  "grants": [
    {
      "resource": "h200",
      "classes": ["adhoc"],
      "reserved": 0,
      "limit": 4
    }
  ]
}
```

See [External workloads](resource-pools-external-workloads.md) for the
integrator API flow (create, renew, terminate).

### Priority lane policies

The priority lane is an internal maximum priority tier for policies that must
outrank normal pipeline contention — for example external inference reclaiming
GPUs from overnight eval jobs, or another critical integration that cannot wait
behind lower-priority ZenML runs.

Set `priority_lane: true` on the policy. Do not set `priority`; the platform
assigns the lane automatically. Priority-lane policies are usually grantless
(`grants: []`) on a node-scoped pool so the subject can use all capacity the
pool declares, but grant-based priority-lane policies are valid when you still
need per-resource ceilings.

Example — external workload bridge on a single node:

```json
{
  "pool": "prod-eu-node-b",
  "account_id": "<external-workload-bridge-service-account-uuid>",
  "priority_lane": true,
  "grants": []
}
```

At reconciliation time:

| Interaction | Behavior |
| --- | --- |
| Priority lane vs normal priority | Lane requests outrank normal policies and may preempt reclaimable allocations |
| Normal vs priority lane | Normal requests cannot preempt priority-lane allocations |
| Priority lane vs priority lane | Equal priority; neither preempts the other in the current release |

Grantless priority-lane admission still requires every demand to match a resource
declared in the pool. An external client that only requests GPUs needs a pool
that declares GPU capacity; it does not bypass pool coverage.

Priority-lane and grantless policies are UI- or SDK-only today. See
[Reconciliation — Priority-lane interactions](resource-pools-reconciliation.md#priority-lane-interactions)
for runtime behavior and
[External workloads](resource-pools-external-workloads.md) for a full setup
walkthrough.

### Multiple policies on the same pool

One pool often carries several policies — for example a step-operator policy
for pipeline workloads and a service-account policy for external reclaim on
the same node. That is expected. What matters is what happens when one request
matches more than one of them.

Each resource request carries one or more subjects:

| Request source | Subjects on the request |
| --- | --- |
| Pipeline step | Run owner (user or service account) and the stack component that launches the step (orchestrator or step operator) |
| Direct API call | Authenticated user or service account only |

A policy matches when its subject (`component_id` or `account_id`) appears on
the request. If both a component policy and an account policy on the same pool
match, the reconciler does not merge or combine them. It picks one policy path
for that pool:

1. Build allocation plans only for policy paths that can satisfy every demand
   in the request (all-or-nothing per pool).
2. Enqueue at most one queue entry per pool, bound to the eligible plan with
   the highest `priority`. Priority-lane policies outrank numeric priorities.
3. At equal priority, tie-break deterministically on capacity class rank, then
   subject id, then policy id.

The winning policy's grants (or grantless admission rules) govern allocation,
preemption, and limits for that request on that pool. Lower-priority matching
policies on the same pool are ignored for that request even though they remain
configured.

Example — production step operator at priority 100 with reserved H200 grants,
same user's service account at priority 50 with a smaller adhoc slice on the
same pool: pipeline steps queue through the component policy. Direct API calls
from that service account use the account policy only (no component subject).

Example — intentional override: attach a priority-lane grantless account policy
on a node pool so external reclaim beats pipeline contention; pipeline steps
still match the component policy, but the account path wins only when the
request includes that account subject and the lane policy builds a complete
plan.

Avoid overlapping policies with incompatible grants on the same pool unless
the priority ordering matches your intent. A higher-priority policy that cannot
build a complete plan is skipped; the next eligible plan is used instead.

### Multiple policies per component (different pools)

{% hint style="warning" %}
One step operator can have policies on several pools (for example primary and
fallback regions). The same logical request may queue in each eligible pool,
but at most one pool owns the active allocation. ZenML never splits one step
across pools.

Because any attached pool might win, every pool and policy must declare and
grant every resource your users might request on that stack — including
`CPU`, `memory`, `step run`, and any custom descriptors.
{% endhint %}

One step operator can have policies on several pools (for example primary and
fallback regions). Higher policy priority is preferred when more than one pool
could satisfy the same request. Every demand must be satisfiable from the
winning pool alone.

## Step 5: Inspect pool state

Use the UI to view occupied capacity, queue length, and active requests.

CLI inspection:

```shell
zenml resource-pool list
zenml resource-pool describe org-gpu-pool
zenml resource-pool list-policies org-gpu-pool
zenml resource-pool requests org-gpu-pool --view all
zenml resource-request list --status pending
```

## CLI and SDK limits

| Feature | CLI | UI |
| --- | --- | --- |
| Flat pool capacity (`default` class) | Yes | Yes |
| Multiple capacity classes, rank, reclaimable | No | Yes |
| Pool attributes (for pool selectors) | No | Yes |
| Component settings on classes | No | Yes |
| Resource descriptors | No | Yes |
| Component attach-policy (default class) | Yes | Yes |
| Full grants with multiple classes | No | Yes |
| Account / service-account policies | No | Yes |
| Priority-lane policies | No | Yes |
| Grantless policies | No | Yes |

The Python SDK (`Client().create_resource_pool`, `create_resource_policy`,
`create_resource_descriptor`) supports the full model programmatically for
automation; descriptors and advanced pool fields are not exposed on the CLI.

## See also

* [Core concepts](resource-pools-core-concepts.md) — definitions
* [User guide](resource-pools-user-guide.md) — what authors set on steps
* [External workloads](resource-pools-external-workloads.md) — service accounts and priority lanes
* [Examples](resource-pools-examples.md) — end-to-end scenarios
* [Reconciliation process](resource-pools-reconciliation.md) — what happens at runtime
