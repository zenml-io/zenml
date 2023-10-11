---
description: Features and use-cases unlocked with ZenML Service Connectors.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Service Connectors use cases

Simply put, ZenML Service Connectors can be used to securely connect ZenML to external resources and services. All the complexity involved in validating, storing, and generating security-sensitive information as well as authenticating and authorizing access to external services is encapsulated in this simple yet powerful concept instead of being spread out across the wide range of Stack Components that you need to run pipelines.

Regardless of your level of experience with infrastructure management, whether you're a novice looking to quickly hook up ZenML to a cloud stack, or an expert platform engineer seeking to implement top-notch infrastructure security practices for your team or organization, Service Connectors will help you get there faster and happier. In the following sections, we'll explore just a few of the many features and use cases that you can unlock with Service Connectors.

## Zero-provisioning fully portable ML pipelines

Imagine being able to use resources from cloud providers like AWS, GCP, and Azure without having to set up and manage cloud-specific CLIs, SDKs, credentials, and configurations in all the environments where your ML pipelines are running. With Service Connectors in ZenML, you can do just that! All you need is a ZenML Service Connector and a few Python libraries, and you're ready to go. No other configuration is required in your environment. This makes it possible for anyone to run your ML pipelines anywhere without any knowledge of the cloud infrastructure being used and without any configuration prerequisites. Plus, integrating ZenML into other CI/CD systems is greatly simplified since you don't have to worry about setting them up for authentication anymore.

## Assisted setup with built-in safe defaults and security best practices

Setting up the connections between your code and cloud services can be a daunting task, especially since cloud providers offer multiple authentication methods that target specific services and use cases. It often requires advanced infrastructure knowledge to configure these connections successfully. Even if you are an infrastructure expert, you'll appreciate the many burdens that Service Connectors automate that you would normally have to deal with yourself, such as:

* validating that credentials are correctly formatted
* verifying that the authentication configuration and credentials can actually be used to gain access to the target resource or service (e.g. checking that an AWS Secret Key can indeed be used to access an S3 bucket).
* discovering all the resources accessible with a set of credentials (e.g. listing all the EKS Kubernetes clusters that are accessible with an AWS IAM role)&#x20;
* converting credentials in the format that they are needed by clients, libraries, and your pipeline code (e.g. generating Kubernetes API and `kubectl` credentials from AWS STS tokens)
* implementing and enforcing security best practices. Notably, automatically generating and refreshing safe-to-distribute, temporary, and access-restricted credentials from long-lived, wide-access credentials (e.g. generating an AWS STS token restricted to accessing a single S3 bucket from IAM user AWS Secret Key credentials).
* providing pre-authenticated and pre-configured clients for Python libraries (e.g. python-kubernetes clients, python-docker clients, boto3 sessions). Thus, decoupling code from configuration and ensuring that your pipelines can just run without being tied to a particular authentication mechanism.

## Lift-and-shift your local configuration for instant portability

One of the most common challenges in machine learning is the "works for me" syndrome: your ML pipelines work well on your local machine, but reproducing the results on a different environment can be difficult due to authentication and permission restrictions. Fortunately, Service Connectors in ZenML provide a solution to this problem. By leveraging "auto-discovery and lift" capabilities, Service Connectors automatically extract authentication configurations and credentials from your local machine, securely store them, and enable sharing with other team members. This breakthrough approach ensures that your ML pipelines are fully reproducible and independent of the environment, making it easier to collaborate and accelerate your project's progress.

## Facilitating separation of responsibilities in teams

The dynamic composition of skill sets and responsibilities within a machine learning team is a critical aspect to ensure its success. The fact is, some team members possess advanced knowledge in infrastructure management, while others do not. Service Connectors in ZenML offers an effective solution to overcome this challenge by facilitating collaboration and responsibility segregation within your team. Specifically, platform engineers are responsible for configuring Service Connectors that establish the connection between ZenML and external infrastructure resources. The Service Connector abstraction empowers other members of the team to access these resources to build and run ML pipelines without requiring any advanced technical knowledge.

## Avoiding vendor lock-in

On top of all that, we'll add avoiding vendor lock-in, not just because it's a neat thing to mention, but because Service Connectors really deliver it. By design, Service Connectors decouple the authentication mechanisms of cloud platforms from access to the standard services that they offer, such as Kubernetes clusters and container registries. This decoupling ensures that you can access these services independently of the underlying cloud provider and authentication schemes. Switching to another equivalent on-prem technology or cloud provider requires no changes to your ML pipeline code.

Service Connectors, in combination with the other abstractions powering ZenML and represented as Stack Components, deliver the promise of fully portable, truly infrastructure-agnostic pipelines.
