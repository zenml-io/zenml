---
description: How to store secrets locally
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


The local secrets manager is a [secrets manager](./secrets-managers.md) flavor 
which comes built-in with ZenML and uses the local filesystem to store secrets.


{% hint style="warning" %}
We are deprecating secrets managers in favor of the
[centralized ZenML secrets store](../../starter-guide/production-fundamentals/secrets-management.md#centralized-secrets-store).
Going forward, we recommend using the secrets store instead of secrets managers
to configure and store secrets.

If you already use secrets managers to manage your secrets, please use the
provided `zenml secrets-manager secrets migrate` CLI command to migrate your
secrets to the centralized secrets store.

The local secrets manager can be easily replaced by the default local secrets
store that comes pre-configured with ZenML. To do so, simply use
`zenml secret` CLI commands to manage your secrets instead of
`zenml secrets-manager secret` CLI commands. You no longer need to register
the local secrets manager or add it to your active stack.
{% endhint %}

## When to use it

The local secrets manager is built for early local development and should not 
be used it a production setting. It stores your secrets without encryption and 
only works in combination with the [local orchestrator](../orchestrators/local.md).

## How to deploy it

The local secrets manager comes with ZenML and works without any additional 
setup.

## How to use it

To use the local secrets manager, we can register it and use it in our active 
stack:
```shell
zenml secrets-manager register <NAME> --flavor=local 

# Add the secrets manager to the active stack
zenml stack update -x <NAME>
```

You can now [register, update or delete secrets](./secrets-managers.md#in-the-cli) 
using the CLI or [fetch secret values inside your steps](./secrets-managers.md#in-a-zenml-step).

For more information and a full list of configurable attributes of the local 
secrets manager, check out the [API Docs](https://apidocs.zenml.io/latest/core_code_docs/core-secrets_managers/#zenml.secrets_managers.local.local_secrets_manager.LocalSecretsManager).
