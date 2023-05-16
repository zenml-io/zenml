---
description: >-
  Connect your ZenML deployment to a cloud provider and other infrastructure
  services and resources
---

# Connect ZenML to infrastructure

A production-grade MLOps platform involves interactions between a diverse combination of third-party libraries and external services sourced from various different vendors. One of the most daunting hurdles in building and operating an MLOps platform composed of multiple components is configuring and maintaining uninterrupted and secured access to the infrastructure resources and services that it consumes.

<figure><img src="../../.gitbook/assets/ConnectorsDiagram.png" alt=""><figcaption><p>High level visualization of how connectors work</p></figcaption></figure>

In layman's terms, your pipeline code needs to "connect" to a handful of different services to run successfully and do what it's designed to do. For example, it might need to connect to a private AWS S3 bucket to read and store artifacts, a Kubernetes cluster to execute steps with Kubeflow or Tekton and a private GCR container registry to build and store container images. Gaining access to all of these services requires knowledge about the different authentication and authorization mechanisms and involves configuring and maintaining valid credentials. It gets even more complicated when these different services need to access each-other. For instance, the Kubernetes container running your pipeline step needs access to the S3 bucket to store artifacts or needs to access a cloud service like AWS SageMaker, VertexAI or AzureML to run a CPU/GPU intensive task like training a model.

The challenge comes from _setting up and implementing proper authentication and authorization_ with best security practices in mind, while at the same time _keeping this complexity away from the day-to-day routines_ of coding and running pipelines.

The hard to swallow truth is there is no single standard that unifies all authentication and authorization related matters. However, with ZenML you get the next best thing: an abstraction that keeps the complexity of authentication and authorization away from your code and makes it easier to tackle them, _<mark style="color:blue;">the ZenML Service Connectors</mark>_.

<table data-view="cards"><thead><tr><th></th><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td>Discover Service Connectors with a glance into their features and use-cases.</td><td></td><td></td><td><a href="connect-to-your-cloud-provider/service-connectors-use-cases.md">service-connectors-use-cases.md</a></td></tr><tr><td>Understand the paradigm and workflow of connecting ZenML to external resources with Service Connectors.</td><td></td><td></td><td><a href="connect-to-your-cloud-provider/connecting-zenml-to-resources.md">connecting-zenml-to-resources.md</a></td></tr><tr><td>Start using Service Connectors with help from the Service Connector guide.</td><td></td><td></td><td><a href="connect-to-your-cloud-provider/service-connectors-guide.md">service-connectors-guide.md</a></td></tr></tbody></table>

