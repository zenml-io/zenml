---
description: Orchestrate pipelines with GitHub Actions
---

The GitHub Actions orchestrator is an [orchestrator](./overview.md) flavor provided with
the ZenML `github` integration that uses [GitHub Actions](https://github.com/features/actions)
to run your pipelines.

## When to use it

You should use the GitHub Actions orchestrator if:
* ...

## How to deploy it

...

## How to use it

To use the GitHub Actions orchestrator, we need:
* The ZenML `github` integration installed. If you haven't done so, run 
    ```shell
    zenml integration install github
    ```

We can then register the orchestrator and use it in our active stack:
```shell
zenml orchestrator register <NAME> \
    --flavor=github

# Add the orchestrator to the active stack
zenml stack update -o <NAME>
```

TODO: explain how to run a pipeline

A concrete example of using the GitHub Actions orchestrator can be found 
[here](https://github.com/zenml-io/zenml/tree/main/examples/github_actions_orchestration).

For more information and a full list of configurable attributes of the GitHub Actions orchestrator, check out the 
[API Docs](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.github.orchestrators.github_actions_orchestrator.GitHubActionsOrchestrator).