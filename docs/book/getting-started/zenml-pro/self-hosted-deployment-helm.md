---
description: Deploy ZenML Pro Self-hosted on Kubernetes with Helm - complete self-hosted setup with no external dependencies.
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

# Self-hosted Deployment on Kubernetes with Helm

This guide provides step-by-step instructions for deploying ZenML Pro in a fully air-gapped setup on Kubernetes using Helm charts. In an air-gapped deployment, all components run within your infrastructure with zero external dependencies.

## Architecture Overview

All components run entirely within your Kubernetes cluster and infrastructure:

```
┌──────────────────────────────────────────────────┐
│         Your Air-gapped Infrastructure           │
│                                                  │
│  ┌────────────────────────────────────────────┐ │
│  │     Kubernetes Cluster                     │ │
│  │                                            │ │
│  │  ┌─────────────────────────────────────┐  │ │
│  │  │  ZenML Pro Control Plane            │  │ │
│  │  │  - Authentication & Authorization   │  │ │
│  │  │  - RBAC Management                  │  │ │
│  │  │  - Dashboard                        │  │ │
│  │  └─────────────────────────────────────┘  │ │
│  │                                            │ │
│  │  ┌─────────────────────────────────────┐  │ │
│  │  │  ZenML Workspace Servers            │  │ │
│  │  │  (one or more)                      │  │ │
│  │  └─────────────────────────────────────┘  │ │
│  │                                            │ │
│  │  ┌─────────────────────────────────────┐  │ │
│  │  │  Load Balancer / Ingress            │  │ │
│  │  │  (HTTPS with internal CA)           │  │ │
│  │  └─────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────┘ │
│                                                  │
│  ┌────────────────────────────────────────────┐ │
│  │     MySQL Database                         │ │
│  │     (for metadata storage)                 │ │
│  └────────────────────────────────────────────┘ │
│                                                  │
│  ┌────────────────────────────────────────────┐ │
│  │     Internal Docker Registry               │ │
│  │     (for container images)                 │ │
│  └────────────────────────────────────────────┘ │
│                                                  │
│  ┌────────────────────────────────────────────┐ │
│  │     Object Storage / NFS                   │ │
│  │     (for artifacts & backups)              │ │
│  └────────────────────────────────────────────┘ │
│                                                  │
└──────────────────────────────────────────────────┘
     🔒 Completely Isolated - No External Access
```

## Prerequisites

Before starting, you need:

**Infrastructure:**
- Kubernetes cluster (1.24+) within your air-gapped network
- MySQL database (8.0+) for metadata storage (PostgreSQL also supported for control plane only)
- Internal Docker registry (Harbor, Quay, Artifactory, etc.)
- Load balancer or Ingress controller for HTTPS
- NFS or object storage for artifacts (optional)

**Network:**
- Internal DNS resolution
- TLS certificates signed by your internal CA
- Network connectivity between cluster components

**Tools (on a machine with internet access for initial setup):**
- Docker
- Helm (3.0+)
- Access to pull ZenML Pro images from private registries (credentials from ZenML)

## Step 1: Prepare Offline Artifacts

This step is performed on a machine with internet access, then transferred to your air-gapped environment.

### 1.1 Pull Container Images

On a machine with internet access and access to the ZenML Pro container registries:

1. Authenticate to the ZenML Pro container registries (AWS ECR or GCP Artifact Registry)
   - Use credentials provided by ZenML Support
   - Follow registry-specific authentication procedures

