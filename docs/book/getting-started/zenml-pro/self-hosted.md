---
description: >
  Guide for installing ZenML Pro self-hosted in a Kubernetes cluster.
---

# ZenML Pro Self-Hosted Deployment

This page provides instructions for installing ZenML Pro - the ZenML Pro Control Plane and one or more ZenML Pro Tenant servers - on-premise in a Kubernetes cluster.

## Overview

ZenML Pro can be installed as an self-hosted deployment. You need to be granted access to the ZenML Pro container images and you'll have to provide your own infrastructure: a Kubernetes cluster, a database server and a few other common prerequisites usually needed to expose Kubernetes services via HTTPs - a load balancer, an Ingress controller, HTTPs certificate(s) and DNS rule(s).

This document will guide you through the process.

## Preparation and prerequisites

### Software Artifacts

The ZenML Pro on-prem installation relies on a set of container images and Helm charts. The container images are stored in private ZenML AWS ECR container registries located at `715803424590.dkr.ecr.eu-west-1.amazonaws.com`.

If you haven't done so already, please [book a demo](https://www.zenml.io/book-your-demo) to get access to the private ZenML Pro container images.

To access these repositories, you need to set up an AWS IAM user or IAM role in your AWS account. The steps below outline how to create an AWS account, configure the necessary IAM entities, and pull images from the private repositories. If you're familiar with AWS or even plan on using an AWS EKS cluster to deploy ZenML Pro, then you can simply use your existing IAM user or IAM role and skip steps 1. and 2.

---

