---
description: Deploy ZenML with one-click
---

## Collaboration with ZenML Overview

![Collaboration with ZenML Overview](../../assets/starter_guide/collaboration/04_cloud_collaboration_overview.png)

The ZenML Server is a distributed client-server ZenML deployment scenario in which multiple ZenML clients can connect to a remote service that provides persistent storage and acts as a central management hub for all ZenML operations involving Stack configurations, Stack Components and other ZenML objects.

A typical organization scenario with ZenML is to have Data Scientists or ML Engineers write pipelines, while the DevOps Engineers help them provision and
register stacks. Typically, one can go through a CI/CD workflow to run pipelines on various different stacks.

Working with a ZenML Server involves two main aspects: deploying the ZenServer somewhere and connecting to it from your ZenML client. In this section, we will learn about the simplest way to deploy ZenML with the CLI, but [there are other similarly easy options available](../../getting-started/deploying-zenml/deploying-zenml.md).

### Deploying with the CLI

The easiest and fastest way to get running on the cloud is by using the `deploy` CLI command. It currently only supports deploying to [Kubernetes](https://kubernetes.io/) on managed cloud services. 

Before we begin, it will help to understand the [architecture](../../getting-started/deploying-zenml/deploying-zenml.md#scenario-3-server-and-database-hosted-in-the-cloud) around the ZenML server and the database that it uses. Here is an illustration:

![ZenML with remote server and DB](../../assets/getting_started/Scenario3.1.png)

If you don't have an existing Kubernetes cluster, you have the following two options to set it up:

- Creating it manually using the documentation for your cloud provider. For convenience, here are links for [AWS](https://docs.aws.amazon.com/eks/latest/userguide/create-cluster.html), [Azure](https://learn.microsoft.com/en-us/azure/aks/learn/quick-kubernetes-deploy-portal?tabs=azure-cli) and [GCP](https://cloud.google.com/kubernetes-engine/docs/how-to/creating-a-zonal-cluster#before_you_begin).
- Using [stack recipes](../../advanced-guide/practical/stack-recipes.md) that set up a cluster along with other tools that you might need in your cloud stack like artifact stores, and secret managers. Take a look at all [available stack recipes](https://github.com/zenml-io/mlops-stacks#-list-of-recipes) to see if there's something that works for you.

> **Note**
> Once you have created your cluster, make sure that you configure your [kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl) client to talk to it. If you have used stack recipes, this step is already done for you!

You're now ready to deploy ZenML! Run the following command:
```
zenml deploy
```

You will be prompted to provide a name for your deployment and details like what cloud provider you want to deploy to, in addition to the username, password and email you want to set for the default user — and that's it! It creates the database and any VPCs, permissions and more that is needed.

> **Note**
> To be able to run the deploy command, you should have your cloud provider's CLI configured locally with permissions to create resources like MySQL databases and networks.

Reasonable defaults are in place for you already and if you wish to configure more settings, take a look at the next scenario that uses a config file.

If you would like more control over the `zenml deploy` command, then read [option 2 here](../../getting-started/deploying-zenml/cli.md#option-2-using-existing-cloud-resources).