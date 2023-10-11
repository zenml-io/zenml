---
description: Understanding the workflow of using Service Connectors to access external resources with ZenML.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Connecting ZenML to resources

Everything around Service Connectors is expressed in terms of resources: a Kubernetes cluster is a resource, an S3 bucket is another resource. Different flavors of Stack Components need to use different resources to function: the Kubernetes and Tekton Orchestrators need access to a Kubernetes cluster, the S3 Artifact Store needs access to an S3 bucket. It is still possible to configure Stack Components like these to authenticate and connect directly to the target services that they need to interact with, but this is not simple to set up and it definitely isn't easily reproducible and maintainable.

Service Connectors simplify the configuration of ZenML Stack Components by taking over and mediating all concerns related to authentication and access to these resources. Once Service Connectors are set up, anyone can configure Stacks and Stack Components to easily access and utilize external resources in their ML pipelines without worrying about the specifics of authentication and access.

In this section, we walk through a typical workflow to explain conceptually the role that Service Connectors play in connecting ZenML to external resources.

## The typical Service Connectors workflow

The first step is _<mark style="color:purple;">finding out what types of resources you can connect ZenML to</mark>_. Maybe you have already planned out the infrastructure options for your MLOps platform and are looking to find out whether ZenML can accommodate them. Or perhaps you want to use a particular Stack Component flavor in your Stack and are wondering whether you can use a Service Connector to connect it to external resources.

This is where the _Service Connector Type_ concept comes in. For now, it is sufficient to think of Service Connector Types as a way to describe all the different kinds of resources that Service Connectors can mediate access to. This is an example of listing the available Service Connector Types with the ZenML CLI.

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

Let's say our cloud provider of choice is AWS and we're looking to hook up an S3 bucket to an S3 Artifact Store stack component and potentially other AWS resources in addition to that. Note that there is an AWS Service Connector type that we can use to gain access to several types of resources, one of which is an S3 bucket. We'll use that in the next steps.

<details>

<summary>Need more details? Find out how to access the wealth of information behind Service Connector Types</summary>

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

<details>

<summary>Want more details ? Find out exactly what happens during an auto-configuration</summary>

A quick glance into the Service Connector configuration that was automatically detected gives a better idea of what happened:

```
$ zenml service-connector describe aws-auto
Service connector 'aws-auto' of type 'aws' with id 'ffbec8d7-b931-46c3-bcc5-c6252c52ee5f' is owned by user 'default' and is 'private'.
                           'aws-auto' aws Service Connector Details                           
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                                   ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ ID               │ ffbec8d7-b931-46c3-bcc5-c6252c52ee5f                                    ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ NAME             │ aws-auto                                                                ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ TYPE             │ 🔶 aws                                                                  ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ AUTH METHOD      │ session-token                                                           ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE TYPES   │ 🔶 aws-generic, 📦 s3-bucket, 🌀 kubernetes-cluster, 🐳 docker-registry ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE NAME    │ <multiple>                                                              ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ SECRET ID        │ 6e03d968-fba0-47ff-b01d-eeb58780bcc8                                    ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ SESSION DURATION │ 43200s                                                                  ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ EXPIRES IN       │ N/A                                                                     ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ OWNER            │ default                                                                 ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ WORKSPACE        │ default                                                                 ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ SHARED           │ ➖                                                                      ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ CREATED_AT       │ 2023-05-16 16:59:56.761936                                              ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-05-16 16:59:56.761939                                              ┃
┗━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
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
```

The AWS Service Connector discovered and lifted the AWS Secret Key that was configured on the local machine and securely stored it in the [Secrets Store](../use-the-secret-store/use-the-secret-store.md). Normally, this would be cause for concern, because the AWS Secret Key gives access to any and all AWS resources in your account and should not be distributed to third parties.

However, in this case, _the following security best practice is automatically enforced by the AWS connector_: the AWS Secret Key will be kept hidden and the clients will never use it directly to gain access to any AWS resources. Instead, the AWS Service Connector will generate short-lived security tokens and distribute those to clients. It will also take care of issuing new tokens when those expire. This is identifiable from the `session-token` authentication method and the session duration configuration attributes.

One way to confirm this is to ask ZenML to show us the exact configuration that a Service Connector client would see, but this requires us to pick a resource for which temporary credentials can be generated and use the `--client` CLI flag:

