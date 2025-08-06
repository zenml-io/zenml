---
description: >-
  Tracking your code and avoiding unnecessary Docker builds by connecting your
  git repo.
icon: code-compare
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Code Repositories

A code repository in ZenML refers to a remote storage location for your code. Some commonly known code repository platforms include [GitHub](https://github.com/) and [GitLab](https://gitlab.com/).

<figure><img src="../../.gitbook/assets/Remote_with_code_repository.png" alt=""><figcaption><p>A visual representation of how the code repository fits into the general ZenML architecture.</p></figcaption></figure>

Connecting code repositories to ZenML solves two fundamental challenges in machine learning workflows. First, it enhances reproducibility by tracking which specific code version (commit hash) was used for each pipeline run, creating a clear audit trail between your code and its results. Second, it dramatically improves development efficiency by optimizing Docker image building. Instead of including source code in each build, ZenML builds images without the code and downloads it at runtime, eliminating the need to rebuild images after every code change. This not only speeds up individual development cycles but allows team members to share and reuse builds, saving time and computing resources across your organization.

Learn more about how code repositories optimize Docker builds [here](https://docs.zenml.io/how-to/customize-docker-builds/how-to-reuse-builds).

## Registering a code repository

If you are planning to use one of the available implementations of code repositories, first, you need to install the corresponding ZenML integration:

```
zenml integration install <INTEGRATION_NAME>
```

Afterward, code repositories can be registered using the CLI:

```shell
zenml code-repository register <NAME> --type=<TYPE> [--CODE_REPOSITORY_OPTIONS]
```

For concrete options, check out the section on the `GitHubCodeRepository`, the `GitLabCodeRepository` or how to develop and register a custom code repository implementation.

## Available implementations

ZenML comes with builtin implementations of the code repository abstraction for the `GitHub` and `GitLab` platforms, but it's also possible to use a custom code repository implementation.

### GitHub

ZenML provides built-in support for using GitHub as a code repository for your ZenML pipelines. You can register a GitHub code repository by providing the URL of the GitHub instance, the owner of the repository, the name of the repository, and a GitHub Personal Access Token (PAT) with access to the repository.

Before registering the code repository, first, you have to install the corresponding integration:

```sh
zenml integration install github
```

Afterward, you can register a GitHub code repository by running the following CLI command:

```shell
zenml code-repository register <NAME> --type=github \
--owner=<OWNER> --repository=<REPOSITORY> \
--token=<GITHUB_TOKEN>
```

where `<REPOSITORY>` is the name of the code repository you are registering, `<OWNER>` is the owner of the repository, `<NAME>` is the name of the repository and `<GITHUB_TOKEN>` is your GitHub Personal Access Token.

If you're using a self-hosted GitHub Enterprise instance, you'll need to also pass the `--api_url=<API_URL>` and `--host=<HOST>` options. `<API_URL>` should point to where the GitHub API is reachable (defaults to `https://api.github.com/`) and `<HOST>` should be the [hostname of your GitHub instance](https://docs.github.com/en/enterprise-server@3.10/admin/configuring-settings/configuring-network-settings/configuring-the-hostname-for-your-instance?learn=deploy_an_instance\&learnProduct=admin).

{% hint style="warning" %}
Please refer to the section on using secrets for stack configuration in order to securely store your GitHub\
Personal Access Token.

```shell
# Using central secrets management
zenml secret create github_secret \
    --pa_token=<GITHUB_TOKEN>
    
# Then reference the username and password
zenml code-repository register ... --token={{github_secret.pa_token}}
    ...
```
{% endhint %}

After registering the GitHub code repository, ZenML will automatically detect if your source files are being tracked by GitHub and store the commit hash for each pipeline run.

<details>

<summary>How to get a token for GitHub</summary>

1. Go to your GitHub account settings and click on [Developer settings](https://github.com/settings/tokens?type=beta).
2. Select "Personal access tokens" and click on "Generate new token".
3.  Give your token a name and a description.

    ![](../../.gitbook/assets/github-fine-grained-token-name.png)
4.  We recommend selecting the specific repository and then giving `contents` read-only access.

    ![](../../.gitbook/assets/github-token-set-permissions.png)

    ![](../../.gitbook/assets/github-token-permissions-overview.png)
5.  Click on "Generate token" and copy the token to a safe place.

    ![](../../.gitbook/assets/copy-github-fine-grained-token.png)

</details>

### GitLab

ZenML also provides built-in support for using GitLab as a code repository for your ZenML pipelines. You can register a GitLab code repository by providing the URL of the GitLab project, the group of the project, the name of the project, and a GitLab Personal Access Token (PAT) with access to the project.

Before registering the code repository, first, you have to install the corresponding integration:

```sh
zenml integration install gitlab
```

Afterward, you can register a GitLab code repository by running the following CLI command:

```shell
zenml code-repository register <NAME> --type=gitlab \
--group=<GROUP> --project=<PROJECT> \
--token=<GITLAB_TOKEN>
```

where `<NAME>` is the name of the code repository you are registering, `<GROUP>` is the group of the project, `<PROJECT>` is the name of the project and `<GITLAB_TOKEN>` is your GitLab Personal Access Token.

If you're using a self-hosted GitLab instance, you'll need to also pass the `--instance_url=<INSTANCE_URL>` and `--host=<HOST>` options. `<INSTANCE_URL>` should point to your GitLab instance (defaults to `https://gitlab.com/`) and `<HOST>` should be the hostname of your GitLab instance (defaults to `gitlab.com`).

{% hint style="warning" %}
Please refer to the section on using secrets for stack configuration in order to securely store your GitLab\
Personal Access Token.

```shell
# Using central secrets management
zenml secret create gitlab_secret \
    --pa_token=<GITLAB_TOKEN>
    
# Then reference the username and password
zenml code-repository register ... --token={{gitlab_secret.pa_token}}
    ...
```
{% endhint %}

After registering the GitLab code repository, ZenML will automatically detect if your source files are being tracked by GitLab and store the commit hash for each pipeline run.

<details>

<summary>How to get a token for GitLab</summary>

1. Go to your GitLab account settings and click on Access Tokens.
2.  Name the token and select the scopes that you need (e.g. `read_repository`, `read_user`, `read_api`)

    ![](../../.gitbook/assets/gitlab-generate-access-token.png)
3.  Click on "Create personal access token" and copy the token to a safe place.

    ![](../../.gitbook/assets/gitlab-copy-access-token.png)

</details>

## Developing a custom code repository

If you're using some other platform to store your code, and you still want to use a code repository in ZenML, you can implement and register a custom code repository.

First, you'll need to subclass and implement the abstract methods of the `zenml.code_repositories.BaseCodeRepository` class:

```python
from abc import ABC, abstractmethod
from typing import Optional

class BaseCodeRepository(ABC):
    """Base class for code repositories."""

    @abstractmethod
    def login(self) -> None:
        """Logs into the code repository."""

    @abstractmethod
    def download_files(
            self, commit: str, directory: str, repo_sub_directory: Optional[str]
    ) -> None:
        """Downloads files from the code repository to a local directory.

        Args:
            commit: The commit hash to download files from.
            directory: The directory to download files to.
            repo_sub_directory: The subdirectory in the repository to
                download files from.
        """

    @abstractmethod
    def get_local_context(
            self, path: str
    ) -> Optional["LocalRepositoryContext"]:
        """Gets a local repository context from a path.

        Args:
            path: The path to the local repository.

        Returns:
            The local repository context object.
        """
```

After you're finished implementing this, you can register it as follows:

```shell
# The `CODE_REPOSITORY_OPTIONS` are key-value pairs that your implementation will receive
# as configuration in its __init__ method. This will usually include stuff like the username
# and other credentials necessary to authenticate with the code repository platform.
zenml code-repository register <NAME> --type=custom --source=my_module.MyRepositoryClass \
    [--CODE_REPOSITORY_OPTIONS]
```