---
description: Store secrets locally
---

The local secrets manager is a [secrets manager](./overview.md) flavor which comes built-in with 
ZenML and uses the local filesystem to store secrets.

## When to use it

The local secrets manager is built for early local development and should not be used it a production setting.
It stores your secrets without encryption and only works in combination with the [local orchestrator](../orchestrators/local.md).

## How to deploy it

The local secrets manager comes with ZenML and works without any additional setup.

## How to use it

To use the local secrets manager, we can register it and use it in our active stack:
```shell
zenml secrets-manager register <NAME> --flavor=local 

# Add the secrets manager to the active stack
zenml stack update -x <NAME>
```

You can now [register, update or delete secrets](./overview.md#in-the-cli) using the CLI or [fetch secret values inside your steps](./overview.md#in-a-zenml-step).

For more information and a full list of configurable attributes of the local secrets manager, check out the 
[API Docs](https://apidocs.zenml.io/latest/api_docs/secrets_managers/#zenml.secrets_managers.local.local_secrets_manager.LocalSecretsManager).
