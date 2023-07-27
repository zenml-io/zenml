---
description: Learning about the ZenML server.
---

# Switch to production

Transitioning your machine learning pipelines to production means deploying your models on real-world data to make predictions that drive business decisions. To achieve this, you need an infrastructure that can handle the demands of running machine learning models at scale. However, setting up such an infrastructure involves careful planning and consideration of various factors, such as data storage, compute resources, monitoring, and security.

Moving to a production environment offers several benefits over staying local:

1. **Scalability**: Production environments are designed to handle large-scale workloads, allowing your models to process more data and deliver faster results.
2. **Reliability**: Production-grade infrastructure ensures high availability and fault tolerance, minimizing downtime and ensuring consistent performance.
3. **Collaboration**: A shared production environment enables seamless collaboration between team members, making it easier to iterate on models and share insights.

Despite these advantages, transitioning to production can be challenging due to the complexities involved in setting up the needed infrastructure.

This is where the **ZenML server** comes in. By providing seamless integration with various [MLOps tools](../../stacks-and-components/component-guide/integration-overview.md) and platforms, ZenML simplifies the process of moving your pipelines into production.

### ZenML Server

When you first get started with ZenML, it is based on the following architecture on your machine.

![Scenario 1: ZenML default local configuration](../../.gitbook/assets/Scenario1.png)

The SQLite database that you can see in this diagram is used to store information about pipelines, pipeline runs, stacks, and other configurations. In the previous pages, we used the `zenml up` command to spin up a local rest server to serve the dashboard as well. The diagram for this will look as follows:

![Scenario 2: ZenML with a local REST Server](../../.gitbook/assets/Scenario2.png)

{% hint style="info" %}
In Scenario 2, the `zenml up` command implicitly connects the client to the server.
{% endhint %}

In order to move into production, you will need to deploy this server somewhere centrally so that the different cloud stack components can read from and write to the server. Additionally, this also allows all your team members to connect to it and share stacks and pipelines.

![Scenario 3: Deployed ZenML Server](../../.gitbook/assets/Scenario3.2.png)

### Deploying a ZenML Server





<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
