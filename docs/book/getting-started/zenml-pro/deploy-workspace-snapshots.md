---
description: Enable snapshot support for self-hosted ZenML Pro workspaces
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

# Enable Snapshot (Workload Manager) Support for the Workspace Server

The Workspace Server includes a Workload Manager feature that allows running pipelines directly from the ZenML Pro UI. This feature requires access to a Kubernetes cluster where ad-hoc pipeline runner pods can be created.

{% hint style="warning" %}
Snapshots are only available from ZenML Pro Workspace Server version 0.90.0 onwards
{% endhint %}

## Prerequisites

Basic requirements:
- Kubernetes cluster (1.24+) accessible from the workspace server
- Dedicated namespace for runner pods
- Service accounts with RBAC permissions to create/manage pods
- Image pull secrets for the service accounts

### Understanding Snapshot Sub-features

Running pipelines from the UI relies on running Kubernetes jobs (aka "runner" jobs) that are responsible for launching the pipelines in the same manner as when running them from the CLI or SDK. These jobs need to use container images with the correct Python package dependencies to be able to launch the pipelines. There are several ways to achieve this and you'll need to choose the one that best fits your needs:

1. **Reuse snapshot container images**: the same pipeline container images that are built for the snapshot being run can also be used for the "runner" jobs. For this to work, you have to grant the "runner" jobs pull access to all container registries where these images are stored (i.e. the Container Registries used in your ZenML Stacks).
2. **Build "runner" container images on-demand**: in this variant, the Workspace Server will launch additional Kubernetes jobs to build the "runner" images when needed and push them to a configured container registry. It requires these "builder" Kubernetes jobs to have push permissions to a private container registry and the "runner" jobs to have pull access to the same container registry.
3. **Use pre-built "runner" image**: you can provide a single pre-built "runner" image (stored by you in a container registry) for all runs. This is the simplest and fastest option, but you have to ensure that the image has all the correct Python package dependencies to be able to launch the pipelines.

**Store logs externally**: By default, logs shown in the ZenML Pro UI are extracted from the "runner" job pods. Since pods may disappear, you can configure external log storage where these logs will be stored. Currently, this is only supported with the AWS implementation. If you enable this, you need to configure the S3 bucket and region where the logs will be stored and grant the ZenML Pro Workspace Server pods write access to this bucket.

| Implementation | Platform | Use Case |
|---------------|----------|----------|
| `KubernetesWorkloadManager` | Any Kubernetes (EKS, GKE, AKS, self-managed) | Standard setup, fast minimalistic configuration |
| `AWSKubernetesWorkloadManager` | EKS | AWS-native with ECR image building and S3 log storage |
| `GCPKubernetesWorkloadManager` | GKE | GCP-native with GCR support (GCS log storage planned) |

### 1. Create Kubernetes Resources for Workload Manager

Create a dedicated namespace and service account for runner jobs:

```bash
# Create namespace
kubectl create namespace zenml-workspace-namespace

# Create service account
kubectl -n zenml-workspace-namespace create serviceaccount zenml-workspace-service-account

# Create role with permissions to create jobs and access registry
# (Specific permissions depend on your implementation choice below)
```

The service account needs permissions to build images and run jobs, including access to container images and any configured bucket for logs.

### 2. Choose Implementation

There are three available implementations:

* **Kubernetes**: Runs pipelines in the same Kubernetes cluster as the ZenML Pro workspace server.
* **AWS**: Extends Kubernetes implementation to build/push images to AWS ECR and store logs in AWS S3.
* **GCP**: Currently same as Kubernetes, with plans to extend for GCP GCR and GCS support.

**Option A: Kubernetes Implementation (Simplest)**

Use the built-in Kubernetes implementation for running snapshots:

```yaml
zenml:
    environment:
        ZENML_SERVER_WORKLOAD_MANAGER_IMPLEMENTATION_SOURCE: zenml_cloud_plugins.kubernetes_workload_manager.KubernetesWorkloadManager
        ZENML_KUBERNETES_WORKLOAD_MANAGER_NAMESPACE: zenml-workspace-namespace
        ZENML_KUBERNETES_WORKLOAD_MANAGER_SERVICE_ACCOUNT: zenml-workspace-service-account
```

**Option B: AWS Implementation (Full Featured)**

For AWS-specific features including external logs and ECR integration:

```yaml
zenml:
    environment:
        ZENML_SERVER_WORKLOAD_MANAGER_IMPLEMENTATION_SOURCE: zenml_cloud_plugins.aws_kubernetes_workload_manager.AWSKubernetesWorkloadManager
        ZENML_KUBERNETES_WORKLOAD_MANAGER_NAMESPACE: zenml-workspace-namespace
        ZENML_KUBERNETES_WORKLOAD_MANAGER_SERVICE_ACCOUNT: zenml-workspace-service-account
```

**Option C: GCP Implementation**

For GCP environments:

```yaml
zenml:
    environment:
        ZENML_SERVER_WORKLOAD_MANAGER_IMPLEMENTATION_SOURCE: zenml_cloud_plugins.gcp_kubernetes_workload_manager.GCPKubernetesWorkloadManager
        ZENML_KUBERNETES_WORKLOAD_MANAGER_NAMESPACE: zenml-workspace-namespace
        ZENML_KUBERNETES_WORKLOAD_MANAGER_SERVICE_ACCOUNT: zenml-workspace-service-account
```

### 3. Configure Runner Image

Choose how runner images are managed:

