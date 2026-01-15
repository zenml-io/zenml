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

This guide provides step-by-step instructions for deploying ZenML Pro in a Hybrid setup using Kubernetes and Helm charts. In this deployment model, the Workspace Server runs in your infrastructure while the Control Plane is managed by ZenML.

<!-- DIAGRAM: Hybrid deployment architecture showing Control Plane (ZenML) connected to Workspace Server (your K8s cluster), database, and workload manager pods -->

**What you'll configure:**
- Workspace Server with database connection
- Network connectivity to ZenML Control Plane
- Workload manager for running pipelines from the UI
- TLS/SSL certificates and domain name

## Prerequisites

- Kubernetes cluster (1.24+) - EKS, GKE, AKS, or self-managed
- `kubectl` configured to access your cluster
- `helm` CLI (3.0+) installed
- A domain name and TLS certificate for your ZenML server
- MySQL database (managed or self-hosted)
- Outbound HTTPS access to `cloudapi.zenml.io`

**Tools (on a machine with internet access for initial setup):**
- Docker
- Helm (3.0+)
- Access to pull ZenML Pro images from private registries (contact [cloud@zenml.io](mailto:cloud@zenml.io))

Before starting, complete the setup described in [Hybrid Deployment Overview](hybrid-deployment.md):
- Step 1: Set up ZenML Pro organization
- Step 2: Configure your infrastructure (database, networking, TLS)
- Step 3: Obtain Pro credentials from ZenML Support

## Step 1: Prepare Helm Chart and docker images

### Pull Container Images

Access and pull from the ZenML Pro container registries:

1. Authenticate to the ZenML Pro container registries (AWS ECR or GCP Artifact Registry)
   - Use the credentials that you provided to the ZenML Support to access the private zenml container registry

2. Pull all required images:
   - **Workspace Server image (AWS ECR):**
     - `715803424590.dkr.ecr.eu-central-1.amazonaws.com/zenml-pro-server:<version>`
   - **Workspace Server image (GCP Artifact Registry):**
     - `europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-server:<version>`
   - **Client image (for pipelines):**
     - `zenmldocker/zenml:<version>`

   Example pull commands (AWS ECR):
   ```bash
   docker pull 715803424590.dkr.ecr.eu-central-1.amazonaws.com/zenml-pro-server:<version>
   docker pull zenmldocker/zenml:<version>
   ```

   Example pull commands (GCP Artifact Registry):
   ```bash
   docker pull europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-server:<version>
   docker pull zenmldocker/zenml:<version>
   ```

### Pull Helm chart

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

**Minimum required settings:**

* the database credentials (`zenml.database.url`)
* the URL (`zenml.serverURL`) and Ingress hostname (`zenml.ingress.host`) where the ZenML Hybrid workspace server will be reachable
* the Pro configuration (`zenml.pro.*`) with your organization and workspace details

**Additional relevant settings:**

* configure container registry credentials (`imagePullSecrets`) if your cluster cannot authenticate directly to the ZenML Pro container registry
* injecting custom CA certificates (`zenml.certificates`), especially important if the TLS certificates used by the ZenML Pro services are signed by a custom Certificate Authority
* configure HTTP proxy settings (`zenml.proxy`)
* custom container image repository location (`zenml.image.repository`)
* additional Ingress settings (`zenml.ingress`)
* Kubernetes resources allocated to the pods (`resources`)

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

## Step 5: Configure Workload Manager

The Workspace Server includes a workload manager that enables running pipelines directly from the ZenML Pro UI. This requires the workspace server to have access to a Kubernetes cluster where ad-hoc runner pods can be created.

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
helm upgrade zenml oci://public.ecr.aws/zenml/zenml \
  --namespace zenml-hybrid \
  --values zenml-hybrid-values.yaml \
  --version <ZENML_OSS_VERSION>
```

## Domain Name

You'll need an FQDN for the ZenML Hybrid workspace server.

* **FQDN Setup**\
  Obtain a Fully Qualified Domain Name (FQDN) (e.g., `zenml.mycompany.com`) from your DNS provider.
  * Identify the external Load Balancer IP address of the Ingress controller using the command `kubectl get svc -n <ingress-namespace>`. Look for the `EXTERNAL-IP` field of the Load Balancer service.
  * Create a DNS `A` record (or `CNAME` for subdomains) pointing the FQDN to the Load Balancer IP. Example:
    * Host: `zenml.mycompany.com`
    * Type: `A`
    * Value: `<Load Balancer IP>`
  * Use a DNS propagation checker to confirm that the DNS record is resolving correctly.

{% hint style="warning" %}
Make sure you don't use a simple DNS prefix for the server (e.g. `https://zenml.cluster` is not recommended). Always use a fully qualified domain name (FQDN) (e.g. `https://zenml.ml.cluster`). The TLS certificates will not be accepted by some browsers otherwise (e.g. Chrome).
{% endhint %}

