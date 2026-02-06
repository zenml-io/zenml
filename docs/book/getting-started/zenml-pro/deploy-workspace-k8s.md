---
description: Deploy ZenML Pro workspaces on Kubernetes with Helm and enroll them in the ZenML Pro control plane
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

This guide provides step-by-step instructions for deploying ZenML Pro workspaces on Kubernetes using Helm and enrolling them in the ZenML Pro control plane.


## Prerequisites

Before starting, make sure you go through the [general prerequisites for hybrid deployments](hybrid-deployment-prerequisites.md) and have collected the necessary artifacts and information. Particular requirements for Kubernetes with Helm deployments are listed below.

**Infrastructure:**
- Kubernetes cluster (1.24+)

**Network:**
- Load balancer, network gateway or Ingress controllers etc. 
- Internal DNS resolution
- TLS certificates signed by your internal CA (or self-signed)
- Network connectivity between cluster components

**Tools (on a machine with internet access for initial setup):**
- Helm (3.0+)


### Enroll the Workspace in the ZenML Pro Control Plane

Before you can deploy a workspace, you need a ZenML Pro organization to enroll the workspace in. The enrollment procedure will create a workspace placeholder in the organization and generate the necessary enrollment credentials. You will use these credentials (e.g. workspace ID, enrollment key) to configure the workspace server during deployment.

Enrolling workspaces is currently only supported through the ZenML Pro OpenAPI interface or programmatically accessing the ZenML Pro API. There is no support for this in the ZenML Pro UI yet.

{% tabs %}
{% tab title="OpenAPI Interface" %}
First, log in to the ZenML Pro UI as usual. Then, to access the ZenML Pro OpenAPI interface, append the `/api/v1` path to the ZenML Pro server URL in your browser. For example: https://zenml-pro.my.domain/api/v1s

Using the OpenAPI interface, you can manage local user accounts by making requests to the `/api/v1/workspaces` endpoint. For example, to create a new super-user account:

![ZenML Pro OpenAPI Interface - Enroll Workspace](.gitbook/assets/pro-openapi-interface-03.png)
{% endtab %}

{% tab title="curl" %}
First, [create a personal access token (PAT)](personal-access-tokens.md) using the ZenML Pro UI. Then, use this PAT to enroll the workspace via curl:

```bash
# Create a new super-user account
curl -X POST "https://zenml-pro.my.domain/api/v1/workspaces?name=my-workspace&enroll=true" \
  -H "Authorization: Bearer <access-token>"
```

The response will contain all the necessary enrollment credentials for the workspace that you will need to configure the workspace server during deployment.

* the workspace ID
* the enrollment key
* the organization ID
* the organization name
* the workspace name


## Install the ZenML Pro Workspace Servers

### Step 1: Create Kubernetes Secrets

If you are using an internal container registry, you may need to create a secret to allow the ZenML Pro workspace servers to pull the images. The following is an example of how to do this:

```bash
# Create namespace for ZenML Pro
kubectl create namespace zenml-pro-workspace

# Create secret for internal registry credentials (if needed)
kubectl -n zenml-pro-workspace create secret docker-registry image-pull-secret \
  --docker-server=internal-registry.mycompany.com \
  --docker-username=<your-username> \
  --docker-password=<your-password>
```

You'll use this secret in the next step when configuring the Helm values for the ZenML Pro workspace server.

### Step 2: Configure Helm Values for Workspace Server

{% hint style="info" %}
The ZenML Pro workspace server is developed on top of the open-source ZenML server and inherits all its features and deployment options. This deployment also uses the open-source ZenML Helm chart, with the only notable differences being that the ZenML Pro workspace server is configured to connect to the ZenML Pro control plane and uses a different container image that is released separately from the open-source ZenML server.
{% endhint %}

