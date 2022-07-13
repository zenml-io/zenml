---
description: Store container images in Azure
---

The Azure container registry is a [container registry](./overview.md) flavor which comes built-in with 
ZenML and uses the [Azure Container Registry](https://azure.microsoft.com/en-us/services/container-registry/)
to store container images.

## When to use it

You should use the Azure container registry if:
* one or more components of your stack need to pull or push container images.
* you have access to Azure. If you're not using Azure, take a look at the
 other [container registry flavors](./overview.md#container-registry-flavors).

## How to deploy it

Go [here](https://portal.azure.com/#create/Microsoft.ContainerRegistry) and 
choose a subscription, resource group, location and registry name. Then click on
`Review + Create` and to create your container registry.

## How to find the registry URI

The Azure container registry URI should have the following format:
```shell
<REGISTRY_NAME>.azurecr.io
# Examples:
zenmlregistry.azurecr.io
myregistry.azurecr.io
```

To figure our the URI for your registry:
* Go to the [Azure portal](https://portal.azure.com/#home).
* In the search bar, enter `container registries` and select the container 
registry you want to use. If you don't have any container registries yet, check out the 
[deployment section](#how-do-you-deploy-it) on how to create one.
* Use the name of your registry to fill the template `<REGISTRY_NAME>.azurecr.io` and get your URI.
## How to use it

To use the Azure container registry, we need:
* [Docker](https://www.docker.com) installed and running.
* The [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli) installed and authenticated.
* The registry URI. Check out the [previous section](#uri-format) on the URI format and how
to get the URI for your registry.

We can then register the container registry and use it in our active stack:
```shell
zenml container-registry register <NAME> \
    --flavor=azure \
    --uri=<REGISTRY_URI>

# Add the container registry to the active stack
zenml stack update -c <NAME>
```

Additionally, we'll need to login to the container registry so Docker can pull and push images:
```shell
# Fill your REGISTRY_NAME in the placeholder in the following command.
# You can find the REGISTRY_NAME as part of your registry URI: `<REGISTRY_NAME>.azurecr.io`
az acr login --name=<REGISTRY_NAME>
```

For more information and a full list of configurable attributes of the Azure container registry, check out the 
[API Docs](https://apidocs.zenml.io/latest/api_docs/container_registries/#zenml.container_registries.azure_container_registry.AzureContainerRegistry).
