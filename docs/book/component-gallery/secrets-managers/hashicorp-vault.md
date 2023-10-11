---
description: How to store secrets in HashiCorp Vault
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


The HashiCorp Vault secrets manager is a [secrets manager](./secrets-managers.md) 
flavor provided with the ZenML `vault` integration that uses [HashiCorp Vault](https://www.vaultproject.io/)
to store secrets.

## When to use it

You should use the HashiCorp Vault secrets manager if:
* a component of your stack requires a secret for authentication, or you want 
to use secrets inside your steps.
* you're already using HashiCorp Vault to store your secrets or want a
self-hosted secrets solution.

## How to deploy it

To get started with this secrets manager, you need to either:
* [self-host a Vault server](https://www.vaultproject.io/docs/install)
* [register for the managed HashiCorp Cloud Platform Vault](https://cloud.hashicorp.com/docs/vault)

Once you decided and finished setting up one of the two solutions, you need to 
enable the [KV Secrets Engine - Version 2](https://www.vaultproject.io/docs/secrets/kv/kv-v2).

## How to use it

To use the Vault secrets manager, we need:
* The ZenML `vault` integration installed. If you haven't done so, run 
    ```shell
    zenml integration install vault
    ```
* The Vault server URL and KV Secrets Engine v2 endpoint.
* A client token to authenticate with the Vault server. Follow 
[this tutorial](https://learn.hashicorp.com/tutorials/vault/tokens?in=vault/tokens)
to generate one.

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

You can now [register, update or delete secrets](./secrets-managers.md#in-the-cli) 
using the CLI or [fetch secret values inside your steps](./secrets-managers.md#in-a-zenml-step).

You can use [secret scoping](./secrets-managers.md#secret-scopes) with the Vault
Secrets Manager to manage multiple Secrets Manager namespaces on top of a
single Vault service instance.

A concrete example of using the HashiCorp Vault secrets manager can be found 
[here](https://github.com/zenml-io/zenml/tree/main/examples/cloud_secrets_manager).

For more information and a full list of configurable attributes of the HashiCorp
Vault secrets manager, check out the [API Docs](https://apidocs.zenml.io/latest/api_docs/integration_code_docs/integrations-vault/#zenml.integrations.vault.secrets_manager.vault_secrets_manager.VaultSecretsManager).
