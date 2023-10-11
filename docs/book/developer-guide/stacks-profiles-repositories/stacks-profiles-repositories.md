---
description: What are stacks, profiles, and repositories in ZenML
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


Machine learning in production is not just about designing and training models. It is a fractured space consisting of a wide variety of tasks ranging from experiment tracking to orchestration, from model deployment to monitoring, from drift detection to feature stores and much, much more than that. Even though there are already some seemingly well-established solutions for these tasks, it can become increasingly difficult to establish a running production system in a reliable and modular manner once all these solutions are brought together.

This is a problem which is especially critical when switching from a research setting to a production setting. 
Due to a lack of standards, the time and resources invested in proof of concepts frequently go completely to waste, because the initial system can not easily be transferred to a production-grade setting.

At **ZenML**, we believe that this is one of the most important and challenging problems in the field of MLOps, and it can be solved with a set of standards and well-structured abstractions. Owing to the nature of MLOps, it is essential that these abstractions not only cover concepts such as pipelines and steps but also the infrastructure elements on which the pipelines run.

Taking this into consideration, ZenML provides additional abstractions that
help you simplify infrastructure configuration and management:
- [Stacks](./stack.md) represent different configurations of MLOps tools and 
infrastructure; Each stack consists of multiple
**Stack Components** that each come in several **Flavors**,
- [Profiles](./profile.md) manage these stacks and enable having various different
ZenML configurations on the same machine,
- [Repositories](./repository.md) link stacks to the pipeline and step code of 
your ML projects.
