---
description: Store secrets locally
---

The Local secrets manager is a [secrets manager](./overview.md) flavor comes built-in with 
ZenML and uses the local filesystem to store secrets.

## When would you want to use it?

The Local secrets manager is built for early local development and should not be used it a production setting.
It stores your secrets without encryption and only works in combination with the [local orchestrator](../orchestrators/local.md).

## How do you deploy it?

The local secrets manager comes with ZenML and works without any additional configuration.

## How to use it?

To use the Local secrets manager, we can simply register it and use it in our active stack:
```shell
zenml secrets-manager register <NAME> --flavor=local 

# Add the secrets manager to the active stack
zenml stack update -x <NAME>
```

You can now [register, update or delete secrets](./overview.md#in-the-cli) using the CLI or [fetch secret values inside your steps](./overview.md#in-a-zenml-step).

For more information and a full list of configurable attributes of the Local secrets manager, check out the 
[API Docs](https://apidocs.zenml.io/latest/api_docs/secrets_managers/#zenml.secrets_managers.local.local_secrets_manager.LocalSecretsManager).
