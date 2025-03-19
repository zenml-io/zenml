---
description: Guide for installing ZenML Pro self-hosted in a Kubernetes cluster.
---

# Self-hosted deployment

This page provides instructions for installing ZenML Pro - the ZenML Pro Control Plane and one or more ZenML Pro Workspace servers - on-premise in a Kubernetes cluster.

## Overview

ZenML Pro can be installed as a self-hosted deployment. You need to be granted access to the ZenML Pro container images and you'll have to provide your own infrastructure: a Kubernetes cluster, a database server and a few other common prerequisites usually needed to expose Kubernetes services via HTTPs - a load balancer, an Ingress controller, HTTPs certificate(s) and DNS rule(s).

This document will guide you through the process.

{% hint style="info" %}
Please note that the SSO (Single Sign-On) and [Run Templates](https://docs.zenml.io/how-to/trigger-pipelines) (i.e. running pipelines from the dashboard) features are currently not available in the on-prem version of ZenML Pro. These features are on our roadmap and will be added in future releases.
{% endhint %}

## Preparation and prerequisites

### Software Artifacts

The ZenML Pro on-prem installation relies on a set of container images and Helm charts. The container images are stored in private ZenML container registries that are not available to the public.

If you haven't done so already, please [book a demo](https://www.zenml.io/book-your-demo) to get access to the private ZenML Pro container images.

#### ZenML Pro Control Plane Artifacts

The following artifacts are required to install the ZenML Pro control plane in your own Kubernetes cluster:

* private container images for the ZenML Pro API server:
  * `715803424590.dkr.ecr.eu-west-1.amazonaws.com/zenml-pro-api` in AWS
  * `europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-api` in GCP
* private container images for the ZenML Pro dashboard:
  * `715803424590.dkr.ecr.eu-west-1.amazonaws.com/zenml-pro-dashboard` in AWS
  * `europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-dashboard` in GCP
* the public ZenML Pro helm chart (as an OCI artifact): `oci://public.ecr.aws/zenml/zenml-pro`

{% hint style="info" %}
The container image tags and the Helm chart versions are both synchronized and linked to the ZenML Pro releases. You can find the ZenML Pro Helm chart along with the available released versions in the [ZenML Pro ArtifactHub repository](https://artifacthub.io/packages/helm/zenml-pro/zenml-pro).

If you're planning on copying the container images to your own private registry (recommended if your Kubernetes cluster isn't running on AWS and can't authenticate directly to the ZenML Pro container registry) make sure to include and keep the same tags.

By default, the ZenML Pro Helm chart uses the same container image tags as the helm chart version. Configuring custom container image tags when setting up your Helm distribution is also possible, but not recommended because it doesn't yield reproducible results and may even cause problems if used with the wrong Helm chart version.
{% endhint %}

#### ZenML Pro Workspace Server Artifacts

The following artifacts are required to install ZenML Pro workspace servers in your own Kubernetes cluster:

* private container images for the ZenML Pro workspace server:
  * `715803424590.dkr.ecr.eu-central-1.amazonaws.com/zenml-pro-server` in AWS
  * `europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-server` in GCP
* the public open-source ZenML Helm chart (as an OCI artifact): `oci://public.ecr.aws/zenml/zenml`

{% hint style="info" %}
The container image tags and the Helm chart versions are both synchronized and linked to the ZenML open-source releases. To find the latest ZenML OSS release, please check the [ZenML OSS ArtifactHub repository (Helm chart versions)](https://artifacthub.io/packages/helm/zenml/zenml) or the [ZenML release page](https://github.com/zenml-io/zenml/releases).

If you're planning on copying the container images to your own private registry (recommended if your Kubernetes cluster isn't running on AWS and can't authenticated directly to the ZenML Pro container registry) make sure to include and keep the same tags.

By default, the ZenML OSS Helm chart uses the same container image tags as the helm chart version. Configuring custom container image tags when setting up your Helm distribution is also possible, but not recommended because it doesn't yield reproducible results and may even cause problems if used with the wrong Helm chart version.
{% endhint %}

#### ZenML Pro Client Artifacts

If you're planning on running containerized ZenML pipelines, or using other containerization related ZenML features, you'll also need to access the public ZenML client container image located [in Docker Hub at `zenmldocker/zenml`](https://hub.docker.com/r/zenmldocker/zenml). This isn't a problem unless you're deploying ZenML Pro in an air-gapped environment, in which case you'll also have to copy the client container image into your own container registry. You'll also have to configure your code to use the correct base container registry via DockerSettings (see the [DockerSettings documentation](https://docs.zenml.io/how-to/customize-docker-builds) for more information).

### Accessing the ZenML Pro Container Images

This section provides instructions for how to access the private ZenML Pro container images.

{% hint style="info" %}
Currently, ZenML Pro container images are only available in AWS Elastic Container Registry (ECR) and Google Cloud Platform (GCP) Artifact Registry. Support for Azure Container Registry (ACR) is on our roadmap and will be added soon.

The ZenML support team can provide credentials upon request, which can be used to pull these images without the need to set up any cloud provider accounts or resources. Contact support if you'd prefer this option.
{% endhint %}

#### AWS

To access the ZenML Pro container images stored in AWS ECR, you need to set up an AWS IAM user or IAM role in your AWS account. The steps below outline how to create an AWS account, configure the necessary IAM entities, and pull images from the private repositories. If you're familiar with AWS or even plan on using an AWS EKS cluster to deploy ZenML Pro, then you can simply use your existing IAM user or IAM role and skip steps 1. and 2.

***

*   **Step 1: Create a Free AWS Account**

    1. Visit the [AWS Free Tier page](https://aws.amazon.com/free/).
    2. Click **Create a Free Account**.
    3. Follow the on-screen instructions to provide your email address, create a root user, and set a secure password.
    4. Enter your contact and payment information for verification purposes. While a credit or debit card is required, you won't be charged for free-tier eligible services.
    5. Confirm your email and complete the verification process.
    6. Log in to the AWS Management Console using your root user credentials.

    ***
*   **Step 2: Create an IAM User or IAM Role**

    **A. Create an IAM User**

    1. Log in to the AWS Management Console.
    2. Navigate to the **IAM** service.
    3. Click **Users** in the left-hand menu, then click **Add Users**.
    4. Provide a user name (e.g., `zenml-ecr-access`).
    5. Select **Access Key - Programmatic access** as the AWS credential type.
    6. Click **Next: Permissions**.
    7. Choose **Attach policies directly**, then select the following policies:
       * **AmazonEC2ContainerRegistryReadOnly**
    8. Click **Next: Tags** and optionally add tags for organization purposes.
    9. Click **Next: Review**, then **Create User**.
    10. Note the **Access Key ID** and **Secret Access Key** displayed after creation. Save these securely.

    **B. Create an IAM Role**

    1. Navigate to the **IAM** service.
    2. Click **Roles** in the left-hand menu, then click **Create Role**.
    3. Choose the type of trusted entity:
       * Select **AWS Account**.
    4. Enter your AWS account ID and click **Next**.
    5. Select the **AmazonEC2ContainerRegistryReadOnly** policy.
    6. Click **Next: Tags**, optionally add tags, then click **Next: Review**.
    7. Provide a role name (e.g., `zenml-ecr-access-role`) and click **Create Role**.

    ***
*   **Step 3: Provide the IAM User/Role ARN**

    1. For an IAM user, the ARN can be found in the **Users** section under the **Summary** tab.
    2. For an IAM role, the ARN is displayed in the **Roles** section under the **Summary** tab.

    Send the ARN to ZenML Support so it can be granted permission to access the ZenML Pro container images and Helm charts.

    ***
*   **Step 4: Authenticate your Docker Client**

    Run these steps on the machine that you'll use to pull the ZenML Pro images. It is recommended that you copy the container images into your own container registry that will be accessible from the Kubernetes cluster where ZenML Pro will be stored, otherwise you'll have to find a way to configure the Kubernetes cluster to authenticate directly to the ZenML Pro container registry and that will be problematic if your Kubernetes cluster is not running on AWS.

    **A. Install AWS CLI**

    1. Follow the instructions to install the AWS CLI: [AWS CLI Installation Guide](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html).

    **B. Configure AWS CLI Credentials**

    1. Open a terminal and run `aws configure`
    2. Enter the following when prompted:
       * **Access Key ID**: Provided during IAM user creation.
       * **Secret Access Key**: Provided during IAM user creation.
       * **Default region name**: `eu-west-1`
       * **Default output format**: Leave blank or enter `json`.
    3.  If you chose to use an IAM role, update the AWS CLI configuration file to specify the role you want to assume. Open the configuration file located at `~/.aws/config` and add the following:

        ```bash
        [profile zenml-ecr-access]
        role_arn = <IAM-ROLE-ARN>
        source_profile = default
        region = eu-west-1
        ```

        Replace `<IAM-ROLE-ARN>` with the ARN of the role you created and ensure `source_profile` points to a profile with sufficient permissions to assume the role.

    **C. Authenticate Docker with ECR**

    Run the following command to authenticate your Docker client with the ZenML ECR repository:

    ```bash
    aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin 715803424590.dkr.ecr.eu-west-1.amazonaws.com
    aws ecr get-login-password --region eu-central-1 | docker login --username AWS --password-stdin 715803424590.dkr.ecr.eu-central-1.amazonaws.com
    ```

    If you used an IAM role, use the specified profile to execute commands. For example:

    ```bash
    aws ecr get-login-password --region eu-west-1 --profile zenml-ecr-access | docker login --username AWS --password-stdin 715803424590.dkr.ecr.eu-west-1.amazonaws.com
    aws ecr get-login-password --region eu-central-1 --profile zenml-ecr-access | docker login --username AWS --password-stdin 715803424590.dkr.ecr.eu-central-1.amazonaws.com
    ```

    This will allow you to authenticate to the ZenML Pro container registries and pull the necessary images with Docker, e.g.:

    ```bash
    # Pull the ZenML Pro API image
    docker pull 715803424590.dkr.ecr.eu-west-1.amazonaws.com/zenml-pro-api:<zenml-pro-version>
    # Pull the ZenML Pro Dashboard image
    docker pull 715803424590.dkr.ecr.eu-west-1.amazonaws.com/zenml-pro-dashboard:<zenml-pro-version>
    # Pull the ZenML Pro Server image
    docker pull 715803424590.dkr.ecr.eu-central-1.amazonaws.com/zenml-pro-server:<zenml-oss-version>
    ```

{% hint style="info" %}
To decide which tag to use, you should check:

* for the available ZenML Pro versions: the [ZenML Pro ArtifactHub repository (Helm chart versions)](https://artifacthub.io/packages/helm/zenml-pro/zenml-pro)
* for the available ZenML OSS versions: the [ZenML OSS ArtifactHub repository (Helm chart versions)](https://artifacthub.io/packages/helm/zenml/zenml) or the [ZenML GitHub releases page](https://github.com/zenml-io/zenml/releases)

Note that the `zenml-pro-api` and `zenml-pro-dashboard` images are stored in the `eu-west-1` region, while the `zenml-pro-server` image is stored in the `eu-central-1` region.
{% endhint %}

#### GCP

To access the ZenML Pro container images stored in Google Cloud Platform (GCP) Artifact Registry, you need to set up a GCP account and configure the necessary permissions. The steps below outline how to create a GCP account, configure authentication, and pull images from the private repositories. If you're familiar with GCP or plan on using a GKE cluster to deploy ZenML Pro, you can use your existing GCP account and skip step 1.

***

*   **Step 1: Create a GCP Account**

    1. Visit the [Google Cloud Console](https://console.cloud.google.com/).
    2. Click **Get Started for Free** or sign in with an existing Google account.
    3. Follow the on-screen instructions to set up your account and create a project.
    4. Set up billing information (required for using GCP services).

    ***
*   **Step 2: Create a Service Account**

    1. Navigate to the [IAM & Admin > Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts) page in the Google Cloud Console.
    2. Click **Create Service Account**.
    3. Enter a service account name (e.g., `zenml-gar-access`).
    4. Add a description (optional) and click **Create and Continue**.
    5. No additional permissions are needed as access will be granted directly to the Artifact Registry.
    6. Click **Done**.
    7. After creation, click on the service account to view its details.
    8. Go to the **Keys** tab and click **Add Key > Create new key**.
    9. Choose **JSON** as the key type and click **Create**.
    10. Save the downloaded JSON key file securely - you'll need it later.

    ***
*   **Step 3: Provide the Service Account Email**

    1. In the service account details page, copy the service account email address (it should look like `zenml-gar-access@your-project.iam.gserviceaccount.com`).
    2. Send this email address to ZenML Support so it can be granted permission to access the ZenML Pro container images.

    ***
*   **Step 4: Authenticate your Docker Client**

    Run these steps on the machine that you'll use to pull the ZenML Pro images. It is recommended that you copy the container images into your own container registry that will be accessible from the Kubernetes cluster where ZenML Pro will be stored.

    **A. Install Google Cloud CLI**

    1. Follow the instructions to install the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install).
    2.  Initialize the CLI by running:

        ```bash
        gcloud init
        ```

    **B. Configure Authentication**

    1.  Activate the service account using the JSON key file you downloaded:

        ```bash
        gcloud auth activate-service-account --key-file=/path/to/your-key-file.json
        ```
    2.  Configure Docker authentication for Artifact Registry:

        ```bash
        gcloud auth configure-docker europe-west3-docker.pkg.dev
        ```

    **C. Pull the Container Images**

    You can now pull the ZenML Pro images:

    ```bash
    # Pull the ZenML Pro API image
    docker pull europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-api:<zenml-pro-version>
    # Pull the ZenML Pro Dashboard image
    docker pull europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-dashboard:<zenml-pro-version>
    # Pull the ZenML Pro Server image
    docker pull europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-server:<zenml-oss-version>
    ```

{% hint style="info" %}
To decide which tag to use, you should check:

* for the available ZenML Pro versions: the [ZenML Pro ArtifactHub repository (Helm chart versions)](https://artifacthub.io/packages/helm/zenml-pro/zenml-pro)
* for the available ZenML OSS versions: the [ZenML OSS ArtifactHub repository (Helm chart versions)](https://artifacthub.io/packages/helm/zenml/zenml) or the [ZenML GitHub releases page](https://github.com/zenml-io/zenml/releases)
{% endhint %}

### Air-Gapped Installation

If you need to install ZenML Pro in an air-gapped environment (a network with no direct internet access), you'll need to transfer all required artifacts to your internal infrastructure. Here's a step-by-step process:

**1. Prepare a Machine with Internet Access**

First, you'll need a machine with both internet access and sufficient storage space to temporarily store all artifacts. On this machine:

1. Follow the authentication steps described above to gain access to the private repositories
2. Install the required tools:
   * Docker
   * Helm

**2. Download All Required Artifacts**

A Bash script like the following can be used to download all necessary components, or you can run the listed commands manually:

```bash
#!/bin/bash

set -e

# Set the version numbers
ZENML_PRO_VERSION="<version>"  # e.g., "0.10.24"
ZENML_OSS_VERSION="<version>"  # e.g., "0.73.0"

# Create directories for artifacts
mkdir -p zenml-artifacts/images
mkdir -p zenml-artifacts/charts

# Set registry URLs
# Use the following if you're pulling from the ZenML private ECR registry
ZENML_PRO_REGISTRY="715803424590.dkr.ecr.eu-west-1.amazonaws.com"
ZENML_PRO_SERVER_REGISTRY="715803424590.dkr.ecr.eu-central-1.amazonaws.com"
# Use the following if you're pulling from the ZenML private GCP Artifact Registry
# ZENML_PRO_REGISTRY="europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro"
# ZENML_PRO_SERVER_REGISTRY=$ZENML_PRO_REGISTRY
ZENML_HELM_REGISTRY="public.ecr.aws/zenml"
ZENML_DOCKERHUB_REGISTRY="zenmldocker"

# Download container images
echo "Downloading container images..."
docker pull ${ZENML_PRO_REGISTRY}/zenml-pro-api:${ZENML_PRO_VERSION}
docker pull ${ZENML_PRO_REGISTRY}/zenml-pro-dashboard:${ZENML_PRO_VERSION}
docker pull ${ZENML_PRO_SERVER_REGISTRY}/zenml-pro-server:${ZENML_OSS_VERSION}
docker pull ${ZENML_DOCKERHUB_REGISTRY}/zenml:${ZENML_OSS_VERSION}

# Save images to tar files
echo "Saving images to tar files..."
docker save ${ZENML_PRO_REGISTRY}/zenml-pro-api:${ZENML_PRO_VERSION} > zenml-artifacts/images/zenml-pro-api.tar
docker save ${ZENML_PRO_REGISTRY}/zenml-pro-dashboard:${ZENML_PRO_VERSION} > zenml-artifacts/images/zenml-pro-dashboard.tar
docker save ${ZENML_PRO_SERVER_REGISTRY}/zenml-pro-server:${ZENML_OSS_VERSION} > zenml-artifacts/images/zenml-pro-server.tar
docker save ${ZENML_DOCKERHUB_REGISTRY}/zenml:${ZENML_OSS_VERSION} > zenml-artifacts/images/zenml-client.tar

# Download Helm charts
echo "Downloading Helm charts..."
helm pull oci://${ZENML_HELM_REGISTRY}/zenml-pro --version ${ZENML_PRO_VERSION} -d zenml-artifacts/charts
helm pull oci://${ZENML_HELM_REGISTRY}/zenml --version ${ZENML_OSS_VERSION} -d zenml-artifacts/charts

# Create a manifest file with versions
echo "Creating manifest file..."
cat > zenml-artifacts/manifest.txt << EOF
ZenML Pro Version: ${ZENML_PRO_VERSION}
ZenML OSS Version: ${ZENML_OSS_VERSION}
Date Created: $(date)

Container Images:
- zenml-pro-api:${ZENML_PRO_VERSION}
- zenml-pro-dashboard:${ZENML_PRO_VERSION}
- zenml-pro-server:${ZENML_OSS_VERSION}
- zenml-client:${ZENML_OSS_VERSION}

Helm Charts:
- zenml-pro-${ZENML_PRO_VERSION}.tgz
- zenml-${ZENML_OSS_VERSION}.tgz
EOF

# Create final archive
echo "Creating final archive..."
tar czf zenml-artifacts.tar.gz zenml-artifacts/
```

**3. Transfer Artifacts to Air-Gapped Environment**

1. Copy the `zenml-artifacts.tar.gz` file to your preferred transfer medium (e.g., USB drive, approved file transfer system)
2. Transfer the archive to a machine in your air-gapped environment that has access to your internal container registry

**4. Load Artifacts in Air-Gapped Environment**

Create a script to load the artifacts in your air-gapped environment or run the listed commands manually:

```bash
#!/bin/bash

set -e

# Extract the archive
echo "Extracting archive..."
tar xzf zenml-artifacts.tar.gz

# Read the manifest
echo "Manifest:"
cat zenml-artifacts/manifest.txt

# Load images and track which ones were loaded
echo "Loading images into Docker..."
LOADED_IMAGES=()

# Load each image and capture its reference
image_ref=$(docker load < zenml-artifacts/images/zenml-pro-api.tar | grep "Loaded image:" | cut -d' ' -f3)
LOADED_IMAGES+=("$image_ref")
echo "Loaded image: $image_ref"

image_ref=$(docker load < zenml-artifacts/images/zenml-pro-dashboard.tar | grep "Loaded image:" | cut -d' ' -f3)
LOADED_IMAGES+=("$image_ref")
echo "Loaded image: $image_ref"

image_ref=$(docker load < zenml-artifacts/images/zenml-pro-server.tar | grep "Loaded image:" | cut -d' ' -f3)
LOADED_IMAGES+=("$image_ref")
echo "Loaded image: $image_ref"

image_ref=$(docker load < zenml-artifacts/images/zenml-client.tar | grep "Loaded image:" | cut -d' ' -f3)
LOADED_IMAGES+=("$image_ref")
echo "Loaded image: $image_ref"
# Tag and push images to your internal registry
INTERNAL_REGISTRY="internal-registry.company.com"

echo "Pushing images to internal registry..."
for img in "${LOADED_IMAGES[@]}"; do
    # Get the image name without the repository and tag
    img_name=$(echo $img | awk -F/ '{print $NF}' | cut -d: -f1)
    # Get the tag
    tag=$(echo $img | cut -d: -f2)
    
    echo "Processing $img"
    docker tag "$img" "${INTERNAL_REGISTRY}/zenml/$img_name:$tag"
    docker push "${INTERNAL_REGISTRY}/zenml/$img_name:$tag"
    echo "Pushed image: ${INTERNAL_REGISTRY}/zenml/$img_name:$tag"
done

# Copy Helm charts to your internal Helm repository (if applicable)
echo "Helm charts are available in: zenml-artifacts/charts/"
```

**5. Update Configuration**

When deploying ZenML Pro in your air-gapped environment, make sure to update all references to container images in your Helm values to point to your internal registry. For example:

```yaml
zenml:
  image:
    api:
      repository: internal-registry.company.com/zenml/zenml-pro-api
    dashboard:
      repository: internal-registry.company.com/zenml/zenml-pro-dashboard
```

{% hint style="info" %}
Remember to maintain the same version tags when copying images to your internal registry to ensure compatibility between components.
{% endhint %}

{% hint style="warning" %}
The scripts provided above are examples and may need to be adjusted based on your specific security requirements and internal infrastructure setup.
{% endhint %}

**6. Using the Helm Charts**

After downloading the Helm charts, you can use their local paths instead of a remote OCI registry to deploy ZenML Pro components. Here's an example of how to use them:

```bash
# Install the ZenML Pro Control Plane (e.g. zenml-pro-0.10.24.tgz)
helm install zenml-pro ./zenml-artifacts/charts/zenml-pro-<version>.tgz \
  --namespace zenml-pro \
  --create-namespace \
  --values your-values.yaml

# Install a ZenML Pro Workspace Server (e.g. zenml-0.73.0.tgz)
helm install zenml-workspace ./zenml-artifacts/charts/zenml-<version>.tgz \
  --namespace zenml-workspace \
  --create-namespace \
  --values your-workspace-values.yaml
```

### Infrastructure Requirements

To deploy the ZenML Pro control plane and one or more ZenML Pro workspace servers, ensure the following prerequisites are met:

1.  **Kubernetes Cluster**

    A functional Kubernetes cluster is required as the primary runtime environment.
2.  **Database Server(s)**

    The ZenML Pro Control Plane and ZenML Pro Workspace servers need to connect to an external database server. To minimize the amount of infrastructure resources needed, you can use a single database server in common for the Control Plane and for all workspaces, or you can use different database servers to ensure server-level database isolation, as long as you keep in mind the following limitations:

    * the ZenML Pro Control Plane can be connected to either MySQL or Postgres as the external database
    * the ZenML Pro Workspace servers can only be connected to a MySQL database (no Postgres support is available)
    * the ZenML Pro Control Plane as well as every ZenML Pro Workspace server needs to use its own individual database (especially important when connected to the same server)

    Ensure you have a valid username and password for the different ZenML Pro services. For improved security, it is recommended to have different users for different services. If the database user does not have permissions to create databases, you must also create a database and give the user full permissions to access and manage it (i.e. create, update and delete tables).
3.  **Ingress Controller**

    Install an Ingress provider in the cluster (e.g., NGINX, Traefik) to handle HTTP(S) traffic routing. Ensure the Ingress provider is properly configured to expose the cluster's services externally.
4.  **Domain Name**

    You'll need an FQDN for the ZenML Pro Control Plane as well as for every ZenML Pro workspace. For this reason, it's highly recommended to use a DNS prefix and associated SSL certificate instead of individual FQDNs and SSL certificates, to make this process easier.

    * **FQDN or DNS Prefix Setup**\
      Obtain a Fully Qualified Domain Name (FQDN) or DNS prefix (e.g., `*.zenml-pro.mydomain.com`) from your DNS provider.
      * Identify the external Load Balancer IP address of the Ingress controller using the command `kubectl get svc -n <ingress-namespace>`. Look for the `EXTERNAL-IP` field of the Load Balancer service.
      * Create a DNS `A` record (or `CNAME` for subdomains) pointing the FQDN to the Load Balancer IP. Example:
        * Host: `zenml-pro.mydomain.com`
        * Type: `A`
        * Value: `<Load Balancer IP>`
      * Use a DNS propagation checker to confirm that the DNS record is resolving correctly.

{% hint style="warning" %}
Make sure you don't use a simple DNS prefix for the servers (e.g. `https://zenml.cluster` is not recommended). This is especially relevant for the TLS certificates that you have to prepare for these endpoints. Always use a fully qualified domain name (FQDN) (e.g. `https://zenml.ml.cluster`). The TLS certificates will not be accepted by some browsers otherwise (e.g. Chrome).
{% endhint %}

5.  **SSL Certificate**

    The ZenML Pro services do not terminate SSL traffic. It is your responsibility to generate and configure the necessary SSL certificates for the ZenML Pro Control Plane as well as all the ZenML Pro workspaces that you will deploy (see the previous point on how to use a DNS prefix to make the process easier).

    *   **Obtaining SSL Certificates**

        Acquire an SSL certificate for the domain. You can use:

        * A commercial SSL certificate provider (e.g., DigiCert, Sectigo).
        * Free services like [Let's Encrypt](https://letsencrypt.org/) for domain validation and issuance.
        * Self-signed certificates (not recommended for production environments). **IMPORTANT**: If you are using self-signed certificates, it is highly recommended to use the same self-signed CA certificate for all the ZenML Pro services (control plane and workspace servers), otherwise it will be difficult to manage the certificates on the client machines. With only one CA certificate, you can install it system-wide on all the client machines only once and then use it to sign all the TLS certificates for the ZenML Pro services.
    *   **Configuring SSL Termination**

        Once the SSL certificate is obtained, configure your load balancer or Ingress controller to terminate HTTPS traffic:

        **For NGINX Ingress Controller**:

        You can configure SSL termination globally for the NGINX Ingress Controller by setting up a default SSL certificate or configuring it at the ingress controller level, or you can specify SSL certificates when configuring the ingress in the ZenML server Helm values.

        Here's how you can do it globally:

        1.  **Create a TLS Secret**

            Store your SSL certificate and private key as a Kubernetes TLS secret in the namespace where the NGINX Ingress Controller is deployed.

            ```bash
            kubectl create secret tls default-ssl-secret \\
              --cert=/path/to/tls.crt \\
              --key=/path/to/tls.key \\
              -n <nginx-ingress-namespace>

            ```
        2.  **Update NGINX Ingress Controller Configurations**

            Configure the NGINX Ingress Controller to use the default SSL certificate.

            *   If using the NGINX Ingress Controller Helm chart, modify the `values.yaml` file or use `-set` during installation:

                ```yaml
                controller:
                  extraArgs:
                    default-ssl-certificate: <nginx-ingress-namespace>/default-ssl-secret

                ```

                Or directly pass the argument during Helm installation or upgrade:

                ```bash
                helm upgrade --install ingress-nginx ingress-nginx \\
                  --repo <https://kubernetes.github.io/ingress-nginx> \\
                  --namespace <nginx-ingress-namespace> \\
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
If you used a custom CA certificate to sign the TLS certificates for the ZenML Pro services, you will need to install the CA certificates on every client machine, as covered in the [Install CA Certificates](self-hosted.md#install-ca-certificates) section.
{% endhint %}

The above are infrastructure requirements for ZenML Pro. If, in addition to ZenML, you would also like to reuse the same Kubernetes cluster to run machine learning workloads with ZenML, you will require the following additional infrastructure resources and services to be able to set up [a remote ZenML Stack](https://docs.zenml.io/user-guides/production-guide/understand-stacks):

* [a Kubernetes ZenML Orchestrator](https://docs.zenml.io/stacks/orchestrators/kubernetes) can be set up to run on the same cluster as ZenML Pro. For authentication, you will be able to configure [a ZenML Kubernetes Service Connector using service account tokens](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/kubernetes-service-connector)
* you'll need a container registry to store the container images built by ZenML. If you don't have one already, you can install [Docker registry](https://github.com/twuni/docker-registry.helm) on the same cluster as ZenML Pro.
* you'll also need some form of centralized object storage to store the artifacts generated by ZenML. If you don't have one already, you can install [MinIO](https://artifacthub.io/packages/helm/bitnami/minio) on the same cluster as ZenML Pro and then configure the [ZenML S3 Artifact Store](https://docs.zenml.io/stacks/artifact-stores/s3) to use it.
* (optional) you can install [Kaniko](https://bitnami.com/stack/kaniko) in your Kubernetes cluster to build the container images for your ZenML pipelines and then configure it as a [ZenML Kaniko Image Builder](https://docs.zenml.io/stacks/image-builders/kaniko) in your ZenML Stack.

## Stage 1/2: Install the ZenML Pro Control Plane

### Set up Credentials

If your Kubernetes cluster is not set to be authenticated to the container registry where the ZenML Pro container images are hosted, you will need to create a secret to allow the ZenML Pro server to pull the images. The following is an example of how to do this if you've received a private access key for the ZenML GCP Artifact Registry from ZenML, but you can use the same approach for your own private container registry:

```
kubectl create ns zenml-pro
kubectl -n zenml-pro create secret docker-registry image-pull-secret \
    --docker-server=europe-west3-docker.pkg.dev \
    --docker-username=_json_key_base64 \
    --docker-password="$(cat key.base64)" \
    --docker-email=unused
```

The `key.base64` file should contain the base64 encoded JSON key for the GCP service account as received from the ZenML support team. The `image-pull-secret` secret will be used in the next step when installing the ZenML Pro helm chart.

### Configure the Helm Chart

There are a variety of options that can be configured for the ZenML Pro helm chart before installation.

You can take look at the [Helm chart README](https://artifacthub.io/packages/helm/zenml-pro/zenml-pro) and [`values.yaml` file](https://artifacthub.io/packages/helm/zenml-pro/zenml-pro?modal=values) and familiarize yourself with some of the configuration settings that you can customize for your ZenML Pro deployment. Alternatively, you can unpack the `README.md` and `values.yaml` files included in the helm chart:

```bash
helm  pull --untar  oci://public.ecr.aws/zenml/zenml-pro --version <version>
less zenml-pro/README.md
less zenml-pro/values.yaml
```

This is an example Helm values YAML file that covers the most common configuration options:

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
      repository: 715803424590.dkr.ecr.eu-west-1.amazonaws.com/zenml-pro-api
      # Use this for direct GAR access
      # repository: europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-api
    dashboard:
      # Change this to point to your own container repository or use this for direct ECR access
      repository: 715803424590.dkr.ecr.eu-west-1.amazonaws.com/zenml-pro-dashboard
      # Use this for direct GAR access
      # repository: europe-west3-docker.pkg.dev/zenml-cloud/zenml-pro/zenml-pro-dashboard

  # The external URL where the ZenML Pro server API and dashboard are reachable.
  #
  # This should be set to a hostname that is associated with the Ingress
  # controller.
  serverURL: https://zenml-pro.my.domain

  # Database configuration.
  database:

    # Credentials to use to connect to an external Postgres or MySQL database.
    external:
      
      # The type of the external database service to use:
      # - postgres: use an external Postgres database service.
      # - mysql: use an external MySQL database service.
      type: mysql
    
      # The host of the external database service.
      host: my-database.my.domain

      # The username to use to connect to the external database service.
      username: zenml

      # The password to use to connect to the external database service.
      password: my-password
      
      # The name of the database to use. Will be created on first run if it
      # doesn't exist.
      #
      # NOTE: if the database user doesn't have permissions to create this
      # database, the database should be created manually before installing
      # the helm chart.
      database: zenmlpro

  ingress:
    enabled: true
    # Use the same hostname configured in `serverURL`
    host: zenml-pro.my.domain
```

Minimum required settings:

* the database credentials (`zenml.database.external`)
* the URL (`zenml.serverURL`) and Ingress hostname (`zenml.ingress.host`) where the ZenML Pro Control Plane API and Dashboard will be reachable

In addition to the above, the following might also be relevant for you:

* configure container registry credentials (`imagePullSecrets`)
* injecting custom CA certificates (`zenml.certificates`), especially important if the TLS certificates used by the ZenML Pro services are signed by a custom Certificate Authority
* configure HTTP proxy settings (`zenml.proxy`)
* custom container image repository locations (`zenml.image.api` and `zenml.image.dashboard`)
* the username and password used for the default admin account (`zenml.auth.password`)
* additional Ingress settings (`zenml.ingress`)
* Kubernetes resources allocated to the pods (`resources`)
* If you set up a common DNS prefix that you plan on using for all the ZenML Pro services, you may configure the domain of the HTTP cookies used by the ZenML Pro dashboard to match it by setting `zenml.auth.authCookieDomain` to the DNS prefix (e.g. `.my.domain` instead of `zenml-pro.my-domain`)

### Install the Helm Chart

{% hint style="info" %}
Ensure that your Kubernetes cluster has access to all the container images. By default, the tags used for the container images are the same as the Helm chart version and it is recommended to keep them in sync, even though it is possible to override the tag values.
{% endhint %}

To install the helm chart (assuming the customized configuration values are in a `my-values.yaml` file), run:

```bash
helm --namespace zenml-pro upgrade --install --create-namespace zenml-pro oci://public.ecr.aws/zenml/zenml-pro --version <version>  --values my-values.yaml
```

If the installation is successful, you should be able to see the following workloads running in your cluster:

```bash
$ kubectl -n zenml-pro get all
NAME                                     READY   STATUS      RESTARTS   AGE
pod/zenml-pro-5db4c4d9d-jwp6x            1/1     Running     0          1m
pod/zenml-pro-dashboard-855c4849-qf2f6   1/1     Running     0          1m

NAME                          TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)   AGE
service/zenml-pro             ClusterIP   172.20.230.49    <none>        80/TCP    162m
service/zenml-pro-dashboard   ClusterIP   172.20.163.154   <none>        80/TCP    162m

NAME                                  READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/zenml-pro             1/1     1            1           1m
deployment.apps/zenml-pro-dashboard   1/1     1            1           1m

NAME                                           DESIRED   CURRENT   READY   AGE
replicaset.apps/zenml-pro-5db4c4d9d            1         1         1       1m
replicaset.apps/zenml-pro-dashboard-855c4849   1         1         1       1m
```

The Helm chart will output information explaining how to connect and authenticate to the ZenML Pro dashboard:

```bash
You may access the ZenML Pro server at: https://zenml-pro.my.domain

Use the following credentials:

  Username: admin@zenml.pro
  Password: fetch the password by running:

    kubectl get secret --namespace zenml-pro zenml-pro -o jsonpath="{.data.ZENML_CLOUD_ADMIN_PASSWORD}" | base64 --decode; echo
```

The credentials are for the default administrator user account provisioned on installation. With these on-hand, you can proceed to the next step and on-board additional users.

### Install CA Certificates

If the TLS certificates used by the ZenML Pro services are signed by a custom Certificate Authority, you need to install the CA certificates on every machine that needs to access the ZenML server:

* installing the CA certificates system-wide is usually the easiest solution. For example, on Ubuntu and Debian-based systems, you can install the CA certificates system-wide by copying the CA certificates into the `/usr/local/share/ca-certificates` directory and running `update-ca-certificates`.
* for some browsers (e.g. Chrome), updating the system's CA certificates is not enough. You will also need to import the CA certificates into the browser.
* for Python, you also need to set the `REQUESTS_CA_BUNDLE` environment variable to the path to the system's CA certificates bundle file (e.g. `export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt`)
* later on, when you're running containerized pipelines with ZenML, you'll also want to install those same CA certificates into the container images built by ZenML by customizing the build process via [DockerSettings](https://docs.zenml.io/how-to/customize-docker-builds). For example:
  *   customize the ZenML client container image using a Dockerfile like this:

      ```dockerfile
      # Use the original ZenML client image as a base image. The ZenML version
      # should match the version of the ZenML server you're using (e.g. 0.73.0).
      FROM zenmldocker/zenml:<zenml-version>

      # Install certificates
      COPY my-custom-ca.crt /usr/local/share/ca-certificates/
      RUN update-ca-certificates

      ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
      ```
  *   then build and push that image to your private container registry:

      ```bash
      docker build -t my.docker.registry/my-custom-zenml-image:<zenml-version> .
      docker push my.docker.registry/my-custom-zenml-image:<zenml-version>
      ```
  *   and finally update your ZenML pipeline code to use the custom ZenML client image by using the `DockerSettings` class:

      ```python
      from zenml.config import DockerSettings
      from zenml import __version__

      # Define the custom base image
      CUSTOM_BASE_IMAGE = f"my.docker.registry/my-custom-zenml-image:{__version__}"

      docker_settings = DockerSettings(
          parent_image=CUSTOM_BASE_IMAGE,
      )

      @pipeline(settings={"docker": docker_settings})
      def my_pipeline() -> None:
          ...

      ```

### Onboard Additional Users

{% hint style="info" %}
Creating user accounts is not currently supported in the ZenML Pro dashboard, because this is not a typical ZenML Pro deployment used in production. A production ZenML Pro deployment should be configured to connect to an external OAuth 2.0 / OIDC identity provider.

However, this feature is currently supported with helper Python scripts, as described below.
{% endhint %}

1.  The deployed ZenML Pro service will come with a pre-installed default administrator account. This admin account serves the purpose of creating and recovering other users. First you will need to get the admin password following the instructions at the previous step.

    ```bash
    kubectl get secret --namespace zenml-pro zenml-pro -o jsonpath="{.data.ZENML_CLOUD_ADMIN_PASSWORD}" | base64 --decode; echo
    ```
2.  Create a `users.yml` file that contains a list of all the users that you want to create for ZenML. Also set a default password. The users will be asked to change this password on their first login.

    ```yaml
    users:
    - email: adam@zenml.io
        password: tu3]4_Xz{5$9
    ```
3.  Run the `create_users.py` script below. This will create all of the users.

    **\[file: create\_users.py]**

    ```python
    import getpass
    from typing import Optional

    import requests
    import yaml
    import sys

    # Configuration
    LOGIN_ENDPOINT = "/api/v1/auth/login"
    USERS_ENDPOINT = "/api/v1/users"

    def login(base_url: str, username: str, password: str):
        """Log in and return the authentication token."""
        # Define the headers
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        # Define the data payload
        data = {
            'grant_type': '',
            'username': username,
            'password': password,
            'client_id': '',
            'client_secret': '',
            'device_code': '',
            'audience': ''
        }

        login_url = f"{base_url}{LOGIN_ENDPOINT}"
        response = requests.post(login_url, headers=headers, data=data)

        if response.status_code == 200:
            return response.json().get("token")
        else:
            print(f"Login failed. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            sys.exit(1)

    def create_user(token: str, base_url: str, email: str, password: Optional[str]):
        """Create a user with the given email."""
        users_url = f"{base_url}{USERS_ENDPOINT}"
        params = {
            'email': email,
            'password': password
        }

        # Define the headers
        headers = {
            'accept': 'application/json',
            "Authorization": f"Bearer {token}"
        }

        # Make the POST request
        response = requests.post(users_url, params=params, headers=headers, data='')

        if response.status_code == 200:
            print(f"User created successfully: {email}")
        else:
            print(f"Failed to create user: {email}")
            print(f"Status code: {response.status_code}")
            print(f"Response: {response.text}")

    def main():
        # Get login credentials
        base_url = input("ZenML URL: ")
        username = input("Enter username: ")
        password = getpass.getpass("Enter password: ")
        # Get the YAML file path
        yaml_file = input("Enter the path to the YAML file containing email addresses: ")

        # Login and get token
        token = login(base_url, username, password)
        print("Login successful.")

        # Read users from YAML file
        try:
            with open(yaml_file, 'r') as file:
                data = yaml.safe_load(file)
        except Exception as e:
            print(f"Error reading YAML file: {e}")
            sys.exit(1)

        users = data['users']

        # Create users
        if isinstance(users, list):
            for user in users:
                create_user(token, base_url, user["email"], user["password"])
        else:
            print("Invalid YAML format. Expected a list of email addresses.")

    if __name__ == "__main__":
        main()
    ```

The script will prompt you for the URL of your deployment, the admin account email and admin account password and finally the location of your `users.yml` file.

![](../../.gitbook/assets/on-prem-01.png)

### Create an Organization

{% hint style="warning" %}
The ZenML Pro admin user should only be used for administrative operations: creating other users, resetting the password of existing users and enrolling workspaces. All other operations should be executed while logged in as a regular user.
{% endhint %}

Head on over to your deployment in the browser and use one of the users you just created to log in.

![](../../.gitbook/assets/on-prem-02.png)

After logging in for the first time, you will need to create a new password. (Be aware: For the time being only the admin account will be able to reset this password)

![](../../.gitbook/assets/on-prem-03.png)

Finally you can create an Organization. This Organization will host all the workspaces you enroll at the next stage.

![](../../.gitbook/assets/on-prem-04.png)

### Invite Other Users to the Organization

Now you can invite your whole team to the org. For this open the drop-down in the top right and head over to the settings.

![](../../.gitbook/assets/on-prem-05.png)

Here in the members tab, add all the users you created in the previous step.

![](../../.gitbook/assets/on-prem-06.png)

For each user, finally head over to the Pending invited screen and copy the invite link for each user.

![](../../.gitbook/assets/on-prem-07.png)

Finally, send the invitation link, along with the account's email and initial password over to your team members.

## Stage 2/2: Enroll and Deploy ZenML Pro workspaces

Installing and updating on-prem ZenML Pro workspace servers is not automated, as it is with the SaaS version. You will be responsible for enrolling workspace servers in the right ZenML Pro organization, installing them and regularly updating them. Some scripts are provided to simplify this task as much as possible.

### Enrolling a Workspace

1.  **Run the `enroll-workspace.py` script below**

    This will collect all the necessary data, then enroll the workspace in the organization and generate a Helm `values.yaml` file template that you can use to install the workspace server:

    **\[file: enroll-workspace.py]**

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
        # Define the headers
        headers = {
            "accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        # Define the data payload
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

        # Define the headers
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {token}",
        }
        params = {
            "organization_id": org_id,
        }
        if workspace_name:
            params["workspace_name"] = workspace_name

        # Create the workspace
        response = requests.get(
            workspace_url,
            params=params,
            headers=headers,
        )

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

    def list_organizations(
        token: str,
        base_url: str,
    ) -> List[Tuple[str, str]]:
        """Get a list of organizations."""
        organization_url = f"{base_url}{ORGANIZATION_ENDPOINT}"

        # Define the headers
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {token}",
        }

        # Create the workspace
        response = requests.get(
            organization_url,
            headers=headers,
        )

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

        # Define the headers
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {token}",
        }

        if delete_existing:
            # Delete the workspace
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

        # Enroll the workspace
        response = requests.post(
            workspace_url,
            json={
                "name": workspace_name,
                "organization_id": org_id,
            },
            params={
                "enroll": True,
            },
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
        """Get the workspace configuration.

        Args:
            workspace_id: Workspace ID.
            workspace_name: Workspace name.
            organization_name: Organization name.
            enrollment_key: Enrollment key.
            repository: Workspace docker image repository.

        Returns:
            The workspace configuration.
        """
        # Generate a secret key to encrypt the SQL database secrets
        encryption_key = f"{uuid.uuid4().hex}{uuid.uuid4().hex}"

        # Generate a hostname and database name from the workspace ID
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
            repository: { repository }
        # TODO: use your actual server domain here
        serverURL: https://zenml.{ short_workspace_id }.example.com
        ingress:
            enabled: true
            # TODO: use your actual domain here
            host: zenml.{ short_workspace_id }.example.com
        pro:
            apiURL: { zenml_pro_url }/api/v1
            dashboardURL: { zenml_pro_url }
            enabled: true
            enrollmentKey: { enrollment_key }
            organizationID: { organization_id }
            organizationName: { organization_name }
            workspaceID: { workspace_id }
            workspaceName: { workspace_name }
        replicaCount: 1
        secretsStore:
            sql:
                encryptionKey: { encryption_key }
            type: sql

    # TODO: these are the minimum resources required for the ZenML server. You can
    # adjust them to your needs.
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
        username = prompt(
            "Enter the ZenML Pro admin account username",
            default_value="admin@zenml.pro",
        )
        password = prompt(
            "Enter the ZenML Pro admin account password", password=True
        )

        # Login and get token
        token = login(zenml_pro_url, username, password)
        print("Login successful.")

        organizations = list_organizations(
            token=token,
            base_url=zenml_pro_url,
        )
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
                organizations = "\n".join(
                    [f"{name} [{id}]" for id, name in organizations]
                )
                print(f"The following organizations are available:\n{organizations}")
                organization_id = prompt(
                    "Which organization ID should the workspace be enrolled in?",
                )
                if organization_id in [id for id, _ in organizations]:
                    break
                print("Invalid organization ID. Please try again.")

        # Generate a default workspace name
        workspace_name = f"zenml-{str(uuid.uuid4())[:8]}"
        workspace_name = prompt(
            "Choose a name for the workspace, or press enter to use a generated name (only lowercase letters, numbers, and hyphens are allowed)",
            default_value=workspace_name,
        )

        existing_workspace_id = workspace_exists(
            token=token,
            base_url=zenml_pro_url,
            org_id=organization_id,
            workspace_name=workspace_name,
        )

        if existing_workspace_id:
            confirm = prompt(
                f"A workspace with name {workspace_name} already exists in the "
                f"organization {organization_id}. Overwrite ? (y/n)",
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

        # Write the workspace configuration to a file
        values_file = f"zenml-{workspace_name}-values.yaml"
        with open(values_file, "w") as file:
            file.write(workspace_config)

        print(
            f"""
    The workspace was enrolled successfully. It can be accessed at:

    {zenml_pro_url}/workspaces/{workspace_name}

    The workspace server Helm values were written to: {values_file}

    Please note the TODOs in the file and adjust them to your needs.

    To install the workspace, run e.g.:

        helm --namespace zenml-pro-{workspace_name} upgrade --install --create-namespace \
            zenml oci://public.ecr.aws/zenml/zenml --version <version> \
            --values {values_file}

    """
        )

    if __name__ == "__main__":
        main()

    ```

    Running the script does two things:

    * it creates a workspace entry in the ZenML Pro database. The workspace will remain in a "provisioning" state and won't be accessible until you actually install it using Helm.
    * it outputs a YAML file with Helm chart configuration values that you can use to deploy the ZenML Pro workspace server in your Kubernetes cluster.

    This is an example of a generated Helm YAML file:

    ```yaml
    zenml:
        analyticsOptIn: false
        threadPoolSize: 20
        database:
            maxOverflow: "-1"
            poolSize: "10"
            # TODO: use the actual database host and credentials
            url: mysql://root:password@mysql.example.com:3306/zenmlf8e306ef90e74b2f99db28298834feed
        image:
            # TODO: use your actual image repository (omit the tag, which is
            # assumed to be the same as the helm chart version)
            repository: 715803424590.dkr.ecr.eu-central-1.amazonaws.com/zenml-pro-server
        # TODO: use your actual server domain here
        serverURL: https://zenml.f8e306ef90e74b2f99db28298834feed.example.com
        ingress:
            enabled: true
            # TODO: use your actual domain here
            host: zenml.f8e306ef90e74b2f99db28298834feed.example.com
        pro:
            apiURL: https://zenml-pro.staging.cloudinfra.zenml.io/api/v1
            dashboardURL: https://zenml-pro.staging.cloudinfra.zenml.io
            enabled: true
            enrollmentKey: Mt9Rw-Cdjlumel7GTCrbLpCQ5KhhtfmiDt43mVOYYsDKEjboGg9R46wWu53WQ20OzAC45u-ZmxVqQkMGj-0hWQ
            organizationID: 0e99e236-0aeb-44cc-aff7-590e41c9a702
            organizationName: MyOrg
            workspaceID: f8e306ef-90e7-4b2f-99db-28298834feed
            workspaceName: zenml-eab14ff8
        replicaCount: 1
        secretsStore:
            sql:
                encryptionKey: 155b20a388064423b1943d64f1686dd0d0aa6454be0a46839b1ee830f6565904
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
2.  **Configure the ZenML Pro workspace Helm chart**

    **IMPORTANT**: In configuring the ZenML Pro workspace Helm chart, keep the following in mind:

    * don't use the same database name for multiple workspaces
    * don't reuse the control plane database name for the workspace server database

    The ZenML Pro workspace server is nothing more than a slightly modified open-source ZenML server. The deployment even uses the official open-source helm chart.

    There are a variety of options that can be configured for the ZenML Pro workspace server chart before installation. You can start by taking a look at the [Helm chart README](https://artifacthub.io/packages/helm/zenml/zenml) and [`values.yaml` file](https://artifacthub.io/packages/helm/zenml/zenml?modal=values) and familiarize yourself with some of the configuration settings that you can customize for your ZenML server deployment. Alternatively, you can unpack the `README.md` and `values.yaml` files included in the helm chart:

    ```bash
    helm  pull --untar  oci://public.ecr.aws/zenml/zenml --version <version>
    less zenml/README.md
    less zenml/values.yaml
    ```

    To configure the Helm chart, use the generated YAML file generated at the previous step as a template and fill in the necessary values marked by `TODO` comments. At a minimum, you'll need to configure the following:

    * configure container registry credentials (`imagePullSecrets`, same as [described for the control plane](self-hosted.md#set-up-credentials))
    * the MySQL database credentials (`zenml.database.url`)
    * the container image repository where the ZenML Pro workspace server container images are stored (`zenml.image.repository`)
    * the hostname where the ZenML Pro workspace server will be reachable (`zenml.ingress.host` and `zenml.serverURL`)

    You may also choose to configure additional features documented in [the official OSS ZenML Helm deployment documentation pages](https://docs.zenml.io/getting-started/deploying-zenml/deploy-with-helm), if you need them:

    * injecting custom CA certificates (`zenml.certificates`), especially important if the TLS certificate used for the ZenML Pro control plane is signed by a custom Certificate Authority
    * configure HTTP proxy settings (`zenml.proxy`)
    * set up secrets stores
    * configure database backup and restore
    * customize Kubernetes resources
    * etc.
3.  **Deploy the ZenML Pro workspace server with Helm**

    To install the helm chart (assuming the customized configuration values are in the generated `zenml-my-workspace-values.yaml` file), run e.g.:

    ```python
    helm --namespace zenml-pro-f8e306ef-90e7-4b2f-99db-28298834feed upgrade --install --create-namespace zenml oci://public.ecr.aws/zenml/zenml --version <version> --values zenml-f8e306ef-90e7-4b2f-99db-28298834feed-values.yaml
    ```

    The deployment is ready when the ZenML server pod is running and healthy:

    ```python
    $ kubectl -n zenml-pro-f8e306ef-90e7-4b2f-99db-28298834feed get all
    NAME                           READY   STATUS      RESTARTS   AGE
    pod/zenml-5c4b6d9dcd-7bhfp     1/1     Running     0          85m

    NAME            TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)   AGE
    service/zenml   ClusterIP   172.20.43.140   <none>        80/TCP    85m

    NAME                    READY   UP-TO-DATE   AVAILABLE   AGE
    deployment.apps/zenml   1/1     1            1           85m

    NAME                               DESIRED   CURRENT   READY   AGE
    replicaset.apps/zenml-5c4b6d9dcd   1         1         1       85m
    ```

    After deployment, your workspace should show up as running in the ZenML Pro dashboard and can be accessed at the next step.

    If you need to deploy multiple workspaces, simply run the enrollment script again with different values.

### Accessing the Workspace

If you use TLS certificates for the ZenML Pro control plane or workspace server signed by a custom Certificate Authority, remember to [install them on the client machines](self-hosted.md#install-ca-certificates).

#### Accessing the Workspace Dashboard

The newly enrolled workspace should be accessible in the ZenML Pro workspace dashboard and the CLI now. You need to login as an organization member and add yourself as a workspace member first):

![](../../.gitbook/assets/on-prem-08.png)

![](../../.gitbook/assets/on-prem-09.png)

![](../../.gitbook/assets/on-prem-10.png)

Then follow the instructions in the checklist to unlock the full dashboard:

![](../../.gitbook/assets/on-prem-11.png)

![](../../.gitbook/assets/on-prem-12.png)

#### Accessing the Workspace from the ZenML CLI

To login to the workspace with the ZenML CLI, you need to pass the custom ZenML Pro API URL to the `zenml login` command:

```bash
zenml login --pro-api-url https://zenml-pro.staging.cloudinfra.zenml.io/api/v1
```

Alternatively, you can set the `ZENML_PRO_API_URL` environment variable:

```bash
export ZENML_PRO_API_URL=https://zenml-pro.staging.cloudinfra.zenml.io/api/v1
zenml login
```

## Day 2 Operations: Upgrades and Updates

This section covers how to upgrade or update your ZenML Pro deployment. The process involves updating both the ZenML Pro Control Plane and the ZenML Pro workspace servers.

{% hint style="warning" %}
Always upgrade the ZenML Pro Control Plane first, then upgrade the workspace servers. This ensures compatibility and prevents potential issues.
{% endhint %}

### Upgrade Checklist

1. **Check Available Versions and Release Notes**
   * For ZenML Pro Control Plane:
     * Check available versions in the [ZenML Pro ArtifactHub repository](https://artifacthub.io/packages/helm/zenml-pro/zenml-pro)
   * For ZenML Pro Workspace Servers:
     * Check available versions in the [ZenML OSS ArtifactHub repository](https://artifacthub.io/packages/helm/zenml/zenml)
     * Review the [ZenML GitHub releases page](https://github.com/zenml-io/zenml/releases) for release notes and breaking changes
2. **Fetch and Prepare New Software Artifacts**
   * Follow the [Software Artifacts](self-hosted.md#software-artifacts) section to get access to the new versions of:
     * ZenML Pro Control Plane container images and Helm chart
     * ZenML Pro workspace server container images and Helm chart
   * If using a private registry, copy the new container images to your private registry
   * If you are using an air-gapped installation, follow the [Air-Gapped Installation](self-hosted.md#air-gapped-installation) instructions
3. **Upgrade the ZenML Pro Control Plane**
   *   Option A - In-place upgrade with existing values. Use this if you don't need to change any configuration values as part of the upgrade:

       ```bash
       helm --namespace zenml-pro upgrade zenml-pro oci://public.ecr.aws/zenml/zenml-pro \
         --version <new-version> --reuse-values
       ```
   *   Option B - Retrieve, modify and reapply values, if necessary. Use this if you need to change any configuration values as part of the upgrade or if you are performing a configuration update without upgrading the ZenML Pro Control Plane.

       ```bash
       # Get the current values
       helm --namespace zenml-pro get values zenml-pro > current-values.yaml

       # Edit current-values.yaml if needed, then upgrade
       helm --namespace zenml-pro upgrade zenml-pro oci://public.ecr.aws/zenml/zenml-pro \
         --version <new-or-existing-version> --values current-values.yaml
       ```
4. **Upgrade ZenML Pro Workspace Servers**
   * For each workspace, perform either:
     *   Option A - In-place upgrade with existing values. Use this if you don't need to change any configuration values as part of the upgrade:

         ```bash
         helm --namespace zenml-pro-<workspace-name-or-id> upgrade zenml oci://public.ecr.aws/zenml/zenml \
         --version <new-version> --reuse-values
         ```
     *   Option B - Retrieve, modify and reapply values, if necessary. Use this if you need to change any configuration values as part of the upgrade or if you are performing a configuration update without upgrading the ZenML Pro Workspace Server.

         ```bash
         # Get the current values
         helm --namespace zenml-pro-<workspace-name-or-id> get values zenml > current-workspace-values.yaml

         # Edit current-workspace-values.yaml if needed, then upgrade
         helm --namespace zenml-pro-<workspace-name-or-id> upgrade zenml oci://public.ecr.aws/zenml/zenml \
         --version <new-version> --values current-workspace-values.yaml
         ```

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
