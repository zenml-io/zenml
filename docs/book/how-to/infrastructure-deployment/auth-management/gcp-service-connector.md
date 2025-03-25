---
description: >-
  Configuring GCP Service Connectors to connect ZenML to GCP resources such as
  GCS buckets, GKE Kubernetes clusters, and GCR container registries.
---

# GCP Service Connector

The ZenML GCP Service Connector facilitates the authentication and access to managed GCP services and resources. These encompass a range of resources, including GCS buckets, GAR and GCR container repositories, and GKE clusters. The connector provides support for various authentication methods, including GCP user accounts, service accounts, short-lived OAuth 2.0 tokens, and implicit authentication.

To ensure heightened security measures, this connector always issues [short-lived OAuth 2.0 tokens to clients instead of long-lived credentials](best-security-practices.md#generating-temporary-and-down-scoped-credentials) unless explicitly configured to do otherwise. Furthermore, it includes [automatic configuration and detection of credentials locally configured through the GCP CLI](service-connectors-guide.md#auto-configuration).

This connector serves as a general means of accessing any GCP service by issuing OAuth 2.0 credential objects to clients. Additionally, the connector can handle specialized authentication for GCS, Docker, and Kubernetes Python clients. It also allows for the configuration of local Docker and Kubernetes CLIs.

```shell
$ zenml service-connector list-types --type gcp
```
```shell
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━┯━━━━━━━┯━━━━━━━━┓
┃         NAME          │ TYPE   │ RESOURCE TYPES        │ AUTH METHODS     │ LOCAL │ REMOTE ┃
┠───────────────────────┼────────┼───────────────────────┼──────────────────┼───────┼────────┨
┃ GCP Service Connector │ 🔵 gcp │ 🔵 gcp-generic        │ implicit         │ ✅    │ ✅     ┃
┃                       │        │ 📦 gcs-bucket         │ user-account     │       │        ┃
┃                       │        │ 🌀 kubernetes-cluster │ service-account  │       │        ┃
┃                       │        │ 🐳 docker-registry    │ external-account │       │        ┃
┃                       │        │                       │ oauth2-token     │       │        ┃
┃                       │        │                       │ impersonation    │       │        ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━┷━━━━━━━┷━━━━━━━━┛
```

## Prerequisites

The GCP Service Connector is part of the GCP ZenML integration. You can either install the entire integration or use a PyPI extra to install it independently of the integration:

* `pip install "zenml[connectors-gcp]"` installs only prerequisites for the GCP Service Connector Type
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

This generic GCP resource type is meant to be used with Stack Components that are not represented by one of the other, more specific resource types like GCS buckets, Kubernetes clusters, or Docker registries. For example, it can be used with [the Google Cloud Image Builder](https://docs.zenml.io/stacks/image-builders/gcp) stack component, or [the Vertex AI Orchestrator](https://docs.zenml.io/stacks/orchestrators/vertex) and [Step Operator](https://docs.zenml.io/stacks/step-operators/vertex). It should be accompanied by a matching set of GCP permissions that allow access to the set of remote resources required by the client and Stack Component (see the documentation of each Stack Component for more details).

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

### GKE Kubernetes cluster

Allows Stack Components to access a GKE cluster as a standard Kubernetes cluster resource. When used by Stack Components, they are provided a pre-authenticated Python Kubernetes client instance.

The configured credentials must have at least the following [GCP permissions](https://cloud.google.com/iam/docs/permissions-reference) associated with the GKE clusters that it can access:

* `container.clusters.list`
* `container.clusters.get`

In addition to the above permissions, the credentials should include permissions to connect to and use the GKE cluster (i.e. some or all permissions in the Kubernetes Engine Developer role).

If set, the resource name must identify a GKE cluster using one of the following formats:

* GKE cluster name: `{cluster-name}`

GKE cluster names are project scoped. The connector can only be used to access GKE clusters in the GCP project that it is configured to use.

### GAR container registry (including legacy GCR support)

{% hint style="warning" %}
**Important Notice: Google Container Registry** [**is being replaced by Artifact Registry**](https://cloud.google.com/artifact-registry/docs/transition/transition-from-gcr)**. Please start using Artifact Registry for your containers. As per Google's documentation, "after May 15, 2024, Artifact Registry will host images for the gcr.io domain in Google Cloud projects without previous Container Registry usage. After March 18, 2025, Container Registry will be shut down.".

Support for legacy GCR registries is still included in the GCP service connector. Users that already have GCP service connectors configured to access GCR registries may continue to use them without taking any action. However, it is recommended to transition to Google Artifact Registries as soon as possible by following [the GCP guide on this subject](https://cloud.google.com/artifact-registry/docs/transition/transition-from-gcr) and making the following updates to ZenML GCP Service Connectors that are used to access GCR resources:

* add the IAM permissions documented here to the GCP Service Connector credentials to enable them to access the Artifact Registries.
* users may keep the gcr.io GCR URLs already configured in the GCP Service Connectors as well as those used in linked Container Registry stack components given that these domains are redirected by Google to GAR as covered in the GCR transition guide. Alternatively, users may update the GCP Service Connector configuration and/or the Container Registry stack components to use the replacement Artifact Registry URLs.

The GCP Service Connector will list the legacy GCR registries as accessible for a GCP project even if the GCP Service Connector credentials do not grant access to GCR registries. This is required for backwards-compatibility and will be removed in a future release.
{% endhint %}

Allows Stack Components to access a Google Artifact Registry as a standard Docker registry resource. When used by Stack Components, they are provided a pre-authenticated Python Docker client instance.

The configured credentials must have at least the following [GCP permissions](https://cloud.google.com/iam/docs/understanding-roles#artifact-registry-roles):

* `artifactregistry.repositories.createOnPush`
* `artifactregistry.repositories.downloadArtifacts`
* `artifactregistry.repositories.get`
* `artifactregistry.repositories.list`
* `artifactregistry.repositories.readViaVirtualRepository`
* `artifactregistry.repositories.uploadArtifacts`
* `artifactregistry.locations.list`

The Artifact Registry Create-on-Push Writer role includes all of the above permissions.

This resource type also includes legacy GCR container registry support. When used with GCR registries, the configured credentials must have at least the following [GCP permissions](https://cloud.google.com/iam/docs/understanding-roles#cloud-storage-roles):

* `storage.buckets.get`
* `storage.multipartUploads.abort`
* `storage.multipartUploads.create`
* `storage.multipartUploads.list`
* `storage.multipartUploads.listParts`
* `storage.objects.create`
* `storage.objects.delete`
* `storage.objects.list`

The Storage Legacy Bucket Writer role includes all of the above permissions while at the same time restricting access to only the GCR buckets.

If set, the resource name must identify a GAR or GCR registry using one of the following formats:

* Google Artifact Registry repository URI: `[https://]<region>-docker.pkg.dev/<project-id>/<registry-id>[/<repository-name>]`
* Google Artifact Registry name: `projects/<project-id>/locations/<location>/repositories/<repository-id>`
* (legacy) GCR repository URI: `[https://][us.|eu.|asia.]gcr.io/<project-id>[/<repository-name>]`

The connector can only be used to access GAR and GCR registries in the GCP
project that it is configured to use.

## Authentication Methods

### Implicit authentication

[Implicit authentication](best-security-practices.md#implicit-authentication) to GCP services using [Application Default Credentials](https://cloud.google.com/docs/authentication/provide-credentials-adc).

{% hint style="warning" %}
This method may constitute a security risk, because it can give users access to the same cloud resources and services that the ZenML Server itself is configured to access. For this reason, all implicit authentication methods are disabled by default and need to be explicitly enabled by setting the `ZENML_ENABLE_IMPLICIT_AUTH_METHODS` environment variable or the helm chart `enableImplicitAuthMethods` configuration option to `true` in the ZenML deployment.
{% endhint %}

This authentication method doesn't require any credentials to be explicitly configured. It automatically discovers and uses credentials from one of the following sources:

* environment variables (GOOGLE\_APPLICATION\_CREDENTIALS)
* local ADC credential files set up by running `gcloud auth application-default login` (e.g. `~/.config/gcloud/application_default_credentials.json`).
* a GCP service account attached to the resource where the ZenML server is running. Only works when running the ZenML server on a GCP resource with a service account attached to it or when using Workload Identity (e.g. GKE cluster).

This is the quickest and easiest way to authenticate to GCP services. However, the results depend on how ZenML is deployed and the environment where it is used and is thus not fully reproducible:

* when used with the default local ZenML deployment or a local ZenML server, the credentials are those set up on your machine (i.e. by running `gcloud auth application-default login` or setting the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to point to a service account key JSON file).
* when connected to a ZenML server, this method only works if the ZenML server is deployed in GCP and will use the service account attached to the GCP resource where the ZenML server is running (e.g. a GKE cluster). The service account permissions may need to be adjusted to allow listing and accessing/describing the GCP resources that the connector is configured to access.

Note that the discovered credentials inherit the full set of permissions of the local GCP CLI credentials or service account attached to the ZenML server GCP workload. Depending on the extent of those permissions, this authentication method might not be suitable for production use, as it can lead to accidental privilege escalation. Instead, it is recommended to use [the Service Account Key](gcp-service-connector.md#gcp-service-account) or [Service Account Impersonation](gcp-service-connector.md#gcp-service-account-impersonation) authentication methods to restrict the permissions that are granted to the connector clients.

To find out more about Application Default Credentials, [see the GCP ADC documentation](https://cloud.google.com/docs/authentication/provide-credentials-adc).

A GCP project is required and the connector may only be used to access GCP resources in the specified project. When used remotely in a GCP workload, the configured project has to be the same as the project of the attached service account.

<details>

<summary>Example configuration</summary>

The following assumes the local GCP CLI has already been configured with user account credentials by running the `gcloud auth application-default login` command:

```sh
zenml service-connector register gcp-implicit --type gcp --auth-method implicit --auto-configure
```

{% code title="Example Command Output" %}
```
Successfully registered service connector `gcp-implicit` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃     RESOURCE TYPE     │ RESOURCE NAMES                                  ┃
┠───────────────────────┼─────────────────────────────────────────────────┨
┃    🔵 gcp-generic     │ zenml-core                                      ┃
┠───────────────────────┼─────────────────────────────────────────────────┨
┃     📦 gcs-bucket     │ gs://zenml-bucket-sl                            ┃
┃                       │ gs://zenml-core.appspot.com                     ┃
┃                       │ gs://zenml-core_cloudbuild                      ┃
┃                       │ gs://zenml-datasets                             ┃
┃                       │ gs://zenml-internal-artifact-store              ┃
┃                       │ gs://zenml-kubeflow-artifact-store              ┃
┃                       │ gs://zenml-project-time-series-bucket           ┃
┠───────────────────────┼─────────────────────────────────────────────────┨
┃ 🌀 kubernetes-cluster │ zenml-test-cluster                              ┃
┠───────────────────────┼─────────────────────────────────────────────────┨
┃ 🐳 docker-registry    │ gcr.io/zenml-core                               ┃
┃                       │ us.gcr.io/zenml-core                            ┃
┃                       │ eu.gcr.io/zenml-core                            ┃
┃                       │ asia.gcr.io/zenml-core                          ┃
┃                       │ asia-docker.pkg.dev/zenml-core/asia.gcr.io      ┃
┃                       │ europe-docker.pkg.dev/zenml-core/eu.gcr.io      ┃
┃                       │ europe-west1-docker.pkg.dev/zenml-core/test     ┃
┃                       │ us-docker.pkg.dev/zenml-core/gcr.io             ┃
┃                       │ us-docker.pkg.dev/zenml-core/us.gcr.io          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

No credentials are stored with the Service Connector:

```sh
zenml service-connector describe gcp-implicit
```

{% code title="Example Command Output" %}
```
Service connector 'gcp-implicit' of type 'gcp' with id '0c49a7fe-5e87-41b9-adbe-3da0a0452e44' is owned by user 'default' and is 'private'.
                         'gcp-implicit' gcp Service Connector Details                          
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                                    ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ ID               │ 0c49a7fe-5e87-41b9-adbe-3da0a0452e44                                     ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ NAME             │ gcp-implicit                                                             ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ TYPE             │ 🔵 gcp                                                                   ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ AUTH METHOD      │ implicit                                                                 ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE TYPES   │ 🔵 gcp-generic, 📦 gcs-bucket, 🌀 kubernetes-cluster, 🐳 docker-registry ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE NAME    │ <multiple>                                                               ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ SECRET ID        │                                                                          ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ SESSION DURATION │ N/A                                                                      ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ EXPIRES IN       │ N/A                                                                      ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ OWNER            │ default                                                                  ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ SHARED           │ ➖                                                                       ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ CREATED_AT       │ 2023-05-19 08:04:51.037955                                               ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-05-19 08:04:51.037958                                               ┃
┗━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
       Configuration       
┏━━━━━━━━━━━━┯━━━━━━━━━━━━┓
┃ PROPERTY   │ VALUE      ┃
┠────────────┼────────────┨
┃ project_id │ zenml-core ┃
┗━━━━━━━━━━━━┷━━━━━━━━━━━━┛
```
{% endcode %}

</details>

### GCP User Account

[Long-lived GCP credentials](best-security-practices.md#long-lived-credentials-api-keys-account-keys) consist of a GCP user account and its credentials.

This method requires GCP user account credentials like those generated by the `gcloud auth application-default login` command.

By default, the GCP connector [generates temporary OAuth 2.0 tokens](best-security-practices.md#generating-temporary-and-down-scoped-credentials) from the user account credentials and distributes them to clients. The tokens have a limited lifetime of 1 hour. This behavior can be disabled by setting the `generate_temporary_tokens` configuration option to `False`, in which case, the connector will distribute the user account credentials JSON to clients instead (not recommended).

This method is preferred during development and testing due to its simplicity and ease of use. It is not recommended as a direct authentication method for production use cases because the clients are granted the full set of permissions of the GCP user account. For production, it is recommended to use the GCP Service Account or GCP Service Account Impersonation authentication methods.

A GCP project is required and the connector may only be used to access GCP resources in the specified project.

If you already have the local GCP CLI set up with these credentials, they will be automatically picked up when auto-configuration is used (see the example below).

<details>

<summary>Example auto-configuration</summary>

The following assumes the local GCP CLI has been configured with GCP user account credentials by running the `gcloud auth application-default login` command:

```sh
zenml service-connector register gcp-user-account --type gcp --auth-method user-account --auto-configure
```

{% code title="Example Command Output" %}
```
Successfully registered service connector `gcp-user-account` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃     RESOURCE TYPE     │ RESOURCE NAMES                                  ┃
┠───────────────────────┼─────────────────────────────────────────────────┨
┃    🔵 gcp-generic     │ zenml-core                                      ┃
┠───────────────────────┼─────────────────────────────────────────────────┨
┃     📦 gcs-bucket     │ gs://zenml-bucket-sl                            ┃
┃                       │ gs://zenml-core.appspot.com                     ┃
┃                       │ gs://zenml-core_cloudbuild                      ┃
┃                       │ gs://zenml-datasets                             ┃
┃                       │ gs://zenml-internal-artifact-store              ┃
┃                       │ gs://zenml-kubeflow-artifact-store              ┃
┃                       │ gs://zenml-project-time-series-bucket           ┃
┠───────────────────────┼─────────────────────────────────────────────────┨
┃ 🌀 kubernetes-cluster │ zenml-test-cluster                              ┃
┠───────────────────────┼─────────────────────────────────────────────────┨
┃ 🐳 docker-registry    │ gcr.io/zenml-core                               ┃
┃                       │ us.gcr.io/zenml-core                            ┃
┃                       │ eu.gcr.io/zenml-core                            ┃
┃                       │ asia.gcr.io/zenml-core                          ┃
┃                       │ asia-docker.pkg.dev/zenml-core/asia.gcr.io      ┃
┃                       │ europe-docker.pkg.dev/zenml-core/eu.gcr.io      ┃
┃                       │ europe-west1-docker.pkg.dev/zenml-core/test     ┃
┃                       │ us-docker.pkg.dev/zenml-core/gcr.io             ┃
┃                       │ us-docker.pkg.dev/zenml-core/us.gcr.io          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

The GCP user account credentials were lifted up from the local host:

```sh
zenml service-connector describe gcp-user-account
```

{% code title="Example Command Output" %}
```
Service connector 'gcp-user-account' of type 'gcp' with id 'ddbce93f-df14-4861-a8a4-99a80972f3bc' is owned by user 'default' and is 'private'.
                       'gcp-user-account' gcp Service Connector Details                        
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                                    ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ ID               │ ddbce93f-df14-4861-a8a4-99a80972f3bc                                     ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ NAME             │ gcp-user-account                                                         ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ TYPE             │ 🔵 gcp                                                                   ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ AUTH METHOD      │ user-account                                                             ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE TYPES   │ 🔵 gcp-generic, 📦 gcs-bucket, 🌀 kubernetes-cluster, 🐳 docker-registry ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE NAME    │ <multiple>                                                               ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ SECRET ID        │ 17692951-614f-404f-a13a-4abb25bfa758                                     ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ SESSION DURATION │ N/A                                                                      ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ EXPIRES IN       │ N/A                                                                      ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ OWNER            │ default                                                                  ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ SHARED           │ ➖                                                                       ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ CREATED_AT       │ 2023-05-19 08:09:44.102934                                               ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-05-19 08:09:44.102936                                               ┃
┗━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
          Configuration           
┏━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━┓
┃ PROPERTY          │ VALUE      ┃
┠───────────────────┼────────────┨
┃ project_id        │ zenml-core ┃
┠───────────────────┼────────────┨
┃ user_account_json │ [HIDDEN]   ┃
┗━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━┛
```
{% endcode %}

</details>

### GCP Service Account

[Long-lived GCP credentials](best-security-practices.md#long-lived-credentials-api-keys-account-keys) consisting of a GCP service account and its credentials.

This method requires [a GCP service account](https://cloud.google.com/iam/docs/service-account-overview) and [a service account key JSON](https://cloud.google.com/iam/docs/service-account-creds#key-types) created for it.

By default, the GCP connector [generates temporary OAuth 2.0 tokens](best-security-practices.md#generating-temporary-and-down-scoped-credentials) from the service account credentials and distributes them to clients. The tokens have a limited lifetime of 1 hour. This behavior can be disabled by setting the `generate_temporary_tokens` configuration option to `False`, in which case, the connector will distribute the service account credentials JSON to clients instead (not recommended).

A GCP project is required and the connector may only be used to access GCP resources in the specified project. If the `project_id` is not provided, the connector will use the one extracted from the service account key JSON.

If you already have the `GOOGLE_APPLICATION_CREDENTIALS` environment variable configured to point to a service account key JSON file, it will be automatically picked up when auto-configuration is used.

<details>

<summary>Example configuration</summary>

The following assumes a GCP service account was created, [granted permissions to access GCS buckets](gcp-service-connector.md#gcs-bucket) in the target project and a service account key JSON was generated and saved locally in the `connectors-devel@zenml-core.json` file:

```sh
zenml service-connector register gcp-service-account --type gcp --auth-method service-account --resource-type gcs-bucket --project_id=zenml-core --service_account_json=@connectors-devel@zenml-core.json
```

{% code title="Example Command Output" %}
```
Expanding argument value service_account_json to contents of file connectors-devel@zenml-core.json.
Successfully registered service connector `gcp-service-account` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃     RESOURCE TYPE     │ RESOURCE NAMES                                  ┃
┠───────────────────────┼─────────────────────────────────────────────────┨
┃     📦 gcs-bucket     │ gs://zenml-bucket-sl                            ┃
┃                       │ gs://zenml-core.appspot.com                     ┃
┃                       │ gs://zenml-core_cloudbuild                      ┃
┃                       │ gs://zenml-datasets                             ┃
┃                       │ gs://zenml-internal-artifact-store              ┃
┃                       │ gs://zenml-kubeflow-artifact-store              ┃
┃                       │ gs://zenml-project-time-series-bucket           ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

The GCP service connector configuration and service account credentials:

```sh
zenml service-connector describe gcp-service-account
```

{% code title="Example Command Output" %}
```
Service connector 'gcp-service-account' of type 'gcp' with id '4b3d41c9-6a6f-46da-b7ba-8f374c3f49c5' is owned by user 'default' and is 'private'.
    'gcp-service-account' gcp Service Connector Details    
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                ┃
┠──────────────────┼──────────────────────────────────────┨
┃ ID               │ 4b3d41c9-6a6f-46da-b7ba-8f374c3f49c5 ┃
┠──────────────────┼──────────────────────────────────────┨
┃ NAME             │ gcp-service-account                  ┃
┠──────────────────┼──────────────────────────────────────┨
┃ TYPE             │ 🔵 gcp                               ┃
┠──────────────────┼──────────────────────────────────────┨
┃ AUTH METHOD      │ service-account                      ┃
┠──────────────────┼──────────────────────────────────────┨
┃ RESOURCE TYPES   │ 📦 gcs-bucket                        ┃
┠──────────────────┼──────────────────────────────────────┨
┃ RESOURCE NAME    │ <multiple>                           ┃
┠──────────────────┼──────────────────────────────────────┨
┃ SECRET ID        │ 0d0a42bb-40a4-4f43-af9e-6342eeca3f28 ┃
┠──────────────────┼──────────────────────────────────────┨
┃ SESSION DURATION │ N/A                                  ┃
┠──────────────────┼──────────────────────────────────────┨
┃ EXPIRES IN       │ N/A                                  ┃
┠──────────────────┼──────────────────────────────────────┨
┃ OWNER            │ default                              ┃
┠──────────────────┼──────────────────────────────────────┨
┃ SHARED           │ ➖                                   ┃
┠──────────────────┼──────────────────────────────────────┨
┃ CREATED_AT       │ 2023-05-19 08:15:48.056937           ┃
┠──────────────────┼──────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-05-19 08:15:48.056940           ┃
┗━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
            Configuration            
┏━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━┓
┃ PROPERTY             │ VALUE      ┃
┠──────────────────────┼────────────┨
┃ project_id           │ zenml-core ┃
┠──────────────────────┼────────────┨
┃ service_account_json │ [HIDDEN]   ┃
┗━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━┛
```
{% endcode %}

</details>

### GCP Service Account impersonation

Generates [temporary STS credentials](best-security-practices.md#impersonating-accounts-and-assuming-roles) by [impersonating another GCP service account](https://cloud.google.com/iam/docs/create-short-lived-credentials-direct#sa-impersonation).

The connector needs to be configured with the email address of the target GCP service account to be impersonated, accompanied by a GCP service account key JSON for the primary service account. The primary service account must have permission to generate tokens for the target service account (i.e. [the Service Account Token Creator role](https://cloud.google.com/iam/docs/service-account-permissions#directly-impersonate)). The connector will generate temporary OAuth 2.0 tokens upon request by using [GCP direct service account impersonation](https://cloud.google.com/iam/docs/create-short-lived-credentials-direct#sa-impersonation). The tokens have a configurable limited lifetime of up to 1 hour.

[The best practice implemented with this authentication scheme](best-security-practices.md#impersonating-accounts-and-assuming-roles) is to keep the set of permissions associated with the primary service account down to the bare minimum and grant permissions to the privilege-bearing service account instead.

A GCP project is required and the connector may only be used to access GCP resources in the specified project.

If you already have the `GOOGLE_APPLICATION_CREDENTIALS` environment variable configured to point to the primary service account key JSON file, it will be automatically picked up when auto-configuration is used.

<details>

<summary>Configuration example</summary>

For this example, we have the following set up in GCP:

* a primary `empty-connectors@zenml-core.iam.gserviceaccount.com` GCP service account with no permissions whatsoever aside from the "Service Account Token Creator" role that allows it to impersonate the secondary service account below. We also generate a service account key for this account.
* a secondary `zenml-bucket-sl@zenml-core.iam.gserviceaccount.com` GCP service account that only has permission to access the `zenml-bucket-sl` GCS bucket

First, let's show that the `empty-connectors` service account has no permission to access any GCS buckets or any other resources for that matter. We'll register a regular GCP Service Connector that uses the service account key (long-lived credentials) directly:

```sh
zenml service-connector register gcp-empty-sa --type gcp --auth-method service-account --service_account_json=@empty-connectors@zenml-core.json  --project_id=zenml-core
```

{% code title="Example Command Output" %}
```
Expanding argument value service_account_json to contents of file /home/stefan/aspyre/src/zenml/empty-connectors@zenml-core.json.
Successfully registered service connector `gcp-empty-sa` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃     RESOURCE TYPE     │ RESOURCE NAMES                                                                                                            ┃
┠───────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃    🔵 gcp-generic     │ zenml-core                                                                                                                ┃
┠───────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃     📦 gcs-bucket     │ 💥 error: connector authorization failure: failed to list GCS buckets: 403 GET                                            ┃
┃                       │ https://storage.googleapis.com/storage/v1/b?project=zenml-core&projection=noAcl&prettyPrint=false:                        ┃
┃                       │ empty-connectors@zenml-core.iam.gserviceaccount.com does not have storage.buckets.list access to the Google Cloud         ┃
┃                       │ project. Permission 'storage.buckets.list' denied on resource (or it may not exist).                                      ┃
┠───────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ 🌀 kubernetes-cluster │ 💥 error: connector authorization failure: Failed to list GKE clusters: 403 Required "container.clusters.list"            ┃
┃                       │ permission(s) for "projects/20219041791". [request_id: "0x84808facdac08541"                                               ┃
┃                       │ ]                                                                                                                         ┃
┠───────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ 🐳 docker-registry    │ gcr.io/zenml-core                                                                                                         ┃
┃                       │ us.gcr.io/zenml-core                                                                                                      ┃
┃                       │ eu.gcr.io/zenml-core                                                                                                      ┃
┃                       │ asia.gcr.io/zenml-core                                                                                                    ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

Verifying access to individual resource types will fail:

```sh
zenml service-connector verify gcp-empty-sa --resource-type kubernetes-cluster
```

{% code title="Example Command Output" %}
```
Error: Service connector 'gcp-empty-sa' verification failed: connector authorization failure: Failed to list GKE clusters:
403 Required "container.clusters.list" permission(s) for "projects/20219041791".
```
{% endcode %}

```sh
zenml service-connector verify gcp-empty-sa --resource-type gcs-bucket
```

{% code title="Example Command Output" %}
```
Error: Service connector 'gcp-empty-sa' verification failed: connector authorization failure: failed to list GCS buckets:
403 GET https://storage.googleapis.com/storage/v1/b?project=zenml-core&projection=noAcl&prettyPrint=false:
empty-connectors@zenml-core.iam.gserviceaccount.com does not have storage.buckets.list access to the Google Cloud project.
Permission 'storage.buckets.list' denied on resource (or it may not exist).
```
{% endcode %}

```sh
zenml service-connector verify gcp-empty-sa --resource-type gcs-bucket --resource-id zenml-bucket-sl
```

{% code title="Example Command Output" %}
```
Error: Service connector 'gcp-empty-sa' verification failed: connector authorization failure: failed to fetch GCS bucket
zenml-bucket-sl: 403 GET https://storage.googleapis.com/storage/v1/b/zenml-bucket-sl?projection=noAcl&prettyPrint=false:
empty-connectors@zenml-core.iam.gserviceaccount.com does not have storage.buckets.get access to the Google Cloud Storage bucket.
Permission 'storage.buckets.get' denied on resource (or it may not exist).
```
{% endcode %}

Next, we'll register a GCP Service Connector that actually uses account impersonation to access the `zenml-bucket-sl` GCS bucket and verify that it can actually access the bucket:

```sh
zenml service-connector register gcp-impersonate-sa --type gcp --auth-method impersonation --service_account_json=@empty-connectors@zenml-core.json  --project_id=zenml-core --target_principal=zenml-bucket-sl@zenml-core.iam.gserviceaccount.com --resource-type gcs-bucket --resource-id gs://zenml-bucket-sl
```

{% code title="Example Command Output" %}
```
Expanding argument value service_account_json to contents of file /home/stefan/aspyre/src/zenml/empty-connectors@zenml-core.json.
Successfully registered service connector `gcp-impersonate-sa` with access to the following resources:
┏━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┓
┃ RESOURCE TYPE │ RESOURCE NAMES       ┃
┠───────────────┼──────────────────────┨
┃ 📦 gcs-bucket │ gs://zenml-bucket-sl ┃
┗━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

</details>

### External Account (GCP Workload Identity)

Use [GCP workload identity federation](https://cloud.google.com/iam/docs/workload-identity-federation) to authenticate to GCP services using AWS IAM credentials, Azure Active Directory credentials or generic OIDC tokens.

This authentication method only requires a GCP workload identity external account JSON file that only contains the configuration for the external account without any sensitive credentials. It allows implementing [a two layer authentication scheme](best-security-practices.md#impersonating-accounts-and-assuming-roles) that keeps the set of permissions associated with implicit credentials down to the bare minimum and grants permissions to the privilege-bearing GCP service account instead.

This authentication method can be used to authenticate to GCP services using credentials from other cloud providers or identity providers. When used with workloads running on AWS or Azure, it involves automatically picking up credentials from the AWS IAM or Azure AD identity associated with the workload and using them to authenticate to GCP services. This means that the result depends on the environment where the ZenML server is deployed and is thus not fully reproducible.

{% hint style="warning" %}
When used with AWS or Azure implicit in-cloud authentication, this method may constitute a security risk, because it can give users access to the identity (e.g. AWS IAM role or Azure AD principal) implicitly associated with the environment where the ZenML server is running. For this reason, all implicit authentication methods are disabled by default and need to be explicitly enabled by setting the `ZENML_ENABLE_IMPLICIT_AUTH_METHODS` environment variable or the helm chart `enableImplicitAuthMethods` configuration option to `true` in the ZenML deployment.
{% endhint %}

By default, the GCP connector generates temporary OAuth 2.0 tokens from the external account credentials and distributes them to clients. The tokens have a limited lifetime of 1 hour. This behavior can be disabled by setting the `generate_temporary_tokens` configuration option to `False`, in which case, the connector will distribute the external account credentials JSON to clients instead (not recommended).

A GCP project is required and the connector may only be used to access GCP resources in the specified roject. This project must be the same as the one for which the external account was configured.

If you already have the GOOGLE\_APPLICATION\_CREDENTIALS environment variable configured to point to an external account key JSON file, it will be automatically picked up when auto-configuration is used.

<details>

<summary>Example configuration</summary>

The following assumes the following prerequisites are met, as covered in [the GCP documentation on how to configure workload identity federation with AWS](https://cloud.google.com/iam/docs/workload-identity-federation-with-other-clouds):

* the ZenML server is deployed in AWS in an EKS cluster (or any other AWS compute environment)
* the ZenML server EKS pods are associated with an AWS IAM role by means of an IAM OIDC provider, as covered in the [AWS documentation on how to associate a IAM role with a service account](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html). Alternatively, [the IAM role associated with the EKS/EC2 nodes](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html) can be used instead. This AWS IAM role provides the implicit AWS IAM identity and credentials that will be used to authenticate to GCP services.
* a GCP workload identity pool and AWS provider are configured for the GCP project where the target resources are located, as covered in [the GCP documentation on how to configure workload identity federation with AWS](https://cloud.google.com/iam/docs/workload-identity-federation-with-other-clouds).
* a GCP service account is configured with permissions to access the target resources and granted the `roles/iam.workloadIdentityUser` role for the workload identity pool and AWS provider
* a GCP external account JSON file is generated for the GCP service account. This is used to configure the GCP connector.

```sh
zenml service-connector register gcp-workload-identity --type gcp \
    --auth-method external-account --project_id=zenml-core \
    --external_account_json=@clientLibraryConfig-aws-zenml.json
```

{% code title="Example Command Output" %}
```
Successfully registered service connector `gcp-workload-identity` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃     RESOURCE TYPE     │ RESOURCE NAMES                                  ┃
┠───────────────────────┼─────────────────────────────────────────────────┨
┃    🔵 gcp-generic     │ zenml-core                                      ┃
┠───────────────────────┼─────────────────────────────────────────────────┨
┃     📦 gcs-bucket     │ gs://zenml-bucket-sl                            ┃
┃                       │ gs://zenml-core.appspot.com                     ┃
┃                       │ gs://zenml-core_cloudbuild                      ┃
┃                       │ gs://zenml-datasets                             ┃
┃                       │ gs://zenml-internal-artifact-store              ┃
┃                       │ gs://zenml-kubeflow-artifact-store              ┃
┃                       │ gs://zenml-project-time-series-bucket           ┃
┠───────────────────────┼─────────────────────────────────────────────────┨
┃ 🌀 kubernetes-cluster │ zenml-test-cluster                              ┃
┠───────────────────────┼─────────────────────────────────────────────────┨
┃ 🐳 docker-registry    │ gcr.io/zenml-core                               ┃
┃                       │ us.gcr.io/zenml-core                            ┃
┃                       │ eu.gcr.io/zenml-core                            ┃
┃                       │ asia.gcr.io/zenml-core                          ┃
┃                       │ asia-docker.pkg.dev/zenml-core/asia.gcr.io      ┃
┃                       │ europe-docker.pkg.dev/zenml-core/eu.gcr.io      ┃
┃                       │ europe-west1-docker.pkg.dev/zenml-core/test     ┃
┃                       │ us-docker.pkg.dev/zenml-core/gcr.io             ┃
┃                       │ us-docker.pkg.dev/zenml-core/us.gcr.io          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

No sensitive credentials are stored with the Service Connector, just meta-information about the external provider and the external account:

```sh
zenml service-connector describe gcp-workload-identity -x
```

{% code title="Example Command Output" %}
```
Service connector 'gcp-workload-identity' of type 'gcp' with id '37b6000e-3f7f-483e-b2c5-7a5db44fe66b' is
owned by user 'default'.
                        'gcp-workload-identity' gcp Service Connector Details                        
┏━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY               │ VALUE                                                                    ┃
┠────────────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ ID                     │ 37b6000e-3f7f-483e-b2c5-7a5db44fe66b                                     ┃
┠────────────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ NAME                   │ gcp-workload-identity                                                    ┃
┠────────────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ TYPE                   │ 🔵 gcp                                                                   ┃
┠────────────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ AUTH METHOD            │ external-account                                                         ┃
┠────────────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE TYPES         │ 🔵 gcp-generic, 📦 gcs-bucket, 🌀 kubernetes-cluster, 🐳 docker-registry ┃
┠────────────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE NAME          │ <multiple>                                                               ┃
┠────────────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ SECRET ID              │ 1ff6557f-7f60-4e63-b73d-650e64f015b5                                     ┃
┠────────────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ SESSION DURATION       │ N/A                                                                      ┃
┠────────────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ EXPIRES IN             │ N/A                                                                      ┃
┠────────────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ EXPIRES_SKEW_TOLERANCE │ N/A                                                                      ┃
┠────────────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ OWNER                  │ default                                                                  ┃
┠────────────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ CREATED_AT             │ 2024-01-30 20:44:14.020514                                               ┃
┠────────────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ UPDATED_AT             │ 2024-01-30 20:44:14.020516                                               ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                              Configuration                                              
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY              │ VALUE                                                                         ┃
┠───────────────────────┼───────────────────────────────────────────────────────────────────────────────┨
┃ project_id            │ zenml-core                                                                    ┃
┠───────────────────────┼───────────────────────────────────────────────────────────────────────────────┨
┃ external_account_json │ {                                                                             ┃
┃                       │   "type": "external_account",                                                 ┃
┃                       │   "audience":                                                                 ┃
┃                       │ "//iam.googleapis.com/projects/30267569827/locations/global/workloadIdentityP ┃
┃                       │ ools/mypool/providers/myprovider",                                            ┃
┃                       │   "subject_token_type": "urn:ietf:params:aws:token-type:aws4_request",        ┃
┃                       │   "service_account_impersonation_url":                                        ┃
┃                       │ "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/myrole@  ┃
┃                       │ zenml-core.iam.gserviceaccount.com:generateAccessToken",                      ┃
┃                       │   "token_url": "https://sts.googleapis.com/v1/token",                         ┃
┃                       │   "credential_source": {                                                      ┃
┃                       │     "environment_id": "aws1",                                                 ┃
┃                       │     "region_url":                                                             ┃
┃                       │ "http://169.254.169.254/latest/meta-data/placement/availability-zone",        ┃
┃                       │     "url":                                                                    ┃
┃                       │ "http://169.254.169.254/latest/meta-data/iam/security-credentials",           ┃
┃                       │     "regional_cred_verification_url":                                         ┃
┃                       │ "https://sts.{region}.amazonaws.com?Action=GetCallerIdentity&Version=2011-06- ┃
┃                       │ 15"                                                                           ┃
┃                       │   }                                                                           ┃
┃                       │ }                                                                             ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

</details>

### GCP OAuth 2.0 token

Uses [temporary OAuth 2.0 tokens](best-security-practices.md#short-lived-credentials) explicitly configured by the user.

This method has the major limitation that the user must regularly generate new tokens and update the connector configuration as OAuth 2.0 tokens expire. On the other hand, this method is ideal in cases where the connector only needs to be used for a short period of time, such as sharing access temporarily with someone else in your team.

Using any of the other authentication methods will automatically generate and refresh OAuth 2.0 tokens for clients upon request.

A GCP project is required and the connector may only be used to access GCP resources in the specified project.

<details>

<summary>Example auto-configuration</summary>

Fetching OAuth 2.0 tokens from the local GCP CLI is possible if the GCP CLI is already configured with valid credentials (i.e. by running `gcloud auth application-default login`). We need to force the ZenML CLI to use the OAuth 2.0 token authentication by passing the `--auth-method oauth2-token` option, otherwise, it would automatically pick up long-term credentials:

```sh
zenml service-connector register gcp-oauth2-token --type gcp --auto-configure --auth-method oauth2-token
```

{% code title="Example Command Output" %}
```
Successfully registered service connector `gcp-oauth2-token` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃     RESOURCE TYPE     │ RESOURCE NAMES                                  ┃
┠───────────────────────┼─────────────────────────────────────────────────┨
┃    🔵 gcp-generic     │ zenml-core                                      ┃
┠───────────────────────┼─────────────────────────────────────────────────┨
┃     📦 gcs-bucket     │ gs://zenml-bucket-sl                            ┃
┃                       │ gs://zenml-core.appspot.com                     ┃
┃                       │ gs://zenml-core_cloudbuild                      ┃
┃                       │ gs://zenml-datasets                             ┃
┃                       │ gs://zenml-internal-artifact-store              ┃
┃                       │ gs://zenml-kubeflow-artifact-store              ┃
┃                       │ gs://zenml-project-time-series-bucket           ┃
┠───────────────────────┼─────────────────────────────────────────────────┨
┃ 🌀 kubernetes-cluster │ zenml-test-cluster                              ┃
┠───────────────────────┼─────────────────────────────────────────────────┨
┃ 🐳 docker-registry    │ gcr.io/zenml-core                               ┃
┃                       │ us.gcr.io/zenml-core                            ┃
┃                       │ eu.gcr.io/zenml-core                            ┃
┃                       │ asia.gcr.io/zenml-core                          ┃
┃                       │ asia-docker.pkg.dev/zenml-core/asia.gcr.io      ┃
┃                       │ europe-docker.pkg.dev/zenml-core/eu.gcr.io      ┃
┃                       │ europe-west1-docker.pkg.dev/zenml-core/test     ┃
┃                       │ us-docker.pkg.dev/zenml-core/gcr.io             ┃
┃                       │ us-docker.pkg.dev/zenml-core/us.gcr.io          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

```sh
zenml service-connector describe gcp-oauth2-token
```

{% code title="Example Command Output" %}
```
Service connector 'gcp-oauth2-token' of type 'gcp' with id 'ec4d7d85-c71c-476b-aa76-95bf772c90da' is owned by user 'default' and is 'private'.
                       'gcp-oauth2-token' gcp Service Connector Details                        
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                                    ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ ID               │ ec4d7d85-c71c-476b-aa76-95bf772c90da                                     ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ NAME             │ gcp-oauth2-token                                                         ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ TYPE             │ 🔵 gcp                                                                   ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ AUTH METHOD      │ oauth2-token                                                             ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE TYPES   │ 🔵 gcp-generic, 📦 gcs-bucket, 🌀 kubernetes-cluster, 🐳 docker-registry ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE NAME    │ <multiple>                                                               ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ SECRET ID        │ 4694de65-997b-4929-8831-b49d5e067b97                                     ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ SESSION DURATION │ N/A                                                                      ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ EXPIRES IN       │ 59m46s                                                                   ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ OWNER            │ default                                                                  ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ SHARED           │ ➖                                                                       ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ CREATED_AT       │ 2023-05-19 09:04:33.557126                                               ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-05-19 09:04:33.557127                                               ┃
┗━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
       Configuration       
┏━━━━━━━━━━━━┯━━━━━━━━━━━━┓
┃ PROPERTY   │ VALUE      ┃
┠────────────┼────────────┨
┃ project_id │ zenml-core ┃
┠────────────┼────────────┨
┃ token      │ [HIDDEN]   ┃
┗━━━━━━━━━━━━┷━━━━━━━━━━━━┛
```
{% endcode %}

Note the temporary nature of the Service Connector. It will expire and become unusable in 1 hour:

```sh
zenml service-connector list --name gcp-oauth2-token
```

{% code title="Example Command Output" %}
```
┏━━━━━━━━┯━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━┓
┃ ACTIVE │ NAME             │ ID                                   │ TYPE   │ RESOURCE TYPES        │ RESOURCE NAME │ SHARED │ OWNER   │ EXPIRES IN │ LABELS ┃
┠────────┼──────────────────┼──────────────────────────────────────┼────────┼───────────────────────┼───────────────┼────────┼─────────┼────────────┼────────┨
┃        │ gcp-oauth2-token │ ec4d7d85-c71c-476b-aa76-95bf772c90da │ 🔵 gcp │ 🔵 gcp-generic        │ <multiple>    │ ➖     │ default │ 59m35s     │        ┃
┃        │                  │                                      │        │ 📦 gcs-bucket         │               │        │         │            │        ┃
┃        │                  │                                      │        │ 🌀 kubernetes-cluster │               │        │         │            │        ┃
┃        │                  │                                      │        │ 🐳 docker-registry    │               │        │         │            │        ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━┛
```
{% endcode %}

</details>

## Auto-configuration

The GCP Service Connector allows [auto-discovering and fetching credentials](service-connectors-guide.md#auto-configuration) and configuration [set up by the GCP CLI](https://cloud.google.com/sdk/gcloud) on your local host.

<details>

<summary>Auto-configuration example</summary>

The following is an example of lifting GCP user credentials granting access to the same set of GCP resources and services that the local GCP CLI is allowed to access. The GCP CLI should already be configured with valid credentials (i.e. by running `gcloud auth application-default login`). In this case, the [GCP user account authentication method](gcp-service-connector.md#gcp-user-account) is automatically detected:

```sh
zenml service-connector register gcp-auto --type gcp --auto-configure
```

{% code title="Example Command Output" %}
```
Successfully registered service connector `gcp-auto` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃     RESOURCE TYPE     │ RESOURCE NAMES                                  ┃
┠───────────────────────┼─────────────────────────────────────────────────┨
┃    🔵 gcp-generic     │ zenml-core                                      ┃
┠───────────────────────┼─────────────────────────────────────────────────┨
┃     📦 gcs-bucket     │ gs://zenml-bucket-sl                            ┃
┃                       │ gs://zenml-core.appspot.com                     ┃
┃                       │ gs://zenml-core_cloudbuild                      ┃
┃                       │ gs://zenml-datasets                             ┃
┃                       │ gs://zenml-internal-artifact-store              ┃
┃                       │ gs://zenml-kubeflow-artifact-store              ┃
┃                       │ gs://zenml-project-time-series-bucket           ┃
┠───────────────────────┼─────────────────────────────────────────────────┨
┃ 🌀 kubernetes-cluster │ zenml-test-cluster                              ┃
┠───────────────────────┼─────────────────────────────────────────────────┨
┃ 🐳 docker-registry    │ gcr.io/zenml-core                               ┃
┃                       │ us.gcr.io/zenml-core                            ┃
┃                       │ eu.gcr.io/zenml-core                            ┃
┃                       │ asia.gcr.io/zenml-core                          ┃
┃                       │ asia-docker.pkg.dev/zenml-core/asia.gcr.io      ┃
┃                       │ europe-docker.pkg.dev/zenml-core/eu.gcr.io      ┃
┃                       │ europe-west1-docker.pkg.dev/zenml-core/test     ┃
┃                       │ us-docker.pkg.dev/zenml-core/gcr.io             ┃
┃                       │ us-docker.pkg.dev/zenml-core/us.gcr.io          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

```sh
zenml service-connector describe gcp-auto
```

{% code title="Example Command Output" %}
```
Service connector 'gcp-auto' of type 'gcp' with id 'fe16f141-7406-437e-a579-acebe618a293' is owned by user 'default' and is 'private'.
                           'gcp-auto' gcp Service Connector Details                            
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                                    ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ ID               │ fe16f141-7406-437e-a579-acebe618a293                                     ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ NAME             │ gcp-auto                                                                 ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ TYPE             │ 🔵 gcp                                                                   ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ AUTH METHOD      │ user-account                                                             ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE TYPES   │ 🔵 gcp-generic, 📦 gcs-bucket, 🌀 kubernetes-cluster, 🐳 docker-registry ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE NAME    │ <multiple>                                                               ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ SECRET ID        │ 5eca8f6e-291f-4958-ae2d-a3e847a1ad8a                                     ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ SESSION DURATION │ N/A                                                                      ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ EXPIRES IN       │ N/A                                                                      ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ OWNER            │ default                                                                  ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ SHARED           │ ➖                                                                       ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ CREATED_AT       │ 2023-05-19 09:15:12.882929                                               ┃
┠──────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-05-19 09:15:12.882930                                               ┃
┗━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
          Configuration           
┏━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━┓
┃ PROPERTY          │ VALUE      ┃
┠───────────────────┼────────────┨
┃ project_id        │ zenml-core ┃
┠───────────────────┼────────────┨
┃ user_account_json │ [HIDDEN]   ┃
┗━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━┛
```
{% endcode %}

</details>

## Local client provisioning

The local `gcloud` CLI, the Kubernetes `kubectl` CLI and the Docker CLI can be[ configured with credentials extracted from or generated by a compatible GCP Service Connector](service-connectors-guide.md#configure-local-clients). Please note that unlike the configuration made possible through the GCP CLI, the Kubernetes and Docker credentials issued by the GCP Service Connector have a short lifetime and will need to be regularly refreshed. This is a byproduct of implementing a high-security profile.

{% hint style="info" %}
Note that the `gcloud` local client can only be configured with credentials issued by the GCP Service Connector if the connector is configured with the [GCP user account authentication method](gcp-service-connector.md#gcp-user-account) or the [GCP service account authentication method](gcp-service-connector.md#gcp-service-account) and if the `generate_temporary_tokens` option is set to true in the Service Connector configuration.

Only the `gcloud` local [application default credentials](https://cloud.google.com/docs/authentication/application-default-credentials) configuration will be updated by the GCP Service Connector configuration. This makes it possible to use libraries and SDKs that use the application default credentials to access GCP resources.
{% endhint %}

<details>

<summary>Local CLI configuration examples</summary>

The following shows an example of configuring the local Kubernetes CLI to access a GKE cluster reachable through a GCP Service Connector:

```sh
zenml service-connector list --name gcp-user-account
```

{% code title="Example Command Output" %}
```
┏━━━━━━━━┯━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━┓
┃ ACTIVE │ NAME             │ ID                                   │ TYPE   │ RESOURCE TYPES        │ RESOURCE NAME │ SHARED │ OWNER   │ EXPIRES IN │ LABELS ┃
┠────────┼──────────────────┼──────────────────────────────────────┼────────┼───────────────────────┼───────────────┼────────┼─────────┼────────────┼────────┨
┃        │ gcp-user-account │ ddbce93f-df14-4861-a8a4-99a80972f3bc │ 🔵 gcp │ 🔵 gcp-generic        │ <multiple>    │ ➖     │ default │            │        ┃
┃        │                  │                                      │        │ 📦 gcs-bucket         │               │        │         │            │        ┃
┃        │                  │                                      │        │ 🌀 kubernetes-cluster │               │        │         │            │        ┃
┃        │                  │                                      │        │ 🐳 docker-registry    │               │        │         │            │        ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━┛
```
{% endcode %}

The following lists all Kubernetes clusters accessible through the GCP Service Connector:

```sh
zenml service-connector verify gcp-user-account --resource-type kubernetes-cluster
```

{% code title="Example Command Output" %}
```
Service connector 'gcp-user-account' is correctly configured with valid credentials and has access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┓
┃     RESOURCE TYPE     │ RESOURCE NAMES     ┃
┠───────────────────────┼────────────────────┨
┃ 🌀 kubernetes-cluster │ zenml-test-cluster ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

Calling the login CLI command will configure the local Kubernetes `kubectl` CLI to access the Kubernetes cluster through the GCP Service Connector:

```sh
zenml service-connector login gcp-user-account --resource-type kubernetes-cluster --resource-id zenml-test-cluster
```

{% code title="Example Command Output" %}
```
⠴ Attempting to configure local client using service connector 'gcp-user-account'...
Context "gke_zenml-core_zenml-test-cluster" modified.
Updated local kubeconfig with the cluster details. The current kubectl context was set to 'gke_zenml-core_zenml-test-cluster'.
The 'gcp-user-account' Kubernetes Service Connector connector was used to successfully configure the local Kubernetes cluster client/SDK.
```
{% endcode %}

To verify that the local Kubernetes `kubectl` CLI is correctly configured, the following command can be used:

```sh
kubectl cluster-info
```

{% code title="Example Command Output" %}
```
Kubernetes control plane is running at https://35.185.95.223
GLBCDefaultBackend is running at https://35.185.95.223/api/v1/namespaces/kube-system/services/default-http-backend:http/proxy
KubeDNS is running at https://35.185.95.223/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy
Metrics-server is running at https://35.185.95.223/api/v1/namespaces/kube-system/services/https:metrics-server:/proxy
```
{% endcode %}

A similar process is possible with GCR container registries:

```sh
zenml service-connector verify gcp-user-account --resource-type docker-registry --resource-id europe-west1-docker.pkg.dev/zenml-core/test
```

{% code title="Example Command Output" %}
```
Service connector 'gcp-user-account' is correctly configured with valid credentials and has access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃   RESOURCE TYPE    │ RESOURCE NAMES                              ┃
┠────────────────────┼─────────────────────────────────────────────┨
┃ 🐳 docker-registry │ europe-west1-docker.pkg.dev/zenml-core/test ┃
┗━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

```sh
zenml service-connector login gcp-user-account --resource-type docker-registry --resource-id europe-west1-docker.pkg.dev/zenml-core/test
```

{% code title="Example Command Output" %}
```
⠦ Attempting to configure local client using service connector 'gcp-user-account'...
WARNING! Your password will be stored unencrypted in /home/stefan/.docker/config.json.
Configure a credential helper to remove this warning. See
https://docs.docker.com/engine/reference/commandline/login/#credentials-store

The 'gcp-user-account' Docker Service Connector connector was used to successfully configure the local Docker/OCI container registry client/SDK.
```
{% endcode %}

To verify that the local Docker container registry client is correctly configured, the following command can be used:

```sh
docker push europe-west1-docker.pkg.dev/zenml-core/test/zenml
```

{% code title="Example Command Output" %}
```
The push refers to repository [europe-west1-docker.pkg.dev/zenml-core/test/zenml]
d4aef4f5ed86: Pushed 
2d69a4ce1784: Pushed 
204066eca765: Pushed 
2da74ab7b0c1: Pushed 
75c35abda1d1: Layer already exists 
415ff8f0f676: Layer already exists 
c14cb5b1ec91: Layer already exists 
a1d005f5264e: Layer already exists 
3a3fd880aca3: Layer already exists 
149a9c50e18e: Layer already exists 
1f6d3424b922: Layer already exists 
8402c959ae6f: Layer already exists 
419599cb5288: Layer already exists 
8553b91047da: Layer already exists 
connectors: digest: sha256:a4cfb18a5cef5b2201759a42dd9fe8eb2f833b788e9d8a6ebde194765b42fe46 size: 3256
```
{% endcode %}

It is also possible to update the local `gcloud` CLI configuration with credentials extracted from the GCP Service Connector:

```sh
zenml service-connector login gcp-user-account --resource-type gcp-generic
```

{% code title="Example Command Output" %}
```
Updated the local gcloud default application credentials file at '/home/user/.config/gcloud/application_default_credentials.json'
The 'gcp-user-account' GCP Service Connector connector was used to successfully configure the local Generic GCP resource client/SDK.
```
{% endcode %}

</details>

## Stack Components use

The[ GCS Artifact Store Stack Component](https://docs.zenml.io/stacks/artifact-stores/gcp) can be connected to a remote GCS bucket through a GCP Service Connector.

The [Google Cloud Image Builder Stack Component](https://docs.zenml.io/stacks/image-builders/gcp), [VertexAI Orchestrator](https://docs.zenml.io/stacks/orchestrators/vertex), and [VertexAI Step Operator](https://docs.zenml.io/stacks/step-operators/vertex) can be connected and use the resources of a target GCP project through a GCP Service Connector.

The GCP Service Connector can also be used with any Orchestrator or Model Deployer stack component flavor that relies on Kubernetes clusters to manage workloads. This allows GKE Kubernetes container workloads to be managed without the need to configure and maintain explicit GCP or Kubernetes `kubectl` configuration contexts and credentials in the target environment or in the Stack Component itself.

Similarly, Container Registry Stack Components can be connected to a Google Artifact Registry or GCR Container Registry through a GCP Service Connector. This allows container images to be built and published to GAR or GCR container registries without the need to configure explicit GCP credentials in the target environment or the Stack Component.

## End-to-end examples

<details>

<summary>GKE Kubernetes Orchestrator, GCS Artifact Store and GCR Container Registry with a multi-type GCP Service Connector</summary>

This is an example of an end-to-end workflow involving Service Connectors that use a single multi-type GCP Service Connector to give access to multiple resources for multiple Stack Components. A complete ZenML Stack is registered and composed of the following Stack Components, all connected through the same Service Connector:

* a [Kubernetes Orchestrator](https://docs.zenml.io/stacks/orchestrators/kubernetes) connected to a GKE Kubernetes cluster
* a [GCS Artifact Store](https://docs.zenml.io/stacks/artifact-stores/gcp) connected to a GCS bucket
* a [GCP Container Registry](https://docs.zenml.io/stacks/container-registries/gcp) connected to a Docker Google Artifact Registry
* a local [Image Builder](https://docs.zenml.io/stacks/image-builders/local)

As a last step, a simple pipeline is run on the resulting Stack.

1.  Configure the local GCP CLI with valid user account credentials with a wide range of permissions (i.e. by running `gcloud auth application-default login`) and install ZenML integration prerequisites:

    ```sh
    zenml integration install -y gcp
    ```

    ```sh
    gcloud auth application-default login
    ```

{% code title="Example Command Output" %}
````
```text
Credentials saved to file: [/home/stefan/.config/gcloud/application_default_credentials.json]

These credentials will be used by any library that requests Application Default Credentials (ADC).

Quota project "zenml-core" was added to ADC which can be used by Google client libraries for billing
and quota. Note that some services may still bill the project owning the resource.
```
````
{% endcode %}

2.  Make sure the GCP Service Connector Type is available

    ```sh
    zenml service-connector list-types --type gcp
    ```

{% code title="Example Command Output" %}
````
```text
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
````
{% endcode %}

3.  Register a multi-type GCP Service Connector using auto-configuration

    ```sh
    zenml service-connector register gcp-demo-multi --type gcp --auto-configure
    ```

{% code title="Example Command Output" %}
````
```text
Successfully registered service connector `gcp-demo-multi` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃     RESOURCE TYPE     │ RESOURCE NAMES                                  ┃
┠───────────────────────┼─────────────────────────────────────────────────┨
┃    🔵 gcp-generic     │ zenml-core                                      ┃
┠───────────────────────┼─────────────────────────────────────────────────┨
┃     📦 gcs-bucket     │ gs://zenml-bucket-sl                            ┃
┃                       │ gs://zenml-core.appspot.com                     ┃
┃                       │ gs://zenml-core_cloudbuild                      ┃
┃                       │ gs://zenml-datasets                             ┃
┠───────────────────────┼─────────────────────────────────────────────────┨
┃ 🌀 kubernetes-cluster │ zenml-test-cluster                              ┃
┠───────────────────────┼─────────────────────────────────────────────────┨
┃ 🐳 docker-registry    │ gcr.io/zenml-core                               ┃
┃                       │ us.gcr.io/zenml-core                            ┃
┃                       │ eu.gcr.io/zenml-core                            ┃
┃                       │ asia.gcr.io/zenml-core                          ┃
┃                       │ asia-docker.pkg.dev/zenml-core/asia.gcr.io      ┃
┃                       │ europe-docker.pkg.dev/zenml-core/eu.gcr.io      ┃
┃                       │ europe-west1-docker.pkg.dev/zenml-core/test     ┃
┃                       │ us-docker.pkg.dev/zenml-core/gcr.io             ┃
┃                       │ us-docker.pkg.dev/zenml-core/us.gcr.io          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
````
{% endcode %}

```
**NOTE**: from this point forward, we don't need the local GCP CLI credentials or the local GCP CLI at all. The steps that follow can be run on any machine regardless of whether it has been configured and authorized to access the GCP project.
```

4\. find out which GCS buckets, GAR registries, and GKE Kubernetes clusters we can gain access to. We'll use this information to configure the Stack Components in our minimal GCP stack: a GCS Artifact Store, a Kubernetes Orchestrator, and a GCP Container Registry.

````
```sh
zenml service-connector list-resources --resource-type gcs-bucket
```

````

{% code title="Example Command Output" %}
````
```text
The following 'gcs-bucket' resources can be accessed by service connectors that you have configured:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE │ RESOURCE NAMES                                  ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────┼─────────────────────────────────────────────────┨
┃ eeeabc13-9203-463b-aa52-216e629e903c │ gcp-demo-multi │ 🔵 gcp         │ 📦 gcs-bucket │ gs://zenml-bucket-sl                            ┃
┃                                      │                │                │               │ gs://zenml-core.appspot.com                     ┃
┃                                      │                │                │               │ gs://zenml-core_cloudbuild                      ┃
┃                                      │                │                │               │ gs://zenml-datasets                             ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
````
{% endcode %}

````
```sh
zenml service-connector list-resources --resource-type kubernetes-cluster
```

````

{% code title="Example Command Output" %}
````
```text
The following 'kubernetes-cluster' resources can be accessed by service connectors that you have configured:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES     ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────────────┼────────────────────┨
┃ eeeabc13-9203-463b-aa52-216e629e903c │ gcp-demo-multi │ 🔵 gcp         │ 🌀 kubernetes-cluster │ zenml-test-cluster ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┛
```
````
{% endcode %}

````
```sh
zenml service-connector list-resources --resource-type docker-registry
```

````

{% code title="Example Command Output" %}
````
```text
The following 'docker-registry' resources can be accessed by service connectors that you have configured:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE      │ RESOURCE NAMES                                  ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼────────────────────┼─────────────────────────────────────────────────┨
┃ eeeabc13-9203-463b-aa52-216e629e903c │ gcp-demo-multi │ 🔵 gcp         │ 🐳 docker-registry │ gcr.io/zenml-core                               ┃
┃                                      │                │                │                    │ us.gcr.io/zenml-core                            ┃
┃                                      │                │                │                    │ eu.gcr.io/zenml-core                            ┃
┃                                      │                │                │                    │ asia.gcr.io/zenml-core                          ┃
┃                                      │                │                │                    │ asia-docker.pkg.dev/zenml-core/asia.gcr.io      ┃
┃                                      │                │                │                    │ europe-docker.pkg.dev/zenml-core/eu.gcr.io      ┃
┃                                      │                │                │                    │ europe-west1-docker.pkg.dev/zenml-core/test     ┃
┃                                      │                │                │                    │ us-docker.pkg.dev/zenml-core/gcr.io             ┃
┃                                      │                │                │                    │ us-docker.pkg.dev/zenml-core/us.gcr.io          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
````
{% endcode %}

5.  register and connect a GCS Artifact Store Stack Component to a GCS bucket:

    ```sh
    zenml artifact-store register gcs-zenml-bucket-sl --flavor gcp --path=gs://zenml-bucket-sl
    ```

{% code title="Example Command Output" %}
````
```text
Running with active stack: 'default' (global)
Successfully registered artifact_store `gcs-zenml-bucket-sl`.
```
````
{% endcode %}

````
```sh
zenml artifact-store connect gcs-zenml-bucket-sl --connector gcp-demo-multi
```

````

{% code title="Example Command Output" %}
````
```text
Running with active stack: 'default' (global)
Successfully connected artifact store `gcs-zenml-bucket-sl` to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE │ RESOURCE NAMES       ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────┼──────────────────────┨
┃ eeeabc13-9203-463b-aa52-216e629e903c │ gcp-demo-multi │ 🔵 gcp         │ 📦 gcs-bucket │ gs://zenml-bucket-sl ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┛
```
````
{% endcode %}

6.  register and connect a Kubernetes Orchestrator Stack Component to a GKE cluster:

    ```sh
    zenml orchestrator register gke-zenml-test-cluster --flavor kubernetes --synchronous=true 
    --kubernetes_namespace=zenml-workloads
    ```

{% code title="Example Command Output" %}
````
```text
Running with active stack: 'default' (global)
Successfully registered orchestrator `gke-zenml-test-cluster`.
```
````
{% endcode %}

````
```sh
zenml orchestrator connect gke-zenml-test-cluster --connector gcp-demo-multi
```

````

{% code title="Example Command Output" %}
````
```text
Running with active stack: 'default' (global)
Successfully connected orchestrator `gke-zenml-test-cluster` to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES     ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────────────┼────────────────────┨
┃ eeeabc13-9203-463b-aa52-216e629e903c │ gcp-demo-multi │ 🔵 gcp         │ 🌀 kubernetes-cluster │ zenml-test-cluster ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┛
```
````
{% endcode %}

7.  Register and connect a GCP Container Registry Stack Component to a GAR registry:

    ```sh
    zenml container-registry register gcr-zenml-core --flavor gcp --uri=europe-west1-docker.pkg.dev/zenml-core/test
    ```

{% code title="Example Command Output" %}
````
```text
Running with active stack: 'default' (global)
Successfully registered container_registry `gcr-zenml-core`.
```
````
{% endcode %}

````
```sh
zenml container-registry connect gcr-zenml-core --connector gcp-demo-multi
```

````

{% code title="Example Command Output" %}
````
```text
Running with active stack: 'default' (global)
Successfully connected container registry `gcr-zenml-core` to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE      │ RESOURCE NAMES                              ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼────────────────────┼─────────────────────────────────────────────┨
┃ eeeabc13-9203-463b-aa52-216e629e903c │ gcp-demo-multi │ 🔵 gcp         │ 🐳 docker-registry │ europe-west1-docker.pkg.dev/zenml-core/test ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
````
{% endcode %}

8.  Combine all Stack Components together into a Stack and set it as active (also throw in a local Image Builder for completion):

    ```sh
    zenml image-builder register local --flavor local
    ```

{% code title="Example Command Output" %}
````
```text
Running with active stack: 'default' (global)
Successfully registered image_builder `local`.
```
````
{% endcode %}

````
```sh
zenml stack register gcp-demo -a gcs-zenml-bucket-sl -o gke-zenml-test-cluster -c gcr-zenml-core -i local --set
```

````

{% code title="Example Command Output" %}
````
```text
Stack 'gcp-demo' successfully registered!
Active global stack set to:'gcp-demo'
```
````
{% endcode %}

9.  Finally, run a simple pipeline to prove that everything works as expected. We'll use the simplest pipelines possible for this example:

    ```python
    from zenml import pipeline, step


    @step
    def step_1() -> str:
        """Returns the `world` string."""
        return "world"


    @step(enable_cache=False)
    def step_2(input_one: str, input_two: str) -> None:
        """Combines the two strings at its input and prints them."""
        combined_str = f"{input_one} {input_two}"
        print(combined_str)


    @pipeline
    def my_pipeline():
        output_step_one = step_1()
        step_2(input_one="hello", input_two=output_step_one)


    if __name__ == "__main__":
        my_pipeline()
    ```

    Saving that to a `run.py` file and running it gives us:

{% code title="Example Command Output" %}
````
```text
$ python run.py 
Building Docker image(s) for pipeline simple_pipeline.
Building Docker image europe-west1-docker.pkg.dev/zenml-core/test/zenml:simple_pipeline-orchestrator.
- Including integration requirements: gcsfs, google-cloud-aiplatform>=1.11.0, google-cloud-build>=3.11.0, google-cloud-container>=2.21.0, google-cloud-functions>=1.8.3, google-cloud-scheduler>=2.7.3, google-cloud-secret-manager, google-cloud-storage>=2.9.0, kfp==1.8.16, kubernetes==18.20.0, shapely<2.0
No .dockerignore found, including all files inside build context.
Step 1/8 : FROM zenmldocker/zenml:0.39.1-py3.8
Step 2/8 : WORKDIR /app
Step 3/8 : COPY .zenml_integration_requirements .
Step 4/8 : RUN pip install --default-timeout=60 --no-cache-dir  -r .zenml_integration_requirements
Step 5/8 : ENV ZENML_ENABLE_REPO_INIT_WARNINGS=False
Step 6/8 : ENV ZENML_CONFIG_PATH=/app/.zenconfig
Step 7/8 : COPY . .
Step 8/8 : RUN chmod -R a+rw .
Pushing Docker image europe-west1-docker.pkg.dev/zenml-core/test/zenml:simple_pipeline-orchestrator.
Finished pushing Docker image.
Finished building Docker image(s).
Running pipeline simple_pipeline on stack gcp-demo (caching disabled)
Waiting for Kubernetes orchestrator pod...
Kubernetes orchestrator pod started.
Waiting for pod of step step_1 to start...
Step step_1 has started.
Step step_1 has finished in 1.357s.
Pod of step step_1 completed.
Waiting for pod of step simple_step_two to start...
Step step_2 has started.
Hello World!
Step step_2 has finished in 3.136s.
Pod of step step_2 completed.
Orchestration pod completed.
Dashboard URL: http://34.148.132.191/default/pipelines/cec118d1-d90a-44ec-8bd7-d978f726b7aa/runs
```
````
{% endcode %}

</details>

<details>

<summary>VertexAI Orchestrator, GCS Artifact Store, Google Artifact Registry and GCP Image Builder with single-instance GCP Service Connectors</summary>

This is an example of an end-to-end workflow involving Service Connectors that use multiple single-instance GCP Service Connectors, each giving access to a resource for a Stack Component. A complete ZenML Stack is registered and composed of the following Stack Components, all connected through its individual Service Connector:

* a [VertexAI Orchestrator](https://docs.zenml.io/stacks/orchestrators/vertex) connected to the GCP project
* a [GCS Artifact Store](https://docs.zenml.io/stacks/artifact-stores/gcp) connected to a GCS bucket
* a [GCP Container Registry](https://docs.zenml.io/stacks/container-registries/gcp) connected to a GCR container registry
* a [Google Cloud Image Builder](https://docs.zenml.io/stacks/image-builders/gcp) connected to the GCP project

As a last step, a simple pipeline is run on the resulting Stack.

1.  Configure the local GCP CLI with valid user account credentials with a wide range of permissions (i.e. by running `gcloud auth application-default login`) and install ZenML integration prerequisites:

    ```sh
    zenml integration install -y gcp
    ```

    ```sh
    gcloud auth application-default login
    ```

{% code title="Example Command Output" %}
````
```text
Credentials saved to file: [/home/stefan/.config/gcloud/application_default_credentials.json]

These credentials will be used by any library that requests Application Default Credentials (ADC).

Quota project "zenml-core" was added to ADC which can be used by Google client libraries for billing
and quota. Note that some services may still bill the project owning the resource.
```
````
{% endcode %}

2.  Make sure the GCP Service Connector Type is available

    ```sh
    zenml service-connector list-types --type gcp
    ```

{% code title="Example Command Output" %}
````
```text
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
````
{% endcode %}

3.  Register an individual single-instance GCP Service Connector using auto-configuration for each of the resources that will be needed for the Stack Components: a GCS bucket, a GCR registry, and generic GCP access for the VertexAI orchestrator and another one for the GCP Cloud Builder:

    ```sh
    zenml service-connector register gcs-zenml-bucket-sl --type gcp --resource-type gcs-bucket --resource-id gs://zenml-bucket-sl --auto-configure
    ```

{% code title="Example Command Output" %}
````
```text
Successfully registered service connector `gcs-zenml-bucket-sl` with access to the following resources:
┏━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┓
┃ RESOURCE TYPE │ RESOURCE NAMES       ┃
┠───────────────┼──────────────────────┨
┃ 📦 gcs-bucket │ gs://zenml-bucket-sl ┃
┗━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┛
```
````
{% endcode %}

````
```sh
zenml service-connector register gcr-zenml-core --type gcp --resource-type docker-registry --auto-configure
```

````

{% code title="Example Command Output" %}
````
```text
Successfully registered service connector `gcr-zenml-core` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃   RESOURCE TYPE       │ RESOURCE NAMES                                  ┃
┠───────────────────────┼─────────────────────────────────────────────────┨
┃ 🐳 docker-registry    │ gcr.io/zenml-core                               ┃
┃                       │ us.gcr.io/zenml-core                            ┃
┃                       │ eu.gcr.io/zenml-core                            ┃
┃                       │ asia.gcr.io/zenml-core                          ┃
┃                       │ asia-docker.pkg.dev/zenml-core/asia.gcr.io      ┃
┃                       │ europe-docker.pkg.dev/zenml-core/eu.gcr.io      ┃
┃                       │ europe-west1-docker.pkg.dev/zenml-core/test     ┃
┃                       │ us-docker.pkg.dev/zenml-core/gcr.io             ┃
┃                       │ us-docker.pkg.dev/zenml-core/us.gcr.io          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
````
{% endcode %}

````
```sh
zenml service-connector register vertex-ai-zenml-core --type gcp --resource-type gcp-generic --auto-configure
```

````

{% code title="Example Command Output" %}
````
```text
Successfully registered service connector `vertex-ai-zenml-core` with access to the following resources:
┏━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃ RESOURCE TYPE  │ RESOURCE NAMES ┃
┠────────────────┼────────────────┨
┃ 🔵 gcp-generic │ zenml-core     ┃
┗━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛
```
````
{% endcode %}

````
```sh
zenml service-connector register gcp-cloud-builder-zenml-core --type gcp --resource-type gcp-generic --auto-configure
```

````

{% code title="Example Command Output" %}
````
```text
Successfully registered service connector `gcp-cloud-builder-zenml-core` with access to the following resources:
┏━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃ RESOURCE TYPE  │ RESOURCE NAMES ┃
┠────────────────┼────────────────┨
┃ 🔵 gcp-generic │ zenml-core     ┃
┗━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛
```
````
{% endcode %}

````
**NOTE**: from this point forward, we don't need the local GCP CLI credentials or the local GCP CLI at all. The steps that follow can be run on any machine regardless of whether it has been configured and authorized to access the GCP project.

In the end, the service connector list should look like this:

```sh
zenml service-connector list
```

````

{% code title="Example Command Output" %}
````
```text
┏━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━┓
┃ ACTIVE │ NAME                         │ ID                                   │ TYPE   │ RESOURCE TYPES     │ RESOURCE NAME        │ SHARED │ OWNER   │ EXPIRES IN │ LABELS ┃
┠────────┼──────────────────────────────┼──────────────────────────────────────┼────────┼────────────────────┼──────────────────────┼────────┼─────────┼────────────┼────────┨
┃        │ gcs-zenml-bucket-sl          │ 405034fe-5e6e-4d29-ba62-8ae025381d98 │ 🔵 gcp │ 📦 gcs-bucket      │ gs://zenml-bucket-sl │ ➖     │ default │            │        ┃
┠────────┼──────────────────────────────┼──────────────────────────────────────┼────────┼────────────────────┼──────────────────────┼────────┼─────────┼────────────┼────────┨
┃        │ gcr-zenml-core               │ 9fddfaba-6d46-4806-ad96-9dcabef74639 │ 🔵 gcp │ 🐳 docker-registry │ gcr.io/zenml-core    │ ➖     │ default │            │        ┃
┠────────┼──────────────────────────────┼──────────────────────────────────────┼────────┼────────────────────┼──────────────────────┼────────┼─────────┼────────────┼────────┨
┃        │ vertex-ai-zenml-core         │ f97671b9-8c73-412b-bf5e-4b7c48596f5f │ 🔵 gcp │ 🔵 gcp-generic     │ zenml-core           │ ➖     │ default │            │        ┃
┠────────┼──────────────────────────────┼──────────────────────────────────────┼────────┼────────────────────┼──────────────────────┼────────┼─────────┼────────────┼────────┨
┃        │ gcp-cloud-builder-zenml-core │ 648c1016-76e4-4498-8de7-808fd20f057b │ 🔵 gcp │ 🔵 gcp-generic     │ zenml-core           │ ➖     │ default │            │        ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━┛
```
````
{% endcode %}

4.  register and connect a GCS Artifact Store Stack Component to the GCS bucket:

    ```sh
    zenml artifact-store register gcs-zenml-bucket-sl --flavor gcp --path=gs://zenml-bucket-sl
    ```

{% code title="Example Command Output" %}
````
```text
Running with active stack: 'default' (global)
Successfully registered artifact_store `gcs-zenml-bucket-sl`.
```
````
{% endcode %}

````
```sh
zenml artifact-store connect gcs-zenml-bucket-sl --connector gcs-zenml-bucket-sl
```

````

{% code title="Example Command Output" %}
````
```text
Running with active stack: 'default' (global)
Successfully connected artifact store `gcs-zenml-bucket-sl` to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME      │ CONNECTOR TYPE │ RESOURCE TYPE │ RESOURCE NAMES       ┃
┠──────────────────────────────────────┼─────────────────────┼────────────────┼───────────────┼──────────────────────┨
┃ 405034fe-5e6e-4d29-ba62-8ae025381d98 │ gcs-zenml-bucket-sl │ 🔵 gcp         │ 📦 gcs-bucket │ gs://zenml-bucket-sl ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┛
```
````
{% endcode %}

5.  register and connect a Google Cloud Image Builder Stack Component to the target GCP project:

    ```sh
    zenml image-builder register gcp-zenml-core --flavor gcp
    ```

{% code title="Example Command Output" %}
````
```text
Running with active stack: 'default' (repository)
Successfully registered image_builder `gcp-zenml-core`.
```
````
{% endcode %}

````
```sh
zenml image-builder connect gcp-zenml-core --connector gcp-cloud-builder-zenml-core 
```

````

{% code title="Example Command Output" %}
````
```text
Running with active stack: 'default' (repository)
Successfully connected image builder `gcp-zenml-core` to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME               │ CONNECTOR TYPE │ RESOURCE TYPE  │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼──────────────────────────────┼────────────────┼────────────────┼────────────────┨
┃ 648c1016-76e4-4498-8de7-808fd20f057b │ gcp-cloud-builder-zenml-core │ 🔵 gcp         │ 🔵 gcp-generic │ zenml-core     ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛
```
````
{% endcode %}

6.  register and connect a Vertex AI Orchestrator Stack Component to the target GCP project

    **NOTE**: If we do not specify a workload service account, the Vertex AI Pipelines Orchestrator uses the Compute Engine default service account in the target project to run pipelines. You must grant this account the Vertex AI Service Agent role, otherwise the pipelines will fail. More information on other configurations possible for the Vertex AI Orchestrator can be found [here](https://docs.zenml.io/stacks/orchestrators/vertex#how-to-use-it).

    ```sh
    zenml orchestrator register vertex-ai-zenml-core --flavor=vertex --location=europe-west1 --synchronous=true
    ```

{% code title="Example Command Output" %}
````
```text
Running with active stack: 'default' (repository)
Successfully registered orchestrator `vertex-ai-zenml-core`.
```
````
{% endcode %}

````
```sh
zenml orchestrator connect vertex-ai-zenml-core --connector vertex-ai-zenml-core
```

````

{% code title="Example Command Output" %}
````
```text
Running with active stack: 'default' (repository)
Successfully connected orchestrator `vertex-ai-zenml-core` to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME       │ CONNECTOR TYPE │ RESOURCE TYPE  │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼──────────────────────┼────────────────┼────────────────┼────────────────┨
┃ f97671b9-8c73-412b-bf5e-4b7c48596f5f │ vertex-ai-zenml-core │ 🔵 gcp         │ 🔵 gcp-generic │ zenml-core     ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛
```
````
{% endcode %}

7.  Register and connect a GCP Container Registry Stack Component to a GCR container registry:

    ```sh
    zenml container-registry register gcr-zenml-core --flavor gcp --uri=gcr.io/zenml-core 
    ```

{% code title="Example Command Output" %}
````
```text
Running with active stack: 'default' (repository)
Successfully registered container_registry `gcr-zenml-core`.
```
````
{% endcode %}

````
```sh
zenml container-registry connect gcr-zenml-core --connector gcr-zenml-core
```

````

{% code title="Example Command Output" %}
````
```text
Running with active stack: 'default' (repository)
Successfully connected container registry `gcr-zenml-core` to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE      │ RESOURCE NAMES    ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼────────────────────┼───────────────────┨
┃ 9fddfaba-6d46-4806-ad96-9dcabef74639 │ gcr-zenml-core │ 🔵 gcp         │ 🐳 docker-registry │ gcr.io/zenml-core ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━┛
```
````
{% endcode %}

8.  Combine all Stack Components together into a Stack and set it as active:

    ```sh
    zenml stack register gcp-demo -a gcs-zenml-bucket-sl -o vertex-ai-zenml-core -c gcr-zenml-core -i gcp-zenml-core --set
    ```

{% code title="Example Command Output" %}
````
```text
Stack 'gcp-demo' successfully registered!
Active repository stack set to:'gcp-demo'
```
````
{% endcode %}

9.  Finally, run a simple pipeline to prove that everything works as expected. We'll use the simplest pipelines possible for this example:

    ```python
    from zenml import pipeline, step


    @step
    def step_1() -> str:
        """Returns the `world` string."""
        return "world"


    @step(enable_cache=False)
    def step_2(input_one: str, input_two: str) -> None:
        """Combines the two strings at its input and prints them."""
        combined_str = f"{input_one} {input_two}"
        print(combined_str)


    @pipeline
    def my_pipeline():
        output_step_one = step_1()
        step_2(input_one="hello", input_two=output_step_one)


    if __name__ == "__main__":
        my_pipeline()
    ```

    Saving that to a `run.py` file and running it gives us:

{% code title="Example Command Output" %}
````
```text
$ python run.py 
Building Docker image(s) for pipeline simple_pipeline.
Building Docker image gcr.io/zenml-core/zenml:simple_pipeline-orchestrator.
- Including integration requirements: gcsfs, google-cloud-aiplatform>=1.11.0, google-cloud-build>=3.11.0, google-cloud-container>=2.21.0, google-cloud-functions>=1.8.3, google-cloud-scheduler>=2.7.3, google-cloud-secret-manager, google-cloud-storage>=2.9.0, kfp==1.8.16, shapely<2.0
Using Cloud Build to build image gcr.io/zenml-core/zenml:simple_pipeline-orchestrator
No .dockerignore found, including all files inside build context.
Uploading build context to gs://zenml-bucket-sl/cloud-build-contexts/5dda6dbb60e036398bee4974cfe3eb768a138b2e.tar.gz.
Build context located in bucket zenml-bucket-sl and object path cloud-build-contexts/5dda6dbb60e036398bee4974cfe3eb768a138b2e.tar.gz
Using Cloud Builder image gcr.io/cloud-builders/docker to run the steps in the build. Container will be attached to network using option --network=cloudbuild.
Running Cloud Build to build the Docker image. Cloud Build logs: https://console.cloud.google.com/cloud-build/builds/068e77a1-4e6f-427a-bf94-49c52270af7a?project=20219041791
The Docker image has been built successfully. More information can be found in the Cloud Build logs: https://console.cloud.google.com/cloud-build/builds/068e77a1-4e6f-427a-bf94-49c52270af7a?project=20219041791.
Finished building Docker image(s).
Running pipeline simple_pipeline on stack gcp-demo (caching disabled)
The attribute pipeline_root has not been set in the orchestrator configuration. One has been generated automatically based on the path of the GCPArtifactStore artifact store in the stack used to execute the pipeline. The generated pipeline_root is gs://zenml-bucket-sl/vertex_pipeline_root/simple_pipeline/simple_pipeline_default_6e72f3e1.
/home/stefan/aspyre/src/zenml/.venv/lib/python3.8/site-packages/kfp/v2/compiler/compiler.py:1290: FutureWarning: APIs imported from the v1 namespace (e.g. kfp.dsl, kfp.components, etc) will not be supported by the v2 compiler since v2.0.0
    warnings.warn(
Writing Vertex workflow definition to /home/stefan/.config/zenml/vertex/8a0b53ee-644a-4fbe-8e91-d4d6ddf79ae8/pipelines/simple_pipeline_default_6e72f3e1.json.
No schedule detected. Creating one-off vertex job...
Submitting pipeline job with job_id simple-pipeline-default-6e72f3e1 to Vertex AI Pipelines service.
The Vertex AI Pipelines job workload will be executed using the connectors-vertex-ai-workload@zenml-core.iam.gserviceaccount.com service account.
Creating PipelineJob
INFO:google.cloud.aiplatform.pipeline_jobs:Creating PipelineJob
PipelineJob created. Resource name: projects/20219041791/locations/europe-west1/pipelineJobs/simple-pipeline-default-6e72f3e1
INFO:google.cloud.aiplatform.pipeline_jobs:PipelineJob created. Resource name: projects/20219041791/locations/europe-west1/pipelineJobs/simple-pipeline-default-6e72f3e1
To use this PipelineJob in another session:
INFO:google.cloud.aiplatform.pipeline_jobs:To use this PipelineJob in another session:
pipeline_job = aiplatform.PipelineJob.get('projects/20219041791/locations/europe-west1/pipelineJobs/simple-pipeline-default-6e72f3e1')
INFO:google.cloud.aiplatform.pipeline_jobs:pipeline_job = aiplatform.PipelineJob.get('projects/20219041791/locations/europe-west1/pipelineJobs/simple-pipeline-default-6e72f3e1')
View Pipeline Job:
https://console.cloud.google.com/vertex-ai/locations/europe-west1/pipelines/runs/simple-pipeline-default-6e72f3e1?project=20219041791
INFO:google.cloud.aiplatform.pipeline_jobs:View Pipeline Job:
https://console.cloud.google.com/vertex-ai/locations/europe-west1/pipelines/runs/simple-pipeline-default-6e72f3e1?project=20219041791
View the Vertex AI Pipelines job at https://console.cloud.google.com/vertex-ai/locations/europe-west1/pipelines/runs/simple-pipeline-default-6e72f3e1?project=20219041791
Waiting for the Vertex AI Pipelines job to finish...
PipelineJob projects/20219041791/locations/europe-west1/pipelineJobs/simple-pipeline-default-6e72f3e1 current state:
PipelineState.PIPELINE_STATE_RUNNING
INFO:google.cloud.aiplatform.pipeline_jobs:PipelineJob projects/20219041791/locations/europe-west1/pipelineJobs/simple-pipeline-default-6e72f3e1 current state:
PipelineState.PIPELINE_STATE_RUNNING
...
PipelineJob run completed. Resource name: projects/20219041791/locations/europe-west1/pipelineJobs/simple-pipeline-default-6e72f3e1
INFO:google.cloud.aiplatform.pipeline_jobs:PipelineJob run completed. Resource name: projects/20219041791/locations/europe-west1/pipelineJobs/simple-pipeline-default-6e72f3e1
Dashboard URL: https://34.148.132.191/default/pipelines/17cac6b5-3071-45fa-a2ef-cda4a7965039/runs
```
````
{% endcode %}

</details>

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
