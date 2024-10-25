---
description: >-
  Connect your ZenML deployment to a cloud provider and other infrastructure
  services and resources.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# 🔌 Connect services (AWS, GCP, Azure, K8s etc)

A production-grade MLOps platform involves interactions between a diverse combination of third-party libraries and external services sourced from various different vendors. One of the most daunting hurdles in building and operating an MLOps platform composed of multiple components is configuring and maintaining uninterrupted and secured access to the infrastructure resources and services that it consumes.

In layman's terms, your pipeline code needs to "connect" to a handful of different services to run successfully and do what it's designed to do. For example, it might need to connect to a private AWS S3 bucket to read and store artifacts, a Kubernetes cluster to execute steps with Kubeflow or Tekton, and a private GCR container registry to build and store container images. ZenML makes this possible by allowing you to configure authentication information and credentials embedded directly into your Stack Components, but this doesn't scale well when you have more than a few Stack Components and has many other disadvantages related to usability and security.

Gaining access to infrastructure resources and services requires knowledge about the different authentication and authorization mechanisms and involves configuring and maintaining valid credentials. It gets even more complicated when these different services need to access each other. For instance, the Kubernetes container running your pipeline step needs access to the S3 bucket to store artifacts or needs to access a cloud service like AWS SageMaker, VertexAI, or AzureML to run a CPU/GPU intensive task like training a model.

The challenge comes from _setting up and implementing proper authentication and authorization_ with the best security practices in mind, while at the same time _keeping this complexity away from the day-to-day routines_ of coding and running pipelines.

The hard-to-swallow truth is there is no single standard that unifies all authentication and authorization-related matters or a single, well-defined set of security best practices that you can follow. However, with ZenML you get the next best thing, an abstraction that keeps the complexity of authentication and authorization away from your code and makes it easier to tackle them: _<mark style="color:blue;">the ZenML Service Connectors</mark>_.

<figure><img src="../../.gitbook/assets/ConnectorsDiagram.png" alt=""><figcaption><p>Service Connectors abstract away complexity and implement security best practices</p></figcaption></figure>

## A representative use-case

The range of features covered by Service Connectors is extensive and going through the entire [Service Connector Guide](service-connectors-guide.md) can be overwhelming. If all you want is to get a quick overview of how Service Connectors work and what they can do for you, this section is for you.

This is a representative example of how you would use a Service Connector to connect ZenML to a cloud service. This example uses [the AWS Service Connector](aws-service-connector.md) to connect ZenML to an AWS S3 bucket and then link [an S3 Artifact Store Stack Component](../../component-guide/artifact-stores/s3.md) to it.

Some details about the current alternatives to using Service Connectors and their drawbacks are provided below. Feel free to skip them if you are already familiar with them or just want to get to the good part.

<details>

<summary>Alternatives to Service Connectors</summary>

There are quicker alternatives to using a Service Connector to link an S3 Artifact Store to a private AWS S3 bucket. Let's lay them out first and then explain why using a Service Connector is the better option:

1.  the authentication information can be embedded directly into the Stack Component, although this is not recommended for security reasons:

    ```shell
    zenml artifact-store register s3 --flavor s3 --path=s3://BUCKET_NAME --key=AWS_ACCESS_KEY --secret=AWS_SECRET_KEY
    ```
2.  [a ZenML secret](../../getting-started/deploying-zenml/secret-management.md) can hold the AWS credentials and then be referenced in the S3 Artifact Store configuration attributes:

    ```shell
    zenml secret create aws --aws_access_key_id=AWS_ACCESS_KEY --aws_secret_access_key=AWS_SECRET_KEY
    zenml artifact-store register s3 --flavor s3 --path=s3://BUCKET_NAME --key='{{aws.aws_access_key_id}}' --secret='{{aws.aws_secret_access_key}}'
    ```
3.  an even better version is to reference the secret itself in the S3 Artifact Store configuration:

    ```shell
    zenml secret create aws --aws_access_key_id=AWS_ACCESS_KEY --aws_secret_access_key=AWS_SECRET_KEY
    zenml artifact-store register s3 --flavor s3 --path=s3://BUCKET_NAME --authentication_secret=aws
    ```

All these options work, but they have many drawbacks:

