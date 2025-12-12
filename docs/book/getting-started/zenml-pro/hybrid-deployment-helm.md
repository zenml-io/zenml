---
description: Deploy ZenML Pro Hybrid using Kubernetes and Helm charts.
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

# Hybrid Deployment on Kubernetes with Helm

This guide provides step-by-step instructions for deploying ZenML Pro in a Hybrid setup using Kubernetes and Helm charts.

## Prerequisites

- Kubernetes cluster (1.24+) - EKS, GKE, AKS, or self-managed
- `kubectl` configured to access your cluster
- `helm` CLI (3.0+) installed
- A domain name and TLS certificate for your ZenML server
- MySQL database (managed or self-hosted)
- Outbound HTTPS access to `cloudapi.zenml.io`

Before starting, complete the setup described in [Hybrid Deployment Overview](hybrid-deployment.md):
- Step 1: Set up ZenML Pro organization
- Step 2: Configure your infrastructure (database, networking, TLS)
- Step 3: Obtain Pro credentials from ZenML Support

## Step 1: Prepare Helm Chart

For OCI-based Helm charts, you can either pull the chart or install directly. To pull the chart first:

```bash
helm pull oci://public.ecr.aws/zenml/zenml --version <ZENML_OSS_VERSION>
```

Alternatively, you can install directly from OCI (see Step 3 below).

## Step 2: Create Helm Values File

Create a file `zenml-hybrid-values.yaml` with your configuration:

```yaml
# ZenML Server Configuration
zenml:
  # Analytics (optional)
  analyticsOptIn: false

  # Thread pool size for concurrent operations
  threadPoolSize: 20

  # Database Configuration
  # Note: Workspace servers only support MySQL, not PostgreSQL
  database:
    maxOverflow: "-1"
    poolSize: "10"

    url: mysql://<user>:<password>@<host>:<port>/<database>

  # Image Configuration
  image:
    repository: 715803424590.dkr.ecr.eu-central-1.amazonaws.com/zenml-pro-server

  # Server URL (your actual domain)
  serverURL: https://zenml.mycompany.com

  # Ingress Configuration
  ingress:
    enabled: true
    host: zenml.mycompany.com

  # Pro Hybrid Configuration
  pro:
    # ZenML Control Plane endpoints
    apiURL: https://cloudapi.zenml.io
    dashboardURL: https://cloud.zenml.io
    enabled: true
    enrollmentKey: <your-enrollment-key>
    # Your organization details
    organizationID: <your-org-id>
    organizationName: <your-org-name>
    # Workspace details (provided by ZenML)
    workspaceID: <your-workspace-id>
    workspaceName: <your-workspace-name>

  # Replica count
  replicaCount: 1

  # Secrets Store Configuration
  secretsStore:
    sql:
      encryptionKey: <your-encryption-key>  # 32-byte hex string
    type: sql

# Resource Limits (adjust to your needs)
resources:
  limits:
    memory: 800Mi
  requests:
    cpu: 100m
    memory: 450Mi
```

## Step 3: Deploy with Helm

Install the ZenML chart directly from OCI:

```bash
helm install zenml oci://public.ecr.aws/zenml/zenml \
  --namespace zenml-hybrid \
  --create-namespace \
  --values zenml-hybrid-values.yaml \
  --version <ZENML_OSS_VERSION>
```

Or if you pulled the chart in Step 1, install from the local file:

```bash
helm install zenml ./zenml-<ZENML_OSS_VERSION>.tgz \
  --namespace zenml-hybrid \
  --create-namespace \
  --values zenml-hybrid-values.yaml
```

Monitor the deployment:

```bash
kubectl -n zenml-hybrid get pods -w
```

Wait for the pod to be running:

```bash
kubectl -n zenml-hybrid get pods
# Output should show:
# NAME                    READY   STATUS    RESTARTS   AGE
# zenml-5c4b6d9dcd-7bhfp  1/1     Running   0          2m
```

