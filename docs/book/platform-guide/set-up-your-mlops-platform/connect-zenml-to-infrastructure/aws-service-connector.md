---
description: Configuring AWS Service Connectors to connect ZenML to AWS resources like S3 buckets, EKS Kubernetes clusters and ECR container registries.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# AWS Service Connector

The ZenML AWS Service Connector facilitates the authentication and access to managed AWS services and resources. These encompass a range of resources, including S3 buckets, ECR container repositories and EKS clusters. The connector provides support for various authentication methods, including explicit long-lived AWS secret keys, IAM roles, short-lived STS tokens and implicit authentication.

To ensure heightened security measures, this connector also enables [the generation of temporary STS security tokens that are scoped down to the minimum permissions necessary](best-security-practices.md#generating-temporary-and-down-scoped-credentials) for accessing the intended resource. Furthermore, it includes [automatic configuration and detection of  credentials locally configured through the AWS CLI](service-connectors-guide.md#auto-configuration).

This connector serves as a general means of accessing any AWS service by issuing pre-authenticated boto3 sessions. Additionally, the connector can handle specialized authentication for S3, Docker and Kubernetes Python clients. It also allows for the configuration of local Docker and Kubernetes CLIs.

```
$ zenml service-connector list-types --type aws
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━┯━━━━━━━┯━━━━━━━━┓
┃         NAME          │ TYPE   │ RESOURCE TYPES        │ AUTH METHODS     │ LOCAL │ REMOTE ┃
┠───────────────────────┼────────┼───────────────────────┼──────────────────┼───────┼────────┨
┃ AWS Service Connector │ 🔶 aws │ 🔶 aws-generic        │ implicit         │ ✅    │ ✅     ┃
┃                       │        │ 📦 s3-bucket          │ secret-key       │       │        ┃
┃                       │        │ 🌀 kubernetes-cluster │ sts-token        │       │        ┃
┃                       │        │ 🐳 docker-registry    │ iam-role         │       │        ┃
┃                       │        │                       │ session-token    │       │        ┃
┃                       │        │                       │ federation-token │       │        ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━┷━━━━━━━┷━━━━━━━━┛

```

## Prerequisites

The AWS Service Connector is part of the AWS ZenML integration. You can either install the entire integration or use a pypi extra to install it independently of the integration:

* `pip install zenml[connectors-aws]` installs only prerequisites for the AWS Service Connector Type
* `zenml integration install aws` installs the entire AWS ZenML integration

It is not required to [install and set up the AWS CLI on your local machine](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html) to use the AWS Service Connector to link Stack Components to AWS resources and services. However, it is recommended to do so if you are looking for a quick setup that includes using the auto-configuration Service Connector features.

{% hint style="info" %}
The auto-configuration examples in this page rely on the AWS CLI being installed and already configured with valid credentials of one type or another. If you want to avoid installing the AWS CLI, we recommend using the interactive mode of the ZenML CLI to register Service Connectors:

```
zenml service-connector register -i --type aws
```
{% endhint %}

## Resource Types

### Generic AWS resource

This resource type allows consumers to use the AWS Service Connector to connect to any AWS service or resource. When used by connector clients, they are provided a generic Python boto3 session instance pre-configured with AWS credentials. This session can then be used to create boto3 clients for any particular AWS service.

This generic AWS resource type is meant to be used with Stack Components that are not represented by other, more specific resource type, like S3 buckets, Kubernetes clusters or Docker registries. It should be accompanied by a matching set of AWS permissions that allow access to the set of remote resources required by the client(s).

The resource name represents the AWS region that the connector is authorized to access.

### S3 bucket

Allows users to connect to S3 buckets. When used by connector consumers, they are provided a pre-configured boto3 S3 client instance.

The configured credentials must have at least the following [AWS IAM permissions](https://docs.aws.amazon.com/IAM/latest/UserGuide/access\_policies.html) associated with [the ARNs of S3 buckets ](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-arn-format.html)that the connector will be allowed to access (e.g. `arn:aws:s3:::*` and `arn:aws:s3:::*/*` represent all the available S3 buckets).

* s3:ListBucket
* s3:GetObject
* s3:PutObject
* s3:DeleteObject
* s3:ListAllMyBuckets

{% hint style="info" %}
If you are using the [AWS IAM role](aws-service-connector.md#aws-iam-role), [Session Token](aws-service-connector.md#aws-session-token) or [Federation Token](aws-service-connector.md#aws-federation-token) authentication methods, you don't have to worry too much about restricting the permissions of the AWS credentials that you use to access the AWS cloud resources. These authentication methods already support [automatically generating temporary tokens](best-security-practices.md#generating-temporary-and-down-scoped-credentials) with permissions down-scoped to the minimum required to access the target resource.
{% endhint %}

If set, the resource name must identify an S3 bucket using one of the following formats:

* S3 bucket URI (canonical resource name): `s3://{bucket-name}`
* S3 bucket ARN: `arn:aws:s3:::{bucket-name}`
* S3 bucket name: `{bucket-name}`

### EKS Kubernetes cluster

Allows users to access an EKS cluster as a standard Kubernetes cluster resource. When used by Stack Components, they are provided a pre-authenticated Python Kubernetes client instance.

The configured credentials must have at least the following [AWS IAM permissions](https://docs.aws.amazon.com/IAM/latest/UserGuide/access\_policies.html) associated with the [ARNs of EKS clusters](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference-arns.html) that the connector will be allowed to access (e.g. `arn:aws:eks:{region_id}:{project_id}:cluster/*` represents all the EKS clusters available in the target AWS region).

* eks:ListClusters
* eks:DescribeCluster

{% hint style="info" %}
If you are using the [AWS IAM role](aws-service-connector.md#aws-iam-role), [Session Token](aws-service-connector.md#aws-session-token) or [Federation Token](aws-service-connector.md#aws-federation-token) authentication methods, you don't have to worry too much about restricting the permissions of the AWS credentials that you use to access the AWS cloud resources. These authentication methods already support [automatically generating temporary tokens](best-security-practices.md#generating-temporary-and-down-scoped-credentials) with permissions down-scoped to the minimum required to access the target resource.
{% endhint %}

In addition to the above permissions, if the credentials are not associated with the same IAM user or role that created the EKS cluster, the IAM principal must be manually added to the EKS cluster's `aws-auth` ConfigMap, otherwise the Kubernetes client will not be allowed to access the cluster's resources. This makes it more challenging to use [the AWS Implicit](aws-service-connector.md#implicit-authentication) and [AWS Federation Token](aws-service-connector.md#aws-federation-token) authentication methods for this resource. For more information, [see this documentation](https://docs.aws.amazon.com/eks/latest/userguide/add-user-role.html).

If set, the resource name must identify an EKS cluster using one of the following formats:

* EKS cluster name (canonical resource name): `{cluster-name}`
* EKS cluster ARN: `arn:aws:eks:{region}:{account-id}:cluster/{cluster-name}`

EKS cluster names are region scoped. The connector can only be used to access EKS clusters in the AWS region that it is configured to use.

### ECR container registry

Allows Stack Components to access one or more ECR repositories as a standard Docker registry resource. When used by Stack Components, they are provided a pre-authenticated python-docker client instance.

The configured credentials must have at least the following [AWS IAM permissions](https://docs.aws.amazon.com/IAM/latest/UserGuide/access\_policies.html) associated with the [ARNs of one or more ECR repositories](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference-arns.html) that the connector will be allowed to access (e.g. `arn:aws:ecr:{region}:{account}:repository/*` represents all the ECR repositories available in the target AWS region).

* ecr:DescribeRegistry
* ecr:DescribeRepositories
* ecr:ListRepositories
* ecr:BatchGetImage
* ecr:DescribeImages
* ecr:BatchCheckLayerAvailability
* ecr:GetDownloadUrlForLayer
* ecr:InitiateLayerUpload
* ecr:UploadLayerPart
* ecr:CompleteLayerUpload
* ecr:PutImage
* ecr:GetAuthorizationToken

{% hint style="info" %}
If you are using the [AWS IAM role](aws-service-connector.md#aws-iam-role), [Session Token](aws-service-connector.md#aws-session-token) or [Federation Token](aws-service-connector.md#aws-federation-token) authentication methods, you don't have to worry too much about restricting the permissions of the AWS credentials that you use to access the AWS cloud resources. These authentication methods already support [automatically generating temporary tokens](best-security-practices.md#generating-temporary-and-down-scoped-credentials) with permissions down-scoped to the minimum required to access the target resource.
{% endhint %}

This resource type is not scoped to a single ECR repository. Instead, a connector configured with this resource type will grant access to all the ECR repositories that the credentials are allowed to access under the configured AWS region (i.e. all repositories under the Docker registry URL `https://{account-id}.dkr.ecr.{region}.amazonaws.com`).

The resource name associated with this resource type uniquely identifies an ECR registry using one of the following formats (the repository name is ignored, only the registry URL/ARN is used):

* ECR repository URI (canonical resource name):

`[https://]{account}.dkr.ecr.{region}.amazonaws.com[/{repository-name}]`

* ECR repository ARN :

`arn:aws:ecr:{region}:{account-id}:repository[/{repository-name}]`

ECR repository names are region scoped. The connector can only be used to access ECR repositories in the AWS region that it is configured to use.

## Authentication Methods

### Implicit authentication

[Implicit authentication](best-security-practices.md#implicit-authentication) to AWS services using environment variables, local configuration files or IAM roles.

This authentication method doesn't require any credentials to be explicitly configured. It automatically discovers and uses credentials from one of the following sources:

* environment variables (AWS\_ACCESS\_KEY\_ID, AWS\_SECRET\_ACCESS\_KEY, AWS\_SESSION\_TOKEN, AWS\_DEFAULT\_REGION)
* local configuration files [set up through the AWS CLI ](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)(\~/aws/credentials, \~/.aws/config)
* IAM roles for Amazon EC2, ECS, EKS, Lambda, etc. Only works when running the ZenML server on an AWS resource with an IAM role attached to it.

This is the quickest and easiest way to authenticate to AWS services. However, the results depend on how ZenML is deployed and the environment where it is used and are thus not fully reproducible:

* when used with the default local ZenML deployment or a local ZenML server, the credentials are the same as those used by the AWS CLI or extracted from local environment variables
* when connected to a ZenML server, this method only works if the ZenML server is deployed in AWS and will use the IAM role attached to the AWS resource where the ZenML server is running (e.g. an EKS cluster). The IAM role permissions may need to be adjusted to allows listing and accessing/describing the AWS resources that the connector is configured to access.

Note that the discovered credentials inherit the full set of permissions of the local AWS client configuration, environment variables or remote AWS IAM role. Depending on the extent of those permissions, this authentication method might not be recommended for production use, as it can lead to accidental privilege escalation. Instead, it is recommended to use the [AWS IAM Role](aws-service-connector.md#aws-iam-role), [AWS Session Token](aws-service-connector.md#aws-session-token) or [AWS Federation Token](aws-service-connector.md#aws-federation-token) authentication methods to limit the validity and/or permissions of the credentials being issued to connector clients.

{% hint style="info" %}
If you need to access an EKS kubernetes cluster with this authentication method, please be advised that the EKS cluster's `aws-auth` ConfigMap may need to be manually configured to allow authentication with the implicit IAM user or role picked up by the Service Connector. For more information, [see this documentation](https://docs.aws.amazon.com/eks/latest/userguide/add-user-role.html).
{% endhint %}

An AWS region is required and the connector may only be used to access AWS resources in the specified region. When used with a remote IAM role, the region has to be the same as the region where the IAM role is configured.

<details>

<summary>Example configuration</summary>

The following assumes the local AWS CLI has a `connectors` AWS CLI profile already configured with credentials:

```
$ AWS_PROFILE=connectors zenml service-connector register aws-implicit --type aws --auth-method implicit --region=us-east-1
⠸ Registering service connector 'aws-implicit'...
Successfully registered service connector `aws-implicit` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────────────┼────────────────┨
┃ e3853748-34a0-4d78-8006-00422ad32884 │ aws-implicit   │ 🔶 aws         │ 🔶 aws-generic        │ 🤷 none listed ┃
┃                                      │                │                │ 📦 s3-bucket          │                ┃
┃                                      │                │                │ 🌀 kubernetes-cluster │                ┃
┃                                      │                │                │ 🐳 docker-registry    │                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛
```

No credentials are stored with the Service Connector:

```
zenml service-connector describe aws-implicit 
Service connector 'aws-implicit' of type 'aws' with id 'e3853748-34a0-4d78-8006-00422ad32884' is owned by user 'default' and is 'private'.
                         'aws-implicit' aws Service Connector Details                         
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                                   ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ ID               │ e3853748-34a0-4d78-8006-00422ad32884                                    ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ NAME             │ aws-implicit                                                            ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ TYPE             │ 🔶 aws                                                                  ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ AUTH METHOD      │ implicit                                                                ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE TYPES   │ 🔶 aws-generic, 📦 s3-bucket, 🌀 kubernetes-cluster, 🐳 docker-registry ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE NAME    │ <multiple>                                                              ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ SECRET ID        │                                                                         ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ SESSION DURATION │ N/A                                                                     ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ EXPIRES IN       │ N/A                                                                     ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ OWNER            │ default                                                                 ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ WORKSPACE        │ default                                                                 ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ SHARED           │ ➖                                                                      ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ CREATED_AT       │ 2023-05-18 14:14:59.844031                                              ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-05-18 14:14:59.844037                                              ┃
┗━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
     Configuration      
┏━━━━━━━━━━┯━━━━━━━━━━━┓
┃ PROPERTY │ VALUE     ┃
┠──────────┼───────────┨
┃ region   │ us-east-1 ┃
┗━━━━━━━━━━┷━━━━━━━━━━━┛
```

Verifying access to resources (note the `AWS_PROFILE` environment points to the same AWS CLI profile used during registration, but may yield different results with a different profile, which is why this method is not suitable for reproducible results):

```
$ AWS_PROFILE=connectors zenml service-connector verify aws-implicit --resource-type s3-bucket
⠸ Verifying service connector 'aws-implicit'...
Service connector 'aws-implicit' is correctly configured with valid credentials and has access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE │ RESOURCE NAMES                        ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────┼───────────────────────────────────────┨
┃ e3853748-34a0-4d78-8006-00422ad32884 │ aws-implicit   │ 🔶 aws         │ 📦 s3-bucket  │ s3://public-flavor-logos              ┃
┃                                      │                │                │               │ s3://zenfiles                         ┃
┃                                      │                │                │               │ s3://zenml-demos                      ┃
┃                                      │                │                │               │ s3://zenml-generative-chat            ┃
┃                                      │                │                │               │ s3://zenml-public-datasets            ┃
┃                                      │                │                │               │ s3://zenml-public-swagger-spec        ┃
┃                                      │                │                │               │ s3://zenml-sandbox-infra              ┃
┃                                      │                │                │               │ s3://zenml-terraform-ci               ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

$ zenml service-connector verify aws-implicit --resource-type s3-bucket
⠸ Verifying service connector 'aws-implicit'...
Service connector 'aws-implicit' is correctly configured with valid credentials and has access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE │ RESOURCE NAMES                                 ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────┼────────────────────────────────────────────────┨
┃ e3853748-34a0-4d78-8006-00422ad32884 │ aws-implicit   │ 🔶 aws         │ 📦 s3-bucket  │ s3://sagemaker-studio-907999144431-m11qlsdyqr8 ┃
┃                                      │                │                │               │ s3://sagemaker-studio-d8a14tvjsmb              ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

Depending on the environment, clients are issued either temporary STS tokens or long-lived credentials, which is a reason why this method isn't well suited for production:

```
$ AWS_PROFILE=zenml zenml service-connector describe aws-implicit --resource-type s3-bucket --resource-id zenfiles --client
INFO:botocore.credentials:Found credentials in shared credentials file: ~/.aws/credentials
Service connector 'aws-implicit (s3-bucket | s3://zenfiles client)' of type 'aws' with id 'e3853748-34a0-4d78-8006-00422ad32884' is owned by user 'default' and is 'private'.
    'aws-implicit (s3-bucket | s3://zenfiles client)' aws Service     
                          Connector Details                           
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                           ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ ID               │ e3853748-34a0-4d78-8006-00422ad32884            ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ NAME             │ aws-implicit (s3-bucket | s3://zenfiles client) ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ TYPE             │ 🔶 aws                                          ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ AUTH METHOD      │ sts-token                                       ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ RESOURCE TYPES   │ 📦 s3-bucket                                    ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ RESOURCE NAME    │ s3://zenfiles                                   ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ SECRET ID        │                                                 ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ SESSION DURATION │ N/A                                             ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ EXPIRES IN       │ 59m57s                                          ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ OWNER            │ default                                         ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ WORKSPACE        │ default                                         ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ SHARED           │ ➖                                              ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ CREATED_AT       │ 2023-05-18 14:44:49.919051                      ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-05-18 14:44:49.919053                      ┃
┗━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
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

$ zenml service-connector describe aws-implicit --resource-type s3-bucket --resource-id s3://sagemaker-studio-d8a14tvjsmb --client
INFO:botocore.credentials:Found credentials in shared credentials file: ~/.aws/credentials
Service connector 'aws-implicit (s3-bucket | s3://sagemaker-studio-d8a14tvjsmb client)' of type 'aws' with id 'e3853748-34a0-4d78-8006-00422ad32884' is owned by user 'default' and is 'private'.
    'aws-implicit (s3-bucket | s3://sagemaker-studio-d8a14tvjsmb client)' aws Service     
                                    Connector Details                                     
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                               ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ ID               │ e3853748-34a0-4d78-8006-00422ad32884                                ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ NAME             │ aws-implicit (s3-bucket | s3://sagemaker-studio-d8a14tvjsmb client) ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ TYPE             │ 🔶 aws                                                              ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ AUTH METHOD      │ secret-key                                                          ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ RESOURCE TYPES   │ 📦 s3-bucket                                                        ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ RESOURCE NAME    │ s3://sagemaker-studio-d8a14tvjsmb                                   ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ SECRET ID        │                                                                     ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ SESSION DURATION │ N/A                                                                 ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ EXPIRES IN       │ N/A                                                                 ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ OWNER            │ default                                                             ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ WORKSPACE        │ default                                                             ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ SHARED           │ ➖                                                                  ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ CREATED_AT       │ 2023-05-18 14:53:58.459272                                          ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-05-18 14:53:58.459276                                          ┃
┗━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
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

</details>

### AWS Secret Key

[Long-lived AWS credentials](best-security-practices.md#long-lived-credentials-api-keys-account-keys) consisting of an AWS access key ID and secret access key associated with an AWS IAM user or AWS account root user (not recommended).

This method is preferred during development and testing due to its simplicity and ease of use. It is not recommended as a direct authentication method for production use cases because the clients have direct access to long-lived credentials and are granted the full set of permissions of the IAM user or AWS account root user associated with the credentials. For production, it is recommended to use [the AWS IAM Role](aws-service-connector.md#aws-iam-role), [AWS Session Token](aws-service-connector.md#aws-session-token) or [AWS Federation Token](aws-service-connector.md#aws-federation-token) authentication method instead.

An AWS region is required and the connector may only be used to access AWS resources in the specified region.

If you already have the local AWS CLI set up with these credentials, they will be automatically picked up when auto-configuration is used (see the example below).

<details>

<summary>Example auto-configuration</summary>

The following assumes the local AWS CLI has a `connectors` AWS CLI profile configured with an AWS Secret Key. We need to force the ZenML CLI to use the Secret Key authentication by passing the `--auth-method secret-key` option, otherwise it would automatically use [the AWS Session Token authentication method](aws-service-connector.md#aws-session-token) as an extra precaution:

```
$ AWS_PROFILE=connectors zenml service-connector register aws-secret-key --type aws --auth-method secret-key --auto-configure
⠸ Registering service connector 'aws-secret-key'...
Successfully registered service connector `aws-secret-key` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────────────┼────────────────┨
┃ a1b07c5a-13af-4571-8e63-57a809c85790 │ aws-secret-key │ 🔶 aws         │ 🔶 aws-generic        │ 🤷 none listed ┃
┃                                      │                │                │ 📦 s3-bucket          │                ┃
┃                                      │                │                │ 🌀 kubernetes-cluster │                ┃
┃                                      │                │                │ 🐳 docker-registry    │                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛
```

The AWS Secret Key was lifted up from the local host:

```
$ zenml service-connector describe aws-secret-key
Service connector 'aws-secret-key' of type 'aws' with id 'a1b07c5a-13af-4571-8e63-57a809c85790' is owned by user 'default' and is 'private'.
                        'aws-secret-key' aws Service Connector Details                        
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                                   ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ ID               │ a1b07c5a-13af-4571-8e63-57a809c85790                                    ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ NAME             │ aws-secret-key                                                          ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ TYPE             │ 🔶 aws                                                                  ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ AUTH METHOD      │ secret-key                                                              ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE TYPES   │ 🔶 aws-generic, 📦 s3-bucket, 🌀 kubernetes-cluster, 🐳 docker-registry ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE NAME    │ <multiple>                                                              ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ SECRET ID        │ 3dacb118-855a-4e03-ba3e-8e60d91582f2                                    ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ SESSION DURATION │ N/A                                                                     ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ EXPIRES IN       │ N/A                                                                     ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ OWNER            │ default                                                                 ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ WORKSPACE        │ default                                                                 ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ SHARED           │ ➖                                                                      ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ CREATED_AT       │ 2023-05-18 14:31:46.174707                                              ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-05-18 14:31:46.174708                                              ┃
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



</details>

### AWS STS Token

Uses [temporary STS tokens](best-security-practices.md#short-lived-credentials) explicitly configured by the user or auto-configured from a local environment.

This method has the major limitation that the user must regularly generate new tokens and update the connector configuration as STS tokens expire. On the other hand, this method is ideal in cases where the connector only needs to be used for a short period of time, such as sharing access temporarily with someone else in your team.

Using other authentication methods like [IAM role](aws-service-connector.md#aws-iam-role), [Session Token](aws-service-connector.md#aws-session-token) or [Federation Token](aws-service-connector.md#aws-federation-token) will automatically generate and refresh STS tokens for clients upon request.

An AWS region is required and the connector may only be used to access AWS resources in the specified region.

<details>

<summary>Example auto-configuration</summary>

Fetching STS tokens from the local AWS CLI is possible if the AWS CLI is already configured with valid credentials. In our example, the `connectors` AWS CLI profile is configured with an IAM user Secret Key. We need to force the ZenML CLI to use the STS token authentication by passing the `--auth-method sts-token` option, otherwise it would automatically use [the session token authentication method](aws-service-connector.md#aws-session-token):

```
$ AWS_PROFILE=connectors zenml service-connector register aws-sts-token --type aws --auto-configure --auth-method sts-token
⠸ Registering service connector 'aws-sts-token'...
Successfully registered service connector `aws-sts-token` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────────────┼────────────────┨
┃ 63e14350-6719-4255-b3f5-0539c8f7c303 │ aws-sts-token  │ 🔶 aws         │ 🔶 aws-generic        │ 🤷 none listed ┃
┃                                      │                │                │ 📦 s3-bucket          │                ┃
┃                                      │                │                │ 🌀 kubernetes-cluster │                ┃
┃                                      │                │                │ 🐳 docker-registry    │                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛

$ zenml service-connector describe aws-sts-token 
Service connector 'aws-sts-token' of type 'aws' with id '63e14350-6719-4255-b3f5-0539c8f7c303' is owned by user 'default' and is 'private'.
                        'aws-sts-token' aws Service Connector Details                         
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                                   ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ ID               │ 63e14350-6719-4255-b3f5-0539c8f7c303                                    ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ NAME             │ aws-sts-token                                                           ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ TYPE             │ 🔶 aws                                                                  ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ AUTH METHOD      │ sts-token                                                               ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE TYPES   │ 🔶 aws-generic, 📦 s3-bucket, 🌀 kubernetes-cluster, 🐳 docker-registry ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE NAME    │ <multiple>                                                              ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ SECRET ID        │ ff93e6a0-2ce2-42ce-a540-1b88d26d0988                                    ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ SESSION DURATION │ N/A                                                                     ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ EXPIRES IN       │ 11h59m55s                                                               ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ OWNER            │ default                                                                 ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ WORKSPACE        │ default                                                                 ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ SHARED           │ ➖                                                                      ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ CREATED_AT       │ 2023-05-19 08:58:09.755925                                              ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-05-19 08:58:09.755927                                              ┃
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
┠───────────────────────┼───────────┨
┃ aws_session_token     │ [HIDDEN]  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━┛
```

Note the temporary nature of the Service Connector. It will become unusable in 12 hours:

```
$ zenml service-connector list --name aws-sts-token 
┏━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━┓
┃ ACTIVE │ NAME          │ ID                                   │ TYPE   │ RESOURCE TYPES        │ RESOURCE NAME │ SHARED │ OWNER   │ EXPIRES IN │ LABELS ┃
┠────────┼───────────────┼──────────────────────────────────────┼────────┼───────────────────────┼───────────────┼────────┼─────────┼────────────┼────────┨
┃        │ aws-sts-token │ 63e14350-6719-4255-b3f5-0539c8f7c303 │ 🔶 aws │ 🔶 aws-generic        │ <multiple>    │ ➖     │ default │ 11h59m50s  │        ┃
┃        │               │                                      │        │ 📦 s3-bucket          │               │        │         │            │        ┃
┃        │               │                                      │        │ 🌀 kubernetes-cluster │               │        │         │            │        ┃
┃        │               │                                      │        │ 🐳 docker-registry    │               │        │         │            │        ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━┛
```

</details>

### AWS IAM Role

Generates [temporary STS credentials](best-security-practices.md#impersonating-accounts-and-assuming-roles) by assuming an AWS IAM role.

The connector needs to be configured with the IAM role to be assumed accompanied by an AWS secret key associated with an IAM user or an STS token associated with another IAM role. The IAM user or IAM role must have permissions to assume the target IAM role. The connector will [generate temporary STS tokens](best-security-practices.md#generating-temporary-and-down-scoped-credentials) upon request by [calling the AssumeRole STS API](https://docs.aws.amazon.com/IAM/latest/UserGuide/id\_credentials\_temp\_request.html#api\_assumerole).

[The best practice implemented with this authentication scheme](best-security-practices.md#impersonating-accounts-and-assuming-roles) is to keep the set of permissions associated with the primary IAM user or IAM role down to the bare minimum and grant permissions to the privilege bearing IAM role instead.

An AWS region is required and the connector may only be used to access AWS resources in the specified region.

One or more optional [IAM session policies](https://docs.aws.amazon.com/IAM/latest/UserGuide/access\_policies.html#policies\_session) may also be configured to further restrict the permissions of the generated STS tokens. If not specified, IAM session policies are automatically configured for the generated STS tokens [to restrict them to the minimum set of permissions required to access the target resource](best-security-practices.md#generating-temporary-and-down-scoped-credentials). Refer to the documentation for each supported Resource Type for the complete list of AWS permissions automatically granted to the generated STS tokens.

The default expiration period for generated STS tokens is 1 hour with a minimum of 15 minutes up to the maximum session duration setting configured for the IAM role (default is 1 hour). If you need longer-lived tokens, you can configure the IAM role to use a higher maximum expiration value (up to 12 hours) or use the AWS Federation Token or AWS Session Token authentication methods.

For more information on IAM roles and the AssumeRole AWS API, see [the official AWS documentation on the subject](https://docs.aws.amazon.com/IAM/latest/UserGuide/id\_credentials\_temp\_request.html#api\_assumerole).

For more information about the difference between this method and the AWS Federation Token authentication method, [consult this AWS documentation page](https://aws.amazon.com/blogs/security/understanding-the-api-options-for-securely-delegating-access-to-your-aws-account/).&#x20;

<details>

<summary>Example auto-configuration</summary>

The following assumes the local AWS CLI has a `zenml` AWS CLI profile already configured with an AWS Secret Key and an IAM role to be assumed:

```
$ AWS_PROFILE=zenml zenml service-connector register aws-iam-role --type aws --auto-configure
⠸ Registering service connector 'aws-iam-role'...
Successfully registered service connector `aws-iam-role` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────────────┼────────────────┨
┃ 8e499202-57fd-478e-9d2f-323d76d8d211 │ aws-iam-role   │ 🔶 aws         │ 🔶 aws-generic        │ 🤷 none listed ┃
┃                                      │                │                │ 📦 s3-bucket          │                ┃
┃                                      │                │                │ 🌀 kubernetes-cluster │                ┃
┃                                      │                │                │ 🐳 docker-registry    │                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛

$ zenml service-connector describe aws-iam-role 
Service connector 'aws-iam-role' of type 'aws' with id '8e499202-57fd-478e-9d2f-323d76d8d211' is owned by user 'default' and is 'private'.
                         'aws-iam-role' aws Service Connector Details                         
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                                   ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ ID               │ 8e499202-57fd-478e-9d2f-323d76d8d211                                    ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ NAME             │ aws-iam-role                                                            ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ TYPE             │ 🔶 aws                                                                  ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ AUTH METHOD      │ iam-role                                                                ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE TYPES   │ 🔶 aws-generic, 📦 s3-bucket, 🌀 kubernetes-cluster, 🐳 docker-registry ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE NAME    │ <multiple>                                                              ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ SECRET ID        │ 2f0bedf0-0ee5-46cc-a96e-0c864d2fff87                                    ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ SESSION DURATION │ 3600s                                                                   ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ EXPIRES IN       │ N/A                                                                     ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ OWNER            │ default                                                                 ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ WORKSPACE        │ default                                                                 ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ SHARED           │ ➖                                                                      ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ CREATED_AT       │ 2023-05-18 15:46:03.666360                                              ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-05-18 15:46:03.666363                                              ┃
┗━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                          Configuration                                           
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY              │ VALUE                                                                  ┃
┠───────────────────────┼────────────────────────────────────────────────────────────────────────┨
┃ region                │ us-east-1                                                              ┃
┠───────────────────────┼────────────────────────────────────────────────────────────────────────┨
┃ role_arn              │ arn:aws:iam::715803424590:role/OrganizationAccountRestrictedAccessRole ┃
┠───────────────────────┼────────────────────────────────────────────────────────────────────────┨
┃ aws_access_key_id     │ [HIDDEN]                                                               ┃
┠───────────────────────┼────────────────────────────────────────────────────────────────────────┨
┃ aws_secret_access_key │ [HIDDEN]                                                               ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

The following is just to show that clients receive temporary STS tokens instead of the AWS Secret Key configured in the connector (note the authentication method, expiration time and credentials):

```
$ zenml service-connector describe aws-iam-role --resource-type s3-bucket --resource-id zenfiles --client
Service connector 'aws-iam-role (s3-bucket | s3://zenfiles client)' of type 'aws' with id '8e499202-57fd-478e-9d2f-323d76d8d211' is owned by user 'default' and is 'private'.
    'aws-iam-role (s3-bucket | s3://zenfiles client)' aws Service     
                          Connector Details                           
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                           ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ ID               │ 8e499202-57fd-478e-9d2f-323d76d8d211            ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ NAME             │ aws-iam-role (s3-bucket | s3://zenfiles client) ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ TYPE             │ 🔶 aws                                          ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ AUTH METHOD      │ sts-token                                       ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ RESOURCE TYPES   │ 📦 s3-bucket                                    ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ RESOURCE NAME    │ s3://zenfiles                                   ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ SECRET ID        │                                                 ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ SESSION DURATION │ N/A                                             ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ EXPIRES IN       │ 59m57s                                          ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ OWNER            │ default                                         ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ WORKSPACE        │ default                                         ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ SHARED           │ ➖                                              ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ CREATED_AT       │ 2023-05-18 16:00:33.275753                      ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-05-18 16:00:33.275755                      ┃
┗━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
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

</details>

### AWS Session Token

Generates [temporary session STS tokens](best-security-practices.md#generating-temporary-and-down-scoped-credentials) for IAM users.

The connector needs to be configured with an AWS secret key associated with an IAM user or AWS account root user (not recommended). The connector will [generate temporary STS tokens](best-security-practices.md#generating-temporary-and-down-scoped-credentials) upon request by calling [the GetSessionToken STS API](https://docs.aws.amazon.com/IAM/latest/UserGuide/id\_credentials\_temp\_request.html#api\_getsessiontoken).

The STS tokens have an expiration period longer that those issued through the [AWS IAM Role authentication method](aws-service-connector.md#aws-iam-role) and are more suitable for long-running processes that cannot automatically re-generate credentials upon expiration.

An AWS region is required and the connector may only be used to access AWS resources in the specified region.

The default expiration period for generated STS tokens is 12 hours with a minimum of 15 minutes and a maximum of 36 hours. Temporary credentials obtained by using the AWS account root user credentials (not recommended) have a maximum duration of 1 hour.

As a precaution, when long-lived credentials (i.e. AWS Secret Keys) are detected on your environment by the Service Connector during auto-configuration, this authentication method is automatically chosen instead of the AWS [Secret Key authentication method](aws-service-connector.md#aws-secret-key) alternative.

Generated STS tokens inherit the full set of permissions of the IAM user or AWS account root user that is calling the GetSessionToken API. Depending on your security needs, this may not be suitable for production use, as it can lead to accidental privilege escalation. Instead, it is recommended to use the AWS Federation Token or [AWS IAM Role authentication](aws-service-connector.md#aws-iam-role) methods to restrict the permissions of the generated STS tokens.

For more information on session tokens and the GetSessionToken AWS API, see [the official AWS documentation on the subject](https://docs.aws.amazon.com/IAM/latest/UserGuide/id\_credentials\_temp\_request.html#api\_getsessiontoken).

<details>

<summary>Example auto-configuration</summary>

The following assumes the local AWS CLI has a `connectors` AWS CLI profile already configured with an AWS Secret Key:

```
$ AWS_PROFILE=connectors zenml service-connector register aws-session-token --type aws --auth-method session-token --auto-configure
⠸ Registering service connector 'aws-session-token'...
Successfully registered service connector `aws-session-token` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME    │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼───────────────────┼────────────────┼───────────────────────┼────────────────┨
┃ 3ae3e595-5cbc-446e-be64-e54e854e0e3f │ aws-session-token │ 🔶 aws         │ 🔶 aws-generic        │ 🤷 none listed ┃
┃                                      │                   │                │ 📦 s3-bucket          │                ┃
┃                                      │                   │                │ 🌀 kubernetes-cluster │                ┃
┃                                      │                   │                │ 🐳 docker-registry    │                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛

$ zenml service-connector describe aws-session-token
Service connector 'aws-session-token' of type 'aws' with id '3ae3e595-5cbc-446e-be64-e54e854e0e3f' is owned by user 'default' and is 'private'.
                      'aws-session-token' aws Service Connector Details                       
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                                   ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ ID               │ 3ae3e595-5cbc-446e-be64-e54e854e0e3f                                    ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ NAME             │ aws-session-token                                                       ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ TYPE             │ 🔶 aws                                                                  ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ AUTH METHOD      │ session-token                                                           ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE TYPES   │ 🔶 aws-generic, 📦 s3-bucket, 🌀 kubernetes-cluster, 🐳 docker-registry ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE NAME    │ <multiple>                                                              ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ SECRET ID        │ 8900cd25-a5bc-4db9-9e54-a817c2ab9212                                    ┃
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
┃ CREATED_AT       │ 2023-05-18 17:00:37.232248                                              ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-05-18 17:00:37.232256                                              ┃
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

The following is just to show that clients receive temporary STS tokens instead of the AWS Secret Key configured in the connector (note the authentication method, expiration time and credentials):

```
$ zenml service-connector describe aws-session-token --resource-type s3-bucket --resource-id zenfiles --client
Service connector 'aws-session-token (s3-bucket | s3://zenfiles client)' of type 'aws' with id '3ae3e595-5cbc-446e-be64-e54e854e0e3f' is owned by user 'default' and is 'private'.
    'aws-session-token (s3-bucket | s3://zenfiles client)' aws Service     
                             Connector Details                             
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                ┃
┠──────────────────┼──────────────────────────────────────────────────────┨
┃ ID               │ 3ae3e595-5cbc-446e-be64-e54e854e0e3f                 ┃
┠──────────────────┼──────────────────────────────────────────────────────┨
┃ NAME             │ aws-session-token (s3-bucket | s3://zenfiles client) ┃
┠──────────────────┼──────────────────────────────────────────────────────┨
┃ TYPE             │ 🔶 aws                                               ┃
┠──────────────────┼──────────────────────────────────────────────────────┨
┃ AUTH METHOD      │ sts-token                                            ┃
┠──────────────────┼──────────────────────────────────────────────────────┨
┃ RESOURCE TYPES   │ 📦 s3-bucket                                         ┃
┠──────────────────┼──────────────────────────────────────────────────────┨
┃ RESOURCE NAME    │ s3://zenfiles                                        ┃
┠──────────────────┼──────────────────────────────────────────────────────┨
┃ SECRET ID        │                                                      ┃
┠──────────────────┼──────────────────────────────────────────────────────┨
┃ SESSION DURATION │ N/A                                                  ┃
┠──────────────────┼──────────────────────────────────────────────────────┨
┃ EXPIRES IN       │ 11h59m57s                                            ┃
┠──────────────────┼──────────────────────────────────────────────────────┨
┃ OWNER            │ default                                              ┃
┠──────────────────┼──────────────────────────────────────────────────────┨
┃ WORKSPACE        │ default                                              ┃
┠──────────────────┼──────────────────────────────────────────────────────┨
┃ SHARED           │ ➖                                                   ┃
┠──────────────────┼──────────────────────────────────────────────────────┨
┃ CREATED_AT       │ 2023-05-18 17:00:58.558295                           ┃
┠──────────────────┼──────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-05-18 17:00:58.558296                           ┃
┗━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
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

</details>

### AWS Federation Token

Generates [temporary STS tokens](best-security-practices.md#generating-temporary-and-down-scoped-credentials) for federated users by [impersonating another user](best-security-practices.md#impersonating-accounts-and-assuming-roles).

The connector needs to be configured with an AWS secret key associated with an IAM user or AWS account root user (not recommended). The IAM user must have permissions to call [the GetFederationToken STS API](https://docs.aws.amazon.com/IAM/latest/UserGuide/id\_credentials\_temp\_request.html#api\_getfederationtoken) (i.e. allow the `sts:GetFederationToken` action on the `*` IAM resource). The connector will generate temporary STS tokens upon request by calling the GetFederationToken STS API.

These STS tokens have an expiration period longer that those issued through [the AWS IAM Role authentication method](aws-service-connector.md#aws-iam-role) and are more suitable for long-running processes that cannot automatically re-generate credentials upon expiration.

An AWS region is required and the connector may only be used to access AWS resources in the specified region.

One or more optional [IAM session policies](https://docs.aws.amazon.com/IAM/latest/UserGuide/access\_policies.html#policies\_session) may also be configured to further restrict the permissions of the generated STS tokens. If not specified, IAM session policies are automatically configured for the generated STS tokens [to restrict them to the minimum set of permissions required to access the target resource](best-security-practices.md#generating-temporary-and-down-scoped-credentials). Refer to the documentation for each supported Resource Type for the complete list of AWS permissions automatically granted to the generated STS tokens.

{% hint style="warning" %}
If this authentication method is used with [the generic AWS resource type](aws-service-connector.md#generic-aws-resource), a session policy MUST be explicitly specified, otherwise the generated STS tokens will not have any permissions.
{% endhint %}

The default expiration period for generated STS tokens is 12 hours with a minimum of 15 minutes and a maximum of 36 hours. Temporary credentials obtained by using the AWS account root user credentials (not recommended) have a maximum duration of 1 hour.

{% hint style="info" %}
If you need to access an EKS kubernetes cluster with this authentication method, please be advised that the EKS cluster's `aws-auth` ConfigMap may need to be manually configured to allow authentication with the federated user. For more information, [see this documentation](https://docs.aws.amazon.com/eks/latest/userguide/add-user-role.html).
{% endhint %}

For more information on user federation tokens, session policies and the GetFederationToken AWS API, see [the official AWS documentation on the subject](https://docs.aws.amazon.com/IAM/latest/UserGuide/id\_credentials\_temp\_request.html#api\_getfederationtoken).

For more information about the difference between this method and [the AWS IAM Role authentication method](aws-service-connector.md#aws-iam-role), [consult this AWS documentation page](https://aws.amazon.com/blogs/security/understanding-the-api-options-for-securely-delegating-access-to-your-aws-account/).

<details>

<summary>Example auto-configuration</summary>

The following assumes the local AWS CLI has a `connectors` AWS CLI profile already configured with an AWS Secret Key:

```
$ AWS_PROFILE=connectors zenml service-connector register aws-federation-token --type aws --auth-method federation-token --auto-configure
⠸ Registering service connector 'aws-federation-token'...
Successfully registered service connector `aws-federation-token` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME       │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼──────────────────────┼────────────────┼───────────────────────┼────────────────┨
┃ 868b17d4-b950-4d89-a6c4-12e520e66610 │ aws-federation-token │ 🔶 aws         │ 🔶 aws-generic        │ 🤷 none listed ┃
┃                                      │                      │                │ 📦 s3-bucket          │                ┃
┃                                      │                      │                │ 🌀 kubernetes-cluster │                ┃
┃                                      │                      │                │ 🐳 docker-registry    │                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛

$ zenml service-connector describe aws-federation-token
Service connector 'aws-federation-token' of type 'aws' with id '868b17d4-b950-4d89-a6c4-12e520e66610' is owned by user 'default' and is 'private'.
                     'aws-federation-token' aws Service Connector Details                     
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                                   ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ ID               │ 868b17d4-b950-4d89-a6c4-12e520e66610                                    ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ NAME             │ aws-federation-token                                                    ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ TYPE             │ 🔶 aws                                                                  ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ AUTH METHOD      │ federation-token                                                        ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE TYPES   │ 🔶 aws-generic, 📦 s3-bucket, 🌀 kubernetes-cluster, 🐳 docker-registry ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE NAME    │ <multiple>                                                              ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ SECRET ID        │ 67a27e5e-d1cc-484c-968c-879be19c20b8                                    ┃
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
┃ CREATED_AT       │ 2023-05-18 17:05:06.289667                                              ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-05-18 17:05:06.289669                                              ┃
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

The following is just to show that clients receive temporary STS tokens instead of the AWS Secret Key configured in the connector (note the authentication method, expiration time and credentials):

```
$ zenml service-connector describe aws-federation-token --resource-type s3-bucket --resource-id zenfiles --client
Service connector 'aws-federation-token (s3-bucket | s3://zenfiles client)' of type 'aws' with id '868b17d4-b950-4d89-a6c4-12e520e66610' is owned by user 'default' and is 'private'.
    'aws-federation-token (s3-bucket | s3://zenfiles client)' aws Service     
                              Connector Details                               
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                   ┃
┠──────────────────┼─────────────────────────────────────────────────────────┨
┃ ID               │ 868b17d4-b950-4d89-a6c4-12e520e66610                    ┃
┠──────────────────┼─────────────────────────────────────────────────────────┨
┃ NAME             │ aws-federation-token (s3-bucket | s3://zenfiles client) ┃
┠──────────────────┼─────────────────────────────────────────────────────────┨
┃ TYPE             │ 🔶 aws                                                  ┃
┠──────────────────┼─────────────────────────────────────────────────────────┨
┃ AUTH METHOD      │ sts-token                                               ┃
┠──────────────────┼─────────────────────────────────────────────────────────┨
┃ RESOURCE TYPES   │ 📦 s3-bucket                                            ┃
┠──────────────────┼─────────────────────────────────────────────────────────┨
┃ RESOURCE NAME    │ s3://zenfiles                                           ┃
┠──────────────────┼─────────────────────────────────────────────────────────┨
┃ SECRET ID        │                                                         ┃
┠──────────────────┼─────────────────────────────────────────────────────────┨
┃ SESSION DURATION │ N/A                                                     ┃
┠──────────────────┼─────────────────────────────────────────────────────────┨
┃ EXPIRES IN       │ 11h59m57s                                               ┃
┠──────────────────┼─────────────────────────────────────────────────────────┨
┃ OWNER            │ default                                                 ┃
┠──────────────────┼─────────────────────────────────────────────────────────┨
┃ WORKSPACE        │ default                                                 ┃
┠──────────────────┼─────────────────────────────────────────────────────────┨
┃ SHARED           │ ➖                                                      ┃
┠──────────────────┼─────────────────────────────────────────────────────────┨
┃ CREATED_AT       │ 2023-05-18 17:07:00.196132                              ┃
┠──────────────────┼─────────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-05-18 17:07:00.196133                              ┃
┗━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
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

</details>

## Auto-configuration

The AWS Service Connector allows [auto-discovering and fetching credentials](service-connectors-guide.md#auto-configuration) and configuration set up [by the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html) during registration. The default AWS CLI profile is used, unless the AWS\_PROFILE environment points to a different profile.

<details>

<summary>Auto-configuration example</summary>

The following is an example of lifting AWS credentials granting access to the same set of AWS resources and services that the local AWS CLI is allowed to access. In this case, [the IAM role authentication method](aws-service-connector.md#aws-iam-role) was automatically detected:

```
$ AWS_PROFILE=zenml zenml service-connector register aws-auto --type aws --auto-configure
⠹ Registering service connector 'aws-auto'...
Successfully registered service connector `aws-auto` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────────────┼────────────────┨
┃ 9f3139fd-4726-421a-bc07-312d83f0c89e │ aws-auto       │ 🔶 aws         │ 🔶 aws-generic        │ 🤷 none listed ┃
┃                                      │                │                │ 📦 s3-bucket          │                ┃
┃                                      │                │                │ 🌀 kubernetes-cluster │                ┃
┃                                      │                │                │ 🐳 docker-registry    │                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛

$ zenml service-connector describe aws-auto 
Service connector 'aws-auto' of type 'aws' with id '9f3139fd-4726-421a-bc07-312d83f0c89e' is owned by user 'default' and is 'private'.
                           'aws-auto' aws Service Connector Details                           
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                                   ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ ID               │ 9f3139fd-4726-421a-bc07-312d83f0c89e                                    ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ NAME             │ aws-auto                                                                ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ TYPE             │ 🔶 aws                                                                  ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ AUTH METHOD      │ iam-role                                                                ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE TYPES   │ 🔶 aws-generic, 📦 s3-bucket, 🌀 kubernetes-cluster, 🐳 docker-registry ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE NAME    │ <multiple>                                                              ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ SECRET ID        │ 1f8b4a17-ff6f-4636-a42c-20bc749e1d8c                                    ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ SESSION DURATION │ 3600s                                                                   ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ EXPIRES IN       │ N/A                                                                     ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ OWNER            │ default                                                                 ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ WORKSPACE        │ default                                                                 ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ SHARED           │ ➖                                                                      ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ CREATED_AT       │ 2023-05-18 17:13:41.463877                                              ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-05-18 17:13:41.463879                                              ┃
┗━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                          Configuration                                           
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY              │ VALUE                                                                  ┃
┠───────────────────────┼────────────────────────────────────────────────────────────────────────┨
┃ region                │ us-east-1                                                              ┃
┠───────────────────────┼────────────────────────────────────────────────────────────────────────┨
┃ role_arn              │ arn:aws:iam::715803424590:role/OrganizationAccountRestrictedAccessRole ┃
┠───────────────────────┼────────────────────────────────────────────────────────────────────────┨
┃ aws_access_key_id     │ [HIDDEN]                                                               ┃
┠───────────────────────┼────────────────────────────────────────────────────────────────────────┨
┃ aws_secret_access_key │ [HIDDEN]                                                               ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

$ zenml service-connector verify aws-auto --resource-type s3-bucket
Service connector 'aws-auto' is correctly configured with valid credentials and has access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE │ RESOURCE NAMES                        ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────┼───────────────────────────────────────┨
┃ 9f3139fd-4726-421a-bc07-312d83f0c89e │ aws-auto       │ 🔶 aws         │ 📦 s3-bucket  │ s3://public-flavor-logos              ┃
┃                                      │                │                │               │ s3://zenfiles                         ┃
┃                                      │                │                │               │ s3://zenml-demos                      ┃
┃                                      │                │                │               │ s3://zenml-generative-chat            ┃
┃                                      │                │                │               │ s3://zenml-public-datasets            ┃
┃                                      │                │                │               │ s3://zenml-public-swagger-spec        ┃
┃                                      │                │                │               │ s3://zenml-sandbox-infra              ┃
┃                                      │                │                │               │ s3://zenml-terraform-ci               ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

$ zenml service-connector verify aws-auto --resource-type kubernetes-cluster
Service connector 'aws-auto' is correctly configured with valid credentials and has access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES   ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────────────┼──────────────────┨
┃ 9f3139fd-4726-421a-bc07-312d83f0c89e │ aws-auto       │ 🔶 aws         │ 🌀 kubernetes-cluster │ zenhacks-cluster ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━┛
```

</details>

## Local client provisioning

The local Kubernetes `kubectl` CLI and the Docker CLI can be [configured with credentials extracted from or generated by a compatible AWS Service Connector](service-connectors-guide.md#configure-local-clients). Please note that unlike the configuration made possible through the AWS CLI, the credentials issued by the AWS Service Connector have a short lifetime and will need to be regularly refreshed. This is a byproduct of implementing a high security profile. &#x20;

<details>

<summary>Local CLI configuration examples</summary>

The following shows an example of configuring the local Kubernetes CLI to access an EKS cluster reachable through an AWS Service Connector:

```
$ zenml service-connector list
┏━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━┯━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ ACTIVE │ NAME                         │ ID                                 │ TYPE          │ RESOURCE TYPES        │ RESOURCE NAME                  │ SHARED │ OWNER   │ EXPIRES IN  │ LABELS                   ┃
┠────────┼──────────────────────────────┼────────────────────────────────────┼───────────────┼───────────────────────┼────────────────────────────────┼────────┼─────────┼─────────────┼──────────────────────────┨
┃        │ aws-session-token            │ 3ae3e595-5cbc-446e-be64-e54e854e0e │ 🔶 aws        │ 🔶 aws-generic        │ <multiple>                     │ ➖     │ default │             │                          ┃
┃        │                              │ 3f                                 │               │ 📦 s3-bucket          │                                │        │         │             │                          ┃
┃        │                              │                                    │               │ 🌀 kubernetes-cluster │                                │        │         │             │                          ┃
┃        │                              │                                    │               │ 🐳 docker-registry    │                                │        │         │             │                          ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━┷━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━┛

$ zenml service-connector verify aws-session-token --resource-type kubernetes-cluster
Service connector 'aws-session-token' is correctly configured with valid credentials and has access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME    │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES   ┃
┠──────────────────────────────────────┼───────────────────┼────────────────┼───────────────────────┼──────────────────┨
┃ 3ae3e595-5cbc-446e-be64-e54e854e0e3f │ aws-session-token │ 🔶 aws         │ 🌀 kubernetes-cluster │ zenhacks-cluster ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━┛

$ zenml service-connector login aws-session-token --resource-type kubernetes-cluster --resource-id zenhacks-cluster
⠇ Attempting to configure local client using service connector 'aws-session-token'...
Cluster "arn:aws:eks:us-east-1:715803424590:cluster/zenhacks-cluster" set.
Context "arn:aws:eks:us-east-1:715803424590:cluster/zenhacks-cluster" modified.
Updated local kubeconfig with the cluster details. The current kubectl context was set to 'arn:aws:eks:us-east-1:715803424590:cluster/zenhacks-cluster'.
The 'aws-session-token' Kubernetes Service Connector connector was used to successfully configure the local Kubernetes cluster client/SDK.

$ kubectl cluster-info
Kubernetes control plane is running at https://A5F8F4142FB12DDCDE9F21F6E9B07A18.gr7.us-east-1.eks.amazonaws.com
CoreDNS is running at https://A5F8F4142FB12DDCDE9F21F6E9B07A18.gr7.us-east-1.eks.amazonaws.com/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy
```

A similar process is possible with ECR container registries:

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

{% hint style="info" %}
This Service Connector does not support configuring the local AWS CLI with credentials stored in or generated from the connector configuration. If this feature is useful to you or your organization, please let us know by messaging us in [Slack](https://zenml.io/slack-invite) or [creating an issue on GitHub](https://github.com/zenml-io/zenml/issues).
{% endhint %}

## Stack Components use

The [S3 Artifact Store Stack Component](../../../user-guide/component-guide/artifact-stores/s3.md) can be connected to a remote AWS S3 bucket through an AWS Service Connector.

The AWS Service Connector can also be used any Orchestrator or Model Deployer stack component flavor that relies on a Kubernetes clusters to manage workloads. This allows EKS Kubernetes container workloads to be managed without the need to configure and maintain explicit AWS or Kubernetes `kubectl` configuration contexts and credentials in the target environment and in the Stack Component.

Similarly, Container Registry Stack Components can be connected to an ECR Container Registry through an AWS Service Connector. This allows container images to be built and published to ECR container registries without the need to configure explicit AWS credentials in the target environment or the Stack Component.

## End-to-end examples

<details>

<summary>EKS Kubernetes Orchestrator, S3 Artifact Store and ECR Container Registry with a multi-type AWS Service Connector</summary>

This is an example of an end-to-end workflow involving Service Connectors that uses a single multi-type AWS Service Connector to give access to multiple resources for multiple Stack Components. A complete ZenML Stack is registered composed of the following Stack Components, all connected through the same Service Connector:

* a [Kubernetes Orchestrator](../../../user-guide/component-guide/orchestrators/kubernetes.md) connected to an EKS Kubernetes cluster
* an [S3 Artifact Store](../../../user-guide/component-guide/artifact-stores/s3.md) connected to an S3 bucket
* an [ECR Container Registry](../../../user-guide/component-guide/container-registries/aws.md) stack component connected to an ECR container registry
* a local [Image Builder](../../../user-guide/component-guide/image-builders/local.md)

As a last step, a simple pipeline is run on the resulting Stack.

1. [Configure the local AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html) with valid IAM user account credentials with a wide range of permissions (i.e. by running `aws configure`) and install ZenML integration prerequisites:

```
$ aws configure --profile connectors
AWS Access Key ID [None]: AKIAIOSFODNN7EXAMPLE
AWS Secret Access Key [None]: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
Default region name [None]: us-east-1
Default output format [None]: json

$ zenml integration install -y aws s3

```

2. Make sure the AWS Service Connector Type is available

```
$ zenml service-connector list-types --type aws
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━┯━━━━━━━┯━━━━━━━━┓
┃         NAME          │ TYPE   │ RESOURCE TYPES        │ AUTH METHODS     │ LOCAL │ REMOTE ┃
┠───────────────────────┼────────┼───────────────────────┼──────────────────┼───────┼────────┨
┃ AWS Service Connector │ 🔶 aws │ 🔶 aws-generic        │ implicit         │ ✅    │ ✅     ┃
┃                       │        │ 📦 s3-bucket          │ secret-key       │       │        ┃
┃                       │        │ 🌀 kubernetes-cluster │ sts-token        │       │        ┃
┃                       │        │ 🐳 docker-registry    │ iam-role         │       │        ┃
┃                       │        │                       │ session-token    │       │        ┃
┃                       │        │                       │ federation-token │       │        ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━┷━━━━━━━┷━━━━━━━━┛
```

3. Register a multi-type AWS Service Connector using auto-configuration

```
$ AWS_PROFILE=connectors zenml service-connector register aws-demo-multi --type aws --auto-configure
⠼ Registering service connector 'aws-demo-multi'...
Successfully registered service connector `aws-demo-multi` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────────────┼────────────────┨
┃ bf073e06-28ce-4a4a-8100-32e7cb99dced │ aws-demo-multi │ 🔶 aws         │ 🔶 aws-generic        │ 🤷 none listed ┃
┃                                      │                │                │ 📦 s3-bucket          │                ┃
┃                                      │                │                │ 🌀 kubernetes-cluster │                ┃
┃                                      │                │                │ 🐳 docker-registry    │                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛
```

**NOTE**: from this point forward, we don't need the local AWS CLI credentials or the local AWS CLI at all. The steps that follow can be run on any machine regardless of whether it has been configured and authorized to access the AWS platform or not.

4. find out which S3 buckets, ECR registries and EKS Kubernetes clusters we can gain access to. We'll use this information to configure the Stack Components in our minimal AWS stack: an S3 Artifact Store, a Kubernetes Orchestrator and an ECR Container Registry.

```
$ zenml service-connector list-resources --resource-type s3-bucket
TThe following 's3-bucket' resources can be accessed by service connectors configured in your workspace:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME      │ CONNECTOR TYPE │ RESOURCE TYPE │ RESOURCE NAMES                        ┃
┠──────────────────────────────────────┼─────────────────────┼────────────────┼───────────────┼───────────────────────────────────────┨
┃ bf073e06-28ce-4a4a-8100-32e7cb99dced │ aws-demo-multi      │ 🔶 aws         │ 📦 s3-bucket  │ s3://public-flavor-logos              ┃
┃                                      │                     │                │               │ s3://zenfiles                         ┃
┃                                      │                     │                │               │ s3://zenml-demos                      ┃
┃                                      │                     │                │               │ s3://zenml-generative-chat            ┃
┃                                      │                     │                │               │ s3://zenml-public-datasets            ┃
┃                                      │                     │                │               │ s3://zenml-public-swagger-spec        ┃
┃                                      │                     │                │               │ s3://zenml-terraform-ci               ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

$ zenml service-connector list-resources --resource-type kubernetes-cluster
The following 'kubernetes-cluster' resources can be accessed by service connectors configured in your workspace:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME        │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES      ┃
┠──────────────────────────────────────┼───────────────────────┼────────────────┼───────────────────────┼─────────────────────┨
┃ bf073e06-28ce-4a4a-8100-32e7cb99dced │ aws-demo-multi        │ 🔶 aws         │ 🌀 kubernetes-cluster │ zenhacks-cluster    ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━┛

$ zenml service-connector list-resources --resource-type docker-registry
The following 'docker-registry' resources can be accessed by service connectors configured in your workspace:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME     │ CONNECTOR TYPE │ RESOURCE TYPE      │ RESOURCE NAMES                                  ┃
┠──────────────────────────────────────┼────────────────────┼────────────────┼────────────────────┼─────────────────────────────────────────────────┨
┃ bf073e06-28ce-4a4a-8100-32e7cb99dced │ aws-demo-multi     │ 🔶 aws         │ 🐳 docker-registry │ 715803424590.dkr.ecr.us-east-1.amazonaws.com    ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

5. register and connect an S3 Artifact Store Stack Component to an S3 bucket:

```
$ zenml artifact-store register s3-zenfiles --flavor s3 --path=s3://zenfiles
Running with active workspace: 'default' (repository)
Running with active stack: 'default' (repository)
Successfully registered artifact_store `s3-zenfiles`.

$ zenml artifact-store connect s3-zenfiles --connector aws-demo-multi
Running with active workspace: 'default' (repository)
Running with active stack: 'default' (repository)
Successfully connected artifact store `s3-zenfiles` to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────┼────────────────┨
┃ bf073e06-28ce-4a4a-8100-32e7cb99dced │ aws-demo-multi │ 🔶 aws         │ 📦 s3-bucket  │ s3://zenfiles  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛
```

6. register and connect a Kubernetes Orchestrator Stack Component to an EKS cluster:

```
$ zenml orchestrator register eks-zenml-zenhacks --flavor kubernetes --synchronous=true --kubernetes_namespace=zenml-workloads
Running with active workspace: 'default' (repository)
Running with active stack: 'default' (repository)
Successfully registered orchestrator `eks-zenml-zenhacks`.

$ zenml orchestrator connect eks-zenml-zenhacks --connector aws-demo-multi
Running with active workspace: 'default' (repository)
Running with active stack: 'default' (repository)
Successfully connected orchestrator `eks-zenml-zenhacks` to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES   ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────────────┼──────────────────┨
┃ bf073e06-28ce-4a4a-8100-32e7cb99dced │ aws-demo-multi │ 🔶 aws         │ 🌀 kubernetes-cluster │ zenhacks-cluster ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━┛
```

7. Register and connect an EC GCP Container Registry Stack Component to an ECR container registry:

```
$ zenml container-registry register ecr-us-east-1 --flavor aws --uri=715803424590.dkr.ecr.us-east-1.amazonaws.com
Running with active workspace: 'default' (repository)
Running with active stack: 'default' (repository)
Successfully registered container_registry `ecr-us-east-1`.

$ zenml container-registry connect ecr-us-east-1 --connector aws-demo-multi
Running with active workspace: 'default' (repository)
Running with active stack: 'default' (repository)
Successfully connected container registry `ecr-us-east-1` to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE      │ RESOURCE NAMES                               ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼────────────────────┼──────────────────────────────────────────────┨
┃ bf073e06-28ce-4a4a-8100-32e7cb99dced │ aws-demo-multi │ 🔶 aws         │ 🐳 docker-registry │ 715803424590.dkr.ecr.us-east-1.amazonaws.com ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

8. Combine all Stack Components together into a Stack and set it as active (also throw in a local Image Builder for completion):

```
$ zenml image-builder register local --flavor local
Running with active workspace: 'default' (global)
Running with active stack: 'default' (global)
Successfully registered image_builder `local`.

$ zenml stack register aws-demo -a s3-zenfiles -o eks-zenml-zenhacks -c ecr-us-east-1 -i local --set
Connected to the ZenML server: 'https://stefan.develaws.zenml.io'
Running with active workspace: 'default' (repository)
Stack 'aws-demo' successfully registered!
Active repository stack set to:'aws-demo'
```

9. Finally, run a simple pipeline to prove that everything works as expected. We'll use the simplest pipelines possible for this example:

```python
from zenml import pipeline, step


@step
def step_1() -> str:
    """Returns the `world` string."""
    return "world"


@step(enable_cache=False)
def step_2(input_one: str, input_two: str) -> None:
    """Combines the two strings at its input and prints them."""
    combined_str = f"{input_one} {input_two}"
    print(combined_str)


@pipeline
def my_pipeline():
    output_step_one = step_1()
    step_2(input_one="hello", input_two=output_step_one)


if __name__ == "__main__":
    my_pipeline()
```

Saving that to a `run.py` file and running it gives us:

```
$ python run.py 
Reusing registered pipeline simple_pipeline (version: 1).
Building Docker image(s) for pipeline simple_pipeline.
Building Docker image 715803424590.dkr.ecr.us-east-1.amazonaws.com/zenml:simple_pipeline-orchestrator.
- Including user-defined requirements: boto3==1.26.76
- Including integration requirements: boto3, kubernetes==18.20.0, s3fs>2022.3.0,<=2023.4.0, sagemaker==2.117.0
No .dockerignore found, including all files inside build context.
Step 1/10 : FROM zenmldocker/zenml:0.39.1-py3.8
Step 2/10 : WORKDIR /app
Step 3/10 : COPY .zenml_user_requirements .
Step 4/10 : RUN pip install --default-timeout=60 --no-cache-dir  -r .zenml_user_requirements
Step 5/10 : COPY .zenml_integration_requirements .
Step 6/10 : RUN pip install --default-timeout=60 --no-cache-dir  -r .zenml_integration_requirements
Step 7/10 : ENV ZENML_ENABLE_REPO_INIT_WARNINGS=False
Step 8/10 : ENV ZENML_CONFIG_PATH=/app/.zenconfig
Step 9/10 : COPY . .
Step 10/10 : RUN chmod -R a+rw .
Amazon ECR requires you to create a repository before you can push an image to it. ZenML is trying to push the image 715803424590.dkr.ecr.us-east-1.amazonaws.com/zenml:simple_pipeline-orchestrator but could only detect the following repositories: []. We will try to push anyway, but in case it fails you need to create a repository named zenml.
Pushing Docker image 715803424590.dkr.ecr.us-east-1.amazonaws.com/zenml:simple_pipeline-orchestrator.
Finished pushing Docker image.
Finished building Docker image(s).
Running pipeline simple_pipeline on stack aws-demo (caching disabled)
Waiting for Kubernetes orchestrator pod...
Kubernetes orchestrator pod started.
Waiting for pod of step step_1 to start...
Step step_1 has started.
Step step_1 has finished in 0.390s.
Pod of step step_1 completed.
Waiting for pod of step step_2 to start...
Step step_2 has started.
Hello World!
Step step_2 has finished in 2.364s.
Pod of step step_2 completed.
Orchestration pod completed.
Dashboard URL: https://stefan.develaws.zenml.io/workspaces/default/pipelines/be5adfe9-45af-4709-a8eb-9522c01640ce/runs
```

</details>

