---
description: Understand workload managers and how they enable running pipelines from the dashboard.
---

# Workload Managers

Workload managers are built into the ZenML Pro server container. They enable you to run pipeline snapshots directly from the dashboard by allowing the server to orchestrate pipeline execution on your infrastructure. Without a workload manager configured, your workspace can only be used for monitoring and analyzing completed pipeline runs. With one configured, you gain the ability to trigger and execute pipelines interactively.

This feature is available in [all ZenML Pro deployment scenarios](deployments-overview.md) (SaaS, Hybrid, and Air-gapped).

## Architecture

The ZenML Pro server container includes workload manager implementations. You configure which implementation to use through environment variables passed to the server. The server then uses that implementation to coordinate pipeline execution with your infrastructure.

### Execution Flow

1. **User triggers a snapshot from the dashboard**: You select a pipeline snapshot and click "Run" in the ZenML Cloud interface.
2. **ZenML server receives the request**: Your ZenML Pro server (running in your workspace, whether SaaS, Hybrid, or Air-gapped) receives the execution request.
3. **Workload manager implementation handles orchestration**: The configured workload manager implementation (Kubernetes, AWS, or GCP) translates the request into infrastructure-specific commands.
4. **Runner pod/task is created**: The workload manager creates a Kubernetes pod, ECS task, or equivalent compute unit on your infrastructure.
5. **Pipeline executes**: The runner pulls the pipeline code, executes the steps, and streams logs back to the workspace.
6. **Results are captured**: Artifacts, metrics, and run metadata are stored in your configured artifact store and metadata backend.

## How Workload Managers Are Configured

Workload managers are enabled by setting environment variables on the ZenML Pro server container. Each implementation requires a specific set of environment variables that tell the server:

- Which workload manager implementation to use
- Where to create runner pods/tasks (namespace, cluster, region)
- How to access container registries and storage
- What permissions and resources runners should have

All configuration happens within a single server deployment—no separate services are needed.

## Supported Implementations

ZenML Pro supports three workload manager implementations:

### 1. Kubernetes Workload Manager

The simplest implementation, suitable for any Kubernetes cluster (EKS, GKE, AKS, self-managed).

**Environment Variables:**

```yaml
ZENML_SERVER_WORKLOAD_MANAGER_IMPLEMENTATION_SOURCE: zenml_cloud_plugins.kubernetes_workload_manager.KubernetesWorkloadManager
ZENML_KUBERNETES_WORKLOAD_MANAGER_NAMESPACE: zenml-workload-manager
ZENML_KUBERNETES_WORKLOAD_MANAGER_SERVICE_ACCOUNT: zenml-runner
ZENML_KUBERNETES_WORKLOAD_MANAGER_RUNNER_IMAGE: 715803424590.dkr.ecr.eu-central-1.amazonaws.com/zenml-pro-server:0.73.0
ZENML_KUBERNETES_WORKLOAD_MANAGER_POD_RESOURCES: '{"requests": {"cpu": "500m", "memory": "512Mi"}, "limits": {"cpu": "2000m", "memory": "2Gi"}}'
ZENML_KUBERNETES_WORKLOAD_MANAGER_TTL_SECONDS_AFTER_FINISHED: 86400
ZENML_SERVER_MAX_CONCURRENT_TEMPLATE_RUNS: 5
```

**Requirements:**
- Kubernetes cluster (1.24+)
- Service account with permissions to create/manage pods in a dedicated namespace
- Network connectivity from cluster to your ZenML server
- Access to a container registry with ZenML runner images

**How it works:**
- The server uses the Kubernetes API to create pods in the specified namespace
- Pods run under the specified service account, inheriting cluster network access
- Completed pods are automatically cleaned up after the TTL expires

**Use cases:**
- Self-managed ZenML servers on Kubernetes (Hybrid or Air-gapped)
- Teams already running Kubernetes infrastructure
- Minimal setup complexity

### 2. AWS Kubernetes Workload Manager

A specialized implementation for EKS that integrates with AWS services (ECR for images, S3 for logs, IAM for permissions).

**Environment Variables:**

