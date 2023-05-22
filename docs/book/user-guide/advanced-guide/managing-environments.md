---
description: How to develop across multiple development environments
---

# Managing Multiple Environments in ZenML

{% hint style="warning" %}
**Note:** This page is a work in progress (WIP) and is currently under development. If you have any questions or need assistance, please join our [Slack community](https://zenml.io/slack).
{% endhint %}

In a ZenML deployment, you might have to manage multiple environments, such as your local development environment, the ZenML server environment, the build environment (image builders), and the orchestrator environment. This guide will help you understand how to manage dependencies and configurations in these different environments.

## Local Development Environment

Your local development environment is where you write and test your ZenML pipelines. To manage dependencies in this environment, you can use your preferred package manager, such as `pip` or `poetry`. Make sure to install the ZenML package and any additional [integrations](../component-galery/README.md) you need for your pipelines.

To ensure that your local environment matches the requirements of your pipelines, you can create a virtual environment and install the necessary packages there. This will help you avoid conflicts with other projects and make it easier to share your environment with your team.

## ZenML Server Environment

The ZenML server environment is where the ZenML server runs and manages your pipelines. This environment should have the ZenML package and any required integrations installed, just like your local development environment. To manage dependencies in the ZenML server environment, you can install them when [deploying ZenML](../../platform-guide/set-up-your-mlops-platform/deploy-zenml/README.md).

## Build Environment (Image Builders)

The build environment is where Docker images are created for your pipelines. These images need to be configured with the correct dependencies and configurations to ensure that your pipeline runs smoothly.

ZenML automatically handles most of the Docker image configuration for you. It starts with a base image that has ZenML and Python installed and then installs any additional dependencies required by your pipeline. You can customize the Docker image configuration using the [DockerSettings](containerize-your-pipeline.md) class.

To manage dependencies in the Docker images, you can follow the steps described in the [Containerize your pipeline](containerize-your-pipeline.md) guide. This includes specifying additional pip dependencies, using a custom parent image, and customizing the build process.

### Customizing the `build` environment

TODO: Include reference to managing envioronments and maybe move to the top

The [image builder](broken-reference/) component of your stack defines the environment in which the Docker build with the previously described Dockerfile gets executed. This could be either on your local machine (when using the [local image builder](broken-reference/)) or in some remote environment. Check our the image builder documentation for more information.

## Orchestrator Environment

The orchestrator environment is responsible for managing the execution of your pipelines. To ensure that the orchestrator environment is properly configured, you need to install the necessary dependencies and integrations, just like in your local development and ZenML server environments.

To manage dependencies in the orchestrator environment, you can use a package manager like `pip` or `poetry`. Make sure to install the ZenML package and any required integrations.

For more information on configuring the orchestrator environment, refer to the [Pipeline Containerization](containerize-your-pipeline.md) guide.

## Summary

Managing multiple environments in a ZenML deployment involves keeping track of dependencies and configurations in your local development environment, the ZenML server environment, the build environment, and the orchestrator environment. By using package managers, specifying dependencies, and customizing Docker image configurations, you can ensure that your environments are consistent and your pipelines run smoothly.