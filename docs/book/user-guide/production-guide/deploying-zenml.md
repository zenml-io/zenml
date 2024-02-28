---
description: Deploying ZenML is the first step to production.
---

# Deploying ZenML

When you first get started with ZenML, it is based on the following architecture on your machine:

![Scenario 1: ZenML default local configuration](../../.gitbook/assets/Scenario1.png)

The SQLite database that you can see in this diagram is used to store all the metadata we produced in the previous guide (pipelines, models, artifacts, etc).

In order to move into production, you will need to deploy this server somewhere centrally outside of your machine. This allows different infrastructure components to interact with, alongside enabling you to collaborate with your team members:

![Scenario 3: Deployed ZenML Server](../../.gitbook/assets/Scenario3.2.png)

## Choosing how to deploy ZenML

While there are many options on how to [deploy ZenML](../../deploying-zenml/), the two simplest ones are:

### Option 1: Sign up for a free ZenML Cloud Trial

[ZenML Cloud](https://zenml.io/cloud) is a managed SaaS solution that offers a one-click deployment for your ZenML server.
Click [here](https://cloud.zenml.io/?utm_source=docs&utm_medium=referral_link&utm_campaign=cloud_promotion&utm_content=signup_link) to start a free trial.

On top of the one-click experience, ZenML Cloud also comes built-in with additional features and a new dashboard that might be beneficial to follow for this guide. You can always go back to self-hosting after your learning journey is complete.

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

To learn more about different options for [deploying ZenML, visit the deployment documentation](../../deploying-zenml/why-deploy-zenml.md).

## Connecting to a deployed ZenML

You can connect your local ZenML client with the ZenML Server using the ZenML CLI and the web-based login. This
can be executed with the command:

```bash
zenml connect --url <SERVER_URL>
```

where SERVER_URL is the host address of your ZenML deployment (e.g. `https://mydeployment.zenml.com`)

{% hint style="info" %}
Having trouble connecting with a browser? There are other ways to connect. Read [here](../advanced-guide/configuring-zenml/connecting-to-zenml.md) for more details.
{% endhint %}

This command will start a series of steps to validate the device from where you are connecting that will happen in your browser. After that, you're now locally connected to a remote ZenML. Nothing of your experience changes, except that all metadata that you produce will be tracked centrally in one place from now on.

{% hint style="info" %}
You can always go back to the local zenml experience by using `zenml disconnect`
{% endhint %}

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>