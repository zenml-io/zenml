---
description: >-
  Fair GPU and compute sharing for AI/ML teams: dependable production capacity,
  shared pools, idle reuse, and workspace-level quotas.
icon: layer-group
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Resource pools

{% hint style="info" %}
Resource pools are part of ZenML's paid features. For availability and plans,
see the [pricing page](https://www.zenml.io/pricing).
{% endhint %}

{% hint style="info" %}
Resource pools are only available for [dynamic pipelines](https://docs.zenml.io/how-to/steps-pipelines/dynamic_pipelines).
{% endhint %}

If you run AI or ML work in a shared environment, you have probably seen the
same problems: jobs fighting over GPUs, surprise slowdowns when another team
launches a big run, or expensive hardware sitting idle while someone waits in a
queue. Resource pools are ZenML Pro’s answer. They are aimed at
*platform and team leaders* who need clear rules, and at *practitioners* who
just want their steps to get the right compute without babysitting the cluster.

Here are typical situations this feature is built for:

**“Our production jobs must finish—no surprises.”**  
You have training, fine-tuning, or inference that cannot vanish because someone
else submitted a heavier workload. You want a clear agreement: this stack or
this team gets a dependable slice of capacity, and critical steps are not stopped
to make room for ad hoc work.

**“We share one pool of GPUs across many teams.”**  
You need one place that describes how much capacity exists, who may use it, and
what happens when everyone wants it at once—without maintaining a separate
spreadsheet or manual booking process for every pipeline.

**“We paid for the hardware—we should use it when it’s free.”**  
When one group is quiet, you want other teams to use spare capacity so machines
do not sit empty. You also want the original team to get their capacity back when
they return, without a long negotiation or a cluster reconfiguration every
time.

**“Engineers describe needs; ops maps them to reality.”**  
Pipeline authors say what each step requires (GPUs, memory, and so on). Platform
or DevOps ties those stacks to the right shared capacity. The same pipeline code
can run in different environment or stages without hard-coding cluster details.

**“We need to ration more than just GPUs.”**  
Alongside standard compute, you may need to track things like licenses, special
hardware, or how many pipeline steps may run at once. Pools let you treat those
as countable resources under the same workspace-level model, as long as your
organization agrees on names and units.

None of this replaces your orchestrator or cloud provider—it coordinates
demand so teams see fair queuing, optional sharing of idle capacity, and explicit
rules for critical versus best-effort work. When you are ready for how ZenML
models that behavior, continue with [Introduction to capacity management](#introduction-to-capacity-management)
and [Core concepts](#core-concepts).

## Introduction to capacity management

ZenML Pro resource pooling separates three concerns: what capacity exists, what
each pipeline step asks for, and which stack components may draw from which pools under
which rules. The subsections below describe the strategy; [Core concepts](#core-concepts)
then defines terms and mechanics precisely.

### Supply: resource pools

On one side, **resource pools** describe resources that are available and
consumable when pipeline steps run. They often include standard compute—GPUs,
CPUs, and RAM—that orchestrators understand and that map to real infrastructure,
but pools are not limited to that. Teams can define **custom resource keys** as a
convention between whoever operates the platform and whoever writes pipelines:
capabilities, access to external services or tools, licenses, or any other
scarce thing you want to schedule in integer units. The same resource key names
must appear in pool capacity and in step requests for the convention to work.
This is the contract between the platform and the users.

The number of **parallel step runs** is also modeled as a resource today so
concurrency can be capped alongside GPU or CPU demand.
A pool can hold **multiple resource types at once** (for example GPUs and a
`step_run` slot). 

**Who defines pools:** the role that owns infrastructure access—IT ops,
platform engineering, DevOps, or similar — defines and maintains resource pools
at workspace scope so every team in that workspace shares the same catalog
of named capacity.

### Demand: `ResourceSettings` on steps

On the other side, **pipeline steps** declare what they need through
`ResourceSettings`. That is typically the ML engineer, AI engineer, or data
engineer annotating each step with GPUs, CPUs, memory, and optionally the same
custom keys the admins put in pools. Authors can align requests with published
pool capacity and follow whatever naming convention the platform agreed on for
non-standard resources.

Steps also declare whether or not they are **preemptible**. Preemption is the
ability to interrupt a running step run before it completes, to free up resources for
other steps demanding them with a higher priority. Steps that are preemptible
are not guaranteed to complete if they go outside of their reserved capacity.
They may be interrupted, re-added to the queue and restarted again later, or
even cancelled if they are not configured to allow retries.

That is the product-level tradeoff: **preemptible** steps may access more of the
pool — including capacity that others are not using right now — but another
workload can force them off the machine if priorities and policies require it,
so they can fail early when contention is high. **Non-preemptible** steps opt
into a smaller, dependable slice: they only consume what resources are reserved
for them, so they are not evicted for pool reasons, at the cost of not using the
“burst” capacity above that reservation.

### The link: subject policies

**Subject policies** connect pools to execution. A policy binds a workload bearing **stack
component** — today an orchestrator or step operator — to a pool and states what
subset of that pool’s resources that component may use. Steps stay decoupled
from a specific pool name: resolution uses the component in the active stack,
so the same step definition can behave differently in different environments
without code changes.

Policies are usually owned by the same platform or admin function, but ML
teams can share ownership where it makes sense. Each policy carries **priority**,
**reserved** amounts per key, and optionally **limits**:

* **Reservation** answers “what pool share is accounted exclusively to this component”
  and is the only capacity that **non-preemptible** steps may rely on: they
  cannot use the gap between reserved and limit.
* **Limits** (and the pool’s own maximum) bound how many resources **preemptible** work
  can take when spare capacity exists; without a limit, the effective ceiling is
  what the pool still has free. A higher limit does not raise the ceiling for
  non-preemptible requests; you need to raise **reserved** if those jobs need more per step.

When thinking about subject policies, it's helpful to understand that multiple
steps in the same run or even in different runs will share the resources defined
in the same subject policy if they run on the same stack component. So they will compete for the same reserved resources. If they go outside of their reserved capacity, they will also compete with other stack components that access the same pool.

Together, pools plus policies plus step annotations implement a **shared,
prioritized, optionally elastic** scheduling story: strict guarantees where
needed, elastic sharing where teams accept preemption risk.

### What this looks like: three surfaces

**1 — Pool (supply).**  
Platform ops create a workspace pool, name it whatever helps the org (say
**datacenter-one**), and record how much of each scarce thing exists there: **10
GPUs**, **200 CPUs** and **500 GB of memory**. That number is the shared ceiling everyone draws from.

```shell
zenml resource-pool create datacenter-one \
  --capacity '{"gpu": 10, "mcpu": 200000, "memory_mb": 5120000}'
```

**2 — Policy (wiring a stack to a pool).**  
They attach a **subject policy** so a specific stack component knows which pool
to use and what slice it may claim. If your pipeline runs on a stack called **prod-stack**, its orchestrator (or step operator) is the component named in
the policy: “prod-stack’s orchestrator may pull from **datacenter-one**, with
*this much* reserved and *this much* limit,” and a priority
versus other stacks.

```shell
zenml resource-pool attach-policy datacenter-one prod-stack \
  --priority 10 \
  --reserved '{"gpu": 4, "mcpu": 8000, "memory_mb": 20480}' \
  --limit '{"gpu": 6, "mcpu": 16000, "memory_mb": 81920}'
```

**3 — Step request (what the run asks for).**  
The data scientist opens a step and says, in effect, **“this step needs three
GPUs, 1 CPU and 2 GB of memory”** and can be preempted.

```python
from zenml import step, pipeline
from zenml.config import ResourceSettings

resource_settings=ResourceSettings(
    gpu_count=3,
    cpu_count=1,
    memory="2GiB",
    preemptible=True,
)

@step(settings={"resources": resource_settings})
def my_step(input: str) -> None:
    print(input)

@pipeline(dynamic=True)
def my_pipeline(input: str) -> None:
    my_step(input)

if __name__ == "__main__":
    my_pipeline(input="Hello, World!")
```

When they launch a **dynamic** run on **prod-stack**, ZenML turns that into a **resource
request**: three GPUs, matched against **datacenter-one** through prod-stack’s policy.
If three are free, the step proceeds; if not, it **waits** in line; if the ask
breaks the rules (too many GPUs, non-preemptible without reservation), it
**fails fast** with a clear status. Run and step views show **queued / allocated
/ rejected** so operators can compare ZenML to the real cluster.

The subsections explain how queues, borrowing, and preemption implement
that model in ZenML Pro.

## See also

* [Workspaces](./workspaces.md) — pools are scoped to the workspace.
* [Teams](./teams.md) — organizational context for who owns which stacks and
  policies.
* ZenML OSS: [step and pipeline configuration](https://docs.zenml.io/how-to/steps-pipelines/configuration).
