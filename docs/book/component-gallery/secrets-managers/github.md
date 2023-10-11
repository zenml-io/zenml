---
description: How to store secrets in GitHub
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


The GitHub secrets manager is a [secrets manager](./secrets-managers.md) flavor 
provided with the ZenML `github` integration that uses 
[GitHub secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
to store secrets.

{% hint style="warning" %}
We are deprecating secrets managers in favor of the
[centralized ZenML secrets store](../../advanced-guide/practical/secrets-management.md#centralized-secrets-store).
Going forward, we recommend using the secrets store instead of secrets managers
to configure and store secrets.

If you already use secrets managers to manage your secrets, please use the
provided `zenml secrets-manager secrets migrate` CLI command to migrate your
secrets to the centralized secrets store.

We're not planning to support GitHub as a direct centralized secrets store
back-end replacement for the GitHub secrets manager stack component because
of its limitation of only allowing reading secret values when running
inside a GitHub Actions workflow.

To continue using secrets, you may use any of the secrets store back-ends
that the ZenML server supports, such as Google Secret Manager, Azure Key Vault, AWS
Secrets Manager, HashiCorp Vault or even the ZenML SQL database. Simply
[configure your ZenML server to connect to one of these services](../../getting-started/deploying-zenml/deploying-zenml.md) directly as a back-end for the centralized secrets store and
then use `zenml secret` CLI commands to manage your secrets instead of
`zenml secrets-manager secret` CLI commands. You no longer need to register
the GitHub secrets manager or add it to your active stack.
{% endhint %}

## When to use it

{% hint style="warning" %}
The GitHub secrets manager does not allow reading secret values unless it's 
running inside a GitHub Actions workflow. For this reason, this secrets 
manager **only** works in combination with a [GitHub Actions orchestrator](../orchestrators/github.md).
{% endhint %}

## How to deploy it

GitHub secrets are automatically enabled when creating a GitHub repository.

## How to use it

To use the GitHub secrets manager, we need:
* The ZenML `github` integration installed. If you haven't done so, run 
    ```shell
    zenml integration install github
    ```
* A personal access token to authenticate with the GitHub API. Follow
[this guide](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
to create one and make sure to give it the `repo` scope.
* Our GitHub username and the personal access token set as environment variables:
    ```shell
    export GITHUB_USERNAME=<GITHUB_USERNAME>
    export GITHUB_AUTHENTICATION_TOKEN=<PERSONAL_ACCESS_TOKEN>
    ```
* The owner and name of the repository that we want to add secrets to.

We can then register the secrets manager and use it in our active stack:
```shell
zenml secrets-manager register <NAME> \
    --flavor=github \
    --owner=<OWNER> \
    --repository=<REPOSITORY>

# Add the secrets manager to the active stack
zenml stack update -x <NAME>
```

You can now [register, update or delete secrets](./secrets-managers.md#in-the-cli) 
using the CLI or [fetch secret values inside your steps](./secrets-managers.md#in-a-zenml-step).

A concrete example of using the GitHub secrets manager can be found 
[here](https://github.com/zenml-io/zenml/tree/main/examples/github_actions_orchestration).

For more information and a full list of configurable attributes of the GitHub 
secrets manager, check out the [API Docs](https://apidocs.zenml.io/latest/integration_code_docs/integrations-github/#zenml.integrations.github.secrets_managers.github_secrets_manager.GitHubSecretsManager).
