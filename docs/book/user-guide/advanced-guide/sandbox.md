---
description: Running pipelines in the ZenML Sandbox.
---

# How to use the Sandbox to run pipelines

At this point you may have tried out some of the pre-built pipelines in the
ZenML Sandbox. (If you want to try this first, please [visit this page](..//starter-guide/switch-to-production.md) in the
Starter Guide to learn how to do this). You might be interested in using the
resources provisioned in the Sandbox to run your own pipelines. This guide will
show you how to do this.

## Prerequisites

- Register a new stack
- register a new container registry (which you are allowed to pull from and push
  to) -- also Kubeflow must be allowed to pull from it, so it can only be a
  public registry

## Set up your code repository

- Register a fork or a new code repository with new token that allows them to
  push
- use the build we created but you have to use the specified dependencies in the builds

## More...

... other things to bo?

## What do do when your sandbox runs out?

The sandbox is only available for 8 hours. After that, it will be deleted. If
you want to continue to use ZenML in a cloud deployment you can either:

- [Register a new sandbox](https://sandbox.zenml.io/)
- [Deploy your own cloud stack](../../platform-guide/set-up-your-mlops-platform/deploy-and-set-up-a-cloud-stack/deploy-a-stack-post-sandbox.md)

For the second option you can use ZenML's Stack Recipes to deploy a stack that
suits your custom use cases. For more information on how to do this, please
[visit our guide to get going](../../platform-guide/set-up-your-mlops-platform/deploy-and-set-up-a-cloud-stack/deploy-a-stack-post-sandbox.md) with this.
