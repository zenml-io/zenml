---
description: Simple, reproducible MLOps.
---

# ZenML 101

**ZenML** is an extensible, open-source MLOps framework to create production-ready machine learning pipelines. Built for data scientists, it has a simple, flexible syntax, is cloud- and tool-agnostic, and has interfaces/abstractions that are catered towards ML workflows.

At its core, **ZenML pipelines execute ML-specific workflows** from sourcing data to splitting, preprocessing, training, all the way to the evaluation of results and even serving. There are many built-in batteries to support common ML development tasks. ZenML is not here to replace the great tools that solve these individual problems. Rather, it **integrates natively with popular ML tooling** and gives standard abstraction to write your workflows.

{% hint style="success" %}
Read more about Why ZenML exists [here](why-zenml.md).
{% endhint %}

## Who is ZenML for?

![Before and after ZenML](../assets/sam-side-by-side-full-text.png)

ZenML is created for data science / machine learning teams that are not only engaged in training models, but also in putting them out in production. Production can mean many things, but examples would be:

* If you are using a model to generate analysis periodically for any business process.
* If you are using models as a software service to serve predictions.
* If you are trying to understand patterns using machine learning for any business process.

In all of the above, there will be a team that is engaged with creating, deploying, managing and improving the entire process. You always want the best results, the best models, and the most robust and reliable results. This is where ZenML can help.

In terms of user personas, ZenML is created for **producers of the models.** This role is classically known as 'data scientist' in the industry and can range from research-minded individuals to more engineering-driven people. The goal of ZenML is to enable these practitioners to **own** their models from experimentation phases to deployment and beyond.

## Why should I use ZenML?

ZenML pipelines are designed to be written early on the development lifecycle. Data scientists can explore their pipelines as they develop towards production, switching stacks from local to cloud deployments with ease. You can read more about why we started building ZenML [on our blog](https://blog.zenml.io/why-zenml/). By using ZenML in the early stages of your project, you get the following benefits:

- **Reproducibility** of training and inference workflows
- A **simple and clear** way to represent the steps of your pipeline in code
- **Plug-and-play integrations**: bring all your favorite tools together
- Easy switching between local and cloud stacks
- Painless **deployment and configuration** of infrastructure
- **Scale up** your stack transparently and logically to suit your training and deployment needs

## Okay, how can I learn more?

A good place to go from this point is to:

* Understand what is so special about [ZenML](why-zenml.md).
* Get up and running with your [first pipeline](quickstart-guide.md).
* Read more about [core concepts](core-concepts.md) to inform your decision about using **ZenML.**

## Get involved!

If you're just not ready to use **ZenML** for whatever reason, but still would like to stay updated, then the best way is to [star the GitHub repository](https://github.com/zenml-io/zenml)! You can then keep up with the latest and greatest from **ZenML**, and it would help us tremendously to get more people using it.

Contributions are also welcome! Please read our [contributing guide](../../../CONTRIBUTING.md) to get started.
