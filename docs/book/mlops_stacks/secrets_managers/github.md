---
description: Store secrets in GitHub
---

The GitHub secrets manager is a [secrets manager](./overview.md) flavor provided with
the ZenML `github` integration that uses [GitHub secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
to store secrets.

## When to use it

{% hint style="warning" %}
The GitHub secrets manager does not allow reading secret values unless it's running inside a
GitHub Actions workflow. For this reason, this secrets manager **only** works in combination
with a [GitHub Actions orchestrator](../orchestrators/github_actions.md).
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

You can now [register, update or delete secrets](./overview.md#in-the-cli) using the CLI or [fetch secret values inside your steps](./overview.md#in-a-zenml-step).

A concrete example of using the GitHub secrets manager can be found 
[here](https://github.com/zenml-io/zenml/tree/main/examples/github_actions_orchestration).

For more information and a full list of configurable attributes of the GitHub secrets manager, check out the 
[API Docs](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.github.secrets_managers.github_secrets_manager.GitHubSecretsManager).
