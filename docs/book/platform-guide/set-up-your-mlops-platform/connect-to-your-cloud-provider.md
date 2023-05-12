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

{% hint style="info" %}
The ZenML CLI provides an even easier and more interactive way of registering Service Connectors. Just use the `-i` command line argument and follow the interactive guide:

```
zenml service-connector register -i
```
{% endhint %}

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

{% hint style="info" %}
The ZenML CLI provides an even easier and more interactive way of connecting a stack component to an external resource. Just pass the `-i` command line argument and follow the interactive guide:

```
zenml artifact-store connect -i
```
{% endhint %}

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

These are some of the advantages of linking an S3 Artifact Store, or any Stack Component for that matter, to an external resource using a Service Connector:

* the S3 Artifact Store can be used in any ZenML Stack, by any person or automated process with access to your ZenML server, on any machine or virtual environment without the need to install or configure the AWS CLI or any AWS credentials. In other cases, this extends to other CLIs/SDKs in addition to AWS (e.g. the Kubernetes `kubectl` CLI).
* setting up AWS accounts, permissions and configuring the Service Connector (first and second steps) can be done by someone with expertise in infrastructure management, while creating and using the S3 Artifact Store (third and following steps) can be done by anyone without any such knowledge.
* you can create and connect any number of S3 Artifact Stores and other types of Stack Components (e.g. Kubernetes/Kubeflow/Tekton Orchestrators, Container Registries) to the AWS resources accessible through the Service Connector, but you only have to configure the Service Connector once.
* if your need to make any changes to the AWS authentication configuration (e.g. refresh expired credentials or remove leaked credentials) you only need to update the Service Connector and the changes will automatically be applied to all Stack Components linked to it.
* this last point is only useful if you're really serious about implementing security best practices: the AWS Service Connector in particular, as well as other cloud provider Service Connectors can automatically generate, distribute and refresh short-lived AWS security credentials for its clients. This keeps long-lived credentials like AWS Secret Keys safely stored on the ZenML Server while the actual workloads and people directly accessing those AWS resources are issued temporary, least-privilege credentials like AWS STS Tokens. This tremendously reduces the impact of potential security incidents.

### Terminology

As with any high-level abstraction, some terminology is needed to express the concepts and operations involved. In spite of the fact that Service Connectors cover such a large area of application as authentication and authorization for a variety of resources from a range of different vendors, we managed to keep this abstraction clean and simple. In the following expandable sections, you'll learn more about Service Connector Types, Resource Types, Resource Names and Service Connectors.

<details>

<summary>Service Connector Types</summary>

This term is used to represent and identify a particular Service Connector implementation and answer questions about its capabilities such as "what types of resources does this Service Connector give me access to", "what authentication methods does it support" and "what credentials and other information do I need to configure for it". This is analogous to the role Flavors play for Stack Components in that the Service Connector Type acts as the template from which one or more Service Connectors are created.

For example, the built-in AWS Service Connector Type shipped with ZenML supports a rich variety of authentication methods and provides access to AWS resources such as S3 buckets, EKS clusters and ECR registries.&#x20;

The `zenml service-connector list-types` and `zenml service-connector describe-type` CLI commands can be used to explore the Service Connector Types available with your ZenML deployment. Extensive documentation is included covering supported authentication methods and Resource Types. The following are just some examples:

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

```sh
$ zenml service-connector describe-type aws
╔══════════════════════════════════════════════════════════════════════════════╗
║                🔶 AWS Service Connector (connector type: aws)                ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                                                                
Authentication methods:                                                         
                                                                                
 • 🔒 implicit                                                                  
 • 🔒 secret-key                                                                
 • 🔒 sts-token                                                                 
 • 🔒 iam-role                                                                  
 • 🔒 session-token                                                             
 • 🔒 federation-token                                                          
                                                                                
Resource types:                                                                 
                                                                                
 • 🔶 aws-generic                                                               
 • 📦 s3-bucket                                                                 
 • 🌀 kubernetes-cluster                                                        
 • 🐳 docker-registry                                                           
                                                                                
Supports auto-configuration: True 
Available locally: True           
Available remotely: True          
                                                                                
This ZenML AWS service connector facilitates connecting to, authenticating to   
and accessing managed AWS services, such as S3 buckets, ECR repositories and EKS
clusters. Explicit long-lived AWS credentials are supported, as well as         
temporary STS security tokens. The connector also supports auto-configuration by
discovering and using credentials configured on a local environment.            
                                                                                
The connector can be used to access to any generic AWS service, such as S3, ECR,
EKS, EC2, etc. by providing pre-authenticated boto3 sessions for these services.
In addition to authenticating to AWS services, the connector is able to manage  
specialized authentication for Docker and Kubernetes Python clients and also    
allows configuration of local Docker and Kubernetes clients.                    
                                                                                
────────────────────────────────────────────────────────────────────────────────

```

