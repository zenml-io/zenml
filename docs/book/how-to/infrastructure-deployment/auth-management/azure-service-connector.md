---
description: >-
  Configuring Azure Service Connectors to connect ZenML to Azure resources such
  as Blob storage buckets, AKS Kubernetes clusters, and ACR container
  registries.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Azure Service Connector

The ZenML Azure Service Connector facilitates the authentication and access to managed Azure services and resources. These encompass a range of resources, including blob storage containers, ACR repositories, and AKS clusters.

This connector also supports [automatic configuration and detection of credentials](service-connectors-guide.md#auto-configuration) locally configured through the Azure CLI.

This connector serves as a general means of accessing any Azure service by issuing credentials to clients. Additionally, the connector can handle specialized authentication for Azure blob storage, Docker and Kubernetes Python clients. It also allows for the configuration of local Docker and Kubernetes CLIs.

```shell
$ zenml service-connector list-types --type azure
```
```shell
┏━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━┯━━━━━━━┯━━━━━━━━┓
┃          NAME           │ TYPE     │ RESOURCE TYPES        │ AUTH METHODS      │ LOCAL │ REMOTE ┃
┠─────────────────────────┼──────────┼───────────────────────┼───────────────────┼───────┼────────┨
┃ Azure Service Connector │ 🇦 azure │ 🇦 azure-generic      │ implicit          │ ✅    │ ✅     ┃
┃                         │          │ 📦 blob-container     │ service-principal │       │        ┃
┃                         │          │ 🌀 kubernetes-cluster │ access-token      │       │        ┃
┃                         │          │ 🐳 docker-registry    │                   │       │        ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━┷━━━━━━━┷━━━━━━━━┛
```

## Prerequisites

The Azure Service Connector is part of the Azure ZenML integration. You can either install the entire integration or use a pypi extra to install it independently of the integration:

* `pip install "zenml[connectors-azure]"` installs only prerequisites for the Azure Service Connector Type
* `zenml integration install azure` installs the entire Azure ZenML integration

It is not required to [install and set up the Azure CLI](https://learn.microsoft.com/en-us/cli/azure/authenticate-azure-cli) on your local machine to use the Azure Service Connector to link Stack Components to Azure resources and services. However, it is recommended to do so if you are looking for a quick setup that includes using the auto-configuration Service Connector features.

{% hint style="info" %}
The auto-configuration option is limited to using temporary access tokens that don't work with Azure blob storage resources. To unlock the full power of the Azure Service Connector it is therefore recommended that you [configure and use an Azure service principal and its credentials](https://learn.microsoft.com/en-us/azure/developer/python/sdk/authentication-on-premises-apps?tabs=azure-portal).
{% endhint %}

## Resource Types

### Generic Azure resource

This resource type allows Stack Components to use the Azure Service Connector to connect to any Azure service or resource. When used by Stack Components, they are provided generic azure-identity credentials that can be used to create Azure python clients for any particular Azure service.

This generic Azure resource type is meant to be used with Stack Components that are not represented by other, more specific resource type, like Azure blob storage containers, Kubernetes clusters or Docker registries. It should be accompanied by a matching set of Azure permissions that allow access to the set of remote resources required by the Stack Components.

The resource name represents the name of the Azure subscription that the connector is authorized to access.

### Azure blob storage container

Allows users to connect to Azure Blob containers. When used by Stack Components, they are provided a pre-configured Azure Blob Storage client.

The configured credentials must have at least the following Azure IAM permissions associated with the blob storage account or containers that the connector that the connector will be allowed to access:

* allow read and write access to blobs (e.g. the `Storage Blob Data Contributor` role)
* allow listing the storage accounts (e.g. the `Reader and Data Access` role). This is only required if a storage account is not configured in the connector.
* allow listing the containers in a storage account (e.g. the `Reader and Data Access` role)

If set, the resource name must identify an Azure blob storage container using one of the following formats:

* Azure blob container URI (canonical resource name): `{az|abfs}://{container-name}`
* Azure blob container name: `{container-name}`

If a storage account is configured in the connector, only blob storage containers in that storage account will be accessible. Otherwise, if a resource group is configured in the connector, only blob storage containers in storage accounts in that resource group will be accessible. Finally, if neither a storage account nor a resource group is configured in the connector, all blob storage containers in all accessible storage accounts will be accessible.

{% hint style="warning" %}
The only Azure authentication method that works with Azure blob storage resources is the service principal authentication method.
{% endhint %}

### AKS Kubernetes cluster

Allows Stack Components to access an AKS cluster as a standard Kubernetes cluster resource. When used by Stack Components, they are provided a pre-authenticated python-kubernetes client instance.

The configured credentials must have at least the following Azure IAM permissions associated with the AKS clusters that the connector will be allowed to access:

* allow listing the AKS clusters and fetching their credentials (e.g. the `Azure Kubernetes Service Cluster Admin Role` role)

If set, the resource name must identify an EKS cluster using one of the following formats:

* resource group scoped AKS cluster name (canonical): `[{resource-group}/]{cluster-name}`
* AKS cluster name: `{cluster-name}`

Given that the AKS cluster name is unique within a resource group, the resource group name may be included in the resource name to avoid ambiguity. If a resource group is configured in the connector, the resource group name in the resource name must match the configured resource group. If no resource group is configured in the connector and a resource group name is not included in the resource name, the connector will attempt to find the AKS cluster in any resource group.

If a resource group is configured in the connector, only AKS clusters in that resource group will be accessible.

### ACR container registry

Allows Stack Components to access one or more ACR registries as a standard Docker registry resource. When used by Stack Components, they are provided a pre-authenticated python-docker client instance.

The configured credentials must have at least the following Azure IAM permissions associated with the ACR registries that the connector will be allowed to access:

* allow access to pull and push images (e.g. the `AcrPull` and `AcrPush` roles)
* allow access to list registries (e.g. the `Contributor` role)

If set, the resource name must identify an ACR registry using one of the following formats:

* ACR registry URI (canonical resource name): `[https://]{registry-name}.azurecr.io`
* ACR registry name: `{registry-name}`

If a resource group is configured in the connector, only ACR registries in that resource group will be accessible.

If an authentication method other than the Azure service principal is used for authentication, the admin account must be enabled for the registry, otherwise, clients will not be able to authenticate to the registry. See the official Azure [documentation on the admin account](https://docs.microsoft.com/en-us/azure/container-registry/container-registry-authentication#admin-account) for more information.

## Authentication Methods

### Implicit authentication

[Implicit authentication](best-security-practices.md#implicit-authentication) to Azure services using environment variables, local configuration files, workload or managed identities.

{% hint style="warning" %}
This method may constitute a security risk, because it can give users access to the same cloud resources and services that the ZenML Server itself is configured to access. For this reason, all implicit authentication methods are disabled by default and need to be explicitly enabled by setting the `ZENML_ENABLE_IMPLICIT_AUTH_METHODS` environment variable or the helm chart `enableImplicitAuthMethods` configuration option to `true` in the ZenML deployment.
{% endhint %}

This authentication method doesn't require any credentials to be explicitly configured. It automatically discovers and uses credentials from one of the following sources:

* [environment variables](https://learn.microsoft.com/en-us/python/api/overview/azure/identity-readme?view=azure-python#environment-variables)
* workload identity - if the application is deployed to an Azure Kubernetes Service with Managed Identity enabled. This option can only be used when running the ZenML server on an AKS cluster.
* managed identity - if the application is deployed to an Azure host with Managed Identity enabled. This option can only be used when running the ZenML client or server on an Azure host.
* Azure CLI - if a user has signed in via [the Azure CLI `az login` command](https://learn.microsoft.com/en-us/cli/azure/authenticate-azure-cli).

This is the quickest and easiest way to authenticate to Azure services. However, the results depend on how ZenML is deployed and the environment where it is used and is thus not fully reproducible:

* when used with the default local ZenML deployment or a local ZenML server, the credentials are the same as those used by the Azure CLI or extracted from local environment variables.
* when connected to a ZenML server, this method only works if the ZenML server is deployed in Azure and will use the workload identity attached to the Azure resource where the ZenML server is running (e.g. an AKS cluster). The permissions of the managed identity may need to be adjusted to allows listing and accessing/describing the Azure resources that the connector is configured to access.

Note that the discovered credentials inherit the full set of permissions of the local Azure CLI configuration, environment variables or remote Azure managed identity. Depending on the extent of those permissions, this authentication method might not be recommended for production use, as it can lead to accidental privilege escalation. Instead, it is recommended to use the Azure service principal authentication method to limit the validity and/or permissions of the credentials being issued to connector clients.

<details>

<summary>Example configuration</summary>

The following assumes the local Azure CLI has already been configured with user account credentials by running the `az login` command:

```sh
zenml service-connector register azure-implicit --type azure --auth-method implicit --auto-configure
```

{% code title="Example Command Output" %}
```
⠙ Registering service connector 'azure-implicit'...
Successfully registered service connector `azure-implicit` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃     RESOURCE TYPE     │ RESOURCE NAMES                                ┃
┠───────────────────────┼───────────────────────────────────────────────┨
┃   🇦 azure-generic    │ ZenML Subscription                            ┃
┠───────────────────────┼───────────────────────────────────────────────┨
┃   📦 blob-container   │ az://demo-zenmlartifactstore                  ┃
┠───────────────────────┼───────────────────────────────────────────────┨
┃ 🌀 kubernetes-cluster │ demo-zenml-demos/demo-zenml-terraform-cluster ┃
┠───────────────────────┼───────────────────────────────────────────────┨
┃  🐳 docker-registry   │ demozenmlcontainerregistry.azurecr.io         ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

No credentials are stored with the Service Connector:

```sh
zenml service-connector describe azure-implicit
```

{% code title="Example Command Output" %}
```
Service connector 'azure-implicit' of type 'azure' with id 'ad645002-0cd4-4d4f-ae20-499ce888a00a' is owned by user 'default' and is 'private'.
                          'azure-implicit' azure Service Connector Details                           
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                                          ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ ID               │ ad645002-0cd4-4d4f-ae20-499ce888a00a                                           ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ NAME             │ azure-implicit                                                                 ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ TYPE             │ 🇦  azure                                                                       ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ AUTH METHOD      │ implicit                                                                       ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE TYPES   │ 🇦  azure-generic, 📦 blob-container, 🌀 kubernetes-cluster, 🐳 docker-registry ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE NAME    │ <multiple>                                                                     ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ SECRET ID        │                                                                                ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ SESSION DURATION │ N/A                                                                            ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ EXPIRES IN       │ N/A                                                                            ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ OWNER            │ default                                                                        ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ SHARED           │ ➖                                                                             ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ CREATED_AT       │ 2023-06-05 09:47:42.415949                                                     ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-06-05 09:47:42.415954                                                     ┃
┗━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

</details>

### Azure Service Principal

Azure service principal credentials consists of an Azure client ID and client secret. These credentials are used to authenticate clients to Azure services.

For this authentication method, the Azure Service Connector requires [an Azure service principal to be created](https://learn.microsoft.com/en-us/azure/developer/python/sdk/authentication-on-premises-apps?tabs=azure-portal) and a client secret to be generated.

<details>

<summary>Example configuration</summary>

The following assumes an Azure service principal was configured with a client secret and has permissions to access an Azure blob storage container, an AKS Kubernetes cluster and an ACR container registry. The service principal client ID, tenant ID and client secret are then used to configure the Azure Service Connector.

```sh
zenml service-connector register azure-service-principal --type azure --auth-method service-principal --tenant_id=a79f3633-8f45-4a74-a42e-68871c17b7fb --client_id=8926254a-8c3f-430a-a2fd-bdab234d491e --client_secret=AzureSuperSecret
```

{% code title="Example Command Output" %}
```
⠙ Registering service connector 'azure-service-principal'...
Successfully registered service connector `azure-service-principal` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃     RESOURCE TYPE     │ RESOURCE NAMES                                ┃
┠───────────────────────┼───────────────────────────────────────────────┨
┃   🇦 azure-generic    │ ZenML Subscription                            ┃
┠───────────────────────┼───────────────────────────────────────────────┨
┃   📦 blob-container   │ az://demo-zenmlartifactstore                  ┃
┠───────────────────────┼───────────────────────────────────────────────┨
┃ 🌀 kubernetes-cluster │ demo-zenml-demos/demo-zenml-terraform-cluster ┃
┠───────────────────────┼───────────────────────────────────────────────┨
┃  🐳 docker-registry   │ demozenmlcontainerregistry.azurecr.io         ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

The Service Connector configuration shows that the connector is configured with service principal credentials:

```sh
zenml service-connector describe azure-service-principal
```

{% code title="Example Command Output" %}
```
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                                          ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ ID               │ 273d2812-2643-4446-82e6-6098b8ccdaa4                                           ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ NAME             │ azure-service-principal                                                        ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ TYPE             │ 🇦  azure                                                                       ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ AUTH METHOD      │ service-principal                                                              ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE TYPES   │ 🇦  azure-generic, 📦 blob-container, 🌀 kubernetes-cluster, 🐳 docker-registry ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE NAME    │ <multiple>                                                                     ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ SECRET ID        │ 50d9f230-c4ea-400e-b2d7-6b52ba2a6f90                                           ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ SESSION DURATION │ N/A                                                                            ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ EXPIRES IN       │ N/A                                                                            ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ OWNER            │ default                                                                        ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ SHARED           │ ➖                                                                             ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ CREATED_AT       │ 2023-06-20 19:16:26.802374                                                     ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-06-20 19:16:26.802378                                                     ┃
┗━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                     Configuration                      
┏━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY      │ VALUE                                ┃
┠───────────────┼──────────────────────────────────────┨
┃ tenant_id     │ a79ff333-8f45-4a74-a42e-68871c17b7fb ┃
┠───────────────┼──────────────────────────────────────┨
┃ client_id     │ 8926254a-8c3f-430a-a2fd-bdab234d491e ┃
┠───────────────┼──────────────────────────────────────┨
┃ client_secret │ [HIDDEN]                             ┃
┗━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

</details>

### Azure Access Token

Uses [temporary Azure access tokens](best-security-practices.md#short-lived-credentials) explicitly configured by the user or auto-configured from a local environment.

This method has the major limitation that the user must regularly generate new tokens and update the connector configuration as API tokens expire. On the other hand, this method is ideal in cases where the connector only needs to be used for a short period of time, such as sharing access temporarily with someone else in your team.

This is the authentication method used during auto-configuration, if you have [the local Azure CLI set up with credentials](https://learn.microsoft.com/en-us/cli/azure/authenticate-azure-cli). The connector will generate an access token from the Azure CLI credentials and store it in the connector configuration.

{% hint style="warning" %}
Given that Azure access tokens are scoped to a particular Azure resource and the access token generated during auto-configuration is scoped to the Azure Management API, this method does not work with Azure blob storage resources. You should use [the Azure service principal authentication method](azure-service-connector.md#azure-service-principal) for blob storage resources instead.
{% endhint %}

<details>

<summary>Example auto-configuration</summary>

Fetching Azure session tokens from the local Azure CLI is possible if the Azure CLI is already configured with valid credentials (i.e. by running `az login`):

```sh
zenml service-connector register azure-session-token --type azure --auto-configure
```

{% code title="Example Command Output" %}
```
⠙ Registering service connector 'azure-session-token'...
connector authorization failure: the 'access-token' authentication method is not supported for blob storage resources
Successfully registered service connector `azure-session-token` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃     RESOURCE TYPE     │ RESOURCE NAMES                                                                                                                  ┃
┠───────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃   🇦 azure-generic    │ ZenML Subscription                                                                                                              ┃
┠───────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃   📦 blob-container   │ 💥 error: connector authorization failure: the 'access-token' authentication method is not supported for blob storage resources ┃
┠───────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃ 🌀 kubernetes-cluster │ demo-zenml-demos/demo-zenml-terraform-cluster                                                                                   ┃
┠───────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┨
┃  🐳 docker-registry   │ demozenmlcontainerregistry.azurecr.io                                                                                           ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

```sh
zenml service-connector describe azure-session-token 
```

{% code title="Example Command Output" %}
```
Service connector 'azure-session-token' of type 'azure' with id '94d64103-9902-4aa5-8ce4-877061af89af' is owned by user 'default' and is 'private'.
                        'azure-session-token' azure Service Connector Details                        
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                                          ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ ID               │ 94d64103-9902-4aa5-8ce4-877061af89af                                           ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ NAME             │ azure-session-token                                                            ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ TYPE             │ 🇦 azure                                                                       ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ AUTH METHOD      │ access-token                                                                   ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE TYPES   │ 🇦 azure-generic, 📦 blob-container, 🌀 kubernetes-cluster, 🐳 docker-registry ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE NAME    │ <multiple>                                                                     ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ SECRET ID        │ b34f2e95-ae16-43b6-8ab6-f0ee33dbcbd8                                           ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ SESSION DURATION │ N/A                                                                            ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ EXPIRES IN       │ 42m25s                                                                         ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ OWNER            │ default                                                                        ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ SHARED           │ ➖                                                                             ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ CREATED_AT       │ 2023-06-05 10:03:32.646351                                                     ┃
┠──────────────────┼────────────────────────────────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-06-05 10:03:32.646352                                                     ┃
┗━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
     Configuration     
┏━━━━━━━━━━┯━━━━━━━━━━┓
┃ PROPERTY │ VALUE    ┃
┠──────────┼──────────┨
┃ token    │ [HIDDEN] ┃
┗━━━━━━━━━━┷━━━━━━━━━━┛
```
{% endcode %}

Note the temporary nature of the Service Connector. It will expire and become unusable in approximately 1 hour:

```sh
zenml service-connector list --name azure-session-token 
```

{% code title="Example Command Output" %}
```
Could not import GCP service connector: No module named 'google.api_core'.
┏━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━┓
┃ ACTIVE │ NAME                │ ID                                   │ TYPE     │ RESOURCE TYPES        │ RESOURCE NAME │ SHARED │ OWNER   │ EXPIRES IN │ LABELS ┃
┠────────┼─────────────────────┼──────────────────────────────────────┼──────────┼───────────────────────┼───────────────┼────────┼─────────┼────────────┼────────┨
┃        │ azure-session-token │ 94d64103-9902-4aa5-8ce4-877061af89af │ 🇦 azure │ 🇦 azure-generic      │ <multiple>    │ ➖     │ default │ 40m58s     │        ┃
┃        │                     │                                      │          │ 📦 blob-container     │               │        │         │            │        ┃
┃        │                     │                                      │          │ 🌀 kubernetes-cluster │               │        │         │            │        ┃
┃        │                     │                                      │          │ 🐳 docker-registry    │               │        │         │            │        ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━┛
```
{% endcode %}

</details>

## Auto-configuration

The Azure Service Connector allows [auto-discovering and fetching credentials](service-connectors-guide.md#auto-configuration) and [configuration set up by the Azure CLI](https://learn.microsoft.com/en-us/cli/azure/authenticate-azure-cli) on your local host.

{% hint style="warning" %}
The Azure service connector auto-configuration comes with two limitations:

1. it can only pick up temporary Azure access tokens and therefore cannot be used for long-term authentication scenarios
2. it doesn't support authenticating to the Azure blob storage service. [The Azure service principal authentication method](azure-service-connector.md#azure-service-principal) can be used instead.
{% endhint %}

For an auto-configuration example, please refer to the [section about Azure access tokens](azure-service-connector.md#azure-access-token).

## Local client provisioning

The local Azure CLI, Kubernetes `kubectl` CLI and the Docker CLI can be [configured with credentials extracted from or generated by a compatible Azure Service Connector](service-connectors-guide.md#configure-local-clients).

{% hint style="info" %}
Note that the Azure local CLI can only be configured with credentials issued by the Azure Service Connector if the connector is configured with the [service principal authentication method](azure-service-connector.md#azure-service-principal).
{% endhint %}

<details>

<summary>Local CLI configuration examples</summary>

The following shows an example of configuring the local Kubernetes CLI to access an AKS cluster reachable through an Azure Service Connector:

```sh
zenml service-connector list --name azure-service-principal
```

{% code title="Example Command Output" %}
```
┏━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━┓
┃ ACTIVE │ NAME                    │ ID                                   │ TYPE     │ RESOURCE TYPES        │ RESOURCE NAME │ SHARED │ OWNER   │ EXPIRES IN │ LABELS ┃
┠────────┼─────────────────────────┼──────────────────────────────────────┼──────────┼───────────────────────┼───────────────┼────────┼─────────┼────────────┼────────┨
┃        │ azure-service-principal │ 3df920bc-120c-488a-b7fc-0e79bc8b021a │ 🇦 azure │ 🇦 azure-generic      │ <multiple>    │ ➖     │ default │            │        ┃
┃        │                         │                                      │          │ 📦 blob-container     │               │        │         │            │        ┃
┃        │                         │                                      │          │ 🌀 kubernetes-cluster │               │        │         │            │        ┃
┃        │                         │                                      │          │ 🐳 docker-registry    │               │        │         │            │        ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━┛
```
{% endcode %}

The verify CLI command can be used to list all Kubernetes clusters accessible through the Azure Service Connector:

```sh
zenml service-connector verify azure-service-principal --resource-type kubernetes-cluster
```

{% code title="Example Command Output" %}
```
⠙ Verifying service connector 'azure-service-principal'...
Service connector 'azure-service-principal' is correctly configured with valid credentials and has access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃     RESOURCE TYPE     │ RESOURCE NAMES                                ┃
┠───────────────────────┼───────────────────────────────────────────────┨
┃ 🌀 kubernetes-cluster │ demo-zenml-demos/demo-zenml-terraform-cluster ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

The login CLI command can be used to configure the local Kubernetes CLI to access a Kubernetes cluster reachable through an Azure Service Connector:

```sh
zenml service-connector login azure-service-principal --resource-type kubernetes-cluster --resource-id demo-zenml-demos/demo-zenml-terraform-cluster
```

{% code title="Example Command Output" %}
```
⠙ Attempting to configure local client using service connector 'azure-service-principal'...
Updated local kubeconfig with the cluster details. The current kubectl context was set to 'demo-zenml-terraform-cluster'.
The 'azure-service-principal' Kubernetes Service Connector connector was used to successfully configure the local Kubernetes cluster client/SDK.
```
{% endcode %}

The local Kubernetes CLI can now be used to interact with the Kubernetes cluster:

```sh
kubectl cluster-info
```

{% code title="Example Command Output" %}
```
Kubernetes control plane is running at https://demo-43c5776f7.hcp.westeurope.azmk8s.io:443
CoreDNS is running at https://demo-43c5776f7.hcp.westeurope.azmk8s.io:443/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy
Metrics-server is running at https://demo-43c5776f7.hcp.westeurope.azmk8s.io:443/api/v1/namespaces/kube-system/services/https:metrics-server:/proxy
```
{% endcode %}

A similar process is possible with ACR container registries:

```sh
zenml service-connector verify azure-service-principal --resource-type docker-registry
```

{% code title="Example Command Output" %}
```
⠦ Verifying service connector 'azure-service-principal'...
Service connector 'azure-service-principal' is correctly configured with valid credentials and has access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃   RESOURCE TYPE    │ RESOURCE NAMES                        ┃
┠────────────────────┼───────────────────────────────────────┨
┃ 🐳 docker-registry │ demozenmlcontainerregistry.azurecr.io ┃
┗━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

```sh
zenml service-connector login azure-service-principal --resource-type docker-registry --resource-id demozenmlcontainerregistry.azurecr.io
```

{% code title="Example Command Output" %}
```
⠹ Attempting to configure local client using service connector 'azure-service-principal'...
WARNING! Your password will be stored unencrypted in /home/stefan/.docker/config.json.
Configure a credential helper to remove this warning. See
https://docs.docker.com/engine/reference/commandline/login/#credentials-store

The 'azure-service-principal' Docker Service Connector connector was used to successfully configure the local Docker/OCI container registry client/SDK.
```
{% endcode %}

The local Docker CLI can now be used to interact with the container registry:

```sh
docker push demozenmlcontainerregistry.azurecr.io/zenml:example_pipeline
```

{% code title="Example Command Output" %}
```
The push refers to repository [demozenmlcontainerregistry.azurecr.io/zenml]
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

It is also possible to update the local Azure CLI configuration with credentials extracted from the Azure Service Connector:

```sh
zenml service-connector login azure-service-principal --resource-type azure-generic
```

{% code title="Example Command Output" %}
```
Updated the local Azure CLI configuration with the connector's service principal credentials.
The 'azure-service-principal' Azure Service Connector connector was used to successfully configure the local Generic Azure resource client/SDK.
```
{% endcode %}

</details>

## Stack Components use

The [Azure Artifact Store Stack Component](../../../component-guide/artifact-stores/azure.md) can be connected to a remote Azure blob storage container through an Azure Service Connector.

The Azure Service Connector can also be used with any Orchestrator or Model Deployer stack component flavor that relies on a Kubernetes clusters to manage workloads. This allows AKS Kubernetes container workloads to be managed without the need to configure and maintain explicit Azure or Kubernetes `kubectl` configuration contexts and credentials in the target environment or in the Stack Component itself.

Similarly, Container Registry Stack Components can be connected to a ACR Container Registry through an Azure Service Connector. This allows container images to be built and published to private ACR container registries without the need to configure explicit Azure credentials in the target environment or the Stack Component.

## End-to-end examples

<details>

<summary>AKS Kubernetes Orchestrator, Azure Blob Storage Artifact Store and ACR Container Registry with a multi-type Azure Service Connector</summary>

This is an example of an end-to-end workflow involving Service Connectors that uses a single multi-type Azure Service Connector to give access to multiple resources for multiple Stack Components. A complete ZenML Stack is registered composed of the following Stack Components, all connected through the same Service Connector:

* a [Kubernetes Orchestrator](../../../component-guide/orchestrators/kubernetes.md) connected to an AKS Kubernetes cluster
* a [Azure Blob Storage Artifact Store](../../../component-guide/artifact-stores/azure.md) connected to an Azure blob storage container
* an [Azure Container Registry](../../../component-guide/container-registries/azure.md) connected to an ACR container registry
* a local [Image Builder](../../../component-guide/image-builders/local.md)

As a last step, a simple pipeline is run on the resulting Stack.

This example needs to use a remote ZenML Server that is reachable from Azure.

1.  Configure an Azure service principal with a client secret and give it permissions to access an Azure blob storage container, an AKS Kubernetes cluster and an ACR container registry. Also make sure you have the Azure ZenML integration installed:

    ```sh
    zenml integration install -y azure
    ```
2.  Make sure the Azure Service Connector Type is available

    ```sh
    zenml service-connector list-types --type azure
    ```

{% code title="Example Command Output" %}
````
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━┯━━━━━━━┯━━━━━━━━┓
┃          NAME           │ TYPE     │ RESOURCE TYPES        │ AUTH METHODS      │ LOCAL │ REMOTE ┃
┠─────────────────────────┼──────────┼───────────────────────┼───────────────────┼───────┼────────┨
┃ Azure Service Connector │ 🇦 azure │ 🇦 azure-generic      │ implicit          │ ✅    │ ✅     ┃
┃                         │          │ 📦 blob-container     │ service-principal │       │        ┃
┃                         │          │ 🌀 kubernetes-cluster │ access-token      │       │        ┃
┃                         │          │ 🐳 docker-registry    │                   │       │        ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━┷━━━━━━━┷━━━━━━━━┛
```
````
{% endcode %}

3.  Register a multi-type Azure Service Connector using the Azure service principal credentials set up at the first step. Note the resources that it has access to:

    ```sh
    zenml service-connector register azure-service-principal --type azure --auth-method service-principal --tenant_id=a79ff3633-8f45-4a74-a42e-68871c17b7fb --client_id=8926254a-8c3f-430a-a2fd-bdab234fd491e --client_secret=AzureSuperSecret
    ```

{% code title="Example Command Output" %}
````
```
⠸ Registering service connector 'azure-service-principal'...
Successfully registered service connector `azure-service-principal` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃     RESOURCE TYPE     │ RESOURCE NAMES                                ┃
┠───────────────────────┼───────────────────────────────────────────────┨
┃   🇦 azure-generic    │ ZenML Subscription                            ┃
┠───────────────────────┼───────────────────────────────────────────────┨
┃   📦 blob-container   │ az://demo-zenmlartifactstore                  ┃
┠───────────────────────┼───────────────────────────────────────────────┨
┃ 🌀 kubernetes-cluster │ demo-zenml-demos/demo-zenml-terraform-cluster ┃
┠───────────────────────┼───────────────────────────────────────────────┨
┃  🐳 docker-registry   │ demozenmlcontainerregistry.azurecr.io         ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
````
{% endcode %}

4.  register and connect an Azure Blob Storage Artifact Store Stack Component to an Azure blob container:

    ```sh
    zenml artifact-store register azure-demo --flavor azure --path=az://demo-zenmlartifactstore
    ```

{% code title="Example Command Output" %}
````
```
Successfully registered artifact_store `azure-demo`.
```
````
{% endcode %}

````
```sh
zenml artifact-store connect azure-demo --connector azure-service-principal
```

````

{% code title="Example Command Output" %}
````
```
Successfully connected artifact store `azure-demo` to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME          │ CONNECTOR TYPE │ RESOURCE TYPE     │ RESOURCE NAMES               ┃
┠──────────────────────────────────────┼─────────────────────────┼────────────────┼───────────────────┼──────────────────────────────┨
┃ f2316191-d20b-4348-a68b-f5e347862196 │ azure-service-principal │ 🇦 azure       │ 📦 blob-container │ az://demo-zenmlartifactstore ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
````
{% endcode %}

5.  register and connect a Kubernetes Orchestrator Stack Component to an AKS cluster:

    ```sh
    zenml orchestrator register aks-demo-cluster --flavor kubernetes --synchronous=true --kubernetes_namespace=zenml-workloads
    ```

{% code title="Example Command Output" %}
````
```
Successfully registered orchestrator `aks-demo-cluster`.
```
````
{% endcode %}

````
```sh
zenml orchestrator connect aks-demo-cluster --connector azure-service-principal
```

````

{% code title="Example Command Output" %}
````
```
Successfully connected orchestrator `aks-demo-cluster` to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME          │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES                                ┃
┠──────────────────────────────────────┼─────────────────────────┼────────────────┼───────────────────────┼───────────────────────────────────────────────┨
┃ f2316191-d20b-4348-a68b-f5e347862196 │ azure-service-principal │ 🇦 azure       │ 🌀 kubernetes-cluster │ demo-zenml-demos/demo-zenml-terraform-cluster ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
````
{% endcode %}

6.  Register and connect an Azure Container Registry Stack Component to an ACR container registry:

    ```sh
    zenml container-registry register acr-demo-registry --flavor azure --uri=demozenmlcontainerregistry.azurecr.io
    ```

{% code title="Example Command Output" %}
````
```
Successfully registered container_registry `acr-demo-registry`.
```
````
{% endcode %}

````
```sh
zenml container-registry connect acr-demo-registry --connector azure-service-principal
```

````

{% code title="Example Command Output" %}
````
```
Successfully connected container registry `acr-demo-registry` to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME          │ CONNECTOR TYPE │ RESOURCE TYPE      │ RESOURCE NAMES                        ┃
┠──────────────────────────────────────┼─────────────────────────┼────────────────┼────────────────────┼───────────────────────────────────────┨
┃ f2316191-d20b-4348-a68b-f5e347862196 │ azure-service-principal │ 🇦 azure       │ 🐳 docker-registry │ demozenmlcontainerregistry.azurecr.io ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
````
{% endcode %}

7.  Combine all Stack Components together into a Stack and set it as active (also throw in a local Image Builder for completion):

    ```sh
    zenml image-builder register local --flavor local
    ```

{% code title="Example Command Output" %}
````
```
Running with active stack: 'default' (global)
Successfully registered image_builder `local`.
```
````
{% endcode %}

````
```sh
zenml stack register gcp-demo -a azure-demo -o aks-demo-cluster -c acr-demo-registry -i local --set
```

````

{% code title="Example Command Output" %}
````
```
Stack 'gcp-demo' successfully registered!
Active repository stack set to:'gcp-demo'
```
````
{% endcode %}

8.  Finally, run a simple pipeline to prove that everything works as expected. We'll use the simplest pipelines possible for this example:

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
```
$ python run.py
Building Docker image(s) for pipeline simple_pipeline.
Building Docker image demozenmlcontainerregistry.azurecr.io/zenml:simple_pipeline-orchestrator.
- Including integration requirements: adlfs==2021.10.0, azure-identity==1.10.0, azure-keyvault-keys, azure-keyvault-secrets, azure-mgmt-containerservice>=20.0.0, azureml-core==1.48.0, kubernetes, kubernetes==18.20.0
No .dockerignore found, including all files inside build context.
Step 1/10 : FROM zenmldocker/zenml:0.40.0-py3.8
Step 2/10 : WORKDIR /app
Step 3/10 : COPY .zenml_user_requirements .
Step 4/10 : RUN pip install --default-timeout=60 --no-cache-dir  -r .zenml_user_requirements
Step 5/10 : COPY .zenml_integration_requirements .
Step 6/10 : RUN pip install --default-timeout=60 --no-cache-dir  -r .zenml_integration_requirements
Step 7/10 : ENV ZENML_ENABLE_REPO_INIT_WARNINGS=False
Step 8/10 : ENV ZENML_CONFIG_PATH=/app/.zenconfig
Step 9/10 : COPY . .
Step 10/10 : RUN chmod -R a+rw .
Pushing Docker image demozenmlcontainerregistry.azurecr.io/zenml:simple_pipeline-orchestrator.
Finished pushing Docker image.
Finished building Docker image(s).
Running pipeline simple_pipeline on stack gcp-demo (caching disabled)
Waiting for Kubernetes orchestrator pod...
Kubernetes orchestrator pod started.
Waiting for pod of step simple_step_one to start...
Step simple_step_one has started.
INFO:azure.identity._internal.get_token_mixin:ClientSecretCredential.get_token succeeded
INFO:azure.identity._internal.get_token_mixin:ClientSecretCredential.get_token succeeded
INFO:azure.identity._internal.get_token_mixin:ClientSecretCredential.get_token succeeded
INFO:azure.identity.aio._internal.get_token_mixin:ClientSecretCredential.get_token succeeded
Step simple_step_one has finished in 0.396s.
Pod of step simple_step_one completed.
Waiting for pod of step simple_step_two to start...
Step simple_step_two has started.
INFO:azure.identity._internal.get_token_mixin:ClientSecretCredential.get_token succeeded
INFO:azure.identity._internal.get_token_mixin:ClientSecretCredential.get_token succeeded
INFO:azure.identity.aio._internal.get_token_mixin:ClientSecretCredential.get_token succeeded
Hello World!
Step simple_step_two has finished in 3.203s.
Pod of step simple_step_two completed.
Orchestration pod completed.
Dashboard URL: https://zenml.stefan.20.23.46.143.nip.io/default/pipelines/98c41e2a-1ab0-4ec9-8375-6ea1ab473686/runs
```
````
{% endcode %}

</details>

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
