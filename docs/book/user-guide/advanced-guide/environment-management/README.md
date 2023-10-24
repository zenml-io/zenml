---
description: Navigating multiple development environments.
---

# Environment management

{% hint style="warning" %}
**Note:** This page is a work in progress (WIP) and is currently under development. If you have any questions or need assistance, please join our [Slack community](https://zenml.io/slack).
{% endhint %}

ZenML deployments often involve multiple environments. This guide helps you manage dependencies and configurations across these environments.

Here is a visual overview of the different environments:

<figure><img src="https://github.com/zenml-io/zenml/blob/release/0.45.4/docs/book/user-guide/.gitbook/assets/SystemArchitecture.png" alt=""><figcaption><p>Left box is the client environment, middle is the zenml server environment, and the right most contains the build environments</p></figcaption></figure>

## Client Environment

The client environment is where the ZenML pipelines are _started_, i.e., where you call the pipeline function (typically in a `run.py` script). There are different types of client environments:

* A local development environment
* A CI runner in production.
* A `runner` image orchestrated by the ZenML server to start pipelines.

In all the environments, you should use your preferred package manager (e.g., `pip` or `poetry`) to manage dependencies. Ensure you install the ZenML package and any required [integrations](../../../stacks-and-components/component-guide/).

The client environment typically follows these key steps when starting a pipeline:

1. Generating an intermediate pipeline representation.
2. Creating or triggering [pipeline and step build environments](./#image-builder-environment) if running remotely.
3. Triggering a run in the [orchestrator](../../../stacks-and-components/component-guide/orchestrators/).

## ZenML Server Environment

The ZenML server environment is a FastAPI application managing pipelines and metadata. It includes the ZenML Dashboard and is accessed when you [deploy ZenML](../../../deploying-zenml/zenml-self-hosted/). To manage dependencies, install them during [ZenML deployment](../../../deploying-zenml/zenml-self-hosted/), but only if you have custom integrations, as most are built-in.

## Execution Environments

When running locally, there is no real concept of a `execution` environment as the client, server, and execution environment are all the same. However, when running a pipeline remotely, ZenML needs to transfer your code and environment over to the remote [orchestrator](../../../stacks-and-components/component-guide/orchestrators/). In order to achieve this, ZenML builds docker images known as `execution environments`.

ZenML handles the Docker image configuration, creation, and pushing, starting with a [base image](https://hub.docker.com/r/zenmldocker/zenml) containing ZenML and Python, then adding pipeline dependencies. To manage the Docker image configuration, follow the steps in the [containerize your pipeline](containerize-your-pipeline.md) guide, including specifying additional pip dependencies, using a custom parent image, and customizing the build process.

The execution environments do not need to be built each time a pipeline is run - you can [reuse builds from previous runs to save time](containerize-your-pipeline.md#reuse-docker-image-builds-from-previous-runs).

## Image Builder Environment

By default, execution environments are created locally in the [client environment](./#client-environment) using the local Docker client. However, this requires Docker installation and permissions. ZenML offers [image builders](../../../stacks-and-components/component-guide/image-builders/), a special [stack component](../../starter-guide/understand-stacks.md), allowing users to build and push docker images in a different specialized _image builder environment_.

Note that even if you don't configure an image builder in your stack, ZenML still uses the [local image builder](../../../stacks-and-components/component-guide/image-builders/local.md) to retain consistency across all builds. In this case, the image builder environment is the same as the client environment.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