```yaml
ZENML_SERVER_WORKLOAD_MANAGER_IMPLEMENTATION_SOURCE: zenml_cloud_plugins.aws_kubernetes_workload_manager.AWSKubernetesWorkloadManager
ZENML_KUBERNETES_WORKLOAD_MANAGER_NAMESPACE: zenml-workload-manager
ZENML_KUBERNETES_WORKLOAD_MANAGER_SERVICE_ACCOUNT: zenml-runner
ZENML_KUBERNETES_WORKLOAD_MANAGER_BUILD_RUNNER_IMAGE: "true"
ZENML_KUBERNETES_WORKLOAD_MANAGER_DOCKER_REGISTRY: <your-ecr-registry>
ZENML_KUBERNETES_WORKLOAD_MANAGER_ENABLE_EXTERNAL_LOGS: "true"
ZENML_AWS_KUBERNETES_WORKLOAD_MANAGER_BUCKET: s3://your-bucket/zenml-logs
ZENML_AWS_KUBERNETES_WORKLOAD_MANAGER_REGION: us-east-1
ZENML_KUBERNETES_WORKLOAD_MANAGER_POD_RESOURCES: '{"requests": {"cpu": "500m", "memory": "512Mi"}, "limits": {"cpu": "2000m", "memory": "2Gi"}}'
ZENML_KUBERNETES_WORKLOAD_MANAGER_TTL_SECONDS_AFTER_FINISHED: 86400
ZENML_SERVER_MAX_CONCURRENT_TEMPLATE_RUNS: 5
```

**Requirements:**
- EKS cluster
- IAM role for the workspace with permissions to access EKS, ECR, and S3
- Docker registry (ECR) for storing runner images
- S3 bucket for exporting logs

**How it works:**
- The server assumes an IAM role to access AWS services
- Runner images are stored and pulled from ECR
- Pod permissions are managed through IAM roles for service accounts (IRSA)
- Logs are streamed to S3 for long-term retention and analysis

**Use cases:**
- AWS-centric environments with EKS
- Need for image building and custom runner management
- Centralized log aggregation in S3
- Fine-grained IAM-based access control

### 3. GCP Kubernetes Workload Manager

Similar to AWS implementation but integrated with GCP services (GCR for images, Cloud Logging for logs).

**Environment Variables:**

```yaml
ZENML_SERVER_WORKLOAD_MANAGER_IMPLEMENTATION_SOURCE: zenml_cloud_plugins.gcp_kubernetes_workload_manager.GCPKubernetesWorkloadManager
ZENML_KUBERNETES_WORKLOAD_MANAGER_NAMESPACE: zenml-workload-manager
ZENML_KUBERNETES_WORKLOAD_MANAGER_SERVICE_ACCOUNT: zenml-runner
ZENML_KUBERNETES_WORKLOAD_MANAGER_BUILD_RUNNER_IMAGE: "true"
ZENML_KUBERNETES_WORKLOAD_MANAGER_DOCKER_REGISTRY: <your-gcr-registry>
ZENML_KUBERNETES_WORKLOAD_MANAGER_POD_RESOURCES: '{"requests": {"cpu": "500m", "memory": "512Mi"}, "limits": {"cpu": "2000m", "memory": "2Gi"}}'
ZENML_KUBERNETES_WORKLOAD_MANAGER_TTL_SECONDS_AFTER_FINISHED: 86400
ZENML_SERVER_MAX_CONCURRENT_TEMPLATE_RUNS: 5
```

**Requirements:**
- GKE cluster
- Service account with permissions to access GKE, GCR, and Cloud Logging
- Docker registry (GCR) for storing runner images

**How it works:**
- The server authenticates to GCP using a service account
- Runner images are stored and pulled from GCR
- Pod permissions are managed through Workload Identity
- Logs are automatically sent to Cloud Logging

**Use cases:**
- GCP-centric environments with GKE
- Leveraging GCP's managed services and Cloud Logging
- Integration with Google Cloud monitoring and observability tools

## IAM Permissions and Service Accounts

Proper permission configuration is critical for workload managers to function correctly. The ZenML Pro server needs sufficient permissions to create and manage runner pods without being overly permissive.

### Kubernetes Service Account

For Kubernetes-based implementations, the server uses a Kubernetes service account to interact with your cluster.

**Required RBAC permissions:**
- Create pods in the designated namespace
- Get/list pods (for monitoring runner status)
- Delete pods (for cleanup after runs complete)
- Get pod logs
- Create, get, patch, delete persistent volume claims (if using persistent storage)
- Get secrets in the namespace (for accessing runner credentials)

