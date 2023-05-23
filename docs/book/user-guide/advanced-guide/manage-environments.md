---
description: Developing across multiple development environments.
---

# Manage environments

{% hint style="warning" %}
**Note:** This page is a work in progress (WIP) and is currently under development. If you have any questions or need assistance, please join our [Slack community](https://zenml.io/slack).
{% endhint %}

In a ZenML deployment, you might have to manage multiple environments, such as your local development environment, the ZenML server environment, and the `build` environment (image builders). This guide will help you understand how to manage dependencies and configurations in these different environments.

## The Client environment

The client environment is the environment in which zenml pipelines are run. This is usually a local development environment but often in production, it can be a [CI runner](../../platform-guide/set-up-your-mlops-platform/productionalize-with-ci-cd-ct.md). To manage dependencies in this environment, you can use your preferred package manager, such as `pip` or `poetry`. You can create a virtual environment and install the necessary packages there. This will help you avoid conflicts with other projects and make it easier to share your environment with your team. Make sure to install the ZenML package and any additional [integrations](../component-guide/component-guide.md) you need for your pipelines.

The client environment often does the following important steps when a pipeline runs:

1. Generates an intermediate representation for the pipeline.
2. If running remotely, creates, or triggers the creation of, the [pipeline and step build environments](manage-environments.md#the-build-environments).
3. Triggers a run in the [orchestrator](../component-guide/orchestrators/orchestrators.md).

## The ZenML Server environment

The ZenML server environment is a FastAPI application that manages your pipelines and their metadata. It is the environment you get when you [deploy ZenML](../../platform-guide/set-up-your-mlops-platform/deploy-zenml/deploy-zenml.md) and usually also includes the ZenML Dashboard. This environment should have the ZenML package and some extra dependencies involved. To manage dependencies in the ZenML server environment, you can install them when [deploying ZenML](../../platform-guide/set-up-your-mlops-platform/deploy-zenml/deploy-zenml.md). However, you would only need to do this when you have custom integrations as most necessary integrations come built-in.

## The `build` environments

When running locally, there is no real concept of a `build` environment as the client, server, and build environment are all the same. However, when running remotely, there are two types of build environments:

* **The pipeline build environment**: A docker image that the main pipeline orchestration node runs in.
* **The step build environment**: A docker image that an individual step runs in.

ZenML automatically handles most of the Docker image configuration, creation, and pushing. It starts with a base image that has ZenML and Python installed and then installs any additional dependencies required by your pipeline. You can customize the Docker image configuration using the [DockerSettings](containerize-your-pipeline.md) class.

To manage dependencies in the Docker images, you can follow the steps described in the [Containerize your pipeline](containerize-your-pipeline.md) guide. This includes specifying additional pip dependencies, using a custom parent image, and customizing the build process.

### Customize how a build image is created (Image Builders)

Normally, the build environments are created locally in the [client environment](#the-client-environment) using the local docker client. However, that means that the client needs to have Docker installed, and needs permissions to be able to build images. As this is often not the case, ZenML provides the ability to add a special [stack component](../starter-guide/understand-stacks.md) known as [image builders](../component-guide/image-builders/), that give users the ability to configure how an image is built and pushed.
