---
description: How to store artifacts using Azure Blob Storage
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


The Azure Artifact Store is an [Artifact Store](./artifact-stores.md) flavor 
provided with the Azure ZenML integration that uses[the Azure Blob Storage managed object storage service](https://azure.microsoft.com/en-us/services/storage/blobs/)
to store ZenML artifacts in an Azure Blob Storage container.

## When would you want to use it?

Running ZenML pipelines with [the local Artifact Store](./local.md) is usually
sufficient if you just want to evaluate ZenML or get started quickly without
incurring the trouble and the cost of employing cloud storage services in your
stack. However, the local Artifact Store becomes insufficient or unsuitable if
you have more elaborate needs for your project:

* if you want to share your pipeline run results with other team members or
stakeholders inside or outside your organization
* if you have other components in your stack that are running remotely (e.g. a
Kubeflow or Kubernetes Orchestrator running in public cloud).
* if you outgrow what your local machine can offer in terms of storage space and
need to use some form of private or public storage service that is shared with
others
* if you are running pipelines at scale and need an Artifact Store that can
handle the demands of production grade MLOps

In all these cases, you need an Artifact Store that is backed by a form of
public cloud or self-hosted shared object storage service.

You should use the Azure Artifact Store when you decide to keep your ZenML
artifacts in a shared object storage and if you have access to the Azure Blob
Storage managed service. You should consider one of the other 
[Artifact Store flavors](./artifact-stores.md#artifact-store-flavors)
if you don't have access to the Azure Blob Storage service.

## How do you deploy it?

The Azure Artifact Store flavor is provided by the Azure ZenML integration, you
need to install it on your local machine to be able to register an Azure
Artifact Store and add it to your stack:

```shell
zenml integration install azure -y
```

The only configuration parameter mandatory for registering an Azure Artifact
Store is the root path URI, which needs to point to an Azure Blog Storage
container and takes the form `az://container-name` or `abfs://container-name`.
Please read [the Azure Blob Storage documentation](https://docs.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-portal)
on how to configure an Azure Blob Storage container.

With the URI to your Azure Blob Storage container known, registering an Azure
Artifact Store can be done as follows:

```shell
# Register the Azure artifact store
zenml artifact-store register az_store -f azure --path=az://container-name

# Register and set a stack with the new artifact store
zenml stack register custom_stack -a az_store ... --set
```

Depending on your use-case, however, you may also need to provide additional
configuration parameters pertaining to [authentication](#authentication-methods)
to match your deployment scenario.

### Authentication Methods

Integrating and using an Azure Artifact Store in your pipelines is not
possible without employing some form of authentication. ZenML currently provides
two options for managing Azure authentication: one for which you don't need to
manage credentials explicitly, the other one that requires you to generate
Azure credentials and store them in a
[ZenML Secret](../../starter-guide/production-fundamentals/secrets-management.md). Each
method has advantages and disadvantages, and you should choose the one that
best suits your use-case. If you're looking for a quick way to get started
locally, we recommend using the *Implicit Authentication* method. However, if
you would like to experiment with ZenML stacks that combine the Azure Artifact
Store with other remote stack components, we recommend using the
*Azure Credentials* method, especially if you don't have a lot of experience
with Azure Managed Identities.

You will need the following information to configure Azure credentials for
ZenML, depending on which type of Azure credentials you want to use:

* an Azure connection string
* an Azure account key
* the client ID, client secret and tenant ID of the Azure service principal

For more information on how to retrieve information about your Azure Storage
Account and Access Key or connection string, please refer to this
[Azure guide](https://docs.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-python?tabs=environment-variable-windows#copy-your-credentials-from-the-azure-portal).

For information on how to configure an Azure service principal, please consult
the [Azure documentation](https://docs.microsoft.com/en-us/azure/active-directory/develop/howto-create-service-principal-portal).

{% tabs %}
{% tab title="Implicit Authentication" %}

This method uses the implicit Azure authentication available _in the environment
where the ZenML code is running_. On your local machine, this is the quickest
way to configure an Azure Artifact Store. You don't need to supply credentials
explicitly when you register the Azure Artifact Store, instead you have to set
one of the following sets of environment variables:

* to use [an Azure storage account key](https://learn.microsoft.com/en-us/azure/storage/common/storage-account-keys-manage),
set `AZURE_STORAGE_ACCOUNT_NAME` to your account name and one of
`AZURE_STORAGE_ACCOUNT_KEY` or `AZURE_STORAGE_SAS_TOKEN` to the Azure key value.
* to use [an Azure storage account key connection string](https://learn.microsoft.com/en-us/azure/storage/common/storage-account-keys-manage),
set `AZURE_STORAGE_CONNECTION_STRING` to your Azure Storage Key connection
string
* to use [Azure Service Principal credentials](https://learn.microsoft.com/en-us/azure/active-directory/develop/app-objects-and-service-principals),
[create an Azure Service Principal](https://learn.microsoft.com/en-us/azure/active-directory/develop/howto-create-service-principal-portal)
and then set set `AZURE_STORAGE_ACCOUNT_NAME` to your account name and
`AZURE_STORAGE_CLIENT_ID`, `AZURE_STORAGE_CLIENT_SECRET` and
`AZURE_STORAGE_TENANT_ID` to the client ID, secret and tenant ID of your
service principal

{% hint style="warning" %}
Certain dashboard functionality, such as visualizing or deleting artifacts, is
not available when using an implicitly authenticated artifact store together 
with a deployed ZenML server because the ZenML server will not have permissions
to access the filesystem.

The implicit authentication method also needs to be coordinated with other stack
components that are highly dependent on the Artifact Store and need to interact
with it directly to function. If these components are not running on your
machine, they do not have access to the local environment variables and
will encounter authentication failures while trying to access the Azure Artifact
Store:

* [Orchestrators](../orchestrators/orchestrators.md) need to access the 
Artifact Store to manage pipeline artifacts
* [Step Operators](../step-operators/step-operators.md) need to access the 
Artifact Store to manage step level artifacts
* [Model Deployers](../model-deployers/model-deployers.md) need to access the 
Artifact Store to load served models

These remote stack components can still use the implicit authentication method:
if they are also running within the Azure Kubernetes Service, you can configure
your cluster to use [Azure Managed Identities](https://docs.microsoft.com/en-us/azure/aks/use-managed-identity).
This mechanism allows Azure workloads like AKS pods to access other Azure
services without requiring explicit credentials.

If you have remote stack components that are not running in Azure, or if
you are unsure how to configure them to use Managed Identities, you should use
one of the other authentication methods.
{% endhint %}

{% endtab %}

{% tab title="Azure Credentials" %}

When you register the Azure Artifact Store, you can create a
[ZenML Secret](../../starter-guide/production-fundamentals/secrets-management.md)
to store a variety of Azure credentials and then reference it in the Artifact
Store configuration:

* to use [an Azure storage account key](https://learn.microsoft.com/en-us/azure/storage/common/storage-account-keys-manage),
set `account_name` to your account name and one of `account_key` or `sas_token`
to the Azure key or SAS token value as attributes in the ZenML secret
* to use [an Azure storage account key connection string](https://learn.microsoft.com/en-us/azure/storage/common/storage-account-keys-manage),
configure the `connection_string` attribute in the ZenML secret to your Azure
Storage Key connection string
* to use [Azure Service Principal credentials](https://learn.microsoft.com/en-us/azure/active-directory/develop/app-objects-and-service-principals),
[create an Azure Service Principal](https://learn.microsoft.com/en-us/azure/active-directory/develop/howto-create-service-principal-portal)
and then set `account_name` to your account name and `client_id`,
`client_secret` and `tenant_id` to the client ID, secret and tenant ID of your
service principal in the ZenML secret

This method has some advantages over the implicit authentication method:

* you don't need to install and configure the Azure CLI on your host
* you don't need to care about enabling your other stack components
(orchestrators, step operators and model deployers) to have access to the
artifact store through Azure Managed Identities
* you can combine the Azure artifact store with other stack components that are
not running in Azure

Configuring Azure credentials in a ZenML secret and then referencing them in the
Artifact Store configuration could look like this:

```shell
# Store the Azure storage account key in a ZenML secret
zenml secret create az_secret \
    --account_name='<YOUR_AZURE_ACCOUNT_NAME>' \
    --account_key='<YOUR_AZURE_ACCOUNT_KEY>' \

# or if you want to use a connection string
zenml secret create az_secret \
    --connection_string='<YOUR_AZURE_CONNECTION_STRING>'

# or if you want to use Azure ServicePrincipal credentials
zenml secret create az_secret \
    --account_name='<YOUR_AZURE_ACCOUNT_NAME>' \
    --tenant_id='<YOUR_AZURE_TENANT_ID>' \
    --client_id='<YOUR_AZURE_CLIENT_ID>' \
    --client_secret='<YOUR_AZURE_CLIENT_SECRET>'

# Register the Azure artifact store and reference the ZenML secret
zenml artifact-store register az_store -f azure \
    --path='az://your-container' \
    --authentication_secret=az_secret

# Register and set a stack with the new artifact store
zenml stack register custom_stack -a az_store ... --set
```

{% endtab %}
{% endtabs %}

For more, up-to-date information on the Azure Artifact Store implementation and
its configuration, you can have a look at [the API docs](https://apidocs.zenml.io/latest/integration_code_docs/integrations-azure/#zenml.integrations.azure.artifact_stores).

## How do you use it?

Aside from the fact that the artifacts are stored in Azure Blob Storage,
using the Azure Artifact Store is no different from [using any other flavor of Artifact Store](./artifact-stores.md#how-to-use-it).