```sh
$ zenml service-connector describe-type aws --resource-type s3-bucket
╔══════════════════════════════════════════════════════════════════════════════╗
║                 📦 AWS S3 bucket (resource type: s3-bucket)                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                                                                
Authentication methods: implicit, secret-key, sts-token, iam-role,              
session-token, federation-token                                                 
                                                                                
Supports resource instances: True                                               
                                                                                
Allows users to connect to S3 buckets. When used by connector consumers, they   
are provided a pre-configured boto3 S3 client instance.                         
                                                                                
The configured credentials must have at least the following S3 permissions:     
                                                                                
 • s3:ListBucket                                                                
 • s3:GetObject                                                                 
 • s3:PutObject                                                                 
 • s3:DeleteObject                                                              
 • s3:ListAllMyBuckets                                                          
                                                                                
If set, the resource name must identify an S3 bucket using one of the following 
formats:                                                                        
                                                                                
 • S3 bucket URI: s3://<bucket-name>                                            
 • S3 bucket ARN: arn:aws:s3:::<bucket-name>                                    
 • S3 bucket name: <bucket-name>                                                
                                                                                
────────────────────────────────────────────────────────────────────────────────

```

```sh
$ zenml service-connector describe-type aws --auth-method secret-key
╔══════════════════════════════════════════════════════════════════════════════╗
║                 🔒 AWS Secret Key (auth method: secret-key)                   ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                                                                
Supports issuing temporary credentials: False                                   
                                                                                
Long-lived AWS credentials consisting of an access key ID and secret access key 
associated with an IAM user or AWS account root user (not recommended). This    
method is preferred during development and testing due to its simplicity and    
ease of use. It is not recommended as a direct authentication method for        
production use cases because the clients are granted the full set of permissions
of the IAM user or AWS account root user associated with the credentials.       
                                                                                
An AWS region is required and the connector may only be used to access AWS      
resources in the specified region.                                              
                                                                                
For production, it is recommended to use the AWS IAM Role, AWS Session Token or 
AWS Federation Token authentication method.                                     
                                                                                
────────────────────────────────────────────────────────────────────────────────
```

</details>

<details>

<summary>Resource Types</summary>

Resource Types are just a way of organizing resources into logical classes based on the standard and/or protocol used to access them, or simply based on their vendor. This creates a unified language that can be used to declare the types of resources that are provided by Service Connectors on one hand and the types of resources that are required by Stack Components on the other hand.

For example, we use the generic "Kubernetes Cluster" resource type to refer to any and all Kubernetes clusters, since they are all generally accessible using the same standard libraries, clients and API regardless of whether they are Amazon EKS, Google GKE, Azure AKS or another flavor of managed or self-hosted deployment. Similarly, there is a generic "Docker Registry" resource type that covers any and all container registries that implement the Docker/OCI interface, be it DockerHub, Amazon ECR, Google GCR, Azure ACR, K3D or something similar. Stack Components that need to connect to a Kubernetes cluster (e.g. the Kubernetes Orchestrator or the KServe Model Deployer) can use the "Kubernetes Cluster" resource type identifier to describe their resource requirements and remain agnostic of their vendor.

The term Resource Type is used in ZenML everywhere resources accessible through Service Connectors are involved. For example, to list all Service Connector Types that can be used to broker access to Kubernetes Clusters, you can pass the `--resource-type` flag to the CLI command:

```sh
$ zenml service-connector list-types --resource-type kubernetes-cluster
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━┯━━━━━━━┯━━━━━━━━┓
┃             NAME             │ TYPE          │ RESOURCE TYPES        │ AUTH METHODS     │ LOCAL │ REMOTE ┃
┠──────────────────────────────┼───────────────┼───────────────────────┼──────────────────┼───────┼────────┨
┃ Kubernetes Service Connector │ 🌀 kubernetes │ 🌀 kubernetes-cluster │ password         │ ✅    │ ✅     ┃
┃                              │               │                       │ token            │       │        ┃
┠──────────────────────────────┼───────────────┼───────────────────────┼──────────────────┼───────┼────────┨
┃    AWS Service Connector     │ 🔶 aws        │ 🔶 aws-generic        │ implicit         │ ✅    │ ✅     ┃
┃                              │               │ 📦 s3-bucket          │ secret-key       │       │        ┃
┃                              │               │ 🌀 kubernetes-cluster │ sts-token        │       │        ┃
┃                              │               │ 🐳 docker-registry    │ iam-role         │       │        ┃
┃                              │               │                       │ session-token    │       │        ┃
┃                              │               │                       │ federation-token │       │        ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━┷━━━━━━━┷━━━━━━━━┛

```

From the above, you can see that there are not one but two Service Connector Types that can connect ZenML to Kubernetes clusters: one deals exclusively with AWS EKS managed Kubernetes clusters, the other one is a generic implementation that can be used with any standard Kubernetes cluster, including those that run on-premise.

Conversely, to list all currently registered Service Connector instances that provide access to Kubernetes clusters:

```sh
$ zenml service-connector list --resource_type kubernetes-cluster
┏━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━┓
┃ ACTIVE │ NAME                  │ ID                           │ TYPE          │ RESOURCE TYPES        │ RESOURCE NAME                │ SHARED │ OWNER   │ EXPIRES IN │ LABELS              ┃
┠────────┼───────────────────────┼──────────────────────────────┼───────────────┼───────────────────────┼──────────────────────────────┼────────┼─────────┼────────────┼─────────────────────┨
┃        │ aws-iam-multi-eu      │ e33c9fac-5daa-48b2-87bb-0187 │ 🔶 aws        │ 🔶 aws-generic        │ <multiple>                   │ ➖     │ default │            │ region:eu-central-1 ┃
┃        │                       │ d3782cde                     │               │ 📦 s3-bucket          │                              │        │         │            │                     ┃
┃        │                       │                              │               │ 🌀 kubernetes-cluster │                              │        │         │            │                     ┃
┃        │                       │                              │               │ 🐳 docker-registry    │                              │        │         │            │                     ┃
┠────────┼───────────────────────┼──────────────────────────────┼───────────────┼───────────────────────┼──────────────────────────────┼────────┼─────────┼────────────┼─────────────────────┨
┃        │ aws-iam-multi-us      │ ed528d5a-d6cb-4fc4-bc52-c3d2 │ 🔶 aws        │ 🔶 aws-generic        │ <multiple>                   │ ➖     │ default │            │ region:us-east-1    ┃
┃        │                       │ d01643e5                     │               │ 📦 s3-bucket          │                              │        │         │            │                     ┃
┃        │                       │                              │               │ 🌀 kubernetes-cluster │                              │        │         │            │                     ┃
┃        │                       │                              │               │ 🐳 docker-registry    │                              │        │         │            │                     ┃
┠────────┼───────────────────────┼──────────────────────────────┼───────────────┼───────────────────────┼──────────────────────────────┼────────┼─────────┼────────────┼─────────────────────┨
┃        │ kube-auto             │ da497715-7502-4cdd-81ed-289e │ 🌀 kubernetes │ 🌀 kubernetes-cluster │ A5F8F4142FB12DDCDE9F21F6E9B0 │ ➖     │ default │            │                     ┃
┃        │                       │ 70664597                     │               │                       │ 7A18.gr7.us-east-1.eks.amazo │        │         │            │                     ┃
┃        │                       │                              │               │                       │ naws.com                     │        │         │            │                     ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━┛
```

</details>

<details>

<summary>Resource Names (also known as Resource IDs)</summary>

If a Resource Type is used to identify a class of resources supported by a Service Connector, we also need some way to uniquely identify each resource instance belonging to that class that a Service Connector can provide access to. For example, an AWS Service Connector can be configured to provide access to multiple S3 buckets identifiable by their bucket names or their `s3://bucket-name` formatted URIs. Similarly, an AWS Service Connector can be configured to provide access to multiple EKS Kubernetes clusters in the same AWS region, each uniquely identifiable by their EKS cluster name. This is what we call Resource Names.