```
$ zenml service-connector describe aws-auto --client --resource-type s3-bucket --resource-id s3://zenfiles
Service connector 'aws-auto (s3-bucket | s3://zenfiles client)' of type 'aws' with id '4c0c0511-0ffd-42c6-9ea9-6a33b19620a2' is owned by user 'default' and is 'private'.
    'aws-auto (s3-bucket | s3://zenfiles client)' aws Service     
                        Connector Details                         
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                       ┃
┠──────────────────┼─────────────────────────────────────────────┨
┃ ID               │ 4c0c0511-0ffd-42c6-9ea9-6a33b19620a2        ┃
┠──────────────────┼─────────────────────────────────────────────┨
┃ NAME             │ aws-auto (s3-bucket | s3://zenfiles client) ┃
┠──────────────────┼─────────────────────────────────────────────┨
┃ TYPE             │ 🔶 aws                                      ┃
┠──────────────────┼─────────────────────────────────────────────┨
┃ AUTH METHOD      │ sts-token                                   ┃
┠──────────────────┼─────────────────────────────────────────────┨
┃ RESOURCE TYPES   │ 📦 s3-bucket                                ┃
┠──────────────────┼─────────────────────────────────────────────┨
┃ RESOURCE NAME    │ s3://zenfiles                               ┃
┠──────────────────┼─────────────────────────────────────────────┨
┃ SECRET ID        │                                             ┃
┠──────────────────┼─────────────────────────────────────────────┨
┃ SESSION DURATION │ N/A                                         ┃
┠──────────────────┼─────────────────────────────────────────────┨
┃ EXPIRES IN       │ 11h59m55s                                   ┃
┠──────────────────┼─────────────────────────────────────────────┨
┃ OWNER            │ default                                     ┃
┠──────────────────┼─────────────────────────────────────────────┨
┃ WORKSPACE        │ default                                     ┃
┠──────────────────┼─────────────────────────────────────────────┨
┃ SHARED           │ ➖                                          ┃
┠──────────────────┼─────────────────────────────────────────────┨
┃ CREATED_AT       │ 2023-05-16 17:28:13.164651                  ┃
┠──────────────────┼─────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-05-16 17:28:13.164654                  ┃
┗━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
            Configuration            
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━┓
┃ PROPERTY              │ VALUE     ┃
┠───────────────────────┼───────────┨
┃ region                │ us-east-1 ┃
┠───────────────────────┼───────────┨
┃ aws_access_key_id     │ [HIDDEN]  ┃
┠───────────────────────┼───────────┨
┃ aws_secret_access_key │ [HIDDEN]  ┃
┠───────────────────────┼───────────┨
┃ aws_session_token     │ [HIDDEN]  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━┛
```

As can be seen, this configuration is of a temporary STS AWS token that will expire in 12 hours.

Of course, the AWS Secret Key to your AWS IAM user or (worse) AWS root account should still not be used as a direct means of authentication outside of local development. This is just an example and the AWS Service Connector supports other authentication methods that are more suitable for production purposes.

</details>

The third step is preparing to configure the Stack Components and Stacks that you will use to run pipelines, the same way you would do it without Service Connectors, but this time you have the option of _<mark style="color:purple;">discovering which remote resources are available</mark>_ for you to use. For example, if you needed an S3 bucket for your S3 Artifact Store, you could run the following CLI command, which is the same as asking "_which S3 buckets am I authorized to access through ZenML ?_". The result is a list of resource names, identifying those S3 buckets and the Service Connectors that facilitate access to them:&#x20;

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

The next step in this journey is _<mark style="color:purple;">configuring and connecting one or more Stack Components to a remote resource</mark>_ via the Service Connector registered and listed in previous steps. This is as easy as saying "_I want this S3 Artifact Store to use the `s3://ml-bucket` S3 bucket_" or "_I want this Kubernetes Orchestrator to use the `mega-ml-cluster` Kubernetes cluster_" and doesn't require any knowledge whatsoever about the authentication mechanisms or even the provenance of those resources. The following example creates an S3 Artifact store and connects it to an S3 bucket with the earlier connector:

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

<details>

<summary>Too much work ? Find out exactly why Service Connectors are worth the extra typing</summary>

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

* the S3 Artifact Store can be used in any ZenML Stack, by any person or automated process with access to your ZenML server, on any machine or virtual environment without the need to install or configure the AWS CLI or any AWS credentials. In the case of other types of resources, this also extends to other CLIs/SDKs in addition to AWS (e.g. you _also_ don't need the Kubernetes `kubectl` CLI when you are accessing an EKS Kubernetes cluster in your pipelines).
* setting up AWS accounts, permissions and configuring the Service Connector (first and second steps) can be done by someone with some expertise in infrastructure management, while creating and using the S3 Artifact Store (third and following steps) can be done by anyone without any such knowledge.
* you can create and connect any number of S3 Artifact Stores and other types of Stack Components (e.g. Kubernetes/Kubeflow/Tekton Orchestrators, Container Registries) to the AWS resources accessible through the Service Connector, but you only have to configure the Service Connector once.
* if your need to make any changes to the AWS authentication configuration (e.g. refresh expired credentials or remove leaked credentials) you only need to update the Service Connector and the changes will automatically be applied to all Stack Components linked to it.
* this last point is only useful if you're really serious about implementing security best practices: the AWS Service Connector in particular, as well as other cloud provider Service Connectors can automatically generate, distribute and refresh short-lived AWS security credentials for its clients. This keeps long-lived, broad access credentials like AWS Secret Keys safely stored on the ZenML Server while the actual workloads and people directly accessing those AWS resources are issued temporary, least-privilege credentials like AWS STS Tokens. This tremendously reduces the attack surface and impact of potential security incidents.

</details>

Of course, the stack component we just connected to the infrastructure is not really useful on its own. We need to _<mark style="color:purple;">make it part of a Stack, set the Stack as active, and finally run some pipelines on it</mark>_. But Service Connectors no longer play any visible role in this part, which is why they're so useful: they do all the heavy lifting in the background so you can focus on what matters.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
