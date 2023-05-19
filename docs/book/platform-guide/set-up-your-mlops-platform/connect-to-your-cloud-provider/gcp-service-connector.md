---
description: >-
  Configure GCP Service Connectors to connect ZenML to GCP resources such as GCS
  buckets, GKE Kubernetes clusters and GCR container registries.
---

# GCP Service Connector

The ZenML GCP Service Connector facilitates the authentication and access to managed GCP services and resources. These encompass a range of resources, including GCS buckets, GCR container repositories and GKE clusters. The connector provides support for various authentication methods, including GCP user accounts, service accounts, short-lived OAuth 2.0 tokens and implicit authentication.

To ensure heightened security measures, this connector always issues [short-lived OAuth 2.0 tokens to clients instead of long-lived credentials](best-security-practices.md#generating-temporary-and-down-scoped-credentials). Furthermore, it includes [automatic configuration and detection of credentials locally configured through the GCP CLI](service-connectors-guide.md#auto-configuration).

This connector serves as a general means of accessing any GCP service by issuing OAuth 2.0 credential objects to clients. Additionally, the connector can handle specialized authentication for GCS, Docker and Kubernetes Python clients. It also allows for the configuration of local Docker and Kubernetes CLIs.

```
$ zenml service-connector list-types --type gcp
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━┯━━━━━━━┯━━━━━━━━┓
┃         NAME          │ TYPE   │ RESOURCE TYPES        │ AUTH METHODS    │ LOCAL │ REMOTE ┃
┠───────────────────────┼────────┼───────────────────────┼─────────────────┼───────┼────────┨
┃ GCP Service Connector │ 🔵 gcp │ 🔵 gcp-generic        │ implicit        │ ✅    │ ✅     ┃
┃                       │        │ 📦 gcs-bucket         │ user-account    │       │        ┃
┃                       │        │ 🌀 kubernetes-cluster │ service-account │       │        ┃
┃                       │        │ 🐳 docker-registry    │ oauth2-token    │       │        ┃
┃                       │        │                       │ impersonation   │       │        ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━┷━━━━━━━┷━━━━━━━━┛
```

## Prerequisites

The GCP Service Connector is part of the GCP ZenML integration. You can either install the entire integration or use a pypi extra to install it independently of the integration:

* `pip install zenml[connectors-gcp]` installs only prerequisites for the GCP Service Connector Type
* `zenml integration install gcp` installs the entire GCP ZenML integration

It is not required to [install and set up the GCP CLI on your local machine](https://cloud.google.com/sdk/gcloud) to use the GCP Service Connector to link Stack Components to GCP resources and services. However, it is recommended to do so if you are looking for a quick setup that includes using the auto-configuration Service Connector features.

{% hint style="info" %}
The auto-configuration examples in this page rely on the GCP CLI being installed and already configured with valid credentials of one type or another. If you want to avoid installing the GCP CLI, we recommend using the interactive mode of the ZenML CLI to register Service Connectors:

```
zenml service-connector register -i --type gcp
```
{% endhint %}

## Resource Types

### Generic GCP resource

This resource type allows Stack Components to use the GCP Service Connector to connect to any GCP service or resource. When used by Stack Components, they are provided a Python google-auth credentials object populated with a GCP OAuth 2.0 token. This credentials object can then be used to create GCP Python clients for any particular GCP service.

This generic GCP resource type is meant to be used with Stack Components that are not represented by other, more specific resource type, like GCS buckets, Kubernetes clusters or Docker registries. For example, it can be used with the Google Cloud Builder Image Builder stack component, or the Vertex AI Orchestrator and Step Operator. It should be accompanied by a matching set of GCP permissions that allow access to the set of remote resources required by the client and Stack Component.

The resource name represents the GCP project that the connector is authorized to access.

### GCS bucket

Allows Stack Components to connect to GCS buckets. When used by Stack Components, they are provided a pre-configured GCS Python client instance.

The configured credentials must have at least the following [GCP permissions](https://cloud.google.com/iam/docs/permissions-reference) associated with the GCS buckets that it can access:

* `storage.buckets.list`
* `storage.buckets.get`
* `storage.objects.create`
* `storage.objects.delete`
* `storage.objects.get`
* `storage.objects.list`
* `storage.objects.update`

For example, the GCP Storage Admin role includes all of the required permissions, but it also includes additional permissions that are not required by the connector.

If set, the resource name must identify a GCS bucket using one of the following formats:

* GCS bucket URI (canonical resource name): gs://{bucket-name}
* GCS bucket name: {bucket-name}

### EKS Kubernetes cluster

Allows Stack Components to access a GKE cluster as a standard Kubernetes cluster resource. When used by Stack Components, they are provided a pre-authenticated Python Kubernetes client instance.

The configured credentials must have at least the following [GCP permissions](https://cloud.google.com/iam/docs/permissions-reference) associated with the GKE clusters that it can access:

* `container.clusters.list`
* `container.clusters.get`

In addition to the above permissions, the credentials should include permissions to connect to and use the GKE cluster (i.e. some or all permissions in the Kubernetes Engine Developer role).

If set, the resource name must identify an GKE cluster using one of the following formats:

* GKE cluster name: `{cluster-name}`

GKE cluster names are project scoped. The connector can only be used to access GKE clusters in the GCP project that it is configured to use.

### ECR container registry

Allows Stack Components to access a GCR registry as a standard Docker registry resource. When used by Stack Components, they are provided a pre-authenticated Python Docker client instance.

The configured credentials must have at least the following [GCP permissions](https://cloud.google.com/iam/docs/permissions-reference):

* `storage.buckets.get`
* `storage.multipartUploads.abort`
* `storage.multipartUploads.create`
* `storage.multipartUploads.list`
* `storage.multipartUploads.listParts`
* `storage.objects.create`
* `storage.objects.delete`
* `storage.objects.list`

The Storage Legacy Bucket Writer role includes all of the above permissions while at the same time restricting access to only the GCR buckets.

The resource name associated with this resource type identifies the GCR container registry associated with the GCP configured project (the repository name is optional):

* GCR repository URI: `[https://]gcr.io/{project-id}[/{repository-name}]`

## Authentication Methods

### Implicit authentication

[Implicit authentication](best-security-practices.md#implicit-authentication) to GCP services using [Application Default Credentials](https://cloud.google.com/docs/authentication/provide-credentials-adc). This authentication method doesn't require any credentials to be explicitly configured. It automatically discovers and uses credentials from one of the following sources:

* environment variables (GOOGLE\_APPLICATION\_CREDENTIALS)
* local ADC credential files set up by running `gcloud auth application-default login` (e.g. `~/.config/gcloud/application_default_credentials.json`).
* GCP service account attached to the resource where the ZenML server is running. Only works when running the ZenML server on a GCP resource with an service account attached to it or when using Workload Identity (e.g. GKE cluster).

This is the quickest and easiest way to authenticate to GCP services. However, the results depend on how ZenML is deployed and the environment where it is used and are thus not fully reproducible:

* when used with the default local ZenML deployment or a local ZenML server, the credentials are those set up on your machine (i.e. by running `gcloud auth application-default login` or setting the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to point to a service account key JSON file).
* when connected to a ZenML server, this method only works if the ZenML server is deployed in GCP and will use the service account attached to the GCP resource where the ZenML server is running (e.g. an GKE cluster). The service account permissions may need to be adjusted to allow listing and accessing/describing the GCP resources that the connector is configured to access.

This is the quickest and easiest way to authenticate to AWS services. However, the results depend on how ZenML is deployed and the environment where it is used and is thus not fully reproducible:

* when used with the default local ZenML deployment or a local ZenML server, the credentials are the same as those used by the AWS CLI or extracted from local environment variables
* when connected to a ZenML server, this method only works if the ZenML server is deployed in AWS and will use the IAM role attached to the AWS resource where the ZenML server is running (e.g. an EKS cluster). The IAM role permissions may need to be adjusted to allows listing and accessing/describing the AWS resources that the connector is configured to access.

Note that the discovered credentials inherit the full set of permissions of the local GCP CLI credentials or service account attached to the GCP workload. Depending on the extent of those permissions, this authentication method might not be recommended for production use, as it can lead to accidental privilege escalation. Instead, it is recommended to use the Service Account Key or Service Account Impersonation authentication methods to restrict the permissions that are granted to the connector clients.

To find out more about Application Default Credentials, [see the GCP ADC documentation](https://cloud.google.com/docs/authentication/provide-credentials-adc).

A GCP project is required and the connector may only be used to access GCP resources in the specified project. When used remotely in a GCP workload, the configured project has to be the same as the project of the attached service account.

<details>

<summary>Example configuration</summary>

The following assumes the local GCP CLI has already been configured with user account credentials by running the `gcloud auth application-default login` command:

```
$ zenml service-connector register gcp-implicit --type gcp --auth-method implicit

```

No credentials are stored with the Service Connector:

```
$ zenml service-connector describe gcp-implicit 

```

Verifying access to resources:

```
$ zenml service-connector verify gcp-implicit --resource-type gcs-bucket

```

</details>

### GCP User Account

[Long-lived GCP credentials](best-security-practices.md#long-lived-credentials-api-keys-account-keys) consisting of a GCP user account and its credentials.

This method requires GCP user account credentials like those generated by the `gcloud auth application-default login` command. The GCP connector [generates temporary OAuth 2.0 tokens](best-security-practices.md#generating-temporary-and-down-scoped-credentials) from the user account credentials and distributes them to clients. The tokens have a limited lifetime of 1 hour.

This method is preferred during development and testing due to its simplicity and ease of use. It is not recommended as a direct authentication method for production use cases because the clients are granted the full set of permissions of the GCP user account. For production, it is recommended to use the GCP Service Account or GCP Service Account Impersonation authentication methods.

A GCP project is required and the connector may only be used to access GCP resources in the specified project.

If you already have the local GCP CLI set up with these credentials, they will be automatically picked up when auto-configuration is used (see the example below).

<details>

<summary>Example auto-configuration</summary>

The following assumes the local GCP CLI has been configured with GCP user account credentials by running the `gcloud auth application-default login` command:

```
$ zenml service-connector register gcp-user-account --type gcp --auth-method user-accoint --auto-configure

```

The GCP user account credentials were lifted up from the local host:

```
$ zenml service-connector describe gcp-user-account

```



</details>

### GCP Service Account

[Long-lived GCP credentials](best-security-practices.md#long-lived-credentials-api-keys-account-keys) consisting of a GCP service account and its credentials.

This method requires [a GCP service account](https://cloud.google.com/iam/docs/service-account-overview) and [a service account key JSON](https://cloud.google.com/iam/docs/service-account-creds#key-types) created for it. The GCP connector generates temporary OAuth 2.0 tokens from the user account credentials and distributes them to clients. The tokens have a limited lifetime of 1 hour.

A GCP project is required and the connector may only be used to access GCP resources in the specified project.

If you already have the `GOOGLE_APPLICATION_CREDENTIALS` environment variable configured to point to a service account key JSON file, it will be automatically picked up when auto-configuration is used.

### GCP Service Account impersonation

Generates [temporary STS credentials](best-security-practices.md#impersonating-accounts-and-assuming-roles) by [impersonating another GCP service account](https://cloud.google.com/iam/docs/create-short-lived-credentials-direct#sa-impersonation).

The connector needs to be configured with the email address of the target GCP service account to be impersonated, accompanied by a GCP service account key JSON for the primary service account. The primary service account must have permissions to generate tokens for the target service account (i.e. [the Service Account Token Creator role](https://cloud.google.com/iam/docs/service-account-permissions#directly-impersonate)). The connector will generate temporary OAuth 2.0 tokens upon request by using [GCP direct service account impersonation](https://cloud.google.com/iam/docs/create-short-lived-credentials-direct#sa-impersonation). The tokens have a configurable limited lifetime of up to 1 hour.

[The best practice implemented with this authentication scheme](best-security-practices.md#impersonating-accounts-and-assuming-roles) is to keep the set of permissions associated with the primary service account down to the bare minimum and grant permissions to the privilege bearing service account instead.

A GCP project is required and the connector may only be used to access GCP resources in the specified project.

If you already have the `GOOGLE_APPLICATION_CREDENTIALS` environment variable configured to point to the primary service account key JSON file, it will be automatically picked up when auto-configuration is used.

### GCP OAuth 2.0 token

Uses [temporary OAuth 2.0 tokens](best-security-practices.md#short-lived-credentials) explicitly configured by the user.

This method has the major limitation that the user must regularly generate new tokens and update the connector configuration as OAuth 2.0 tokens expire. This method is best used in cases where the connector only needs to be used for a short period of time.

Using any of the other authentication methods will automatically generate and refresh OAuth 2.0 tokens for clients upon request.

A GCP project is required and the connector may only be used to access GCP resources in the specified project.

## Auto-configuration

The GCP Service Connector allows [auto-discovering and fetching credentials](service-connectors-guide.md#auto-configuration) and configuration [set up by the GCP CLI](https://cloud.google.com/sdk/gcloud) during registration.

<details>

<summary>Auto-configuration example</summary>

The following is an example of lifting GCP user credentials granting access to the same set of GCP resources and services that the local GCP CLI is allowed to access. In this case, the [GCP user account authentication method](gcp-service-connector.md#gcp-user-account) was automatically detected:

```
$ zenml service-connector register gcp-auto --type gcp --auto-configure

$ zenml service-connector describe gcp-auto 

$ zenml service-connector verify gcp-auto --resource-type gcs-bucket

$ zenml service-connector verify gcp-auto --resource-type kubernetes-cluster

```

</details>

## Local client provisioning

The local Kubernetes `kubectl` CLI and the Docker CLI can be[ configured with credentials extracted from or generated by a compatible GCP Service Connector](service-connectors-guide.md#configure-local-clients). Please note that unlike the configuration made possible through the GCP CLI, the credentials issued by the GCP Service Connector have a short lifetime and will need to be regularly refreshed. This is a byproduct of implementing a high security profile. &#x20;

<details>

<summary>Local CLI configuration examples</summary>

The following shows an example of configuring the local Kubernetes CLI to access a GKE cluster reachable through a GCP Service Connector:

```
$ zenml service-connector list

$ zenml service-connector verify gcp-user-account --resource-type kubernetes-cluster

$ zenml service-connector login gcp-user-account --resource-type kubernetes-cluster --resource-id zenhacks-cluster

$ kubectl cluster-info

```

A similar process is possible with GCR container registries:

```
$ zenml service-connector verify gcp-user-account --resource-type docker-registry


$ zenml service-connector login gcp-user-account --resource-type docker-registry 

$ docker pull gcr.io/zenml-server

```

</details>

{% hint style="info" %}
This Service Connector does not support configuring the local GCP CLI with credentials stored in or generated from the connector configuration. If this feature is useful to you or your organization, please let us know by messaging us in [Slack](https://zenml.io/slack-invite) or [creating an issue on GitHub](https://github.com/zenml-io/zenml/issues).
{% endhint %}

## Stack Components use

The GCS Artifact Store Stack Component can be connected to a remote GCS bucket through a GCP Service Connector.

The GCP Service Connector can also be used in a wide range of Orchestrators and Model Deployer stack component flavors that rely on Kubernetes clusters to manage their workloads. This allows GKE Kubernetes container workloads to be managed without the need to configure and maintain explicit GCP or Kubernetes `kubectl` configuration contexts and credentials in the target environment and in the Stack Component.

Similarly, Container Registry Stack Components can be connected to a GCR Container Registry through an GCP Service Connector. This allows container images to be built and published to GCR container registries without the need to configure explicit GCP credentials in the target environment or the Stack Component.