Resource Names make it generally easy to identify a particular resource instance accessible through a Service Connector, especially when used together with the Service Connector name and the Resource Type. The following ZenML CLI command output shows a few examples featuring Resource Names for S3 buckets, EKS clusters, ECR registries and general Kubernetes clusters. As you can see, the way we name resources varies from implementation to implementation and resource type to resource type:

```sh
$ zenml service-connector list-resources
The following resources can be accessed by service connectors configured in your workspace:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME        │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES                                                   ┃
┠──────────────────────────────────────┼───────────────────────┼────────────────┼───────────────────────┼──────────────────────────────────────────────────────────────────┨
┃ 8d307b98-f125-4d7a-b5d5-924c07ba04bb │ aws-session-docker    │ 🔶 aws         │ 🐳 docker-registry    │ 715803424590.dkr.ecr.us-east-1.amazonaws.com                     ┃
┠──────────────────────────────────────┼───────────────────────┼────────────────┼───────────────────────┼──────────────────────────────────────────────────────────────────┨
┃ d1e5ecf5-1531-4507-bbf5-be0a114907a5 │ aws-session-s3        │ 🔶 aws         │ 📦 s3-bucket          │ s3://public-flavor-logos                                         ┃
┃                                      │                       │                │                       │ s3://sagemaker-us-east-1-715803424590                            ┃
┃                                      │                       │                │                       │ s3://spark-artifact-store                                        ┃
┃                                      │                       │                │                       │ s3://spark-demo-as                                               ┃
┃                                      │                       │                │                       │ s3://spark-demo-dataset                                          ┃
┠──────────────────────────────────────┼───────────────────────┼────────────────┼───────────────────────┼──────────────────────────────────────────────────────────────────┨
┃ d2341762-28a3-4dfc-98b9-1ae9aaa93228 │ aws-key-docker-eu     │ 🔶 aws         │ 🐳 docker-registry    │ 715803424590.dkr.ecr.eu-central-1.amazonaws.com                  ┃
┠──────────────────────────────────────┼───────────────────────┼────────────────┼───────────────────────┼──────────────────────────────────────────────────────────────────┨
┃ 0658a465-2921-4d6b-a495-2dc078036037 │ aws-key-kube-zenhacks │ 🔶 aws         │ 🌀 kubernetes-cluster │ zenhacks-cluster                                                 ┃
┠──────────────────────────────────────┼───────────────────────┼────────────────┼───────────────────────┼──────────────────────────────────────────────────────────────────┨
┃ 049e7f5e-e14c-42b7-93d4-a273ef414e66 │ eks-eu-central-1      │ 🔶 aws         │ 🌀 kubernetes-cluster │ kubeflowmultitenant                                              ┃
┃                                      │                       │                │                       │ zenbox                                                           ┃
┠──────────────────────────────────────┼───────────────────────┼────────────────┼───────────────────────┼──────────────────────────────────────────────────────────────────┨
┃ b551f3ae-1448-4f36-97a2-52ce303f20c9 │ kube-auto             │ 🌀 kubernetes  │ 🌀 kubernetes-cluster │ A5F8F4142FB12DDCDE9F21F6E9B07A18.gr7.us-east-1.eks.amazonaws.com ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

</details>

<details>

<summary>Service Connectors</summary>

The Service Connector is how you configure ZenML to authenticate and connect to one or more external resources. It stores the required configuration and security credentials and can optionally be scoped with a Resource Type and a Resource Name.

Depending on the Service Connector Type implementation, a Service Connector instance can be configured in one of the following modes regarding the types and number of resources that it has access to:

* a **multi-type** Service Connector instance that can be configured once and used to gain access to multiple types of resources. This is only possible with Service Connector Types that support multiple Resource Types to begin with, such as those that target multi-service cloud providers such as AWS, GCP and Azure. In contrast, a **single-type** Service Connector can only be used with a single Resource Type. To configure a multi-type Service Connector, you can simply skip scoping its Resource Type during registration.
* a **multi-instance** Service Connector instance can be configured once and used to gain access to multiple resources of the same type, each identifiable by a Resource Name. Not all types of connectors and not all types of resources support multiple instances. Some Service Connectors Types like the generic Kubernetes and Docker connector types only allow **single-instance** configurations: a Service Connector instance can only be used to access a single Kubernetes cluster and a single Docker registry. To configure a multi-instance Service Connector, you can simply skip scoping its Resource Name during registration.

</details>
