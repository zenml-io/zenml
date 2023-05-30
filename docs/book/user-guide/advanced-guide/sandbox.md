---
description: Running pipelines in the MLOps Platform Sandbox.
---

# MLOps Platform Sandbox

The [MLOps Platform Sandbox](https://sandbox.zenml.io) is an ephemeral MLOps platform with
ZenML, [MLflow](https://mlflow.org), [Kubeflow](https://www.kubeflow.org/) and [Minio](https://min.io/). It aims to
demonstrate the ease of building a production-ready machine learning solution using top open-source tools. The Sandbox serves as a learning and experimentation platform and is not intended for commercial projects or large-scale production use. It provides users with a controlled environment to gain a better understanding of MLOps tools and processes before moving on to build their custom MLOps stack based on their specific needs.

## How does the Sandbox work?

After signing up, a user "creates a sandbox". This provisions the following services on a cluster maintained by the ZenML team:

- [MLflow](https://mlflow.org): The [experiment tracker](../component-guide/experiment-trackers/experiment-trackers.md)
to track metadata.
- [Orchestrator](https://kubeflow.org): The [orchestrator](../component-guide/orchestrators/orchestrators.md) to run ML workloads on kubernetes.
- [Minio]([https://](https://min.io/)): The [artifact store](../component-guide/artifact-stores/artifact-stores.md) to store artifacts produced by the pipelines.
- [ZenML](https://zenml.io): The MLOps framework that brings it all together.

Each sandbox gets a limited amount of compute and storage to play around with. The ZenML service that ships with each sandbox comes built-in with the following:

- A [registered stack with the other services](../starter-guide/understand-stacks.md) with all the credentials as [secrets](../../platform-guide/set-up-your-mlops-platform/use-the-secret-store/use-the-secret-store.md).
- A set of examples pipeline [execution environment builds](./manage-environments.md#execution-environments). These docker images are hosted on Dockerhub and allow you to run the example pipelines easily.
- A connected [code repository](./connect-your-git-repository.md) that has the code for the example pipelines. This repository is the official ZenML repository (with the code being in the [examples](https://github.com/zenml-io/zenml/tree/main/examples) directory)

In order to run the example pipelines, the user therefore needs to download the repository locally to their machine and just run a pipeline with a supported build. The Sandbox UI provides a convenient interface to copy the relevant commands. The [starter guide](../starter-guide/switch-to-production.md) also provides more detail on how to run these example pipelines.

[ADD SCREENSHOT HERE]

## How to use the Sandbox to run custom pipelines

As discussed above, the sandbox provides pre-built pipelines for users to run. If you want to try running these pipelines first, please [visit this page](../starter-guide/switch-to-production.md) in the Starter Guide to learn how to do this. 

This limitation is in place to control costs and demonstrate how MLOps engineers can enforce rules through a central control plane. However, creating new pipeline builds is not permitted due to the container registry's read-only access. 

You might be interested in using the resources provisioned in the Sandbox to run your own pipelines. There are three ways to do this:

### Run code and re-use execution environments from example pipelines (no new dependencies needed)

- Register a fork or a new code repository with new token that allows them to push
- use the build we created but you have to use the specified dependencies in the builds
- 
### Run code with custom dependencies


### Use services directly

... other things to bo?

## What do do when your sandbox runs out?

The sandbox is only available for 8 hours. After that, it will be deleted. If
you want to continue to use ZenML in a cloud deployment you can either:

- [Register a new sandbox](https://sandbox.zenml.io/)
- [Deploy your own cloud stack](../../platform-guide/set-up-your-mlops-platform/deploy-and-set-up-a-cloud-stack/deploy-a-stack-post-sandbox.md)

For the second option you can use ZenML's Stack Recipes to deploy a stack that
suits your custom use cases. For more information on how to do this, please
[visit our guide to get going](../../platform-guide/set-up-your-mlops-platform/deploy-and-set-up-a-cloud-stack/deploy-a-stack-post-sandbox.md) with this.
