---
description: >-
  A guide to managing Service Connectors and connecting ZenML to external
  resources.
---

# Service Connectors Guide

## Terminology

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
┠──────────────────────────────┼───────────────┼───────────────────────┼──────────────────┼───────┼────────┨
┃    GCP Service Connector     │ 🔵 gcp        │ 🔵 gcp-generic        │ implicit         │ ✅    │ ✅     ┃
┃                              │               │ 📦 gcs-bucket         │ user-account     │       │        ┃
┃                              │               │ 🌀 kubernetes-cluster │ service-account  │       │        ┃
┃                              │               │ 🐳 docker-registry    │ oauth2-token     │       │        ┃
┃                              │               │                       │ impersonation    │       │        ┃
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

Depending on the Service Connector Type implementation, a Service Connector instance can be configured in one of the following modes with regards to the types and number of resources that it has access to:

* a **multi-type** Service Connector instance that can be configured once and used to gain access to multiple types of resources. This is only possible with Service Connector Types that support multiple Resource Types to begin with, such as those that target multi-service cloud providers like AWS, GCP and Azure. In contrast, a **single-type** Service Connector can only be used with a single Resource Type. To configure a multi-type Service Connector, you can simply skip scoping its Resource Type during registration.
* a **multi-instance** Service Connector instance can be configured once and used to gain access to multiple resources of the same type, each identifiable by a Resource Name. Not all types of connectors and not all types of resources support multiple instances. Some Service Connectors Types like the generic Kubernetes and Docker connector types only allow **single-instance** configurations: a Service Connector instance can only be used to access a single Kubernetes cluster and a single Docker registry. To configure a multi-instance Service Connector, you can simply skip scoping its Resource Name during registration.



</details>

## Explore Service Connector Types

Service Connector Types are not only templates used to instantiate Service Connectors, they also form a body of knowledge that documents best security practices and guides users through the complicated world of authentication and authorization.

ZenML ships with a handful of Service Connector Types that enable you right out-of-the-box to connect ZenML to cloud resources and services available from cloud providers such as AWS and GCP, as well as on-premise infrastructure. In addition to built-in Service Connector Types, ZenML can be easily extended with custom Service Connector implementations.

To discover the Connector Types available with your ZenML deployment, you can use the `zenml service-connector list-types` CLI command:

```
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
┠──────────────────────────────┼───────────────┼───────────────────────┼──────────────────┼───────┼────────┨
┃    GCP Service Connector     │ 🔵 gcp        │ 🔵 gcp-generic        │ implicit         │ ✅    │ ✅     ┃
┃                              │               │ 📦 gcs-bucket         │ user-account     │       │        ┃
┃                              │               │ 🌀 kubernetes-cluster │ service-account  │       │        ┃
┃                              │               │ 🐳 docker-registry    │ oauth2-token     │       │        ┃
┃                              │               │                       │ impersonation    │       │        ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━┷━━━━━━━┷━━━━━━━━┛
```

### Basic Service Connector Types

Service Connector Types like those for Kubernetes and Docker can only handle one type of resource.

### Local and remote availability

The `LOCAL` and `REMOTE` flags in the `zenml service-connector list-types` output indicate if the Service Connector implementation is available locally (i.e. where the ZenML client and pipelines are running) and remotely (i.e. where the ZenML server is running).&#x20;

{% hint style="info" %}
Some Service Connector Types may require additional Python packages to be installed to be available locally. All built-in Service Connector Types are by default available on the ZenML server. ZenML provides the following pypi extras that you can install to make them available on your clients:

* `pip install zenml[connectors-aws]` installs the prerequisites for the AWS Service Connector Type. Alternatively, install the entire AWS ZenML integration by running `zenml integration install aws.`
* `pip install zenml[connectors-gcp]` installs the prerequisites for the GCP Service Connector Type. Alternatively, install the entire GCP ZenML integration by running `zenml integration install gcp`.
* `pip install zenml[connectors-kubernetes]` installs the prerequisites for the Kubernetes Service Connector Type. Alternatively, install the entire Kubernetes ZenML integration by running `zenml integration install kubernetes`.
* the Docker Service Connector Type doesn't require extra packages to be installed.
{% endhint %}

The local/remote availability determines the possible actions and operations that can be performed with a Service Connector. The following are possible with either a remote or a local Service Connector Type:

* Service Connector registration and update.
* Service Connector verification (i.e. checking whether its configuration and credentials are valid and can be actively used to access the remote resources).
* Listing all the resources that can be accessed by a Service Connector.
* Connecting a Stack Component to a remote resource via a Service Connector

The following operations are only possible with Service Connector Types that are locally available (with some notable exceptions covered in the information box that follows):

* Service Connector auto-configuration and discovery of credentials stored by a local client, CLI or SDK (e.g. aws or kubectl).
* Using the configuration and credentials managed by a Service Connector to configure a local client, CLI or SDK (e.g. docker or kubectl).
* Running pipelines with a Stack Component that is connected to a remote resource through a Service Connector&#x20;

{% hint style="info" %}
One interesting and useful byproduct of the way Service Connectors are designed is the fact that you don't need to have all Service Connector Types available client-side to be able to access some of the resources that they provide. Take the following situation for example:

* the GCP Service Connector Type can provide access to GKE Kubernetes clusters and GCR Docker container registries.
* however, you don't need the GCP Service Connector Type or any GCP libraries to be installed on the ZenML clients to connect to and use those Kubernetes clusters or Docker registries in your ML pipelines.
* the Kubernetes Service Connector Type is enough to access any Kubernetes cluster, regardless of its provenance (AWS, GCP etc.)
* the Docker Service Connector Type is enough to access any Docker container registry, regardless of its provenance (AWS, GCP, etc.)
{% endhint %}

## Register Service Connectors

## Discover available resources

## Connect Stack Components to resources



