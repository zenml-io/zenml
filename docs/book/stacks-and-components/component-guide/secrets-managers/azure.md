---
description: Storing secrets in Azure.
---

# Azure Secrets Manager

The Azure secrets manager is a [secrets manager](secrets-managers.md) flavor provided with the ZenML `azure` integration
that uses [Azure Key Vault](https://azure.microsoft.com/en-us/services/key-vault/#product-overview) to store secrets.

{% hint style="warning" %}
We are deprecating secrets managers in favor of
the [centralized ZenML secrets store](/docs/book/user-guide/advanced-guide/secret-management/secret-management.md)
. Going forward, we recommend using the secrets store instead of secrets managers to configure and store secrets.

If you already use secrets managers to manage your secrets, please use the
provided `zenml secrets-manager secrets migrate` CLI command to migrate your secrets to the centralized secrets store.

To continue using Azure Key Vault as the service of choice for managing your secrets in the
cloud, [configure your ZenML server to connect to and use the Azure Key Vault service](/docs/book/deploying-zenml/zenml-self-hosted/zenml-self-hosted.md)
directly as a back-end for the centralized secrets store and then use `zenml secret` CLI commands to manage your secrets
instead of `zenml secrets-manager secret` CLI commands. You no longer need to register the Azure secrets manager stack
component or add it to your active stack.

Alternatively, you may use any of the other secrets store back-ends that the ZenML server supports, such as Google
Secret Manager, AWS Secrets Manager, HashiCorp Vault, or even the ZenML SQL database.
{% endhint %}

### When to use it

You should use the Azure secrets manager if:

* a component of your stack requires a secret for authentication, or you want to use secrets inside your steps.
* you're already using Azure, especially if your orchestrator is running in Azure. If you're using a different cloud
  provider, take a look at the other [secrets manager flavors](secrets-managers.md#secrets-manager-flavors).

### How to deploy it

* Go to the [Azure portal](https://portal.azure.com/#home).
* In the search bar, enter `key vaults` and open up the corresponding service.
* Click on `+ Create` in the top left.
* Fill in all values and create the key vault.

### How to use it

To use the Azure secrets manager, we need:

* The ZenML `azure` integration installed. If you haven't done so, run

  ```shell
  zenml integration install azure
  ```
* The [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli) installed and authenticated.
* The name of the key vault to use. You can find a list of your key vaults by going to
  the [Azure portal](https://portal.azure.com/#home) and searching for `key vaults`. If you don't have a key vault yet,
  follow the
* [deployment guide](azure.md#how-to-deploy-it) to create one.

We can then register the secrets manager and use it in our active stack:

```shell
zenml secrets-manager register <NAME> \
    --flavor=azure \
    --key_vault_name=<KEY_VAULT_NAME>

# Add the secrets manager to the active stack
zenml stack update -x <NAME>
```

You can now [register, update or delete secrets](secrets-managers.md#in-the-cli) using the CLI
or [fetch secret values inside your steps](secrets-managers.md#in-a-zenml-step).

You can use [secret scoping](secrets-managers.md#secret-scopes) with the Azure Secrets Manager to emulate multiple
Secrets Manager namespaces on top of a single Azure key vault.

A concrete example of using the Azure secrets manager can be
found [here](https://github.com/zenml-io/zenml/tree/main/examples/cloud\_secrets\_manager).

For more information and a full list of configurable attributes of the Azure secrets manager, check out
the [API Docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-azure/#zenml.integrations.azure.secrets\_managers.azure\_secrets\_manager.AzureSecretsManager)
.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
