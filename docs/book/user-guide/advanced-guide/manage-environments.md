---
description: Navigating multiple development environments.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Manage multiple environments through which code propagates

{% hint style="warning" %}
**Note:** This page is a work in progress (WIP) and is currently under development. If you have any questions or need
assistance, please join our [Slack community](https://zenml.io/slack).
{% endhint %}

ZenML deployments often involve multiple environments. This guide helps you manage dependencies and configurations across these environments.

Here is a visual overview of the different environments:

<figure><img src="../../.gitbook/assets/SystemArchitecture.png" alt=""><figcaption><p>Left box is the client environment, middle is the zenml server environment, and the right most contains the build environments</p></figcaption></figure>

## Client Environment

The client environment is where the ZenML pipelines are *started*, i.e., where you call the pipeline function (typically in a `run.py` script). There are different types of client environments:

- A local development environment
- A [CI runner](../../platform-guide/set-up-your-mlops-platform/productionalize-with-ci-cd-ct.md) in production. 
- A `runner` image orchestrated by the ZenML server to start pipelines.

In all the environments, you should use your preferred package manager (e.g., `pip` or `poetry`) to manage dependencies. Ensure you install the ZenML package and any required [integrations](../component-guide/component-guide.md).

The client environment typically follows these key steps when starting a pipeline:

1. Generating an intermediate pipeline representation.
2. Creating or triggering [pipeline and step build environments](manage-environments.md#image-builder-environment) if running
   remotely.
3. Triggering a run in the [orchestrator](../component-guide/orchestrators/orchestrators.md).

## ZenML Server Environment

The ZenML server environment is a FastAPI application managing pipelines and metadata. It includes the ZenML Dashboard
and is accessed when you [deploy ZenML](../../platform-guide/set-up-your-mlops-platform/deploy-zenml/deploy-zenml.md).
To manage dependencies, install them
during [ZenML deployment](../../platform-guide/set-up-your-mlops-platform/deploy-zenml/deploy-zenml.md), but only if you
have custom integrations, as most are built-in.

## Execution Environments

When running locally, there is no real concept of a `execution` environment as the client, server, and execution environment are
all the same. However, when running a pipeline remotely, ZenML needs to transfer your code and
environment over to the remote [orchestrator](../component-guide/orchestrators/orchestrators.md). In order to achieve this, ZenML builds docker images known
as `execution environments`.

ZenML handles the Docker image configuration, creation, and pushing, starting with a [base image](https://hub.docker.com/r/zenmldocker/zenml) containing ZenML and Python,
then adding pipeline dependencies. To manage the Docker image configuration, follow the steps in
the [containerize your pipeline](containerize-your-pipeline.md) guide, including specifying additional pip dependencies,
using a custom parent image, and customizing the build process.

The execution environments do not need to be built each time a pipeline is run - you
can [reuse builds from previous runs to save time](containerize-your-pipeline.md#reuse-docker-image-builds-from-previous-runs).

## Image Builder Environment

By default, execution environments are created locally in the [client environment](#client-environment) using the local
Docker client. However, this requires Docker installation and permissions. ZenML
offers [image builders](../component-guide/image-builders/image-builders.md), a
special [stack component](../starter-guide/understand-stacks.md), allowing users to build and push docker images in a different specialized *image builder environment*.

Note that even if you don't configure an image builder in your stack, ZenML still uses
the [local image builder](../component-guide/image-builders/local.md) to retain consistency across all builds. In this case, the image builder environment is the same as the client environment.
