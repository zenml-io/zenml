---
description: Storing container images in Azure.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Azure Container Registry

The Azure container registry is a [container registry](./container-registries.md) flavor that comes built-in with ZenML and uses the [Azure Container Registry](https://azure.microsoft.com/en-us/services/container-registry/) to store container images.

### When to use it

You should use the Azure container registry if:

* one or more components of your stack need to pull or push container images.
* you have access to Azure. If you're not using Azure, take a look at the other [container registry flavors](./container-registries.md#container-registry-flavors).

### How to deploy it

{% hint style="info" %}
Would you like to skip ahead and deploy a full ZenML cloud stack already,
including an Azure container registry? Check out the
[in-browser stack deployment wizard](../../how-to/stack-deployment/deploy-a-cloud-stack.md),
the [stack registration wizard](../../how-to/stack-deployment/register-a-cloud-stack.md),
or [the ZenML Azure Terraform module](../../how-to/stack-deployment/deploy-a-cloud-stack-with-terraform.md)
for a shortcut on how to deploy & register this stack component.
{% endhint %}

Go [here](https://portal.azure.com/#create/Microsoft.ContainerRegistry) and choose a subscription, resource group, location, and registry name. Then click on `Review + Create` and to create your container registry.

### How to find the registry URI

The Azure container registry URI should have the following format:

```shell
<REGISTRY_NAME>.azurecr.io
# Examples:
zenmlregistry.azurecr.io
myregistry.azurecr.io
```

To figure out the URI for your registry:

* Go to the [Azure portal](https://portal.azure.com/#home).
* In the search bar, enter `container registries` and select the container registry you want to use. If you don't have any container registries yet, check out the [deployment section](azure.md#how-to-deploy-it) on how to create one.
* Use the name of your registry to fill the template `<REGISTRY_NAME>.azurecr.io` and get your URI.

### How to use it

To use the Azure container registry, we need:

* [Docker](https://www.docker.com) installed and running.
* The registry URI. Check out the [previous section](azure.md#how-to-find-the-registry-uri) on the URI format and how to get the URI for your registry.

We can then register the container registry and use it in our active stack:

```shell
zenml container-registry register <NAME> \
    --flavor=azure \
    --uri=<REGISTRY_URI>

# Add the container registry to the active stack
zenml stack update -c <NAME>
```

You also need to set up [authentication](azure.md#authentication-methods) required to log in to the container registry.

#### Authentication Methods

Integrating and using an Azure Container Registry in your pipelines is not possible without employing some form of authentication. If you're looking for a quick way to get started locally, you can use the _Local Authentication_ method. However, the recommended way to authenticate to the Azure cloud platform is through [an Azure Service Connector](../../how-to/auth-management/azure-service-connector.md). This is particularly useful if you are configuring ZenML stacks that combine the Azure Container Registry with other remote stack components also running in Azure.

{% tabs %}
{% tab title="Local Authentication" %}
This method uses the Docker client authentication available _in the environment where the ZenML code is running_. On your local machine, this is the quickest way to configure an Azure Container Registry. You don't need to supply credentials explicitly when you register the Azure Container Registry, as it leverages the local credentials and configuration that the Azure CLI and Docker client store on your local machine. However, you will need to install and set up the Azure CLI on your machine as a prerequisite, as covered in [the Azure CLI documentation](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli), before you register the Azure Container Registry.

With the Azure CLI installed and set up with credentials, you need to login to the container registry so Docker can pull and push images:

```shell
# Fill your REGISTRY_NAME in the placeholder in the following command.
# You can find the REGISTRY_NAME as part of your registry URI: `<REGISTRY_NAME>.azurecr.io`
az acr login --name=<REGISTRY_NAME>
```

{% hint style="warning" %}
Stacks using the Azure Container Registry set up with local authentication are not portable across environments. To make ZenML pipelines fully portable, it is recommended to use [an Azure Service Connector](../../how-to/auth-management/azure-service-connector.md) to link your Azure Container Registry to the remote ACR registry.
{% endhint %}
{% endtab %}

{% tab title="Azure Service Connector (recommended)" %}
To set up the Azure Container Registry to authenticate to Azure and access an ACR registry, it is recommended to leverage the many features provided by [the Azure Service Connector](../../how-to/auth-management/azure-service-connector.md) such as auto-configuration, local login, best security practices regarding long-lived credentials and reusing the same credentials across multiple stack components.

If you don't already have an Azure Service Connector configured in your ZenML deployment, you can register one using the interactive CLI command. You have the option to configure an Azure Service Connector that can be used to access a ACR registry or even more than one type of Azure resource:

```sh
zenml service-connector register --type azure -i
```

A non-interactive CLI example that uses [Azure Service Principal credentials](https://learn.microsoft.com/en-us/azure/active-directory/develop/app-objects-and-service-principals) to configure an Azure Service Connector targeting a single ACR registry is:

```sh
zenml service-connector register <CONNECTOR_NAME> --type azure --auth-method service-principal --tenant_id=<AZURE_TENANT_ID> --client_id=<AZURE_CLIENT_ID> --client_secret=<AZURE_CLIENT_SECRET> --resource-type docker-registry --resource-id <REGISTRY_URI>
```

{% code title="Example Command Output" %}
```
$ zenml service-connector register azure-demo --type azure --auth-method service-principal --tenant_id=a79f3633-8f45-4a74-a42e-68871c17b7fb --client_id=8926254a-8c3f-430a-a2fd-bdab234d491e --client_secret=AzureSuperSecret --resource-type docker-registry --resource-id demozenmlcontainerregistry.azurecr.io
⠸ Registering service connector 'azure-demo'...
Successfully registered service connector `azure-demo` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃   RESOURCE TYPE    │ RESOURCE NAMES                        ┃
┠────────────────────┼───────────────────────────────────────┨
┃ 🐳 docker-registry │ demozenmlcontainerregistry.azurecr.io ┃
┗━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

> **Note**: Please remember to grant the entity associated with your Azure credentials permissions to read and write to your ACR registry as well as to list accessible ACR registries. For a full list of permissions required to use an Azure Service Connector to access a ACR registry, please refer to the [Azure Service Connector ACR registry resource type documentation](../../how-to/auth-management/azure-service-connector.md#acr-container-registry) or read the documentation available in the interactive CLI commands and dashboard. The Azure Service Connector supports [many different authentication methods](../../how-to/auth-management/azure-service-connector.md#authentication-methods) with different levels of security and convenience. You should pick the one that best fits your use case.

If you already have one or more Azure Service Connectors configured in your ZenML deployment, you can check which of them can be used to access the ACR registry you want to use for your Azure Container Registry by running e.g.:

```sh
zenml service-connector list-resources --connector-type azure --resource-type docker-registry
```

{% code title="Example Command Output" %}
```
The following 'docker-registry' resources can be accessed by 'azure' service connectors configured in your workspace:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE      │ RESOURCE NAMES                        ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼────────────────────┼───────────────────────────────────────┨
┃ db5821d0-a658-4504-ae96-04c3302d8f85 │ azure-demo     │ 🇦 azure       │ 🐳 docker-registry │ demozenmlcontainerregistry.azurecr.io ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

After having set up or decided on an Azure Service Connector to use to connect to the target ACR registry, you can register the Azure Container Registry as follows:

```sh
# Register the Azure container registry and reference the target ACR registry URI
zenml container-registry register <CONTAINER_REGISTRY_NAME> -f azure \
    --uri=<REGISTRY_URL>

# Connect the Azure container registry to the target ACR registry via an Azure Service Connector
zenml container-registry connect <CONTAINER_REGISTRY_NAME> -i
```

A non-interactive version that connects the Azure Container Registry to a target ACR registry through an Azure Service Connector:

```sh
zenml container-registry connect <CONTAINER_REGISTRY_NAME> --connector <CONNECTOR_ID>
```

{% code title="Example Command Output" %}
```
$ zenml container-registry connect azure-demo --connector azure-demo
Successfully connected container registry `azure-demo` to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE      │ RESOURCE NAMES                        ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼────────────────────┼───────────────────────────────────────┨
┃ db5821d0-a658-4504-ae96-04c3302d8f85 │ azure-demo     │ 🇦  azure       │ 🐳 docker-registry │ demozenmlcontainerregistry.azurecr.io ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

As a final step, you can use the Azure Container Registry in a ZenML Stack:

```sh
# Register and set a stack with the new container registry
zenml stack register <STACK_NAME> -c <CONTAINER_REGISTRY_NAME> ... --set
```

{% hint style="info" %}
Linking the Azure Container Registry to a Service Connector means that your local Docker client is no longer authenticated to access the remote registry. If you need to manually interact with the remote registry via the Docker CLI, you can use the [local login Service Connector feature](../../how-to/auth-management/service-connectors-guide.md#configure-local-clients) to temporarily authenticate your local Docker client to the remote registry:

```sh
zenml service-connector login <CONNECTOR_NAME> --resource-type docker-registry --resource-id <CONTAINER_REGISTRY_URI>
```

{% code title="Example Command Output" %}
```
$ zenml service-connector login azure-demo --resource-type docker-registry --resource-id demozenmlcontainerregistry.azurecr.io
⠹ Attempting to configure local client using service connector 'azure-demo'...
WARNING! Your password will be stored unencrypted in /home/stefan/.docker/config.json.
Configure a credential helper to remove this warning. See
https://docs.docker.com/engine/reference/commandline/login/#credentials-store

The 'azure-demo' Docker Service Connector connector was used to successfully configure the local Docker/OCI container registry client/SDK.
```
{% endcode %}
{% endhint %}
{% endtab %}
{% endtabs %}

For more information and a full list of configurable attributes of the Azure container registry, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/core\_code\_docs/core-container\_registries/#zenml.container\_registries.azure\_container\_registry.AzureContainerRegistry) .

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
