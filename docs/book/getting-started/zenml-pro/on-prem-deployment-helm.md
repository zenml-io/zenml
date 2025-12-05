---
description: Deploy ZenML Pro Air-gapped on Kubernetes with Helm - complete self-hosted setup with no external dependencies.
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
│  │     PostgreSQL Database                    │ │
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
- PostgreSQL database (12+) for metadata storage
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
   - **Pro Control Plane images:**
     - `715803424590.dkr.ecr.eu-west-1.amazonaws.com/zenml-pro-api:<version>`
     - `715803424590.dkr.ecr.eu-west-1.amazonaws.com/zenml-pro-dashboard:<version>`
   - **Workspace Server image:**
     - `715803424590.dkr.ecr.eu-central-1.amazonaws.com/zenml-pro-server:<version>`
   - **Client image (for pipelines):**
     - `zenmldocker/zenml:<version>`

   Example pull commands:
   ```bash
   docker pull 715803424590.dkr.ecr.eu-west-1.amazonaws.com/zenml-pro-api:<version>
   docker pull 715803424590.dkr.ecr.eu-west-1.amazonaws.com/zenml-pro-dashboard:<version>
   docker pull 715803424590.dkr.ecr.eu-central-1.amazonaws.com/zenml-pro-server:<version>
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

## Step 4: Create Kubernetes Namespace and Secrets

```bash
# Create namespace for ZenML Pro
kubectl create namespace zenml-pro

# Create secret for internal registry credentials (if needed)
kubectl -n zenml-pro create secret docker-registry internal-registry-secret \
  --docker-server=internal-registry.mycompany.com \
  --docker-username=<your-username> \
  --docker-password=<your-password>

# Create secret for TLS certificate
kubectl -n zenml-pro create secret tls zenml-tls \
  --cert=/path/to/tls.crt \
  --key=/path/to/tls.key
```

## Step 5: Set Up PostgreSQL Database

Create a PostgreSQL database instance (within your air-gapped network):

**Configuration:**
- **Accessibility**: Reachable from your Kubernetes cluster
- **Databases**: At least 2 (one for control plane, one for workspace)
- **Users**: Create dedicated database users with permissions
- **Backups**: Configure automated backups to local storage
- **Monitoring**: Enable local log aggregation

**Connection strings needed for later:**
- Control Plane DB: `postgresql://user:password@db-host:5432/zenml_pro`
- Workspace DB: `postgresql://user:password@db-host:5432/zenml_workspace`

## Step 6: Configure Helm Values for Control Plane

Create a file `zenml-pro-values.yaml`:

```yaml
# ZenML Pro Control Plane Values

zenml:
  # Image configuration - use your internal registry
  image:
    api:
      repository: internal-registry.mycompany.com/zenml/zenml-pro-api
      tag: "0.10.24"
    dashboard:
      repository: internal-registry.mycompany.com/zenml/zenml-pro-dashboard
      tag: "0.10.24"

  # Server URL - use your internal domain
  serverURL: https://zenml-pro.internal.mycompany.com

  # Database for Control Plane
  database:
    external:
      type: postgresql
      host: postgres.internal.mycompany.com
      port: 5432
      username: zenml_pro_user
      password: <secure-password>
      database: zenml_pro

  # Ingress configuration
  ingress:
    enabled: true
    className: nginx  # or your ingress controller
    host: zenml-pro.internal.mycompany.com
    tls:
      enabled: true
      secretName: zenml-tls

  # Authentication (no external IdP needed for air-gap)
  auth:
    password: <admin-password>

  # Resource constraints
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 2000m
      memory: 4Gi

# Image pull secrets for internal registry
imagePullSecrets:
  - name: internal-registry-secret

# Pod security context
podSecurityContext:
  fsGroup: 1000
  runAsNonRoot: true
  runAsUser: 1000
```

## Step 7: Deploy ZenML Pro Control Plane

Using the local Helm chart:

```bash
helm install zenml-pro ./zenml-pro-0.10.24.tgz \
  --namespace zenml-pro \
  --values zenml-pro-values.yaml
```

Verify deployment:

```bash
kubectl -n zenml-pro get pods
kubectl -n zenml-pro get svc
kubectl -n zenml-pro get ingress
```

Wait for all pods to be running and healthy.

## Step 8: Configure Helm Values for Workspace Server

Create a file `zenml-workspace-values.yaml`:

