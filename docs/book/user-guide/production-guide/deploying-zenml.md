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

While there are many options on how to [deploy ZenML](../../getting-started/deploying-zenml/README.md), the two simplest ones are:

### Option 1: Sign up for a free ZenML Pro Trial

[ZenML Pro](https://zenml.io/pro) comes as a managed SaaS solution that offers a one-click deployment for your ZenML server.

If you have the ZenML Python client already installed, you can fast-track to connecting to a trial ZenML Pro instance by simply running:

```bash
zenml login --pro
```

Alternatively, click [here](https://cloud.zenml.io/?utm\_source=docs\&utm\_medium=referral\_link\&utm\_campaign=cloud\_promotion\&utm\_content=signup\_link) to start a free trial.

On top of the one-click SaaS experience, ZenML Pro also comes built-in with additional features and a new dashboard that might be beneficial to follow for this guide. You can always go back to self-hosting after your learning journey is complete.

### Option 2: Self-host ZenML on your cloud provider

As ZenML is open source, it is easy to [self-host it](../../getting-started/deploying-zenml/README.md) in a Kubernetes cluster. If you don't have an existing Kubernetes cluster, you can create it manually using the documentation for your cloud provider. For convenience, here are links for [AWS](https://docs.aws.amazon.com/eks/latest/userguide/create-cluster.html), [Azure](https://learn.microsoft.com/en-us/azure/aks/learn/quick-kubernetes-deploy-portal?tabs=azure-cli), and [GCP](https://cloud.google.com/kubernetes-engine/docs/how-to/creating-a-zonal-cluster#before\_you\_begin).

To learn more about different options for [deploying ZenML, visit the deployment documentation](../../getting-started/deploying-zenml/README.md).

## Connecting to a deployed ZenML

You can connect your local ZenML client with the ZenML Server using the ZenML CLI and the web-based login. This can be executed with the command:

```bash
zenml login <server-url>
```

{% hint style="info" %}
Having trouble connecting with a browser? There are other ways to connect. Read [here](../../how-to/connecting-to-zenml/README.md) for more details.
{% endhint %}

This command will start a series of steps to validate the device from where you are connecting that will happen in your browser. After that, you're now locally connected to a remote ZenML. Nothing of your experience changes, except that all metadata that you produce will be tracked centrally in one place from now on.

{% hint style="info" %}
You can always go back to the local zenml experience by using `zenml logout`
{% endhint %}

## Further resources

To learn more about deploying ZenML, check out the following resources:

- [Deploying ZenML](../../getting-started/deploying-zenml/README.md): an overview of
  the different options for deploying ZenML and the system architecture of a
  deployed ZenML instance.
- [Full how-to guides](../../getting-started/deploying-zenml/README.md): guides on how to
  deploy ZenML on Docker or Hugging Face Spaces or Kubernetes or some other cloud
  provider.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