## Step 4: Verify the Deployment

### Check Service is Running

```bash
kubectl -n zenml-hybrid get svc
kubectl -n zenml-hybrid get ingress
```

### Verify Control Plane Connection

```bash
kubectl -n zenml-hybrid logs deployment/zenml | tail -20
```

Look for messages indicating successful connection to the control plane.

### Test HTTPS Connectivity

```bash
curl -k https://zenml.mycompany.com/health
# Should return 200 OK with a JSON response
```

### Access the Dashboard

1. Navigate to `https://zenml.mycompany.com` in your browser
2. You should be redirected to ZenML Cloud login
3. Sign in with your organization credentials
4. You should see your workspace listed

## Step 5: (Optional) Enable Snapshot Support / Workload Manager

Pipeline snapshots (running pipelines from the UI) require a workload manager. For hybrid deployments, you can configure one of the following:

{% hint style="warning" %}
Snapshots are only available from ZenML workspace server version 0.90.0 onwards.
{% endhint %}

### 1. Create Kubernetes Resources for Workload Manager

Create a dedicated namespace and service account:

```bash
kubectl create namespace zenml-workspace-namespace
kubectl -n zenml-workspace-namespace create serviceaccount zenml-workspace-service-account
```

### 2. Configure Workload Manager in Helm Values

Add environment variables to your `zenml-hybrid-values.yaml`:

**Option A: Kubernetes-based (Simplest)**

```yaml
zenml:
    environment:
        ZENML_SERVER_WORKLOAD_MANAGER_IMPLEMENTATION_SOURCE: zenml_cloud_plugins.kubernetes_workload_manager.KubernetesWorkloadManager
        ZENML_KUBERNETES_WORKLOAD_MANAGER_NAMESPACE: zenml-workspace-namespace
        ZENML_KUBERNETES_WORKLOAD_MANAGER_SERVICE_ACCOUNT: zenml-workspace-service-account
        ZENML_KUBERNETES_WORKLOAD_MANAGER_RUNNER_IMAGE: 715803424590.dkr.ecr.eu-central-1.amazonaws.com/zenml-pro-server:<ZENML_OSS_VERSION>
```

**Option B: AWS-based (if running on EKS)**

```yaml
zenml:
    environment:
        ZENML_SERVER_WORKLOAD_MANAGER_IMPLEMENTATION_SOURCE: zenml_cloud_plugins.aws_kubernetes_workload_manager.AWSKubernetesWorkloadManager
        ZENML_KUBERNETES_WORKLOAD_MANAGER_NAMESPACE: zenml-workspace-namespace
        ZENML_KUBERNETES_WORKLOAD_MANAGER_SERVICE_ACCOUNT: zenml-workspace-service-account
        ZENML_KUBERNETES_WORKLOAD_MANAGER_BUILD_RUNNER_IMAGE: "true"
        ZENML_KUBERNETES_WORKLOAD_MANAGER_DOCKER_REGISTRY: <your-ecr-registry>
        ZENML_KUBERNETES_WORKLOAD_MANAGER_ENABLE_EXTERNAL_LOGS: "true"
        ZENML_AWS_KUBERNETES_WORKLOAD_MANAGER_BUCKET: s3://your-bucket/zenml-logs
        ZENML_AWS_KUBERNETES_WORKLOAD_MANAGER_REGION: us-east-1
```

**Option C: GCP-based (if running on GKE)**

```yaml
zenml:
    environment:
        ZENML_SERVER_WORKLOAD_MANAGER_IMPLEMENTATION_SOURCE: zenml_cloud_plugins.gcp_kubernetes_workload_manager.GCPKubernetesWorkloadManager
        ZENML_KUBERNETES_WORKLOAD_MANAGER_NAMESPACE: zenml-workspace-namespace
        ZENML_KUBERNETES_WORKLOAD_MANAGER_SERVICE_ACCOUNT: zenml-workspace-service-account
        ZENML_KUBERNETES_WORKLOAD_MANAGER_BUILD_RUNNER_IMAGE: "true"
        ZENML_KUBERNETES_WORKLOAD_MANAGER_DOCKER_REGISTRY: <your-gcr-registry>
```

