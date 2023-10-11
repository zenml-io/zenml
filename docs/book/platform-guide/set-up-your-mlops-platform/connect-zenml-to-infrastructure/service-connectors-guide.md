---
description: The complete guide to managing Service Connectors and connecting ZenML to external resources.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Service Connectors guide

This documentation section contains everything that you need to use Service Connectors to connect ZenML to external resources. A lot of information is covered, so it might be useful to use the following guide to navigate it:

* if you're only getting started with Service Connectors, we suggest starting by familiarizing yourself with the [terminology](service-connectors-guide.md#terminology).
* check out the section on [Service Connector Types](service-connectors-guide.md#cloud-provider-service-connector-types) to understand the different Service Connector implementations that are available and when to use them.
* jumping straight to the sections on [Registering Service Connectors](service-connectors-guide.md#register-service-connectors) can get you set up quickly if you are only looking for a quick way to evaluate Service Connectors and their features.
* if all you need to do is connect a ZenML Stack Component to an external resource or service like a Kubernetes cluster, a Docker container registry, or an object storage bucket and you already have some Service Connectors available, the section on [connecting Stack Components to resources](service-connectors-guide.md#connect-stack-components-to-resources) is all you need.

In addition to this guide, there is an entire section dedicated to [best security practices concerning the various authentication methods](best-security-practices.md) implemented by Service Connectors, such as which types of credentials to use in development or production and how to keep your security information safe. That section is particularly targeted at engineers with some knowledge of infrastructure, but it should be accessible to larger audiences.

## Terminology

As with any high-level abstraction, some terminology is needed to express the concepts and operations involved. In spite of the fact that Service Connectors cover such a large area of application as authentication and authorization for a variety of resources from a range of different vendors, we managed to keep this abstraction clean and simple. In the following expandable sections, you'll learn more about Service Connector Types, Resource Types, Resource Names, and Service Connectors.

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
                                                                                
The ZenML AWS Service Connector facilitates the authentication and access to    
managed AWS services and resources. These encompass a range of resources,       
including S3 buckets, ECR repositories, and EKS clusters. The connector provides
support for various authentication methods, including explicit long-lived AWS   
secret keys, IAM roles, short-lived STS tokens and implicit authentication.     
                                                                                
To ensure heightened security measures, this connector also enables the         
generation of temporary STS security tokens that are scoped down to the minimum 
permissions necessary for accessing the intended resource. Furthermore, it      
includes automatic configuration and detection of credentials locally configured
through the AWS CLI.                                                            
                                                                                
This connector serves as a general means of accessing any AWS service by issuing
pre-authenticated boto3 sessions to clients. Additionally, the connector can    
handle specialized authentication for S3, Docker and Kubernetes Python clients. 
It also allows for the configuration of local Docker and Kubernetes CLIs.       
                                                                                
The AWS Service Connector is part of the AWS ZenML integration. You can either  
install the entire integration or use a pypi extra to install it independently  
of the integration:                                                             
                                                                                
 • pip install zenml[connectors-aws] installs only prerequisites for the AWS    
   Service Connector Type                                                       
 • zenml integration install aws installs the entire AWS ZenML integration      
                                                                                
It is not required to install and set up the AWS CLI on your local machine to   
use the AWS Service Connector to link Stack Components to AWS resources and     
services. However, it is recommended to do so if you are looking for a quick    
setup that includes using the auto-configuration Service Connector features.    
                                                                                
────────────────────────────────────────────────────────────────────────────────
```

```sh
$ zenml service-connector describe-type aws --resource-type kubernetes-cluster
╔══════════════════════════════════════════════════════════════════════════════╗
║      🌀 AWS EKS Kubernetes cluster (resource type: kubernetes-cluster)       ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                                                                
Authentication methods: implicit, secret-key, sts-token, iam-role,              
session-token, federation-token                                                 
                                                                                
Supports resource instances: True                                               
                                                                                
Authentication methods:                                                         
                                                                                
 • 🔒 implicit                                                                  
 • 🔒 secret-key                                                                
 • 🔒 sts-token                                                                 
 • 🔒 iam-role                                                                  
 • 🔒 session-token                                                             
 • 🔒 federation-token                                                          
                                                                                
Allows users to access an EKS cluster as a standard Kubernetes cluster resource.
When used by Stack Components, they are provided a pre-authenticated            
python-kubernetes client instance.                                              
                                                                                
The configured credentials must have at least the following AWS IAM permissions 
associated with the ARNs of EKS clusters that the connector will be allowed to  
access (e.g. arn:aws:eks:{region}:{account}:cluster/* represents all the EKS    
clusters available in the target AWS region).                                   
                                                                                
 • eks:ListClusters                                                             
 • eks:DescribeCluster                                                          
                                                                                
In addition to the above permissions, if the credentials are not associated with
the same IAM user or role that created the EKS cluster, the IAM principal must  
be manually added to the EKS cluster's aws-auth ConfigMap, otherwise the        
Kubernetes client will not be allowed to access the cluster's resources. This   
makes it more challenging to use the AWS Implicit and AWS Federation Token      
authentication methods for this resource. For more information, see this        
documentation.                                                                  
                                                                                
If set, the resource name must identify an EKS cluster using one of the         
following formats:                                                              
                                                                                
 • EKS cluster name (canonical resource name): {cluster-name}                   
 • EKS cluster ARN: arn:aws:eks:{region}:{account}:cluster/{cluster-name}       
                                                                                
EKS cluster names are region scoped. The connector can only be used to access   
EKS clusters in the AWS region that it is configured to use.                    
                                                                                
────────────────────────────────────────────────────────────────────────────────
```

```sh
$ zenml service-connector describe-type aws --auth-method secret-key
╔══════════════════════════════════════════════════════════════════════════════╗
║                 🔒 AWS Secret Key (auth method: secret-key)                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                                                                
Supports issuing temporary credentials: False                                   
                                                                                
Long-lived AWS credentials consisting of an AWS access key ID and secret access 
key associated with an AWS IAM user or AWS account root user (not recommended). 
                                                                                
This method is preferred during development and testing due to its simplicity   
and ease of use. It is not recommended as a direct authentication method for    
production use cases because the clients have direct access to long-lived       
credentials and are granted the full set of permissions of the IAM user or AWS  
account root user associated with the credentials. For production, it is        
recommended to use the AWS IAM Role, AWS Session Token or AWS Federation Token  
authentication method instead.                                                  
                                                                                
An AWS region is required and the connector may only be used to access AWS      
resources in the specified region.                                              
                                                                                
If you already have the local AWS CLI set up with these credentials, they will  
be automatically picked up when auto-configuration is used.                     
                                                                                
Attributes:                                                                     
                                                                                
 • aws_access_key_id {string, secret, required}: AWS Access Key ID              
 • aws_secret_access_key {string, secret, required}: AWS Secret Access Key      
 • region {string, required}: AWS Region                                        
 • endpoint_url {string, optional}: AWS Endpoint URL                            
                                                                                
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

<details>

<summary>Exploring the documentation embedded into Service Connector Types</summary>

A lot more is hidden behind a Service Connector Type than a name and a simple list of resource types. Before using a Service Connector Type to configure a Service Connector, you probably need to understand what it is, what it can offer and what are the supported authentication methods and their requirements. All this can be accessed on-site directly through the CLI. Some examples are included here.

Showing information about the `aws` Service Connector Type:

```
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
                                                                                
The ZenML AWS Service Connector facilitates the authentication and access to    
managed AWS services and resources. These encompass a range of resources,       
including S3 buckets, ECR repositories, and EKS clusters. The connector provides
support for various authentication methods, including explicit long-lived AWS   
secret keys, IAM roles, short-lived STS tokens and implicit authentication.     
                                                                                
To ensure heightened security measures, this connector also enables the         
generation of temporary STS security tokens that are scoped down to the minimum 
permissions necessary for accessing the intended resource. Furthermore, it      
includes automatic configuration and detection of credentials locally configured
through the AWS CLI.                                                            
                                                                                
This connector serves as a general means of accessing any AWS service by issuing
pre-authenticated boto3 sessions to clients. Additionally, the connector can    
handle specialized authentication for S3, Docker and Kubernetes Python clients. 
It also allows for the configuration of local Docker and Kubernetes CLIs.       
                                                                                
The AWS Service Connector is part of the AWS ZenML integration. You can either  
install the entire integration or use a pypi extra to install it independently  
of the integration:                                                             
                                                                                
 • pip install zenml[connectors-aws] installs only prerequisites for the AWS    
   Service Connector Type                                                       
 • zenml integration install aws installs the entire AWS ZenML integration      
                                                                                
It is not required to install and set up the AWS CLI on your local machine to   
use the AWS Service Connector to link Stack Components to AWS resources and     
services. However, it is recommended to do so if you are looking for a quick    
setup that includes using the auto-configuration Service Connector features.    
                                                                                
────────────────────────────────────────────────────────────────────────────────
```

Fetching details about the `s3-bucket` resource type:

```
$ zenml service-connector describe-type aws --resource-type s3-bucket
╔══════════════════════════════════════════════════════════════════════════════╗
║                 📦 AWS S3 bucket (resource type: s3-bucket)                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                                                                
Authentication methods: implicit, secret-key, sts-token, iam-role,              
session-token, federation-token                                                 
                                                                                
Supports resource instances: True                                               
                                                                                
Authentication methods:                                                         
                                                                                
 • 🔒 implicit                                                                  
 • 🔒 secret-key                                                                
 • 🔒 sts-token                                                                 
 • 🔒 iam-role                                                                  
 • 🔒 session-token                                                             
 • 🔒 federation-token                                                          
                                                                                
Allows users to connect to S3 buckets. When used by Stack Components, they are  
provided a pre-configured boto3 S3 client instance.                             
                                                                                
The configured credentials must have at least the following AWS IAM permissions 
associated with the ARNs of S3 buckets that the connector will be allowed to    
access (e.g. arn:aws:s3:::* and arn:aws:s3:::*/* represent all the available S3 
buckets).                                                                       
                                                                                
 • s3:ListBucket                                                                
 • s3:GetObject                                                                 
 • s3:PutObject                                                                 
 • s3:DeleteObject                                                              
 • s3:ListAllMyBuckets                                                          
                                                                                
If set, the resource name must identify an S3 bucket using one of the following 
formats:                                                                        
                                                                                
 • S3 bucket URI (canonical resource name): s3://{bucket-name}                  
 • S3 bucket ARN: arn:aws:s3:::{bucket-name}                                    
 • S3 bucket name: {bucket-name}                                                
                                                                                
────────────────────────────────────────────────────────────────────────────────
```

Displaying information about the `session-token` authentication method:

```
$ zenml service-connector describe-type aws --auth-method session-token
╔══════════════════════════════════════════════════════════════════════════════╗
║              🔒 AWS Session Token (auth method: session-token)               ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                                                                
Supports issuing temporary credentials: True                                    
                                                                                
Generates temporary session STS tokens for IAM users. The connector needs to be 
configured with an AWS secret key associated with an IAM user or AWS account    
root user (not recommended). The connector will generate temporary STS tokens   
upon request by calling the GetSessionToken STS API.                            
                                                                                
These STS tokens have an expiration period longer that those issued through the 
AWS IAM Role authentication method and are more suitable for long-running       
processes that cannot automatically re-generate credentials upon expiration.    
                                                                                
An AWS region is required and the connector may only be used to access AWS      
resources in the specified region.                                              
                                                                                
The default expiration period for generated STS tokens is 12 hours with a       
minimum of 15 minutes and a maximum of 36 hours. Temporary credentials obtained 
by using the AWS account root user credentials (not recommended) have a maximum 
duration of 1 hour.                                                             
                                                                                
As a precaution, when long-lived credentials (i.e. AWS Secret Keys) are detected
on your environment by the Service Connector during auto-configuration, this    
authentication method is automatically chosen instead of the AWS Secret Key     
authentication method alternative.                                              
                                                                                
Generated STS tokens inherit the full set of permissions of the IAM user or AWS 
account root user that is calling the GetSessionToken API. Depending on your    
security needs, this may not be suitable for production use, as it can lead to  
accidental privilege escalation. Instead, it is recommended to use the AWS      
Federation Token or AWS IAM Role authentication methods to restrict the         
permissions of the generated STS tokens.                                        
                                                                                
For more information on session tokens and the GetSessionToken AWS API, see: the
official AWS documentation on the subject.                                      
                                                                                
Attributes:                                                                     
                                                                                
 • aws_access_key_id {string, secret, required}: AWS Access Key ID              
 • aws_secret_access_key {string, secret, required}: AWS Secret Access Key      
 • region {string, required}: AWS Region                                        
 • endpoint_url {string, optional}: AWS Endpoint URL                            
                                                                                
────────────────────────────────────────────────────────────────────────────────
```

</details>

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
* they support multiple authentication methods. Some of these allow clients direct access to long-lived, broad-access credentials and are only recommended for local development use. Others support distributing temporary API tokens automatically generated from long-lived credentials, which are safer for production use-cases, but may be more difficult to set up. A few authentication methods even support down-scoping the permissions of temporary API tokens so that they only allow access to the target resource and restrict access to everything else. This is covered at length [in the section on best practices for authentication methods](service-connectors-guide.md).&#x20;
* there is flexibility regarding the range of resources that a single cloud provider Service Connector instance configured with a single set of credentials can be scoped to access:
  * a _multi-type Service Connector_ instance can access any type of resources from the range of supported Resource Types&#x20;
  * a _multi-instance Service Connector_ instance can access multiple resources of the same type
  * a _single-instance Service Connector_ instance is scoped to access a single resource

The following output shows three different Service Connectors configured from the same GCP Service Connector Type using three different scopes but with the same credentials:

* a multi-type GCP Service Connector that allows access to every possible resource accessible with the configured credentials
* a multi-instance GCS Service Connector that allows access to multiple GCS buckets
* a single-instance GCS Service Connector that only permits access to one GCS bucket

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

* Service Connector registration, update, and discovery (i.e. the `zenml service-connector register`, `zenml service-connector update`, `zenml service-connector list` and `zenml service-connector describe` CLI commands).
* Service Connector verification: checking whether its configuration and credentials are valid and can be actively used to access the remote resources (i.e. the `zenml service-connector verify` CLI commands).
* Listing the resources that can be accessed through a Service Connector (i.e. the `zenml service-connector verify` and `zenml service-connector list-resources` CLI commands)
* Connecting a Stack Component to a remote resource via a Service Connector&#x20;

The following operations are only possible with Service Connector Types that are locally available (with some notable exceptions covered in the information box that follows):

* Service Connector auto-configuration and discovery of credentials stored by a local client, CLI, or SDK (e.g. aws or kubectl).
* Using the configuration and credentials managed by a Service Connector to configure a local client, CLI, or SDK (e.g. docker or kubectl).
* Running pipelines with a Stack Component that is connected to a remote resource through a Service Connector&#x20;

{% hint style="info" %}
One interesting and useful byproduct of the way cloud provider Service Connectors are designed is the fact that you don't need to have the cloud provider Service Connector Type available client-side to be able to access some of its resources. Take the following situation for example:

* the GCP Service Connector Type can provide access to GKE Kubernetes clusters and GCR Docker container registries.
* however, you don't need the GCP Service Connector Type or any GCP libraries to be installed on the ZenML clients to connect to and use those Kubernetes clusters or Docker registries in your ML pipelines.
* the Kubernetes Service Connector Type is enough to access any Kubernetes cluster, regardless of its provenance (AWS, GCP, etc.)
* the Docker Service Connector Type is enough to access any Docker container registry, regardless of its provenance (AWS, GCP, etc.)
{% endhint %}

## Register Service Connectors

When you reach this section, you probably already made up your mind about the type of infrastructure or cloud provider that you want to use to run your ZenML pipelines after reading through [the Service Connector Types section](service-connectors-guide.md#explore-service-connector-types), and you probably carefully weighed your [choices of authentication methods and best security practices](best-security-practices.md). Either that or you simply want to quickly try out a Service Connector to [connect one of the ZenML Stack components to an external resource](service-connectors-guide.md#connect-stack-components-to-resources).

If you are looking for a quick, assisted tour, we recommend using the interactive CLI mode to configure Service Connectors, especially if this is your first time doing it:

```
zenml service-connector register -i
```

Regardless of how you came here, you should already have some idea of the following:

* the type of resources that you want to connect ZenML to. This may be a Kubernetes cluster, a Docker container registry or an object storage service like AWS S3 or GCS.
* the Service Connector implementation (i.e. Service Connector Type) that you want to use to connect to those resources. This could be one of the cloud provider Service Connector Types like AWS and GCP that provide access to a broader range of services, or one of the basic Service Connector Types like Kubernetes or Docker that only target a specific resource.
* the credentials and authentication method that you want to use

Other questions that should be answered in this section:

* are you just looking to connect a ZenML Stack Component to a single resource? or would you rather configure a wide-access ZenML Service Connector that gives ZenML and all its users access to a broader range of resource types and resource instances with a single set of credentials issued by your cloud provider?
* have you already provisioned all the authentication prerequisites (e.g. service accounts, roles, permissions) and prepared the credentials you will need to configure the Service Connector? If you already have one of the cloud provider CLIs configured with credentials on your local host, you can easily use the Service Connector auto-configuration capabilities to get faster where you need to go.

For help answering these questions, you can also use the interactive CLI mode to register Service Connectors and/or consult the documentation dedicated to each individual Service Connector Type.&#x20;

### Auto-configuration

Many Service Connector Types support using auto-configuration to discover and extract configuration information and credentials directly from your local environment. This assumes that you have already installed and set up the local CLI or SDK associated with the type of resource or cloud provider that you're willing to use. The Service Connector auto-configuration feature relies on these CLIs being configured with valid credentials to work properly. Some examples are listed here, but you should consult the documentation section for the Service Connector Type of choice to find out if and how auto-configuration is supported:

* AWS uses the [`aws configure` CLI command](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)&#x20;
* GCP offers [the `gcloud auth application-default login` CLI command](https://cloud.google.com/docs/authentication/provide-credentials-adc#how\_to\_provide\_credentials\_to\_adc)
* Azure provides [the `az login` CLI command](https://learn.microsoft.com/en-us/cli/azure/authenticate-azure-cli)

<details>

<summary>Or simply try it and find out</summary>

```
$ zenml service-connector register kubernetes-auto --type kubernetes --auto-configure
Successfully registered service connector `kubernetes-auto` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME  │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼─────────────────┼────────────────┼───────────────────────┼────────────────┨
┃ ca4b6a61-bcf3-4d5f-b241-d7e77e26e877 │ kubernetes-auto │ 🌀 kubernetes  │ 🌀 kubernetes-cluster │ 35.185.95.223  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛

$ AWS_PROFILE=zenml zenml service-connector register aws-auto --type aws --auto-configure
⠼ Registering service connector 'aws-auto'...
Successfully registered service connector `aws-auto` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────────────┼────────────────┨
┃ a7d35e28-8b37-4cab-a7a9-f4e3f53ff1a9 │ aws-auto       │ 🔶 aws         │ 🔶 aws-generic        │ 🤷 none listed ┃
┃                                      │                │                │ 📦 s3-bucket          │                ┃
┃                                      │                │                │ 🌀 kubernetes-cluster │                ┃
┃                                      │                │                │ 🐳 docker-registry    │                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛

$ zenml service-connector register gcp-auto --type gcp --auto-configure
Successfully registered service connector `gcp-auto` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────────────┼────────────────┨
┃ 73d7c155-e077-4e76-9983-9673de152849 │ gcp-auto       │ 🔵 gcp         │ 🔵 gcp-generic        │ 🤷 none listed ┃
┃                                      │                │                │ 📦 gcs-bucket         │                ┃
┃                                      │                │                │ 🌀 kubernetes-cluster │                ┃
┃                                      │                │                │ 🐳 docker-registry    │                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛
```

</details>

### Scopes: multi-type, multi-instance, and single-instance

These terms are briefly explained in the [Terminology](service-connectors-guide.md#terminology) section: you can register a Service Connector that grants access to multiple types of resources, to multiple instances of the same Resource Type, or to a single resource.

Service Connectors created from basic Service Connector Types like Kubernetes and Docker are single-resource by default, while Service Connectors used to connect to managed cloud resources like AWS and GCP can take all three forms.

<details>

<summary>Example of registering Service Connectors with different scopes</summary>

The following example shows registering three different Service Connectors configured from the same AWS Service Connector Type using three different scopes but with the same credentials:

* a multi-type AWS Service Connector that allows access to every possible resource accessible with the configured credentials
* a multi-instance AWS Service Connector that allows access to multiple S3 buckets
* a single-instance AWS Service Connector that only permits access to one S3 bucket

```
$ AWS_PROFILE=zenml zenml service-connector register aws-multi-type --type aws --auto-configure
⠼ Registering service connector 'aws-multi-type'...
Successfully registered service connector `aws-multi-type` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────────────┼────────────────┨
┃ 4a550c82-aa64-4a48-9c7f-d5e127d77a44 │ aws-multi-type │ 🔶 aws         │ 🔶 aws-generic        │ 🤷 none listed ┃
┃                                      │                │                │ 📦 s3-bucket          │                ┃
┃                                      │                │                │ 🌀 kubernetes-cluster │                ┃
┃                                      │                │                │ 🐳 docker-registry    │                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛

$ AWS_PROFILE=zenml zenml service-connector register aws-multi-instance --type aws --auto-configure --resource-type s3-bucket
⠏ Registering service connector 'aws-multi-instance'...
Successfully registered service connector `aws-multi-instance` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME     │ CONNECTOR TYPE │ RESOURCE TYPE │ RESOURCE NAMES                        ┃
┠──────────────────────────────────────┼────────────────────┼────────────────┼───────────────┼───────────────────────────────────────┨
┃ 66c0922d-db84-4e2c-9044-c13ce1611613 │ aws-multi-instance │ 🔶 aws         │ 📦 s3-bucket  │ s3://public-flavor-logos              ┃
┃                                      │                    │                │               │ s3://zenfiles                         ┃
┃                                      │                    │                │               │ s3://zenml-demos                      ┃
┃                                      │                    │                │               │ s3://zenml-generative-chat            ┃
┃                                      │                    │                │               │ s3://zenml-public-datasets            ┃
┃                                      │                    │                │               │ s3://zenml-public-swagger-spec        ┃
┃                                      │                    │                │               │ s3://zenml-sandbox-infra              ┃
┃                                      │                    │                │               │ s3://zenml-terraform-ci               ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

$ AWS_PROFILE=zenml zenml service-connector register aws-single-instance --type aws --auto-configure --resource-type s3-bucket --resource-id s3://zenfiles
⠸ Registering service connector 'aws-single-instance'...
Successfully registered service connector `aws-single-instance` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME      │ CONNECTOR TYPE │ RESOURCE TYPE │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼─────────────────────┼────────────────┼───────────────┼────────────────┨
┃ 65c82e59-cba0-4a01-b8f6-d75e8a1d0f55 │ aws-single-instance │ 🔶 aws         │ 📦 s3-bucket  │ s3://zenfiles  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛
```

</details>

The following might help understand the difference between scopes:

* the difference between a multi-instance and a multi-type Service Connector is that the Resource Type scope is locked to a particular value during configuration for the multi-instance Service Connector
* similarly, the difference between a multi-instance and a multi-type Service Connector is that the Resource Name (Resource ID) scope is locked to a particular value during configuration for the single-instance Service Connector

### Service Connector Verification

When registering Service Connectors, the authentication configuration and credentials are automatically verified to ensure that they can indeed be used to gain access to the target resources:

* for multi-type Service Connectors, this verification only means checking that the configured credentials can be used to authenticate successfully to the remote service, without checking permissions for individual resources and Resource Types.
* for multi-instance Service Connectors, this verification step means listing all resources that the credentials have permission to access in addition to validating that the credentials can be used to authenticate to the target service or platform.
* for single-instance Service Connectors, the verification step simply checks that the configured credentials have permission to access the target resource.

The verification can also be performed later on an already registered Service Connector. Furthermore, for multi-type and multi-instance Service Connectors, the verification operation can be scoped to a Resource Type and a Resource Name.

<details>

<summary>Example of on-demand Service Connector verification</summary>

The following shows how a multi-type a multi-instance and a single-instance Service Connector can be verified with multiple scopes after registration.

First, listing the Service Connectors will clarify which scopes they are configured with:

```
$ zenml service-connector list
┏━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━┓
┃ ACTIVE │ NAME                   │ ID                                   │ TYPE          │ RESOURCE TYPES        │ RESOURCE NAME           │ SHARED │ OWNER   │ EXPIRES IN │ LABELS ┃
┠────────┼────────────────────────┼──────────────────────────────────────┼───────────────┼───────────────────────┼─────────────────────────┼────────┼─────────┼────────────┼────────┨
┃        │ aws-multi-type         │ 4a550c82-aa64-4a48-9c7f-d5e127d77a44 │ 🔶 aws        │ 🔶 aws-generic        │ <multiple>              │ ➖     │ default │            │        ┃
┃        │                        │                                      │               │ 📦 s3-bucket          │                         │        │         │            │        ┃
┃        │                        │                                      │               │ 🌀 kubernetes-cluster │                         │        │         │            │        ┃
┃        │                        │                                      │               │ 🐳 docker-registry    │                         │        │         │            │        ┃
┠────────┼────────────────────────┼──────────────────────────────────────┼───────────────┼───────────────────────┼─────────────────────────┼────────┼─────────┼────────────┼────────┨
┃        │ aws-multi-instance     │ 66c0922d-db84-4e2c-9044-c13ce1611613 │ 🔶 aws        │ 📦 s3-bucket          │ <multiple>              │ ➖     │ default │            │        ┃
┠────────┼────────────────────────┼──────────────────────────────────────┼───────────────┼───────────────────────┼─────────────────────────┼────────┼─────────┼────────────┼────────┨
┃        │ aws-single-instance    │ 65c82e59-cba0-4a01-b8f6-d75e8a1d0f55 │ 🔶 aws        │ 📦 s3-bucket          │ s3://zenfiles           │ ➖     │ default │            │        ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━┛

```

Verifying the multi-type Service Connector does not display any actual resources by default, but will still verify that the credentials are globally valid. This is like asking "are these credentials valid and can they be used to authenticate to AWS ?":

```
$ zenml service-connector verify aws-multi-type
Service connector 'aws-multi-type' is correctly configured with valid credentials and has access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────────────┼────────────────┨
┃ 4a550c82-aa64-4a48-9c7f-d5e127d77a44 │ aws-multi-type │ 🔶 aws         │ 🔶 aws-generic        │ 🤷 none listed ┃
┃                                      │                │                │ 📦 s3-bucket          │                ┃
┃                                      │                │                │ 🌀 kubernetes-cluster │                ┃
┃                                      │                │                │ 🐳 docker-registry    │                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛
The '4a550c82-aa64-4a48-9c7f-d5e127d77a44' service connector is a multi-type connector - i.e. configured to provide access to
multiple types of resources. A list of resources is not included for multi-type connectors. You can use the `--resource-type`
argument to show a full list of resources it can access for a particular resource type.
```

As suggested, we can scope the verification down to a particular Resource Type or all the way down to a Resource Name. This is the equivalent of asking "are these credentials valid and which S3 buckets are they authorized to access ?" and "can these credentials be used to access this particular Kubernetes cluster in AWS ?":

```
$ zenml service-connector verify aws-multi-type --resource-type s3-bucket
Service connector 'aws-multi-type' is correctly configured with valid credentials and has access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE │ RESOURCE NAMES                        ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────┼───────────────────────────────────────┨
┃ 4a550c82-aa64-4a48-9c7f-d5e127d77a44 │ aws-multi-type │ 🔶 aws         │ 📦 s3-bucket  │ s3://public-flavor-logos              ┃
┃                                      │                │                │               │ s3://zenfiles                         ┃
┃                                      │                │                │               │ s3://zenml-demos                      ┃
┃                                      │                │                │               │ s3://zenml-generative-chat            ┃
┃                                      │                │                │               │ s3://zenml-public-datasets            ┃
┃                                      │                │                │               │ s3://zenml-public-swagger-spec        ┃
┃                                      │                │                │               │ s3://zenml-sandbox-infra              ┃
┃                                      │                │                │               │ s3://zenml-terraform-ci               ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

$ zenml service-connector verify aws-multi-type --resource-type kubernetes-cluster
Service connector 'aws-multi-type' is correctly configured with valid credentials and has access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES   ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────────────┼──────────────────┨
┃ 4a550c82-aa64-4a48-9c7f-d5e127d77a44 │ aws-multi-type │ 🔶 aws         │ 🌀 kubernetes-cluster │ zenhacks-cluster ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━┛

```

Verifying the multi-instance Service Connector already displays all the resources that it can access. We can also scope the verification to a single resource:

```
$ zenml service-connector verify aws-multi-instance
Service connector 'aws-multi-instance' is correctly configured with valid credentials and has access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME     │ CONNECTOR TYPE │ RESOURCE TYPE │ RESOURCE NAMES                        ┃
┠──────────────────────────────────────┼────────────────────┼────────────────┼───────────────┼───────────────────────────────────────┨
┃ 66c0922d-db84-4e2c-9044-c13ce1611613 │ aws-multi-instance │ 🔶 aws         │ 📦 s3-bucket  │ s3://public-flavor-logos              ┃
┃                                      │                    │                │               │ s3://zenml-demos                      ┃
┃                                      │                    │                │               │ s3://zenml-generative-chat            ┃
┃                                      │                    │                │               │ s3://zenml-public-datasets            ┃
┃                                      │                    │                │               │ s3://zenml-public-swagger-spec        ┃
┃                                      │                    │                │               │ s3://zenml-sandbox-infra              ┃
┃                                      │                    │                │               │ s3://zenml-terraform-ci               ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

$ zenml service-connector verify aws-multi-instance --resource-id s3://zenml-demos
Service connector 'aws-multi-instance' is correctly configured with valid credentials and has access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME     │ CONNECTOR TYPE │ RESOURCE TYPE │ RESOURCE NAMES   ┃
┠──────────────────────────────────────┼────────────────────┼────────────────┼───────────────┼──────────────────┨
┃ 66c0922d-db84-4e2c-9044-c13ce1611613 │ aws-multi-instance │ 🔶 aws         │ 📦 s3-bucket  │ s3://zenml-demos ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━┛
```

Finally, verifying the single-instance Service Connector is straight-forward and requires no further explanation:

```
$ zenml service-connector verify aws-single-instance 
Service connector 'aws-single-instance' is correctly configured with valid credentials and has access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME      │ CONNECTOR TYPE │ RESOURCE TYPE │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼─────────────────────┼────────────────┼───────────────┼────────────────┨
┃ 65c82e59-cba0-4a01-b8f6-d75e8a1d0f55 │ aws-single-instance │ 🔶 aws         │ 📦 s3-bucket  │ s3://zenfiles  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛
```

</details>

## Configure local clients

Yet another neat feature built into some Service Container Types that is the opposite of [Service Connector auto-configuration](service-connectors-guide.md#auto-configuration) is the ability to configure local CLI and SDK utilities installed on your host, like the Docker or Kubernetes CLI (`kubectl`) with credentials issued by a compatible Service Connector.

You may need to exercise this feature to get direct CLI access to a remote service in order to manually manage some configurations or resources, to debug some workloads or to simply verify that the Service Connector credentials are actually working.

{% hint style="warning" %}
When configuring local CLI utilities with credentials extracted from Service Connectors, keep in mind that most Service Connectors, particularly those used with cloud platforms, exercise the security best practice of issuing _temporary credentials such as API tokens._ The implication is that your local CLI will only be allowed access to the remote service for a short time before those credentials expire, then you need to fetch another set of credentials from the Service Connector.
{% endhint %}

<details>

<summary>Examples of local CLI configuration</summary>

The following examples show how the local Kubernetes `kubectl` CLI can be configured with credentials issued by a Service Connector and then used to access a Kubernetes cluster directly:

```
$ zenml service-connector list-resources --resource-type kubernetes-cluster
The following 'kubernetes-cluster' resources can be accessed by service connectors configured in your workspace:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME       │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES                                                                      ┃
┠──────────────────────────────────────┼──────────────────────┼────────────────┼───────────────────────┼─────────────────────────────────────────────────────────────────────────────────────┨
┃ 9d953320-3560-4a78-817c-926a3898064d │ gcp-user-multi       │ 🔵 gcp         │ 🌀 kubernetes-cluster │ zenml-test-cluster                                                                  ┃
┠──────────────────────────────────────┼──────────────────────┼────────────────┼───────────────────────┼─────────────────────────────────────────────────────────────────────────────────────┨
┃ 4a550c82-aa64-4a48-9c7f-d5e127d77a44 │ aws-multi-type       │ 🔶 aws         │ 🌀 kubernetes-cluster │ zenhacks-cluster                                                                    ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

$ zenml service-connector login gcp-user-multi --resource-type kubernetes-cluster --resource-id zenml-test-cluster
⠇ Attempting to configure local client using service connector 'gcp-user-multi'...
Updated local kubeconfig with the cluster details. The current kubectl context was set to 'gke_zenml-core_zenml-test-cluster'.
The 'gcp-user-multi' Kubernetes Service Connector connector was used to successfully configure the local Kubernetes cluster client/SDK.

$ kubectl cluster-info
Kubernetes control plane is running at https://35.185.95.223
GLBCDefaultBackend is running at https://35.185.95.223/api/v1/namespaces/kube-system/services/default-http-backend:http/proxy
KubeDNS is running at https://35.185.95.223/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy
Metrics-server is running at https://35.185.95.223/api/v1/namespaces/kube-system/services/https:metrics-server:/proxy

$ zenml service-connector login aws-multi-type --resource-type kubernetes-cluster --resource-id zenhacks-cluster
⠏ Attempting to configure local client using service connector 'aws-multi-type'...
Updated local kubeconfig with the cluster details. The current kubectl context was set to 'arn:aws:eks:us-east-1:715803424590:cluster/zenhacks-cluster'.
The 'aws-multi-type' Kubernetes Service Connector connector was used to successfully configure the local Kubernetes cluster client/SDK.

$ kubectl cluster-info
Kubernetes control plane is running at https://A5F8F4142FB12DDCDE9F21F6E9B07A18.gr7.us-east-1.eks.amazonaws.com
CoreDNS is running at https://A5F8F4142FB12DDCDE9F21F6E9B07A18.gr7.us-east-1.eks.amazonaws.com/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy
```

The same is possible with the local  Docker client:

```
$ zenml service-connector verify aws-session-token --resource-type docker-registry
Service connector 'aws-session-token' is correctly configured with valid credentials and has access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME    │ CONNECTOR TYPE │ RESOURCE TYPE      │ RESOURCE NAMES                               ┃
┠──────────────────────────────────────┼───────────────────┼────────────────┼────────────────────┼──────────────────────────────────────────────┨
┃ 3ae3e595-5cbc-446e-be64-e54e854e0e3f │ aws-session-token │ 🔶 aws         │ 🐳 docker-registry │ 715803424590.dkr.ecr.us-east-1.amazonaws.com ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

$ zenml service-connector login aws-session-token --resource-type docker-registry 
⠏ Attempting to configure local client using service connector 'aws-session-token'...
WARNING! Your password will be stored unencrypted in /home/stefan/.docker/config.json.
Configure a credential helper to remove this warning. See
https://docs.docker.com/engine/reference/commandline/login/#credentials-store

The 'aws-session-token' Docker Service Connector connector was used to successfully configure the local Docker/OCI container registry client/SDK.

$ docker pull 715803424590.dkr.ecr.us-east-1.amazonaws.com/zenml-server
Using default tag: latest
latest: Pulling from zenml-server
e9995326b091: Pull complete 
f3d7f077cdde: Pull complete 
0db71afa16f3: Pull complete 
6f0b5905c60c: Pull complete 
9d2154d50fd1: Pull complete 
d072bba1f611: Pull complete 
20e776588361: Pull complete 
3ce69736a885: Pull complete 
c9c0554c8e6a: Pull complete 
bacdcd847a66: Pull complete 
482033770844: Pull complete 
Digest: sha256:bf2cc3895e70dfa1ee1cd90bbfa599fa4cd8df837e27184bac1ce1cc239ecd3f
Status: Downloaded newer image for 715803424590.dkr.ecr.us-east-1.amazonaws.com/zenml-server:latest
715803424590.dkr.ecr.us-east-1.amazonaws.com/zenml-server:latest
```

</details>

## Discover available resources

One of the questions that you may have as a ZenML user looking to register and connect a Stack Component to an external resource is "what resources do I even have access to ?". Sure, you can browse through all the registered Service connectors and manually verify each one to find a particular resource that you are looking for, but this is counterproductive.

A better way is to ask ZenML directly questions such as:

* what are the Kubernetes clusters that I can get access to through Service Connectors?
* can I access this particular S3 bucket through one of the Service Connectors? Which one?

The `zenml service-connector list-resources` CLI command can be used exactly for this purpose.

<details>

<summary>Resource discovery examples</summary>

It is possible to show globally all the various resources that can be accessed through all available Service Connectors, and all Service Connectors that are in an error state. This operation is expensive and may take some time to complete, depending on the number of Service Connectors involved:

```
$ zenml service-connector list-resources
The following resources can be accessed by service connectors configured in your workspace:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME         │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES                                                                    ┃
┠──────────────────────────────────────┼────────────────────────┼────────────────┼───────────────────────┼───────────────────────────────────────────────────────────────────────────────────┨
┃ 9d953320-3560-4a78-817c-926a3898064d │ gcp-user-multi         │ 🔵 gcp         │ 🔵 gcp-generic        │ 🤷 none listed                                                                    ┃
┃                                      │                        │                │ 📦 gcs-bucket         │                                                                                   ┃
┃                                      │                        │                │ 🌀 kubernetes-cluster │                                                                                   ┃
┃                                      │                        │                │ 🐳 docker-registry    │                                                                                   ┃
┠──────────────────────────────────────┼────────────────────────┼────────────────┼───────────────────────┼───────────────────────────────────────────────────────────────────────────────────┨
┃ b485626e-7fee-4525-90da-5b26c72331eb │ dockerhub              │ 🐳 docker      │ 🐳 docker-registry    │ docker.io                                                                         ┃
┠──────────────────────────────────────┼────────────────────────┼────────────────┼───────────────────────┼───────────────────────────────────────────────────────────────────────────────────┨
┃ 4315e8eb-fcbd-4938-a4d7-a9218ab372a1 │ kube-auto              │ 🌀 kubernetes  │ 🌀 kubernetes-cluster │ 💥 error: connector authorization failure: failed to verify Kubernetes cluster    ┃
┃                                      │                        │                │                       │ access: (401)                                                                     ┃
┃                                      │                        │                │                       │ Reason: Unauthorized                                                              ┃
┠──────────────────────────────────────┼────────────────────────┼────────────────┼───────────────────────┼───────────────────────────────────────────────────────────────────────────────────┨
┃ 4a550c82-aa64-4a48-9c7f-d5e127d77a44 │ aws-multi-type         │ 🔶 aws         │ 🔶 aws-generic        │ 🤷 none listed                                                                    ┃
┃                                      │                        │                │ 📦 s3-bucket          │                                                                                   ┃
┃                                      │                        │                │ 🌀 kubernetes-cluster │                                                                                   ┃
┃                                      │                        │                │ 🐳 docker-registry    │                                                                                   ┃
┠──────────────────────────────────────┼────────────────────────┼────────────────┼───────────────────────┼───────────────────────────────────────────────────────────────────────────────────┨
┃ 66c0922d-db84-4e2c-9044-c13ce1611613 │ aws-multi-instance     │ 🔶 aws         │ 📦 s3-bucket          │ s3://public-flavor-logos                                                          ┃
┃                                      │                        │                │                       │ s3://zenfiles                                                                     ┃
┃                                      │                        │                │                       │ s3://zenml-demos                                                                  ┃
┃                                      │                        │                │                       │ s3://zenml-generative-chat                                                        ┃
┃                                      │                        │                │                       │ s3://zenml-public-datasets                                                        ┃
┃                                      │                        │                │                       │ s3://zenml-public-swagger-spec                                                    ┃
┃                                      │                        │                │                       │ s3://zenml-sandbox-infra                                                          ┃
┃                                      │                        │                │                       │ s3://zenml-terraform-ci                                                           ┃
┠──────────────────────────────────────┼────────────────────────┼────────────────┼───────────────────────┼───────────────────────────────────────────────────────────────────────────────────┨
┃ 65c82e59-cba0-4a01-b8f6-d75e8a1d0f55 │ aws-single-instance    │ 🔶 aws         │ 📦 s3-bucket          │ s3://zenfiles                                                                     ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
2 connectors in your results are multi-type connectors - i.e. are configured to provide access to multiple types of resources. A list of resources is not included for these connectors. Use
the '--resource-type' option to filter by resource type and display the resources that can be accessed by these connectors.

```

More interesting is to scope the search to a particular Resource Type. This also yields more results, especially if you have many multi-type Service Connectors configured:

```
$ zenml service-connector list-resources --resource-type kubernetes-cluster
The following 'kubernetes-cluster' resources can be accessed by service connectors configured in your workspace:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME       │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES                                                                      ┃
┠──────────────────────────────────────┼──────────────────────┼────────────────┼───────────────────────┼─────────────────────────────────────────────────────────────────────────────────────┨
┃ 9d953320-3560-4a78-817c-926a3898064d │ gcp-user-multi       │ 🔵 gcp         │ 🌀 kubernetes-cluster │ zenml-test-cluster                                                                  ┃
┠──────────────────────────────────────┼──────────────────────┼────────────────┼───────────────────────┼─────────────────────────────────────────────────────────────────────────────────────┨
┃ 4315e8eb-fcbd-4938-a4d7-a9218ab372a1 │ kube-auto            │ 🌀 kubernetes  │ 🌀 kubernetes-cluster │ 💥 error: connector authorization failure: failed to verify Kubernetes cluster      ┃
┃                                      │                      │                │                       │ access: (401)                                                                       ┃
┠──────────────────────────────────────┼──────────────────────┼────────────────┼───────────────────────┼─────────────────────────────────────────────────────────────────────────────────────┨
┃ 4a550c82-aa64-4a48-9c7f-d5e127d77a44 │ aws-multi-type       │ 🔶 aws         │ 🌀 kubernetes-cluster │ zenhacks-cluster                                                                    ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

Finally, you can as for a particular resource, if you know its Resource Name beforehand:

```
$ zenml service-connector list-resources --resource-type s3-bucket --resource-id zenfiles
The  's3-bucket' resource with name 'zenfiles' can be accessed by service connectors configured in your workspace:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME       │ CONNECTOR TYPE │ RESOURCE TYPE │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼──────────────────────┼────────────────┼───────────────┼────────────────┨
┃ 4a550c82-aa64-4a48-9c7f-d5e127d77a44 │ aws-multi-type       │ 🔶 aws         │ 📦 s3-bucket  │ s3://zenfiles  ┃
┠──────────────────────────────────────┼──────────────────────┼────────────────┼───────────────┼────────────────┨
┃ 66c0922d-db84-4e2c-9044-c13ce1611613 │ aws-multi-instance   │ 🔶 aws         │ 📦 s3-bucket  │ s3://zenfiles  ┃
┠──────────────────────────────────────┼──────────────────────┼────────────────┼───────────────┼────────────────┨
┃ 65c82e59-cba0-4a01-b8f6-d75e8a1d0f55 │ aws-single-instance  │ 🔶 aws         │ 📦 s3-bucket  │ s3://zenfiles  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛
```

</details>

## Connect Stack Components to resources

Service Connectors and the resources and services that they can authenticate to and grant access to are only useful because they are a means of providing Stack Components a better and easier way of accessing external resources.

If you are looking for a quick, assisted tour, we recommend using the interactive CLI mode to connect a Stack Component to a compatible Service Connector, especially if this is your first time doing it, e.g.:

```
zenml artifact-store connect <component-name> -i
zenml orchestrator connect <component-name> -i
zenml container-registry connect <component-name> -i
```

WhichTo connect a Stack Component to an external resource or service, you first need to [register one or more Service Connectors](service-connectors-guide.md#register-service-connectors), or have someone else in your team with more infrastructure knowledge do it for you. If you already have that covered, you might want to ask ZenML "which resources/services am I even authorized to access with the available Service Connectors?". [The resource discovery feature](service-connectors-guide.md#end-to-end-examples) is designed exactly for this purpose. This last check is already included in the interactive ZenML CLI command used to connect a Stack Component to a remote resource.

{% hint style="info" %}
Not all Stack Components support being connected to an external resource or service via a Service Connector. Whether a Stack Component can use a Service Connector to connect to a remote resource or service or not is shown in the Stack Component flavor details:

```
$ zenml artifact-store flavor describe s3
Configuration class: S3ArtifactStoreConfig

Configuration for the S3 Artifact Store.

[...]

This flavor supports connecting to external resources with a Service
Connector. It requires a 's3-bucket' resource. You can get a list of
all available connectors and the compatible resources that they can
access by running:

'zenml service-connector list-resources --resource-type s3-bucket'
If no compatible Service Connectors are yet registered, you can can
register a new one by running:

'zenml service-connector register -i'

```
{% endhint %}

For Stack Components that do support Service Connectors, their flavor indicates the Resource Type and, optionally, Service Connector Type compatible with the Stack Component. This can be used to figure out which resources are available and which Service Connectors can grant access to them. In some cases it is even possible to figure out the exact Resource Name based on the attributes already configured in the Stack Component, which makes it possible to decide automatically which Resource Name to use:

```
$ zenml artifact-store register s3-zenfiles --flavor s3 --path=s3://zenfiles
Running with active workspace: 'default' (global)
Running with active stack: 'default' (global)
Successfully registered artifact_store `s3-zenfiles`.

$ zenml service-connector list-resources --resource-type s3-bucket --resource-id zenfiles
The  's3-bucket' resource with name 'zenfiles' can be accessed by service connectors configured in your workspace:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME       │ CONNECTOR TYPE │ RESOURCE TYPE │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼──────────────────────┼────────────────┼───────────────┼────────────────┨
┃ 4a550c82-aa64-4a48-9c7f-d5e127d77a44 │ aws-multi-type       │ 🔶 aws         │ 📦 s3-bucket  │ s3://zenfiles  ┃
┠──────────────────────────────────────┼──────────────────────┼────────────────┼───────────────┼────────────────┨
┃ 66c0922d-db84-4e2c-9044-c13ce1611613 │ aws-multi-instance   │ 🔶 aws         │ 📦 s3-bucket  │ s3://zenfiles  ┃
┠──────────────────────────────────────┼──────────────────────┼────────────────┼───────────────┼────────────────┨
┃ 65c82e59-cba0-4a01-b8f6-d75e8a1d0f55 │ aws-single-instance  │ 🔶 aws         │ 📦 s3-bucket  │ s3://zenfiles  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛

$ zenml artifact-store connect s3-zenfiles --connector aws-multi-type
Running with active workspace: 'default' (global)
Running with active stack: 'default' (global)
Successfully connected artifact store `s3-zenfiles` to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────┼────────────────┨
┃ 4a550c82-aa64-4a48-9c7f-d5e127d77a44 │ aws-multi-type │ 🔶 aws         │ 📦 s3-bucket  │ s3://zenfiles  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛
```

## End-to-end examples

To get an idea of what a complete end-to-end journey looks like, from registering Service Connector all the way to configuring Stacks and Stack Components and running pipelines that access remote resources through Service Connectors, take a look at the following full-fledged examples:

* [the AWS Service Connector end-to-end examples](aws-service-connector.md#end-to-end-examples)
* [the GCP Service Connector end-to-end examples](gcp-service-connector.md#end-to-end-examples)