## SSL Certificate

The ZenML Hybrid workspace server does not terminate SSL traffic. It is your responsibility to generate and configure the necessary SSL certificates for the workspace server.

### Obtaining SSL Certificates

Acquire an SSL certificate for the domain. You can use:

* A commercial SSL certificate provider (e.g., DigiCert, Sectigo).
* Free services like [Let's Encrypt](https://letsencrypt.org/) for domain validation and issuance.
* Self-signed certificates (not recommended for production environments). **IMPORTANT**: If you are using self-signed certificates, you will need to install the CA certificate on every client machine that connects to the workspace server.

### Configuring SSL Termination

Once the SSL certificate is obtained, configure your load balancer or Ingress controller to terminate HTTPS traffic:

**For NGINX Ingress Controller**:

You can configure SSL termination globally for the NGINX Ingress Controller by setting up a default SSL certificate or configuring it at the ingress controller level, or you can specify SSL certificates when configuring the ingress in the ZenML server Helm values.

Here's how you can do it globally:

1.  **Create a TLS Secret**

    Store your SSL certificate and private key as a Kubernetes TLS secret in the namespace where the NGINX Ingress Controller is deployed.

    ```bash
    kubectl create secret tls default-ssl-secret \
      --cert=/path/to/tls.crt \
      --key=/path/to/tls.key \
      -n <nginx-ingress-namespace>
    ```

2.  **Update NGINX Ingress Controller Configurations**

    Configure the NGINX Ingress Controller to use the default SSL certificate.

    *   If using the NGINX Ingress Controller Helm chart, modify the `values.yaml` file or use `--set` during installation:

        ```yaml
        controller:
          extraArgs:
            default-ssl-certificate: <nginx-ingress-namespace>/default-ssl-secret
        ```

        Or directly pass the argument during Helm installation or upgrade:

        ```bash
        helm upgrade --install ingress-nginx ingress-nginx \
          --repo https://kubernetes.github.io/ingress-nginx \
          --namespace <nginx-ingress-namespace> \
          --set controller.extraArgs.default-ssl-certificate=<nginx-ingress-namespace>/default-ssl-secret
        ```

    *   If the NGINX Ingress Controller was installed manually, edit its deployment to include the argument in the `args` section of the container:

        ```yaml
        spec:
          containers:
          - name: controller
            args:
              - --default-ssl-certificate=<nginx-ingress-namespace>/default-ssl-secret
        ```

**For Traefik**:

*   Configure Traefik to use TLS by creating a certificate resolver for Let's Encrypt or specifying the certificates manually in the `traefik.yml` or `values.yaml` file. Example for Let's Encrypt:

    ```yaml
    tls:
      certificatesResolvers:
        letsencrypt:
          acme:
            email: your-email@example.com
            storage: acme.json
            httpChallenge:
              entryPoint: web
    entryPoints:
      web:
        address: ":80"
      websecure:
        address: ":443"
    ```

* Reference the domain in your IngressRoute or Middleware configuration.

{% hint style="warning" %}
If you used a custom CA certificate to sign the TLS certificates for the ZenML Hybrid workspace server, you will need to install the CA certificates on every client machine.
{% endhint %}

### Configure Ingress in Helm Values

After setting up SSL termination at the ingress controller level, configure the ZenML Helm values to use ingress:

**For NGINX:**

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

**For Traefik:**

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

## Database Backup Strategy (Optional)

ZenML supports backing up the database before migrations are performed. Configure the backup strategy in your values file:

```yaml
zenml:
  database:
    # Backup strategy: in-memory (default), dump-file, database, or disabled
    backupStrategy: in-memory
    # For dump-file strategy with persistent storage:
    # backupPVStorageClass: standard
    # backupPVStorageSize: 1Gi
    # For database strategy (MySQL only):
    # backupDatabase: "zenml_backup"
```

{% hint style="info" %}
Local SQLite persistence (`zenml.database.persistence`) is only relevant when not using an external MySQL database. For hybrid deployments with external MySQL, configure backups at the database level.
{% endhint %}

## Scaling & High Availability

### Multiple Replicas

```yaml
zenml:
  replicaCount: 3
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

### Debug Logging

Enable verbose debug logging in the ZenML server:

```yaml
zenml:
  debug: true  # Sets ZENML_LOGGING_VERBOSITY to DEBUG
```

### Collecting Logs

View server logs with:

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

For the latest available ZenML Helm chart versions, visit: https://artifacthub.io/packages/helm/zenml/zenml


2. Update values file with new version
3. Upgrade:

```bash
helm upgrade zenml oci://public.ecr.aws/zenml/zenml \
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