* first of all, not all Stack Components support referencing secrets in their configuration attributes, so this is not a universal solution.
* some Stack Components, like those linked to Kubernetes clusters, rely on credentials being set up on the machine where the pipeline is running, which makes pipelines less portable and more difficult to set up. In other cases, you also need to install and set up cloud-specific SDKs and CLIs to be able to use the Stack Component.
* people configuring and using Stack Components linked to cloud resources need to be given access to cloud credentials, or even provision the credentials themselves, which requires access to the cloud provider platform and knowledge about how to do it.
* in many cases, you can only configure long-lived credentials directly in Stack Components. This is a security risk because they can inadvertently grant access to key resources and services to a malicious party if they are compromised. Implementing a process that rotates credentials regularly is a complex task that requires a lot of effort and maintenance.
* Stack Components don't implement any kind of verification regarding the validity and permission of configured credentials. If the credentials are invalid or if they lack the proper permissions to access the remote resource or service, you will only find this out later, when running a pipeline will fail at runtime.
* ultimately, given that different Stack Component flavors rely on the same type of resource or cloud provider, it is not good design to duplicate the logic that handles authentication and authorization in each Stack Component implementation.

These drawbacks are addressed by Service Connectors.

</details>

Without Service Connectors, credentials are stored directly in the Stack Component configuration or ZenML Secret and are directly used in the runtime environment. The Stack Component implementation is directly responsible for validating credentials, authenticating and connecting to the infrastructure service. This is illustrated in the following diagram:

![Authentication without Service Connectors](../../.gitbook/assets/authentication\_without\_connectors.png)

When Service Connectors are involved in the authentication and authorization process, they can act as brokers. The credentials validation and authentication process takes place on the ZenML server. In most cases, the main credentials never have to leave the ZenML server as the Service Connector automatically converts them into short-lived credentials with a reduced set of privileges and issues these credentials to clients. Furthermore, multiple Stack Components of different flavors can use the same Service Connector to access different types or resources with the same credentials:

![Authentication with Service Connectors](../../.gitbook/assets/authentication\_with\_connectors.png)

In working with Service Connectors, the first step is usually _<mark style="color:purple;">finding out what types of resources you can connect ZenML to</mark>_. Maybe you have already planned out the infrastructure options for your MLOps platform and are looking to find out whether ZenML can accommodate them. Or perhaps you want to use a particular Stack Component flavor in your Stack and are wondering whether you can use a Service Connector to connect it to external resources.

Listing the available Service Connector Types will give you a good idea of what you can do with Service Connectors:

```sh
zenml service-connector list-types
```

{% code title="Example Command Output" %}
```
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
┠──────────────────────────────┼───────────────┼───────────────────────┼──────────────────┼───────┼────────┨
┃  HyperAI Service Connector   │ 🤖 hyperai    │ 🤖 hyperai-instance   │ rsa-key          │ ✅   │ ✅     ┃
┃                              │               │                       │ dsa-key          │       │        ┃
┃                              │               │                       │ ecdsa-key        │       │        ┃
┃                              │               │                       │ ed25519-key      │       │        ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━┷━━━━━━━┷━━━━━━━━┛
```
{% endcode %}

Service Connector Types are also displayed in the dashboard during the configuration of a new Service Connector:

The cloud provider of choice for our example is AWS and we're looking to hook up an S3 bucket to an S3 Artifact Store Stack Component. We'll use the AWS Service Connector Type.

<details>

<summary>Interactive structured docs with Service Connector Types</summary>

A lot more is hidden behind a Service Connector Type than a name and a simple list of resource types. Before using a Service Connector Type to configure a Service Connector, you probably need to understand what it is, what it can offer and what are the supported authentication methods and their requirements. All this can be accessed on-site directly through the CLI or in the dashboard. Some examples are included here.

Showing information about the AWS Service Connector Type:

```sh
zenml service-connector describe-type aws
```

{% code title="Example Command Output" %}
```
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
                                                                                
 • pip install "zenml[connectors-aws]" installs only prerequisites for the AWS    
   Service Connector Type                                                       
 • zenml integration install aws installs the entire AWS ZenML integration      
                                                                                
It is not required to install and set up the AWS CLI on your local machine to   
use the AWS Service Connector to link Stack Components to AWS resources and     
services. However, it is recommended to do so if you are looking for a quick    
setup that includes using the auto-configuration Service Connector features.    
                                                                                
────────────────────────────────────────────────────────────────────────────────
```
{% endcode %}

Dashboard equivalent:

<img src="../../.gitbook/assets/aws-service-connector-type.png" alt="AWS Service Connector Type Details" data-size="original">

Fetching details about the S3 bucket resource type:

```sh
zenml service-connector describe-type aws --resource-type s3-bucket
```