**Example RBAC role:**

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: zenml-workload-manager
  namespace: zenml-workload-manager
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

### AWS IAM Role

For AWS-based implementations, the ZenML Pro server container needs an IAM role (typically via IRSA—IAM roles for service accounts) to access EKS and related AWS services.

**Required permissions:**

**EKS cluster access:**
- `eks:DescribeCluster` - Retrieve cluster details
- `eks:ListClusters` - List available clusters

**Pod creation and management (via Kubernetes API using IRSA):**
- The IAM role must be associated with a Kubernetes service account
- The role is assumed by pods running under that service account
- This allows the ZenML server to access the Kubernetes API

**ECR (if building images):**
- `ecr:DescribeRepositories` - List image repositories
- `ecr:BatchCheckLayerAvailability` - Check for existing layers
- `ecr:GetDownloadUrlForLayer` - Download layer data
- `ecr:BatchGetImage` - Retrieve images
- `ecr:PutImage` - Push images to registry

**S3 (for log export):**
- `s3:PutObject` - Write logs to bucket
- `s3:GetObject` - Read logs from bucket
- `s3:ListBucket` - List log files

**Example IAM policy:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eks:DescribeCluster",
        "eks:ListClusters"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:DescribeRepositories"
      ],
      "Resource": "arn:aws:ecr:region:account:repository/zenml-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::your-log-bucket",
        "arn:aws:s3:::your-log-bucket/*"
      ]
    }
  ]
}
```

### GCP Service Account

For GCP-based implementations, the ZenML Pro server uses a GCP service account with appropriate roles.

**Required roles:**
- `roles/container.developer` - Access to create and manage pods in GKE
- `roles/storage.admin` (or more restrictive) - Access to GCR for image operations
- `roles/logging.logWriter` - Write logs to Cloud Logging

**Permissions by service:**

**GKE pod management:**
- `container.operations.create`
- `container.operations.get`
- `container.pods.create`
- `container.pods.get`
- `container.pods.list`
- `container.pods.delete`

**GCR image access:**
- `storage.buckets.get`
- `storage.objects.create`
- `storage.objects.get`
- `storage.objects.list`
- `storage.objects.delete`

**Cloud Logging:**
- `logging.logEntries.create`

## General Considerations

When configuring workload managers, keep these factors in mind:

### Network Connectivity

- **Egress from server to Kubernetes API**: The ZenML Pro server must have network access to your Kubernetes cluster's API server (port 6443 by default)
- **Egress from runners to server**: Runner pods must have network access to your ZenML server (cloud.zenml.io for SaaS, your custom domain for Hybrid/Air-gapped, port 443)
- **Artifact storage access**: Runners need network access to your artifact store (S3, GCS, Azure Blob, local NFS, etc.)
- **Metadata backend access**: Runners need to reach your database for metadata operations
- **Container registry access**: Runners need to pull images from your container registry

For air-gapped deployments, ensure all dependencies are available internally:
- Private container registry with runner images
- Internal artifact storage accessible from runners
- Internal database (no external connectivity required)
- Kubernetes API accessible from the server container

### Resource Configuration

Configure appropriate resources for runner pods:

- **CPU requests/limits**: Depends on pipeline complexity; start with 500m requests and 2000m limits, adjust based on workload profiling
- **Memory requests/limits**: Typical range is 512Mi to 2Gi; larger for data-intensive workloads
- **Ephemeral storage**: Consider temporary storage for intermediate pipeline data
- **Pod disruption budget**: For production deployments, define minimum available pods to prevent service disruption

The `ZENML_KUBERNETES_WORKLOAD_MANAGER_POD_RESOURCES` environment variable controls these settings for all runner pods.

### Image Management

Runner pods need access to container images:

- **Pre-built images**: ZenML provides official runner images in its public ECR registry (715803424590.dkr.ecr.eu-central-1.amazonaws.com)
- **Custom images**: For air-gapped setups, pull images into your private registry before deployment
- **Image pull secrets**: Configure if your registry requires authentication
- **Regular updates**: Keep runner images up-to-date for security and compatibility
- **Image building**: For AWS and GCP implementations, set `ZENML_KUBERNETES_WORKLOAD_MANAGER_BUILD_RUNNER_IMAGE: "true"` to allow the server to build custom images

### Logging and Observability

- **Log collection**: Logs can be streamed to S3 (AWS), Cloud Logging (GCP), or local storage
- **Monitoring**: Use your infrastructure's native monitoring (CloudWatch, Cloud Monitoring, Prometheus)
- **Pod events**: Kubernetes events track pod creation, scheduling, and termination
- **Execution tracing**: ZenML captures step-level execution metadata for debugging
- **Enable external logs**: Use `ZENML_KUBERNETES_WORKLOAD_MANAGER_ENABLE_EXTERNAL_LOGS: "true"` for AWS implementation

### Isolation and Security

- **Namespace isolation**: Use dedicated namespaces (e.g., `zenml-workload-manager`) to separate runner pods from other workloads
- **Pod security policies**: Apply network policies to restrict pod communication
- **Secret management**: Use Kubernetes secrets or cloud-native secret managers for runner credentials
- **Service account scoping**: Limit workspace permissions to only what's needed for runner management
- **Image scanning**: Scan runner images for vulnerabilities before deployment
- **RBAC enforcement**: Ensure Kubernetes RBAC policies prevent unauthorized pod creation

### Scaling and Concurrency

Configure limits to prevent resource exhaustion:

- **Concurrent runs**: Set `ZENML_SERVER_MAX_CONCURRENT_TEMPLATE_RUNS` to limit simultaneous executions (typical: 2-10 depending on runner resources and cluster capacity)
- **TTL for completed pods**: Clean up finished pods automatically using `ZENML_KUBERNETES_WORKLOAD_MANAGER_TTL_SECONDS_AFTER_FINISHED` (e.g., 86400 seconds = 24 hours)
- **Pod disruption budgets**: For HA setups, define minimum available pods to ensure service continuity
- **Horizontal Pod Autoscaler (HPA)**: For the ZenML server itself (not runners), consider HPA if handling many concurrent run submissions

### Troubleshooting Common Issues

**Pods fail to start:**
- Check RBAC permissions for the service account: `kubectl auth can-i create pods --as=system:serviceaccount:zenml-workload-manager:zenml-runner -n zenml-workload-manager`
- Verify image pull secrets if using private registries
- Check resource availability (CPU, memory) in cluster
- Review pod events: `kubectl describe pod <pod-name> -n zenml-workload-manager`
- Check server logs for workload manager errors: `kubectl logs -n zenml-workspace deployment/zenml`

**Logs not appearing:**
- Verify server can reach artifact store and database
- Check network connectivity between cluster and server
- Ensure S3/Cloud Logging permissions are correct
- Review pod logs for pipeline execution errors: `kubectl logs <pod-name> -n zenml-workload-manager`

**Server can't reach cluster:**
- Verify network connectivity to Kubernetes API server
- Check credentials/RBAC permissions (especially for Hybrid deployments with OAuth2)
- Confirm service account role bindings are in place
- Test cluster connectivity: `kubectl cluster-info`

**Runners can't reach server:**
- Verify egress network policies allow outbound HTTPS (port 443)
- Check firewall rules for ingress/egress to ZenML server
- Confirm server URL is resolvable and reachable from pods
- Test from pod: `kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- curl https://<server-url>/health`

## Next Steps

- [Set up workload managers in Hybrid deployments](hybrid-deployment-helm.md#step-7-optional-enable-snapshot-support--workload-manager)
- [Configure workload managers in Air-gapped environments](air-gapped-deployment-helm.md#step-13-optional-enable-snapshot-support--workload-manager)
- [Learn about pipeline snapshots](https://docs.zenml.io/concepts/snapshots)

## Related Resources

**Deployment & Infrastructure:**
- [Deployment Scenarios Overview](deployments-overview.md) - Compare SaaS, Hybrid, and Air-gapped options
- [Hybrid SaaS Deployment](hybrid-deployment.md) - Balance control with convenience
- [Air-gapped Deployment](air-gapped-deployment.md) - Complete control and data sovereignty
- [Self-hosted Deployment Guide](self-hosted.md) - Comprehensive deployment reference

**Core Concepts:**
- [Workspaces](workspaces.md) - Isolated environments for teams and projects
- [Organizations](organization.md) - Top-level entity for managing users and teams
- [Roles & Permissions](roles.md) - Control access to workload manager configuration

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
