---
description: Running your pipelines on production infrastructure
---

# Switch to production

Transitioning your machine learning pipelines to production means deploying your models on real-world data to make predictions that drive business decisions. To achieve this, you need an infrastructure that can handle the demands of running machine learning models at scale. However, setting up such an infrastructure involves careful planning and consideration of various factors, such as data storage, compute resources, monitoring, and security.

Moving to a production environment offers several benefits over staying local:

1. **Scalability**: Production environments are designed to handle large-scale workloads, allowing your models to process more data and deliver faster results.
2. **Reliability**: Production-grade infrastructure ensures high availability and fault tolerance, minimizing downtime and ensuring consistent performance.
3. **Collaboration**: A shared production environment enables seamless collaboration between team members, making it easier to iterate on models and share insights.

Despite these advantages, transitioning to production can be challenging due to the complexities involved in setting up the needed infrastructure.

This is where ZenML comes in. By providing seamless integration with various [MLOps tools](../component-guide/integration-overview.md) and platforms, ZenML simplifies the process of moving your pipelines into production.

There are several options how you can deploy your own infrastructure with ZenML:
- With the [deploy CLI](../../platform-guide/set-up-your-mlops-platform/deploy-and-set-up-a-cloud-stack/deploy-and-set-up-a-cloud-stack.md), you can quickly set up a full-fledged MLOps stack with just a few commands. 
- You have the option to deploy individual stack components through the [stack-component CLI](../../platform-guide/set-up-your-mlops-platform/deploy-and-set-up-a-cloud-stack/deploy-a-stack-component.md)
- You can [deploy a stack with multiple components](../../platform-guide/set-up-your-mlops-platform/deploy-and-set-up-a-cloud-stack/deploy-a-stack-using-stack-recipes.md) at once using Terraform stack recipes.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