2. Pull all required images:
   - **Pro Control Plane images (AWS ECR):**
     - `715803424590.dkr.ecr.eu-west-1.amazonaws.com/zenml-pro-api:<version>`
     - `715803424590.dkr.ecr.eu-west-1.amazonaws.com/zenml-pro-dashboard:<version>`
   - **Pro Control Plane images (GCP Artifact Registry):**
     - `europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-api:<version>`
     - `europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-dashboard:<version>`
   - **Workspace Server image (AWS ECR):**
     - `715803424590.dkr.ecr.eu-central-1.amazonaws.com/zenml-pro-server:<version>`
   - **Workspace Server image (GCP Artifact Registry):**
     - `europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-server:<version>`
   - **Client image (for pipelines):**
     - `zenmldocker/zenml:<version>`

   Example pull commands (AWS ECR):
   ```bash
   docker pull 715803424590.dkr.ecr.eu-west-1.amazonaws.com/zenml-pro-api:<version>
   docker pull 715803424590.dkr.ecr.eu-west-1.amazonaws.com/zenml-pro-dashboard:<version>
   docker pull 715803424590.dkr.ecr.eu-central-1.amazonaws.com/zenml-pro-server:<version>
   docker pull zenmldocker/zenml:<version>
   ```

   Example pull commands (GCP Artifact Registry):
   ```bash
   docker pull europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-api:<version>
   docker pull europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-dashboard:<version>
   docker pull europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-server:<version>
   docker pull zenmldocker/zenml:<version>
   ```

3. Tag images with your internal registry:
   ```
   internal-registry.mycompany.com/zenml/zenml-pro-api:version
   internal-registry.mycompany.com/zenml/zenml-pro-dashboard:version
   internal-registry.mycompany.com/zenml/zenml-pro-server:version
   internal-registry.mycompany.com/zenml/zenml:version
   ```

4. Save images to tar files for transfer:
   ```bash
   docker save 715803424590.dkr.ecr.eu-west-1.amazonaws.com/zenml-pro-api:<version> > zenml-pro-api.tar
   docker save 715803424590.dkr.ecr.eu-west-1.amazonaws.com/zenml-pro-dashboard:<version> > zenml-pro-dashboard.tar
   docker save 715803424590.dkr.ecr.eu-central-1.amazonaws.com/zenml-pro-server:<version> > zenml-pro-server.tar
   docker save zenmldocker/zenml:<version> > zenml-client.tar
   ```

### 1.2 Download Helm Charts

On the same machine with internet access:

1. Pull the Helm charts:
   - ZenML Pro Control Plane: `oci://public.ecr.aws/zenml/zenml-pro`
   - ZenML Workspace Server: `oci://public.ecr.aws/zenml/zenml`

2. Save charts as `.tgz` files for transfer

