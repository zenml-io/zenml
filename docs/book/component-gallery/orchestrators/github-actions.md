---
description: How to orchestrate pipelines with GitHub Actions
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


The GitHub Actions orchestrator is an [orchestrator](./orchestrators.md) 
flavor provided with the ZenML `github` integration that uses [GitHub Actions](https://github.com/features/actions)
to run your pipelines.

## When to use it

You should use the GitHub Actions orchestrator if:
* you're using GitHub for your projects.
* you're looking for a free, managed solution to run your pipelines.
* you're looking for a UI in which you can track your pipeline
runs.
* your pipeline steps don't require many resources to run. The GitHub
Actions orchestrator uses GitHub Actions runners to run your pipelines. These 
runners have access to limited hardware resources and are not able to run 
computationally intensive tasks.

## How to deploy it

The GitHub Actions orchestrator runs on hardware provided by GitHub
Actions runners and only requires you to have a GitHub account and repository.

## How to use it

To use the GitHub Actions orchestrator, we need:

* The ZenML `github` integration installed. If you haven't done so, run 
    ```shell
    zenml integration install github
    ```
* [Docker](https://www.docker.com) installed and running.
* A [remote artifact store](../artifact-stores/artifact-stores.md) as part of 
your stack.
* A [GitHub container registry](../container-registries/github.md) as part of 
your stack.

We can then register the orchestrator and use it in our active stack:

```shell
zenml orchestrator register <NAME> --flavor=github

# Add the orchestrator to the active stack
zenml stack update -o <NAME>
```

{% hint style="info" %}
ZenML will build a Docker image called `<CONTAINER_REGISTRY_URI>/zenml:<PIPELINE_NAME>`
which includes your code and use it to run your pipeline steps in GitHub. 
Check out [this page](../../advanced-guide/pipelines/containerization.md)
if you want to learn more about how ZenML builds these images and how you can 
customize them.
{% endhint %}

You can now run any ZenML pipeline using the GitHub Actions orchestrator:

```shell
python file_that_runs_a_zenml_pipeline.py
```

In contrast with our other orchestrators, this does not automatically run
your pipeline. Your pipeline will only work once you push the workflow file
that the orchestrator has written in the previous `python` call.
If you want to automate this process and want the orchestrator to commit and
run these files automatically, you can set the orchestrators `push` attribute to
`True`. To do so, simply update your orchestrator:

```shell
zenml orchestrator update <NAME> --push=True
```

A concrete example of using the GitHub Actions orchestrator can be found 
[here](https://github.com/zenml-io/zenml/tree/main/examples/github_actions_orchestration).

For more information and a full list of configurable attributes of the GitHub 
Actions orchestrator, check out the [API Docs](https://apidocs.zenml.io/latest/api_docs/integration_code_docs/integrations-github/#zenml.integrations.github.orchestrators.github_actions_orchestrator.GitHubActionsOrchestrator).