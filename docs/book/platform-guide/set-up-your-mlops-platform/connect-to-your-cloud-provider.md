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

Regardless of your level of experience with infrastructure management, whether you're a novice looking to quickly hook up ZenML to a cloud stack, or an expert platform engineer seeking to implement top-notch infrastructure security practices for your team or organization, Service Connectors will help you get there faster and happier. In the following sections, we'll explore just a few of the many features and use-cases that you can unlock with Service Connectors.

### Zero-provisioning fully portable ML pipelines

Imagine being able to use resources from cloud providers like AWS, GCP, and Azure without having to set up and manage cloud specific CLIs, SDKs, credentials and configurations in all the environments where your ML pipelines are running. With Service Connectors in ZenML, you can do just that! All you need is a ZenML Service Connector, a few Python libraries, and you're ready to go. No other configuration is required on your environment. This makes it possible for anyone to run your ML pipelines anywhere without any knowledge of the cloud infrastructure being used and without any configuration prerequisites. Plus, integrating ZenML into other CI/CD systems is greatly simplified since you don't have to worry about setting them up for authentication anymore.

### Assisted set-up with built-in safety measures, defaults and best practices

Setting up the connections between your code and cloud services can be a daunting task, especially since cloud providers offer multiple authentication methods that target specific services and use cases. It often requires advanced infrastructure knowledge to configure these connections successfully. Even if you are an infrastructure expert, you'll appreciate the many burdens that Service Connectors automate that you would normally have to deal with yourself, such as:

* validating that credentials are correctly formatted
* verifying that the authentication configuration and credentials can actually be used to gain access to the target resource or service (e.g. checking that an AWS Secret Key can indeed be used to access an S3 bucket).
* discovering all the resources accessible with a set of credentials (e.g. listing all the EKS Kubernetes clusters that are accessible with an AWS IAM role)&#x20;
* converting credentials in the format that they are needed by clients, libraries and your pipeline code (e.g. generating Kubernetes API and kubectl credentials from AWS STS tokens)
* implementing and enforcing security best practices. Notably, automatically generating and refreshing safe-to-distribute, temporary and access-restricted credentials from long-lived, wide-access credentials (e.g. generating an AWS STS token restricted to accessing a single S3 bucket from IAM user AWS Secret Key credentials).
* providing pre-authenticated and pre-configured clients for Python libraries (e.g. python-kubernetes clients, python-docker clients, boto3 sessions). Thus decoupling code from configuration and ensuring that your pipelines can just run without being tied to a particular authentication mechanism.

### Lift-and-shift your local configuration for instant portability

One of the most common challenges in machine learning is the "works for me" PoC syndrome, where pipelines work well on a local machine, but reproducing the results on a different environment can be difficult due to authentication and permission restrictions. Fortunately, Service Connectors in ZenML provide a solution to this problem. By leveraging "auto-discovery and lift" capabilities, Service Connectors automatically extract authentication configurations and credentials from your local machine, securely store them, and enable sharing with other team members. This breakthrough approach ensures that your ML pipelines are fully reproducible, independent of the environment, making it easier to collaborate and accelerate your project's progress.

### Facilitating separation of concerns and responsibilities in teams

The dynamic composition of skill sets and responsibilities within a machine learning team is a critical aspect to ensure its success. The fact is, some team members possess advanced knowledge in infrastructure management, while others do not. Service Connectors in ZenML offers an effective solution to overcome this challenge by facilitating collaboration and responsibility segregation within your team. Specifically, platform engineers are responsible for configuring Service Connectors that establish the connection between ZenML and external infrastructure resources. The Service Connector abstraction empowers other members of the team to access these resources to build and run ML pipelines without requiring any advanced technical knowledge.

### Avoiding vendor lock-in

On top of all that, we'll add avoiding vendor lock-in, not just because it's a trendy thing to mention, but because Service Connectors really deliver it. By design, Service Connectors decouple the authentication mechanisms of cloud platforms from access to the standard services that they offer, such as Kubernetes clusters and container registries. This decoupling ensures that you can access these services independently of the underlying cloud provider and authentication schemes. Switching to another equivalent on-prem technology or cloud provider requires no changes to your ML pipeline code.

Service Connectors, in combination with the other abstractions powering ZenML and represented as Stack Components, deliver the promise of fully portable, truly infrastructure agnostic pipelines.

## Connecting ZenML to resources

