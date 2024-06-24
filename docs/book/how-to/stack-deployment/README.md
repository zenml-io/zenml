---
description: Deploying your stack components directly from the ZenML CLI
---

# ⚒️ Manage stacks

The first step in running your pipelines on remote infrastructure is to deploy all the components that you would need, like an MLflow tracking server, a Seldon Core model deployer, and more to your cloud.

This can bring plenty of benefits like scalability, reliability, and collaboration. ZenML eases the path to production by providing a seamless way for all tools to interact with others through the use of abstractions. However, one of the most painful parts of this process, from what we see on our Slack and in general, is the deployment of these stack components.

## Deploying and managing MLOps tools is tricky 😭😵‍💫

It is not trivial to set up all the different tools that you might need for your pipeline.

* 🌈 Each tool comes with a certain set of requirements. For example, a Kubeflow installation will require you to have a Kubernetes cluster, and so would a Seldon Core deployment.
* 🤔 Figuring out the defaults for infra parameters is not easy. Even if you have identified the backing infra that you need for a stack component, setting up reasonable defaults for parameters like instance size, CPU, memory, etc., needs a lot of experimentation to figure out.
* 🚧 Many times, standard tool installations don't work out of the box. For example, to run a custom pipeline in Vertex AI, it is not enough to just run an imported pipeline. You might also need a custom service account that is configured to perform tasks like reading secrets from your secret store or talking to other GCP services that your pipeline might need.
* 🔐 Some tools need an additional layer of installations to enable a more secure, production-grade setup. For example, a standard MLflow tracking server deployment comes without an authentication frontend which might expose all of your tracking data to the world if deployed as-is.
* 🗣️ All the components that you deploy must have the right permissions to be able to talk to each other. When you run your pipeline, it is inevitable that some components would need to communicate with the others. For example, your workloads running in a Kubernetes cluster might require access to the container registry or the code repository, and so on.
* 🧹 Cleaning up your resources after you're done with your experiments is super important yet very challenging. Many of the components need a range of other resources to work which might slide past your radar if you're not careful. For example, if your Kubernetes cluster has made use of Load Balancers, you might still have one lying around in your account even after deleting the cluster, costing you money and frustration.

All of these points make taking your pipelines to production a more difficult task than it should be. We believe that the expertise in setting up these often-complex stacks shouldn't be a prerequisite to running your ML pipelines.

Thus, to make even this process easier for our users, we have created the `deploy` CLI which allows you to quickly get started with a full-fledged MLOps stack using only a few commands. You can choose to deploy individual stack components through the stack-component CLI or deploy a stack with multiple components together (a tad more manual steps).

## What is `mlstacks`?

[MLStacks](https://mlstacks.zenml.io) is a [Python package](https://pypi.org/project/mlstacks/) that allows you to quickly spin up MLOps infrastructure using Terraform. It is designed to be used with [ZenML](https://zenml.io), but can be used with any MLOps tool or platform.

The ZenML CLI has special subcommands that allow you to deploy individual stack components as well as whole stacks using MLStacks. These stacks will be useful for you if:

* You are at the start of your MLOps journey, and would like to explore different tools.
* You are looking for guidelines for production-grade deployments.

## Installing the mlstacks extra

To install `mlstacks`, either run `pip install mlstacks` or `pip install "zenml[mlstacks]"` to install it along with ZenML.

MLStacks uses Terraform on the backend to manage infrastructure. You will need to have Terraform installed. Please visit [the Terraform docs](https://learn.hashicorp.com/tutorials/terraform/install-cli#install-terraform) for installation instructions.

MLStacks also uses Helm to deploy Kubernetes resources. You will need to have Helm installed. Please visit [the Helm docs](https://helm.sh/docs/intro/install/#from-script) for installation instructions.

## Deploying a stack component

The ZenML CLI allows you to deploy individual stack components using the `deploy` subcommand which is implemented for all supported stack components. You can find the list of supported stack components [here](../stack-deployment/README.md).

## Deploying a stack

For deploying a full stack, use the `zenml stack deploy` command. See the [stack deployment](deploy-a-stack-using-mlstacks.md) page for more details of which cloud providers and stack components are supported.

## How does `mlstacks` work?

MLStacks is built around the concept of a stack specification. A stack specification is a YAML file that describes the stack and includes references to component specification files. A component specification is a YAML file that describes a component. (Currently all deployments of components (in various combinations) must be defined within the context of a stack.)

ZenML handles the creation of stack specifications for you when you run one of the `deploy` subcommands using the CLI. A valid specification is generated and used by `mlstacks` to deploy your stack using Terraform. The Terraform definitions and state are stored in your global configuration directory along with any state files generated while deploying your stack.

Your configuration directory could be in a number of different places depending on your operating system, but read more about it in the [Click docs](https://click.palletsprojects.com/en/8.1.x/api/#click.get\_app\_dir) to see which location applies to your situation.

<table data-view="cards"><thead><tr><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td><mark style="color:purple;"><strong>Deploy stack components individually</strong></mark></td><td>Individually deploying different stack components.</td><td><a href="deploy-a-stack-component.md">deploy-a-stack-component.md</a></td></tr><tr><td><mark style="color:purple;"><strong>Deploy a stack with multiple components using mlstacks</strong></mark></td><td>Deploying an entire stack with ZenML's `mlstacks` package.</td><td><a href="../../how-to/stack-deployment/deploy-a-stack-using-mlstacks.md">../../how-to/stack-deployment/deploy-a-stack-using-mlstacks.md</a></td></tr><tr><td><mark style="color:purple;"><strong>Contribute new components or flavors</strong></mark></td><td>Creating your custom stack component solutions.</td><td><a href="../../../../CONTRIBUTING.md">CONTRIBUTING.md</a></td></tr></tbody></table>

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
