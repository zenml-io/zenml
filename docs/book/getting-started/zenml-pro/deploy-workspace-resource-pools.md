---
description: >-
  Enable the ZenML Pro resource pool reconciler worker for self-hosted workspace
  servers on Kubernetes.
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

# Enable Resource Pools for the Workspace Server

[Resource pools](resource-pools.md) let you model shared capacity (GPUs, custom
keys, and related limits) for dynamic pipelines. Keeping pool state
consistent uses a background **reconciler** process in ZenML Pro.

On **Kubernetes** self-hosted deployments, you enable that process by adding
a Helm **worker** deployment named `resource-pool-reconciler` that runs
`plugins start-resource-pool-reconciler` (same image as the workspace server).

{% hint style="warning" %}
**Commercial add-on:** Resource pools are not included in the base ZenML Pro
plan. Your organization must purchase and enable them explicitly. See the
[pricing page](https://www.zenml.io/pricing) for plans and contact ZenML if
you need entitlements enabled for your license.
{% endhint %}

{% hint style="warning" %}
Deploy this worker only for workspace servers installed with the ZenML Helm
chart on Kubernetes. Other platforms (for example AWS ECS) are not covered
here.
{% endhint %}

## Prerequisites

- Resource pools apply to
  [dynamic pipelines](https://docs.zenml.io/how-to/steps-pipelines/dynamic_pipelines).
  Ensure your teams understand that contract before enabling the reconciler.
- Enough cluster resources for one extra Deployment (see the example `resources`
  below).

## What to configure in Helm

Merge a `workerDeployments` entry into your workspace values file next to
your existing `server:` configuration. The worker uses the same container
image as the ZenML Pro server by default; it overrides the entrypoint to run
the reconciler.

Set SQLAlchemy pool sizes appropriate for a dedicated worker pod. The example
below is a reasonable starting point; adjust `resources` and probes for your
environment.

{% hint style="warning" %}
The **resource pool reconciler** must always run as a **single replica** with a
**`Recreate`** rollout strategy. Do not scale it horizontally or switch to
`RollingUpdate`; multiple reconciler pods or overlapping rollouts can corrupt
or confuse pool reconciliation.
{% endhint %}

```yaml
workerDeployments:
  resource-pool-reconciler:
    enabled: true
    replicaCount: 1
    command: ["plugins"]
    args: ["start-resource-pool-reconciler"]
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

### Environment variables (reference)

| Variable | Purpose |
|----------|---------|
| `ZENML_STORE_POOL_SIZE` | SQLAlchemy pool size for store access in the worker |
| `ZENML_STORE_MAX_OVERFLOW` | SQLAlchemy max overflow for the store connection pool |

## Apply the change

After updating your values file, upgrade the release (adjust release name and
namespace as you use them):

```bash
helm upgrade zenml oci://public.ecr.aws/zenml/zenml \
  --namespace zenml-workspace \
  --values zenml-workspace-values.yaml
```

## Related resources

- [Resource pools](resource-pools.md) — product overview and concepts
- [Resource pools — Core concepts](resource-pools-core-concepts.md)
- [Self-hosted Deployment on Kubernetes with Helm](deploy-workspace-k8s.md)
- [Helm chart on Artifact Hub](https://artifacthub.io/packages/helm/zenml/zenml)