Everything around Service Connectors is expressed in terms of resources. A Kubernetes cluster is a resource. An S3 bucket is another resource. Service Connectors simplify the configuration of ZenML to enable authentication and access to these resources. Once Service Connectors are set up, Stacks and Stack Components can easily access and utilize these resources in your ML pipelines without worrying about the specifics of authentication and access.

Before diving into terminology and the rich set of features attainable with Service Connectors, it will help to walk through a typical workflow to understand conceptually what the fuss is all about.

### Typical Service Connector workflow

The first step is _<mark style="color:purple;">finding out what types of resources you can connect ZenML to</mark>_. This is where the _Service Connector Type_ concept comes in. For now, it is sufficient to think of Service Connector Types as a way to describe all the supported types of Service Connectors that can be configured and the kind of resources that they can access. This is an example of listing the available Service Connector Types with the ZenML CLI. Note that there is an AWS Service Connector type that we can use to gain access to several types of AWS resources:

```sh
$ zenml service-connector list-types
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━┯━━━━━━━┯━━━━━━━━┓
┃             NAME             │ TYPE          │ RESOURCE TYPES        │ AUTH METHODS     │ LOCAL │ REMOTE ┃
┠──────────────────────────────┼───────────────┼───────────────────────┼──────────────────┼───────┼────────┨
┃ Kubernetes Service Connector │ 🌀 kubernetes │ 🌀 kubernetes-cluster │ password         │ ✅    │ ✅     ┃
┃                              │               │                       │ token            │       │        ┃
┠──────────────────────────────┼───────────────┼───────────────────────┼──────────────────┼───────┼────────┨
┃   Docker Service Connector   │ 🐳 docker     │ 🐳 docker-registry    │ password         │ ✅    │ ✅     ┃
┠──────────────────────────────┼───────────────┼───────────────────────┼──────────────────┼───────┼────────┨
┃    AWS Service Connector     │ 🔶 aws        │ 🔶 aws-generic        │ implicit         │ ✅    │ ✅     ┃
┃                              │               │ 📦 s3-bucket          │ secret-key       │       │        ┃
┃                              │               │ 🌀 kubernetes-cluster │ sts-token        │       │        ┃
┃                              │               │ 🐳 docker-registry    │ iam-role         │       │        ┃
┃                              │               │                       │ session-token    │       │        ┃
┃                              │               │                       │ federation-token │       │        ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━┷━━━━━━━┷━━━━━━━━┛

```

The second step is _<mark style="color:purple;">registering a Service Connector</mark>_ that effectively enables ZenML to authenticate to and access one or more remote resources. This step is best handled by someone with some infrastructure knowledge, but there are sane defaults and auto-detection mechanisms built into the AWS Service Connector that can make this a walk in the park even for the uninitiated. A simple example of this is registering an AWS Service Connector with AWS credentials _automatically lifted up from your local host_, giving ZenML access to the same resources that you can access from your local machine through the AWS CLI, such as EKS clusters, ECR repositories or S3 buckets:

```shell
$ zenml service-connector register aws-auto --type aws --auto-configure
⠦ Registering service connector 'aws-auto'...
Successfully registered service connector `aws-auto` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────────────┼────────────────┨
┃ ffbec8d7-b931-46c3-bcc5-c6252c52ee5f │ aws-auto       │ 🔶 aws         │ 🔶 aws-generic        │ 🤷 none listed ┃
┃                                      │                │                │ 📦 s3-bucket          │                ┃
┃                                      │                │                │ 🌀 kubernetes-cluster │                ┃
┃                                      │                │                │ 🐳 docker-registry    │                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛

```

The third step is preparing to configure the Stack Components and Stacks that you will use to run pipelines, the same way you would do it without Service Connectors, but this time you have the option of _<mark style="color:purple;">discovering which remote resources are available</mark>_ for you to use. For example, if you needed an S3 bucket for your S3 Artifact Store, you could run the following CLI command, which is the same as asking "_which S3 buckets am I authorized to access through ZenML ?_". The result is a list of resource names, identifying those S3 buckets:

