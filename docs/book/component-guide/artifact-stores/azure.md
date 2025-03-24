---
description: Storing artifacts using Azure Blob Storage
---

# Azure Blob Storage

The Azure Artifact Store is an [Artifact Store](./) flavor provided with the Azure ZenML integration that uses [the Azure Blob Storage managed object storage service](https://azure.microsoft.com/en-us/services/storage/blobs/) to store ZenML artifacts in an Azure Blob Storage container.

### When would you want to use it?

Running ZenML pipelines with [the local Artifact Store](local.md) is usually sufficient if you just want to evaluate ZenML or get started quickly without incurring the trouble and the cost of employing cloud storage services in your stack. However, the local Artifact Store becomes insufficient or unsuitable if you have more elaborate needs for your project:

* if you want to share your pipeline run results with other team members or stakeholders inside or outside your organization
* if you have other components in your stack that are running remotely (e.g. a Kubeflow or Kubernetes Orchestrator running in a public cloud).
* if you outgrow what your local machine can offer in terms of storage space and need to use some form of private or public storage service that is shared with others
* if you are running pipelines at scale and need an Artifact Store that can handle the demands of production-grade MLOps

In all these cases, you need an Artifact Store that is backed by a form of public cloud or self-hosted shared object storage service.

You should use the Azure Artifact Store when you decide to keep your ZenML artifacts in a shared object storage and if you have access to the Azure Blob Storage managed service. You should consider one of the other [Artifact Store flavors](./#artifact-store-flavors) if you don't have access to the Azure Blob Storage service.

### How do you deploy it?

{% hint style="info" %}
Would you like to skip ahead and deploy a full ZenML cloud stack already, including an Azure Artifact Store? Check out the[in-browser stack deployment wizard](https://docs.zenml.io/how-to/infrastructure-deployment/stack-deployment/deploy-a-cloud-stack), the [stack registration wizard](https://docs.zenml.io/how-to/infrastructure-deployment/stack-deployment/register-a-cloud-stack), or [the ZenML Azure Terraform module](https://docs.zenml.io/how-to/infrastructure-deployment/stack-deployment/deploy-a-cloud-stack-with-terraform) for a shortcut on how to deploy & register this stack component.
{% endhint %}

The Azure Artifact Store flavor is provided by the Azure ZenML integration, you need to install it on your local machine to be able to register an Azure Artifact Store and add it to your stack:

```shell
zenml integration install azure -y
```

The only configuration parameter mandatory for registering an Azure Artifact Store is the root path URI, which needs to point to an Azure Blog Storage container and take the form `az://container-name` or `abfs://container-name`. Please read [the Azure Blob Storage documentation](https://docs.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-portal) on how to configure an Azure Blob Storage container.

With the URI to your Azure Blob Storage container known, registering an Azure Artifact Store can be done as follows:

```shell
# Register the Azure artifact store
zenml artifact-store register az_store -f azure --path=az://container-name

# Register and set a stack with the new artifact store
zenml stack register custom_stack -a az_store ... --set
```

Depending on your use case, however, you may also need to provide additional configuration parameters pertaining to [authentication](azure.md#authentication-methods) to match your deployment scenario.

#### Authentication Methods

Integrating and using an Azure Artifact Store in your pipelines is not possible without employing some form of authentication. If you're looking for a quick way to get started locally, you can use the _Implicit Authentication_ method. However, the recommended way to authenticate to the Azure cloud platform is through [an Azure Service Connector](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/azure-service-connector). This is particularly useful if you are configuring ZenML stacks that combine the Azure Artifact Store with other remote stack components also running in Azure.

You will need the following information to configure Azure credentials for ZenML, depending on which type of Azure credentials you want to use:

* an Azure connection string
* an Azure account key
* the client ID, client secret and tenant ID of the Azure service principal

For more information on how to retrieve information about your Azure Storage Account and Access Key or connection string, please refer to this [Azure guide](https://docs.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-python?tabs=environment-variable-windows#copy-your-credentials-from-the-azure-portal).

For information on how to configure an Azure service principal, please consult the [Azure documentation](https://docs.microsoft.com/en-us/azure/active-directory/develop/howto-create-service-principal-portal).

{% tabs %}
{% tab title="Implicit Authentication" %}
This method uses the implicit Azure authentication available _in the environment where the ZenML code is running_. On your local machine, this is the quickest way to configure an Azure Artifact Store. You don't need to supply credentials explicitly when you register the Azure Artifact Store, instead, you have to set one of the following sets of environment variables:

* to use [an Azure storage account key](https://learn.microsoft.com/en-us/azure/storage/common/storage-account-keys-manage) , set `AZURE_STORAGE_ACCOUNT_NAME` to your account name and one of `AZURE_STORAGE_ACCOUNT_KEY` or `AZURE_STORAGE_SAS_TOKEN` to the Azure key value.
* to use [an Azure storage account key connection string](https://learn.microsoft.com/en-us/azure/storage/common/storage-account-keys-manage) , set `AZURE_STORAGE_CONNECTION_STRING` to your Azure Storage Key connection string
* to use [Azure Service Principal credentials](https://learn.microsoft.com/en-us/azure/active-directory/develop/app-objects-and-service-principals) , [create an Azure Service Principal](https://learn.microsoft.com/en-us/azure/active-directory/develop/howto-create-service-principal-portal) and then set `AZURE_STORAGE_ACCOUNT_NAME` to your account name and `AZURE_STORAGE_CLIENT_ID` , `AZURE_STORAGE_CLIENT_SECRET` and `AZURE_STORAGE_TENANT_ID` to the client ID, secret and tenant ID of your service principal

{% hint style="warning" %}
Certain dashboard functionality, such as visualizing or deleting artifacts, is not available when using an implicitly authenticated artifact store together with a deployed ZenML server because the ZenML server will not have permission to access the filesystem.

The implicit authentication method also needs to be coordinated with other stack components that are highly dependent on the Artifact Store and need to interact with it directly to the function. If these components are not running on your machine, they do not have access to the local environment variables and will encounter authentication failures while trying to access the Azure Artifact Store:

* [Orchestrators](https://docs.zenml.io/stacks/orchestrators/) need to access the Artifact Store to manage pipeline artifacts
* [Step Operators](https://docs.zenml.io/stacks/step-operators/) need to access the Artifact Store to manage step-level artifacts
* [Model Deployers](https://docs.zenml.io/stacks/model-deployers/) need to access the Artifact Store to load served models

To enable these use cases, it is recommended to use [an Azure Service Connector](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/azure-service-connector) to link your Azure Artifact Store to the remote Azure Blob storage container.
{% endhint %}
{% endtab %}

{% tab title="Azure Service Connector (recommended)" %}
To set up the Azure Artifact Store to authenticate to Azure and access an Azure Blob storage container, it is recommended to leverage the many features provided by [the Azure Service Connector](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/azure-service-connector) such as auto-configuration, best security practices regarding long-lived credentials and reusing the same credentials across multiple stack components.

If you don't already have an Azure Service Connector configured in your ZenML deployment, you can register one using the interactive CLI command. You have the option to configure an Azure Service Connector that can be used to access more than one Azure blob storage container or even more than one type of Azure resource:

```sh
zenml service-connector register --type azure -i
```

A non-interactive CLI example that uses [Azure Service Principal credentials](https://learn.microsoft.com/en-us/azure/active-directory/develop/app-objects-and-service-principals) to configure an Azure Service Connector targeting a single Azure Blob storage container is:

```sh
zenml service-connector register <CONNECTOR_NAME> --type azure --auth-method service-principal --tenant_id=<AZURE_TENANT_ID> --client_id=<AZURE_CLIENT_ID> --client_secret=<AZURE_CLIENT_SECRET> --resource-type blob-container --resource-id <BLOB_CONTAINER_NAME>
```

{% code title="Example Command Output" %}
```
$ zenml service-connector register azure-blob-demo --type azure --auth-method service-principal --tenant_id=a79f3633-8f45-4a74-a42e-68871c17b7fb --client_id=8926254a-8c3f-430a-a2fd-bdab234d491e --client_secret=AzureSuperSecret --resource-type blob-container --resource-id az://demo-zenmlartifactstore
Successfully registered service connector `azure-blob-demo` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃   RESOURCE TYPE   │ RESOURCE NAMES               ┃
┠───────────────────┼──────────────────────────────┨
┃ 📦 blob-container │ az://demo-zenmlartifactstore ┃
┗━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

> **Note**: Please remember to grant the Azure service principal permissions to read and write to your Azure Blob storage container as well as to list accessible storage accounts and Blob containers. For a full list of permissions required to use an AWS Service Connector to access one or more S3 buckets, please refer to the [Azure Service Connector Blob storage container resource type documentation](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/azure-service-connector#azure-blob-storage-container) or read the documentation available in the interactive CLI commands and dashboard. The Azure Service Connector supports [many different authentication methods](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/azure-service-connector#authentication-methods) with different levels of security and convenience. You should pick the one that best fits your use-case.

If you already have one or more Azure Service Connectors configured in your ZenML deployment, you can check which of them can be used to access the Azure Blob storage container you want to use for your Azure Artifact Store by running e.g.:

```sh
zenml service-connector list-resources --resource-type blob-container
```

{% code title="Example Command Output" %}
```
The following 'blob-container' resources can be accessed by service connectors:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME          │ CONNECTOR TYPE │ RESOURCE TYPE     │ RESOURCE NAMES               ┃
┠──────────────────────────────────────┼─────────────────────────┼────────────────┼───────────────────┼──────────────────────────────┨
┃ 273d2812-2643-4446-82e6-6098b8ccdaa4 │ azure-service-principal │ 🇦  azure       │ 📦 blob-container │ az://demo-zenmlartifactstore ┃
┠──────────────────────────────────────┼─────────────────────────┼────────────────┼───────────────────┼──────────────────────────────┨
┃ f6b329e1-00f7-4392-94c9-264119e672d0 │ azure-blob-demo         │ 🇦  azure       │ 📦 blob-container │ az://demo-zenmlartifactstore ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

After having set up or decided on an Azure Service Connector to use to connect to the target Azure Blob storage container, you can register the Azure Artifact Store as follows:

```sh
# Register the Azure artifact-store and reference the target blob storage container
zenml artifact-store register <AZURE_STORE_NAME> -f azure \
    --path='az://your-container'

# Connect the Azure artifact-store to the target container via an Azure Service Connector
zenml artifact-store connect <AZURE_STORE_NAME> -i
```

A non-interactive version that connects the Azure Artifact Store to a target blob storage container through an Azure Service Connector:

```sh
zenml artifact-store connect <S3_STORE_NAME> --connector <CONNECTOR_ID>
```

{% code title="Example Command Output" %}
```
$ zenml artifact-store connect azure-blob-demo --connector azure-blob-demo
Successfully connected artifact store `azure-blob-demo` to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME  │ CONNECTOR TYPE │ RESOURCE TYPE     │ RESOURCE NAMES               ┃
┠──────────────────────────────────────┼─────────────────┼────────────────┼───────────────────┼──────────────────────────────┨
┃ f6b329e1-00f7-4392-94c9-264119e672d0 │ azure-blob-demo │ 🇦  azure       │ 📦 blob-container │ az://demo-zenmlartifactstore ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

As a final step, you can use the Azure Artifact Store in a ZenML Stack:

```sh
# Register and set a stack with the new artifact store
zenml stack register <STACK_NAME> -a <AZURE_STORE_NAME> ... --set
```
{% endtab %}

{% tab title="ZenML Secret" %}
When you register the Azure Artifact Store, you can create a [ZenML Secret](https://docs.zenml.io/getting-started/deploying-zenml/secret-management) to store a variety of Azure credentials and then reference it in the Artifact Store configuration:

* to use [an Azure storage account key](https://learn.microsoft.com/en-us/azure/storage/common/storage-account-keys-manage) , set `account_name` to your account name and one of `account_key` or `sas_token` to the Azure key or SAS token value as attributes in the ZenML secret
* to use [an Azure storage account key connection string](https://learn.microsoft.com/en-us/azure/storage/common/storage-account-keys-manage) , configure the `connection_string` attribute in the ZenML secret to your Azure Storage Key connection string
* to use [Azure Service Principal credentials](https://learn.microsoft.com/en-us/azure/active-directory/develop/app-objects-and-service-principals) , [create an Azure Service Principal](https://learn.microsoft.com/en-us/azure/active-directory/develop/howto-create-service-principal-portal) and then set `account_name` to your account name and `client_id`, `client_secret` and `tenant_id` to the client ID, secret and tenant ID of your service principal in the ZenML secret

This method has some advantages over the implicit authentication method:

* you don't need to install and configure the Azure CLI on your host
* you don't need to care about enabling your other stack components (orchestrators, step operators and model deployers) to have access to the artifact store through Azure Managed Identities
* you can combine the Azure artifact store with other stack components that are not running in Azure

Configuring Azure credentials in a ZenML secret and then referencing them in the Artifact Store configuration could look like this:

```shell
# Store the Azure storage account key in a ZenML secret
zenml secret create az_secret \
    --account_name='<YOUR_AZURE_ACCOUNT_NAME>' \
    --account_key='<YOUR_AZURE_ACCOUNT_KEY>'

# or if you want to use a connection string
zenml secret create az_secret \
    --connection_string='<YOUR_AZURE_CONNECTION_STRING>'

# or if you want to use Azure ServicePrincipal credentials
zenml secret create az_secret \
    --account_name='<YOUR_AZURE_ACCOUNT_NAME>' \
    --tenant_id='<YOUR_AZURE_TENANT_ID>' \
    --client_id='<YOUR_AZURE_CLIENT_ID>' \
    --client_secret='<YOUR_AZURE_CLIENT_SECRET>'

# Alternatively for providing key-value pairs, you can utilize the '--values' option by specifying a file path containing 
# key-value pairs in either JSON or YAML format.
# File content example: {"account_name":"<YOUR_AZURE_ACCOUNT_NAME>",...}
zenml secret create az_secret \
    --values=@path/to/file.txt

# Register the Azure artifact store and reference the ZenML secret
zenml artifact-store register az_store -f azure \
    --path='az://your-container' \
    --authentication_secret=az_secret

# Register and set a stack with the new artifact store
zenml stack register custom_stack -a az_store ... --set
```
{% endtab %}
{% endtabs %}

For more, up-to-date information on the Azure Artifact Store implementation and its configuration, you can have a look at [the SDK docs](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-azure.html#zenml.integrations.azure) .

### How do you use it?

Aside from the fact that the artifacts are stored in Azure Blob Storage, using the Azure Artifact Store is no different from [using any other flavor of Artifact Store](./#how-to-use-it).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
