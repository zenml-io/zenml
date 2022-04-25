# Secrets Manager

Most projects involving either cloud infrastructure or of a certain complexity will involve secrets of some kind. You
use secrets, for example, when connecting to AWS, which requires an `access_key_id` and a `secret_access_key which it (
usually) stores in your `~/.aws/credentials` file.
You might find you need to access those secrets from within your Kubernetes cluster as it runs individual steps, or you
might just want a centralized location for the storage of secrets across your project. ZenML offers a local secrets
manager and an integration with the managed `AWS Secrets Manager`.

## CLI

Check out the CLI commands concerning the artifact store
[here](https://apidocs.zenml.io/latest/cli/#zenml.cli--setting-up-a-secrets-manager).

## Implementations 

WIP

## Build Your Own

WIP
