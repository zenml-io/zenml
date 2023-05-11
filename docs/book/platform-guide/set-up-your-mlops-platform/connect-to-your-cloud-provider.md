---
description: >-
  Connect your ZenML deployment to a cloud provider and other infrastructure
  services and resources
---

# Connect ZenML to infrastructure

A production-grade MLOps platform involves interactions between a diverse combination of third-party libraries and external services sourced from various different vendors. One of the most daunting hurdles in building and operating an MLOps platform composed of multiple components is configuring and maintaining uninterrupted and secured access to the infrastructure resources and services that it consumes.

In layman's terms, your pipeline code needs to "connect" to a handful of different services to run successfully and do what it's designed to do. For example, it might need to connect to a private AWS S3 bucket to read and store artifacts, a Kubernetes cluster to execute steps with Kubeflow or Tekton and a private GCR container registry to build and store container images. Gaining access to all of these services requires knowledge about the different authentication and authorization mechanisms and involves configuring and maintaining valid credentials. It gets even more complicated when these different services need to access each-other. For instance, the Kubernetes container running your pipeline step needs access to the S3 bucket to store artifacts or needs to access a cloud service like AWS SageMaker, VertexAI or AzureML to run a CPU/GPU intensive task like training a model.

The challenge comes from _setting up and implementing proper authentication and authorization_ with best security practices in mind, while at the same time _keeping this complexity away from the day-to-day routines_ of coding and running pipelines.

Sadly, there is no single standard that unifies all authentication and authorization related matters. With ZenML you get the next best thing, an abstraction that keeps the complexity away from your code and makes it easier to reason about these things: _<mark style="color:blue;">the ZenML Service Connectors</mark>_.

## ZenML Service Connectors

Simply put, ZenML Service Connectors can be used to securely connect ZenML to external resources and services. All the complexity involved in validating, storing and generating security sensitive information as well as authenticating to external services is encapsulated in this simple and yet powerful concept.

Here are just a handful of use-cases that you can unlock with Service Connectors:

1. imagine being able to use the managed resources from cloud providers like AWS, GCP, and Azure without having to set up and manage cloud specific CLIs, SDKs, credentials and configurations in all the environments where your ML pipelines are running. With Service Connectors in ZenML, you can do just that! All you need is a ZenML Service Connector, a few Python libraries, and you're ready to go. No other configuration is required on your environment. This makes it possible for anyone to run your ML pipelines anywhere without any knowledge of the cloud infrastructure being used. Plus, integrating ZenML into other CI/CD systems is greatly simplified since you don't have to worry about authentication anymore.
2. setting up the connections between your code and cloud services can be a daunting task, especially since cloud providers offer multiple authentication methods that target specific services and use cases. It often requires advanced infrastructure knowledge to configure these connections successfully. If you are an infrastructure expert, you'll appreciate the many burdens that Service Connectors automate that you would normally have to deal with yourself, such as:
   * validating that credentials are correctly formatted
   * verifying that the authentication configuration and credentials can actually be used to gain access to the target resource or service (e.g. checking that an AWS Secret Key can be used to access an S3 bucket).
   * discovering all the resources accessible with a set of credentials (e.g. listing all the EKS Kubernetes clusters that are accessible with an AWS Secret Key)&#x20;
   * converting credentials in the format that they are needed by your libraries and pipeline code (e.g. generating Kubernetes API credentials from AWS credentials)
   * implementing and enforcing security best practices. Notably, generating and rotating safe-to-distribute, temporary and access-restricted credentials from long-lived, wide-access credentials (e.g. generating an AWS STS token restricted to accessing a single S3 bucket from IAM user AWS Secret Key credentials).
   * providing pre-authenticated and pre-configured clients for Python libraries. Thus ensuring that the pipeline code can just run without being tied to a particular set of credentials.
3. one of the most common challenges in machine learning is the "works for me" PoC syndrome, where pipelines work well on a local machine, but reproducing the results on a different environment can be difficult due to authentication and permission restrictions. Fortunately, Service Connectors in ZenML provide a solution to this problem. By leveraging "auto-discovery and lift" capabilities, Service Connectors automatically extract authentication configurations from your local machine, securely store them, and enable sharing with other team members. This breakthrough approach ensures that your ML pipelines are fully reproducible, independent of the environment, making it easier to collaborate and accelerate your project's progress.
4. the dynamic composition of skill sets and responsibilities within a machine learning team is a critical aspect to ensure its success. The fact is, some team members possess advanced knowledge in infrastructure management, while others do not. Service Connectors in ZenML offers an effective solution to overcome this challenge by facilitating collaboration and responsibility segregation within your team. Specifically, platform engineers are responsible for configuring Service Connectors that establish the connection between ZenML and external infrastructure resources. The Service Connector abstraction empowers other members of the team to access these resources without requiring any advanced technical knowledge.
5. on top of all that, we'll add avoiding vendor lock-in. Not just because it's a trendy thing to mention, but because Service Connectors really deliver it. By design, Service Connectors decouple the authentication mechanisms of cloud platforms from access to some standard services they offer, such as Kubernetes clusters and container registries. This decoupling ensures that you can access these services independently of the underlying cloud provider and authentication scheme.

## It's All About Resources







:construction: WIP:construction:
