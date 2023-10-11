---
description: Connect your ZenML deployment to a cloud provider and other infrastructure services and resources.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Connect ZenML to infrastructure

A production-grade MLOps platform involves interactions between a diverse
combination of third-party libraries and external services sourced from various
different vendors. One of the most daunting hurdles in building and operating an
MLOps platform composed of multiple components is configuring and maintaining
uninterrupted and secured access to the infrastructure resources and services
that it consumes.

In layman's terms, your pipeline code needs to "connect" to a handful of
different services to run successfully and do what it's designed to do. For
example, it might need to connect to a private AWS S3 bucket to read and store
artifacts, a Kubernetes cluster to execute steps with Kubeflow or Tekton, and a
private GCR container registry to build and store container images. ZenML makes
this possible by allowing you to configure authentication information and
credentials embedded directly into your Stack Components, but this doesn't scale
well when you have more than a few Stack Components and has many other
disadvantages related to usability and security.

Gaining access to infrastructure resources and services requires knowledge about
the different authentication and authorization mechanisms and involves
configuring and maintaining valid credentials. It gets even more complicated
when these different services need to access each other. For instance, the
Kubernetes container running your pipeline step needs access to the S3 bucket to
store artifacts or needs to access a cloud service like AWS SageMaker, VertexAI,
or AzureML to run a CPU/GPU intensive task like training a model.

The challenge comes from _setting up and implementing proper authentication and
authorization_ with the best security practices in mind, while at the same time
_keeping this complexity away from the day-to-day routines_ of coding and
running pipelines.

The hard-to-swallow truth is there is no single standard that unifies all
authentication and authorization-related matters or a single, well-defined set
of security best practices that you can follow. However, with ZenML you get the
next best thing, an abstraction that keeps the complexity of authentication and
authorization away from your code and makes it easier to tackle them:
_<mark style="color:blue;">the ZenML Service Connectors</mark>_.

<figure><img src="../../.gitbook/assets/ConnectorsDiagram.png" alt=""><figcaption><p>Service Connectors abstract away complexity and implement security best practices</p></figcaption></figure>

<table data-view="cards"><thead><tr><th></th><th></th><th data-hidden></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td><span data-gb-custom-inline data-tag="emoji" data-code="1f4a1">💡</span> <mark style="color:purple;"><strong>Service Connectors Overview</strong></mark></td><td>Discover Service Connectors with a glance into their features and use-cases.</td><td></td><td><a href="connect-zenml-to-infrastructure/service-connectors-use-cases.md">service-connectors-use-cases.md</a></td></tr><tr><td><span data-gb-custom-inline data-tag="emoji" data-code="1f9f2">🧲</span> <mark style="color:purple;"><strong>Connecting ZenML to Resources</strong></mark></td><td>Understand the paradigm and workflow of connecting ZenML to external resources with Service Connectors.</td><td></td><td><a href="connect-zenml-to-infrastructure/connecting-zenml-to-resources.md">connecting-zenml-to-resources.md</a></td></tr><tr><td><span data-gb-custom-inline data-tag="emoji" data-code="1fa84">🪄</span> <mark style="color:purple;"><strong>The complete guide to Service Connectors</strong></mark></td><td>Everything you need to know to unlock the power of Service Connectors in your project.</td><td></td><td><a href="connect-zenml-to-infrastructure/service-connectors-guide.md">service-connectors-guide.md</a></td></tr><tr><td><span data-gb-custom-inline data-tag="emoji" data-code="2705">✅</span> <mark style="color:purple;"><strong>Security Best Practices</strong></mark></td><td>Best practices concerning the various authentication methods implemented by Service Connectors.</td><td></td><td><a href="connect-zenml-to-infrastructure/best-security-practices.md">best-security-practices.md</a></td></tr><tr><td><span data-gb-custom-inline data-tag="emoji" data-code="1f40b">🐋</span> <mark style="color:purple;"><strong>Docker Service Connector</strong></mark></td><td>Use the Docker Service Connector to connect ZenML to a generic Docker container registry.</td><td></td><td><a href="connect-zenml-to-infrastructure/docker-service-connector.md">docker-service-connector.md</a></td></tr><tr><td><span data-gb-custom-inline data-tag="emoji" data-code="1f300">🌀</span> <mark style="color:purple;"><strong>Kubernetes Service Connector</strong></mark></td><td>Use the Kubernetes Service Connector to connect ZenML to a generic Kubernetes cluster.</td><td></td><td><a href="connect-zenml-to-infrastructure/kubernetes-service-connector.md">kubernetes-service-connector.md</a></td></tr><tr><td><span data-gb-custom-inline data-tag="emoji" data-code="1f536">🔶</span> <mark style="color:purple;"><strong>AWS Service Connector</strong></mark></td><td>Use the AWS Service Connector to connect ZenML to AWS cloud resources.</td><td></td><td><a href="connect-zenml-to-infrastructure/aws-service-connector.md">aws-service-connector.md</a></td></tr><tr><td><span data-gb-custom-inline data-tag="emoji" data-code="1f535">🔵</span> <mark style="color:purple;"><strong>GCP Service Connector</strong></mark></td><td>Use the GCP Service Connector to connect ZenML to a GCP cloud resources.</td><td></td><td><a href="connect-zenml-to-infrastructure/gcp-service-connector.md">gcp-service-connector.md</a></td></tr></tbody></table>