{% code title="Example Command Output" %}
```
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
{% endcode %}

Dashboard equivalent:

<img src="../../.gitbook/assets/.gitbook/assets/aws-s3-bucket-resource-type.png" alt="AWS Service Connector Type Details" data-size="original">

Displaying information about the AWS Session Token authentication method:

```sh
zenml service-connector describe-type aws --auth-method session-token
```

{% code title="Example Command Output" %}
```
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
{% endcode %}

Dashboard equivalent:

<img src="../../.gitbook/assets/.gitbook/assets/aws-session-token-auth-method.png" alt="AWS Service Connector Type Details" data-size="original">

</details>

Not all Stack Components support being linked to a Service Connector. This is indicated in the flavor description of each Stack Component. Our example uses the S3 Artifact Store, which does support it:

```sh
$ zenml artifact-store flavor describe s3
Configuration class: S3ArtifactStoreConfig

[...]

This flavor supports connecting to external resources with a Service Connector. It requires a 's3-bucket' resource. You can get a list of all available connectors and the compatible resources that they can 
access by running:

'zenml service-connector list-resources --resource-type s3-bucket'
If no compatible Service Connectors are yet registered, you can register a new one by running:

'zenml service-connector register -i'
```

The second step is _<mark style="color:purple;">registering a Service Connector</mark>_ that effectively enables ZenML to authenticate to and access one or more remote resources. This step is best handled by someone with some infrastructure knowledge, but there are sane defaults and auto-detection mechanisms built into most Service Connectors that can make this a walk in the park even for the uninitiated. For our simple example, we're registering an AWS Service Connector with AWS credentials _automatically lifted up from your local host_, giving ZenML access to the same resources that you can access from your local machine through the AWS CLI.

This step assumes the AWS CLI is already installed and set up with credentials on your machine (e.g. by running `aws configure`).

```sh
zenml service-connector register aws-s3 --type aws --auto-configure --resource-type s3-bucket
```

