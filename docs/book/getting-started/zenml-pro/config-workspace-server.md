---
description: Configuration reference for the ZenML Workspace Server.
icon: database
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Workspace Server Configuration

This page provides the configuration reference for the ZenML Workspace Server, including the workload manager that enables running pipelines from the UI. For an overview of what the Workspace Server does, see [System Architecture](system-architecture.md#workspace-server).

{% hint style="info" %}
This configuration is relevant for **Hybrid** and **Self-hosted** deployments. In SaaS deployments, the Workspace Server is fully managed by ZenML.
{% endhint %}

<!-- DIAGRAM: Workspace Server connectivity showing SDK clients, dashboard, orchestrators, and workload manager runner pods -->

## Permissions

When running your own Workspace Server, you need full CRUD permissions on a dedicated database (MySQL only, PostgreSQL not supported for workspace servers).

## Network Requirements

| Direction | Source/Destination | Protocol | Purpose |
|-----------|-------------------|----------|---------|
| **Ingress** | ZenML SDK clients | HTTPS | API requests from developers and CI/CD |
| **Ingress** | ZenML Pro Dashboard | HTTPS | UI data requests |
| **Ingress** | Orchestrator pods/tasks | HTTPS | Pipeline status updates, metadata logging |
| **Egress** | Database | TCP | MySQL persistent storage |
| **Egress** | Control Plane | HTTPS | Authentication |
| **Egress** | Secrets backend | HTTPS | AWS Secrets Manager, GCP Secret Manager, etc. |
| **Egress** | Artifact Store | HTTPS | Artifact visualizations |
| **Egress** | Kubernetes API | HTTPS | Workload manager pod creation (port 6443) |

## Workload Manager

The Workspace Server includes a workload manager that enables running pipelines directly from the ZenML Pro UI. **This requires access to a Kubernetes cluster where ad-hoc runner pods can be created.**

{% hint style="warning" %}
Snapshots are only available from ZenML workspace server version 0.90.0 onwards.
{% endhint %}

### Requirements

- Kubernetes cluster (1.24+) accessible from the workspace server
- Dedicated namespace for runner pods
- Service account with RBAC permissions to create/manage pods

### Supported Implementations

| Implementation | Platform | Use Case |
|---------------|----------|----------|
| `KubernetesWorkloadManager` | Any Kubernetes (EKS, GKE, AKS, self-managed) | Standard setup, fast minimalistic configuration |
| `AWSKubernetesWorkloadManager` | EKS | AWS-native with ECR image building and S3 log storage |
| `GCPKubernetesWorkloadManager` | GKE | GCP-native with GCR support (GCS log storage planned) |

### Environment Variables Reference

**Required for all implementations:**

| Variable | Required | Description |
|----------|----------|-------------|
| `ZENML_SERVER_WORKLOAD_MANAGER_IMPLEMENTATION_SOURCE` | Yes | Implementation class (see values below) |
| `ZENML_KUBERNETES_WORKLOAD_MANAGER_NAMESPACE` | Yes | Kubernetes namespace for runner jobs (must exist) |
| `ZENML_KUBERNETES_WORKLOAD_MANAGER_SERVICE_ACCOUNT` | Yes | Kubernetes service account for runner jobs (must exist) |

**Implementation source values:**
- `zenml_cloud_plugins.kubernetes_workload_manager.KubernetesWorkloadManager`
- `zenml_cloud_plugins.aws_kubernetes_workload_manager.AWSKubernetesWorkloadManager`
- `zenml_cloud_plugins.gcp_kubernetes_workload_manager.GCPKubernetesWorkloadManager`

**Runner image configuration:**

| Variable | Required | Description |
|----------|----------|-------------|
| `ZENML_KUBERNETES_WORKLOAD_MANAGER_BUILD_RUNNER_IMAGE` | No | Whether to build runner images (default: `false`) |
| `ZENML_KUBERNETES_WORKLOAD_MANAGER_DOCKER_REGISTRY` | Conditional | Registry for runner images (required if building images) |
| `ZENML_KUBERNETES_WORKLOAD_MANAGER_RUNNER_IMAGE` | No | Pre-built runner image (used if not building). Must have all requirements to instantiate the stack. |

**Optional configuration:**

| Variable | Description |
|----------|-------------|
| `ZENML_KUBERNETES_WORKLOAD_MANAGER_ENABLE_EXTERNAL_LOGS` | Store logs externally (default: `false`, AWS only) |
| `ZENML_KUBERNETES_WORKLOAD_MANAGER_POD_RESOURCES` | Pod resources in JSON format |
| `ZENML_KUBERNETES_WORKLOAD_MANAGER_TTL_SECONDS_AFTER_FINISHED` | Cleanup time for finished jobs (default: 2 days) |
| `ZENML_KUBERNETES_WORKLOAD_MANAGER_NODE_SELECTOR` | Node selector in JSON format |
| `ZENML_KUBERNETES_WORKLOAD_MANAGER_TOLERATIONS` | Tolerations in JSON format |
| `ZENML_KUBERNETES_WORKLOAD_MANAGER_JOB_BACKOFF_LIMIT` | Backoff limit for builder/runner jobs |
| `ZENML_KUBERNETES_WORKLOAD_MANAGER_POD_FAILURE_POLICY` | Pod failure policy for builder/runner jobs |
| `ZENML_SERVER_MAX_CONCURRENT_TEMPLATE_RUNS` | Max concurrent snapshot runs per pod (default: 2) |

**AWS-specific variables:**

| Variable | Required | Description |
|----------|----------|-------------|
| `ZENML_AWS_KUBERNETES_WORKLOAD_MANAGER_BUCKET` | Conditional | S3 bucket for logs (required if external logs enabled) |
| `ZENML_AWS_KUBERNETES_WORKLOAD_MANAGER_REGION` | Conditional | AWS region (required if building images) |

### Configuration Examples

**Minimal Kubernetes Configuration:**

```yaml
zenml:
    environment:
        ZENML_SERVER_WORKLOAD_MANAGER_IMPLEMENTATION_SOURCE: zenml_cloud_plugins.kubernetes_workload_manager.KubernetesWorkloadManager
        ZENML_KUBERNETES_WORKLOAD_MANAGER_NAMESPACE: zenml-workspace-namespace
        ZENML_KUBERNETES_WORKLOAD_MANAGER_SERVICE_ACCOUNT: zenml-workspace-service-account
```

**Full AWS Configuration:**

```yaml
zenml:
    environment:
        ZENML_SERVER_WORKLOAD_MANAGER_IMPLEMENTATION_SOURCE: zenml_cloud_plugins.aws_kubernetes_workload_manager.AWSKubernetesWorkloadManager
        ZENML_KUBERNETES_WORKLOAD_MANAGER_NAMESPACE: zenml-workspace-namespace
        ZENML_KUBERNETES_WORKLOAD_MANAGER_SERVICE_ACCOUNT: zenml-workspace-service-account
        ZENML_KUBERNETES_WORKLOAD_MANAGER_BUILD_RUNNER_IMAGE: "true"
        ZENML_KUBERNETES_WORKLOAD_MANAGER_DOCKER_REGISTRY: 339712793861.dkr.ecr.eu-central-1.amazonaws.com
        ZENML_KUBERNETES_WORKLOAD_MANAGER_ENABLE_EXTERNAL_LOGS: "true"
        ZENML_KUBERNETES_WORKLOAD_MANAGER_POD_RESOURCES: '{"requests": {"cpu": "100m", "memory": "400Mi"}, "limits": {"memory": "700Mi"}}'
        ZENML_AWS_KUBERNETES_WORKLOAD_MANAGER_BUCKET: s3://my-bucket/run-template-logs
        ZENML_AWS_KUBERNETES_WORKLOAD_MANAGER_REGION: eu-central-1
        ZENML_KUBERNETES_WORKLOAD_MANAGER_NODE_SELECTOR: '{"node-pool": "zenml-pool"}'
        ZENML_KUBERNETES_WORKLOAD_MANAGER_TOLERATIONS: '[{"key": "node-pool", "operator": "Equal", "value": "zenml-pool", "effect": "NoSchedule"}]'
        ZENML_SERVER_MAX_CONCURRENT_TEMPLATE_RUNS: 10
```

**Full GCP Configuration:**

```yaml
zenml:
    environment:
        ZENML_SERVER_WORKLOAD_MANAGER_IMPLEMENTATION_SOURCE: zenml_cloud_plugins.gcp_kubernetes_workload_manager.GCPKubernetesWorkloadManager
        ZENML_KUBERNETES_WORKLOAD_MANAGER_NAMESPACE: zenml-workspace-namespace
        ZENML_KUBERNETES_WORKLOAD_MANAGER_SERVICE_ACCOUNT: zenml-workspace-service-account
        ZENML_KUBERNETES_WORKLOAD_MANAGER_BUILD_RUNNER_IMAGE: "true"
        ZENML_KUBERNETES_WORKLOAD_MANAGER_DOCKER_REGISTRY: europe-west3-docker.pkg.dev/zenml-project/zenml-snapshots/zenml
        ZENML_KUBERNETES_WORKLOAD_MANAGER_POD_RESOURCES: '{"requests": {"cpu": "100m", "memory": "400Mi"}, "limits": {"memory": "700Mi"}}'
        ZENML_KUBERNETES_WORKLOAD_MANAGER_NODE_SELECTOR: '{"node-pool": "zenml-pool"}'
        ZENML_KUBERNETES_WORKLOAD_MANAGER_TOLERATIONS: '[{"key": "node-pool", "operator": "Equal", "value": "zenml-pool", "effect": "NoSchedule"}]'
        ZENML_SERVER_MAX_CONCURRENT_TEMPLATE_RUNS: 10
```

### Kubernetes RBAC

The service account needs these permissions in the workload manager namespace:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: zenml-workload-manager
  namespace: zenml-workspace-namespace
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["create", "get", "list", "delete", "patch"]
- apiGroups: [""]
  resources: ["pods/logs"]
  verbs: ["get"]
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get"]
- apiGroups: [""]
  resources: ["persistentvolumeclaims"]
  verbs: ["create", "get", "delete"]
```

## High Availability

For production deployments, consider multiple replicas (2+) behind a load balancer, database replication with read replicas, liveness/readiness probes, and auto-scaling based on CPU/memory utilization.

## Related Documentation

- [System Architecture](system-architecture.md) - How components interact
- [Control Plane Configuration](config-control-plane.md) - Configure the Control Plane
- [Upgrades - Workspace Server](upgrades-workspace-server.md) - How to upgrade the Workspace Server

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
