---
description: How to develop across multiple development environments
---

# Managing Multiple Environments in ZenML

{% hint style="warning" %}
**Note:** This page is a work in progress (WIP) and is currently under development. If you have any questions or need assistance, please join our [Slack community](https://zenml.io/slack).
{% endhint %}

In a ZenML deployment, you might have to manage multiple environments, such as your local development environment, the ZenML server environment, and the build environment (image builders). This guide will help you understand how to manage dependencies and configurations in these different environments.

## The Client Environment

The client environment is the environment in which zenml pipelines are run. This is usually a local development environment but often in production it can be a [CI runner](../../platform-guide/set-up-your-mlops-platform/productionalize-with-ci-cd-ct.md). To manage dependencies in this environment, you can use your preferred package manager, such as `pip` or `poetry`. You can create a virtual environment and install the necessary packages there. This will help you avoid conflicts with other projects and make it easier to share your environment with your team. Make sure to install the ZenML package and any additional [integrations](../component-galery/README.md) you need for your pipelines.

To summarize, the client environment needs the ZenML dependency and all other dependencies that are required to run your pipeline. It often generates the [pipeline build environment](#the-pipeline-build-environment)

## The ZenML Server Environment

The ZenML server environment is a FastAPI application that manages your pipelines and its metadata. It is the environment you get when you [deploy ZenML](../../platform-guide/set-up-your-mlops-platform/deploy-zenml/README.md), and usually has the ZenML Dashboard built into it. This environment should have the ZenML package and some extra dependencies involved. To manage dependencies in the ZenML server environment, you can install them when [deploying ZenML](../../platform-guide/set-up-your-mlops-platform/deploy-zenml/README.md). However, you would only need to do this when you have custom integrations as most neccessary integrations come built-in.

## The Build Environments

There are two types of build environments:

- The pipeline build environment: 
- The step build environment: 

The build environment is the  environment that runs within the [orchestrator](../component-galery/orchestrators/README.md). These images need to be configured with the correct dependencies and configurations to ensure that your pipeline runs smoothly.

ZenML automatically handles most of the Docker image configuration for you. It starts with a base image that has ZenML and Python installed and then installs any additional dependencies required by your pipeline. You can customize the Docker image configuration using the [DockerSettings](containerize-your-pipeline.md) class.

To manage dependencies in the Docker images, you can follow the steps described in the [Containerize your pipeline](containerize-your-pipeline.md) guide. This includes specifying additional pip dependencies, using a custom parent image, and customizing the build process.

### Customize the build enviornment with Image Builders

Link to [image builders](../component-galery/image-builders/README.md)