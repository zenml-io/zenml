---
description: How to develop across multiple development environments
---

# TODO

The "Managing environments" page:
- What kind of environments even exist when using ZenML: theres the client
  environment, the build environment (image builders), the server environment
  (tell them that this needs to have some stuff installed if they want to use
  feature X and how to do it), the orchestrator environment (link to pipeline
  containerization page)
- how to handle multiple pipelines/workspaces on a local machine
- how to handle custom packages/integrations in the ZenML server

# ENDTODO

# Managing Multiple Environments in ZenML

# This page is WIP

In a ZenML deployment, you might have to manage multiple environments, such as your local development environment, the ZenML server environment, and the environment within the Docker images created when building pipelines. This guide will help you understand how to manage dependencies and configurations in these different environments.

- what kind of environments even exist when using ZenML: theres the client environment, the build environment (image builders), the server environment (tell them that this needs to have some stuff installed if they want to use feature X and how to do it), the orchestrator environment (link to pipeline containerization page)
- how to handle multiple pipelines/workspaces on a local machine
- how to handle custom packages/integrations in the ZenML server

## Local Development Environment

Your local development environment is where you write and test your ZenML pipelines. To manage dependencies in this environment, you can use your preferred package manager, such as `pip` or `poetry`. Make sure to install the ZenML package and any additional [ZenML integrations](broken-reference) you need for your pipelines.

To ensure that your local environment matches the requirements of your pipelines, you can create a virtual environment and install the necessary packages there. This will help you avoid conflicts with other projects and make it easier to share your environment with your team.

## ZenML Server Environment

The ZenML server environment is where the ZenML server runs and manages your pipelines. This environment should have the ZenML package and any required integrations installed, just like your local development environment. To manage dependencies in the ZenML server environment, you can use the same package manager as in your local environment.

To ensure that the ZenML server environment matches your local development environment, you can use a `requirements.txt` file to specify the exact package versions you need. This way, you can easily share the same environment configuration between your local development environment and the ZenML server.

## Docker Images for Pipeline Execution

When you build pipelines in ZenML, it creates Docker images that encapsulate the environment needed to run your pipeline steps. These images need to be configured with the correct dependencies and configurations to ensure that your pipeline runs smoothly.

ZenML automatically handles most of the Docker image configuration for you. It starts with a base image that has ZenML and Python installed and then installs any additional dependencies required by your pipeline. You can customize the Docker image configuration using the [DockerSettings](containerize-your-pipeline.md) class.

To manage dependencies in the Docker images, you can follow the steps described in the [Containerize your pipeline](containerize-your-pipeline.md) guide. This includes specifying additional pip dependencies, using a custom parent image, and customizing the build process.

## Summary

Managing multiple environments in a ZenML deployment involves keeping track of dependencies and configurations in your local development environment, the ZenML server environment, and the Docker images created for pipeline execution. By using package managers, specifying dependencies, and customizing Docker image configurations, you can ensure that your environments are consistent and your pipelines run smoothly.