```yaml
zenml:
  # Image configuration - use your internal registry
  image:
    repository: internal-registry.mycompany.com/zenml/zenml-pro-server
    tag: "0.73.0"

  # Server URL
  serverURL: https://zenml-workspace.internal.mycompany.com

  # Database for Workspace
  database:
    external:
      type: postgresql
      host: postgres.internal.mycompany.com
      port: 5432
      username: zenml_workspace_user
      password: <secure-password>
      database: zenml_workspace

  # Pro configuration (for air-gapped, disable external control plane)
  pro:
    enabled: false  # Disable external control plane connection

  # Ingress configuration
  ingress:
    enabled: true
    className: nginx
    host: zenml-workspace.internal.mycompany.com
    tls:
      enabled: true
      secretName: zenml-tls

  # Resource constraints
  resources:
    requests:
      cpu: 250m
      memory: 512Mi
    limits:
      cpu: 1000m
      memory: 2Gi

# Image pull secrets
imagePullSecrets:
  - name: internal-registry-secret

# Pod security context
podSecurityContext:
  fsGroup: 1000
  runAsNonRoot: true
  runAsUser: 1000
```

## Step 9: Deploy ZenML Workspace Server

```bash
# Create namespace
kubectl create namespace zenml-workspace

# Deploy workspace
helm install zenml ./zenml-0.73.0.tgz \
  --namespace zenml-workspace \
  --values zenml-workspace-values.yaml
```

Verify deployment:

```bash
kubectl -n zenml-workspace get pods
kubectl -n zenml-workspace get svc
kubectl -n zenml-workspace get ingress
```

## Step 10: Configure Internal DNS

Update your internal DNS to resolve:
- `zenml-pro.internal.mycompany.com` → Your ALB/Ingress IP
- `zenml-workspace.internal.mycompany.com` → Your ALB/Ingress IP

## Step 11: Install Internal CA Certificate

On all client machines that will access ZenML:

1. Obtain your internal CA certificate
2. Install it in the system certificate store:
   - **Linux**: Copy to `/usr/local/share/ca-certificates/` and run `update-ca-certificates`
   - **macOS**: Use `sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain <cert.pem>`
   - **Windows**: Use `certutil -addstore "Root" cert.pem`

3. For Python/ZenML client:
   ```bash
   export REQUESTS_CA_BUNDLE=/path/to/ca-bundle.crt
   ```

4. For containerized pipelines, include the CA certificate in your custom ZenML image

## Step 12: Verify the Deployment

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

## Step 13: (Optional) Enable Snapshot Support / Workload Manager

Pipeline snapshots (running pipelines from the dashboard) require additional configuration:

### 1. Create Kubernetes Resources for Workload Manager

Create a dedicated namespace and service account for runner jobs:

```bash
# Create namespace
kubectl create namespace zenml-workload-manager

# Create service account
kubectl -n zenml-workload-manager create serviceaccount zenml-runner

# Create role with permissions to create jobs and access registry
# (Specific permissions depend on your implementation choice below)
```

### 2. Choose Implementation

**Option A: Kubernetes Implementation (Simplest)**

Use the built-in Kubernetes implementation for running snapshots:

```yaml
zenml:
  environment:
    ZENML_SERVER_WORKLOAD_MANAGER_IMPLEMENTATION_SOURCE: zenml_cloud_plugins.kubernetes_workload_manager.KubernetesWorkloadManager
    ZENML_KUBERNETES_WORKLOAD_MANAGER_NAMESPACE: zenml-workload-manager
    ZENML_KUBERNETES_WORKLOAD_MANAGER_SERVICE_ACCOUNT: zenml-runner
```

**Option B: GCP Implementation (if using GCP)**

For GCP-specific features:

```yaml
zenml:
  environment:
    ZENML_SERVER_WORKLOAD_MANAGER_IMPLEMENTATION_SOURCE: zenml_cloud_plugins.gcp_kubernetes_workload_manager.GCPKubernetesWorkloadManager
    ZENML_KUBERNETES_WORKLOAD_MANAGER_NAMESPACE: zenml-workload-manager
    ZENML_KUBERNETES_WORKLOAD_MANAGER_SERVICE_ACCOUNT: zenml-runner
    ZENML_KUBERNETES_WORKLOAD_MANAGER_BUILD_RUNNER_IMAGE: "true"
    ZENML_KUBERNETES_WORKLOAD_MANAGER_DOCKER_REGISTRY: <your-internal-registry>/zenml
```

### 3. Configure Runner Image

Choose how runner images are managed:

**Option A: Use Pre-built Runner Image (Simpler for Air-gap)**

```yaml
zenml:
  environment:
    ZENML_KUBERNETES_WORKLOAD_MANAGER_BUILD_RUNNER_IMAGE: "false"
    ZENML_KUBERNETES_WORKLOAD_MANAGER_RUNNER_IMAGE: internal-registry.mycompany.com/zenml/zenml:0.73.0
```

Pre-build your runner image and push to your internal registry.

**Option B: Have ZenML Build Runner Images**

Requires access to internal Docker registry with push permissions:

```yaml
zenml:
  environment:
    ZENML_KUBERNETES_WORKLOAD_MANAGER_BUILD_RUNNER_IMAGE: "true"
    ZENML_KUBERNETES_WORKLOAD_MANAGER_DOCKER_REGISTRY: internal-registry.mycompany.com/zenml
```

### 4. Configure Pod Resources and Policies

```yaml
zenml:
  environment:
    ZENML_KUBERNETES_WORKLOAD_MANAGER_POD_RESOURCES: '{"requests": {"cpu": "100m", "memory": "400Mi"}, "limits": {"memory": "700Mi"}}'
    ZENML_KUBERNETES_WORKLOAD_MANAGER_TTL_SECONDS_AFTER_FINISHED: 86400  # 1 day
    ZENML_KUBERNETES_WORKLOAD_MANAGER_NODE_SELECTOR: '{"node-pool": "compute"}'
    ZENML_SERVER_MAX_CONCURRENT_TEMPLATE_RUNS: 2
```

### 5. Update Workspace Deployment

Update your workspace server Helm values with workload manager configuration and redeploy:

```bash
helm upgrade zenml ./zenml-<version>.tgz \
  --namespace zenml-workspace \
  --values zenml-workspace-values.yaml
```

## Step 14: Create Users and Organizations

In the ZenML Pro dashboard:

1. Create an organization
2. Create users for your team
3. Assign roles and permissions
4. Configure teams

## Network Requirements Summary

| Traffic | Source | Destination | Port | Direction |
|---------|--------|-------------|------|-----------|
| Web Access | Client Machines | Ingress Controller | 443 | Inbound |
| API Access | ZenML Client | Workspace Server | 443 | Inbound |
| Database | Kubernetes Pods | PostgreSQL | 5432 | Outbound |
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

For HA, configure PostgreSQL streaming replication:
1. Set up a standby database
2. Configure continuous archiving
3. Test failover procedures

## Backup & Recovery

### Automated Backups

Configure automated PostgreSQL backups:
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
  psql -h postgres.internal.mycompany.com -U zenml_pro_user -d zenml_pro
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

## Day 2 Operations: Updates and Upgrades

### Receiving New Versions

When new ZenML versions are released:

1. **Request offline bundle** from ZenML Support containing:
   - Updated container images
   - Updated Helm charts
   - Release notes and migration guide
   - Vulnerability assessment (if applicable)

2. **Review release notes** for:
   - Breaking changes
   - Database migration requirements
   - New features and configuration options
   - Security updates

3. **Transfer bundle** to your air-gapped environment using approved methods

### Upgrade Process

1. **Backup current state:**
   - Database backup
   - Values.yaml files
   - TLS certificates

2. **Update container images in internal registry:**
   - Extract and load new images
   - Tag and push to your internal registry

3. **Update Helm charts:**
   - Extract new chart versions
   - Review any changes to values schema

4. **Upgrade control plane first:**
   ```bash
   helm upgrade zenml-pro ./zenml-pro-<new-version>.tgz \
     --namespace zenml-pro \
     --values zenml-pro-values.yaml
   ```

5. **Verify control plane:**
   - Check pod status
   - Review logs
   - Test connectivity

6. **Upgrade workspace servers:**
   ```bash
   helm upgrade zenml ./zenml-<new-version>.tgz \
     --namespace zenml-workspace \
     --values zenml-workspace-values.yaml
   ```

7. **Verify workspaces:**
   - Check all pods are running
   - Review logs
   - Run health checks
   - Test dashboard access

### Database Migrations

Some updates may require database migrations:

1. **Review migration guide** in release notes
2. **Back up database** before upgrading
3. **Monitor logs** for any migration-related errors
4. **Verify data integrity** after upgrade
5. **Test key features** (workspace access, pipeline runs, etc.)

## Disaster Recovery & Backup Strategy

### Backup Components

Regular backups should include:

1. **PostgreSQL Databases:**
   - Schedule automated backups (daily minimum)
   - Test restore procedures regularly
   - Store backups in a different location (second disk, external storage)
   - Retain for 30+ days

2. **Configuration:**
   - Version control Helm values files
   - Store TLS certificates securely
   - Document any manual customizations

3. **Container Images:**
   - Keep copies of all images used
   - Maintain manifest of images and versions

### Recovery Procedures

Document and test:

1. **Database Recovery:**
   - Steps to restore from backup
   - Verification procedures
   - Estimated recovery time

2. **Full Cluster Recovery:**
   - How to redeploy from scratch
   - Image and chart preparation
   - Restore order (databases first, then control plane, then workspaces)

3. **Partial Recovery:**
   - Recovering single workspace
   - Recovering specific components

## Related Resources

- [Air-gapped Deployment Overview](air-gapped-deployment.md)
- [Self-hosted Deployment Guide](self-hosted.md) - Comprehensive deployment reference
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
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
