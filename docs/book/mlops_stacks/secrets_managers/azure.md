---
description: Store secrets in Azure
---

The Azure secrets manager is a [secrets manager](./overview.md) flavor provided with
the ZenML `azure` integration that uses [Azure Key Vault](https://azure.microsoft.com/en-us/services/key-vault/#product-overview)
to store secrets.

## When to use it

You should use the Azure secrets manager if:
* a component of your stack requires a secret for authentication or you want 
to use secrets inside your steps.
* you're already using Azure, especially if your orchestrator is running in Azure.
If you're using a different cloud provider, take a look at the other [secrets manager flavors](./overview.md#secrets-manager-flavors).

## How to deploy it

* Go to the [Azure portal](https://portal.azure.com/#home).
* In the search bar, enter `key vaults` and open up the corresponding service.
* Click on `+ Create` in the top left.
* Fill in all values and create the key vault.

## How to use it

To use the Azure secrets manager, we need:
* The ZenML `azure` integration installed. If you haven't done so, run 
    ```shell
    zenml integration install azure
    ```
* The [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli) installed and authenticated.
* The name of the key vault to use. You can find a list of your key vaults by going to the
[Azure portal](https://portal.azure.com/#home) and searching for `key vaults`. If you don't have any key vault yet,
follow the [deployment guide](#how-do-you-deploy-it) to create one.

We can then register the secrets manager and use it in our active stack:
```shell
zenml secrets-manager register <NAME> \
    --flavor=azure_key_vault \
    --key_vault_name=<KEY_VAULT_NAME>

# Add the secrets manager to the active stack
zenml stack update -x <NAME>
```

You can now [register, update or delete secrets](./overview.md#in-the-cli) using the CLI or [fetch secret values inside your steps](./overview.md#in-a-zenml-step).

A concrete example of using the Azure secrets manager can be found 
[here](https://github.com/zenml-io/zenml/tree/main/examples/cloud_secrets_manager).

For more information and a full list of configurable attributes of the Azure secrets manager, check out the 
[API Docs](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.azure.secrets_managers.azure_secrets_manager.AzureSecretsManager).
