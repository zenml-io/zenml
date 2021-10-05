---
description: 'Simple, reproducible MLOps.'
---

# ZenML 101

**ZenML** is an extensible, open-source MLOps framework to create production-ready machine learning pipelines. It has a simple, flexible syntax, is cloud and tooling agnostic, and has interfaces/abstractions that are catered towards ML workflows. 

At its core, **ZenML**  pipelines execute ML-specific workflows from **sourcing data** to **splitting, preprocessing, training**, all the way to the **evaluation of results** and even **serving**. There are many built-in batteries as things progress in ML development. ZenML is not here to replace the great tools that solve the individual problems. Rather, it integrates natively with many popular ML tooling, and gives standard abstraction to write your workflows.

{% hint style="success" %}
Read more about Why ZenML exists [here](why-zenml.md).
{% endhint %}

## Who is ZenML for?

ZenML is created for data science / machine learning teams that are engaged in not only training models, but also putting them out in production. Production can mean many things, but examples would be:

* If you are using a model to generate analysis periodically for any business process.
* If you are using models as a software service to serve predictions.
* If you are trying to understand patterns using machine learning for any business process.

In all of the above, there will be team that is engaged with creating, deploying, managing and improving the entire process. You always want the best results, the best models, and the most robust and reliable results. This is where ZenML can help.

In terms of user persona, ZenML is created for **producers of the models.** This role is classically known as 'data scientist' in the industry and can range from research-minded individuals to more engineering-driven people. The goal of ZenML is to enable these practitioners to **own** their models until deployment and beyond.

## What do I get out of it?

By using ZenML at the early stages of development, you get the following features:

* **Reproducibility** of training and inference workflows.  __
* Managing ML **metadata**, including versioning data, code, and models.  
* Getting an **overview** of your ML development, with a reliable link between training and deployment.  __
* Maintaining **comparability** between ML models.  
* **Scaling** ML training/inference to large datasets.  __
* Retaining code **quality** alongside development velocity.  
* **Reusing** code/data and reducing waste. 
* Keeping up with the **ML tooling landscape** with standard abstractions and interfaces.

## Okay, how can I learn more?

A good place to go from this point is to:

* Understand [what is so special about ZenML](why-zenml.md).
* Take a look at some of the [key decisions that we made while building ZenML.](framework-design.md)
* Get up and running with your [first pipeline](https://github.com/zenml-io/zenml/tree/f912d2d512477e6ed84e839259d42cb73eeedf2b/docs/book/starter-guide/quickstart.md) with our [starter guide](https://github.com/zenml-io/zenml/tree/f912d2d512477e6ed84e839259d42cb73eeedf2b/docs/book/starter-guide/repository.md).
* Read more about [core concepts](core/core-concepts.md) to inform your decision about using **ZenML.**

## Get involved!

If you're just not ready to use **ZenML** for whatever reason, but still would like to stay updated, then the best way is to [star the GitHub repository](https://github.com/zenml-io/zenml)! You can then keep up with the latest and greatest from **ZenML**, and it would help us tremendously to get more people using it.

Contributions are also welcome! Please read our [contributing guide](https://github.com/zenml-io/zenml/blob/main/CONTRIBUTING.md) to get started.