### 3. Configure Pod Resources (Optional but Recommended)

```yaml
zenml:
    environment:
        ZENML_KUBERNETES_WORKLOAD_MANAGER_POD_RESOURCES: '{"requests": {"cpu": "100m", "memory": "400Mi"}, "limits": {"memory": "700Mi"}}'
        ZENML_KUBERNETES_WORKLOAD_MANAGER_TTL_SECONDS_AFTER_FINISHED: 86400
        ZENML_SERVER_MAX_CONCURRENT_TEMPLATE_RUNS: 5
```

### 4. Redeploy with Updated Values

```bash
helm upgrade zenml zenml/zenml \
  --namespace zenml-hybrid \
  --values zenml-hybrid-values.yaml
```

## Step 6: Configure Environment Variables (Advanced)

For advanced configurations, you can set additional environment variables in your Helm values:

```yaml
zenml:
  environment:
    ZENML_LOGGING_LEVEL: INFO
    ZENML_ANALYTICS_OPT_IN: "false"
    # Add other environment variables as needed
```

## Database Configuration Examples

### AWS RDS MySQL

```yaml
zenml:
    database:
        maxOverflow: "-1"
        poolSize: "10"
        url: mysql://admin:<your-rds-password>@zenml-db.123456789.us-east-1.rds.amazonaws.com:3306/zenml_hybrid
```

### Google Cloud SQL MySQL

```yaml
zenml:
    database:
        maxOverflow: "-1"
        poolSize: "10"
        url: mysql://root:<your-cloud-sql-password>@34.123.45.67:3306/zenml_hybrid
```

### Self-Managed MySQL

```yaml
zenml:
    database:
        maxOverflow: "-1"
        poolSize: "10"
        url: mysql://zenml_user:<your-password>@mysql.internal.mycompany.com:3306/zenml_hybrid
```

## Networking & Firewall Configuration

### Kubernetes Network Policy

If your cluster uses network policies, allow traffic:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: zenml-egress
  namespace: zenml-hybrid
spec:
  podSelector:
    matchLabels:
      app: zenml
  policyTypes:
    - Egress
  egress:
    # Allow DNS
    - to:
        - namespaceSelector: {}
      ports:
        - protocol: UDP
          port: 53
    # Allow outbound to ZenML Cloud
    - to:
        - ipBlock:
            cidr: 0.0.0.0/0
      ports:
        - protocol: TCP
          port: 443
    # Allow database access
    - to:
        - podSelector:
            matchLabels:
              app: mysql
      ports:
        - protocol: TCP
          port: 3306
```

### Firewall Rules

Ensure your infrastructure firewall allows:

**Egress:**
- Destination: `cloudapi.zenml.io` (HTTPS port 443)
- Destination: Your database server (e.g., port 3306 for MySQL)

**Ingress:**
- Source: Your organization's networks or public internet
- Destination: Your ZenML server domain (HTTPS port 443)

## Ingress Controller Setup

### Using NGINX Ingress Controller

If not already installed:

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm install nginx-ingress ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace
```

Configure your Helm values:

```yaml
zenml:
  ingress:
    enabled: true
    className: nginx
    host: zenml.mycompany.com
    annotations:
      nginx.ingress.kubernetes.io/ssl-redirect: "true"
      nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    tls:
      enabled: true
      secretName: zenml-tls
```

### Using Traefik

```yaml
zenml:
  ingress:
    enabled: true
    className: traefik
    host: zenml.mycompany.com
    annotations:
      traefik.ingress.kubernetes.io/router.entrypoints: websecure
      traefik.ingress.kubernetes.io/router.tls: "true"
    tls:
      enabled: true
      secretName: zenml-tls
```

