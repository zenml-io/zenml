---
description: >-
  Enable ZenML Pro event triggers and schedules (scheduler and executor
  microservices) for self-hosted workspace servers on Kubernetes.
layout:
  title:
    visible: true
  description:
    visible: true
  tableOfContents:
    visible: true
  outline:
    visible: true
  pagination:
    visible: true
---

# Enable Event Triggers and Schedules for the Workspace Server

ZenML Pro [schedule triggers](triggers.md#schedule-triggers) run pipelines on a
cron or interval. [Platform event triggers](triggers.md#platform-event-triggers)
run pipelines when lifecycle events occur in the ZenML platform (for example
after another pipeline completes). On self-hosted workspaces, both are part
of the same opt-in capability and use the same background infrastructure:
two additional microservices—the **scheduler** and the **executor**—plus a
**Redis** broker that connects them.

{% hint style="warning" %}
**Commercial add-on:** Event triggers and schedules (schedule triggers and
platform event triggers) are not included in the base ZenML Pro plan. Your
organization must purchase and enable them explicitly. See the
[pricing page](https://www.zenml.io/pricing) for plans and contact ZenML if you
need entitlements enabled for your license.
{% endhint %}

{% hint style="warning" %}
Deploy these microservices only for workspace servers installed with the ZenML
Helm chart on Kubernetes. Other platforms (for example AWS ECS) are not covered
here.
{% endhint %}

{% hint style="info" %}
**Prerequisite:** Event triggers and schedules dispatch work against [pipeline
snapshots](snapshots.md). You must enable the workload manager (snapshot
support) on the workspace server before or together with the scheduler
and executor. Follow [Enable Snapshot Support](deploy-workspace-snapshots.md)
first if you have not configured it yet.
{% endhint %}

## Prerequisites

- **[Snapshot support (workload manager)](deploy-workspace-snapshots.md)
  configured** so triggered runs can execute pipeline snapshots in Kubernetes.
- A **Redis** instance reachable from the workspace namespace. The scheduler and
  executor use Redis Streams as a message broker. Use a URL such as
  `redis://<redis-host>:6379/0`, or `rediss://<redis-host>:<port>/0` when Redis
  requires TLS.
- Enough cluster resources for the two microservices below (see the example
  `resources`).

## What to configure in Helm

The ZenML Helm chart deploys optional background processes as additional
microservices, each declared under the `workerDeployments` key in your
workspace `values.yaml`. Each map entry becomes its own Kubernetes
Deployment.

Add a `workerDeployments` block next to your existing `server:` configuration.
Each microservice uses the same container image as the ZenML Pro server by
default and overrides the entrypoint to run the `plugins` helper with the
subcommands below.

The example enables both the **scheduler** and **executor** microservices:
they use the `plugins` command with `start-scheduler` and `start-executor`,
share `ZENML_REDIS_BROKER_URL`, and set SQLAlchemy pool sizes appropriate for
dedicated pods. Adjust `resources`, probes, and pool sizes to match your
cluster and load.

{% hint style="warning" %}
The **scheduler** microservice must always run as a **single replica** with a
**`Recreate`** rollout strategy. Do not scale it horizontally or switch to
`RollingUpdate`; multiple scheduler pods or overlapping rollouts can break
schedule and event dispatch.
{% endhint %}

```yaml
workerDeployments:
  scheduler:
    enabled: true
    replicaCount: 1
    command: ["plugins"]
    args: ["start-scheduler"]
    strategy:
      type: Recreate
    resources:
      requests:
        cpu: 100m
        memory: 256Mi
      limits:
        cpu: 500m
        memory: 512Mi
    environment:
      ZENML_STORE_POOL_SIZE: "1"
      ZENML_STORE_MAX_OVERFLOW: "1"
    secretEnvironment:
      ZENML_REDIS_BROKER_URL: redis://zenml-redis:6379/0
    livenessProbe:
      httpGet:
        path: /health
        port: 8000
      initialDelaySeconds: 30
      periodSeconds: 60
      timeoutSeconds: 2
      failureThreshold: 3
    readinessProbe:
      httpGet:
        path: /health
        port: 8000
      initialDelaySeconds: 10
      periodSeconds: 30
      timeoutSeconds: 2
      failureThreshold: 3

  executor:
    enabled: true
    replicaCount: 1
    command: ["plugins"]
    args: ["start-executor"]
    resources:
      requests:
        cpu: 100m
        memory: 256Mi
      limits:
        cpu: 500m
        memory: 1024Mi
    environment:
      ZENML_CONSUMER_WORKER_POOL_SIZE: "16"
      ZENML_STORE_POOL_SIZE: "1"
      ZENML_STORE_MAX_OVERFLOW: "8"
    secretEnvironment:
      ZENML_REDIS_BROKER_URL: redis://zenml-redis:6379/0
    livenessProbe:
      httpGet:
        path: /health
        port: 8000
      initialDelaySeconds: 30
      periodSeconds: 60
      timeoutSeconds: 2
      failureThreshold: 3
    readinessProbe:
      httpGet:
        path: /health
        port: 8000
      initialDelaySeconds: 10
      periodSeconds: 30
      timeoutSeconds: 2
      failureThreshold: 3
```

For platform event triggers, the workspace **API server** must use the
**same** Redis broker URL so it can publish pipeline lifecycle events (for
example run completion) to Redis Streams for the executor to consume. Define
this as a Kubernetes Secret in `server.secretEnvironment` and merge with
any keys you already set:

```yaml
server:
  secretEnvironment:
    ZENML_REDIS_BROKER_URL: redis://zenml-redis:6379/0
```

### Environment variables (reference)

| Variable | Where | Purpose |
|----------|--------|---------|
| `ZENML_REDIS_BROKER_URL` | scheduler, executor, API server | Redis connection URL for the broker |
| `ZENML_STORE_POOL_SIZE` | scheduler, executor | SQLAlchemy pool size (defaults apply if unset) |
| `ZENML_STORE_MAX_OVERFLOW` | scheduler, executor | SQLAlchemy max overflow for the store connection pool |
| `ZENML_CONSUMER_WORKER_POOL_SIZE` | executor | Async pool size for dispatch processing in the executor microservice |

## Apply the change

After updating your values file, upgrade the release (adjust release name and
namespace as you use them):

```bash
helm upgrade zenml oci://public.ecr.aws/zenml/zenml \
  --namespace zenml-workspace \
  --values zenml-workspace-values.yaml
```

## Related behavior

- **Triggers and snapshots:** Both schedule and platform event triggers attach
  to [pipeline snapshots](snapshots.md). Snapshot support is therefore a
  **prerequisite**: without the [workload manager](deploy-workspace-snapshots.md),
  triggered runs cannot execute as described in [Triggers](triggers.md).
- **Concepts:** See [Schedule Triggers](triggers.md#schedule-triggers) and
  [Platform Event Triggers](triggers.md#platform-event-triggers) for how these
  triggers are modeled in ZenML Pro.

## Related resources

- [Self-hosted Deployment on Kubernetes with Helm](deploy-workspace-k8s.md)
- [Enable Snapshot (Workload Manager) Support](deploy-workspace-snapshots.md)
- [Triggers](triggers.md)
- [Helm chart on Artifact Hub](https://artifacthub.io/packages/helm/zenml/zenml)
