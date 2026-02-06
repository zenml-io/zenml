---
description: Prepare for deploying the ZenML Pro control plane and/or workspace servers in a self-hosted environment.
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

# Self-hosted Deployment Prerequisites and Preparation

This page outlines the general infrastructure requirements and preparation steps for deploying ZenML Pro components (control plane or workspace servers) in a self-hosted environment. These prerequisites apply regardless of the specific deployment method you choose. After reviewing these requirements and collecting the necessary artifacts and information, proceed to the deployment guide for your chosen component and infrastructure type.

## ZenML Pro Software Artifacts

ZenML Pro consists of two distinct software component groups, each with its own release cycle and versioning:

### Control Plane Components

{% hint style="info" %}
You only need to deploy and manage the Control Plane components if you are setting up [the fully self-hosted scenario](self-hosted.md). If you are using the [hybrid scenario](hybrid.md) or the [SaaS scenario](saas-deployment.md), the Control Plane is fully managed by ZenML.
{% endhint %}

The **Control Plane API** and **Control Plan Web UI** are developed and released together as part of the ZenML Pro product. These components:

- Share a unified version number (e.g., `0.13.0`)
- Have container images and Helm chart releases aligned to the same version
- Container images are privately hosted in the ZenML GCP Artifact Registry and ZenML AWS ECR repositories. Access to these registries is [granted upon request](#authenticating-to-zenml-pro-container-registries):

    - **images hosted in the ZenML GCP Artifact Registry**:
      - `europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-api:<version>`
      - `europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-dashboard:<version>`

    - **images hosted in the ZenML AWS ECR repositories**:
      - `715803424590.dkr.ecr.eu-west-1.amazonaws.com/zenml-pro-api:<version>`
      - `715803424590.dkr.ecr.eu-west-1.amazonaws.com/zenml-pro-dashboard:<version>`

- The `zenml-pro` Helm chart is publicly hosted in [ZenML Pro ArtifactHub repository](https://artifacthub.io/packages/helm/zenml-pro/zenml-pro)

**Release notes:** [ZenML Pro Control Plane Changelog](https://docs.zenml.io/changelog/pro-control-plane)

### ZenML Pro Workspace Server Component

{% hint style="info" %}
You need to deploy and manage the Workspace Server components if you are setting up either the [hybrid scenario](hybrid.md) or [the self-hosted scenario](self-hosted.md). If you are using the [SaaS scenario](saas-deployment.md), the Workspace Servers are fully managed by ZenML.
{% endhint %}

The **Workspace Server** is built on top of the open-source ZenML server. This component:

- Follows the same versioning as ZenML OSS releases (e.g., `0.93.2`)
- Is released simultaneously with ZenML OSS
- Uses the same OSS `zenml` Helm chart for deployment
- Receives the same features and fixes as the OSS server, with additional Pro-specific integrations
- Container images are privately hosted in the ZenML GCP Artifact Registry and ZenML AWS ECR repositories. Access to these registries is [granted upon request](#authenticating-to-zenml-pro-container-registries):

  - **images hosted in the ZenML GCP Artifact Registry**:
    - `europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-server:<version>`

  - **images hosted in the ZenML AWS ECR repositories**:
    - `715803424590.dkr.ecr.eu-central-1.amazonaws.com/zenml-pro-server:<version>`
    
- The `zenml` Helm chart is publicly hosted in [ZenML OSS ArtifactHub repository](https://artifacthub.io/packages/helm/zenml/zenml)

**Release notes:** [ZenML Server & SDK Changelog](https://docs.zenml.io/changelog/server-sdk)

{% hint style="info" %}
The Control Plane and Workspace Server versions are independent. For example, you might run Control Plane version `0.13.0` with Workspace Servers running version `0.93.2`. Compatibility between versions is guaranteed as long as the Control Plane version is at least as new as the Workspace Server version.
{% endhint %}

### Authenticating to ZenML Pro Container Registries

Access to the ZenML Pro container registries is granted upon request. The authentication method depends on your infrastructure:

**Option 1: AWS IAM Role (recommended for AWS workloads)**

If you run your infrastructure on AWS (EKS, ECS, EC2, Fargate, etc.), you can provide ZenML with the IAM role ARN associated with your workload. ZenML will grant this role permission to pull images from the AWS ECR repositories.

| Scenario | What to provide |
|----------|-----------------|
| EKS with IRSA | The IAM role ARN used by your Kubernetes service account |
| ECS tasks | The task execution role ARN |
| EC2 instances | The instance profile role ARN |

This approach is preferred because it uses native AWS IAM authentication without managing long-lived credentials.

**Option 2: GCP Service Account (recommended for GCP workloads)**

If you run your infrastructure on GCP (GKE, Cloud Run, Compute Engine, etc.), you can provide ZenML with your service account principal. ZenML will grant this principal permission to pull images from the GCP Artifact Registry.

| Scenario | What to provide |
|----------|-----------------|
| GKE with Workload Identity | The Kubernetes service account email (e.g., `sa-name@project-id.iam.gserviceaccount.com`) |
| Cloud Run | The service account email used by your Cloud Run service |
| Compute Engine | The service account email attached to your VM instances |

This approach uses native GCP IAM authentication without managing long-lived credentials.

**Option 3: Docker credentials (for other environments)**

If you run on infrastructure outside of AWS or GCP, or if you prefer to use explicit credentials, ZenML can provide you with GCP authentication credentials that work with Docker directly.

Use these credentials to authenticate with Docker before pulling the images hosted in the ZenML GCP Artifact Registry:

```bash
cat your-zenml-issued-key.json | docker login -u _json_key --password-stdin https://europe-west3-docker.pkg.dev
```

{% hint style="info" %}
To request access to the ZenML Pro container registries, contact [cloud@zenml.io](mailto:cloud@zenml.io) with details about your infrastructure and preferred authentication method.
{% endhint %}

### Air-gapped Deployment Process

If you need to deploy ZenML Pro fully self-hosted (control plane and workspace servers) in an air-gapped environment (a network with no direct internet access), you'll need to transfer all required artifacts to your internal infrastructure. Here's a step-by-step process performed on a machine with internet access that builds a bundle of all required artifacts that can then be transferred to your air-gapped environment.

#### 1. Pull Container Images

{% hint style="info" %}
Access to the ZenML Pro container registries is restricted and granted upon request. See the [Authentication to ZenML Pro Container Registries](#authenticating-to-zenml-pro-container-registries) section for more details.
{% endhint %}

On a machine with internet access and access to the ZenML Pro container registries, after having authenticated your docker client, pull all required images. Example commands:
  ```bash
  docker pull europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-api:<version>
  docker pull europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-dashboard:<version>
  docker pull europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-server:<version>
  docker pull zenmldocker/zenml:<version>
  ```

Save images to tar files for transfer:
   ```bash
   docker save europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-api:<version> > zenml-pro-api.tar
   docker save europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-dashboard:<version> > zenml-pro-dashboard.tar
   docker save europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-server:<version> > zenml-pro-server.tar
   docker save zenmldocker/zenml:<version> > zenml-client.tar
   ```

#### 2. Download Helm Charts

This step is only required if you are using Helm to deploy ZenML Pro.

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

#### 3. Create Offline Bundle

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

#### 4. Transfer to Air-gapped Environment

Transfer the bundle to your air-gapped environment using approved methods:
- Physical media (USB drive, external drive)
- Approved secure file transfer system
- Air-gap transfer appliances
- Any method compliant with your security policies

#### 5. Load Images into Internal Registry

In your air-gapped environment, load the images:

1. Extract all tar files:
   ```bash
   cd images/
   for file in *.tar; do docker load < "$file"; done
   ```

2. Tag images for your internal registry:
   ```bash
   docker tag europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-api:<version> internal-registry.mycompany.com/zenml/zenml-pro-api:<version>
   docker tag europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-dashboard:<version> internal-registry.mycompany.com/zenml/zenml-pro-dashboard:<version>
   docker tag europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-server:<version> internal-registry.mycompany.com/zenml/zenml-pro-server:<version>
   docker tag zenmldocker/zenml:<version> internal-registry.mycompany.com/zenml/zenml:<version>
   ```

3. Push images to your internal registry:
   ```
   docker push internal-registry.mycompany.com/zenml/zenml-pro-api:version
   docker push internal-registry.mycompany.com/zenml/zenml-pro-dashboard:version
   docker push internal-registry.mycompany.com/zenml/zenml-pro-server:version
   docker push internal-registry.mycompany.com/zenml/zenml:version
   ```

## Infrastructure Prerequisites

ZenML Pro requires several infrastructure components to operate. The specific implementation of these components may vary depending on your environment, cloud provider, and organizational policies.

### Containerized Workload Infrastructure

ZenML Pro runs as a set of containerized services that require an orchestration platform capable of running and managing containers. This infrastructure hosts the following components:

- The **Control Plane API** server for organization and workspace management
- The **Control Plane Web UI** for the central web interface
- **Workspace Servers**: One or more ZenML server instances that handle ML pipeline metadata

{% hint style="info" %}
The Control Plane and Workspace Server components are completely independent from an infrastructure perspective. Different types of containerized infrastructure can be used for the Control Plane and the Workspace Server. For example, you can use ECS for the Control Plane and Kubernetes for the Workspace Server, or vice versa.
{% endhint %}

**Supported options:**

| Infrastructure Type | Support Level |
|---------------------|---------------|
| Kubernetes (managed or self-hosted, 1.24+) | ✅ Officially supported and documented |
| Container-as-a-Service (ECS, Cloud Run, etc.) | ⚠️ Possible but not documented |
| Serverless containers (Fargate, Lambda, etc.) | ⚠️ Possible but not documented |
| Virtual machines with Docker (VMware, VirtualBox, etc.) | ⚠️ Possible but not documented |
| Docker-compose | ✅ Can be provided upon request for local testing purposes |

{% hint style="warning" %}
While ZenML Pro can theoretically run on any container orchestration platform, only Kubernetes deployments are officially fully supported and documented. If you require a different deployment target, please contact [cloud@zenml.io](mailto:cloud@zenml.io) to discuss your requirements.
{% endhint %}

### Database

ZenML Pro requires relational database(s) for storing metadata:

| Component | MySQL 8.0+ | PostgreSQL |
|-----------|------------|------------|
| Control Plane | ✅ Supported | ✅ Supported |
| Workspace Servers | ✅ Supported | ❌ Not supported |

**Database options:**

- **Managed database services**: AWS RDS, Google Cloud SQL, Azure Database for MySQL/PostgreSQL, etc.
- **Self-hosted databases**: MySQL or PostgreSQL running on VMs, Kubernetes, or bare metal

**Database naming:**

Each ZenML Pro component requires its own dedicated database (not a separate database instance — just a unique database name within the instance):

- One database for the **control plane** (e.g., `zenml_pro`) - only applicable if you are setting up [the fully self-hosted scenario](self-hosted.md)
- One database for **each workspace server** (e.g., `zenml_workspace_1`, `zenml_workspace_2`, etc.) - applicable for both the [hybrid scenario](hybrid.md) and [the fully self-hosted scenario](self-hosted.md)

{% hint style="info" %}
The databases do not need to be created in advance. ZenML Pro will automatically create them on first startup, provided the database user has the necessary permissions (`CREATE DATABASE`). If your database user lacks these permissions, create the databases manually before deployment.
{% endhint %}

**Sizing considerations:**

- A single MySQL database instance can host all ZenML Pro databases for small-to-medium deployments. For increased reliability and data isolation, consider using separate database instances for the control plane and workspace servers.
- For high availability, configure database replication and automated backups
- Contact [cloud@zenml.io](mailto:cloud@zenml.io) for sizing guidance based on your expected workload

### Container Registry

A container registry is required for most ZenML Pro deployments. While ZenML Pro container images can be pulled directly from ZenML's authenticated registries (AWS ECR or GCP Artifact Registry), you will almost certainly need your own container registry for running ML pipelines.

**Reasons why you might need a container registry:**

- **ML pipeline workloads**: When running ZenML pipelines with containerized orchestrators (Kubernetes, Docker, Kubeflow, Sagemaker, Vertex AI, etc.), ZenML builds and pushes container images containing your pipeline dependencies. These images must be stored in a registry accessible by your orchestration infrastructure.
- **Air-gapped deployments**: ZenML Pro images must be stored in an internal registry since external registries are not reachable.
- **Image customization**: When you need to modify ZenML Pro images to install CA certificates, configure HTTP proxies, or add other customizations.
- **Compliance requirements**: When organizational policies require all container images to be sourced from internal registries.

{% hint style="info" %}
Even if you use ZenML's hosted registries for the ZenML Pro control plane and workspace server images, you will still need a separate container registry for your ML pipeline images if you plan to use any containerized orchestrator.
{% endhint %}

**Supported container registries:**

| Registry Type | Examples |
|---------------|----------|
| Cloud-managed | AWS ECR, Google Artifact Registry, Azure Container Registry |
| Self-hosted | Harbor, Quay, JFrog Artifactory, Docker Registry |
| Local | Docker is enough for local testing purposes with docker-compose |

### SSO Identity Provider (Optional)

{% hint style="info" %}
SSO configuration is optional and only applicable if you are setting up [the fully self-hosted scenario](self-hosted.md). You can start with local accounts and enable SSO later without losing existing data. [The hybrid scenario](hybrid.md) already uses the ZenML Pro SaaS SSO for authentication.
{% endhint %}

By default, the ZenML Pro control plane uses local accounts with password authentication. Single Sign-On (SSO) can be enabled to authenticate users through an external identity provider instead.

**Supported identity providers:**

Any OIDC-compatible identity provider can be used, including:

| Provider Type | Examples |
|---------------|----------|
| Cloud identity services | Google Workspace, Microsoft Entra ID (Azure AD), Okta, Auth0 |
| Self-hosted solutions | Keycloak, Authentik, Dex, Gluu |
| Enterprise directories | ADFS, Ping Identity, OneLogin |

**Identity provider requirements:**

Your identity provider must meet the following specifications:

| Requirement | Description |
|-------------|-------------|
| OAuth 2.0 authorization code flow | Must support the standard authorization code grant |
| Required scopes | `openid`, `email`, `profile` |
| OpenID configuration endpoint | Must expose `/.well-known/openid-configuration` at a URL reachable by the ZenML Pro control plane |
| JWKS | Must implement JSON Web Key Set for signing ID tokens |
| Logout endpoint (optional) | If supported, enables single logout functionality |

**ZenML Pro client configuration in the identity provider:**

When registering ZenML Pro as an OIDC client in your identity provider, configure the following:

| Setting | Value |
|---------|-------|
| Redirect URI | `https://<zenml-ui-url>/api/auth/callback` |
| Post-logout redirect URI | `https://<zenml-ui-url>/api/auth/logout-complete` (if logout is supported) |
| Allowed scopes | `openid`, `email`, `profile` |
| Client type | Confidential (requires client secret) |

After registration, your identity provider will issue a **client ID** and **client secret** that you will need when configuring ZenML Pro in addition to the URL to the OpenID configuration endpoint (`/.well-known/openid-configuration`).

### Network Services

ZenML Pro requires several network services to expose its APIs and handle secure communications:

#### Load Balancer / Ingress

A load balancer or ingress mechanism is needed to:

- Route external traffic to the control plane API and dashboard
- Route traffic to workspace server APIs
- Distribute traffic across multiple replicas for high availability

**Options:**

- **Cloud provider load balancers**: AWS ALB/NLB, GCP Load Balancer, Azure Load Balancer, etc.
- **Kubernetes Ingress controllers**: NGINX Ingress Controller, Traefik, HAProxy, Contour, etc.
- **Kubernetes Gateway API**: The newer, more expressive routing standard using `Gateway` and `HTTPRoute` resources, supported by implementations like Envoy Gateway, Istio, NGINX Gateway Fabric, GKE Gateway Controller, and others
- **Reverse proxies**: NGINX, Envoy, HAProxy, etc. (for non-Kubernetes deployments)

#### DNS / Hostnames

ZenML Pro requires DNS hostnames for the control plane API, the web UI, and each workspace server. Planning your DNS structure in advance simplifies TLS certificate management and service integration.

**Recommended approach — common subdomain:**

Using a common parent subdomain for all ZenML Pro components is recommended:

| Component | Example Hostname |
|-----------|------------------|
| Web UI | `zenml.ml.example.com` |
| Control Plane API | `zenml-api.ml.example.com`; can also share the same hostname as the web UI if HTTP path routing is used (e.g. `https://zenml.ml.example.com/api/v1`) |
| Workspace Server | `zenml-workspace-1.ml.example.com` |

**Benefits of a common subdomain:**

- **Simplified TLS certificates**: A single wildcard certificate (`*.zenml.example.com`) can secure all components
- **Secure cookie sharing**: Authentication cookies can be shared across subdomains, enabling seamless integration between the dashboard and workspace servers
- **Easier DNS management**: All records can be managed under a single DNS zone

**Alternative — separate domains:**

{% hint style="info" %}
The Control Plane and Workspace Server components can run on different domains. The authentication mechanisms will still work effectively across domains.
{% endhint %}

Using completely separate domains or subdomains is also supported but requires additional configuration:

| Component | Example Hostname |
|-----------|------------------|
| Control Plane API | `zenml-api.site-one.com` |
| Web UI | `zenml.site-one.com` |
| Workspace Server | `ml-workspace.site-two.com` |

With separate domains, you will need individual TLS certificates for each endpoint and may need to configure CORS and cookie settings explicitly.

{% hint style="warning" %}
Always use fully qualified domain names (FQDNs) for your endpoints (e.g., `https://zenml.ml.example.com`). Avoid simple DNS prefixes without a proper domain structure (e.g., `https://zenml.cluster`) or localhost names (e.g., `https://localhost`, `https://zenml.localhost`), as some browsers and TLS implementations may not accept certificates for such names.
{% endhint %}

#### TLS/HTTPS Termination

ZenML Pro containers do **not** handle TLS termination internally. HTTPS traffic must be terminated externally before reaching the containers.

**Options for TLS termination:**

- **Cloud provider load balancers**: With SSL/TLS certificates managed by the cloud provider or uploaded manually
- **Kubernetes Ingress controllers**: With cert-manager for automatic certificate management or manually provisioned certificates
- **Kubernetes Gateway API**: Supports TLS termination via `Gateway` listener configuration with certificates stored in Kubernetes Secrets; also integrates with cert-manager
- **Reverse proxies**: With TLS configuration (for non-Kubernetes deployments)

**Certificate requirements:**

- Valid TLS certificates for all exposed endpoints (control plane API, dashboard, workspace servers)
- Certificates can be issued by a public CA, a private/internal CA, or be self-signed
- If using self-signed certificates or a private CA, the CA certificate must be installed on all client machines and in container images used for ZenML Pro containers and ML pipelines

{% hint style="info" %}
If you are using self-signed certificates, it is highly recommended to at least use a common self-signed CA certificate for all the ZenML Pro services (control plane and workspace servers). This simplifies certificate management - you only need to install one CA certificate system-wide on all servers and client machines, then use it to sign all the TLS certificates for the ZenML Pro services.
{% endhint %}

#### Internal Connectivity

The following internal network connectivity is required:

| Source | Destination | Port | Purpose |
|--------|-------------|------|---------|
| ZenML containers | Database server | 3306 (MySQL) or 5432 (PostgreSQL) | Metadata storage |
| Container runtime (e.g. Kubernetes nodes, Docker hosts, etc.) | Container registry | 443 | Image pulls (if using private registry) |
| Workspace servers | Control plane | 443 | Enrollment, status updates, RBAC permissions (if using [the fully self-hosted scenario](self-hosted.md)) |
| Web UI | Control plane | 443 | Authentication, API requests, UI data requests (if using [the fully self-hosted scenario](self-hosted.md)) |

#### External Connectivity

Depending on your deployment model:

| Connectivity | Required For |
|--------------|--------------|
| Inbound HTTPS (443) | Client access to dashboard and APIs |
| Outbound HTTPS (443) | Control plane server connecting to the identity provider for SSO authentication (if enabled and using [the fully self-hosted scenario](self-hosted.md)) |
| Outbound HTTPS (443) | Pulling images from ZenML registries (if not air-gapped) |
| Outbound HTTPS (443) | Workspace servers connecting to the control plane for enrollment, status updates, RBAC permissions (if using [the hybrid scenario](hybrid.md)) |

## Information to Collect Before Deployment

Before proceeding with the deployment, gather all the information listed below. Having these details ready will streamline the deployment process and reduce configuration errors.

{% hint style="info" %}
Use the tables below as a checklist. Fill in the values for your environment and keep them handy during deployment.
{% endhint %}

### Database Configuration

You need connection details for each database. A single database instance can host multiple databases (one per component), or you can use separate instances for isolation.

| Parameter | Control Plane | Workspace Server(s) |
|-----------|---------------|---------------------|
| Database type | MySQL or PostgreSQL | MySQL only |
| Hostname / endpoint | `_______________` | `_______________` |
| Port | `_______________` (default: 3306/5432) | `_______________` (default: 3306) |
| Database name | `_______________` (e.g., `zenml_pro`) | `_______________` (e.g., `zenml_workspace_1`) |
| Username | `_______________` | `_______________` |
| Password | `_______________` | `_______________` |
| SSL/TLS required | Yes / No | Yes / No |
| CA certificate path (if applicable) | `_______________` | `_______________` |

{% hint style="warning" %}
Each workspace server requires its own dedicated database. If you plan to deploy multiple workspaces, prepare a separate database name for each.
{% endhint %}

### DNS and Hostnames

| Component | Hostname | Notes |
|-----------|----------|-------|
| Web UI | `_______________` | e.g., `zenml.ml.example.com` |
| Control Plane API | `_______________` | Can share hostname with UI using path routing, e.g., `zenml.ml.example.com/api/v1` |
| Workspace Server 1 | `_______________` | e.g., `workspace-1.ml.example.com` |
| Workspace Server 2 (if applicable) | `_______________` | |
| Additional workspaces... | `_______________` | |

### TLS Certificates

| Parameter | Value |
|-----------|-------|
| Certificate type | ☐ Public CA &nbsp;&nbsp; ☐ Private/Internal CA &nbsp;&nbsp; ☐ Self-signed |
| Wildcard certificate | ☐ Yes (`*._______________`) &nbsp;&nbsp; ☐ No (individual certs) |
| Certificate file(s) path | `_______________` |
| Private key file path | `_______________` |
| CA certificate path (if private CA) | `_______________` |
| Certificate management | ☐ Manual &nbsp;&nbsp; ☐ cert-manager &nbsp;&nbsp; ☐ Cloud provider managed |

### Container Registry for ZenML Pro Images

Choose where ZenML Pro container images will be pulled from:

| Parameter | Value |
|-----------|-------|
| Image source | ☐ ZenML AWS ECR &nbsp;&nbsp; ☐ ZenML GCP Artifact Registry &nbsp;&nbsp; ☐ Private registry |
| Registry URL (if private) | `_______________` |
| Authentication method | ☐ AWS IAM Role &nbsp;&nbsp; ☐ GCP Service Account &nbsp;&nbsp; ☐ Docker credentials |
| IAM Role ARN / Service Account (if applicable) | `_______________` |
| Registry username (if Docker credentials) | `_______________` |
| Registry password/token (if Docker credentials) | `_______________` |

**Image URIs:**

| Image | URI |
|-------|-----|
| Control Plane API | `_______________` (e.g., `europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-api:<version>`) |
| Web UI (Dashboard) | `_______________` (e.g., `europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-dashboard:<version>`) |
| Workspace Server | `_______________` (e.g., `europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-server:<version>`) |

### SSO Configuration (if enabled)

Skip this section if using local accounts only.

| Parameter | Value |
|-----------|-------|
| Identity provider | `_______________` (e.g., Okta, Azure AD, Keycloak) |
| OIDC discovery URL | `_______________` (e.g., `https://idp.example.com/.well-known/openid-configuration`) |
| Client ID | `_______________` |
| Client secret | `_______________` |
| Redirect URI (configured in IdP) | `https://<web-ui-url>/api/auth/callback` |
| Post-logout redirect URI (if applicable) | `https://<web-ui-url>/api/auth/logout-complete` |
| IDP logout URI to call (if applicable) | `https://<idp-url>/v2/logout` |

## Next Steps

Once you have collected all the required information, proceed to the deployment guide for your chosen component and infrastructure type:

- [Control Plane Kubernetes Deployment](deploy-control-plane-k8s.md) — Deploy ZenML Pro control plane on Kubernetes using Helm charts
- [Workspace Server Kubernetes Deployment](deploy-workspace-k8s.md) — Deploy ZenML Pro workspace servers on Kubernetes using Helm charts
- [Workspace Server AWS ECS Deployment](deploy-workspace-ecs.md) — Deploy ZenML Pro workspace servers on AWS ECS
