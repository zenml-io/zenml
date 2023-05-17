---
description: >-
  The complete guide to managing Service Connectors and connecting ZenML to
  external resources.
---

# Service Connectors Guide

This documentation section contains everything that you need to use Service Connectors to connect ZenML to external resources. A lot of information is covered, so it might be useful to  use the following guide to navigate it:

* if you're only getting started with Service Connectors, we suggest starting by familiarizing yourself with the [terminology](service-connectors-guide.md#terminology)
* check out the section on [Service Connector Types](service-connectors-guide.md#service-connector-types) to understand the different Service Connector implementations that are available and when to use them
* there is an entire section dedicated to [best practices concerning the various authentication methods](service-connectors-guide.md#best-practices-for-authentication-methods) implemented by Service Connectors, such as which types of credentials to use in development or production and how to keep your security information safe. This section is particularly targeted at engineers with some knowledge in infrastructure, but it should be accessible to larger audiences.

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

Resource Types are a way of organizing resources into logical, well-known classes based on the standard and/or protocol used to access them, or simply based on their vendor. This creates a unified language that can be used to declare the types of resources that are provided by Service Connectors on one hand and the types of resources that are required by Stack Components on the other hand.

For example, we use the generic `kubernetes-cluster` resource type to refer to any and all Kubernetes clusters, since they are all generally accessible using the same standard libraries, clients and API regardless of whether they are Amazon EKS, Google GKE, Azure AKS or another flavor of managed or self-hosted deployment. Similarly, there is a generic `docker-registry` resource type that covers any and all container registries that implement the Docker/OCI interface, be it DockerHub, Amazon ECR, Google GCR, Azure ACR, K3D or something similar. Stack Components that need to connect to a Kubernetes cluster (e.g. the Kubernetes Orchestrator or the KServe Model Deployer) can use the `kubernetes-cluster` resource type identifier to describe their resource requirements and remain agnostic of their vendor.

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

Conversely, to list all currently registered Service Connector instances that provide access to Kubernetes clusters, one might run:

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

If a Resource Type is used to identify a class of resources, we also need some way to uniquely identify each resource instance belonging to that class that a Service Connector can provide access to. For example, an AWS Service Connector can be configured to provide access to multiple S3 buckets identifiable by their bucket names or their `s3://bucket-name` formatted URIs. Similarly, an AWS Service Connector can be configured to provide access to multiple EKS Kubernetes clusters in the same AWS region, each uniquely identifiable by their EKS cluster name. This is what we call Resource Names.

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

Every Service Connector Type defines its own rules for how Resource Names are formatted. These rules are documented in the section belonging each resource type. For example:

```
$ zenml service-connector describe-type aws --resource-type docker-registry
╔══════════════════════════════════════════════════════════════════════════════╗
║        🐳 AWS ECR container registry (resource type: docker-registry)        ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                                                                
Authentication methods: implicit, secret-key, sts-token, iam-role,              
session-token, federation-token                                                 
                                                                                
Supports resource instances: False                                              
                                                                                
Allows users to access one or more ECR repositories as a standard Docker        
registry resource. When used by connector consumers, they are provided a        
pre-authenticated python-docker client instance.                                
                                                                                
The configured credentials must have at least the following ECR permissions for 
one or more ECR repositories:                                                   
                                                                                
 • ecr:DescribeRegistry                                                         
 • ecr:DescribeRepositories                                                     
 • ecr:ListRepositories                                                         
 • ecr:BatchGetImage                                                            
 • ecr:DescribeImages                                                           
 • ecr:BatchCheckLayerAvailability                                              
 • ecr:GetDownloadUrlForLayer                                                   
 • ecr:InitiateLayerUpload                                                      
 • ecr:UploadLayerPart                                                          
 • ecr:CompleteLayerUpload                                                      
 • ecr:PutImage                                                                 
 • ecr:GetAuthorizationToken                                                    
                                                                                
This resource type is not scoped to a single ECR repository. Instead, a         
connector configured with this resource type will grant access to all the ECR   
repositories that the credentials are allowed to access under the configured AWS
region (i.e. all repositories under the Docker registry URL                     
<account-id>.dkr.ecr.<region>.amazonaws.com).                                   
                                                                                
The resource name associated with this resource type uniquely identifies an ECR 
registry using one of the following formats (the repository name is ignored,    
only the registry URL/ARN is used):                                             
                                                                                
 • ECR repository URI:                                                          
   https://<account-id>.dkr.ecr.<region>.amazonaws.com[/<repository-name>]      
 • ECR repository ARN:                                                          
   arn:aws:ecr:<region>:<account-id>:repository[/<repository-name>]             
                                                                                
ECR repository names are region scoped. The connector can only be used to access
ECR repositories in the AWS region that it is configured to use.                
                                                                                
────────────────────────────────────────────────────────────────────────────────
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

Service Connector Types like the [Kubernetes Service Connector](kubernetes-service-connector.md) and [Docker Service Connector](docker-service-connector.md) can only handle one resource at a time: Kubernetes clusters and Docker container registries respectively. These basic Service Connector Types are the easiest to instantiate and manage, as each Service Connector instance is tied exactly to one resource (i.e. they are _single-instance_ connectors).

The following output shows two Service Connector instances configured from basic Service Connector Types:

* a Docker Service Connector that grants authenticated access to the DockerHub registry and allows pushing/pulling images that are stored in private repositories belonging to a DockerHub account
* a Kubernetes Service Connector that authenticates access to a Kubernetes cluster running on-premise and allows managing containerized workloads running there.

```
$ zenml service-connector list
┏━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━┓
┃ ACTIVE │ NAME           │ ID                                   │ TYPE          │ RESOURCE TYPES        │ RESOURCE NAME │ SHARED │ OWNER   │ EXPIRES IN │ LABELS ┃
┠────────┼────────────────┼──────────────────────────────────────┼───────────────┼───────────────────────┼───────────────┼────────┼─────────┼────────────┼────────┨
┃        │ dockerhub      │ b485626e-7fee-4525-90da-5b26c72331eb │ 🐳 docker     │ 🐳 docker-registry    │ docker.io     │ ➖     │ default │            │        ┃
┠────────┼────────────────┼──────────────────────────────────────┼───────────────┼───────────────────────┼───────────────┼────────┼─────────┼────────────┼────────┨
┃        │ kube-on-prem   │ 4315e8eb-fcbd-4938-a4d7-a9218ab372a1 │ 🌀 kubernetes │ 🌀 kubernetes-cluster │ 192.168.0.12  │ ➖     │ default │            │        ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━┛

```

### Cloud provider Service Connector Types

Cloud service providers like AWS, GCP and Azure implement one or more authentication schemes that are unified across a wide range or resources and services, all managed under the same umbrella. This allows users to access many different resources with a single set of authentication credentials. Some authentication methods are straightforward to set up, but are only meant to be used for development and testing. Other authentication schemes are powered by extensive roles and permissions management systems and are targeted at production environments where security and operations at scale are big concerns. The corresponding cloud provider Service Connector Types are designed accordingly:

* they support multiple types of resources (e.g. Kubernetes clusters, Docker registries, a form of object storage)
* they usually include some form of "generic" Resource Type that can be used by clients to access types of resources that are not yet part of the supported set. When this generic Resource Type is used, clients and Stack Components that access the connector are provided some form of generic session, credentials or client that can be used to access any of the cloud provider resources. For example, in the AWS case, clients accessing the `aws-generic` Resource Type are issued a pre-authenticated `boto3` Session object that can be used to access any AWS service.
* they support multiple authentication methods. Some of these allow clients direct access to long-lived, broad-access credentials and are only recommended for local development use. Others support distributing temporary API tokens automatically generated from long-lived credentials, which are safer for production use-cases, but may be more difficult to set up. A few authentication methods even support down-scoping the permissions of temporary API tokens so that they only allow access to the target resource and restrict access to everything else. This is covered at length [in the section on best practices for authentication methods](service-connectors-guide.md#best-practices-for-authentication-methods).&#x20;
* there is flexibility regarding the range of resources that a single cloud provider Service Connector instance configured with a single set of credentials can be scoped to access:
  * a _multi-type Service Connector_ instance can access any type of resources from the range of supported Resource Types&#x20;
  * a _multi-instance Service Connector_ instance can access multiple resources of the same type
  * a _single-instance Service Connector_ instance is scoped to access a single resource

The following output shows three different Service Connectors configured from the same GCP Service Connector Type using three different scopes but with the same credentials:

* a multi-type GCP Service Connector that allows access to every possible resource accessible with the configured credentials
* a multi-instance GCS Service Connector that allows access to multiple GCS buckets
* a single-instance GCS Serice Connector that only permits access to one GCS bucket

```
$ zenml service-connector list
┏━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━┓
┃ ACTIVE │ NAME                   │ ID                                   │ TYPE   │ RESOURCE TYPES        │ RESOURCE NAME           │ SHARED │ OWNER   │ EXPIRES IN │ LABELS ┃
┠────────┼────────────────────────┼──────────────────────────────────────┼────────┼───────────────────────┼─────────────────────────┼────────┼─────────┼────────────┼────────┨
┃        │ gcp-multi              │ 9d953320-3560-4a78-817c-926a3898064d │ 🔵 gcp │ 🔵 gcp-generic        │ <multiple>              │ ➖     │ default │            │        ┃
┃        │                        │                                      │        │ 📦 gcs-bucket         │                         │        │         │            │        ┃
┃        │                        │                                      │        │ 🌀 kubernetes-cluster │                         │        │         │            │        ┃
┃        │                        │                                      │        │ 🐳 docker-registry    │                         │        │         │            │        ┃
┠────────┼────────────────────────┼──────────────────────────────────────┼────────┼───────────────────────┼─────────────────────────┼────────┼─────────┼────────────┼────────┨
┃        │ gcs-multi              │ ff9c0723-7451-46b7-93ef-fcf3efde30fa │ 🔵 gcp │ 📦 gcs-bucket         │ <multiple>              │ ➖     │ default │            │        ┃
┠────────┼────────────────────────┼──────────────────────────────────────┼────────┼───────────────────────┼─────────────────────────┼────────┼─────────┼────────────┼────────┨
┃        │ gcs-langchain-slackbot │ cf3953e9-414c-4875-ba00-24c62a0dc0c5 │ 🔵 gcp │ 📦 gcs-bucket         │ gs://langchain-slackbot │ ➖     │ default │            │        ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━┛
```

### Local and remote availability

{% hint style="success" %}
You only need to be aware of local and remote availability for Service Connector Types if you are explicitly looking to use a Service Connector Type without installing its package prerequisites or if you are implementing or using a custom Service Connector Type implementation with your ZenML deployment. In all other cases, you may safely ignore this section.
{% endhint %}

The `LOCAL` and `REMOTE` flags in the `zenml service-connector list-types` output indicate if the Service Connector implementation is available locally (i.e. where the ZenML client and pipelines are running) and remotely (i.e. where the ZenML server is running).&#x20;

{% hint style="info" %}
All built-in Service Connector Types are by default available on the ZenML server, but some built-in Service Connector Types require additional Python packages to be installed to be available in your local environment. See the section documenting each Service Connector Type to find what these prerequisites are and how to install them.
{% endhint %}

The local/remote availability determines the possible actions and operations that can be performed with a Service Connector. The following are possible with a Service Connector Type that is available either locally or remotely:

* Service Connector registration, update and discovery (i.e. the `zenml service-connector register`, `zenml service-connector update`, `zenml service-connector list` and `zenml service-connector describe` CLI commands).
* Service Connector verification: checking whether its configuration and credentials are valid and can be actively used to access the remote resources (i.e. the `zenml service-connector verify` CLI commands).
* Listing the resources that can be accessed through a Service Connector (i.e. the `zenml service-connector verify` and `zenml service-connector list-resources` CLI commands)
* Connecting a Stack Component to a remote resource via a Service Connector&#x20;

The following operations are only possible with Service Connector Types that are locally available (with some notable exceptions covered in the information box that follows):

* Service Connector auto-configuration and discovery of credentials stored by a local client, CLI or SDK (e.g. aws or kubectl).
* Using the configuration and credentials managed by a Service Connector to configure a local client, CLI or SDK (e.g. docker or kubectl).
* Running pipelines with a Stack Component that is connected to a remote resource through a Service Connector&#x20;

{% hint style="info" %}
One interesting and useful byproduct of the way cloud provider Service Connectors are designed is the fact that you don't need to have the cloud provider Service Connector Type available client-side to be able to access some of its resources. Take the following situation for example:

* the GCP Service Connector Type can provide access to GKE Kubernetes clusters and GCR Docker container registries.
* however, you don't need the GCP Service Connector Type or any GCP libraries to be installed on the ZenML clients to connect to and use those Kubernetes clusters or Docker registries in your ML pipelines.
* the Kubernetes Service Connector Type is enough to access any Kubernetes cluster, regardless of its provenance (AWS, GCP etc.)
* the Docker Service Connector Type is enough to access any Docker container registry, regardless of its provenance (AWS, GCP, etc.)
{% endhint %}

## Best practices for authentication methods

Service Connector Types, especially those targeted at cloud providers, offer a plethora of authentication methods matching those supported by the remote cloud platforms. While there is no single authentication standard that unifies this process, there are some patterns that are easily identifiable and can be used as guidelines when deciding which authentication method to use to configure a Service Connector.

This section explores some of those patterns and gives some advice regarding which authentication methods are best suited for your needs.

{% hint style="info" %}
This section may require some general knowledge about authentication and authorization to be properly understood. We tried to keep it simple and limit ourselves to talking about high-level concepts, but some areas may get a bit too technical.
{% endhint %}

### Username and password

{% hint style="danger" %}
The key take-away is this: you should avoid using your primary account password as authentication credentials as much as possible. If there are alternative authentication methods that you can use or other types of credentials (e.g. session tokens, API keys, API tokens), you should always try to use those instead.

Ultimately, if you have no choice, be cognizant of the third parties you share your passwords with. If possible, they should never leave the premises of your local host or development environment.
{% endhint %}

This is the typical authentication method that uses a username or account name plus the associated password. While this is the de facto method used to authenticate with web consoles and local CLIs, this is the least secure of all authentication methods and _never_ something you want to share with other members of your team or organization or use to authenticate automated workloads.

In fact, cloud platforms don't even allow using user account passwords directly as a credential when authenticating to the cloud platform APIs. There is always a process in place that allows exchanging the account/password credential for [another form of long-lived credential](service-connectors-guide.md#long-lived-credentials-api-keys-account-keys).

Even when passwords are mentioned as credentials, some services (e.g. DockerHub) also allow using an API access key in place of the user account password.

### Implicit authentication

{% hint style="info" %}
The key take-away here is that implicit authentication gives you immediate access to some cloud resources and require no configuration, but it may take some extra effort to expand the range of resources that you're initially allowed to access with it. This is not an authentication method you want to use if you're interested in portability and enabling others to reproduce your results.
{% endhint %}

Implicit authentication is just a fancy way of saying that the Service Connector will use locally stored credentials, configuration files, environment variables, basically any form of authentication available on the environment where it is running, either locally or in the cloud.

Most cloud providers and their associated Service Connector Types include some form of implicit authentication that is able to automatically discover and use the following forms of authentication in the environment where they are running:

* configuration and credentials set up and stored locally through the cloud platform CLI
* configuration and credentials passed as environment variables
* some form of implicit authentication attached to the workload environment itself. This is only available in virtual environments that are already running inside the same cloud where other resources are available for use. This is called differently depending on the cloud provider in question, but they are essentially the same thing:
  * in AWS, if you're running on Amazon EC2, ECS, EKS, Lambda or some other form of AWS cloud workload, credentials can be loaded directly from _the instance metadata service._ This [uses the IAM role attached to your workload](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html) to authenticate to other AWS services without the need to configure explicit credentials.
  * in GCP, a similar _metadata service_ allows accessing other GCP cloud resources via [the service account attached to the GCP workload](https://cloud.google.com/docs/authentication/application-default-credentials#attached-sa) (e.g. GCP VMs or GKE clusters).
  * in Azure, the [Azure Managed Identity](https://learn.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/overview) services can be used to gain access to other Azure services without requiring explicit credentials

There are a few caveats that you should be aware of when choosing an implicit authentication method. It may seem like the easiest way out, but it carries with it some implications that may impact portability and usability later down the road:

* when used with a local ZenML deployment, like the default deployment, or [a local ZenML server started with `zenml up`](../../../user-guide/starter-guide/transition-to-the-cloud.md), the implicit authentication method will use the configuration files and credentials or environment variables set up _on your local machine_. These will not be available to anyone else outside your local environment and will also not be accessible to workloads running in other environments on your local host. This includes for example local K3D Kubernetes clusters and local Docker containers.
* when used with a remote ZenML server, the implicit authentication method only works if your ZenML server is deployed in the same cloud as the one supported by the Service Connector Type that you are using. For instance, if you're using the AWS Service Connector Type, then the ZenML server must also be deployed in AWS (e.g. in an EKS Kubernetes cluster). You may also need to manually adjust the cloud configuration of the remote cloud workload where the ZenML server is running to allow access to resources (e.g. add permissions to the AWS IAM role attached to the EC2 or EKS node, add roles to the GCP service account attached to the GKE cluster nodes).

<details>

<summary>GCP implicit authentication method example</summary>

The following is an example of using the GCP Service Connector's implicit authentication method to gain immediate access to all the GCP resources that the ZenML server also has access to. Note that this is only possible because the ZenML server is also deployed in GCP, in a GKE cluster, and the cluster is attached to a GCP service account with permissions to access the project resources:

```
$ zenml service-connector register gcp-implicit --type gcp --auth-method implicit --project_id=zenml-core
Successfully registered service connector `gcp-implicit` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────────────┼────────────────┨
┃ 0e244dd6-6f0a-4e63-ae79-33f8d6d6f8f9 │ gcp-implicit   │ 🔵 gcp         │ 🔵 gcp-generic        │ 🤷 none listed ┃
┃                                      │                │                │ 📦 gcs-bucket         │                ┃
┃                                      │                │                │ 🌀 kubernetes-cluster │                ┃
┃                                      │                │                │ 🐳 docker-registry    │                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛

$ zenml service-connector verify gcp-implicit --resource-type gcs-bucket
Service connector 'gcp-implicit' is correctly configured with valid credentials and has access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE │ RESOURCE NAMES                                  ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────┼─────────────────────────────────────────────────┨
┃ 0e244dd6-6f0a-4e63-ae79-33f8d6d6f8f9 │ gcp-implicit   │ 🔵 gcp         │ 📦 gcs-bucket │ gs://annotation-gcp-store                       ┃
┃                                      │                │                │               │ gs://zenml-bucket-sl                            ┃
┃                                      │                │                │               │ gs://zenml-kubeflow-artifact-store              ┃
┃                                      │                │                │               │ gs://zenml-project-time-series-bucket           ┃
┃                                      │                │                │               │ gs://zenml-public-bucket                        ┃
┃                                      │                │                │               │ gs://zenml-vertex-test                          ┃
┃                                      │                │                │               │ gs://zenml_projects_artifact_store              ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

$ zenml service-connector verify gcp-implicit --resource-type kubernetes-cluster
Service connector 'gcp-implicit' is correctly configured with valid credentials and has access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES     ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────────────┼────────────────────┨
┃ 0e244dd6-6f0a-4e63-ae79-33f8d6d6f8f9 │ gcp-implicit   │ 🔵 gcp         │ 🌀 kubernetes-cluster │ zenml-test-cluster ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┛

$ zenml service-connector verify gcp-implicit --resource-type docker-registry
Service connector 'gcp-implicit' is correctly configured with valid credentials and has access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE      │ RESOURCE NAMES    ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼────────────────────┼───────────────────┨
┃ 0e244dd6-6f0a-4e63-ae79-33f8d6d6f8f9 │ gcp-implicit   │ 🔵 gcp         │ 🐳 docker-registry │ gcr.io/zenml-core ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━┛
```

</details>

### Long-lived credentials (API keys, account keys)

{% hint style="success" %}
This is the magic formula of authentication methods. When paired with another ability, such as [automatically generating short-lived API tokens](service-connectors-guide.md#issuing-temporary-and-down-scoped-credentials), or [impersonating accounts or assuming roles](service-connectors-guide.md#impersonating-accounts-and-assuming-roles), this is the ideal authentication mechanism to use, particularly when using ZenML in production and when sharing results with other members of your ZenML team.
{% endhint %}

As a general best practice, but implemented particularly well for cloud platforms, account passwords are never directly used as a credential when authenticating to the cloud platform APIs. There is always a process in place that exchanges the account/password credential for another type of long-lived credential:

* AWS uses the [`aws configure` CLI command](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)&#x20;
* GCP offers the [`gcloud auth login` and `gcloud auth application-default login` CLI commands](https://cloud.google.com/sdk/docs/authorizing)
* Azure provides [the `az login` CLI command](https://learn.microsoft.com/en-us/cli/azure/authenticate-azure-cli)

None of your original login information is stored on your local machine or used to access workloads. Instead, an API key, account key or some other form of intermediate credential is generated and stored on the local host and used to authenticate to remote cloud service APIs.

{% hint style="info" %}
When using auto-configuration with Service Connector registration, this is usually the type of credentials automatically identified and extracted from your local machine.
{% endhint %}

Different cloud providers use different names for these types of long-lived credentials, but they usually represent the same concept, with minor variations regarding the identity information and level of permissions attached to them:

* AWS has [Account Access Keys](https://docs.aws.amazon.com/powershell/latest/userguide/pstools-appendix-sign-up.html) and [IAM User Access Keys](https://docs.aws.amazon.com/IAM/latest/UserGuide/id\_credentials\_access-keys.html)
* GCP has [User Account Credentials](https://cloud.google.com/docs/authentication#user-accounts) and [Service Account Credentials](https://cloud.google.com/docs/authentication#service-accounts)

Generally speaking, a differentiation is being made between the following two classes of credentials:

* _user credentials_: credentials representing a human user and usually directly tied to a user account identity. These credentials are usually associated with a broad spectrum of permissions and it is therefore not recommended to share them or make them available outside the confines of your local host.&#x20;
* _service credentials:_ credentials used with automated processes and programmatic access, where humans are not directly involved. These credentials are not directly tied to a user account identity, but some other form of accounting like a service account or an IAM user devised to be used by non-human actors. It is also usually possible to restrict the range of permissions associated with this class of credentials, which makes them better candidates for sharing them with a larger audience.

ZenML cloud provider Service Connectors can use both classes of credentials, but you should aim to use _service credentials_ as often as possible instead of _user credentials_, especially in production environments. Attaching automated workloads like ML pipelines to service accounts instead of user accounts acts as an extra layer of protection for your user identity and facilitates enforcing another security best practice called [_"the least-privilege principle"_](https://en.wikipedia.org/wiki/Principle\_of\_least\_privilege)_:_ granting each actor only the minimum level of permissions required to function correctly.

Using long-lived credentials on their own still isn't ideal, because if leaked, they pose a security risk, even when they have limited permissions attached. The good news is that ZenML Service Connectors include additional mechanisms that, when used in combination with long-lived credentials, make it even safer to share long-lived credentials with other ZenML users and automated workloads:

* automatically [generating temporary credentials](service-connectors-guide.md#generating-temporary-and-down-scoped-credentials) from long-lived credentials and even downgrading their permission scope to enforce the least-privilege principle
* implementing [authentication schemes that impersonate accounts and assume roles](service-connectors-guide.md#impersonating-accounts-and-assuming-roles)

### Generating temporary and down-scoped credentials

Most [authentication methods that utilize long-lived credentials](service-connectors-guide.md#long-lived-credentials-api-keys-account-keys) also implement additional mechanisms that help reduce the accidental credentials exposure and risk of security incidents even further, making them ideal for production.

_**Issuing temporary credentials**_: this authentication strategy keeps long-lived credentials safely stored on the ZenML server and away from the eyes of actual API clients and people that need to authenticate to the remote resources. Instead, clients are issued API tokens that have a limited lifetime and expire after a given amount of time. The Service Connector is able to generate these API tokens from long-lived credentials on a need-to-have basis. For example, the AWS Service Connector's "Session Token", "Federation Token" and "IAM Role" authentication methods and basically all authentication methods supported by the GCP Service Connector support this feature.

<details>

<summary>AWS temporary credentials example</summary>

The following example shows the difference between the long-lived AWS credentials configured for an AWS Service Connector and kept on the ZenML server and the temporary Kubernetes API token credentials that the client receives and uses to access the resource. Note the expiration time on the Kubernetes API token:

```
$ zenml service-connector describe eks-zenhacks-cluster
Service connector 'eks-zenhacks-cluster' of type 'aws' with id '7365b136-65b2-4a88-8283-9ecaefbe812b' is owned by user 'default' and is 'private'.
   'eks-zenhacks-cluster' aws Service Connector Details    
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                ┃
┠──────────────────┼──────────────────────────────────────┨
┃ ID               │ 7365b136-65b2-4a88-8283-9ecaefbe812b ┃
┠──────────────────┼──────────────────────────────────────┨
┃ NAME             │ eks-zenhacks-cluster                 ┃
┠──────────────────┼──────────────────────────────────────┨
┃ TYPE             │ 🔶 aws                               ┃
┠──────────────────┼──────────────────────────────────────┨
┃ AUTH METHOD      │ session-token                        ┃
┠──────────────────┼──────────────────────────────────────┨
┃ RESOURCE TYPES   │ 🌀 kubernetes-cluster                ┃
┠──────────────────┼──────────────────────────────────────┨
┃ RESOURCE NAME    │ zenhacks-cluster                     ┃
┠──────────────────┼──────────────────────────────────────┨
┃ SECRET ID        │ 735c0e1a-cf1e-4a43-aed0-144b9a61c903 ┃
┠──────────────────┼──────────────────────────────────────┨
┃ SESSION DURATION │ 43200s                               ┃
┠──────────────────┼──────────────────────────────────────┨
┃ EXPIRES IN       │ N/A                                  ┃
┠──────────────────┼──────────────────────────────────────┨
┃ OWNER            │ default                              ┃
┠──────────────────┼──────────────────────────────────────┨
┃ WORKSPACE        │ default                              ┃
┠──────────────────┼──────────────────────────────────────┨
┃ SHARED           │ ➖                                   ┃
┠──────────────────┼──────────────────────────────────────┨
┃ CREATED_AT       │ 2023-05-17 14:33:06.173039           ┃
┠──────────────────┼──────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-05-17 14:33:06.173041           ┃
┗━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
            Configuration            
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━┓
┃ PROPERTY              │ VALUE     ┃
┠───────────────────────┼───────────┨
┃ region                │ us-east-1 ┃
┠───────────────────────┼───────────┨
┃ aws_access_key_id     │ [HIDDEN]  ┃
┠───────────────────────┼───────────┨
┃ aws_secret_access_key │ [HIDDEN]  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━┛

$ zenml service-connector describe eks-zenhacks-cluster --client
Service connector 'eks-zenhacks-cluster (kubernetes-cluster | zenhacks-cluster client)' of type 'kubernetes' with id '7365b136-65b2-4a88-8283-9ecaefbe812b' is owned by user 'default' and is 
'private'.
 'eks-zenhacks-cluster (kubernetes-cluster | zenhacks-cluster client)' kubernetes Service 
                                    Connector Details                                     
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                               ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ ID               │ 7365b136-65b2-4a88-8283-9ecaefbe812b                                ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ NAME             │ eks-zenhacks-cluster (kubernetes-cluster | zenhacks-cluster client) ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ TYPE             │ 🌀 kubernetes                                                       ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ AUTH METHOD      │ token                                                               ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ RESOURCE TYPES   │ 🌀 kubernetes-cluster                                               ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ RESOURCE NAME    │ arn:aws:eks:us-east-1:715803424590:cluster/zenhacks-cluster         ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ SECRET ID        │                                                                     ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ SESSION DURATION │ N/A                                                                 ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ EXPIRES IN       │ 11h59m56s                                                           ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ OWNER            │ default                                                             ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ WORKSPACE        │ default                                                             ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ SHARED           │ ➖                                                                  ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ CREATED_AT       │ 2023-05-17 14:33:41.861267                                          ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-05-17 14:33:41.861269                                          ┃
┗━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                           Configuration                                            
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY              │ VALUE                                                                    ┃
┠───────────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ server                │ https://A5F8F4142FB12DDCDE9F21F6E9B07A18.gr7.us-east-1.eks.amazonaws.com ┃
┠───────────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ insecure              │ False                                                                    ┃
┠───────────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ cluster_name          │ arn:aws:eks:us-east-1:715803424590:cluster/zenhacks-cluster              ┃
┠───────────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ token                 │ [HIDDEN]                                                                 ┃
┠───────────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ certificate_authority │ [HIDDEN]                                                                 ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

```

</details>

_**Issuing downscoped credentials**_: in addition to the above, some authentication methods also support restricting the generated temporary API tokens to the minimum set of permissions required to access the target resource or set of resources. This is currently available for the AWS Service Connector's "Federation Token" and "IAM Role" authentication methods.

<details>

<summary>AWS down-scoped credentials example</summary>

It's not easy to showcase this without using some ZenML Python Client code, but here is an example that proves that the AWS client token issued to an S3 client can only access the S3 bucket resource it was issued for, even if the originating AWS Service Connector is able to access multiple S3 buckets with the corresponding long-lived credentials:

```
$ zenml service-connector register aws-federation-multi --type aws --auth-method=federation-token --auto-configure 
⠴ Registering service connector 'aws-federation-multi'...
Successfully registered service connector `aws-federation-multi` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME       │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼──────────────────────┼────────────────┼───────────────────────┼────────────────┨
┃ 88b82bbe-bf35-4fbe-8805-217121c133c9 │ aws-federation-multi │ 🔶 aws         │ 🔶 aws-generic        │ 🤷 none listed ┃
┃                                      │                      │                │ 📦 s3-bucket          │                ┃
┃                                      │                      │                │ 🌀 kubernetes-cluster │                ┃
┃                                      │                      │                │ 🐳 docker-registry    │                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛

$ zenml service-connector verify aws-federation-multi --resource-type s3-bucket
Service connector 'aws-federation-multi' is correctly configured with valid credentials and has access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME       │ CONNECTOR TYPE │ RESOURCE TYPE │ RESOURCE NAMES                        ┃
┠──────────────────────────────────────┼──────────────────────┼────────────────┼───────────────┼───────────────────────────────────────┨
┃ 88b82bbe-bf35-4fbe-8805-217121c133c9 │ aws-federation-multi │ 🔶 aws         │ 📦 s3-bucket  │ s3://public-flavor-logos              ┃
┃                                      │                      │                │               │ s3://zenbytes-bucket                  ┃
┃                                      │                      │                │               │ s3://zenfiles                         ┃
┃                                      │                      │                │               │ s3://zenml-demos                      ┃
┃                                      │                      │                │               │ s3://zenml-generative-chat            ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

# The next part involves running some ZenML Python code

$ python
>>> from zenml.client import Client
>>> client = Client()
>>>
>>> # Get a Service Connector client for a particular S3 bucket
>>> connector_client = client.get_service_connector_client(name_id_or_prefix="aws-federation-multi", resource_type="s3-bucket", resource_id="s3://zenfiles")
>>>
>>> # Get the S3 boto3 python client pre-configured and pre-authenticated
>>> # from the Service Connector client
>>> s3_client = connector_client.connect()
>>>
>>> # Verify access to the chosen S3 bucket using the temporary token that
>>> # was issued to the client.
>>> s3_client.head_bucket(Bucket="zenfiles")
{'ResponseMetadata': {'HTTPStatusCode': 200, ...}}
>>>
>>> # Try to access another S3 bucket that the original AWS long-lived credentials can access.
>>> # An error will be thrown indicating that the bucket is not accessible.
>>> s3_client.head_bucket(Bucket="zenml-demos")
╭─────────────────────────────── Traceback (most recent call last) ────────────────────────────────╮
│ <stdin>:1 in <module>                                                                            │
│                                                                                                  │
│ /home/stefan/aspyre/src/zenml/.venv/lib/python3.8/site-packages/botocore/client.py:530 in        │
│ _api_call                                                                                        │
│                                                                                                  │
│    527 │   │   │   │   │   f"{py_operation_name}() only accepts keyword arguments."              │
│    528 │   │   │   │   )                                                                         │
│    529 │   │   │   # The "self" in this scope is referring to the BaseClient.                    │
│ ❱  530 │   │   │   return self._make_api_call(operation_name, kwargs)                            │
│    531 │   │                                                                                     │
│    532 │   │   _api_call.__name__ = str(py_operation_name)                                       │
│    533                                                                                           │
│                                                                                                  │
│ /home/stefan/aspyre/src/zenml/.venv/lib/python3.8/site-packages/botocore/client.py:964 in        │
│ _make_api_call                                                                                   │
│                                                                                                  │
│    961 │   │   if http.status_code >= 300:                                                       │
│    962 │   │   │   error_code = parsed_response.get("Error", {}).get("Code")                     │
│    963 │   │   │   error_class = self.exceptions.from_code(error_code)                           │
│ ❱  964 │   │   │   raise error_class(parsed_response, operation_name)                            │
│    965 │   │   else:                                                                             │
│    966 │   │   │   return parsed_response                                                        │
│    967                                                                                           │
╰──────────────────────────────────────────────────────────────────────────────────────────────────╯
ClientError: An error occurred (403) when calling the HeadBucket operation: Forbidden
```

</details>

### Impersonating accounts and assuming roles

{% hint style="success" %}
These types of authentication methods require more work to set up because multiple permission bearing accounts and roles need to be provisioned in advance depending on the target audience. On the other hand, they also provide the most flexibility and control. Despite their operational cost, if you are a platform engineer and have the infrastructure know-how necessary to understand and set up the authentication resources, this is for you.
{% endhint %}

These authentication methods deliver another way of [configuring long-lived credentials](service-connectors-guide.md#long-lived-credentials-api-keys-account-keys) in your Service Connectors without exposing them to clients. They are especially useful as an alternative to cloud provider Service Connectors authentication methods that do not support [automatically downscoping the permissions of issued temporary tokens](service-connectors-guide.md#generating-temporary-and-down-scoped-credentials).

The processes of account impersonation and role assumption are very similar and can be summarized as follows:

* you configure a Service Connector with long-lived credentials associated with a primary user account or primary service account (preferable). As a best practice, it is common to attach a reduced set of permissions or even no permissions to these credentials other than those that allow the account impersonation or role assumption operation. This makes it more difficult to do any damage if the primary credentials are accidentally leaked.
* in addition to the primary account and its long-lived credentials, you also need to provision one or more secondary access entities in the cloud platform bearing the effective permissions that will be needed to access the target resource(s):
  * one or more IAM roles (to be assumed)
  * one or more service accounts (to be impersonated)
* the Service Connector configuration also needs to contain the name of a target IAM role to be assumed or a service account to be impersonated.
* upon request, the Service Connector will exchange the long-lived credentials associated with the primary account for short-lived API tokens that only have the permissions associated with the target IAM role or service account. These temporary credentials are issued to clients and used to access the target resource, while the long-lived credentials are kept safe and never have to leave the ZenML server boundary.

<details>

<summary>GCP account impersonation example</summary>

For this example, we have the following set up in GCP:

* a primary `empty-connectors@zenml-core.iam.gserviceaccount.com` GCP service account with no permissions whatsoever aside from the "Service Account Token Creator" role that allows it to impersonate the secondary service account below. We also generate a service account key for this account.
* a secondary `zenml-bucket-sl@zenml-core.iam.gserviceaccount.com` GCP service account that only has permissions to access the `zenml-bucket-sl` GCS bucket

First, let's show that the `empty-connectors` service account has no permissions to access any GCS buckets or any other resources for that matter. We'll register a regular GCP Service Connector that uses the service account key (long-lived credentials) directly:

```
$ zenml service-connector register gcp-empty-sa --type gcp --auth-method service-account --service_account_json=@empty-connectors@zenml-core.json  --project_id=zenml-core
Expanding argument value service_account_json to contents of file /home/stefan/aspyre/src/zenml/empty-connectors@zenml-core.json.
Successfully registered service connector `gcp-empty-sa` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────────────┼────────────────┨
┃ db967769-4cd5-4f07-a3f4-54e3fe534d88 │ gcp-empty-sa   │ 🔵 gcp         │ 🔵 gcp-generic        │ 🤷 none listed ┃
┃                                      │                │                │ 📦 gcs-bucket         │                ┃
┃                                      │                │                │ 🌀 kubernetes-cluster │                ┃
┃                                      │                │                │ 🐳 docker-registry    │                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛

$ zenml service-connector verify gcp-empty-sa --resource-type kubernetes-cluster
Error: Service connector 'gcp-empty-sa' verification failed: connector authorization failure: Failed to list GKE clusters:
403 Required "container.clusters.list" permission(s) for "projects/20219041791".

$ zenml service-connector verify gcp-empty-sa --resource-type gcs-bucket
Error: Service connector 'gcp-empty-sa' verification failed: connector authorization failure: failed to list GCS buckets:
403 GET https://storage.googleapis.com/storage/v1/b?project=zenml-core&projection=noAcl&prettyPrint=false:
empty-connectors@zenml-core.iam.gserviceaccount.com does not have storage.buckets.list access to the Google Cloud project.
Permission 'storage.buckets.list' denied on resource (or it may not exist).

$ zenml service-connector verify gcp-empty-sa --resource-type gcs-bucket --resource-id zenml-bucket-sl
Error: Service connector 'gcp-empty-sa' verification failed: connector authorization failure: failed to fetch GCS bucket
zenml-bucket-sl: 403 GET https://storage.googleapis.com/storage/v1/b/zenml-bucket-sl?projection=noAcl&prettyPrint=false:
empty-connectors@zenml-core.iam.gserviceaccount.com does not have storage.buckets.get access to the Google Cloud Storage bucket.
Permission 'storage.buckets.get' denied on resource (or it may not exist).

```

Next, we'll register a GCP Service Connector that actually uses account impersonation to access the `zenml-bucket-sl` GCS bucket and verify that it can actually access the bucket:

```
$ zenml service-connector register gcp-impersonate-sa --type gcp --auth-method impersonation --service_account_json=@empty-connectors@zenml-core.json  --project_id=zenml-core --target_principal=zenml-bucket-sl@zenml-core.iam.gserviceaccount.com --resource-type gcs-bucket --resource-id gs://zenml-bucket-sl
Expanding argument value service_account_json to contents of file /home/stefan/aspyre/src/zenml/empty-connectors@zenml-core.json.
Successfully registered service connector `gcp-impersonate-sa` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME     │ CONNECTOR TYPE │ RESOURCE TYPE │ RESOURCE NAMES       ┃
┠──────────────────────────────────────┼────────────────────┼────────────────┼───────────────┼──────────────────────┨
┃ f586c28e-3d60-4be5-8961-853592c48e41 │ gcp-impersonate-sa │ 🔵 gcp         │ 📦 gcs-bucket │ gs://zenml-bucket-sl ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┛

$ zenml service-connector verify gcp-impersonate-sa --resource-type gcs-bucket --resource-id zenml-bucket-sl
Service connector 'gcp-impersonate-sa' is correctly configured with valid credentials and has access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME     │ CONNECTOR TYPE │ RESOURCE TYPE │ RESOURCE NAMES       ┃
┠──────────────────────────────────────┼────────────────────┼────────────────┼───────────────┼──────────────────────┨
┃ f586c28e-3d60-4be5-8961-853592c48e41 │ gcp-impersonate-sa │ 🔵 gcp         │ 📦 gcs-bucket │ gs://zenml-bucket-sl ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┛
```

</details>

### Short-lived credentials

{% hint style="warning" %}
This category of authentication methods uses temporary credentials explicitly configured in the Service Connector. Of all available authentication methods, this is probably the least useful and you will likely never have to manually generate and use temporary credentials to authenticate to remote resources because they are terribly impractical: when they expire, Service Connectors become unusable and need to either be manually updated or replaced.
{% endhint %}

A previous section described how [temporary credentials can be automatically generated from other, long-lived credentials](service-connectors-guide.md#generating-temporary-and-down-scoped-credentials) by most cloud provider Service Connectors. It only stands to reason that temporary credentials can also be generated manually by external means such as cloud provider CLIs and used directly to configure Service Connectors.

This may be used as a way to grant an external party temporary access to some resources and have the Service Connector automatically become unusable (i.e. expire) after some time.

## Register Service Connectors

## Discover available resources

## Connect Stack Components to resources

### Using Resource Types as requirements

Service Connectors and the resources and services that they can authenticate to and grant access to are only useful because they are a means of providing Stack Components . instead of configuring credentials or secrets directly in the Stack Component configuration

