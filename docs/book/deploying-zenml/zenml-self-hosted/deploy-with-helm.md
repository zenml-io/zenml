---
description: Deploying ZenML in a Kubernetes cluster with Helm.
---

# Deploy with Helm

If you wish to manually deploy and manage ZenML in a Kubernetes cluster of your choice, ZenML also includes a Helm chart among its available deployment options.

You can find the chart on this [ArtifactHub repository](https://artifacthub.io/packages/helm/zenml/zenml), along with the templates, default values and instructions on how to install it. Read on to find detailed explanations on prerequisites, configuration, and deployment scenarios.

## Prerequisites

You'll need the following:

* A Kubernetes cluster
* Optional, but recommended: a MySQL-compatible database reachable from the Kubernetes cluster (e.g. one of the managed databases offered by Google Cloud, AWS, or Azure). A MySQL server version of 8.0 or higher is required
* the [Kubernetes client](https://kubernetes.io/docs/tasks/tools/#kubectl) already installed on your machine and configured to access your cluster
* [Helm](https://helm.sh/docs/intro/install/) installed on your machine
* Optional: an external Secrets Manager service (e.g. one of the managed secrets management services offered by Google Cloud, AWS, Azure, or HashiCorp Vault). By default, ZenML stores secrets inside the SQL database that it's connected to, but you also have the option of using an external cloud Secrets Manager service if you already happen to use one of those cloud or service providers

## ZenML Helm Configuration

You can start by taking a look at the [`values.yaml` file](https://artifacthub.io/packages/helm/zenml/zenml?modal=values) and familiarize yourself with some of the configuration settings that you can customize for your ZenML deployment.

In addition to tools and infrastructure, you will also need to collect and [prepare information related to your database](deploy-with-helm.md#collect-information-from-your-sql-database-service) and [information related to your external secrets management service](deploy-with-helm.md#collect-information-from-your-secrets-management-service) to be used for the Helm chart configuration and you may also want to install additional [optional services in your cluster](deploy-with-helm.md#optional-cluster-services).

When you are ready, you can proceed to the [installation](deploy-with-helm.md#zenml-helm-installation) section.

### Collect information from your SQL database service

Using an external MySQL-compatible database service is optional, but is recommended for production deployments. If omitted, ZenML will default to using an embedded SQLite database, which has the following limitations:

* the SQLite database is not persisted, meaning that it will be lost if the ZenML server pod is restarted or deleted
* the SQLite database does not scale horizontally, meaning that you will not be able to use more than one replica at a time for the ZenML server pod

If you decide to use an external MySQL-compatible database service, you will need to collect and prepare the following information for the Helm chart configuration:

* the hostname and port where the SQL database is reachable from the Kubernetes cluster
* the username and password that will be used to connect to the database. It is recommended that you create a dedicated database user for the ZenML server and that you restrict its privileges to only access the database that will be used by ZenML. Enforcing secure SSL connections for the user/database is also recommended. See the [MySQL documentation](https://dev.mysql.com/doc/refman/5.7/en/access-control.html) for more information on how to set up users and privileges.
* the name of the database that will be used by ZenML. The database does not have to exist prior to the deployment ( ZenML will create it on the first start). However, you need to create the database if you follow the best practice of restricting database user privileges to only access it.
* if you plan on using SSL to secure the client database connection, you may also need to prepare additional SSL certificates and keys:
  * the TLS CA certificate that was used to sign the server TLS certificate, if you're using a self-signed certificate or signed by a custom certificate authority that is not already trusted by default by most operating systems.
  * the TLS client certificate and key. This is only needed if you decide to use client certificates for your DB connection (some managed DB services support this, CloudSQL is an example).

### Collect information from your secrets management service

Using an externally managed secrets management service like those offered by Google Cloud, AWS, Azure or HashiCorp Vault is optional, but is recommended if you are already using those cloud service providers. If omitted, ZenML will default to using the SQL database to store secrets.

If you decide to use an external secrets management service, you will need to collect and prepare the following information for the Helm chart configuration (for supported back-ends only):

For the AWS secrets manager:

* the AWS region that you want to use to store your secrets
* an AWS access key ID and secret access key that provides full access to the AWS secrets manager service. You can create a dedicated IAM user for this purpose, or use an existing user with the necessary permissions. If you deploy the ZenML server in an EKS Kubernetes cluster that is already configured to use implicit authorization with an IAM role for service accounts, you can omit this step.

For the Google Cloud secrets manager:

* the Google Cloud project ID that you want to use to store your secrets
* a Google Cloud service account that has access to the secrets manager service. You can create a dedicated service account for this purpose, or use an existing service account with the necessary permissions.

For the Azure Key Vault:

* the name of the Azure Key Vault that you want to use to store your secrets
* the Azure tenant ID, client ID, and client secret associated with the Azure service principal that will be used to access the Azure Key Vault. You can create a dedicated application service principal for this purpose, or use an existing service principal with the necessary permissions. If you deploy the ZenML server in an AKS Kubernetes cluster that is already configured to use implicit authorization through the Azure-managed identity service, you can omit this step.

For the HashiCorp Vault:

* the URL of the HashiCorp Vault server
* the token that will be used to access the HashiCorp Vault server.

### Optional cluster services

It is common practice to install additional infrastructure-related services in a Kubernetes cluster to support the deployment and long-term management of applications. For example:

* an Ingress service like [nginx-ingress](https://kubernetes.github.io/ingress-nginx/deploy/) is recommended if you want to expose HTTP services to the internet. An Ingress is required if you want to use secure HTTPS for your ZenML deployment. The alternative is to use a LoadBalancer service to expose the ZenML service using plain HTTP, but this is not recommended for production.
* a [cert-manager](https://cert-manager.io/docs/installation/) is recommended if you want to generate and manage TLS certificates for your ZenML deployment. It can be used to automatically provision TLS certificates from a certificate authority (CA) of your choice, such as [Let's Encrypt](https://letsencrypt.org/). As an alternative, the ZenML Helm chart can be configured to auto-generate self-signed or you can generate the certificates yourself and provide them to the Helm chart, but this makes it more difficult to manage the certificates and you need to manually renew them when they expire.

## ZenML Helm Installation

### Configure the Helm chart

To use the Helm chart with custom values that includes path to files like the database SSL certificates, you need to pull the chart to your local directory first. You can do this with the following command:

```bash
helm pull oci://public.ecr.aws/zenml/zenml --version <VERSION> --untar
```

Next, to customize the Helm chart for your deployment, you should create a copy of the `values.yaml` file that you can find at `./zenml-server/values.yaml`  (let’s call this `custom-values.yaml`). You’ll use this as a template to customize your configuration. Any values that you don’t override you should simply remove from your `custom-values.yaml` file to keep it clean and compatible with future Helm chart releases.

In most cases, you’ll need to change the following configuration values in `custom-values.yaml`:

* the default username and password values
* the database configuration, if you mean to use an external database:
  * the database URL, formatted as `mysql://<username>:<password>@<hostname>:<port>/<database>`
  * CA and/or client TLS certificates, if you’re using SSL to secure the connection to the database
* the Ingress configuration, if enabled:
  * enabling TLS
  * enabling self-signed certificates
  * configuring the hostname that will be used to access the ZenML server, if different from the IP address or hostname associated with the Ingress service installed in your cluster

> **Note** All the file paths that you use in your helm chart (e.g. for certificates like `database.sslCa`) must be relative to the `./zenml-server` helm chart directory, meaning that you also have to copy these files there.

### Install the Helm chart

Once everything is configured, you can run the following command in the `./zenml-server` folder to install the Helm chart.

```
helm -n <namespace> --create-namespace install zenml-server . --values custom-values.yaml 
```

### Connect to the deployed ZenML server

The Helm chart should print out a message with the URL of the deployed ZenML server. You can use the URL to open the ZenML UI in your browser. You can also use the URL to connect your local ZenML client to the server.

To connect to a ZenML server, you can either pass the configuration as command line arguments or as a YAML file:

```bash
zenml connect --url=https://zenml.example.com:8080 --no-verify-ssl
```

or

```bash
zenml connect --config=/path/to/zenml_server_config.yaml
```

The YAML file should have the following structure when connecting to a ZenML server:

```yaml
url: <The URL of the ZenML server>
verify_ssl: |
  <Either a boolean, in which case it controls whether the
  server's TLS certificate is verified, or a string, in which case it
  must be a path to a CA certificate bundle to use or the CA bundle
  value itself>
```

Example of a ZenML server YAML configuration file:

```yaml
url: https://ac8ef63af203226194a7725ee71d85a-7635928635.us-east-1.elb.amazonaws.com/zenml
verify_ssl: |
  -----BEGIN CERTIFICATE-----
  MIIDETCCAfmgAwIBAgIQYUmQg2LR/pHAMZb/vQwwXjANBgkqhkiG9w0BAQsFADAT
  MREwDwYDVQQDEwh6ZW5tbC1jYTAeFw0yMjA5MjYxMzI3NDhaFw0yMzA5MjYxMzI3
...
  ULnzA0JkRWRnFqH6uXeJo1KAVqtxn1xf8PYxx3NlNDr9wi8KKwARf2lwm6sH4mvq
  1aZ/0iYnGKCu7rLJzxeguliMf69E
  -----END CERTIFICATE-----
```

Both options can be combined, in which case the command line arguments will override the values in the YAML file. For example, it is possible to supply the password only as a command line argument:

```bash
zenml connect --username zenml --password='Pa@#$#word' --config=/path/to/zenml_server_config.yaml
```

To disconnect from the current ZenML server and revert to using the local default database, use the following command:

```bash
zenml disconnect
```

## ZenML Helm Deployment Scenarios

This section covers some common Helm deployment scenarios for ZenML.

### Minimal deployment

The example below is a minimal configuration for a ZenML server deployment that uses a temporary SQLite database and a ClusterIP service that is not exposed to the internet:

```yaml
zenml:

  # Use your own password here
  defaultPassword: password

  ingress:
    enabled: false
```

Once deployed, you have to use port-forwarding to access the ZenML server and to connect to it from your local machine:

```bash
kubectl -n zenml-server port-forward svc/zenml-server 8080:8080
zenml connect --url=http://localhost:8080 --username=default --password password
```

This is just a simple example only fit for testing and evaluation purposes. For production deployments, you should use an external database and an Ingress service with TLS certificates to secure and expose the ZenML server to the internet.

### Basic deployment with local database

This deployment use-case still uses a local database, but it exposes the ZenML server to the internet using an Ingress service with TLS certificates generated by the cert-manager and signed by Let's Encrypt.

First, you need to install cert-manager and nginx-ingress in your Kubernetes cluster. You can use the following commands to install them with their default configuration:

```bash
helm repo add jetstack https://charts.jetstack.io
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm install cert-manager jetstack/cert-manager --namespace cert-manager --create-namespace --set installCRDs=true
helm install nginx-ingress ingress-nginx/ingress-nginx --namespace nginx-ingress --create-namespace
```

Next, you need to create a ClusterIssuer resource that will be used by cert-manager to generate TLS certificates with Let's Encrypt:

```bash
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-staging
  namespace: cert-manager
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: <your email address here>
    privateKeySecretRef:
      name: letsencrypt-staging
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

Finally, you can deploy the ZenML server with the following Helm values:

```yaml
zenml:

  # Use your own password here
  defaultPassword: password

  ingress:
    enabled: true
    annotations:
      cert-manager.io/cluster-issuer: "letsencrypt-staging"
    tls:
      enabled: true
      generateCerts: false
```

> **Note** This use-case exposes ZenML at the root URL path of the IP address or hostname of the Ingress service. You cannot share the same Ingress hostname and URL path for multiple applications. See the next section for a solution to this problem.

### Shared Ingress controller

If the root URL path of your Ingress controller is already in use by another application, you cannot use it for ZenML. This section presents three possible solutions to this problem.

#### Use a dedicated Ingress hostname for ZenML

If you know the IP address of the load balancer in use by your Ingress controller, you can use a service like https://nip.io/ to create a new DNS name associated with it and expose ZenML at this new root URL path. For example, if your Ingress controller has the IP address `192.168.10.20`, you can use a DNS name like `zenml.192.168.10.20.nip.io` to expose ZenML at the root URL path `https://zenml.192.168.10.20.nip.io`.

To find the IP address of your Ingress controller, you can use a command like the following:

```bash
kubectl -n nginx-ingress get svc nginx-ingress-ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

You can deploy the ZenML server with the following Helm values:

```yaml
zenml:

  # Use your own password here
  defaultPassword: password

  ingress:
    enabled: true
    annotations:
      cert-manager.io/cluster-issuer: "letsencrypt-staging"
    host: zenml.<nginx ingress IP address>.nip.io
    tls:
      enabled: true
      generateCerts: false
```

> **Note** This method does not work if your Ingress controller is behind a load balancer that uses a hostname mapped to several IP addresses instead of an IP address.

#### Use a dedicated Ingress URL path for ZenML

If you cannot use a dedicated Ingress hostname for ZenML, you can use a dedicated Ingress URL path instead. For example, you can expose ZenML at the URL path `https://<your ingress hostname>/zenml`.

To deploy the ZenML server with a dedicated Ingress URL path, you can use the following Helm values:

```yaml
zenml:

  # Use your own password here
  defaultPassword: password

  ingress:
    enabled: true
    annotations:
      cert-manager.io/cluster-issuer: "letsencrypt-staging"
      nginx.ingress.kubernetes.io/rewrite-target: /$1
    path: /zenml/?(.*)
    tls:
      enabled: true
      generateCerts: false
```

> **Note** This method has one current limitation: the ZenML UI does not support URL rewriting and will not work properly if you use a dedicated Ingress URL path. You can still connect your client to the ZenML server and use it to run pipelines as usual, but you will not be able to use the ZenML UI.

#### Use a DNS service to map a different hostname to the Ingress controller

This method requires you to configure a DNS service like AWS Route 53 or Google Cloud DNS to map a different hostname to the Ingress controller. For example, you can map the hostname `zenml.<subdomain>` to the Ingress controller's IP address or hostname. Then, simply use the new hostname to expose ZenML at the root URL path.

### Secret Backends

{% tabs %}
{% tab title="AWS" %}
#### Using the AWS Secrets Manager as a secrets store backend

Unless explicitly disabled or configured otherwise, the ZenML server will use the SQL database as a secrets store backend. If you want to use the AWS Secrets Manager instead, you need to configure it in the Helm values. Depending on where you deploy your ZenML server and how your Kubernetes cluster is configured, you may also need to provide the AWS credentials needed to access the AWS Secrets Manager API:

```yaml
 zenml:

   # ...

   # Secrets store settings. This is used to store centralized secrets.
   secretsStore:

     # Set to false to disable the secrets store.
     enabled: true

     # The type of the secrets store
     type: aws

     # Configuration for the AWS Secrets Manager secrets store
     aws:

       # The AWS region to use. This must be set to the region where the AWS
       # Secrets Manager service that you want to use is located.
       region_name: us-east-1

       # The AWS credentials to use to authenticate with the AWS Secrets
       # Manager instance. You can omit these if you are running the ZenML server
       # in an AWS EKS cluster that has an IAM role attached to it that has
       # permissions to access the AWS Secrets Manager instance.
       aws_access_key_id: <your AWS access key ID>
       aws_secret_access_key: <your AWS secret access key>
       aws_session_token: <your AWS session token>
```
{% endtab %}

{% tab title="GCP" %}
#### Using the GCP Secrets Manager as a secrets store backend

Unless explicitly disabled or configured otherwise, the ZenML server will use the SQL database as a secrets store backend. If you want to use the GCP Secrets Manager instead, you need to configure it in the Helm values. Depending on where you deploy your ZenML server and how your Kubernetes cluster is configured, you may also need to provide the GCP credentials needed to access the GCP Secrets Manager API:

```yaml
 zenml:

   # ...

   # Secrets store settings. This is used to store centralized secrets.
   secretsStore:

     # Set to false to disable the secrets store.
     enabled: true

     # The type of the secrets store
     type: gcp

     # Configuration for the GCP Secrets Manager secrets store
     gcp:

       # The GCP project ID to use. This must be set to the project ID where the
       # GCP Secrets Manager service that you want to use is located.
       project_id: my-gcp-project

       # Path to the GCP credentials file to use to authenticate with the GCP Secrets
       # Manager instance. You can omit this if you are running the ZenML server
       # in a GCP GKE cluster that uses workload identity to authenticate with
       # GCP services without the need for credentials.
       # NOTE: the credentials file needs to be copied in the helm chart folder
       # and the path configured here needs to be relative to the root of the
       # helm chart.
       google_application_credentials: cloud-credentials.json

 serviceAccount:

   # If you're using workload identity, you need to annotate the service
   # account with the GCP service account name (see https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity)
   annotations:
     iam.gke.io/gcp-service-account: <SERVICE_ACCOUNT_NAME>@<PROJECT_NAME>.iam.gserviceaccount.com

```
{% endtab %}

{% tab title="Azure" %}
#### Using the Azure Key Vault as a secrets store backend

Unless explicitly disabled or configured otherwise, the ZenML server will use the SQL database as a secrets store backend. If you want to use the Azure Key Vault service instead, you need to configure it in the Helm values. Depending on where you deploy your ZenML server and how your Kubernetes cluster is configured, you may also need to provide the Azure credentials needed to access the Azure Key Vault API:

```yaml
 zenml:

   # ...

   # Secrets store settings. This is used to store centralized secrets.
   secretsStore:

     # Set to false to disable the secrets store.
     enabled: true

     # The type of the secrets store
     type: azure

     # Configuration for the Azure Key Vault secrets store
     azure:

       # The name of the Azure Key Vault. This must be set to point to the Azure
       # Key Vault instance that you want to use.
       key_vault_name:

       # The Azure application service principal credentials to use to
       # authenticate with the Azure Key Vault API. You can omit these if you are
       # running the ZenML server hosted in Azure and are using a managed
       # identity to access the Azure Key Vault service.
       azure_client_id: <your Azure client ID>
       azure_client_secret: <your Azure client secret>
       azure_tenant_id: <your Azure tenant ID>
```
{% endtab %}

{% tab title="Hashicorp" %}
#### Using the HashiCorp Vault as a secrets store backend

Unless explicitly disabled or configured otherwise, the ZenML server will use the SQL database as a secrets store backend. If you want to use the HashiCorp Vault service instead, you need to configure it in the Helm values:

```yaml
 zenml:

   # ...

   # Secrets store settings. This is used to store centralized secrets.
   secretsStore:

     # Set to false to disable the secrets store.
     enabled: true

     # The type of the secrets store
     type: hashicorp

     # Configuration for the HashiCorp Vault secrets store
     hashicorp:

       # The url of the HashiCorp Vault server to use
       vault_addr: https://vault.example.com
       # The token used to authenticate with the Vault server
       vault_token: <your Vault token>
       # The Vault Enterprise namespace. Not required for Vault OSS.
       vault_namespace: <your Vault namespace>
```
{% endtab %}

{% tab title="Custom" %}
#### Using a custom secrets store backend implementation

You have the option of using [a custom implementation of the secrets store API](../../user-guide/advanced-guide/secret-management/secret-management.md) as your secrets store back-end. This must come in the form of a class derived from `zenml.zen_stores.secrets_stores.base_secrets_store.BaseSecretsStore`. This class must be importable from within the ZenML server container, which means you most likely need to build a custom container image that contains the class. Then, you can configure the Helm values to use your custom secrets store as follows:

```yaml
 zenml:

   # ...

   # Secrets store settings. This is used to store centralized secrets.
   secretsStore:

     # Set to false to disable the secrets store.
     enabled: true

     # The type of the secrets store
     type: custom

     # Configuration for the HashiCorp Vault secrets store
     custom:

       # The class path of the custom secrets store implementation. This should
       # point to a full Python class that extends the
       # `zenml.zen_stores.secrets_stores.base_secrets_store.BaseSecretsStore`
       # base class. The class should be importable from the container image
       # that you are using for the ZenML server.
       class_path: my.custom.secrets.store.MyCustomSecretsStore

   # Extra environment variables used to configure the custom secrets store.
   environment:
     ZENML_SECRETS_STORE_OPTION_1: value1
     ZENML_SECRETS_STORE_OPTION_2: value2

   # Extra environment variables to set in the ZenML server container that
   # should be kept secret and are used to configure the custom secrets store.
   secretEnvironment:
     ZENML_SECRETS_STORE_SECRET_OPTION_3: value3
     ZENML_SECRETS_STORE_SECRET_OPTION_4: value4
```
{% endtab %}
{% endtabs %}

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