The example below is a basic configuration for the ZenML Pro control plane Helm chart. For a full list of configurable values and documentation, also see the [OSS ZenML Helm chart on ArtifactHub](https://artifacthub.io/packages/helm/zenml/zenml).

For advanced deployment configurations, you can also consult the [Deploy with Helm](https://docs.zenml.io/deploying-zenml/deploying-zenml/deploy-with-helm) documentation, which covers topics such as:
* database configuration options
* external secrets store backends (AWS Secrets Manager, GCP Secret Manager, Azure Key Vault, HashiCorp Vault)
* database backup strategies

```yaml
# Set up imagePullSecrets to authenticate to the container registry where the
# ZenML Pro container images are hosted, if necessary (see the previous step)
imagePullSecrets:
  - name: image-pull-secret

zenml:
    analyticsOptIn: false
    threadPoolSize: 10
    database:
        maxOverflow: "-1"
        poolSize: "10"
        # Note: Workspace servers only support MySQL, not PostgreSQL
        url: mysql://zenml_workspace_user:password@mysql.internal.mycompany.com:3306/zenml_workspace
    image:
      # Change this to point to your own container repository
      repository: internal-registry.mycompany.com/zenml/zenml-pro-server
      # Or use this for direct GAR access:
      # repository: europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-server
      # Or use this for direct AWS ECR access:
      # repository: 715803424590.dkr.ecr.eu-central-1.amazonaws.com/zenml-pro-server

      # Use this only to override the default image tag whose default value is
      # the same as the Helm chart appVersion.
      # tag: <ZENML_PRO_VERSION>


    # The external URL where the ZenML Pro control plane API and UI are reachable.
    #
    # This should be set to the hostname that is associated with the Ingress
    # controller, load balancer or any other network gateway.
    serverURL: https://zenml-workspace.internal.mycompany.com

    # Ingress configuration, if you are using an Ingress controller.
    ingress:
        enabled: true
        # Use the same hostname configured in `serverURL`
        host: zenml-workspace.internal.mycompany.com

    # ZenML Pro configuration - this is the only configuration that is specific
    # to ZenML Pro.
    pro:
        enabled: true

        # The URL where the ZenML Pro control plane API is reachable.
        # Only set this if you are using a self-hosted ZenML Pro control plane.
        # Leave unset to use the default value of https://cloudapi.zenml.io
        # if you are using a hybrid SaaS/self-hosted deployment.
        apiURL: https://zenml-pro.internal.mycompany.com/api/v1

        # The URL where the ZenML Pro control plane UI is reachable.
        # Only set this if you are using a self-hosted ZenML Pro control plane.
        # Leave unset to use the default value of https://cloud.zenml.io
        # if you are using a hybrid SaaS/self-hosted deployment.
        dashboardURL: https://zenml-pro.internal.mycompany.com

        # These are the details obtained from the control plane when enrolling
        # the workspace.
        enrollmentKey: <enrollment-key-from-control-plane>
        organizationID: <your-organization-id>
        organizationName: <your-organization-name>
        workspaceID: <your-workspace-id>
        workspaceName: <your-workspace-name>

    # Replica count - use at least 2 for high availability
    replicaCount: 1

    # Secrets store configuration
    secretsStore:
        sql:
            encryptionKey: <generate-a-64-character-hex-key>
        type: sql

# These are the minimum resources required for the ZenML server. You can
# adjust them to your needs.
resources:
    limits:
        memory: 800Mi
    requests:
        cpu: 100m
        memory: 450Mi
```

**Minimum required settings:**

* the database credentials (`zenml.database.url`)
* the URL (`zenml.serverURL`) and Ingress hostname (`zenml.ingress.host`) where the ZenML Pro workspace server will be reachable
* the Pro configuration (`zenml.pro.*`) with your organization and workspace details

**Additional relevant settings:**

* configure container registry credentials (`imagePullSecrets`) if your cluster needs to authenticate to the container registry
* injecting custom CA certificates (`zenml.certificates`), especially important if the TLS certificates used by the ZenML Pro services are signed by a custom Certificate Authority
* configure HTTP proxy settings (`zenml.proxy`)
* custom container image repository location (`zenml.image.repository`)
* additional Ingress settings (`zenml.ingress`)
* Kubernetes resources allocated to the pods (`resources`)

### Step 3: Deploy the ZenML Pro Workspace Server with Helm

Using the remote Helm chart, if you have access to the internet:

```bash
helm install zenml oci://public.ecr.aws/zenml/zenml \
  --version <ZENML_OSS_VERSION> \
  --namespace zenml-workspace \
  --create-namespace \
  --values zenml-workspace-values.yaml
```

Using the local Helm chart, if you have downloaded the chart previously:

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

### Step 4: Install Internal CA Certificates

If the TLS certificates used by the ZenML Pro workspace server are signed by a custom Certificate Authority, you need to install the CA certificates on every machine that needs to access the ZenML workspace server.

#### System-wide Installation

On all client machines that will access the ZenML workspace server:

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

#### For Containerized Pipelines

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


### Access the Workspace UI

1. Open the ZenML Pro control plane UI in your browser
2. Sign in with your organization credentials
3. You should see your workspace running and ready to use in the organization it was enrolled in

### Access the Workspaces from ZenML CLI

To login to a workspace with the ZenML CLI:

```bash
zenml login <WORKSPACE_NAME>
```

### (Optional) Enable Snapshot Support / Workload Manager

The Workspace Server includes a workload manager feature that enables running pipelines directly from the ZenML Pro UI. This requires the workspace server to have access to a Kubernetes cluster where ad-hoc runner pods can be created.

{% hint style="warning" %}
The workload manager feature and snapshots are only available from ZenML workspace server version 0.90.0 onwards.
{% endhint %}

If you want to enable snapshot support for the ZenML Pro workspace server, you need to follow the instructions in the [Enable Snapshot Support](self-hosted-deployment-helm-snapshots.md) guide.

## Day 2 Operations

For information on upgrading ZenML Pro components, see the [Upgrades & Updates](upgrades-updates.md) guide.

## Related Resources

- [Self-hosted Deployment Overview](self-hosted-deployment.md)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [MySQL Documentation](https://dev.mysql.com/doc/)
- [Helm Documentation](https://helm.sh/docs/)

## Support

For self-hosted and hybrid SaaS/self-hosted deployments, contact ZenML Support:
- Email: [cloud@zenml.io](mailto:cloud@zenml.io)
- Provide: Deployment status, configuration details and any error logs

Request from ZenML Support:
- Pre-deployment architecture consultation
- Offline support packages
- Update bundles and release notes
- Security documentation (SBOM, vulnerability reports)

