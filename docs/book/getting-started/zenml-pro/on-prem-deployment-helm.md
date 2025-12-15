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

For a comprehensive look at each main component, see:

- [ZenML Pro Control Plane Service](../zenml-pro/self-hosted.md) – details for the central authentication, dashboard, and RBAC management service.
- [ZenML Pro Workspace Server Service](../zenml-pro/hybrid-deployment-helm.md) – details and configuration for individual workspace environments.

These pages offer full documentation, architecture, and details for each core ZenML Pro service.

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

## (Optional) Prepare Software Bundle for Air-Gapped Environment

If your network is fully air-gapped, you must prepare all required ZenML Pro deployment artifacts (container images, Helm charts, and a manifest file) ahead of time on a machine that has internet access, and transfer them into the secured environment.

**Overview of the steps:**

1. **Pull all required container images** from ZenML Pro registries (AWS ECR, GCP Artifact Registry, Docker Hub).
2. **Download Helm charts** for ZenML Pro Control Plane and Workspace Server.
3. **Create a bundle** of all images and charts, including a manifest file documenting versions and sources.
4. **Transfer the bundle** into your air-gapped environment using approved procedures.
5. **Load the images** into your internal registry for use by the cluster.

### Step 1: Prepare Images and Charts (on Internet-Connected Machine)

1. **Authenticate** to the ZenML Pro registries using credentials provided by ZenML.
2. **Pull the required images:**
   - Control Plane:
     - `715803424590.dkr.ecr.eu-west-1.amazonaws.com/zenml-pro-api:<version>`
     - `715803424590.dkr.ecr.eu-west-1.amazonaws.com/zenml-pro-dashboard:<version>`
   - Workspace Server:
     - `715803424590.dkr.ecr.eu-central-1.amazonaws.com/zenml-pro-server:<version>`
   - Client (pipelines, agents, etc.):
     - `zenmldocker/zenml:<version>`

   Example commands:
   ```bash
   docker pull 715803424590.dkr.ecr.eu-west-1.amazonaws.com/zenml-pro-api:<version>
   docker pull 715803424590.dkr.ecr.eu-west-1.amazonaws.com/zenml-pro-dashboard:<version>
   docker pull 715803424590.dkr.ecr.eu-central-1.amazonaws.com/zenml-pro-server:<version>
   docker pull zenmldocker/zenml:<version>
   ```

3. **(Optional)** Tag images for your internal registry, e.g.:
   ```
   docker tag 715803424590.dkr.ecr.eu-west-1.amazonaws.com/zenml-pro-api:<version> internal-registry.mycompany.com/zenml/zenml-pro-api:<version>
   ```

4. **Save all images as tar files:**
   ```bash
   docker save 715803424590.dkr.ecr.eu-west-1.amazonaws.com/zenml-pro-api:<version> > zenml-pro-api.tar
   docker save 715803424590.dkr.ecr.eu-west-1.amazonaws.com/zenml-pro-dashboard:<version> > zenml-pro-dashboard.tar
   docker save 715803424590.dkr.ecr.eu-central-1.amazonaws.com/zenml-pro-server:<version> > zenml-pro-server.tar
   docker save zenmldocker/zenml:<version> > zenml-client.tar
   ```

5. **Download Helm charts:**
   - ZenML Pro Control Plane: `oci://public.ecr.aws/zenml/zenml-pro`
   - ZenML Workspace Server: `oci://public.ecr.aws/zenml/zenml`
   
   Save as `.tgz` files, e.g.:
   ```bash
   helm pull oci://public.ecr.aws/zenml/zenml-pro --version <version> --destination ./charts
   helm pull oci://public.ecr.aws/zenml/zenml --version <version> --destination ./charts
   ```

6. **Organize your offline bundle directory:**

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

   The `manifest.txt` should include:
   - Image names and versions
   - Chart names and versions
   - Date of export
   - Intended internal registry URLs

### Step 2: Transfer Bundle to Air-Gapped Environment

Move the `zenml-air-gapped-bundle/` into your secure environment using only methods permitted by your security policy (e.g., encrypted USB drive, air-gap appliance, or secure internal transfer).

### Step 3: Load Images to Internal Registry (inside air-gapped network)

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

You are now ready to proceed with an air-gapped Helm-based deployment using your internal registry and the downloaded Helm chart tarballs.