{% hint style="info" %}
**Version Synchronization**: The container image tags and the Helm chart versions are synchronized:
- **ZenML Pro Control Plane**: Image tags match the ZenML Pro Helm chart version. Check the [ZenML Pro ArtifactHub repository](https://artifacthub.io/packages/helm/zenml-pro/zenml-pro) for available versions.
- **ZenML Workspace Server**: Image tags match the ZenML OSS Helm chart version. Check the [ZenML OSS ArtifactHub repository](https://artifacthub.io/packages/helm/zenml/zenml) or the [ZenML GitHub releases page](https://github.com/zenml-io/zenml/releases).

When copying images to your internal registry, maintain the same version tags to ensure compatibility between components.
{% endhint %}

### 1.3 Create Offline Bundle

Create a bundle containing all artifacts:

```
zenml-air-gapped-bundle/
├── images/
│   ├── zenml-pro-api.tar
│   ├── zenml-pro-dashboard.tar
│   ├── zenml-pro-server.tar
│   └── zenml-client.tar
├── charts/
│   ├── zenml-pro-<version>.tgz
│   └── zenml-<version>.tgz
└── manifest.txt
```

The manifest should document:
- All image names and versions
- Helm chart versions
- Date of bundle creation
- Required internal registry URLs

## Step 2: Transfer to Air-gapped Environment

Transfer the bundle to your air-gapped environment using approved methods:
- Physical media (USB drive, external drive)
- Approved secure file transfer system
- Air-gap transfer appliances
- Any method compliant with your security policies

## Step 3: Load Images into Internal Registry

In your air-gapped environment, load the images:

1. Extract all tar files:
   ```
   cd images/
   for file in *.tar; do docker load < "$file"; done
   ```

2. Tag images for your internal registry:
   ```
   docker tag 715803424590.dkr.ecr.eu-west-1.amazonaws.com/zenml-pro-api:version internal-registry.mycompany.com/zenml/zenml-pro-api:version
   docker tag 715803424590.dkr.ecr.eu-west-1.amazonaws.com/zenml-pro-dashboard:version internal-registry.mycompany.com/zenml/zenml-pro-dashboard:version
   docker tag 715803424590.dkr.ecr.eu-central-1.amazonaws.com/zenml-pro-server:version internal-registry.mycompany.com/zenml/zenml-pro-server:version
   docker tag zenmldocker/zenml:version internal-registry.mycompany.com/zenml/zenml:version
   ```

3. Push images to your internal registry:
   ```
   docker push internal-registry.mycompany.com/zenml/zenml-pro-api:version
   docker push internal-registry.mycompany.com/zenml/zenml-pro-dashboard:version
   docker push internal-registry.mycompany.com/zenml/zenml-pro-server:version
   docker push internal-registry.mycompany.com/zenml/zenml:version
   ```

## Step 4: Create Kubernetes Secrets

```bash
# Create namespace for ZenML Pro
kubectl create namespace zenml-pro

# Create secret for internal registry credentials (if needed)
kubectl -n zenml-pro create secret docker-registry image-pull-secret \
  --docker-server=internal-registry.mycompany.com \
  --docker-username=<your-username> \
  --docker-password=<your-password>
```

{% hint style="info" %}
If you are using self-signed certificates, it is highly recommended to use the same self-signed CA certificate for all the ZenML Pro services (control plane and workspace servers). This simplifies certificate management - you only need to install one CA certificate system-wide on all client machines, then use it to sign all the TLS certificates for the ZenML Pro services.
{% endhint %}

## Step 5: Set Up Databases

Create database instances (within your air-gapped network):

**Important Database Support:**
- **Control Plane**: Supports both PostgreSQL and MySQL
- **Workspace Servers**: Only support MySQL (PostgreSQL is not supported)

**Configuration:**
- **Accessibility**: Reachable from your Kubernetes cluster
- **Databases**: At least 2 (one for control plane, one for workspace)
- **Users**: Create dedicated database users with permissions
- **Backups**: Configure automated backups to local storage
- **Monitoring**: Enable local log aggregation

**Connection strings needed for later:**
- Control Plane DB (PostgreSQL or MySQL): `postgresql://user:password@db-host:5432/zenml_pro` or `mysql://user:password@db-host:3306/zenml_pro`
- Workspace DB (MySQL only): `mysql://user:password@db-host:3306/zenml_workspace`

## Step 6: Configure Helm Values for Control Plane

Create a file `zenml-pro-values.yaml`:

```yaml
# Set up imagePullSecrets to authenticate to the container registry where the
# ZenML Pro container images are hosted, if necessary (see the previous step)
imagePullSecrets:
  - name: image-pull-secret

# ZenML Pro server related options.
zenml:

  image:
    api:
      # Change this to point to your own container repository or use this for direct ECR access
      repository: internal-registry.mycompany.com/zenml/zenml-pro-api
      # Use this for direct GAR access
      # repository: europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-api
    dashboard:
      # Change this to point to your own container repository or use this for direct ECR access
      repository: internal-registry.mycompany.com/zenml/zenml-pro-dashboard
      # Use this for direct GAR access
      # repository: europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-dashboard

  # The external URL where the ZenML Pro server API and dashboard are reachable.
  #
  # This should be set to a hostname that is associated with the Ingress
  # controller.
  serverURL: https://zenml-pro.internal.mycompany.com

  # Database configuration.
  database:

    # Credentials to use to connect to an external Postgres or MySQL database.
    external:
      
      # The type of the external database service to use:
      # - postgres: use an external Postgres database service.
      # - mysql: use an external MySQL database service.
      type: mysql
    
      # The host of the external database service.
      host: mysql.internal.mycompany.com

      # The username to use to connect to the external database service.
      username: zenml_pro_user

      # The password to use to connect to the external database service.
      password: <secure-password>
      
      # The name of the database to use. Will be created on first run if it
      # doesn't exist.
      #
      # NOTE: if the database user doesn't have permissions to create this
      # database, the database should be created manually before installing
      # the helm chart.
      database: zenml_pro

  ingress:
    enabled: true
    # Use the same hostname configured in `serverURL`
    host: zenml-pro.internal.mycompany.com
```

## Step 7: Deploy ZenML Pro Control Plane

Using the local Helm chart:

```bash
helm install zenml-pro ./zenml-pro-<ZENML_PRO_VERSION>.tgz \
  --namespace zenml-pro \
  --create-namespace \
  --values zenml-pro-values.yaml
```

Verify deployment:

```bash
kubectl -n zenml-pro get pods
kubectl -n zenml-pro get svc
kubectl -n zenml-pro get ingress
```

Wait for all pods to be running and healthy.

## Step 8: Enroll Workspace in Control Plane

Before deploying the workspace server, you must enroll it in the control plane to obtain the necessary enrollment credentials.

1. **Access the Control Plane Dashboard**
   - Navigate to `https://zenml-pro.internal.mycompany.com`
   - Log in with your admin credentials

2. **Create an Organization** (if not already created)
   - Go to Organization settings
   - Create a new organization or use an existing one
   - Note the Organization ID and Name

3. **Enroll the Workspace**
   - Use the enrollment script from the [Self-hosted Deployment Guide](self-hosted.md#enrolling-a-workspace) or
   - Create a workspace through the dashboard and obtain:
     - Enrollment Key
     - Organization ID
     - Organization Name
     - Workspace ID
     - Workspace Name

4. **Save these values** - you'll need them in the next step

## Step 9: Configure Helm Values for Workspace Server

Create a file `zenml-workspace-values.yaml`:

```yaml
zenml:
    analyticsOptIn: false
    threadPoolSize: 20
    database:
        maxOverflow: "-1"
        poolSize: "10"
        # TODO: use the actual database host and credentials
        # Note: Workspace servers only support MySQL, not PostgreSQL
        url: mysql://zenml_workspace_user:password@mysql.internal.mycompany.com:3306/zenml_workspace
    image:
        # TODO: use your actual image repository (omit the tag, which is
        # assumed to be the same as the helm chart version)
        repository: internal-registry.mycompany.com/zenml/zenml-pro-server
    # TODO: use your actual server domain here
    serverURL: https://zenml-workspace.internal.mycompany.com
    ingress:
        enabled: true
        # TODO: use your actual domain here
        host: zenml-workspace.internal.mycompany.com
    pro:
        apiURL: https://zenml-pro.internal.mycompany.com/api/v1
        dashboardURL: https://zenml-pro.internal.mycompany.com
        enabled: true
        enrollmentKey: <enrollment-key-from-control-plane>
        organizationID: <your-organization-id>
        organizationName: <your-organization-name>
        workspaceID: <your-workspace-id>
        workspaceName: <your-workspace-name>
    replicaCount: 1
    secretsStore:
        sql:
            encryptionKey: <generate-a-64-character-hex-key>
        type: sql

# TODO: these are the minimum resources required for the ZenML server. You can
# adjust them to your needs.
resources:
    limits:
        memory: 800Mi
    requests:
        cpu: 100m
        memory: 450Mi
```

## Step 10: Deploy ZenML Workspace Server

```bash
# Deploy workspace
helm install zenml ./zenml-<ZENML_OSS_VERSION>.tgz \
  --namespace zenml-workspace \
  --create-namespace \
  --values zenml-workspace-values.yaml
```

Verify deployment:

```bash
kubectl -n zenml-workspace get pods
kubectl -n zenml-workspace get svc
kubectl -n zenml-workspace get ingress
```

## Step 11: Configure Internal DNS

Update your internal DNS to resolve:
- `zenml-pro.internal.mycompany.com` → Your ALB/Ingress IP
- `zenml-workspace.internal.mycompany.com` → Your ALB/Ingress IP

{% hint style="warning" %}
Always use a fully qualified domain name (FQDN) (e.g. `https://zenml.ml.cluster`). Do not use a simple DNS prefix for the servers (e.g. `https://zenml.cluster` is not recommended). This is especially relevant for the TLS certificates that you prepare for these endpoints. The TLS certificates will not be accepted by some browsers (e.g. Chrome) otherwise.
{% endhint %}

## Step 12: Install Internal CA Certificate

If the TLS certificates used by the ZenML Pro services are signed by a custom Certificate Authority, you need to install the CA certificates on every machine that needs to access the ZenML server.

### System-wide Installation

On all client machines that will access ZenML:

1. Obtain your internal CA certificate
2. Install it in the system certificate store:
   - **Linux**: Copy to `/usr/local/share/ca-certificates/` and run `update-ca-certificates`
   - **macOS**: Use `sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain <cert.pem>`
   - **Windows**: Use `certutil -addstore "Root" cert.pem`

3. For some browsers (e.g., Chrome), updating the system's CA certificates is not enough. You will also need to import the CA certificates into the browser.

4. For Python/ZenML client:
   ```bash
   export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
   ```

### For Containerized Pipelines

When running containerized pipelines with ZenML, you'll need to install the CA certificates into the container images built by ZenML. Customize the build process via [DockerSettings](https://docs.zenml.io/how-to/customize-docker-builds):

1. Create a custom Dockerfile:
   ```dockerfile
   # Use the original ZenML client image as a base image
   FROM zenmldocker/zenml:<zenml-version>

   # Install certificates
   COPY my-custom-ca.crt /usr/local/share/ca-certificates/
   RUN update-ca-certificates

   ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
   ```

2. Build and push the image to your internal registry:
   ```bash
   docker build -t internal-registry.mycompany.com/zenml/zenml:<zenml-version> .
   docker push internal-registry.mycompany.com/zenml/zenml:<zenml-version>
   ```

3. Update your ZenML pipeline code to use the custom image:
   ```python
   from zenml.config import DockerSettings
   from zenml import __version__

   # Define the custom base image
   CUSTOM_BASE_IMAGE = f"internal-registry.mycompany.com/zenml/zenml:{__version__}"

   docker_settings = DockerSettings(
       parent_image=CUSTOM_BASE_IMAGE,
   )

   @pipeline(settings={"docker": docker_settings})
   def my_pipeline() -> None:
       ...
   ```

## Step 13: Verify the Deployment

1. **Check Control Plane Health**
   ```bash
   curl -k https://zenml-pro.internal.mycompany.com/health
   ```

2. **Check Workspace Health**
   ```bash
   curl -k https://zenml-workspace.internal.mycompany.com/health
   ```

3. **Access the Dashboard**
   - Navigate to `https://zenml-pro.internal.mycompany.com` in your browser
   - Log in with admin credentials

4. **Check Logs**
   ```bash
   kubectl -n zenml-pro logs deployment/zenml-pro
   kubectl -n zenml-workspace logs deployment/zenml
   ```

## Step 14: (Optional) Enable Snapshot Support / Workload Manager

Pipeline snapshots (running pipelines from the UI) requires additional configuration.

{% hint style="warning" %}
Snapshots are only available from ZenML workspace server version 0.90.0 onwards.
{% endhint %}

### Understanding Snapshot Sub-features

Snapshots come with optional sub-features that can be turned on or off:

* **Building runner container images**: Running pipelines from the UI relies on Kubernetes jobs ("runner" jobs) that need container images with the correct Python packages. You can:
  - Reuse existing pipeline container images (requires Kubernetes cluster access to those registries)
  - Have ZenML build "runner" images and push to a configured registry
  - Use a single pre-built "runner" image for all runs

* **Store logs externally**: By default, logs are extracted from runner job pods. Since pods may disappear, you can configure external log storage (currently only supported with AWS implementation).

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

## Step 15: Create Users and Organizations

In the ZenML Pro dashboard:

1. Create an organization
2. Create users for your team
3. Assign roles and permissions
4. Configure teams

{% hint style="info" %}
For detailed instructions on creating users programmatically, including Python scripts for batch user creation, see the [Self-hosted Deployment Guide](self-hosted.md#onboard-additional-users).
{% endhint %}

## Step 16: Access the Workspace from ZenML CLI

To login to the workspace with the ZenML CLI, you need to pass the custom ZenML Pro API URL:

```bash
zenml login --pro-api-url https://zenml-pro.internal.mycompany.com/api/v1
```

Alternatively, you can set the `ZENML_PRO_API_URL` environment variable:

```bash
export ZENML_PRO_API_URL=https://zenml-pro.internal.mycompany.com/api/v1
zenml login
```

## Network Requirements Summary

| Traffic | Source | Destination | Port | Direction |
|---------|--------|-------------|------|-----------|
| Web Access | Client Machines | Ingress Controller | 443 | Inbound |
| API Access | ZenML Client | Workspace Server | 443 | Inbound |
| Database | Kubernetes Pods | MySQL | 3306 | Outbound |
| Registry | Kubernetes | Internal Registry | 443 | Outbound |
| Inter-service | Kubernetes Internal | Kubernetes Services | 443 | Internal |

## Scaling & High Availability

### Multiple Control Plane Replicas

```yaml
zenml:
  replicaCount: 3
```

### Multiple Workspace Replicas

```yaml
zenml:
  replicaCount: 2
```

### Pod Disruption Budgets

Protect against accidental disruptions:

```yaml
podDisruptionBudget:
  enabled: true
  minAvailable: 1
```

### Database Replication

For HA, configure MySQL replication:
1. Set up a standby database
2. Configure binary log replication
3. Test failover procedures

## Backup & Recovery

### Automated Backups

Configure automated MySQL backups:
- **Frequency**: Daily or more frequent
- **Retention**: 30+ days
- **Location**: Internal storage (not external)
- **Testing**: Test restore procedures regularly

### Backup Checklist

1. Database backups (automated)
2. Configuration backups (values.yaml files, versioned)
3. TLS certificates (secure storage)
4. Custom CA certificate (backup copy)
5. Helm chart versions (archived)

### Recovery Procedure

Documented recovery procedure should cover:
1. Database restoration steps
2. Helm redeployment steps
3. Data validation after restore
4. User communication plan

## Monitoring & Logging

### Internal Monitoring

Set up internal monitoring for:
- CPU and memory usage
- Pod restart count
- Database connection count
- Ingress error rates
- Certificate expiration dates

### Log Aggregation

Forward logs to your internal log aggregation system:
- Application logs from ZenML pods
- Ingress logs
- Database logs
- Kubernetes events

### Alerting

Create alerts for:
- Pod failures
- High resource usage
- Database connection errors
- Certificate near expiration
- Disk space warnings

## Maintenance

### Regular Tasks

- Monitor disk space (databases, artifact storage)
- Review and manage user access
- Update internal CA certificate before expiration
- Test backup and recovery procedures
- Monitor pod logs for warnings

### Periodic Updates

When updating to a new ZenML version:

1. Pull new images on internet-connected machine
2. Push to internal registry
3. Create new offline bundle with updated Helm charts
4. Transfer bundle to air-gapped environment
5. Update Helm charts in air-gapped environment
6. Update image tags in values.yaml
7. Perform helm upgrade on control plane
8. Perform helm upgrade on workspace servers
9. Verify health after upgrade
10. Update client images in your custom ZenML container

## Troubleshooting

### Pods Won't Start

Check pod logs and events:
```bash
kubectl -n zenml-pro describe pod zenml-pro-xxxxx
kubectl -n zenml-pro logs zenml-pro-xxxxx
```

Common issues:
- Image pull failures (check registry access)
- Database connectivity (verify connection string)
- Certificate issues (verify CA is trusted)

### Database Connection Failed

```bash
# Test from pod
kubectl -n zenml-pro exec -it zenml-pro-xxxxx -- \
  mysql -h mysql.internal.mycompany.com -u zenml_pro_user -p zenml_pro
```

### Can't Access via HTTPS

1. Verify certificate validity
2. Verify DNS resolution
3. Check Ingress status
4. Verify CA certificate is installed on client

### Image Pull Errors

1. Verify images are in internal registry
2. Check registry credentials in secret
3. Verify imagePullSecrets configured correctly

## Day 2 Operations

For information on upgrading ZenML Pro components, see the [Upgrades & Updates](upgrades-updates.md) guide.

## Related Resources

- [Self-hosted Deployment Overview](self-hosted-deployment.md)
- [Self-hosted Deployment Guide](self-hosted.md) - Comprehensive deployment reference
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [MySQL Documentation](https://dev.mysql.com/doc/)
- [Helm Documentation](https://helm.sh/docs/)

## Support

For air-gapped deployments, contact ZenML Support:
- Email: [cloud@zenml.io](mailto:cloud@zenml.io)
- Provide: Your offline bundle, deployment status, and any error logs

Request from ZenML Support:
- Pre-deployment architecture consultation
- Offline support packages
- Update bundles and release notes
- Security documentation (SBOM, vulnerability reports)