{% code title="Example Command Output" %}
```
⠼ Registering service connector 'aws-s3'...
Successfully registered service connector `aws-s3` with access to the following resources:
┏━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ RESOURCE TYPE │ RESOURCE NAMES                        ┃
┠───────────────┼───────────────────────────────────────┨
┃ 📦 s3-bucket  │ s3://aws-ia-mwaa-715803424590         ┃
┃               │ s3://zenbytes-bucket                  ┃
┃               │ s3://zenfiles                         ┃
┃               │ s3://zenml-demos                      ┃
┃               │ s3://zenml-generative-chat            ┃
┃               │ s3://zenml-public-datasets            ┃
┃               │ s3://zenml-public-swagger-spec        ┃
┗━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

The CLI validates and shows all S3 buckets that can be accessed with the auto-discovered credentials.

{% hint style="info" %}
The ZenML CLI provides an interactive way of registering Service Connectors. Just use the `-i` command line argument and follow the interactive guide:

```
zenml service-connector register -i
```
{% endhint %}

<details>

<summary>What happens during auto-configuration</summary>

A quick glance into the Service Connector configuration that was automatically detected gives a better idea of what happened:

```sh
zenml service-connector describe aws-s3
```

{% code title="Example Command Output" %}
```
Service connector 'aws-s3' of type 'aws' with id '96a92154-4ec7-4722-bc18-21eeeadb8a4f' is owned by user 'default' and is 'private'.
          'aws-s3' aws Service Connector Details           
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                ┃
┠──────────────────┼──────────────────────────────────────┨
┃ ID               │ 96a92154-4ec7-4722-bc18-21eeeadb8a4f ┃
┠──────────────────┼──────────────────────────────────────┨
┃ NAME             │ aws-s3                               ┃
┠──────────────────┼──────────────────────────────────────┨
┃ TYPE             │ 🔶 aws                               ┃
┠──────────────────┼──────────────────────────────────────┨
┃ AUTH METHOD      │ session-token                        ┃
┠──────────────────┼──────────────────────────────────────┨
┃ RESOURCE TYPES   │ 📦 s3-bucket                         ┃
┠──────────────────┼──────────────────────────────────────┨
┃ RESOURCE NAME    │ <multiple>                           ┃
┠──────────────────┼──────────────────────────────────────┨
┃ SECRET ID        │ a8c6d0ff-456a-4b25-8557-f0d7e3c12c5f ┃
┠──────────────────┼──────────────────────────────────────┨
┃ SESSION DURATION │ 43200s                               ┃
┠──────────────────┼──────────────────────────────────────┨
┃ EXPIRES IN       │ N/A                                  ┃
┠──────────────────┼──────────────────────────────────────┨
┃ OWNER            │ default                              ┃
┠──────────────────┼──────────────────────────────────────┨
┃ SHARED           │ ➖                                   ┃
┠──────────────────┼──────────────────────────────────────┨
┃ CREATED_AT       │ 2023-06-15 18:45:17.822337           ┃
┠──────────────────┼──────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-06-15 18:45:17.822341           ┃
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
```
{% endcode %}

The AWS Service Connector discovered and lifted the AWS Secret Key that was configured on the local machine and securely stored it in the [Secrets Store](../../getting-started/deploying-zenml/secret-management.md).

Moreover, the following security best practice is automatically enforced by the AWS connector: the AWS Secret Key will be kept hidden on the ZenML Server and the clients will never use it directly to gain access to any AWS resources. Instead, the AWS Service Connector will generate short-lived security tokens and distribute those to clients. It will also take care of issuing new tokens when those expire. This is identifiable from the `session-token` authentication method and the session duration configuration attributes.

One way to confirm this is to ask ZenML to show us the exact configuration that a Service Connector client would see, but this requires us to pick an S3 bucket for which temporary credentials can be generated:

```sh
zenml service-connector describe aws-s3 --resource-id s3://zenfiles
```

{% code title="Example Command Output" %}
```
Service connector 'aws-s3 (s3-bucket | s3://zenfiles client)' of type 'aws' with id '96a92154-4ec7-4722-bc18-21eeeadb8a4f' is owned by user 'default' and is 'private'.
    'aws-s3 (s3-bucket | s3://zenfiles client)' aws Service     
                       Connector Details                        
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                     ┃
┠──────────────────┼───────────────────────────────────────────┨
┃ ID               │ 96a92154-4ec7-4722-bc18-21eeeadb8a4f      ┃
┠──────────────────┼───────────────────────────────────────────┨
┃ NAME             │ aws-s3 (s3-bucket | s3://zenfiles client) ┃
┠──────────────────┼───────────────────────────────────────────┨
┃ TYPE             │ 🔶 aws                                    ┃
┠──────────────────┼───────────────────────────────────────────┨
┃ AUTH METHOD      │ sts-token                                 ┃
┠──────────────────┼───────────────────────────────────────────┨
┃ RESOURCE TYPES   │ 📦 s3-bucket                              ┃
┠──────────────────┼───────────────────────────────────────────┨
┃ RESOURCE NAME    │ s3://zenfiles                             ┃
┠──────────────────┼───────────────────────────────────────────┨
┃ SECRET ID        │                                           ┃
┠──────────────────┼───────────────────────────────────────────┨
┃ SESSION DURATION │ N/A                                       ┃
┠──────────────────┼───────────────────────────────────────────┨
┃ EXPIRES IN       │ 11h59m56s                                 ┃
┠──────────────────┼───────────────────────────────────────────┨
┃ OWNER            │ default                                   ┃
┠──────────────────┼───────────────────────────────────────────┨
┃ SHARED           │ ➖                                        ┃
┠──────────────────┼───────────────────────────────────────────┨
┃ CREATED_AT       │ 2023-06-15 18:56:33.880081                ┃
┠──────────────────┼───────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-06-15 18:56:33.880082                ┃
┗━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
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
{% endcode %}

As can be seen, this configuration is of a temporary STS AWS token that will expire in 12 hours. The AWS Secret Key is not visible on the client side.

</details>

The next step in this journey is _<mark style="color:purple;">configuring and connecting one (or more) Stack Components to a remote resource</mark>_ via the Service Connector registered in the previous step. This is as easy as saying "_I want this S3 Artifact Store to use the `s3://my-bucket` S3 bucket_" and doesn't require any knowledge whatsoever about the authentication mechanisms or even the provenance of those resources. The following example creates an S3 Artifact store and connects it to an S3 bucket with the earlier connector:

```sh
zenml artifact-store register s3-zenfiles --flavor s3 --path=s3://zenfiles
zenml artifact-store connect s3-zenfiles --connector aws-s3
```

{% code title="Example Command Output" %}
```
$ zenml artifact-store register s3-zenfiles --flavor s3 --path=s3://zenfiles
Successfully registered artifact_store `s3-zenfiles`.

$ zenml artifact-store connect s3-zenfiles --connector aws-s3
Successfully connected artifact store `s3-zenfiles` to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────┼────────────────┨
┃ 96a92154-4ec7-4722-bc18-21eeeadb8a4f │ aws-s3         │ 🔶 aws         │ 📦 s3-bucket  │ s3://zenfiles  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛
```
{% endcode %}

{% hint style="info" %}
The ZenML CLI provides an even easier and more interactive way of connecting a stack component to an external resource. Just pass the `-i` command line argument and follow the interactive guide:

```
zenml artifact-store register s3-zenfiles --flavor s3 --path=s3://zenfiles
zenml artifact-store connect s3-zenfiles -i
```
{% endhint %}

The S3 Artifact Store Stack Component we just connected to the infrastructure is now ready to be used in a stack to run a pipeline:

```sh
zenml stack register s3-zenfiles -o default -a s3-zenfiles --set
```

A simple pipeline could look like this:

```python
from zenml import step, pipeline

@step
def simple_step_one() -> str:
    """Simple step one."""
    return "Hello World!"


@step
def simple_step_two(msg: str) -> None:
    """Simple step two."""
    print(msg)


@pipeline
def simple_pipeline() -> None:
    """Define single step pipeline."""
    message = simple_step_one()
    simple_step_two(msg=message)


if __name__ == "__main__":
    simple_pipeline()
```

Save this as `run.py` and run it with the following command:

```sh
python run.py
```

{% code title="Example Command Output" %}
```
Running pipeline simple_pipeline on stack s3-zenfiles (caching enabled)
Step simple_step_one has started.
Step simple_step_one has finished in 1.065s.
Step simple_step_two has started.
Hello World!
Step simple_step_two has finished in 5.681s.
Pipeline run simple_pipeline-2023_06_15-19_29_42_159831 has finished in 12.522s.
Dashboard URL: http://127.0.0.1:8237/default/pipelines/8267b0bc-9cbd-42ac-9b56-4d18275bdbb4/runs
```
{% endcode %}

This example is just a simple demonstration of how to use Service Connectors to connect ZenML Stack Components to your infrastructure. The range of features and possibilities is much larger. ZenML ships with built-in Service Connectors able to connect and authenticate to AWS, GCP, and Azure and offers many different authentication methods and security best practices. Follow the resources below for more information.

<table data-view="cards"><thead><tr><th></th><th></th><th data-hidden></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td><span data-gb-custom-inline data-tag="emoji" data-code="1fa84">🪄</span> <mark style="color:purple;"><strong>The complete guide to Service Connectors</strong></mark></td><td>Everything you need to know to unlock the power of Service Connectors in your project.</td><td></td><td><a href="./service-connectors-guide.md">./service-connectors-guide.md</a></td></tr><tr><td><span data-gb-custom-inline data-tag="emoji" data-code="2705">✅</span> <mark style="color:purple;"><strong>Security Best Practices</strong></mark></td><td>Best practices concerning the various authentication methods implemented by Service Connectors.</td><td></td><td><a href="./best-security-practices.md">./best-security-practices.md</a></td></tr><tr><td><span data-gb-custom-inline data-tag="emoji" data-code="1f40b">🐋</span> <mark style="color:purple;"><strong>Docker Service Connector</strong></mark></td><td>Use the Docker Service Connector to connect ZenML to a generic Docker container registry.</td><td></td><td><a href="./docker-service-connector.md">./docker-service-connector.md</a></td></tr><tr><td><span data-gb-custom-inline data-tag="emoji" data-code="1f300">🌀</span> <mark style="color:purple;"><strong>Kubernetes Service Connector</strong></mark></td><td>Use the Kubernetes Service Connector to connect ZenML to a generic Kubernetes cluster.</td><td></td><td><a href="./kubernetes-service-connector.md">./kubernetes-service-connector.md</a></td></tr><tr><td><span data-gb-custom-inline data-tag="emoji" data-code="1f536">🔶</span> <mark style="color:purple;"><strong>AWS Service Connector</strong></mark></td><td>Use the AWS Service Connector to connect ZenML to AWS cloud resources.</td><td></td><td><a href="./aws-service-connector.md">./aws-service-connector.md</a></td></tr><tr><td><span data-gb-custom-inline data-tag="emoji" data-code="1f535">🔵</span> <mark style="color:purple;"><strong>GCP Service Connector</strong></mark></td><td>Use the GCP Service Connector to connect ZenML to GCP cloud resources.</td><td></td><td><a href="./gcp-service-connector.md">./gcp-service-connector.md</a></td></tr><tr><td><span data-gb-custom-inline data-tag="emoji" data-code="1f170">🅰️</span> <mark style="color:purple;"><strong>Azure Service Connector</strong></mark></td><td>Use the Azure Service Connector to connect ZenML to Azure cloud resources.</td><td></td><td><a href="./azure-service-connector.md">./azure-service-connector.md</a></td></tr></tbody></table>

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
