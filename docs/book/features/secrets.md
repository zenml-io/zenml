---
description: ZenML provides functionality to store secrets locally and with AWS.
---

# Managing Secrets

Most projects involving either cloud infrastructure or of a certain complexity
will involve secrets of some kind. You use secrets, for example, when connecting
to AWS, which requires an `access_key_id` and a `secret_access_key` which it (usually)
stores in your `~/.aws/credentials` file.

You might find you need to access those secrets from within your Kubernetes
cluster as it runs individual steps, or you might just want a centralized
location for the storage of secrets across your project. ZenML offers a basic
local secrets manager and an integration with the managed [AWS Secrets
Manager](https://aws.amazon.com/secrets-manager).

## Registering a secrets manager

The local secrets manager currently exists in a YAML- and filesystem-based
flavor. (An SQLite-powered flavor is coming soon!) If you want to use the AWS
Secrets Manager as a non-local flavor that is also possible with ZenML.

To register a local secrets manager, use the CLI interface:

```shell
zenml secrets-manager register SECRETS_MANAGER_NAME -t local
```

You will then need to add the secrets manager to a new stack that you register,
for example:

```shell
zenml stack register STACK_NAME \
    -m METADATA_STORE_NAME \
    -a ARTIFACT_STORE_NAME \
    -o ORCHESTRATOR_NAME \
    -x SECRETS_MANAGER_NAME
zenml stack set STACK_NAME
```

## Interacting with the Secrets Manager

A full guide on using the CLI interface to register, access, update and delete
secrets is available [here](https://apidocs.zenml.io/latest/cli/).

## Using Secrets in a Kubeflow environment

## Using the AWS Secrets Manager integration