- **Step 1: Create a Free AWS Account**
    1. Visit the [AWS Free Tier page](https://aws.amazon.com/free/).
    2. Click **Create a Free Account**.
    3. Follow the on-screen instructions to provide your email address, create a root user, and set a secure password.
    4. Enter your contact and payment information for verification purposes. While a credit or debit card is required, you won't be charged for free-tier eligible services.
    5. Confirm your email and complete the verification process.
    6. Log in to the AWS Management Console using your root user credentials.
    
    ---
    
- **Step 2: Create an IAM User or IAM Role**
    
    **A. Create an IAM User**
    
    1. Log in to the AWS Management Console.
    2. Navigate to the **IAM** service.
    3. Click **Users** in the left-hand menu, then click **Add Users**.
    4. Provide a user name (e.g., `zenml-ecr-access`).
    5. Select **Access Key - Programmatic access** as the AWS credential type.
    6. Click **Next: Permissions**.
    7. Choose **Attach policies directly**, then select the following policies:
        - **AmazonEC2ContainerRegistryReadOnly**
    8. Click **Next: Tags** and optionally add tags for organization purposes.
    9. Click **Next: Review**, then **Create User**.
    10. Note the **Access Key ID** and **Secret Access Key** displayed after creation. Save these securely.
    
    **B. Create an IAM Role**
    
    1. Navigate to the **IAM** service.
    2. Click **Roles** in the left-hand menu, then click **Create Role**.
    3. Choose the type of trusted entity:
        - Select **AWS Account**.
    4. Enter your AWS account ID and click **Next**.
    5. Select the **AmazonEC2ContainerRegistryReadOnly** policy.
    6. Click **Next: Tags**, optionally add tags, then click **Next: Review**.
    7. Provide a role name (e.g., `zenml-ecr-access-role`) and click **Create Role**.
    
    ---
    
- **Step 3: Provide the IAM User/Role ARN**
    1. For an IAM user, the ARN can be found in the **Users** section under the **Summary** tab.
    2. For an IAM role, the ARN is displayed in the **Roles** section under the **Summary** tab.
    
    Send the ARN to ZenML Support so it can be granted permission to access the ZenML Pro container images and Helm charts.

    ---
    
- **Step 4: Authenticate your Docker Client**
    
    Run these steps on the machine that you'll use to pull the ZenML Pro images. It is recommended that you copy the container images into your own container registry that will be accessible from the Kubernetes cluster where ZenML Pro will be stored, otherwise you'll have to find a way to configure the Kubernetes cluster to authenticate directly to the ZenML Pro container registry and that will be problematic if your Kubernetes cluster is not running on AWS.
    
    **A. Install AWS CLI**
    
    1. Follow the instructions to install the AWS CLI: [AWS CLI Installation Guide](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html).
    
    **B. Configure AWS CLI Credentials**
    
    1. Open a terminal and run `aws configure`
    2. Enter the following when prompted:
        - **Access Key ID**: Provided during IAM user creation.
        - **Secret Access Key**: Provided during IAM user creation.
        - **Default region name**: `eu-west-1`
        - **Default output format**: Leave blank or enter `json`.
    3. If you chose to use an IAM role, update the AWS CLI configuration file to specify the role you want to assume. Open the configuration file located at `~/.aws/config` and add the following:
        
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
    
    This will allow you to authenticate to the ZenML Pro container registries and pull images with Docker, e.g.:
    
    ```bash
    docker pull 715803424590.dkr.ecr.eu-west-1.amazonaws.com/zenml-pro-api:<tag>
    docker pull 715803424590.dkr.ecr.eu-west-1.amazonaws.com/zenml-pro-dashboard:<tag>
    docker pull 715803424590.dkr.ecr.eu-central-1.amazonaws.com/zenml-pro-server:<tag>
    ```    

#### ZenML Pro Control Plane Artifacts

The following artifacts are required to install the ZenML Pro control plane in your own Kubernetes cluster:

- `715803424590.dkr.ecr.eu-west-1.amazonaws.com/zenml-pro-api` - private container images for the ZenML Pro API server
- `715803424590.dkr.ecr.eu-west-1.amazonaws.com/zenml-pro-dashboard` - private container images for the ZenML Pro dashboard
- `oci://public.ecr.aws/zenml/zenml-pro` - the public ZenML Pro helm chart (as an OCI artifact)

{% hint style="info" %}
The container image tags and the Helm chart versions are both synchronized and linked to the ZenML Pro releases. You can find the ZenML Pro Helm chart along with the available released versions in the [ZenML Pro ArtifactHub repository](https://artifacthub.io/packages/helm/zenml-pro/zenml-pro).

If you're planning on copying the container images to your own private registry (recommended if your Kubernetes cluster isn't running on AWS and can't authenticate directly to the ZenML Pro container registry) make sure to include and keep the same tags.

By default, the ZenML Pro Helm chart uses the same container image tags as the helm chart version. Configuring custom container image tags when setting up your Helm distribution is also possible, but not recommended because it doesn't yield reproducible results and may even cause problems if used with the wrong Helm chart version.
{% endhint %}

#### ZenML Pro Tenant Server Artifacts

The following artifacts are required to install ZenML Pro tenant servers in your own Kubernetes cluster:

- `715803424590.dkr.ecr.eu-central-1.amazonaws.com/zenml-pro-server` - private container images for the ZenML Pro tenant server
- `oci://public.ecr.aws/zenml/zenml` - the public open-source ZenML Helm chart (as an OCI artifact).

{% hint style="info" %}
The container image tags and the Helm chart versions are both synchronized and linked to the ZenML open-source releases. To find the latest ZenML OSS release, please check the [ZenML release page](https://github.com/zenml-io/zenml/releases).

If you're planning on copying the container images to your own private registry (recommended if your Kubernetes cluster isn't running on AWS and can't authenticated directly to the ZenML Pro container registry) make sure to include and keep the same tags.

By default, the ZenML OSS Helm chart uses the same container image tags as the helm chart version. Configuring custom container image tags when setting up your Helm distribution is also possible, but not recommended because it doesn't yield reproducible results and may even cause problems if used with the wrong Helm chart version.
{% endhint %}

#### ZenML Pro Client Artifacts

If you're planning on running containerized ZenML pipelines, or using other containerization related ZenML features, you'll also need to access the public ZenML client container image located [in Docker Hub at `zenmldocker/zenml`](https://hub.docker.com/r/zenmldocker/zenml). This isn't a problem unless you're deploying ZenML Pro in an air-gapped environment, in which case you'll also have to copy the client container image into your own container registry. You'll also have to configure your code to use the correct base container registry via DockerSettings (see the [DockerSettings documentation](../../how-to/customize-docker-builds/README.md) for more information).

### Air-Gapped Installation

If you need to install ZenML Pro in an air-gapped environment (a network with no direct internet access), you'll need to transfer all required artifacts to your internal infrastructure. Here's a step-by-step process:

**1. Prepare a Machine with Internet Access**

First, you'll need a machine with both internet access and sufficient storage space to temporarily store all artifacts. On this machine:

1. Follow the authentication steps described above to gain access to the private repositories
2. Install the required tools:
   - Docker
   - AWS CLI
   - Helm
   - A tool like `skopeo` for copying container images (optional but recommended)

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
ZENML_PRO_REGISTRY="715803424590.dkr.ecr.eu-west-1.amazonaws.com"
ZENML_PRO_SERVER_REGISTRY="715803424590.dkr.ecr.eu-central-1.amazonaws.com"
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
# Install the ZenML Pro Control Plane
helm install zenml-pro ./zenml-artifacts/charts/zenml-pro-0.10.24.tgz \
  --namespace zenml-pro \
  --create-namespace \
  --values your-values.yaml

# Install a ZenML Pro Tenant Server
helm install zenml-tenant ./zenml-artifacts/charts/zenml-0.73.0.tgz \
  --namespace zenml-tenant \
  --create-namespace \
  --values your-tenant-values.yaml
```

### Infrastructure Requirements

To deploy the ZenML Pro control plane and one or more ZenML Pro tenant servers, ensure the following prerequisites are met:

1. **Kubernetes Cluster**
    
    A functional Kubernetes cluster is required as the primary runtime environment.
    
2. **Database Server(s)**
    
    The ZenML Pro Control Plane and ZenML Pro Tenant servers need to connect to an external database server.  To minimize the amount of infrastructure resources needed, you can use a single database server in common for the Control Plane and for all tenants, or you can use different database servers to ensure server-level database isolation, as long as you keep in mind the following limitations:
    
    - the ZenML Pro Control Plane can be connected to either MySQL or Postgres as the external database
    - the ZenML Pro Tenant servers can only be connected to a MySQL database (no Postgres support is available)
    - the ZenML Pro Control Plane as well as every ZenML Pro Tenant server needs to use its own individual database (especially important when connected to the same server)
    
    Ensure you have a valid username and password for the different ZenML Pro services. For improved security, it is recommended to have different users for different services. If the database user does not have permissions to create databases, you must also create a database and give the user full permissions to access and manage it (i.e. create, update and delete tables).
    
3. **Ingress Controller**
    
    Install an Ingress provider in the cluster (e.g., NGINX, Traefik) to handle HTTP(S) traffic routing. Ensure the Ingress provider is properly configured to expose the cluster's services externally.
    
4. **Domain Name**
    
    You'll need an FQDN for the ZenML Pro Control Plane as well as for every ZenML Pro tenant. For this reason, it's highly recommended to use a DNS prefix and associated SSL certificate instead of individual FQDNs and SSL certificates, to make this process easier.
    
    - **FQDN or DNS Prefix Setup**
    Obtain a Fully Qualified Domain Name (FQDN) or DNS prefix (e.g., `*.zenml-pro.mydomain.com`) from your DNS provider.
        - Identify the external Load Balancer IP address of the Ingress controller using the command `kubectl get svc -n <ingress-namespace>`. Look for the `EXTERNAL-IP` field of the Load Balancer service.
        - Create a DNS `A` record (or `CNAME` for subdomains) pointing the FQDN to the Load Balancer IP. Example:
            - Host: `zenml-pro.mydomain.com`
            - Type: `A`
            - Value: `<Load Balancer IP>`
        - Use a DNS propagation checker to confirm that the DNS record is resolving correctly.
5. **SSL Certificate**
    
    The ZenML Pro services do not terminate SSL traffic. It is your responsibility to generate and configure the necessary SSL certificates for the ZenML Pro Control Plane as well as all the ZenML Pro tenants that you will deploy (see the previous point on how to use a DNS prefix to make the process easier).
    
    - **Obtaining SSL Certificates**
        
        Acquire an SSL certificate for the domain. You can use:
        
        - A commercial SSL certificate provider (e.g., DigiCert, Sectigo).
        - Free services like [Let's Encrypt](https://letsencrypt.org/) for domain validation and issuance.
    - **Configuring SSL Termination**
        
        Once the SSL certificate is obtained, configure your load balancer or Ingress controller to terminate HTTPS traffic:
        
        **For NGINX Ingress Controller**:
        
        You can configure SSL termination globally for the NGINX Ingress Controller by setting up a default SSL certificate or configuring it at the ingress controller level, or you can specify SSL certificates when configuring the ingress in the ZenML server Helm values.
        
        Here's how you can do it globally:
        
        1. **Create a TLS Secret**
            
            Store your SSL certificate and private key as a Kubernetes TLS secret in the namespace where the NGINX Ingress Controller is deployed.
            
            ```bash
            kubectl create secret tls default-ssl-secret \\
              --cert=/path/to/tls.crt \\
              --key=/path/to/tls.key \\
              -n <nginx-ingress-namespace>
            
            ```
            
        2. **Update NGINX Ingress Controller Configurations**
            
            Configure the NGINX Ingress Controller to use the default SSL certificate.
            
            - If using the NGINX Ingress Controller Helm chart, modify the `values.yaml` file or use `-set` during installation:
                
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
                
            - If the NGINX Ingress Controller was installed manually, edit its deployment to include the argument in the `args` section of the container:
                
                ```yaml
                spec:
                  containers:
                  - name: controller
                    args:
                      - --default-ssl-certificate=<nginx-ingress-namespace>/default-ssl-secret
                
                ```
                
        
        **For Traefik**:
        
        - Configure Traefik to use TLS by creating a certificate resolver for Let's Encrypt or specifying the certificates manually in the `traefik.yml` or `values.yaml` file. Example for Let's Encrypt:
            
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
            
        - Reference the domain in your IngressRoute or Middleware configuration.

## Stage 1/2: Install the ZenML Pro Control Plane

### Configure the Helm Chart

There are a variety of options that can be configured for the ZenML Pro helm chart before installation.

You can take look at the [`values.yaml` file](https://artifacthub.io/packages/helm/zenml-pro/zenml-pro?modal=values) and familiarize yourself with some of the configuration settings that you can customize for your ZenML Pro deployment. Alternatively, you can unpack the `values.yaml` file included in the helm chart:

```bash
helm  pull --untar  oci://public.ecr.aws/zenml/zenml-pro --version <version>
less zenml-pro/values.yaml
```

This is an example Helm values YAML file that covers the most common configuration options: 

```yaml
# ZenML Pro server related options.
zenml:

  image:
    api:
      # Change this to point to your own container repository
      repository: 715803424590.dkr.ecr.eu-west-1.amazonaws.com/zenml-pro-api
    dashboard:
      # Change this to point to your own container repository
      repository: 715803424590.dkr.ecr.eu-west-1.amazonaws.com/zenml-pro-dashboard

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

- the database credentials (`zenml.database.external`)
- the URL (`zenml.serverURL`) and Ingress hostname (`zenml.ingress.host`) where the ZenML Pro Control Plane API and Dashboard will be reachable

In addition to the above, the following might also be relevant for you:

- custom container image repository locations (`zenml.image.api` and `zenml.image.dashboard`)
- the username and password used for the default admin account (`zenml.auth.password`)
- additional Ingress settings (`zenml.ingress`)
- Kubernetes resources allocated to the pods (`resources`)
- If you set up a common DNS prefix that you plan on using for all the ZenML Pro services, you may configure the domain of the HTTP cookies used by the ZenML Pro dashboard to match it by setting `zenml.auth.authCookieDomain` to the DNS prefix (e.g. `.my.domain` instead of `zenml-pro.my-domain`)

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

### Onboard Additional Users

{% hint style="info" %}
Creating user accounts is not currently supported in the ZenML Pro dashboard, because this is not a typical ZenML Pro deployment used in production. A production ZenML Pro deployment should be configured to connect to an external OAuth 2.0 / OIDC identity provider.

However, this feature is currently supported with helper Python scripts, as described below.
{% endhint %}

1. The deployed ZenML Pro service will come with a pre-installed default administrator account. This admin account serves the purpose of creating and recovering other users. First you will need to get the admin password following the instructions at the previous step.

```bash
kubectl get secret --namespace zenml-pro zenml-pro -o jsonpath="{.data.ZENML_CLOUD_ADMIN_PASSWORD}" | base64 --decode; echo
```

1. Create a `users.yml` file that contains a list of all the users that you want to create for ZenML. Also set a default password. The users will be asked to change this password on their first login.

```yaml
users:
  - email: adam@zenml.io
    password: tu3]4_Xz{5$9
```

1. Run the `create_users.py` script below. This will create all of the users.

**[file: create_users.py]**

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
The ZenML Pro admin user should only be used for administrative operations: creating other users, resetting the password of existing users and enrolling tenants. All other operations should be executed while logged in as a regular user.
{% endhint %}

Head on over to your deployment in the browser and use one of the users you just created to log in.

![](../../.gitbook/assets/on-prem-02.png)

After logging in for the first time, you will need to create a new password. (Be aware: For the time being only the admin account will be able to reset this password)

![](../../.gitbook/assets/on-prem-03.png)

Finally you can create an Organization. This Organization will host all the tenants you enroll at the next stage.

![](../../.gitbook/assets/on-prem-04.png)

### Invite Other Users to the Organization

Now you can invite your whole team to the org. For this open the drop-down in the top right and head over to the settings.

![](../../.gitbook/assets/on-prem-05.png)

Here in the members tab, add all the users you created in the previous step.

![](../../.gitbook/assets/on-prem-06.png)

For each user, finally head over to the Pending invited screen and copy the invite link for each user.

![](../../.gitbook/assets/on-prem-07.png)

Finally, send the invitation link, along with the account's email and initial password over to your team members.

## Stage 2/2: Enroll and Deploy ZenML Pro tenants

Installing and updating on-prem ZenML Pro tenant servers is not automated, as it is with the SaaS version. You will be responsible for enrolling tenant servers in the right ZenML Pro organization, installing them and regularly updating them. Some scripts are provided to simplify this task as much as possible.

### Enrolling a Tenant

1. run the `enroll-tenant.py` script below. This will collect all the necessary data, then enroll the tenant in the organization and generate a Helm `values.yaml` file template that you can use to install the tenant server:
    
    **[file: enroll-tenant.py]**
    
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
    TENANT_ENDPOINT = "/api/v1/tenants"
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
    
    def tenant_exists(
        token: str,
        base_url: str,
        org_id: str,
        tenant_name: Optional[str] = None,
    ) -> Optional[str]:
        """Get a tenant with a given name or url."""
        tenant_url = f"{base_url}{TENANT_ENDPOINT}"
    
        # Define the headers
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {token}",
        }
        params = {
            "organization_id": org_id,
        }
        if tenant_name:
            params["tenant_name"] = tenant_name
    
        # Create the tenant
        response = requests.get(
            tenant_url,
            params=params,
            headers=headers,
        )
    
        if response.status_code == 200:
            json_response = response.json()
            if len(json_response) > 0:
                return json_response[0]["id"]
        else:
            print(f"Failed to fetch tenants for organization: {org_id}")
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
    
        # Create the tenant
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
    
    def enroll_tenant(
        token: str,
        base_url: str,
        org_id: str,
        tenant_name: str,
        delete_existing: Optional[str] = None,
    ) -> dict:
        """Enroll a tenant."""
        tenant_url = f"{base_url}{TENANT_ENDPOINT}"
    
        # Define the headers
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {token}",
        }
    
        if delete_existing:
            # Delete the tenant
            response = requests.delete(
                f"{tenant_url}/{delete_existing}",
                headers=headers,
            )
    
            if response.status_code == 200:
                print(f"Tenant deleted successfully: {delete_existing}")
            else:
                print(f"Failed to delete tenant: {delete_existing}")
                print(f"Status code: {response.status_code}")
                print(f"Response: {response.text}")
                sys.exit(1)
    
        # Enroll the tenant
        response = requests.post(
            tenant_url,
            json={
                "name": tenant_name,
                "organization_id": org_id,
            },
            params={
                "enroll": True,
            },
            headers=headers,
        )
    
        if response.status_code == 200:
            tenant = response.json()
            tenant_id = tenant.get("id")
            print(f"Tenant enrolled successfully: {tenant_name} [{tenant_id}]")
    
            return tenant
        else:
            print(f"Failed to enroll tenant: {tenant_name}")
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
    
    def get_tenant_config(
        zenml_pro_url: str,
        organization_id: str,
        organization_name: str,
        tenant_id: str,
        tenant_name: str,
        enrollment_key: str,
        repository: str = DEFAULT_REPOSITORY,
    ) -> str:
        """Get the tenant configuration.
    
        Args:
            tenant_id: Tenant ID.
            tenant_name: Tenant name.
            organization_name: Organization name.
            enrollment_key: Enrollment key.
            repository: Tenant docker image repository.
    
        Returns:
            The tenant configuration.
        """
        # Generate a secret key to encrypt the SQL database secrets
        encryption_key = f"{uuid.uuid4().hex}{uuid.uuid4().hex}"
    
        # Generate a hostname and database name from the tenant ID
        short_tenant_id = tenant_id.replace("-", "")
    
        return f"""
    zenml:
        analyticsOptIn: false
        threadPoolSize: 20
        database:
            maxOverflow: "-1"
            poolSize: "10"
            # TODO: use the actual database host and credentials
            url: mysql://root:password@mysql.example.com:3306/zenml{short_tenant_id}
        image:
            # TODO: use your actual image repository (omit the tag, which is
            # assumed to be the same as the helm chart version)
            repository: { repository }
        # TODO: use your actual server domain here
        serverURL: https://zenml.{ short_tenant_id }.example.com
        ingress:
            enabled: true
            # TODO: use your actual domain here
            host: zenml.{ short_tenant_id }.example.com
        pro:
            apiURL: { zenml_pro_url }/api/v1
            dashboardURL: { zenml_pro_url }
            enabled: true
            enrollmentKey: { enrollment_key }
            organizationID: { organization_id }
            organizationName: { organization_name }
            tenantID: { tenant_id }
            tenantName: { tenant_name }
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
                    "Which organization ID should the tenant be enrolled in?",
                )
                if organization_id in [id for id, _ in organizations]:
                    break
                print("Invalid organization ID. Please try again.")
    
        # Generate a default tenant name
        tenant_name = f"zenml-{str(uuid.uuid4())[:8]}"
        tenant_name = prompt(
            "Choose a name for the tenant, or press enter to use a generated name",
            default_value=tenant_name,
        )
    
        existing_tenant_id = tenant_exists(
            token=token,
            base_url=zenml_pro_url,
            org_id=organization_id,
            tenant_name=tenant_name,
        )
    
        if existing_tenant_id:
            confirm = prompt(
                f"A tenant with name {tenant_name} already exists in the "
                f"organization {organization_id}. Overwrite ? (y/n)",
                default_value="n",
            )
            if confirm.lower() != "y":
                print("Exiting.")
                sys.exit(0)
    
        tenant = enroll_tenant(
            token=token,
            base_url=zenml_pro_url,
            org_id=organization_id,
            tenant_name=tenant_name,
            delete_existing=existing_tenant_id,
        )
    
        tenant_id = tenant.get("id")
        organization_name = tenant.get("organization").get("name")
        enrollment_key = tenant.get("enrollment_key")
    
        tenant_config = get_tenant_config(
            zenml_pro_url=zenml_pro_url,
            tenant_name=tenant_name,
            tenant_id=tenant_id,
            organization_id=organization_id,
            organization_name=organization_name,
            enrollment_key=enrollment_key,
        )
    
        # Write the tenant configuration to a file
        values_file = f"zenml-{tenant_id}-values.yaml"
        with open(values_file, "w") as file:
            file.write(tenant_config)
    
        print(
            f"""
    The tenant was enrolled successfully. It can be accessed at:
    
    {zenml_pro_url}/organizations/{organization_id}/tenants/{tenant_id}
    
    The tenant server Helm values were written to: {values_file}
    
    Please note the TODOs in the file and adjust them to your needs.
    
    To install the tenant, run e.g.:
    
        helm --namespace zenml-pro-{tenant_id} upgrade --install --create-namespace \
            zenml oci://public.ecr.aws/zenml/zenml --version <version> \
            --values {values_file}
    
    """
        )
    
    if __name__ == "__main__":
        main()
    
    ```
    

Running the script does two things:

- it creates a tenant entry in the ZenML Pro database. The tenant will remain in a "provisioning" state and won't be accessible until you actually install it using Helm.
- it outputs a YAML file with Helm chart configuration values that you can use to deploy the ZenML Pro tenant server in your Kubernetes cluster.

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
        tenantID: f8e306ef-90e7-4b2f-99db-28298834feed
        tenantName: zenml-eab14ff8
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

1. deploy the ZenML Pro tenant server with Helm:
    
    The ZenML Pro tenant server is nothing more than a slightly modified open-source ZenML server. The deployment even uses the official open-source helm chart.
    
    There are a variety of options that can be configured for the ZenML Pro tenant server chart before installation. You can start by taking a look at the [`values.yaml` file](https://artifacthub.io/packages/helm/zenml/zenml?modal=values) and familiarize yourself with some of the configuration settings that you can customize for your ZenML server deployment. Alternatively, you can unpack the `values.yaml` file included in the helm chart:
    
    ```bash
    helm  pull --untar  oci://public.ecr.aws/zenml/zenml --version <version>
    less zenml/values.yaml
    ```
    
    To configure the Helm chart, use the generated YAML file generated at the previous step as a template and fill in the necessary values marked by `TODO` comments. At a minimum, you'll need to configure the following:
    
    - the MySQL database credentials (`zenml.database.url`)
    - the container image repository where the ZenML Pro tenant server container images are stored (`zenml.image.repository`)
    - the hostname where the ZenML Pro tenant server will be reachable (`zenml.ingress.host` and `zenml.serverURL`)
    
    You may also choose to configure additional features, if you need them, such as secrets stores, and database backup and restore, Kubernetes resources and so on. These are documented in [the official OSS ZenML Helm deployment documentation pages](https://docs.zenml.io/getting-started/deploying-zenml/deploy-with-helm).
    
    To install the helm chart (assuming the customized configuration values are in the generated `zenml-f8e306ef-90e7-4b2f-99db-28298834feed-values.yaml` file), run e.g.:
    
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
    

After deployment, your tenant should show up as running in the ZenML Pro dashboard and can be accessed at the next step.

If you need to deploy multiple tenants, simply run the enrollment script again with different values.

### Accessing the Tenant

The newly enrolled tenant should be accessible in the ZenML Pro tenant dashboard and the CLI now. You need to login as an organization member and add yourself as a tenant member first):

![](../../.gitbook/assets/on-prem-08.png)

![](../../.gitbook/assets/on-prem-09.png)

![](../../.gitbook/assets/on-prem-10.png)

Then follow the instructions in the checklist to unlock the full dashboard:

![](../../.gitbook/assets/on-prem-11.png)

![](../../.gitbook/assets/on-prem-12.png)

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