```sh
$ zenml service-connector list-resources --resource-type s3-bucket
The following 's3-bucket' resources can be accessed by service connectors configured in your workspace:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME      │ CONNECTOR TYPE │ RESOURCE TYPE │ RESOURCE NAMES                        ┃
┠──────────────────────────────────────┼─────────────────────┼────────────────┼───────────────┼───────────────────────────────────────┨
┃ ffbec8d7-b931-46c3-bcc5-c6252c52ee5f │ aws-auto            │ 🔶 aws         │ 📦 s3-bucket  │ s3://public-flavor-logos              ┃
┃                                      │                     │                │               │ s3://sagemaker-us-east-1-715803424590 ┃
┃                                      │                     │                │               │ s3://spark-artifact-store             ┃
┃                                      │                     │                │               │ s3://zenfiles                         ┃
┃                                      │                     │                │               │ s3://zenml-demos                      ┃
┃                                      │                     │                │               │ s3://zenmlpublicdata                  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

The last step in this journey is _<mark style="color:purple;">configuring and connecting a Stack Component to a remote resource</mark>_ via the Service Connector registered and listed in previous steps. This is as easy as saying "_I want this S3 Artifact Store to use the `s3://ml-bucket` S3 bucket_" or "_I want this Kubernetes Orchestrator to use the `mega-ml-cluster` Kubernetes cluster_" and doesn't require any knowledge whatsoever about the authentication mechanisms or even the provenance of those resources. The following example creates an S3 Artifact store and connects it to an S3 bucket with the previous connector:

```sh
$ zenml artifact-store register s3-zenfiles --flavor s3 --path=s3://zenfiles
Successfully registered artifact_store `s3-zenfiles`.

$ zenml artifact-store connect s3-zenfiles --connector aws-auto
Successfully connected artifact store `s3-zenfiles` to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────┼────────────────┨
┃ ffbec8d7-b931-46c3-bcc5-c6252c52ee5f │ aws-auto       │ 🔶 aws         │ 📦 s3-bucket  │ s3://zenfiles  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛

```



At this point, you may wonder why you would need to do all this extra work when you could have simply configured your S3 Artifact Store with embedded AWS credentials or referencing AWS credentials in a ZenML secret, like this:

```sh
$ zenml secret create aws-secret -i
Entering interactive mode:
Please enter a secret key: aws_access_key_id
Please enter the secret value for the key [aws_access_key_id]: ****
Do you want to add another key-value pair to this secret? [y/n]: y
Please enter a secret key: aws_secret_access_key
Please enter the secret value for the key [aws_secret_access_key]: ****
Do you want to add another key-value pair to this secret? [y/n]: n
The following secret will be registered.
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃      SECRET_KEY       │ SECRET_VALUE ┃
┠───────────────────────┼──────────────┨
┃   aws_access_key_id   │ ***          ┃
┠───────────────────────┼──────────────┨
┃ aws_secret_access_key │ ***          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛
Secret 'aws-secret' successfully created.

$ zenml artifact-store register s3-zenfiles --flavor s3 --path=s3://zenfiles --authentication_secret=aws-secret
Successfully registered artifact_store `s3-zenfiles`.

```

These are some of the advantages of linking an S3 Artifact Store (any Stack Component for that matter) to a Service Connector:

* the S3 Artifact Store can be used in any ZenML Stack, by any person or automated process with access to your ZenML server, on any machine or virtual environment without the need to install or configure the AWS CLI or any AWS credentials. In other cases, this extends to other CLIs/SDKs in addition to AWS (e.g. the Kubernetes `kubectl` client).
* setting up AWS accounts, permissions and configuring the Service Connector (first and second steps) can be done by someone with expertise in infrastructure management, while creating and using the S3 Artifact Store (third and following steps) can be done by anyone without any such knowledge.
* you can create and connect any number of S3 Artifact Stores and other types of Stack Components (e.g. Kubernetes/Kubeflow/Tekton Orchestrators, Container Registries) to the AWS resources accessible through the Service Connector, but you only had to configure the Service Connector once.
* if your need to make any changes to the AWS authentication configuration (e.g. refresh expired credentials or remove leaked credentials) you only need to update the Service Connector and the changes will automatically be appliet to all Stack Components linked to it.
* this last point is only useful if you're really serious about implementing security best practices: the AWS Service Connector in particular, as well as other cloud provider Service Connectors can automatically generate, distribute and refresh short-lived AWS security credentials for its clients. This keeps long-lived credentials like AWS Secret Keys safely stored on the ZenML Server while the actual workloads and people directly accessing those AWS resources are issued temporary, least-privilege credentials like AWS STS Tokens. This tremendously reduces the impact of potential security incidents.

### Terminology





:construction: WIP:construction:
