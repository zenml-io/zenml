---
description: Navigating multiple development environments.
---

# Manage multiple environments through which code propagates

{% hint style="warning" %}
**Note:** This page is a work in progress (WIP) and is currently under development. If you have any questions or need
assistance, please join our [Slack community](https://zenml.io/slack).
{% endhint %}

ZenML deployments often involve multiple environments, such as local development, ZenML server, and `build`
environments (image builders). This guide helps you manage dependencies and configurations across these environments.

Here is a visual overview of the different environments:

<figure><img src="../../.gitbook/assets/SystemArchitecture.png" alt=""><figcaption><p>Left box is the client environment, middle is the zenml server environment, and the right most contains the build environments</p></figcaption></figure>

## Client Environment

The client environment is where ZenML pipelines run, typically a local development environment or
a [CI runner](../../platform-guide/set-up-your-mlops-platform/productionalize-with-ci-cd-ct.md) in production. Use your
preferred package manager (e.g., `pip` or `poetry`) to manage dependencies, and create a virtual environment to install
packages, avoiding conflicts and facilitating sharing. Ensure you install the ZenML package and any
required [integrations](../component-guide/component-guide.md).

Key steps in a pipeline run include:

1. Generating an intermediate pipeline representation.
2. Creating or triggering [pipeline and step build environments](manage-environments.md#build-environments) if running
   remotely.
3. Triggering a run in the [orchestrator](../component-guide/orchestrators/orchestrators.md).

## ZenML Server Environment

The ZenML server environment is a FastAPI application managing pipelines and metadata. It includes the ZenML Dashboard
and is accessed when you [deploy ZenML](../../platform-guide/set-up-your-mlops-platform/deploy-zenml/deploy-zenml.md).
To manage dependencies, install them
during [ZenML deployment](../../platform-guide/set-up-your-mlops-platform/deploy-zenml/deploy-zenml.md), but only if you
have custom integrations, as most are built-in.

## Build Environments

When running locally, there is no real concept of a `build` environment as the client, server, and build environment are
all the same. However, when running a pipeline with a remote orchestrator, ZenML needs to transfer your code and
environment over to the remote orchestrator. In order to achieve this, ZenML creates docker images known
as `build environments`. There are two types of build environments:

* **Pipeline build environment**: A Docker image for the main pipeline orchestration node.
* **Step build environment**: A Docker image for individual steps.

ZenML handles Docker image configuration, creation, and pushing, starting with a base image containing ZenML and Python,
then adding pipeline dependencies. To manage the Docker image configuration, follow the steps in
the [Containerize your pipeline](containerize-your-pipeline.md) guide, including specifying additional pip dependencies,
using a custom parent image, and customizing the build process.

The `build` environments do not need to be built each time a pipeline is run - you
can [reuse builds from previous runs to save time](containerize-your-pipeline.md#reuse-docker-image-builds-from-previous-runs)
.

### Customizing Build Image Creation (Image Builders)

By default, build environments are created locally in the [client environment](#client-environment) using the local
Docker client. However, this requires Docker installation and permissions. ZenML
offers [image builders](../component-guide/image-builders/), a
special [stack component](../starter-guide/understand-stacks.md), allowing users to configure image building and
pushing.

Note that even if you don't configure an image builder in your stack, ZenML still uses
the [local image builder](../component-guide/image-builders/local.md) to retain
consistency across all builds.
