---
description: Running pipelines in the MLOps Platform Sandbox.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Use the Sandbox

The [MLOps Platform Sandbox](https://sandbox.zenml.io) is a temporary MLOps platform that includes ZenML, [MLflow](https://mlflow.org), [Kubeflow](https://www.kubeflow.org/), and [Minio](https://min.io/). Its purpose is to showcase the simplicity of creating a production-ready machine-learning solution using popular open-source tools. The Sandbox is designed for learning and experimentation, not for commercial projects or large-scale production use. It offers users a controlled environment to explore MLOps tools and processes before building their custom MLOps stack based on their specific requirements.

## How does the Sandbox work?

After signing up, a user "creates a sandbox" which provisions the following services on a cluster managed by the ZenML team:

* [MLflow](https://mlflow.org): An [experiment tracker](../component-guide/experiment-trackers/experiment-trackers.md) for tracking metadata.
* [Kubeflow](https://kubeflow.org): An [orchestrator](../component-guide/orchestrators/orchestrators.md) for running ML workloads on Kubernetes.
* [Minio](https://min.io/): An [artifact store](../component-guide/artifact-stores/artifact-stores.md) for storing artifacts produced by pipelines.
* [ZenML](https://zenml.io): The MLOps framework that integrates everything.

Each sandbox comes with limited computing and storage resources. The ZenML service included with each sandbox has the following features:

* A [registered stack with other services](../starter-guide/understand-stacks.md), including all credentials as [secrets](../../platform-guide/set-up-your-mlops-platform/use-the-secret-store/use-the-secret-store.md).
* A set of an example pipeline [execution environment builds](manage-environments.md#execution-environments). These Docker images are hosted on Dockerhub and make running the example pipelines easy.
* A connected [code repository](connect-your-git-repository.md) containing the code for the example pipelines. This repository is the official ZenML repository (with the code located in the [examples](https://github.com/zenml-io/zenml/tree/main/examples) directory).

In order to run the example pipelines, users need to download the repository locally and execute a pipeline with a supported build. The Sandbox UI offers a convenient interface for copying the relevant commands. The [starter guide](../starter-guide/switch-to-production.md) also provides more details on running these example pipelines.

![ZenML Sandbox Gitbook commands](/docs/book/.gitbook/assets/zenml_sandbox_step_3_commands.png)

## How do I use the Sandbox to run custom pipelines?

As discussed above, the sandbox provides pre-built pipelines for users to run.
If you want to try running these pipelines first, please [visit this
page](../starter-guide/switch-to-production.md) in the starter guide to learn
how to do this. The limitation on running custom pipelines is in place to
control costs and demonstrate how MLOps engineers can enforce rules through a
central control plane.

You might nevertheless be interested in using the resources provisioned in the Sandbox to run your own pipelines. There are two ways to do this:

### Run pipelines without custom dependencies

If you have code that uses the same dependencies as the ones provided in the examples docs, you can simply update the example pipeline code (or even add new pipelines) by pushing to a git repository, and reusing existing [environment builds](containerize-your-pipeline.md#reuse-docker-image-builds-from-previous-runs) of the example pipelines.

Of course, in order to be able to do that, you need to be able to push to the code repository. You can do this by following these steps:

1. Fork an existing Github repository or create a new one.

2. Push your code to the repository. Alternatively, you can copy the example code from the ZenML repository to your new repository and make the necessary modifications.

3. Register the new code repository with ZenML by following [code repository guide](../component-guide/code-repositories/code-repositories.md).

4. Reuse the builds from the example code repository to execute your own code using the [guide to build reuse](containerize-your-pipeline.md#reuse-docker-image-builds-from-previous-runs).

Read more about how to connect a git repository to ZenML [here](connect-your-git-repository.md).

After that is done, you can change the code and run the pipeline with your chosen execution environment build. Learn more about reusing execution environments [here](containerize-your-pipeline.md#reuse-docker-image-builds-from-previous-runs).

{% hint style="warning" %}
Please note that this will only work if you are using the same dependencies as the example code. If you are using different dependencies, such as a different framework or stack components, you will need to build and push your own Docker images to a container registry as described in the next section.
{% endhint %}

### Run pipelines with custom dependencies

The sandbox is a pre-configured stack that connects to and uses ZenML's public container registry. This allows you to execute pipelines using the provided example code and dependencies, eliminating the need to build and push Docker images to a container registry on your own. However, if you wish to run your own code with custom dependencies, you must register a new stack that uses a public container registry where you have `write` access and the repository is `publicly accessible` so that Kubeflow can pull the images.

Let's take [the Docker Hub registry](https://hub.docker.com/) as an example. To proceed, create a Docker Hub account and establish a new repository. Next, create a new stack component that uses this container registry. You can refer to the [container registry stack component guide](../component-guide/container-registries/container-registries.md) for detailed instructions.

Once the stack component is created, you can register a new stack that incorporates this component. Execute the following command:

```shell
zenml stack register my_stack \
  -o sandbox-kubeflow \
  -a sandbox-minio \
  -e sandbox-mlflow \
  -dv sandbox-validator \
  -c <MY_CONTAINER_REGISTRY> \
  --set
```
Replace `<MY_CONTAINER_REGISTRY>` with the specific name of the container registry used in your stack

## What to do when your sandbox runs out?

The Sandbox will only run for 4 hours. After that, it will be deleted. If you want to continue to use ZenML in a cloud deployment you can either:

<table data-view="cards"><thead><tr><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td><mark style="color:purple;"><strong>Register a new Sandbox</strong></mark></td><td>Create and utilize a brand new Sandbox instance</td><td><a href="https://sandbox.zenml.io">https://sandbox.zenml.io</a></td></tr><tr><td><mark style="color:purple;"><strong>Extend your Sandbox time limit</strong></mark></td><td>Fill out a form to extend the time limit of your Sandbox instances</td><td><a href="https://zenml.io/extend-sandbox">https://zenml.io/extend-sandbox</a></td></tr><tr><td><mark style="color:purple;"><strong>Deploy your own cloud stack</strong></mark></td><td>Deploy and use a stack on a cloud environment</td><td><a href="../../platform-guide/set-up-your-mlops-platform/deploy-and-set-up-a-cloud-stack/deploy-a-stack-post-sandbox.md">deploy-a-stack-post-sandbox.md</a></td></tr></tbody></table>