## TLS Certificate Management

### Self-Signed Certificates (Development Only)

```bash
# Generate certificate
openssl req -x509 -newkey rsa:4096 -keyout tls.key -out tls.crt -days 365 -nodes \
  -subj "/CN=zenml.mycompany.com"

# Create secret
kubectl -n zenml-hybrid create secret tls zenml-tls \
  --cert=tls.crt --key=tls.key
```

### Using cert-manager with Let's Encrypt

1. Install cert-manager:

```bash
helm repo add jetstack https://charts.jetstack.io
helm repo update
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set installCRDs=true
```

2. Create ClusterIssuer:

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@mycompany.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
      - http01:
          ingress:
            class: nginx
```

3. Update Helm values:

```yaml
zenml:
  ingress:
    annotations:
      cert-manager.io/cluster-issuer: letsencrypt-prod
    tls:
      enabled: true
```

## Persistent Storage (Optional)

If you need persistent storage for the ZenML server:

```yaml
persistence:
  enabled: true
  storageClassName: standard
  accessMode: ReadWriteOnce
  size: 10Gi
```

## Scaling & High Availability

### Multiple Replicas

```yaml
zenml:
  replicaCount: 3
```

### Pod Disruption Budget

```yaml
podDisruptionBudget:
  enabled: true
  minAvailable: 1
```

### Horizontal Pod Autoscaler

```yaml
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 5
  targetCPUUtilizationPercentage: 80
```

## Monitoring & Logging

### Prometheus Metrics

```yaml
zenml:
  metrics:
    enabled: true
    port: 8001
```

### Logging Configuration

```yaml
zenml:
  logging:
    level: INFO
    format: json
```

Collect logs with:

```bash
kubectl -n zenml-hybrid logs deployment/zenml -f
```

## Updating the Deployment

### Update Configuration

1. Modify `zenml-hybrid-values.yaml`
2. Upgrade with Helm:

```bash
helm upgrade zenml oci://public.ecr.aws/zenml/zenml \
  --namespace zenml-hybrid \
  --values zenml-hybrid-values.yaml \
  --version <ZENML_OSS_VERSION>
```

### Upgrade ZenML Version

1. Check available versions:

For OCI charts, you can check available versions by attempting to pull different versions, or contact ZenML Support for the latest version information.

2. Update values file with new version
3. Upgrade:

```bash
helm upgrade zenml zenml/zenml \
  --namespace zenml-hybrid \
  --values zenml-hybrid-values.yaml \
  --version <new-version>
```

## Troubleshooting

### Pod won't start

```bash
kubectl -n zenml-hybrid describe pod zenml-xxxxx
kubectl -n zenml-hybrid logs zenml-xxxxx
```

### Database connection errors

```bash
# Test database connectivity from pod
kubectl -n zenml-hybrid exec -it zenml-xxxxx -- \
  mysql -h <db-host> -u <user> -p<password> -e "SELECT 1"
```

### Control plane connection issues

```bash
# Check logs for auth errors
kubectl -n zenml-hybrid logs zenml-xxxxx | grep -i "oauth\|auth\|control"
```

### Ingress not working

```bash
kubectl -n zenml-hybrid get ingress
kubectl -n zenml-hybrid describe ingress zenml
```

## Uninstalling

```bash
helm uninstall zenml --namespace zenml-hybrid
kubectl delete namespace zenml-hybrid
```

## Next Steps

- [Configure your organization in ZenML Cloud](https://cloud.zenml.io)
- [Set up users and teams](../organization.md)
- [Configure stacks and service connectors](https://docs.zenml.io/stacks)
- [Run your first pipeline](https://docs.zenml.io/getting-started/quickstart)

## Related Documentation

- [Hybrid Deployment Overview](hybrid-deployment.md)
- [Self-hosted Deployment Guide](self-hosted.md)
- [ZenML Helm Chart Documentation](https://artifacthub.io/packages/helm/zenml/zenml)
