---
description: Running pipelines in the MLOps Platform Sandbox.
---

# MLOps Platform Sandbox

The [MLOps Platform Sandbox](https://sandbox.zenml.io) is a temporary MLOps platform that includes ZenML, [MLflow](https://mlflow.org), [Kubeflow](https://www.kubeflow.org/), and [Minio](https://min.io/). Its purpose is to showcase the simplicity of creating a production-ready machine learning solution using popular open-source tools. The Sandbox is designed for learning and experimentation, not for commercial projects or large-scale production use. It offers users a controlled environment to explore MLOps tools and processes before building their custom MLOps stack based on their specific requirements.

## How does the Sandbox work?

After signing up, a user "creates a sandbox" which provisions the following services on a cluster managed by the ZenML team:

- [MLflow](https://mlflow.org): An [experiment tracker](../component-guide/experiment-trackers/experiment-trackers.md) for tracking metadata.
- [Kubeflow](https://kubeflow.org): An [orchestrator](../component-guide/orchestrators/orchestrators.md) for running ML workloads on Kubernetes.
- [Minio](https://min.io/): An [artifact store](../component-guide/artifact-stores/artifact-stores.md) for storing artifacts produced by pipelines.
- [ZenML](https://zenml.io): The MLOps framework that integrates everything.

Each sandbox comes with limited compute and storage resources. The ZenML service included with each sandbox has the following features:

- A [registered stack with other services](../starter-guide/understand-stacks.md), including all credentials as [secrets](../../platform-guide/set-up-your-mlops-platform/use-the-secret-store/use-the-secret-store.md).
- A set of example pipeline [execution environment builds](./manage-environments.md#execution-environments). These Docker images are hosted on Dockerhub and make running the example pipelines easy.
- A connected [code repository](./connect-your-git-repository.md) containing the code for the example pipelines. This repository is the official ZenML repository (with the code located in the [examples](https://github.com/zenml-io/zenml/tree/main/examples) directory).

To run the example pipelines, users need to download the repository locally and execute a pipeline with a supported build. The Sandbox UI offers a convenient interface for copying the relevant commands. The [starter guide](../starter-guide/switch-to-production.md) also provides more details on running these example pipelines.

[ADD SCREENSHOT HERE]

## How to use the Sandbox to run custom pipelines

As discussed above, the sandbox provides pre-built pipelines for users to run. If you want to try running these pipelines first, please [visit this page](../starter-guide/switch-to-production.md) in the Starter Guide to learn how to do this. This limitation is in place to control costs and demonstrate how MLOps engineers can enforce rules through a central control plane.

You might be interested in using the resources provisioned in the Sandbox to run your own pipelines. There are two ways to do this:

### Run code and re-use execution environments from example pipelines (no new dependencies needed)

To update the code, you need to be able to push to the code repository. In order to do that, you can either:

- Fork the zenml repository, so that the examples directory is within your code, and you can edit it in your fork, or
- Create a new code repository with a new token that allows you to push. You can then copy the examples code into your new code repository, and edit it.

Read more how to connect a git repository to ZenML [here](./connect-your-git-repository.md).

After that is done, you can change the code and run the pipeline with your chosen execution environment build. Learn more about reusing execution environments [here](./containerize-your-pipeline.md#reuse-docker-image-builds-from-previous-runs).

### Run code with custom dependencies

If you have code with different dependencies than the ones in the sandbox examples, you need to copy the stack provided in the sandbox and swap the container registry with a public container registry where you have write access. The [container registry stack component](../component-guide/container-registries/container-registries.md) docs talk more about how to do this.

In order to register a new stack, you can execute the following:

```shell
zenml stack register my_stack \
  -o sandbox-kubeflow \
  -a sandbox-minio \
  -e sandbox-mlflow \
  -dv sandbox-validator \
  -c <MY_CONTAINER_REGISTRY> \
  --set
```

With the above stack, you can run whatever code you'd like without tying it to a container registry, because ZenML will just build and push docker images to your container registry from your local client.

## What do do when your sandbox runs out?

The sandbox is only available for 8 hours. After that, it will be deleted. If
you want to continue to use ZenML in a cloud deployment you can either:

- [Register a new sandbox](https://sandbox.zenml.io/)
- [Deploy your own cloud stack](../../platform-guide/set-up-your-mlops-platform/deploy-and-set-up-a-cloud-stack/deploy-a-stack-after-using-the-sandbox.md)

For the second option you can use ZenML's Stack Recipes to deploy a stack that
suits your custom use cases. For more information on how to do this, please
[visit our guide to get going](../../platform-guide/set-up-your-mlops-platform/deploy-and-set-up-a-cloud-stack/deploy-a-stack-after-using-the-sandbox.md) with this.
