---
description: >-
  End-to-end resource pool use cases for CPU queues, GPU node pools, cloud
  machine types, licenses, external workloads, governance schedulers, and
  policy patterns.
---
# Examples

The examples below show practical resource pool configurations for common
ZenML Pro workload management scenarios. Each example explains the
infrastructure being modeled, the access policies that apply to it, and the
Resource Manager API JSON that corresponds to the UI configuration.

Configure these objects in the ZenML Pro UI under **Organization Settings >
Resource Pools** or **Workspace Settings > Resource Pools**. The JSON snippets
use the Resource Manager REST API shape for teams that automate the same setup.

## How to read these examples

Resource pool examples have two layers:

1. **Inventory modeling**: descriptors and pool classes describe what
   infrastructure exists. A class should usually represent a real bundle such
   as a CPU worker group, a Kubernetes node pool, a SageMaker machine type, or a
   licensed training slot.
2. **Access modeling**: policies and grants describe who may consume that
   inventory, at which priority, with which reservations, limits, defaults, and
   concurrency caps.

That separation matters. If two teams use the same H200 Kubernetes node pool,
do not duplicate the pool just to express two different access rules. Model the
node pool once, then attach separate policies for production, research,
external services, or emergency operators.

The examples progress from small to more advanced:

| Example | Focus |
| --- | --- |
| [Simple CPU and memory queue](#example-1-simple-cpu-and-memory-queue) | First pool, first class, basic concurrency, basic team policy |
| [One GPU machine shape](#example-2-one-gpu-machine-shape) | Exact hardware descriptor, class bundle, production reservation, experiment burst |
| [Kubernetes cluster with two node pools](#example-3-kubernetes-cluster-with-two-node-pools) | Multiple classes, target settings, reserved and burst node pools |
| [Kubernetes cluster with per-node classes](#example-4-kubernetes-cluster-with-per-node-classes) | Modeling each node as a class for node-level placement |
| [Multiple Kubernetes clusters as classes](#example-5-multiple-kubernetes-clusters-as-classes) | Class-level service connector settings and cluster burst |
| [Multi-region GPU dispatch](#example-6-multi-region-gpu-dispatch) | Multiple pools for different regions and step operators |
| [Shared organization pool across workspaces](#example-7-shared-organization-pool-across-workspaces) | Organization-scope policies, workspace/project/team access |
| [Cloud machine types](#example-8-cloud-machine-types) | Modeling machine families such as SageMaker or Vertex AI worker types |
| [Training license with traceability](#example-9-training-license-with-traceability) | Custom descriptor, finite license seats, unlimited CPU/memory tracking |
| [External inference priority lane](#example-10-external-inference-priority-lane) | Service account subject, grantless priority-lane policy, direct request |
| [Governance with Kueue or Run:ai](#example-11-governance-with-kueue-or-runai) | Letting infrastructure own allocation while ZenML owns policy routing |
| [Policy cookbook](#example-12-policy-cookbook) | Common access patterns on top of existing inventory |

## Example 1: Simple CPU and Memory Queue

Start with a CPU-only workspace. One workspace uses a remote execution backend,
and pipeline authors can launch more CPU-heavy dynamic steps than the workers
should run at the same time. The resource pool defines a queue, a maximum
number of active jobs, and a baseline access policy for the workspace.

The inventory model is intentionally small:

* Use the stock `CPU` and `memory` descriptors.
* Create one pool for the remote worker backend.
* Create one class named `standard-workers`.
* Bundle CPU and memory in that class because they are consumed together by the
  same worker group.
* Add a pool concurrency limit so excess jobs queue instead of overloading the
  worker backend.

CPU and memory examples are useful even when those resources are less scarce
than GPUs. Resource pools can provide admission control and traceability for
general compute workloads as well as accelerator workloads.

### Inventory

```json
{
  "name": "workspace-standard-compute",
  "description": "Standard CPU and memory workers for dynamic steps",
  "rank": 10,
  "accounting_mode": "authoritative",
  "concurrency_limit": 12,
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
            "subject_id": "<orchestrator-id>",
            "attributes": {
              "component_type": "orchestrator"
            }
          }
        }
      }
    }
  ],
  "classes": [
    {
      "class": "standard-workers",
      "rank": 100,
      "reclaimable": "never",
      "concurrency_limit": 12,
      "resources": [
        {"resource": "CPU", "quantity": 96, "unit": "CPU"},
        {"resource": "memory", "quantity": 384, "unit": "GiB"}
      ],
      "attributes": {
        "worker_group": "standard",
        "environment": "dev"
      }
    }
  ]
}
```

The class does not describe one worker. It describes the total schedulable
envelope of the worker group. Resource Manager accounts against the class total
while the orchestrator still launches the actual tasks.

### Access pattern: Workspace baseline

```json
{
  "pool": "workspace-standard-compute",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "workspace",
      "subject_id": "<workspace-id>"
    }
  },
  "priority": 10,
  "priority_lane": false,
  "concurrency_limit": 10,
  "grants": [
    {
      "class": "standard-workers",
      "resources": [
        {
          "resource": "CPU",
          "reserved": 16,
          "limit": 80,
          "unit": "CPU",
          "missing_action": "reject"
        },
        {
          "resource": "memory",
          "reserved": 64,
          "limit": 320,
          "unit": "GiB",
          "missing_action": "reject"
        }
      ]
    }
  ]
}
```

The policy gives the workspace a small protected CPU/memory share and a larger
ceiling. If the workspace launches a burst of dynamic steps, up to ten requests
can be active under the policy. The rest queue even if raw CPU accounting would
still fit, because the policy concurrency limit is a separate active-request
guardrail.

### Runtime behavior: baseline queue

```python
ResourceSettings(
    cpu_count=4,
    memory="16GiB",
    reclaim_tolerance="none",
)
```

The typed settings produce `cpu` and `memory` demands. Those match the stock
`CPU` and `memory` descriptors by kind. Because the request is non-reclaimable,
it must fit inside the grant's reserved share in authoritative mode.

If the workspace has four active steps that each request 4 CPUs and 16 GiB
memory, the next identical step still fits the reserved share. If twenty such
steps arrive at once, Resource Manager admits up to the policy concurrency
limit and queues the rest. The queue is useful here even when raw CPU and memory
would technically fit, because the concurrency limit protects the worker
backend from too many active processes.

### Access pattern: Interactive work outranks nightly batch

The same CPU inventory can support two different behaviors: interactive work
gets a small but responsive lane, while nightly batch gets a wide but low
priority lane.

```json
{
  "pool": "workspace-standard-compute",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "workspace",
      "subject_id": "<workspace-id>",
      "contains": {
        "subject_type": "project",
        "subject_id": "<interactive-project-id>"
      }
    }
  },
  "priority": 50,
  "priority_lane": false,
  "concurrency_limit": 4,
  "grants": [
    {
      "class": "standard-workers",
      "resources": [
        {"resource": "CPU", "reserved": 16, "limit": 32, "unit": "CPU", "missing_action": "reject"},
        {"resource": "memory", "reserved": 64, "limit": 128, "unit": "GiB", "missing_action": "reject"}
      ]
    }
  ]
}
```

```json
{
  "pool": "workspace-standard-compute",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "workspace",
      "subject_id": "<workspace-id>",
      "contains": {
        "subject_type": "project",
        "subject_id": "<nightly-batch-project-id>"
      }
    }
  },
  "priority": 5,
  "priority_lane": false,
  "concurrency_limit": 20,
  "grants": [
    {
      "class": "standard-workers",
      "resources": [
        {"resource": "CPU", "reserved": 0, "limit": 80, "unit": "CPU", "missing_action": "reject"},
        {"resource": "memory", "reserved": 0, "limit": 320, "unit": "GiB", "missing_action": "reject"}
      ]
    }
  ]
}
```

When both projects submit at the same time, interactive requests are considered
first because their policy priority is higher. Nightly work can fill idle CPU
and memory, but it has no reservation. If an interactive request arrives while
nightly work holds reclaimable capacity, Resource Manager may preempt the
nightly request. If the nightly request used `reclaim_tolerance="none"`, it
would not have been admitted through this zero-reservation policy in the first
place.

### Access pattern: Keep one account from flooding the queue

Use an account-level policy when one user or automation account can create many
runs. This keeps a burst of runs from one account in a bounded queue.

```json
{
  "pool": "workspace-standard-compute",
  "subject_selector": {
    "subject_type": "account",
    "subject_id": "<user-account-id>",
    "attributes": {
      "is_service_account": false
    }
  },
  "priority": 15,
  "priority_lane": false,
  "concurrency_limit": 2,
  "grants": [
    {
      "class": "standard-workers",
      "resources": [
        {"resource": "CPU", "reserved": 0, "limit": 16, "unit": "CPU", "missing_action": "reject"},
        {"resource": "memory", "reserved": 0, "limit": 64, "unit": "GiB", "missing_action": "reject"}
      ]
    }
  ]
}
```

If the account launches ten pipeline runs and each run has several dynamic
steps, the account policy caps active requests at two. Other users in the
workspace can still be admitted through broader workspace or project policies
if they have matching grants.

## Example 2: One GPU Machine Shape

Now add an accelerator while keeping the infrastructure simple. Assume one GPU
worker group made of four identical H200 machines. Each machine provides two
H200 GPUs plus CPU and memory. Pipeline authors request H200 capacity, and
ZenML selects the matching pool class.

The strategy is:

* Add a custom descriptor named `h200` with built-in kind `gpu`.
* Create one class that bundles H200 GPUs, CPU, and memory together.
* Add a production policy with reserved capacity.
* Add a lower-priority experiment policy that can use leftover capacity.

This example shows why descriptor `kind` is important. A pipeline author can
use `gpu_count=1`, and Resource Manager can match `h200` because the descriptor
uses `kind: "gpu"`.

### Descriptor

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

### Inventory

```json
{
  "name": "team-h200-machines",
  "description": "Four H200 training machines owned by the ML platform team",
  "rank": 50,
  "accounting_mode": "authoritative",
  "concurrency_limit": 8,
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
            "subject_id": "<gpu-step-operator-id>",
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
      "class": "h200-standard",
      "rank": 100,
      "reclaimable": "never",
      "concurrency_limit": 8,
      "resources": [
        {"resource": "h200", "quantity": 8, "unit": "GPU"},
        {"resource": "CPU", "quantity": 192, "unit": "CPU"},
        {"resource": "memory", "quantity": 1536, "unit": "GiB"}
      ],
      "attributes": {
        "accelerator": "h200",
        "machine_count": "4",
        "owner": "ml-platform"
      }
    }
  ]
}
```

The class total is the aggregate capacity of the machine group. The class is
not a single resource row; it is the shape Resource Manager can allocate as one
candidate. A request for 2 H200 GPUs, 16 CPUs, and 128 GiB memory must fit in
this one class.

### Access pattern: Production reservation

```json
{
  "pool": "team-h200-machines",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "team",
      "subject_id": "<production-team-id>"
    }
  },
  "priority": 100,
  "priority_lane": false,
  "concurrency_limit": 4,
  "grants": [
    {
      "class": "h200-standard",
      "resources": [
        {"resource": "h200", "reserved": 4, "limit": 8, "unit": "GPU", "missing_action": "reject"},
        {"resource": "CPU", "reserved": 64, "limit": 192, "unit": "CPU", "missing_action": "default", "default_value": 8},
        {"resource": "memory", "reserved": 512, "limit": 1536, "unit": "GiB", "missing_action": "default", "default_value": 64}
      ]
    }
  ]
}
```

The production team gets half the GPUs as protected reserved share and can
burst to the whole class when it is free. CPU and memory have defaults so a
GPU-only request from an author still accounts for a reasonable CPU/memory
footprint.

### Access pattern: Experiment burst

```json
{
  "pool": "team-h200-machines",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "workspace",
      "subject_id": "<workspace-id>",
      "contains": {
        "subject_type": "project",
        "subject_id": "<experiments-project-id>"
      }
    }
  },
  "priority": 20,
  "priority_lane": false,
  "concurrency_limit": 6,
  "grants": [
    {
      "class": "h200-standard",
      "resources": [
        {"resource": "h200", "reserved": 0, "limit": 4, "unit": "GPU", "missing_action": "reject"},
        {"resource": "CPU", "reserved": 0, "limit": 96, "unit": "CPU", "missing_action": "default", "default_value": 4},
        {"resource": "memory", "reserved": 0, "limit": 768, "unit": "GiB", "missing_action": "default", "default_value": 32}
      ]
    }
  ]
}
```

The experiment project has no reservation. It can consume idle capacity, but a
non-reclaimable request from that project is rejected because there is no
reserved share. Authors should use `reclaim_tolerance="coordinated"` or
`"any"` for this policy.

### Runtime behavior: reservation, limit, and reclaim

For example, production has two active requests using 2 H200 GPUs each. The
production reservation is now full, but the production limit is still 8 H200s.
A third production request for 2 H200 GPUs can still run if idle class capacity
exists, because the limit allows burst above the reservation.

In another case, experiments already use 4 H200 GPUs through the lower-priority
policy and a production request for 4 H200 GPUs arrives with
`reclaim_tolerance="none"`. Resource Manager first checks whether the request
fits the production reserved share. If it does not, the request queues or is
rejected according to the admission route; it will not depend on interrupting
experiments. If the production request allows coordinated reclaim and has
higher priority, Resource Manager may select lower-priority experiment
allocations as victims.

### Access pattern: Avoid self-preemption inside one project

Preemption groups are useful when different policies match related work. The
selector below tells Resource Manager that requests from the same experiments
project should not preempt one another just because one matched a higher
priority policy.

```json
{
  "pool": "team-h200-machines",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "workspace",
      "subject_id": "<workspace-id>",
      "contains": {
        "subject_type": "project",
        "subject_id": "<experiments-project-id>"
      }
    }
  },
  "preemption_group": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "workspace",
      "subject_id": "<workspace-id>",
      "contains": {
        "subject_type": "project",
        "subject_id": "<experiments-project-id>"
      }
    }
  },
  "priority": 60,
  "priority_lane": false,
  "concurrency_limit": 4,
  "grants": [
    {
      "class": "h200-standard",
      "resources": [
        {"resource": "h200", "reserved": 0, "limit": 4, "unit": "GPU", "missing_action": "reject"},
        {"resource": "CPU", "reserved": 0, "limit": 96, "unit": "CPU", "missing_action": "default", "default_value": 8},
        {"resource": "memory", "reserved": 0, "limit": 768, "unit": "GiB", "missing_action": "default", "default_value": 64}
      ]
    }
  ]
}
```

If two pipeline runs from the same project are already allocated and a third
run from the same project arrives through this higher-priority policy, the
preemption group prevents Resource Manager from selecting the first two runs as
victims. The group does not protect unrelated projects. This keeps preemption
available for unrelated lower-priority work while preventing related runs from
interrupting each other.

## Example 3: Kubernetes Cluster With Two Node Pools

This example models a Kubernetes cluster with two real node pools:

* `h200-reserved`: expensive reserved H200 nodes for production training.
* `a10-burst`: cheaper shared A10 nodes for experiments and sweeps.

One ZenML resource pool models both Kubernetes node pools as separate classes.
The pool is the shared accounting boundary. The classes are the infrastructure
shapes inside that boundary.

The strategy is:

* Use class rank to prefer the reserved H200 class when a request can run
  there.
* Use `reclaimable: "never"` for reserved nodes and `"coordinated"` for burst
  nodes.
* Use class target settings to inject node selectors and tolerations.
* Attach different policies for production and research.

### Inventory

```json
{
  "name": "k8s-prod-eu-gpu",
  "description": "Production Kubernetes GPU node pools in prod-eu",
  "rank": 100,
  "accounting_mode": "authoritative",
  "concurrency_limit": 48,
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
                "subject_id": "<kubernetes-step-operator-id>",
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
                "subject_id": "<gke-connector-id>",
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
        "tier": "tier-a-gpu",
        "purchase": "reserved"
      }
    },
    {
      "class": "a10-burst",
      "rank": 30,
      "reclaimable": "coordinated",
      "concurrency_limit": 24,
      "resources": [
        {"resource": "GPU", "quantity": 24, "unit": "GPU"},
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
              },
              "labels": {
                "workload-tier": "best-effort"
              }
            }
          }
        }
      ],
      "attributes": {
        "accelerator": "a10",
        "tier": "tier-b-gpu",
        "purchase": "shared-burst"
      }
    }
  ],
  "target_settings": [
    {
      "target_type": "service_connector",
      "settings": {
        "connector_id": "<gke-connector-id>",
        "resource_type": "kubernetes-cluster",
        "resource_id": "prod-eu"
      }
    }
  ],
  "attributes": {
    "cluster": "prod-eu",
    "region": "eu-west-1",
    "platform": "kubernetes"
  }
}
```

The `h200-reserved` class has finite CPU and memory because production capacity
is fully accounted. The `a10-burst` class tracks CPU and memory as unlimited:
GPU quantity and concurrency are enforced, while CPU and memory remain visible
on requests for traceability.

### Access pattern: Production reservation

```json
{
  "pool": "k8s-prod-eu-gpu",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "team",
      "subject_id": "<production-ml-team-id>"
    }
  },
  "priority": 100,
  "priority_lane": false,
  "concurrency_limit": 8,
  "grants": [
    {
      "class": "h200-reserved",
      "concurrency_limit": 6,
      "resources": [
        {"resource": "h200", "reserved": 4, "limit": 8, "unit": "GPU", "missing_action": "reject"},
        {"resource": "CPU", "reserved": 32, "limit": 128, "unit": "CPU", "missing_action": "default", "default_value": 4},
        {"resource": "memory", "reserved": 256, "limit": 1024, "unit": "GiB", "missing_action": "default", "default_value": 16}
      ],
      "target_settings": [
        {
          "target_type": "component",
          "settings": {
            "pod_settings": {
              "labels": {
                "zenml.io/resource-policy": "production"
              }
            }
          }
        }
      ]
    }
  ]
}
```

Production work gets high priority and reserved H200 share. Authors should use
`reclaim_tolerance="none"` for critical steps. Those requests wait for reserved
capacity instead of borrowing interruptible capacity.

### Access pattern: Research burst tier

```json
{
  "pool": "k8s-prod-eu-gpu",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "workspace",
      "subject_id": "<workspace-id>",
      "contains": {
        "subject_type": "project",
        "subject_id": "<research-project-id>"
      }
    }
  },
  "priority": 30,
  "priority_lane": false,
  "concurrency_limit": 16,
  "grants": [
    {
      "class": "a10-burst",
      "concurrency_limit": 12,
      "resources": [
        {"resource": "GPU", "reserved": 0, "limit": 16, "unit": "GPU", "missing_action": "reject"},
        {"resource": "CPU", "reserved": 0, "limit": null, "unit": "CPU", "missing_action": "default", "default_value": 4},
        {"resource": "memory", "reserved": 0, "limit": null, "unit": "GiB", "missing_action": "default", "default_value": 24}
      ]
    }
  ]
}
```

The research policy deliberately grants only `a10-burst`. Even if H200 capacity
is idle, this project will not consume it through this policy. This expresses
the rule that experiments may use the burst tier, but not reserved production
accelerators.

### Access pattern: Platform validation can use both classes

Image, driver, and runtime validation often needs access to both node pools.
That is a different access rule from either production or research, so keep the
same inventory and add a policy with two grants.

```json
{
  "pool": "k8s-prod-eu-gpu",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "team",
      "subject_id": "<ml-platform-team-id>"
    }
  },
  "priority": 80,
  "priority_lane": false,
  "concurrency_limit": 10,
  "grants": [
    {
      "class": "h200-reserved",
      "concurrency_limit": 2,
      "resources": [
        {"resource": "h200", "reserved": 0, "limit": 2, "unit": "GPU", "missing_action": "reject"},
        {"resource": "CPU", "reserved": 0, "limit": 32, "unit": "CPU", "missing_action": "default", "default_value": 8},
        {"resource": "memory", "reserved": 0, "limit": 256, "unit": "GiB", "missing_action": "default", "default_value": 64}
      ]
    },
    {
      "class": "a10-burst",
      "concurrency_limit": 8,
      "resources": [
        {"resource": "GPU", "reserved": 0, "limit": 8, "unit": "GPU", "missing_action": "reject"},
        {"resource": "CPU", "reserved": 0, "limit": null, "unit": "CPU", "missing_action": "default", "default_value": 4},
        {"resource": "memory", "reserved": 0, "limit": null, "unit": "GiB", "missing_action": "default", "default_value": 24}
      ]
    }
  ]
}
```

The grant-level concurrency limits keep validation from occupying many H200
slots while still allowing broader A10 testing. A request pinned to
`gpu_class="h200-reserved"` can only use the H200 grant. A request without a
class pin can be planned against either class if all of its demands fit.

### Runtime behavior: class choice under pressure

If a production request asks for `h200` explicitly, only the `h200-reserved`
class can satisfy it because `h200` is a specific descriptor. If a research
request asks for the built-in `GPU` kind, the `a10-burst` class can satisfy it,
and the H200 class will not be used unless a policy grant and descriptor match
allow that route.

If a platform validation request can use either class, class rank prefers H200
when both are available. If H200 class concurrency is already full, the A10
grant can still admit the request if the request is compatible with the stock
`GPU` descriptor and the lower-ranked class has room.

## Example 4: Kubernetes Cluster With Per-Node Classes

The previous Kubernetes example models node pools. Some clusters require a more
precise model: each node is meaningful because it has local disks, attached
licenses, a special network path, or a workload that must be placed on one
named machine. In that case, model each Kubernetes node as its own class.

For simplicity, assume one cluster with three GPU nodes:

* `gpu-node-a`: reserved production node with four H200 GPUs.
* `gpu-node-b`: general shared node with four H200 GPUs.
* `gpu-node-c`: burst node with eight A10 GPUs.

The strategy is:

* Use one ZenML pool for the cluster.
* Use one class per node.
* Put a node selector in each class's component target settings.
* Use grants to decide which teams can use which node classes.
* Use class rank to express preferred placement when a request is not pinned to
  a specific node class.

### Inventory

```json
{
  "name": "k8s-prod-node-level",
  "description": "Node-level model of three GPU nodes in one Kubernetes cluster",
  "rank": 85,
  "accounting_mode": "authoritative",
  "concurrency_limit": 24,
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
            "subject_id": "<kubernetes-step-operator-id>",
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
      "class": "gpu-node-a",
      "rank": 100,
      "reclaimable": "never",
      "concurrency_limit": 4,
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
              "node_selector": {
                "kubernetes.io/hostname": "gpu-node-a"
              },
              "tolerations": [
                {
                  "key": "dedicated",
                  "operator": "Equal",
                  "value": "production-gpu",
                  "effect": "NoSchedule"
                }
              ]
            }
          }
        }
      ],
      "attributes": {
        "node": "gpu-node-a",
        "accelerator": "h200",
        "tier": "reserved"
      }
    },
    {
      "class": "gpu-node-b",
      "rank": 70,
      "reclaimable": "coordinated",
      "concurrency_limit": 4,
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
              "node_selector": {
                "kubernetes.io/hostname": "gpu-node-b"
              }
            }
          }
        }
      ],
      "attributes": {
        "node": "gpu-node-b",
        "accelerator": "h200",
        "tier": "shared"
      }
    },
    {
      "class": "gpu-node-c",
      "rank": 30,
      "reclaimable": "coordinated",
      "concurrency_limit": 8,
      "resources": [
        {"resource": "GPU", "quantity": 8, "unit": "GPU"},
        {"resource": "CPU", "quantity": 96, "unit": "CPU"},
        {"resource": "memory", "quantity": 384, "unit": "GiB"}
      ],
      "target_settings": [
        {
          "target_type": "component",
          "settings": {
            "pod_settings": {
              "node_selector": {
                "kubernetes.io/hostname": "gpu-node-c"
              },
              "labels": {
                "workload-tier": "burst"
              }
            }
          }
        }
      ],
      "attributes": {
        "node": "gpu-node-c",
        "accelerator": "a10",
        "tier": "burst"
      }
    }
  ],
  "attributes": {
    "cluster": "prod-eu",
    "modeling": "per-node"
  }
}
```

Use this level of detail when node identity matters. Every class has its own
pod settings, so Resource Manager can select a class and the target component
can receive the node selector that makes Kubernetes place the pod on the
intended node.

### Access pattern: Production can use only the reserved node

```json
{
  "pool": "k8s-prod-node-level",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "team",
      "subject_id": "<production-ml-team-id>"
    }
  },
  "priority": 120,
  "priority_lane": false,
  "concurrency_limit": 4,
  "grants": [
    {
      "class": "gpu-node-a",
      "resources": [
        {"resource": "h200", "reserved": 4, "limit": 4, "unit": "GPU", "missing_action": "reject"},
        {"resource": "CPU", "reserved": 32, "limit": 64, "unit": "CPU", "missing_action": "default", "default_value": 8},
        {"resource": "memory", "reserved": 256, "limit": 512, "unit": "GiB", "missing_action": "default", "default_value": 64}
      ]
    }
  ]
}
```

This policy intentionally does not grant `gpu-node-b` or `gpu-node-c`.
Production training gets deterministic placement and a protected reservation on
the reserved node. If the production team requests 6 H200 GPUs, the request is
rejected because no single granted node class can satisfy that bundle.

### Access pattern: Research can use shared H200 and burst A10

```json
{
  "pool": "k8s-prod-node-level",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "workspace",
      "subject_id": "<workspace-id>",
      "contains": {
        "subject_type": "project",
        "subject_id": "<research-project-id>"
      }
    }
  },
  "priority": 35,
  "priority_lane": false,
  "concurrency_limit": 10,
  "grants": [
    {
      "class": "gpu-node-b",
      "resources": [
        {"resource": "h200", "reserved": 0, "limit": 4, "unit": "GPU", "missing_action": "reject"},
        {"resource": "CPU", "reserved": 0, "limit": 64, "unit": "CPU", "missing_action": "default", "default_value": 8},
        {"resource": "memory", "reserved": 0, "limit": 512, "unit": "GiB", "missing_action": "default", "default_value": 64}
      ]
    },
    {
      "class": "gpu-node-c",
      "resources": [
        {"resource": "GPU", "reserved": 0, "limit": 8, "unit": "GPU", "missing_action": "reject"},
        {"resource": "CPU", "reserved": 0, "limit": 96, "unit": "CPU", "missing_action": "default", "default_value": 4},
        {"resource": "memory", "reserved": 0, "limit": 384, "unit": "GiB", "missing_action": "default", "default_value": 24}
      ]
    }
  ]
}
```

Research has no reserved share. It can use `gpu-node-b` for H200 experiments
and `gpu-node-c` for generic GPU work. Because `gpu-node-c` uses the stock
`GPU` descriptor, it can satisfy a generic `gpu_count` request. It does not
satisfy a request that explicitly demands the `h200` descriptor.

### Access pattern: Node repair drains one class

When a node needs maintenance, keep the pool and other classes alive. Add or
update a temporary policy that prevents new work from using that node while
still allowing an operations team to run one diagnostic job.

```json
{
  "pool": "k8s-prod-node-level",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "team",
      "subject_id": "<ml-platform-team-id>"
    }
  },
  "priority": 200,
  "priority_lane": true,
  "concurrency_limit": 1,
  "grants": [
    {
      "class": "gpu-node-b",
      "concurrency_limit": 1,
      "resources": [
        {"resource": "h200", "reserved": 0, "limit": 1, "unit": "GPU", "missing_action": "reject"},
        {"resource": "CPU", "reserved": 0, "limit": 8, "unit": "CPU", "missing_action": "default", "default_value": 4},
        {"resource": "memory", "reserved": 0, "limit": 64, "unit": "GiB", "missing_action": "default", "default_value": 16}
      ],
      "target_settings": [
        {
          "target_type": "component",
          "settings": {
            "pod_settings": {
              "labels": {
                "maintenance-window": "node-b"
              }
            }
          }
        }
      ]
    }
  ]
}
```

The operational decision is expressed in access policy, not by deleting
inventory. Existing lower-priority reclaimable work on `gpu-node-b` can be
preempted if the platform diagnostic request needs the slot. New research work
can still use `gpu-node-c`; production work can still use `gpu-node-a`.

### Runtime behavior: node-level placement

If an author pins `gpu_class="gpu-node-b"`, only grants for `gpu-node-b` can
admit the request. If the author does not pin a class and the demands are
compatible with more than one granted class, Resource Manager uses policy
priority and class rank to order candidates. The selected class contributes the
pod settings that place the workload on a particular Kubernetes node.

The trade-off is operational overhead. Per-node classes are precise, but class
resources and node selectors must stay aligned with the cluster. For most
clusters, node-pool classes are simpler. Use per-node classes when the node
itself is a scheduling unit that users or operators care about.

## Example 5: Multiple Kubernetes Clusters as Classes

Another modeling style is one pool that represents a fleet of reachable
clusters. Each class is a cluster, not a node or node pool. Use this pattern
when the same logical step operator can launch into several clusters, or when
the platform integration chooses a cluster based on class-level target
settings.

The important difference from the multi-region example later is that this is
one pool with several classes. Each class has its own service connector
settings, so the selected class determines which cluster credentials and
cluster identifier are passed to the target.

The strategy is:

* Use one pool for the fleet.
* Use one class per cluster.
* Put class-level `service_connector` target settings on each class.
* Use class rank to prefer the primary cluster and burst into the secondary
  cluster.
* Use policies to give different teams access to different clusters.

### Inventory

```json
{
  "name": "k8s-cross-cluster-training",
  "description": "Training capacity across three Kubernetes clusters",
  "rank": 75,
  "accounting_mode": "authoritative",
  "concurrency_limit": 60,
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
                "subject_id": "<multi-cluster-step-operator-id>",
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
                "attributes": {
                  "connector_type": "kubernetes"
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
      "class": "stockholm-cluster",
      "rank": 100,
      "reclaimable": "never",
      "concurrency_limit": 16,
      "resources": [
        {"resource": "h200", "quantity": 16, "unit": "GPU"},
        {"resource": "CPU", "quantity": 256, "unit": "CPU"},
        {"resource": "memory", "quantity": 2048, "unit": "GiB"}
      ],
      "target_settings": [
        {
          "target_type": "service_connector",
          "settings": {
            "connector_id": "<stockholm-k8s-connector-id>",
            "resource_type": "kubernetes-cluster",
            "resource_id": "stockholm-prod"
          }
        },
        {
          "target_type": "component",
          "settings": {
            "namespace": "training-prod",
            "pod_settings": {
              "node_selector": {
                "zenml.io/gpu-fleet": "h200"
              }
            }
          }
        }
      ],
      "attributes": {
        "cluster": "stockholm-prod",
        "region": "stockholm",
        "tier": "primary"
      }
    },
    {
      "class": "frankfurt-cluster",
      "rank": 70,
      "reclaimable": "coordinated",
      "concurrency_limit": 12,
      "resources": [
        {"resource": "h200", "quantity": 12, "unit": "GPU"},
        {"resource": "CPU", "quantity": 192, "unit": "CPU"},
        {"resource": "memory", "quantity": 1536, "unit": "GiB"}
      ],
      "target_settings": [
        {
          "target_type": "service_connector",
          "settings": {
            "connector_id": "<frankfurt-k8s-connector-id>",
            "resource_type": "kubernetes-cluster",
            "resource_id": "frankfurt-prod"
          }
        },
        {
          "target_type": "component",
          "settings": {
            "namespace": "training-prod",
            "pod_settings": {
              "node_selector": {
                "zenml.io/gpu-fleet": "h200"
              },
              "labels": {
                "cluster-preference": "secondary"
              }
            }
          }
        }
      ],
      "attributes": {
        "cluster": "frankfurt-prod",
        "region": "frankfurt",
        "tier": "secondary"
      }
    },
    {
      "class": "madrid-burst-cluster",
      "rank": 30,
      "reclaimable": "coordinated",
      "concurrency_limit": 24,
      "resources": [
        {"resource": "GPU", "quantity": 24, "unit": "GPU"},
        {"resource": "CPU", "quantity": null},
        {"resource": "memory", "quantity": null}
      ],
      "target_settings": [
        {
          "target_type": "service_connector",
          "settings": {
            "connector_id": "<madrid-k8s-connector-id>",
            "resource_type": "kubernetes-cluster",
            "resource_id": "madrid-burst"
          }
        },
        {
          "target_type": "component",
          "settings": {
            "namespace": "training-burst",
            "pod_settings": {
              "labels": {
                "workload-tier": "burst"
              }
            }
          }
        }
      ],
      "attributes": {
        "cluster": "madrid-burst",
        "region": "madrid",
        "tier": "burst"
      }
    }
  ],
  "attributes": {
    "modeling": "cluster-as-class",
    "fleet": "europe-training"
  }
}
```

This model makes class selection carry both accounting and access details. If
Resource Manager selects `frankfurt-cluster`, the target receives the Frankfurt
service connector settings. If it selects `madrid-burst-cluster`, the target
receives the Madrid connector and burst namespace settings.

### Access pattern: Primary cluster first, secondary cluster as burst

```json
{
  "pool": "k8s-cross-cluster-training",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "team",
      "subject_id": "<foundation-models-team-id>"
    }
  },
  "priority": 90,
  "priority_lane": false,
  "concurrency_limit": 20,
  "grants": [
    {
      "class": "stockholm-cluster",
      "resources": [
        {"resource": "h200", "reserved": 8, "limit": 16, "unit": "GPU", "missing_action": "reject"},
        {"resource": "CPU", "reserved": 128, "limit": 256, "unit": "CPU", "missing_action": "default", "default_value": 16},
        {"resource": "memory", "reserved": 1024, "limit": 2048, "unit": "GiB", "missing_action": "default", "default_value": 128}
      ]
    },
    {
      "class": "frankfurt-cluster",
      "resources": [
        {"resource": "h200", "reserved": 0, "limit": 8, "unit": "GPU", "missing_action": "reject"},
        {"resource": "CPU", "reserved": 0, "limit": 128, "unit": "CPU", "missing_action": "default", "default_value": 16},
        {"resource": "memory", "reserved": 0, "limit": 1024, "unit": "GiB", "missing_action": "default", "default_value": 128}
      ]
    }
  ]
}
```

The team gets a protected share in Stockholm and burst access in Frankfurt.
Because `stockholm-cluster` has higher class rank, compatible requests prefer
Stockholm when both grants can admit them. When Stockholm is full, Frankfurt can
admit the request through the second grant if the request is reclaimable enough
for that zero-reservation route.

### Access pattern: Research can use only the burst cluster

```json
{
  "pool": "k8s-cross-cluster-training",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "workspace",
      "subject_id": "<workspace-id>",
      "contains": {
        "subject_type": "project",
        "subject_id": "<research-sweeps-project-id>"
      }
    }
  },
  "priority": 25,
  "priority_lane": false,
  "concurrency_limit": 18,
  "grants": [
    {
      "class": "madrid-burst-cluster",
      "concurrency_limit": 18,
      "resources": [
        {"resource": "GPU", "reserved": 0, "limit": 24, "unit": "GPU", "missing_action": "reject"},
        {"resource": "CPU", "reserved": 0, "limit": null, "unit": "CPU", "missing_action": "default", "default_value": 4},
        {"resource": "memory", "reserved": 0, "limit": null, "unit": "GiB", "missing_action": "default", "default_value": 24}
      ]
    }
  ]
}
```

This policy deliberately excludes the H200 clusters. Research sweeps can fill
the burst cluster, but they cannot consume the primary or secondary H200
clusters through this policy.

### Access pattern: One team gets direct access to one cluster

```json
{
  "pool": "k8s-cross-cluster-training",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "team",
      "subject_id": "<frankfurt-ops-team-id>"
    }
  },
  "priority": 110,
  "priority_lane": false,
  "concurrency_limit": 6,
  "grants": [
    {
      "class": "frankfurt-cluster",
      "resources": [
        {"resource": "h200", "reserved": 4, "limit": 12, "unit": "GPU", "missing_action": "reject"},
        {"resource": "CPU", "reserved": 64, "limit": 192, "unit": "CPU", "missing_action": "default", "default_value": 16},
        {"resource": "memory", "reserved": 512, "limit": 1536, "unit": "GiB", "missing_action": "default", "default_value": 128}
      ],
      "target_settings": [
        {
          "target_type": "component",
          "settings": {
            "pod_settings": {
              "labels": {
                "cluster-owner": "frankfurt-ops"
              }
            }
          }
        }
      ]
    }
  ]
}
```

The Frankfurt operations team gets high-priority access to its cluster without
receiving any route into Stockholm or Madrid. This pattern works well when
cluster ownership maps to teams and the organization still requires one
pool-level accounting surface.

### Runtime behavior: selected class selects the connector

If a foundation models run requests 4 H200 GPUs and Stockholm has room,
Resource Manager selects the `stockholm-cluster` grant. The selected class
contributes the Stockholm service connector settings and the target launches in
`stockholm-prod`.

If Stockholm is full and the run is allowed to use reclaimable burst capacity,
the Frankfurt grant becomes the next candidate. The request is still one
allocation plan; it does not split two GPUs into Stockholm and two into
Frankfurt. If the research sweeps project sends the same generic GPU request,
it only has a Madrid route because its policy only grants
`madrid-burst-cluster`.

## Example 6: Multi-Region GPU Dispatch

In some deployments, the same GPU model is available in more than one region or
cluster. Pipeline authors can request H200 capacity without choosing the region
manually.

Model this as multiple pools, one per reachable execution target or region,
with similar classes and different target bindings. Pool rank represents the
placement preference. A higher-rank pool is tried first when both can admit the
request. Attributes make it possible for an advanced request to target one
region explicitly.

### Stockholm pool

```json
{
  "name": "h200-stockholm",
  "description": "H200 capacity in the Stockholm Kubernetes cluster",
  "rank": 100,
  "accounting_mode": "authoritative",
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
            "subject_id": "<stockholm-step-operator-id>",
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
      "resources": [
        {"resource": "h200", "quantity": 16, "unit": "GPU"},
        {"resource": "CPU", "quantity": 256, "unit": "CPU"},
        {"resource": "memory", "quantity": 2048, "unit": "GiB"}
      ],
      "attributes": {
        "region": "stockholm",
        "tier": "tier-a-gpu"
      }
    }
  ],
  "attributes": {
    "region": "stockholm",
    "cluster": "se-prod"
  }
}
```

### Frankfurt pool

```json
{
  "name": "h200-frankfurt",
  "description": "H200 capacity in the Frankfurt Kubernetes cluster",
  "rank": 80,
  "accounting_mode": "authoritative",
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
            "subject_id": "<frankfurt-step-operator-id>",
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
      "resources": [
        {"resource": "h200", "quantity": 8, "unit": "GPU"},
        {"resource": "CPU", "quantity": 128, "unit": "CPU"},
        {"resource": "memory", "quantity": 1024, "unit": "GiB"}
      ],
      "attributes": {
        "region": "frankfurt",
        "tier": "tier-a-gpu"
      }
    }
  ],
  "attributes": {
    "region": "frankfurt",
    "cluster": "de-prod"
  }
}
```

### Access pattern: Same team policy on both pools

Attach equivalent policies to both pools:

```json
{
  "pool": "h200-stockholm",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "team",
      "subject_id": "<foundation-models-team-id>"
    }
  },
  "priority": 90,
  "priority_lane": false,
  "grants": [
    {
      "class": "h200-reserved",
      "resources": [
        {"resource": "h200", "reserved": 8, "limit": 16, "unit": "GPU", "missing_action": "reject"},
        {"resource": "CPU", "reserved": 64, "limit": 256, "unit": "CPU", "missing_action": "default", "default_value": 8},
        {"resource": "memory", "reserved": 512, "limit": 2048, "unit": "GiB", "missing_action": "default", "default_value": 64}
      ]
    }
  ]
}
```

The same policy for Frankfurt would use `"pool": "h200-frankfurt"` and smaller
reservation/limit values if that cluster has less capacity.

### Runtime behavior: regional dispatch

```python
ResourceSettings(
    gpu_count=4,
    gpu_class="h200-reserved",
    cpu_count=32,
    memory="256GiB",
    reclaim_tolerance="none",
)
```

The author asks for the hardware class, not the region. If both pools can admit
the request, Stockholm wins because its pool rank is higher. If Stockholm is
full and Frankfurt can admit the request, Frankfurt can win instead, depending
on the policy and current queue state.

### Access pattern: Pin one project to Frankfurt

The same regional inventory can also enforce residency or cost decisions. Add a
project-specific policy only on the Frankfurt pool when a project must stay
there.

```json
{
  "pool": "h200-frankfurt",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "workspace",
      "subject_id": "<workspace-id>",
      "contains": {
        "subject_type": "project",
        "subject_id": "<eu-residency-project-id>"
      }
    }
  },
  "priority": 95,
  "priority_lane": false,
  "concurrency_limit": 4,
  "grants": [
    {
      "class": "h200-reserved",
      "resources": [
        {"resource": "h200", "reserved": 2, "limit": 8, "unit": "GPU", "missing_action": "reject"},
        {"resource": "CPU", "reserved": 32, "limit": 128, "unit": "CPU", "missing_action": "default", "default_value": 8},
        {"resource": "memory", "reserved": 256, "limit": 1024, "unit": "GiB", "missing_action": "default", "default_value": 64}
      ]
    }
  ]
}
```

That project is not admitted by any policy on the Stockholm pool, so
Stockholm's higher pool rank does not matter for it. Other projects that match
policies on both pools still use rank-based dispatch.

### Runtime behavior: one request, several candidate pools

When a request can target both step operators and matches policies on both
pools, Resource Manager creates candidate routes for Stockholm and Frankfurt.
The winning route must satisfy the entire bundle: GPUs, CPU, memory,
concurrency, target binding, and policy grant. It does not split a single step
across regions.

## Example 7: Shared Organization Pool Across Workspaces

Large organizations often buy GPUs centrally while teams work in many ZenML
workspaces. The goal is not "Workspace A owns a pool and Workspace B owns a
different pool." The goal is one organization-level pool governed by policies
that encode which teams, projects, or workspaces may use it.

This example focuses on policy strategy:

* The inventory is organization-scoped and shared.
* A broad workspace policy lets a whole workspace use a small default share.
* A team policy gives a production team stronger reservations.
* A project policy caps a sandbox project so it cannot consume the whole pool.

### Shared inventory

```json
{
  "name": "org-shared-gpu-fleet",
  "description": "Centrally purchased GPU fleet shared across workspaces",
  "rank": 90,
  "accounting_mode": "authoritative",
  "concurrency_limit": 64,
  "target_bindings": [
    {
      "target_selector": {
        "any": [
          {
            "subject_type": "organization",
            "subject_id": "<org-id>",
            "contains": {
              "subject_type": "workspace",
              "subject_id": "<workspace-a-id>",
              "contains": {
                "subject_type": "component",
                "subject_id": "<workspace-a-step-operator-id>",
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
              "subject_id": "<workspace-b-id>",
              "contains": {
                "subject_type": "component",
                "subject_id": "<workspace-b-step-operator-id>",
                "attributes": {
                  "component_type": "step_operator"
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
      "class": "tier-a-gpu",
      "rank": 100,
      "reclaimable": "never",
      "concurrency_limit": 24,
      "resources": [
        {"resource": "h200", "quantity": 24, "unit": "GPU"},
        {"resource": "CPU", "quantity": 384, "unit": "CPU"},
        {"resource": "memory", "quantity": 3072, "unit": "GiB"}
      ],
      "attributes": {
        "tier": "tier-a-gpu",
        "chargeback_group": "central-ml"
      }
    }
  ],
  "attributes": {
    "scope": "organization",
    "cost_center": "central-ml-platform"
  }
}
```

The target binding explicitly lists the step operators that can launch work
against this shared fleet. That is an infrastructure access decision. The
policies below are separate access decisions about who may consume that
infrastructure.

### Access pattern: Default workspace access

```json
{
  "pool": "org-shared-gpu-fleet",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "workspace",
      "subject_id": "<workspace-a-id>"
    }
  },
  "priority": 20,
  "priority_lane": false,
  "concurrency_limit": 8,
  "grants": [
    {
      "class": "tier-a-gpu",
      "resources": [
        {"resource": "h200", "reserved": 0, "limit": 4, "unit": "GPU", "missing_action": "reject"},
        {"resource": "CPU", "reserved": 0, "limit": 64, "unit": "CPU", "missing_action": "default", "default_value": 4},
        {"resource": "memory", "reserved": 0, "limit": 512, "unit": "GiB", "missing_action": "default", "default_value": 32}
      ]
    }
  ]
}
```

This policy says: any request from Workspace A can use up to four H200s if they
are idle, but Workspace A does not own a protected share by default.

### Access pattern: Production team reservation

```json
{
  "pool": "org-shared-gpu-fleet",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "team",
      "subject_id": "<search-prod-team-id>"
    }
  },
  "priority": 120,
  "priority_lane": false,
  "concurrency_limit": 12,
  "grants": [
    {
      "class": "tier-a-gpu",
      "resources": [
        {"resource": "h200", "reserved": 8, "limit": 16, "unit": "GPU", "missing_action": "reject"},
        {"resource": "CPU", "reserved": 128, "limit": 256, "unit": "CPU", "missing_action": "default", "default_value": 8},
        {"resource": "memory", "reserved": 1024, "limit": 2048, "unit": "GiB", "missing_action": "default", "default_value": 64}
      ]
    }
  ]
}
```

This higher-priority policy can coexist with the workspace default policy. A
request from a member of the production team may match both policies; Resource
Manager orders candidate plans by priority and rank. The team reservation is
the protected envelope for critical work.

### Access pattern: Sandbox project cap

```json
{
  "pool": "org-shared-gpu-fleet",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "workspace",
      "subject_id": "<workspace-a-id>",
      "contains": {
        "subject_type": "project",
        "subject_id": "<sandbox-project-id>"
      }
    }
  },
  "priority": 5,
  "priority_lane": false,
  "concurrency_limit": 4,
  "grants": [
    {
      "class": "tier-a-gpu",
      "resources": [
        {"resource": "h200", "reserved": 0, "limit": 2, "unit": "GPU", "missing_action": "reject"},
        {"resource": "CPU", "reserved": 0, "limit": 32, "unit": "CPU", "missing_action": "default", "default_value": 2},
        {"resource": "memory", "reserved": 0, "limit": 256, "unit": "GiB", "missing_action": "default", "default_value": 16}
      ]
    }
  ]
}
```

This policy prevents a sandbox project from becoming the reason production work
waits. It still lets users submit large sweeps; extra work queues and rolls in
as capacity frees up.

### Access pattern: Project-specific promotion without changing inventory

When a sandbox project becomes production-critical for a week, do not edit the
pool class. Add a temporary higher-priority policy for that project and remove
or time-limit it later.

```json
{
  "pool": "org-shared-gpu-fleet",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "workspace",
      "subject_id": "<workspace-a-id>",
      "contains": {
        "subject_type": "project",
        "subject_id": "<sandbox-project-id>"
      }
    }
  },
  "priority": 90,
  "priority_lane": false,
  "concurrency_limit": 6,
  "grants": [
    {
      "class": "tier-a-gpu",
      "resources": [
        {"resource": "h200", "reserved": 2, "limit": 6, "unit": "GPU", "missing_action": "reject"},
        {"resource": "CPU", "reserved": 32, "limit": 96, "unit": "CPU", "missing_action": "default", "default_value": 8},
        {"resource": "memory", "reserved": 256, "limit": 768, "unit": "GiB", "missing_action": "default", "default_value": 64}
      ]
    }
  ]
}
```

Now a request from that project may match both the low-priority sandbox cap and
the temporary promotion. Resource Manager evaluates both routes. The higher
priority route gives the project a short-lived reservation and higher ceiling
without changing the broad default policy.

### Runtime behavior: overlapping subject scopes

A single request can carry subjects for account, team, workspace, project,
pipeline, component, and service connector. In this example, a production team
member running a pipeline in Workspace A may match the workspace policy and the
team policy. The team route ranks higher because its policy priority is 120,
so it wins when it can satisfy the request.

If a sandbox project request asks for 4 H200 GPUs, the low-priority sandbox cap
rejects that route because its limit is 2. If the temporary promotion is active,
the same request can be admitted through the promotion because its limit is 6.
If both routes are impossible, the request queues only when Resource Manager
can identify a future route; otherwise it is rejected with the reason visible
on the request.

## Example 8: Cloud Machine Types

Cloud backends often expose machine shapes rather than simple resource pools.
A SageMaker, Vertex AI, Azure ML, or Modal-style backend may ask for an
instance type. Resource pool classes can model these shapes: the class name
represents the machine shape, and target settings carry the backend-specific
machine type.

The strategy is:

* Use classes for machine families.
* Bundle the machine's GPU, CPU, and memory in the class.
* Use target settings to tell the stack component which instance type to use.
* Use rank to prefer reserved or cheaper machine types.

### Inventory

```json
{
  "name": "aws-training-machines",
  "description": "SageMaker training machine families",
  "rank": 60,
  "accounting_mode": "authoritative",
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
            "subject_id": "<sagemaker-step-operator-id>",
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
      "class": "p5-48xlarge",
      "rank": 100,
      "reclaimable": "never",
      "concurrency_limit": 4,
      "resources": [
        {"resource": "GPU", "quantity": 32, "unit": "GPU"},
        {"resource": "CPU", "quantity": 768, "unit": "CPU"},
        {"resource": "memory", "quantity": 8192, "unit": "GiB"}
      ],
      "target_settings": [
        {
          "target_type": "component",
          "settings": {
            "instance_type": "ml.p5.48xlarge",
            "volume_size_gb": 1024
          }
        }
      ],
      "attributes": {
        "provider": "aws",
        "machine_type": "ml.p5.48xlarge",
        "tier": "gpu-large"
      }
    },
    {
      "class": "m7i-24xlarge",
      "rank": 20,
      "reclaimable": "never",
      "concurrency_limit": 10,
      "resources": [
        {"resource": "CPU", "quantity": 960, "unit": "CPU"},
        {"resource": "memory", "quantity": 3840, "unit": "GiB"}
      ],
      "target_settings": [
        {
          "target_type": "component",
          "settings": {
            "instance_type": "ml.m7i.24xlarge",
            "volume_size_gb": 512
          }
        }
      ],
      "attributes": {
        "provider": "aws",
        "machine_type": "ml.m7i.24xlarge",
        "tier": "cpu-large"
      }
    }
  ]
}
```

### Access pattern: GPU training pipeline

```json
{
  "pool": "aws-training-machines",
  "subject_selector": {
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
          "subject_id": "<large-training-pipeline-id>"
        }
      }
    }
  },
  "priority": 80,
  "priority_lane": false,
  "concurrency_limit": 4,
  "grants": [
    {
      "class": "p5-48xlarge",
      "resources": [
        {"resource": "GPU", "reserved": 8, "limit": 32, "unit": "GPU", "missing_action": "reject"},
        {"resource": "CPU", "reserved": 96, "limit": 768, "unit": "CPU", "missing_action": "default", "default_value": 24},
        {"resource": "memory", "reserved": 1024, "limit": 8192, "unit": "GiB", "missing_action": "default", "default_value": 128}
      ]
    }
  ]
}
```

### Access pattern: CPU preprocessing project

```json
{
  "pool": "aws-training-machines",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "workspace",
      "subject_id": "<workspace-id>",
      "contains": {
        "subject_type": "project",
        "subject_id": "<feature-engineering-project-id>"
      }
    }
  },
  "priority": 30,
  "priority_lane": false,
  "concurrency_limit": 10,
  "grants": [
    {
      "class": "m7i-24xlarge",
      "resources": [
        {"resource": "CPU", "reserved": 120, "limit": 720, "unit": "CPU", "missing_action": "reject"},
        {"resource": "memory", "reserved": 480, "limit": 2880, "unit": "GiB", "missing_action": "reject"}
      ]
    }
  ]
}
```

The same pool can represent GPU and CPU machine families. Policies decide which
pipelines or projects can use each class.

### Access pattern: Give production first choice of expensive machines

Use a higher-priority pipeline policy when a small number of production
pipelines should get the scarce, expensive shape before exploratory training.

```json
{
  "pool": "aws-training-machines",
  "subject_selector": {
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
          "subject_id": "<production-retrain-pipeline-id>"
        }
      }
    }
  },
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
          "subject_id": "<production-retrain-pipeline-id>"
        }
      }
    }
  },
  "priority": 140,
  "priority_lane": false,
  "concurrency_limit": 2,
  "grants": [
    {
      "class": "p5-48xlarge",
      "resources": [
        {"resource": "GPU", "reserved": 16, "limit": 32, "unit": "GPU", "missing_action": "reject"},
        {"resource": "CPU", "reserved": 192, "limit": 768, "unit": "CPU", "missing_action": "default", "default_value": 96},
        {"resource": "memory", "reserved": 2048, "limit": 8192, "unit": "GiB", "missing_action": "default", "default_value": 1024}
      ]
    }
  ]
}
```

The preemption group prevents two runs of the same production pipeline from
preempting each other. They queue behind one another when the pipeline-level
concurrency limit is full.

### Runtime behavior: machine shape selection

A preprocessing step with only `cpu_count` and `memory` demands is planned
against `m7i-24xlarge` because the GPU class is not needed and the CPU policy
matches the project. A training step with `gpu_count=8` cannot run on the CPU
class and must match a policy that grants `p5-48xlarge`.

If exploratory training asks for 16 GPUs while the policy limit is 8, that
route is rejected even if the pool has idle P5 capacity. Increase the policy
limit to allow that subject to use more of the existing inventory.

## Example 9: Training License With Traceability

Not all scarce resources are hardware. A vendor might sell four floating
training licenses, while CPU and memory come from a large shared backend. The
license is the resource that requires enforcement. CPU and memory are still
worth recording because operators want to understand what each licensed job
consumed.

The strategy is:

* Create a custom `training-license` descriptor.
* Put finite license seats in the class.
* Put CPU and memory in the same class with unlimited quantities for
  traceability.
* Use a pool or grant concurrency limit when the real rule is "four jobs at
  once."

### Descriptor

```json
{
  "name": "training-license",
  "kind": "license",
  "description": "Floating training license",
  "attributes": {
    "vendor": "acme",
    "contract": "enterprise"
  },
  "units": [
    {"name": "seat", "multiplier": 1}
  ]
}
```

### Inventory

```json
{
  "name": "licensed-training",
  "description": "Training jobs that require a floating vendor license",
  "rank": 50,
  "accounting_mode": "authoritative",
  "concurrency_limit": 4,
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
            "subject_id": "<orchestrator-id>",
            "attributes": {
              "component_type": "orchestrator"
            }
          }
        }
      }
    }
  ],
  "classes": [
    {
      "class": "license-seat",
      "rank": 100,
      "reclaimable": "never",
      "resources": [
        {"resource": "training-license", "quantity": 4, "unit": "seat"},
        {"resource": "CPU", "quantity": null},
        {"resource": "memory", "quantity": null}
      ],
      "attributes": {
        "license": "acme-training"
      }
    }
  ]
}
```

### Access pattern: Project license access

```json
{
  "pool": "licensed-training",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "workspace",
      "subject_id": "<workspace-id>",
      "contains": {
        "subject_type": "project",
        "subject_id": "<licensed-project-id>"
      }
    }
  },
  "priority": 50,
  "priority_lane": false,
  "concurrency_limit": 4,
  "grants": [
    {
      "class": "license-seat",
      "resources": [
        {"resource": "training-license", "reserved": 1, "limit": 4, "unit": "seat", "missing_action": "reject"},
        {"resource": "CPU", "reserved": 0, "limit": null, "unit": "CPU", "missing_action": "omit"},
        {"resource": "memory", "reserved": 0, "limit": null, "unit": "GiB", "missing_action": "omit"}
      ]
    }
  ]
}
```

### Runtime behavior: custom license demand

```python
from zenml.models import ResourceRequestDemand

ResourceSettings(
    resources=[
        ResourceRequestDemand(
            resource="training-license",
            quantity=1,
            unit="seat",
            class_name="license-seat",
        )
    ],
    cpu_count=8,
    memory="32GiB",
)
```

The request explicitly asks for the custom license. CPU and memory are also
recorded because the author set them through `ResourceSettings`. The pool class
does not limit CPU and memory globally, but request inspection still shows the
full footprint of licensed work.

### Access pattern: Split license seats between teams

If two teams share four floating seats, model the seats once and express the
split through policy grants.

```json
{
  "pool": "licensed-training",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "team",
      "subject_id": "<forecasting-team-id>"
    }
  },
  "priority": 60,
  "priority_lane": false,
  "concurrency_limit": 3,
  "grants": [
    {
      "class": "license-seat",
      "resources": [
        {"resource": "training-license", "reserved": 2, "limit": 3, "unit": "seat", "missing_action": "reject"},
        {"resource": "CPU", "reserved": 0, "limit": null, "unit": "CPU", "missing_action": "omit"},
        {"resource": "memory", "reserved": 0, "limit": null, "unit": "GiB", "missing_action": "omit"}
      ]
    }
  ]
}
```

```json
{
  "pool": "licensed-training",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "team",
      "subject_id": "<ranking-team-id>"
    }
  },
  "priority": 60,
  "priority_lane": false,
  "concurrency_limit": 3,
  "grants": [
    {
      "class": "license-seat",
      "resources": [
        {"resource": "training-license", "reserved": 2, "limit": 3, "unit": "seat", "missing_action": "reject"},
        {"resource": "CPU", "reserved": 0, "limit": null, "unit": "CPU", "missing_action": "omit"},
        {"resource": "memory", "reserved": 0, "limit": null, "unit": "GiB", "missing_action": "omit"}
      ]
    }
  ]
}
```

Each team has two protected seats and can borrow a third seat while idle. The
sum of reservations equals the four-seat license contract. The sum of limits is
larger than the pool quantity by design because limits describe the maximum a
policy may use when capacity is idle, not extra physical seats.

### Runtime behavior: traceability without CPU enforcement

If the forecasting team has three licensed jobs running, its fourth job waits
or is rejected by the policy limit even if CPU workers are free. If the ranking
team is idle, the forecasting team may borrow one extra seat up to its limit of
three. CPU and memory demands appear on the request and allocation records, but
because the class quantities are unlimited and the grant limits are null, CPU
and memory do not block admission in this example.

## Example 10: External Inference Priority Lane

This example models a shared cluster where ZenML training runs overnight on GPU
nodes that an inference system needs during traffic peaks. The inference system
does not launch through ZenML, but it can still coordinate with Resource
Manager as a trusted external workload.

The strategy is:

* Use a service account as the policy subject.
* Include a service connector subject in direct requests so pool target
  bindings can match the infrastructure target.
* Use `priority_lane: true` for the external inference policy.
* Use `grants: []` when the external system owns the whole matching class
  bundle during its claim.

### Access pattern: Priority-lane external claim

```json
{
  "pool": "k8s-prod-eu-gpu",
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
  "preemption_group": {
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
  "concurrency_limit": 8,
  "grants": []
}
```

Grantless access is deliberate here. The service account is trusted to claim
real infrastructure usage, and the policy should not restrict it to a small
reserved slice. In authoritative mode, the request still has to fit the class
resources and concurrency limits.

### Runtime behavior: direct external request

```json
{
  "subjects": [
    {
      "subject_type": "organization",
      "subject_id": "<org-id>",
      "child": {
        "subject_type": "account",
        "subject_id": "<inference-service-account-id>",
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
          "subject_id": "<gke-connector-id>",
          "attributes": {
            "connector_type": "gcp",
            "effective_resource_type": "kubernetes-cluster",
            "effective_resource_id": "prod-eu"
          }
        }
      }
    }
  ],
  "pool": "k8s-prod-eu-gpu",
  "demands": [
    {"resource": "h200", "quantity": 4, "unit": "GPU", "class": "h200-reserved"},
    {"resource": "CPU", "quantity": 48, "unit": "CPU", "class": "h200-reserved"},
    {"resource": "memory", "quantity": 384, "unit": "GiB", "class": "h200-reserved"}
  ],
  "reclaim_tolerance": "none",
  "lease_expires_at": "2026-07-23T18:30:00Z",
  "metadata": {
    "service": "recommendations",
    "traffic_window": "peak"
  }
}
```

The service account subject matches the policy. The service connector subject
matches the pool target. If lower-priority ZenML work is using reclaimable
capacity, the priority-lane request can cause Resource Manager to preempt it
and return capacity to the external service.

### Access pattern: Soft external reservation without priority lane

Not every external workload needs emergency power. A batch scoring service can
use a normal policy with a reservation and limit.

```json
{
  "pool": "k8s-prod-eu-gpu",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "account",
      "subject_id": "<batch-scoring-service-account-id>",
      "attributes": {
        "is_service_account": true
      }
    }
  },
  "priority": 45,
  "priority_lane": false,
  "concurrency_limit": 4,
  "grants": [
    {
      "class": "a10-burst",
      "resources": [
        {"resource": "GPU", "reserved": 4, "limit": 12, "unit": "GPU", "missing_action": "reject"},
        {"resource": "CPU", "reserved": 0, "limit": null, "unit": "CPU", "missing_action": "default", "default_value": 4},
        {"resource": "memory", "reserved": 0, "limit": null, "unit": "GiB", "missing_action": "default", "default_value": 24}
      ]
    }
  ]
}
```

This policy lets the external service coordinate fairly with ZenML work. It
does not jump to the maximum possible priority, so higher-priority production
training can still outrank it. Use priority lane only for systems that must
reclaim capacity immediately.

### Runtime behavior: external claim during a traffic spike

At night, research sweeps may hold reclaimable A10 capacity. At 09:00, the
inference controller creates the priority-lane request for 4 H200 GPUs with
`reclaim_tolerance="none"`. Resource Manager compares it against active
allocations. Lower-priority reclaimable allocations that are not protected by
the same preemption group can be selected as victims. Allocations with
`reclaim_tolerance="none"` are not selected as victims.

If the direct request omits the service connector subject, it may match the
policy subject but fail the pool target binding. External clients should send
both identity subjects and target subjects.

## Example 11: Governance With Kueue or Run:ai

Some environments already use an infrastructure scheduler such as Kueue or
Run:ai for hard enforcement. In that case, Resource Manager can route work,
apply target settings, and provide a consistent ZenML policy layer while the
infrastructure scheduler remains responsible for runtime allocation.

The strategy is:

* Set `accounting_mode: "governance"`.
* Model classes as the queues or workload classes known to the infrastructure
  scheduler.
* Put Kueue, Run:ai, or scheduler-specific settings in component target
  settings.
* Use policies to decide which ZenML subjects are allowed to target those
  infrastructure queues.

### Inventory

```json
{
  "name": "kueue-governed-gpu",
  "description": "GPU workloads governed by Kubernetes Kueue",
  "rank": 80,
  "accounting_mode": "governance",
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
            "subject_id": "<kubernetes-orchestrator-id>",
            "attributes": {
              "component_type": "orchestrator"
            }
          }
        }
      }
    }
  ],
  "classes": [
    {
      "class": "kueue-gpu-training",
      "rank": 100,
      "reclaimable": "coordinated",
      "resources": [
        {"resource": "GPU", "quantity": 32, "unit": "GPU"},
        {"resource": "CPU", "quantity": null},
        {"resource": "memory", "quantity": null}
      ],
      "target_settings": [
        {
          "target_type": "component",
          "settings": {
            "pod_settings": {
              "labels": {
                "kueue.x-k8s.io/queue-name": "gpu-training"
              }
            }
          }
        }
      ],
      "attributes": {
        "scheduler": "kueue",
        "queue": "gpu-training"
      }
    }
  ]
}
```

### Access pattern: Research queue access

```json
{
  "pool": "kueue-governed-gpu",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "team",
      "subject_id": "<research-team-id>"
    }
  },
  "priority": 40,
  "priority_lane": false,
  "grants": [
    {
      "class": "kueue-gpu-training",
      "resources": [
        {"resource": "GPU", "reserved": 0, "limit": 8, "unit": "GPU", "missing_action": "reject"},
        {"resource": "CPU", "reserved": 0, "limit": null, "unit": "CPU", "missing_action": "default", "default_value": 4},
        {"resource": "memory", "reserved": 0, "limit": null, "unit": "GiB", "missing_action": "default", "default_value": 24}
      ]
    }
  ]
}
```

In governance mode, use this as a routing and policy-control pattern. Runtime
capacity enforcement, queue fairness, and preemption are expected to happen in
the infrastructure scheduler.

### Access pattern: Separate Kueue queues by subject

Because the class target settings can name a Kueue queue, the same inventory
style can expose multiple infrastructure queues as classes.

```json
{
  "pool": "kueue-governed-gpu",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "team",
      "subject_id": "<production-ml-team-id>"
    }
  },
  "priority": 100,
  "priority_lane": false,
  "concurrency_limit": 12,
  "grants": [
    {
      "class": "kueue-gpu-training",
      "resources": [
        {"resource": "GPU", "reserved": 0, "limit": 16, "unit": "GPU", "missing_action": "reject"},
        {"resource": "CPU", "reserved": 0, "limit": null, "unit": "CPU", "missing_action": "default", "default_value": 8},
        {"resource": "memory", "reserved": 0, "limit": null, "unit": "GiB", "missing_action": "default", "default_value": 64}
      ],
      "target_settings": [
        {
          "target_type": "component",
          "settings": {
            "pod_settings": {
              "labels": {
                "kueue.x-k8s.io/queue-name": "gpu-production"
              }
            }
          }
        }
      ]
    }
  ]
}
```

The policy-level target settings override or supplement the general class
settings for this subject. Resource Manager still records the request, grants,
and selected class. Kueue decides when pods actually run and how preemption is
enforced inside Kubernetes.

### Runtime behavior: governance is not authoritative allocation

In authoritative mode, Resource Manager accounts for the pool quantity and
preempts lower-priority reclaimable work when needed. In governance mode, the
policy still controls whether a ZenML subject may target a class, but the
infrastructure scheduler is the source of truth for actual capacity, fairness,
and pod preemption. Use governance when your Kubernetes scheduler already owns
those decisions and ZenML should provide policy, routing, and observability.

## Example 12: Policy Cookbook

The remaining examples reuse inventory from earlier sections and focus on
policy language. Once a pool models the infrastructure, policies define
priority, access, reservations, limits, and operational guardrails.

### Give one team a reserved share and a burst ceiling

Use this when a team pays for a baseline but may borrow idle capacity.

```json
{
  "pool": "org-shared-gpu-fleet",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "team",
      "subject_id": "<recommendations-team-id>"
    }
  },
  "priority": 70,
  "priority_lane": false,
  "grants": [
    {
      "class": "tier-a-gpu",
      "resources": [
        {"resource": "h200", "reserved": 4, "limit": 10, "unit": "GPU", "missing_action": "reject"},
        {"resource": "CPU", "reserved": 64, "limit": 160, "unit": "CPU", "missing_action": "default", "default_value": 8},
        {"resource": "memory", "reserved": 512, "limit": 1280, "unit": "GiB", "missing_action": "default", "default_value": 64}
      ]
    }
  ]
}
```

The reservation protects the team from starvation. The limit prevents the team
from taking the entire class when everyone else is also busy.

### Make production outrank experiments

Use two policies against the same class. The production policy has higher
priority and reserved share. The experiment policy has lower priority and no
reservation.

```json
{
  "pool": "k8s-prod-eu-gpu",
  "subject_selector": {
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
  },
  "priority": 150,
  "priority_lane": false,
  "grants": [
    {
      "class": "h200-reserved",
      "resources": [
        {"resource": "h200", "reserved": 6, "limit": 8, "unit": "GPU", "missing_action": "reject"},
        {"resource": "CPU", "reserved": 96, "limit": 128, "unit": "CPU", "missing_action": "default", "default_value": 8},
        {"resource": "memory", "reserved": 768, "limit": 1024, "unit": "GiB", "missing_action": "default", "default_value": 64}
      ]
    }
  ]
}
```

```json
{
  "pool": "k8s-prod-eu-gpu",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "workspace",
      "subject_id": "<workspace-id>",
      "contains": {
        "subject_type": "project",
        "subject_id": "<experiments-project-id>"
      }
    }
  },
  "priority": 10,
  "priority_lane": false,
  "grants": [
    {
      "class": "h200-reserved",
      "resources": [
        {"resource": "h200", "reserved": 0, "limit": 2, "unit": "GPU", "missing_action": "reject"},
        {"resource": "CPU", "reserved": 0, "limit": 32, "unit": "CPU", "missing_action": "default", "default_value": 4},
        {"resource": "memory", "reserved": 0, "limit": 256, "unit": "GiB", "missing_action": "default", "default_value": 32}
      ]
    }
  ]
}
```

If experiments use `reclaim_tolerance="coordinated"` or `"any"`, production can
preempt them when needed. If production uses `reclaim_tolerance="none"`, it
waits for reserved share instead of depending on reclaimable capacity.

### Put a hard cap on one user or service account

Use this when a single automation account launches many jobs and should never
occupy more than a small slice.

```json
{
  "pool": "workspace-standard-compute",
  "subject_selector": {
    "subject_type": "account",
    "subject_id": "<user-account-id>",
    "attributes": {
      "is_service_account": false
    }
  },
  "priority": 15,
  "priority_lane": false,
  "concurrency_limit": 2,
  "grants": [
    {
      "class": "standard-workers",
      "resources": [
        {"resource": "CPU", "reserved": 0, "limit": 16, "unit": "CPU", "missing_action": "reject"},
        {"resource": "memory", "reserved": 0, "limit": 64, "unit": "GiB", "missing_action": "reject"}
      ]
    }
  ]
}
```

The concurrency limit is the most important field here. Even if the user's
jobs request only 1 CPU each, no more than two active requests can run through
this policy.

### Use a scheduled policy window

Use this when burst access is allowed only overnight. The policy selector is an
expression because the time window is attached to the policy match.

```json
{
  "pool": "k8s-prod-eu-gpu",
  "subject_selector": {
    "any": [
      {
        "subject_type": "organization",
        "subject_id": "<org-id>",
        "contains": {
          "subject_type": "workspace",
          "subject_id": "<workspace-id>",
          "contains": {
            "subject_type": "project",
            "subject_id": "<nightly-evals-project-id>"
          }
        }
      }
    ],
    "time_selector": {
      "schedule": {
        "timezone": "Europe/Berlin",
        "start_time": "20:00:00",
        "end_time": "08:00:00",
        "days_of_week": ["mon", "tue", "wed", "thu", "fri"],
        "days_of_month": [],
        "weeks_of_month": [],
        "months": []
      }
    }
  },
  "priority": 25,
  "priority_lane": false,
  "grants": [
    {
      "class": "a10-burst",
      "resources": [
        {"resource": "GPU", "reserved": 0, "limit": 16, "unit": "GPU", "missing_action": "reject"},
        {"resource": "CPU", "reserved": 0, "limit": null, "unit": "CPU", "missing_action": "default", "default_value": 4},
        {"resource": "memory", "reserved": 0, "limit": null, "unit": "GiB", "missing_action": "default", "default_value": 24}
      ]
    }
  ]
}
```

This pattern keeps daytime capacity available for interactive and production
work while still letting nightly sweeps fill the cluster.

### Admit a trusted system to the whole pool

Use grantless policies only for trusted subjects. They expose every matching
class resource to the subject.

```json
{
  "pool": "team-h200-machines",
  "subject_selector": {
    "subject_type": "organization",
    "subject_id": "<org-id>",
    "contains": {
      "subject_type": "account",
      "subject_id": "<maintenance-service-account-id>",
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

The service account gets the maximum priority and access to every matching
class. It still cannot allocate resources that the pool class does not contain,
and it still respects pool, class, and policy concurrency limits.

## See also

* [Admin guide](resource-pools-admin-guide.md) - UI setup flow and exact API
  shape.
* [Core concepts](resource-pools-core-concepts.md) - descriptors, classes,
  subjects, policies, and requests.
* [User guide](resource-pools-user-guide.md) - author settings and request
  inspection.
* [External workloads](resource-pools-external-workloads.md) - direct request
  details.
* [Reconciliation process](resource-pools-reconciliation.md) - runtime
  behavior.
