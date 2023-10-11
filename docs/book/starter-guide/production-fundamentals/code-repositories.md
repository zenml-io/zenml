---
description: How to track the code of your pipelines
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


## What is a code repository

A code repository in ZenML refers to a remote storage location for your code.
Some commonly known code repository platforms include [GitHub](https://github.com/)
and [GitLab](https://gitlab.com/).

Code repositories enable ZenML to keep track of the code version that you use for your
pipeline runs. Additionally, running a pipeline which is tracked in a registered code
repository can speed up the Docker image building for containerized stack components.

Check out [this diagram](../../getting-started/architecture-diagrams.md#the-code-repository)
for a visual representation how the code repository fits into the general ZenML architecture.

{% hint style="info" %}
Check out our
[code repository example](https://github.com/zenml-io/zenml/tree/main/examples/code_repository)
for a practical tutorial on how to use a ZenML code repository.
{% endhint %}

### Registering a code repository

Code repositories can be registered using the CLI:
```shell
zenml code-repository register <NAME> --type=<TYPE> [--CODE_REPOSITORY_OPTIONS]
```

For concrete options, check out the section on the [`GitHubCodeRepository`](#github),
the [`GitLabCodeRepository`](#gitlab) or how to develop and register a
[custom code repository implementation](#developing-a-custom-code-repository).

### Detecting local code repository checkouts

Once you have registered one or more code repositories, ZenML will check whether the files
you use when running a pipeline are tracked inside one of those code repositories. This happens
as follows:
* First, the [source root](../../reference/glossary.md#source-root) is computed
* Next, ZenML checks whether this source root directory is included in a local checkout of one
of the registered code repositories

### Tracking code version for pipeline runs

If a [local code repository checkout](#detecting-local-code-repository-checkouts) is detected
when running a pipeline, ZenML will store a reference the current commit for the pipeline run
so you'll be able to know exactly which code was used. Note that this reference is only tracked
if your local checkout is clean (i.e. it does not contain any untracked or uncommitted files).
This is to ensure that your pipeline is actually running with the exact code stored at the specific
code repository commit.

### Speeding up Docker builds for containerized components

When using containerized components in your stack, ZenML needs to build Docker images to
remotely execute your code. If you're not using a code repository, this code will be included
in the Docker images that ZenML builds. This, however, means that new Docker images will be built and
pushed whenever you make changes to any of your source files. When running a pipeline that is
part of a [local code repository checkout](#detecting-local-code-repository-checkouts), ZenML
can instead build the Docker images without including any of your source files, and download
the files inside the container before running your code. This greatly speeds up the building
process and also allows you to re-use images that one of your colleagues might have built for
the same stack.

Some additional points:
- The file download is only possible if the local checkout is clean (i.e. it does
not contain any untracked or uncommitted files) and the latest commit has been pushed to
the remote repository. This is necessary as otherwise the file download inside the Docker
container will fail.
- If you want to disable or enforce the downloading of files, check out
[this docs page](./containerization.md#handling-source-files) for the available options.

## Available code repository implementation

ZenML comes with builtin implementations of the code repository abstraction for the
`GitHub` and `GitLab` platforms, but it's also possible to use a 
[custom code repository implementation](#developing-a-custom-code-repository).

### GitHub

ZenML provides built-in support for using GitHub as a code repository for your
ZenML pipelines. You can register a GitHub code repository by providing the URL
of the GitHub instance, the owner of the repository, the name of the repository,
and a GitHub Personal Access Token (PAT) with access to the repository.

```shell
zenml code-repository register <NAME> --type=github \
--url=<GITHUB_URL> --owner=<OWNER> --repository=<REPOSITORY> \
--token=<GITHUB_TOKEN>
```

where <NAME> is the name of the code repository you are registering, <OWNER> is
the owner of the repository, <REPOSITORY> is the name of the repository, 
<GITHUB_TOKEN> is your GitHub Personal Access Token and <GITHUB_URL> is the URL
of the GitHub instance which defaults to `https://github.com.` You will need to
set a URL if you are using GitHub Enterprise.

After registering the GitHub code repository, ZenML will automatically detect
if your source files are being tracked by GitHub and store the commit hash for
each pipeline run.

<details>
  <summary>How To get a token for GitHub</summary>
  <ol style="list-style-type: decimal; padding-left: 1.5em;">
    <li>
        <div>
            Go to your GitHub account settings and click on <a href="https://github.com/settings/tokens?type=beta">Developer settings</a>.
        </div>
    </li>
    <li>
        <div>
            Select "Personal access tokens" and click on "Generate new token".
        </div>
    </li>
    <li>
        <div>
            Give your token a name and a description.
        </div>
        <div style="text-align: center;">
            <img src="../../assets/code_repo/github-fine-grained-token-name.png" style="max-width: 100%;">
        </div>
    </li>
    <li>
        <div>
            We recommend selecting the specific repository and then giving <code>contents</code> read-only access.
        </div>
        <div style="text-align: center;">
            <img  src="../../assets/code_repo/github-token-set-permissions.png" style="max-width: 100%;">
        </div>
        <div style="text-align: center;">
            <img src="../../assets/code_repo/github-token-permissions-overview.png" style="max-width: 100%;">
        </div>
    </li>
    <li>
        <div>
            Click on "Generate token" and copy the token to a safe place.
        </div>
        <div style="text-align: center;">
            <img  src="../../assets/code_repo/copy-github-fine-grained-token.png" style="max-width: 100%;">
        </div>
    </li>
  </ol>
</details>



### GitLab

ZenML also provides built-in support for using GitLab as a code repository for
your ZenML pipelines. You can register a GitLab code repository by providing the
URL of the GitLab project, the group of the project, the name of the project,
and a GitLab Personal Access Token (PAT) with access to the project.

To register a GitLab code repository, run the following CLI command:

```shell
zenml code-repository register <NAME> --type=gitlab \
--url=<GITLAB_URL> --group=<GROUP> --project=<PROJECT> \
--token=<GITLAB_TOKEN>
```

where <NAME> is the name of the code repository you are registering, <GROUP> is
the group of the project, <PROJECT> is the name of the project, <GITLAB_TOKEN>
is your GitLab Personal Access Token and <GITLAB_URL> is the URL of the GitLab
instance which defaults to `https://gitlab.com.` You will need to set a URL if
you have a self-hosted GitLab instance.

After registering the GitLab code repository, ZenML will automatically detect
if your source files are being tracked by GitLab and store the commit hash for
each pipeline run.

<details>
  <summary>How To get a token for GitLab</summary>
  <ol style="list-style-type: decimal; padding-left: 1.5em;">
    <li>
        <div>
            Go to your GitLab account settings and click on <a href="https://gitlab.com/-/profile/personal_access_tokens">Access Tokens</a>.
        </div>
    </li>
    <li>
        <div>
            Name the token and select the scopes that you need (e.g. <code>read_repository</code>, <code>read_user</code>, <code>read_api</code>)
        </div>
        <div style="text-align: center;">
            <img src="../../assets/code_repo/gitlab-generate-access-token.png" style="max-width: 100%;">
        </div>
    </li>
    <li>
        <div>
            Click on "Create personal access token" and copy the token to a safe place.
        </div>
        <div style="text-align: center;">
            <img  src="../../assets/code_repo/gitlab-copy-access-token.png" style="max-width: 100%;">
        </div>
    </li>
  </ol>
</details>

### Developing a custom code repository

If you're using some other platform to store your code and you still want to use
a code repository in ZenML, you can implement and register a custom code repository.

First, you'll need to subclass and implement the abstract methods of the
`zenml.code_repositories.BaseCodeRepository` class:

```python
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