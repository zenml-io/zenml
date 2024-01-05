---
description: Deploying ZenML is the first step to production.
---

# Deploying ZenML

When you first get started with ZenML, it is based on the following architecture on your machine:

![Scenario 1: ZenML default local configuration](../../.gitbook/assets/Scenario1.png)

The SQLite database that you can see in this diagram is used to store all the metadata we produced in the previous guide (pipelines, models, artifacts) etc.

In order to move into production, you will need to deploy this server somewhere centrally outside of your machine. This allows different infrastructure components to interact with, alongside enabling you to collaborate with your team members:

![Scenario 3: Deployed ZenML Server](../../.gitbook/assets/Scenario3.2.png)

## Choosing how to deploy ZenML

While there are many options on how to [deploy ZenML](../../deploying-zenml/), the two simplest ones are:

### Option 1: Sign up for a free ZenML Cloud Trial

[ZenML Cloud](https://zenml.io/cloud) is a managed SaaS solution that offers a one-click deployment for your ZenML server.
Click [here](https://cloud.zenml.io) to start a free trial.

On top of the one-click experience, ZenML Cloud also comes built in with additional features and a new dashboard, that might be beneficial to follow for this guide. You can always go back to self-hosting after your learning journey is complete.

### Option 2: Self-host ZenML on your cloud provider

As ZenML is open source, it is easy to [self-host it](../../deploying-zenml/zenml-self-hosted/). There is even a [ZenML CLI](../../deploying-zenml/zenml-self-hosted/deploy-with-zenml-cli.md) one-liner that deploys ZenML on a Kubernetes cluster, abstracting away all the infrastructure complexity. If you don't have an existing Kubernetes cluster, you can create it manually using the documentation for your cloud provider. For convenience, here are links for [AWS](https://docs.aws.amazon.com/eks/latest/userguide/create-cluster.html), [Azure](https://learn.microsoft.com/en-us/azure/aks/learn/quick-kubernetes-deploy-portal?tabs=azure-cli), and [GCP](https://cloud.google.com/kubernetes-engine/docs/how-to/creating-a-zonal-cluster#before\_you\_begin).

{% hint style="warning" %}
Once you have created your cluster, make sure that you configure your [kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl) client to connect to it.
{% endhint %}

You're now ready to deploy ZenML! Run the following command:

```bash
zenml deploy
```

You will be prompted to provide a name for your deployment and details like what cloud provider you want to deploy to, in addition to the username, password, and email you want to set for the default user — and that's it! It creates the database and any VPCs, permissions, and more that are needed.

{% hint style="info" %}
In order to be able to run the `deploy` command, you should have your cloud provider's CLI configured locally with permissions to create resources like MySQL databases and networks.
{% endhint %}

Reasonable defaults are in place for you already and if you wish to configure more settings, take a look at the next scenario that uses a config file.

## Connecting to a deployed ZenML

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>