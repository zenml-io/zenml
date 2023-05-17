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
* they support multiple authentication methods. Some of these allow clients direct access to long-lived, broad-access credentials and are only recommended for local development use. Others support distributing temporary API tokens automatically generated from long-lived credentials, which are safer for production use-cases, but may be more difficult to set up. A few authentication methods even support down-scoping the permissions of temporary API tokens so that they only allow access to the target resource and restrict access to everything else.
* there is flexibility regarding the range of resources that a single cloud provider Service Connector instance configured with a single set of credentials can be scoped to access:
  * a _multi-type Service Connector_ instance can access any type of resources from the range of supported Resource Types&#x20;
  * a _multi-instance Service Connector_ instance can access multiple resources of the same type
  * a _single-instance Service Connector_ instance is scoped to access a single resource

The following output shows three different Service Connectors configured from the same GCP Service Connector Type using three different scopes:

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

### Username and password

{% hint style="danger" %}
The key take-away is this: you should avoid using your primary account password as authentication credentials as much as possible. If there are alternative authentication methods that you can use or other types of credentials (e.g. session tokens, API keys, API tokens), you should always try to use those instead.

Ultimately, if you have no choice, be cognizant of the third parties you share your passwords with. If possible, they should never leave the premises of your local host or development environment.
{% endhint %}

This is the typical authentication method that uses a username or account name plus the associated password. While this is the de facto method used to authenticate with web consoles and local CLIs, this is the least secure of all authentication methods and _never_ something you want to share with other members of your team or organization or use to authenticate automated workloads.

In fact, cloud platforms don't even allow using the root account password directly as a credential when authenticating to the cloud platform APIs. There is always a process in place that allows exchanging the account/password credential for something else:

* AWS uses the [`aws configure` CLI command](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)&#x20;
* GCP offers the [`gcloud auth login` and `gcloud auth application-default login` CLI commands](https://cloud.google.com/sdk/docs/authorizing)
* Azure provides [the `az login` CLI command](https://learn.microsoft.com/en-us/cli/azure/authenticate-azure-cli)

None of your original login information is stored on your local machine. Instead, an authentication token, a secret key or some other form of intermediate credential is generated and stored on the local host and used to authenticate to remote cloud service APIs.

Some services (e.g. DockerHub) allow using an API access key instead of the password, which is always preferable to plain passwords.

### Implicit authentication

{% hint style="info" %}
The key take-away here is that implicit authentication gives you immediate access to some cloud resources, but it may take some extra effort to expand the range of resources that you're initially allowed to access with it. This is not an authentication method you want to use if you're interested in portability and enabling others to reproduce your results.
{% endhint %}

Implicit authentication is just a fancy way of saying that the Service Connector will use locally stored credentials, configuration files, environment variables, basically any form of authentication available on the environment where it is running, either locally or in the cloud.

Most cloud providers and their associated Service Connector Types include some form of implicit authentication that is able to automatically discover and use the following forms of authentication:

* configuration and credentials set up and stored locally through the cloud platform CLI
* configuration and credentials passed as environment variables
* some form of implicit authentication attached to the workload environment itself. This is only available in virtual environments that are already running inside the same cloud where other resources are available for use. This is called differently depending on the cloud provider in question, but they are essentially the same thing:
  * in AWS, if you're running on Amazon EC2, ECS, EKS, Lambda or some other form of AWS cloud workload, credentials can be loaded directly from _the instance metadata service._ This [uses the IAM role attached to your workload](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html) to authenticate to other AWS services without the need to configure explicit credentials.
  * in GCP, a similar _metadata service_ allows accessing othe GCP cloud resources via [the service account attached to the GCP workload](https://cloud.google.com/docs/authentication/application-default-credentials#attached-sa).
  * in Azure, the [Azure Managed Identity](https://learn.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/overview) services can be used to gain access to other Azure services without requiring explicit credentials

There are a few cave-ats that you should be aware of when choosing an implicit authentication method. It may seem like the easiest way out, but it carries with it some implications that may impact portability and usability:

* when used with a local ZenML deployment, like the default deployment, or [a local ZenML server started with `zenml up`](../../../user-guide/starter-guide/transition-to-the-cloud.md) the implicit authentication method will use the configuration files and credentials or environment variables set up _on your local machine_. These will not be available to anyone else outside your local environment and will also not be accessible to workloads running in other environments on your local host. This includes for example local Kubernetes clusters and local Docker containers.
* when used with a remote ZenML server, the implicit authentication method only works if your ZenML server is deployed in the same cloud as the one supported by the Service Connector Type that you are using. For instance, if you're using the AWS Service Connector Type, then the ZenML server must also be deployed in AWS (e.g. in an EKS Kubernetes cluster). You may also need to manually adjust the cloud configuration of the remote cloud workload where the ZenML server is running to allow access to more resources (e.g. add more permissions to the AWS IAM role attached to the EC2 or EKS node, add more roles to the GCP service account attached to the GKE cluster nodes).

### Long-lived credentials (API keys, account keys)

#### Impersonating accounts and assuming roles

#### Issuing temporary and down-scoped credentials

### Short-lived credentials

## Register Service Connectors

## Discover available resources

## Connect Stack Components to resources

### Using Resource Types as requirements

Service Connectors and the resources and services that they can authenticate to and grant access to are only useful because they are a means of providing Stack Components . instead of configuring credentials or secrets directly in the Stack Component configuration

