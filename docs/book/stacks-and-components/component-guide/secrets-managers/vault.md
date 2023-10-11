---
description: Storing secrets in HashiCorp Vault.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To check the latest version please [visit https://docs.zenml.io](https://docs.zenml.io)
{% endhint %}


# HashiCorp Vault Secrets Manager

The HashiCorp Vault secrets manager is a [secrets manager](secrets-managers.md) flavor provided with the ZenML `vault`
integration that uses [HashiCorp Vault](https://www.vaultproject.io/) to store secrets.

{% hint style="warning" %}
We are deprecating secrets managers in favor of
the [centralized ZenML secrets store](/docs/book/user-guide/advanced-guide/secret-management/secret-management.md)
. Going forward, we recommend using the secrets store instead of secrets managers to configure and store secrets.

If you already use secrets managers to manage your secrets, please use the
provided `zenml secrets-manager secrets migrate` CLI command to migrate your secrets to the centralized secrets store.

To continue using HashiCorp Vault as the service of choice for managing your secrets in the
cloud, [configure your ZenML server to connect to and use the HashiCorp Vault service](/docs/book/deploying-zenml/zenml-self-hosted/zenml-self-hosted.md)
directly as a back-end for the centralized secrets store and then use `zenml secret` CLI commands to manage your secrets
instead of `zenml secrets-manager secret` CLI commands. You no longer need to register the HashiCorp Vault secrets
manager or add it to your active stack.

Alternatively, you may use any of the other secrets store back-ends that the ZenML server supports, such as Google
Secret Manager, Azure Key Vault, AWS Secrets Manager, or even the ZenML SQL database.
{% endhint %}

### When to use it

You should use the HashiCorp Vault secrets manager if:

* a component of your stack requires a secret for authentication, or you want to use secrets inside your steps.
* you're already using HashiCorp Vault to store your secrets or want a self-hosted secrets solution.

### How to deploy it

To get started with this secrets manager, you need to either:

* [self-host a Vault server](https://www.vaultproject.io/docs/install)
* [register for the managed HashiCorp Cloud Platform Vault](https://cloud.hashicorp.com/docs/vault)

Once you decided and finished setting up one of the two solutions, you need to enable
the [KV Secrets Engine - Version 2](https://www.vaultproject.io/docs/secrets/kv/kv-v2).

### How to use it

To use the Vault secrets manager, we need:

* The ZenML `vault` integration installed. If you haven't done so, run

  ```shell
  zenml integration install vault
  ```
* The Vault server URL and KV Secrets Engine v2 endpoint.
* A client token to authenticate with the Vault server.
  Follow [this tutorial](https://learn.hashicorp.com/tutorials/vault/tokens?in=vault/tokens) to generate one.

We can then register the secrets manager and use it in our active stack:

```shell
zenml secrets-manager register <NAME> \
    --flavor=vault \
    --url=<VAULT_SERVER_URL> \
    --token=<VAULT_TOKEN> \
    --mount_point=<PATH_TO_KV_V2_ENGINE>

# Add the secrets manager to the active stack
zenml stack update -x <NAME>
```

You can now [register, update or delete secrets](secrets-managers.md#in-the-cli) using the CLI
or [fetch secret values inside your steps](secrets-managers.md#in-a-zenml-step).

You can use [secret scoping](secrets-managers.md#secret-scopes) with the Vault Secrets Manager to manage multiple
Secrets Manager namespaces on top of a single Vault service instance.

For more information and a full list of configurable attributes of the HashiCorp Vault secrets manager, check out
the [API Docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-vault/#zenml.integrations.vault.secrets\_manager.vault\_secrets\_manager.VaultSecretsManager)
.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
