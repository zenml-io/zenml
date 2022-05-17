---
description: Tracking the execution of your pipelines/steps
---

The configuration of each pipeline, step and produced artifacts are all tracked
within the metadata store. ZenML puts a lot of emphasis on guaranteed tracking 
of inputs across pipeline steps. The strict, fully automated, and deeply 
built-in tracking enables some powerful features - e.g. reproducibility.

{% hint style="warning" %}
**Base abstraction in progress!**

We are actively working on the base abstraction for the metadata stores, which 
will be available soon. As a result, their extension is possible at the moment.
When you are selecting a metadata store for your stack, you can use one of the 
flavors listed down below.
{% endhint %}

## List of available metadata stores

|                     | Flavor               | Integration         |
|---------------------|----------------------|---------------------|
| SQLiteMetadataStore | sqlite                | `built-in`     |
| MySQLMetadataStore   | mysql                  | `built-in`    |
| KubeflowMetadataStore   | kubeflow  | kubeflow |


