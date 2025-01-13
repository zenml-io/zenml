---
description: >-
  Connect a Git repository to ZenML to track code changes and collaborate on
  MLOps projects.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Configure a code repository

Throughout the lifecycle of a MLOps pipeline, it can get quite tiresome to always wait for a Docker build every time after running a pipeline (even if the local Docker cache is used). However, there is a way to just have one pipeline build and keep reusing it until a change to the pipeline environment is made: by connecting a code repository.

With ZenML, connecting to a Git repository optimizes the Docker build processes. It also has the added bonus of being a better way of managing repository changes and enabling better code collaboration. Here is how the flow changes when running a pipeline:

<figure><img src="../../.gitbook/assets/run_with_repository.png" alt=""><figcaption><p>Sequence of events that happen when running a pipeline on a remote stack with a code repository</p></figcaption></figure>

1. You trigger a pipeline run on your local machine. ZenML parses the `@pipeline` function to determine the necessary steps.
2. The local client requests stack information from the ZenML server, which responds with the cloud stack configuration.
3. The local client detects that we're using a code repository and requests the information from the git repo.
4. Instead of building a new Docker image, the client checks if an existing image can be reused based on the current Git commit hash and other environment metadata.
5. The client initiates a run in the orchestrator, which sets up the execution environment in the cloud, such as a VM.
6. The orchestrator downloads the code directly from the Git repository and uses the existing Docker image to run the pipeline steps.
7. Pipeline steps execute, storing artifacts in the cloud-based artifact store.
8. Throughout the execution, the pipeline run status and metadata are reported back to the ZenML server.

By connecting a Git repository, you avoid redundant builds and make your MLOps processes more efficient. Your team can work on the codebase simultaneously, with ZenML handling the version tracking and ensuring that the correct code version is always used for each run.

## Creating a GitHub Repository

While ZenML supports [many different flavors of git repositories](../../how-to/setting-up-a-project-repository/connect-your-git-repository.md), this guide will focus on [GitHub](https://github.com). To create a repository on GitHub:

1. Sign in to [GitHub](https://github.com/).
2. Click the "+" icon and select "New repository."
3. Name your repository, set its visibility, and add a README or .gitignore if needed.
4. Click "Create repository."

We can now push our local code (from the [previous chapters](understand-stacks.md#run-a-pipeline-on-the-new-local-stack)) to GitHub with these commands:

```sh
# Initialize a Git repository
git init

# Add files to the repository
git add .

# Commit the files
git commit -m "Initial commit"

# Add the GitHub remote
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git

# Push to GitHub
git push -u origin master
```

Replace `YOUR_USERNAME` and `YOUR_REPOSITORY_NAME` with your GitHub information.

## Linking to ZenML

To connect your GitHub repository to ZenML, you'll need a GitHub Personal Access Token (PAT).

<details>

<summary>How to get a PAT for GitHub</summary>

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

Now, we can install the GitHub integration and register your repository:

```sh
zenml integration install github
zenml code-repository register <REPO_NAME> --type=github \
--url=https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git \
--owner=YOUR_USERNAME --repository=YOUR_REPOSITORY_NAME \
--token=YOUR_GITHUB_PERSONAL_ACCESS_TOKEN
```

Fill in `<REPO_NAME>`, `YOUR_USERNAME`, `YOUR_REPOSITORY_NAME`, and `YOUR_GITHUB_PERSONAL_ACCESS_TOKEN` with your details.

Your code is now connected to your ZenML server. ZenML will automatically detect if your source files are being tracked by GitHub and store the commit hash for each subsequent pipeline run.

You can try this out by running our training pipeline again:

```python
# This will build the Docker image the first time
python run.py --training-pipeline

# This will skip Docker building
python run.py --training-pipeline
```

You can read more about [the ZenML Git Integration here](../../how-to/setting-up-a-project-repository/connect-your-git-repository.md).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
