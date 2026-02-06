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

### Understanding Workload Manager Sub-features

Running pipelines from the UI relies on running Kubernetes jobs (aka "runner" jobs) that are responsible for launching the pipelines in the same manner as when running them from the CLI or SDK. These jobs need to use container images with the correct Python package dependencies to be able to launch the pipelines. There are several ways to achieve this and you'll need to choose the one that best fits your needs:

1. **Reuse snapshot container images**: the same pipeline container images that are built for the snapshot being run can also be used for the "runner" jobs. For this to work, you have to grant the "runner" jobs pull access to all container registries where these images are stored (i.e. the Container Registries used in your ZenML Stacks). This option allows running only snapshots associated with stacks that include the same container registry.

2. **Build "runner" container images on-demand**: in this variant, the Workspace Server will launch additional Kubernetes jobs to build the "runner" images when needed and push them to a configured container registry. It requires these "builder" Kubernetes jobs to have push permissions to a private container registry and the "runner" jobs to have pull access to the same container registry. This option is the most flexible and allows running snapshots associated with any stack and any integration.

3. **Use pre-built "runner" image**: you can provide a single pre-built "runner" image (stored by you in a container registry) for all runs. This is the simplest and fastest option, but you have to ensure that the image has all the correct Python package dependencies to be able to launch the pipelines. This option is the most limited and requires you to pre-build a container image that contains all the dependencies for all possible stacks and integrations used by your pipelines.

**Store logs externally**: By default, logs shown in the ZenML Pro UI are extracted from the "runner" job pods. Since pods may disappear, you can configure external log storage where these logs will be stored. Currently, this is only supported with the AWS implementation. If you enable this, you need to configure the S3 bucket and region where the logs will be stored and grant the ZenML Pro Workspace Server pods write access to this bucket.

There are three available Workload Manager implementations:

* **Kubernetes**: Runs pipelines in the same Kubernetes cluster as the ZenML Pro workspace server.
* **AWS**: Extends the Kubernetes implementation to build/push images to AWS ECR and store logs in AWS S3.

### 1. Create Kubernetes Resources for the Workload Manager

Create a dedicated namespace and service account where the runner jobs will be launched.

```bash
# Create namespace
kubectl create namespace zenml-workload-manager

# Create service account
kubectl -n zenml-workload-manager create serviceaccount zenml-workload-manager
```

### 2. Choose Implementation

Your choice of implementation will determine the additional environment variables you need to configure in the ZenML Workspace Server Helm deployment: 

**Option A: Kubernetes Implementation (Basic)**

Provides generic Kubernetes functionality to run snapshots.

```yaml
zenml:
    environment:
        ZENML_SERVER_WORKLOAD_MANAGER_IMPLEMENTATION_SOURCE: zenml_cloud_plugins.kubernetes_workload_manager.KubernetesWorkloadManager
        ZENML_KUBERNETES_WORKLOAD_MANAGER_NAMESPACE: zenml-workload-manager
        ZENML_KUBERNETES_WORKLOAD_MANAGER_SERVICE_ACCOUNT: zenml-workload-manager
```

**Option B: AWS Implementation**

Provides AWS-specific features including external S3 logs and ECR integration.

```yaml
zenml:
    environment:
        ZENML_SERVER_WORKLOAD_MANAGER_IMPLEMENTATION_SOURCE: zenml_cloud_plugins.aws_kubernetes_workload_manager.AWSKubernetesWorkloadManager
        ZENML_KUBERNETES_WORKLOAD_MANAGER_NAMESPACE: zenml-workload-manager
        ZENML_KUBERNETES_WORKLOAD_MANAGER_SERVICE_ACCOUNT: zenml-workload-manager
        ZENML_AWS_KUBERNETES_WORKLOAD_MANAGER_REGION: eu-central-1
        # To enable storing logs externally in S3, also set the following environment variables:
        ZENML_KUBERNETES_WORKLOAD_MANAGER_ENABLE_EXTERNAL_LOGS: "true"
        ZENML_AWS_KUBERNETES_WORKLOAD_MANAGER_BUCKET: s3://my-bucket/run-template-logs
```

### 3. Configure the Runner Image Source

Choose how runner images are managed. Your choice of implementation will determine the additional environment variables you need to configure in the ZenML Workspace Server Helm deployment: 

**Option 1: Reuse snapshot container images**

Reuse the container images built for the snapshot being run.

```yaml
zenml:
    environment:
        ZENML_KUBERNETES_WORKLOAD_MANAGER_BUILD_RUNNER_IMAGE: "false"
        # Keep this empty or skip setting it to reuse the snapshot container images
        # ZENML_KUBERNETES_WORKLOAD_MANAGER_RUNNER_IMAGE:
```

**Option 2: Have ZenML Build Runner Images**

Build the runner images on-demand.

```yaml
zenml:
    environment:
        ZENML_KUBERNETES_WORKLOAD_MANAGER_BUILD_RUNNER_IMAGE: "true"
        ZENML_KUBERNETES_WORKLOAD_MANAGER_DOCKER_REGISTRY: internal-registry.mycompany.com/zenml
```

**Option 3: Use a Pre-built Runner Image**

Use a pre-built runner image for all runs.

```yaml
zenml:
    environment:
        ZENML_KUBERNETES_WORKLOAD_MANAGER_BUILD_RUNNER_IMAGE: "false"
        ZENML_KUBERNETES_WORKLOAD_MANAGER_RUNNER_IMAGE: internal-registry.mycompany.com/zenml/zenml:<ZENML_OSS_VERSION>
```

### 4. Configure Permissions

The Kubernetes service account running the ZenML Workspace Server needs additional permissions:

* permissions to create jobs in the workload manager Kubernetes namespace set up in step 1.
 to build images and run jobs, including access to container images and any configured bucket for logs.
* if the AWS implementation is used and external S3 logs are enabled, permissions to write to the configured S3 bucket.

The workload manager Kubernetes service account set up in step 1 also needs the following container registry permissions:
* permissions to pull images from the container registry where the runner images are stored.
* if the option to build runner images on-demand is chosen, permissions to push images to the container registry where the runner images will be pushed.

Granting these permissions can be achieved in several ways:

    * grant the entire cluster access to the container registry
    * use implicit workload identity access to the container registry - available in most cloud providers by granting the Kubernetes service account access to the container registry
    * configure a service account with implicit access to the container registry - associating some cloud service identity (e.g. a GCP service account, an AWS IAM role, etc.) with the Kubernetes service account
    * configure an image pull secret for the service account - similar to the previous option, but using a Kubernetes secret instead of a cloud service identity

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

**Configuration with a Pre-built Runner Image:**

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

