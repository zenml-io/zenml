---
description: Store artifacts using Azure Blob Storage
---

The Azure Artifact Store is an [Artifact Store](./overview.md) flavor provided with
the Azure ZenML integration that uses [the Azure Blob Storage managed object storage service](https://azure.microsoft.com/en-us/services/storage/blobs/)
to store ZenML artifacts in a Azure Blob Storage container.

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
Storage managed service.
You should consider one of the other [Artifact Store flavors](./overview.md#artifact-store-flavors)
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

{% hint style="info" %}
Configuring an Azure Artifact Store in can be a complex and error prone process,
especially if you plan on using it alongside other stack components running in
the Azure cloud. You might consider referring to the [ZenML Cloud Guide](../../cloud-guide/overview.md)
for a more holistic approach to configuring full Azure-based stacks for ZenML.
{% endhint %}

### Authentication Methods

Integrating and using an Azure Artifact Store in your pipelines is not
possible without employing some form of authentication. ZenML currently provides
two options for configuring Azure credentials, the recommended one being to use
a [Secrets Manager](#secrets-manager-recommended) in your stack to store the
sensitive information in a secure location.

You will need the following information to configure Azure credentials for
ZenML, depending on which type of Azure credentials you want to use:

* an Azure connection string
* an Azure acount key
* the client ID, client secret and tenant ID of the Azure service principle

For more information on how to retrieve information about your Azure Storage
Account and Access Key or connection string, please refer to this
[Azure guide](https://docs.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-python?tabs=environment-variable-windows#copy-your-credentials-from-the-azure-portal).

For information on how to configure an Azure service principle, please consult
the [Azure documentation](https://docs.microsoft.com/en-us/azure/active-directory/develop/howto-create-service-principal-portal).

{% tabs %}
{% tab title="Implicit Authentication" %}

This method uses the implicit Azure authentication available _in the environment
where the ZenML code is running_. On your local machine, this is the quickest
way to configure an Azure Artifact Store. You don't need to supply credentials
explicitly when you register the Azure Artifact Store, instead you have to set
one of the following sets of environment variables:

* to use an Azure connection string, set `AZURE_STORAGE_CONNECTION_STRING` to
your Azure Storage Key connection string
* to use an Azure account key, set `AZURE_STORAGE_ACCOUNT_NAME` to your account
name and one of `AZURE_STORAGE_ACCOUNT_KEY` or `AZURE_STORAGE_SAS_TOKEN` to the
Azure key value.
* to use Azure ServicePrincipal credentials, set `AZURE_STORAGE_ACCOUNT_NAME` to
your account name and `AZURE_STORAGE_CLIENT_ID`, `AZURE_STORAGE_CLIENT_SECRET`
and `AZURE_STORAGE_TENANT_ID` to the 

{% hint style="warning" %}
The implicit authentication method needs to be coordinated with other stack
components that are highly dependent on the Artifact Store and need to interact
with it directly to function. If these components are not running on your
machine, they do not have access to the local environment variables and
will encounter authentication failures while trying to access the Azure Artifact
Store:

* [Orchestrators](../orchestrators/overview.md) need to access the Artifact
Store to manage pipeline artifacts
* [Step Operators](../step_operators/overview.md) need to access the Artifact
Store to manage step level artifacts
* [Model Deployers](../model_deployers/overview.md) need to access the Artifact
Store to load served models

These remote stack components can still use the implicit authentication method:
if they are also running within the Azure Kubenetes Service, you can configure
your cluster to use [Azure Managed Identities](https://docs.microsoft.com/en-us/azure/aks/use-managed-identity).
This mechanism allows Azure workloads like AKS pods to access other Azure
services without requiring explicit credentials.

If you have remote stack components that are not running in AKS, or if
you are unsure how to configure them to use Managed Identities, you should use
one of the other authentication methods.
{% endhint %}

{% endtab %}

{% tab title="Secrets Manager (Recommended)" %}

This method requires using a [Secrets Manager](../secrets_managers/overview.md)
in your stack to store the sensitive Azure authentication information in a secure
location and configuring the Azure credentials using a ZenML secret.

The ZenML Azure secret schema supports a variety of credentials:

* use an Azure account name and access key or SAS token (the `account_name`,
`account_key` and `sas_token` attributes need to be configured in the ZenML
secret)
* use an Azure connection string (configure the `connection_string` attribute in
the ZenML secret)
* use Azure ServicePrincipal credentials (which requires `account_name`,
`tenant_id`, `client_id` and `client_secret` to be configured in the ZenML
secret)

The Azure credentials are configured as a ZenML secret that is referenced in the
Artifact Store configuration, e.g.:

```shell
# Register the Azure artifact store
zenml artifact-store register az_store -f azure \
    --path='az://your-container' \
    --authentication_secret=az_secret

# Register a secrets manager
zenml secrets-manager register secrets_manager \
    --flavor=<FLAVOR_OF_YOUR_CHOICE> ...

# Register and set a stack with the new artifact store and secrets manager
zenml stack register custom_stack -a az_store -x secrets_manager ... --set

# Create the secret referenced in the artifact store
zenml secret register az_secret -s azure \
    --connection_sting='your-Azure-connection-string'
```

{% endtab %}
{% endtabs %}

For more, up-to-date information on the Azure Artifact Store implementation and
its configuration, you can have a look at [the API docs](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.azure.artifact_stores).

## How do you use it?

Aside from the fact that the artifacts are stored in Azure Blob Storage,
using the Azure Artifact Store is no different than [using any other flavor of Artifact Store](./overview.md#how-to-use-it).