## Step 1: Create Kubernetes Namespace and Secrets

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

## Step 2: Set Up Databases

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

## Step 3: Configure Helm Values for Control Plane

To learn more about the ZenML Pro control plane, see [Control Plane Architecture and Setup](control-plane.md).

The ZenML Pro Helm chart for on-prem deployments exposes many configurable values. For the full list and documentation of each field, consult the [ZenML Pro Helm chart reference](https://artifacthub.io/packages/helm/zenml-pro/zenml-pro).

### Minimum Helm values required for a control plane deployment

At a minimum, you must set:

- The image repositories and tags for API and Dashboard (pointing to your internal/private registry).
- The `serverURL` and ingress hostname (must match your TLS cert and DNS).
- The external database connection for the control plane.
- Admin password for the control plane.

Below is an example `zenml-pro-values.yaml`:

```yaml
zenml:
  image:
    api:
      repository: internal-registry.mycompany.com/zenml/zenml-pro-api
      tag: "<ZENML_PRO_VERSION>"
    dashboard:
      repository: internal-registry.mycompany.com/zenml/zenml-pro-dashboard
      tag: "<ZENML_PRO_VERSION>"

  serverURL: https://zenml-pro.internal.mycompany.com

  database:
    external:
      type: mysql
      host: <db-host>
      port: 3306
      username: <db-user>
      password: <db-password>
      database: zenml_pro

  ingress:
    enabled: true
    className: nginx
    host: zenml-pro.internal.mycompany.com
    tls:
      enabled: true
      secretName: zenml-tls

  auth:
    password: <admin-password>

  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 2000m
      memory: 4Gi

  # Add the secret if you use an internal registry
  imagePullSecrets:
    - name: internal-registry-secret
```

> Get the full list of available configurations and advanced options from the [Helm chart documentation](https://artifacthub.io/packages/helm/zenml-pro/zenml-pro) or by running `helm show values zenml-pro/zenml-pro`.

**Note:** 
- For high-availability, monitoring, backups, and advanced security options, see [the full Helm chart documentation](https://artifacthub.io/packages/helm/zenml-pro/zenml-pro).
- For breaking changes, new features, and release notes, always check the [ZenML Pro changelog](https://docs.zenml.io/changelog).

## Step 3: Deploy ZenML Pro Control Plane

Using the local Helm chart:

```bash
helm install zenml-pro ./zenml-pro-<ZENML_PRO_VERSION>.tgz \
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

## Step 4: Enroll Workspace in Control Plane

Before deploying the workspace server, you must enroll it in the control plane to obtain the necessary enrollment credentials.

1. **Access the Control Plane Dashboard**
   - Navigate to `https://zenml-pro.internal.mycompany.com`
   - Log in with your admin credentials

2. **Create an Organization** (if not already created)
   - Go to Organization settings
   - Create a new organization or use an existing one
   - Note the Organization ID and Name

3. **Enroll the Workspace**
   
   You can either use the enrollment script below or create a workspace through the dashboard.

   **Option A: Use the Enrollment Script**
   
   Run the `enroll-workspace.py` script below. It will collect all the necessary data, create a workspace placeholder in the organization, and generate a Helm `values.yaml` file template.

   <details>
   <summary>Click to expand enrollment script</summary>

   Save this as `enroll-workspace.py` and run it with `python enroll-workspace.py`:

   ```python
   import getpass
   import sys
   import uuid
   from typing import List, Optional, Tuple

   import requests

   DEFAULT_API_ROOT_PATH = "/api/v1"
   DEFAULT_REPOSITORY = (
       "715803424590.dkr.ecr.eu-central-1.amazonaws.com/zenml-pro-server"
   )

   # Configuration
   LOGIN_ENDPOINT = "/api/v1/auth/login"
   WORKSPACE_ENDPOINT = "/api/v1/workspaces"
   ORGANIZATION_ENDPOINT = "/api/v1/organizations"

   def login(base_url: str, username: str, password: str) -> str:
       """Log in and return the authentication token."""
       headers = {
           "accept": "application/json",
           "Content-Type": "application/x-www-form-urlencoded",
       }
       data = {
           "grant_type": "",
           "username": username,
           "password": password,
           "client_id": "",
           "client_secret": "",
           "device_code": "",
           "audience": "",
       }
       login_url = f"{base_url}{LOGIN_ENDPOINT}"
       response = requests.post(login_url, headers=headers, data=data)
       if response.status_code == 200:
           return response.json().get("access_token")
       else:
           print(f"Login failed. Status code: {response.status_code}")
           print(f"Response: {response.text}")
           sys.exit(1)

   def workspace_exists(
       token: str,
       base_url: str,
       org_id: str,
       workspace_name: Optional[str] = None,
   ) -> Optional[str]:
       """Get a workspace with a given name or url."""
       workspace_url = f"{base_url}{WORKSPACE_ENDPOINT}"
       headers = {
           "accept": "application/json",
           "Authorization": f"Bearer {token}",
       }
       params = {"organization_id": org_id}
       if workspace_name:
           params["workspace_name"] = workspace_name
       response = requests.get(workspace_url, params=params, headers=headers)
       if response.status_code == 200:
           json_response = response.json()
           if len(json_response) > 0:
               return json_response[0]["id"]
       else:
           print(f"Failed to fetch workspaces for organization: {org_id}")
           print(f"Status code: {response.status_code}")
           print(f"Response: {response.text}")
           sys.exit(1)
       return None

   def list_organizations(token: str, base_url: str) -> List[Tuple[str, str]]:
       """Get a list of organizations."""
       organization_url = f"{base_url}{ORGANIZATION_ENDPOINT}"
       headers = {
           "accept": "application/json",
           "Authorization": f"Bearer {token}",
       }
       response = requests.get(organization_url, headers=headers)
       if response.status_code == 200:
           json_response = response.json()
           return [(org["id"], org["name"]) for org in json_response]
       else:
           print("Failed to fetch organizations")
           print(f"Status code: {response.status_code}")
           print(f"Response: {response.text}")
           sys.exit(1)

   def enroll_workspace(
       token: str,
       base_url: str,
       org_id: str,
       workspace_name: str,
       delete_existing: Optional[str] = None,
   ) -> dict:
       """Enroll a workspace."""
       workspace_url = f"{base_url}{WORKSPACE_ENDPOINT}"
       headers = {
           "accept": "application/json",
           "Authorization": f"Bearer {token}",
       }
       if delete_existing:
           response = requests.delete(
               f"{workspace_url}/{delete_existing}",
               headers=headers,
           )
           if response.status_code == 200:
               print(f"Workspace deleted successfully: {delete_existing}")
           else:
               print(f"Failed to delete workspace: {delete_existing}")
               print(f"Status code: {response.status_code}")
               print(f"Response: {response.text}")
               sys.exit(1)
       response = requests.post(
           workspace_url,
           json={"name": workspace_name, "organization_id": org_id},
           params={"enroll": True},
           headers=headers,
       )
       if response.status_code == 200:
           workspace = response.json()
           workspace_id = workspace.get("id")
           print(f"Workspace enrolled successfully: {workspace_name} [{workspace_id}]")
           return workspace
       else:
           print(f"Failed to enroll workspace: {workspace_name}")
           print(f"Status code: {response.status_code}")
           print(f"Response: {response.text}")
           sys.exit(1)

   def prompt(
       prompt_text: str,
       default_value: Optional[str] = None,
       password: bool = False,
   ) -> str:
       """Prompt the user with a default value."""
       while True:
           if default_value:
               text = f"{prompt_text} [{default_value}]: "
           else:
               text = f"{prompt_text}: "
           if password:
               user_input = getpass.getpass(text)
           else:
               user_input = input(text)
           if user_input.strip() == "":
               if default_value:
                   return default_value
               print("Please provide a value.")
               continue
           return user_input

   def get_workspace_config(
       zenml_pro_url: str,
       organization_id: str,
       organization_name: str,
       workspace_id: str,
       workspace_name: str,
       enrollment_key: str,
       repository: str = DEFAULT_REPOSITORY,
   ) -> str:
       """Get the workspace configuration."""
       encryption_key = f"{uuid.uuid4().hex}{uuid.uuid4().hex}"
       short_workspace_id = workspace_id.replace("-", "")
       return f"""
   zenml:
       analyticsOptIn: false
       threadPoolSize: 20
       database:
           maxOverflow: "-1"
           poolSize: "10"
           # TODO: use the actual database host and credentials
           url: mysql://root:password@mysql.example.com:3306/zenml{short_workspace_id}
       image:
           # TODO: use your actual image repository (omit the tag, which is
           # assumed to be the same as the helm chart version)
           repository: {repository}
       # TODO: use your actual server domain here
       serverURL: https://zenml.{short_workspace_id}.example.com
       ingress:
           enabled: true
           # TODO: use your actual domain here
           host: zenml.{short_workspace_id}.example.com
       pro:
           apiURL: {zenml_pro_url}/api/v1
           dashboardURL: {zenml_pro_url}
           enabled: true
           enrollmentKey: {enrollment_key}
           organizationID: {organization_id}
           organizationName: {organization_name}
           workspaceID: {workspace_id}
           workspaceName: {workspace_name}
       replicaCount: 1
       secretsStore:
           sql:
               encryptionKey: {encryption_key}
           type: sql

   # TODO: these are the minimum resources required for the ZenML server.
   resources:
       limits:
           memory: 800Mi
       requests:
           cpu: 100m
           memory: 450Mi
   """

   def main() -> None:
       zenml_pro_url = prompt(
           "What is the URL of your ZenML Pro instance? (e.g. https://zenml-pro.mydomain.com)",
       )
       username = prompt("Enter the ZenML Pro admin account username", default_value="admin")
       password = prompt("Enter the ZenML Pro admin account password", password=True)
       token = login(zenml_pro_url, username, password)
       print("Login successful.")

       organizations = list_organizations(token=token, base_url=zenml_pro_url)
       if len(organizations) == 0:
           print("No organizations found. Please create an organization first.")
           sys.exit(1)
       elif len(organizations) == 1:
           organization_id, organization_name = organizations[0]
           confirm = prompt(
               f"The following organization was found: {organization_name} [{organization_id}]. "
               f"Use this organization? (y/n)",
               default_value="n",
           )
           if confirm.lower() != "y":
               print("Exiting.")
               sys.exit(0)
       else:
           while True:
               orgs_str = "\n".join([f"{name} [{id}]" for id, name in organizations])
               print(f"The following organizations are available:\n{orgs_str}")
               organization_id = prompt("Which organization ID should the workspace be enrolled in?")
               if organization_id in [id for id, _ in organizations]:
                   break
               print("Invalid organization ID. Please try again.")

       workspace_name = f"zenml-{str(uuid.uuid4())[:8]}"
       workspace_name = prompt(
           "Choose a name for the workspace (only lowercase letters, numbers, and hyphens)",
           default_value=workspace_name,
       )
       existing_workspace_id = workspace_exists(
           token=token, base_url=zenml_pro_url, org_id=organization_id, workspace_name=workspace_name
       )
       if existing_workspace_id:
           confirm = prompt(
               f"A workspace with name {workspace_name} already exists. Overwrite? (y/n)",
               default_value="n",
           )
           if confirm.lower() != "y":
               print("Exiting.")
               sys.exit(0)

       workspace = enroll_workspace(
           token=token,
           base_url=zenml_pro_url,
           org_id=organization_id,
           workspace_name=workspace_name,
           delete_existing=existing_workspace_id,
       )
       workspace_id = workspace.get("id")
       organization_name = workspace.get("organization").get("name")
       enrollment_key = workspace.get("enrollment_key")

       workspace_config = get_workspace_config(
           zenml_pro_url=zenml_pro_url,
           workspace_name=workspace_name,
           workspace_id=workspace_id,
           organization_id=organization_id,
           organization_name=organization_name,
           enrollment_key=enrollment_key,
       )
       values_file = f"zenml-{workspace_name}-values.yaml"
       with open(values_file, "w") as file:
           file.write(workspace_config)

       print(f"""
   The workspace was enrolled successfully. It can be accessed at:
   {zenml_pro_url}/workspaces/{workspace_name}

   The workspace server Helm values were written to: {values_file}
   Please note the TODOs in the file and adjust them to your needs.

   To install the workspace, run:
       helm --namespace zenml-pro-{workspace_name} upgrade --install --create-namespace \\
           zenml oci://public.ecr.aws/zenml/zenml --version <version> \\
           --values {values_file}
   """)

   if __name__ == "__main__":
       main()
   ```

   </details>

   **Option B: Create via Dashboard**
   
   Create a workspace through the dashboard and obtain:
   - Enrollment Key
   - Organization ID
   - Organization Name
   - Workspace ID
   - Workspace Name

4. **Save these values** - you'll need them in the next step

## Step 5: Configure Helm Values for Workspace Server

The ZenML workspace server uses the open-source ZenML Helm chart. For the full list of configurable values and documentation, see the [ZenML Helm chart on ArtifactHub](https://artifacthub.io/packages/helm/zenml/zenml).

Create a file `zenml-workspace-values.yaml`:

```yaml
zenml:
  # Image configuration - use your internal registry
  image:
    repository: internal-registry.mycompany.com/zenml/zenml-pro-server
    tag: "<ZENML_OSS_VERSION>"  # e.g., "0.73.0"

  # Server URL
  serverURL: https://zenml-workspace.internal.mycompany.com

  # Database for Workspace
  # Note: Workspace servers only support MySQL, not PostgreSQL
  database:
    external:
      type: mysql
      host: mysql.internal.mycompany.com
      port: 3306
      username: zenml_workspace_user
      password: <secure-password>
      database: zenml_workspace

  # Pro configuration - connect to local control plane
  pro:
    enabled: true
    apiURL: https://zenml-pro.internal.mycompany.com/api/v1
    dashboardURL: https://zenml-pro.internal.mycompany.com
    enrollmentKey: <enrollment-key-from-control-plane>
    organizationID: <your-organization-id>
    organizationName: <your-organization-name>
    workspaceID: <your-workspace-id>
    workspaceName: <your-workspace-name>

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

## Step 6: Deploy ZenML Workspace Server

```bash
# Create namespace
kubectl create namespace zenml-workspace

# Deploy workspace
helm install zenml ./zenml-<ZENML_OSS_VERSION>.tgz \
  --namespace zenml-workspace \
  --values zenml-workspace-values.yaml
```

Verify deployment:

```bash
kubectl -n zenml-workspace get pods
kubectl -n zenml-workspace get svc
kubectl -n zenml-workspace get ingress
```

## Step 7: Configure Internal DNS

Update your internal DNS to resolve:
- `zenml-pro.internal.mycompany.com` → Your ALB/Ingress IP
- `zenml-workspace.internal.mycompany.com` → Your ALB/Ingress IP

## Step 8: Install Internal CA Certificate

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

## Step 9: Verify the Deployment

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

## Step 10: (Optional) Enable Snapshot Support / Workload Manager

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
    ZENML_KUBERNETES_WORKLOAD_MANAGER_RUNNER_IMAGE: internal-registry.mycompany.com/zenml/zenml:<ZENML_OSS_VERSION>
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

## Step 11: Create Users and Organizations

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

The latest versions of ZenML images and Helm charts can be discovered and reviewed at:

- **ZenML Pro Helm chart**: [artifacthub.io/packages/helm/zenml-pro/zenml-pro](https://artifacthub.io/packages/helm/zenml-pro/zenml-pro)
- **ZenML (OSS/workspace) Helm chart**: [artifacthub.io/packages/helm/zenml/zenml](https://artifacthub.io/packages/helm/zenml/zenml)
- **ZenML container images**: Tags are published alongside each [release on ArtifactHub](https://artifacthub.io/packages/helm/zenml/zenml) and [ZenML changelog](https://docs.zenml.io/changelog).
- **Changelog and release notes** for updates and migrations: [ZenML Changelog](https://docs.zenml.io/changelog)

When preparing for an update or upgrade, always consult the changelog for:
- New Helm chart releases and corresponding Helm values
- Updated container image tags (OSS and Pro)
- Migration requirements and compatibility notes
- Security/vulnerability disclosures

For air-gapped or regulated environments, coordinate with ZenML Support to acquire new versions in the format required for your infrastructure.

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


## Support

For air-gapped deployments, contact ZenML Support:
- Email: [cloud@zenml.io](mailto:cloud@zenml.io)
- Provide: Your offline bundle, deployment status, and any error logs

Request from ZenML Support:
- Pre-deployment architecture consultation
- Offline support packages
- Update bundles and release notes
- Security documentation (SBOM, vulnerability reports)