**Option A: Use Pre-built Runner Image (Simpler for Air-gap)**

```yaml
zenml:
    environment:
        ZENML_KUBERNETES_WORKLOAD_MANAGER_BUILD_RUNNER_IMAGE: "false"
        ZENML_KUBERNETES_WORKLOAD_MANAGER_RUNNER_IMAGE: internal-registry.mycompany.com/zenml/zenml:<ZENML_OSS_VERSION>
```

Pre-build your runner image and push to your internal registry. Note that this image needs to have all requirements installed to instantiate the stack that will be used for the template run.

**Option B: Have ZenML Build Runner Images**

Requires access to internal Docker registry with push permissions:

```yaml
zenml:
    environment:
        ZENML_KUBERNETES_WORKLOAD_MANAGER_BUILD_RUNNER_IMAGE: "true"
        ZENML_KUBERNETES_WORKLOAD_MANAGER_DOCKER_REGISTRY: internal-registry.mycompany.com/zenml
```

### 4. Environment Variable Reference

All supported environment variables for workload manager configuration:

| Variable | Required | Description |
|----------|----------|-------------|
| `ZENML_SERVER_WORKLOAD_MANAGER_IMPLEMENTATION_SOURCE` | Yes | Implementation class (see options above) |
| `ZENML_KUBERNETES_WORKLOAD_MANAGER_NAMESPACE` | Yes | Kubernetes namespace for runner jobs |
| `ZENML_KUBERNETES_WORKLOAD_MANAGER_SERVICE_ACCOUNT` | Yes | Kubernetes service account for runner jobs |
| `ZENML_KUBERNETES_WORKLOAD_MANAGER_BUILD_RUNNER_IMAGE` | No | Whether to build runner images (default: `false`) |
| `ZENML_KUBERNETES_WORKLOAD_MANAGER_DOCKER_REGISTRY` | Conditional | Registry for runner images (required if building images) |
| `ZENML_KUBERNETES_WORKLOAD_MANAGER_RUNNER_IMAGE` | No | Pre-built runner image (used if not building) |
| `ZENML_KUBERNETES_WORKLOAD_MANAGER_ENABLE_EXTERNAL_LOGS` | No | Store logs externally (default: `false`, AWS only) |
| `ZENML_KUBERNETES_WORKLOAD_MANAGER_POD_RESOURCES` | No | Pod resources in JSON format |
| `ZENML_KUBERNETES_WORKLOAD_MANAGER_TTL_SECONDS_AFTER_FINISHED` | No | Cleanup time for finished jobs (default: 2 days) |
| `ZENML_KUBERNETES_WORKLOAD_MANAGER_NODE_SELECTOR` | No | Node selector in JSON format |
| `ZENML_KUBERNETES_WORKLOAD_MANAGER_TOLERATIONS` | No | Tolerations in JSON format |
| `ZENML_KUBERNETES_WORKLOAD_MANAGER_JOB_BACKOFF_LIMIT` | No | Backoff limit for builder/runner jobs |
| `ZENML_KUBERNETES_WORKLOAD_MANAGER_POD_FAILURE_POLICY` | No | Pod failure policy for builder/runner jobs |
| `ZENML_SERVER_MAX_CONCURRENT_TEMPLATE_RUNS` | No | Max concurrent snapshot runs per pod (default: 2) |

**AWS-specific variables:**

| Variable | Required | Description |
|----------|----------|-------------|
| `ZENML_AWS_KUBERNETES_WORKLOAD_MANAGER_BUCKET` | Conditional | S3 bucket for logs (required if external logs enabled) |
| `ZENML_AWS_KUBERNETES_WORKLOAD_MANAGER_REGION` | Conditional | AWS region (required if building images) |

### 5. Complete Configuration Examples

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

**Air-gapped Configuration with Pre-built Runner:**

```yaml
zenml:
    environment:
        ZENML_SERVER_WORKLOAD_MANAGER_IMPLEMENTATION_SOURCE: zenml_cloud_plugins.kubernetes_workload_manager.KubernetesWorkloadManager
        ZENML_KUBERNETES_WORKLOAD_MANAGER_NAMESPACE: zenml-workspace-namespace
        ZENML_KUBERNETES_WORKLOAD_MANAGER_SERVICE_ACCOUNT: zenml-workspace-service-account
        ZENML_KUBERNETES_WORKLOAD_MANAGER_BUILD_RUNNER_IMAGE: "false"
        ZENML_KUBERNETES_WORKLOAD_MANAGER_RUNNER_IMAGE: internal-registry.mycompany.com/zenml/zenml:<ZENML_OSS_VERSION>
        ZENML_KUBERNETES_WORKLOAD_MANAGER_POD_RESOURCES: '{"requests": {"cpu": "100m", "memory": "400Mi"}, "limits": {"memory": "700Mi"}}'
        ZENML_KUBERNETES_WORKLOAD_MANAGER_TTL_SECONDS_AFTER_FINISHED: 86400
        ZENML_SERVER_MAX_CONCURRENT_TEMPLATE_RUNS: 2
```

### 6. Update Workspace Deployment

Update your workspace server Helm values with workload manager configuration and redeploy:

```bash
helm upgrade zenml ./zenml-<version>.tgz \
  --namespace zenml-workspace \
  --values zenml-workspace-values.yaml
```

## Related Resources

- [Self-hosted Deployment Overview](self-hosted-deployment.md)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Helm Documentation](https://helm.sh/docs/)

