---
description: >-
  Configuring AWS Service Connectors to connect ZenML to AWS resources like S3
  buckets, EKS Kubernetes clusters and ECR container registries.
---

# AWS Service Connector

The ZenML AWS Service Connector facilitates the authentication and access to managed AWS services and resources. These encompass a range of resources, including S3 buckets, ECR container repositories, and EKS clusters. The connector provides support for various authentication methods, including explicit long-lived AWS secret keys, IAM roles, short-lived STS tokens, and implicit authentication.

To ensure heightened security measures, this connector also enables [the generation of temporary STS security tokens that are scoped down to the minimum permissions necessary](best-security-practices.md#generating-temporary-and-down-scoped-credentials) for accessing the intended resource. Furthermore, it includes [automatic configuration and detection of credentials locally configured through the AWS CLI](service-connectors-guide.md#auto-configuration).

This connector serves as a general means of accessing any AWS service by issuing pre-authenticated boto3 sessions. Additionally, the connector can handle specialized authentication for S3, Docker, and Kubernetes Python clients. It also allows for the configuration of local Docker and Kubernetes CLIs.

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

{% hint style="info" %}
This service connector will not be able to work if [Multi-Factor Authentication (MFA)](https://docs.aws.amazon.com/IAM/latest/UserGuide/id\_credentials\_mfa\_enable\_cliapi.html) is enabled on the role used by the AWS CLI. When MFA is enabled, the AWS CLI generates temporary credentials that are valid for a limited time. These temporary credentials cannot be used by the ZenML AWS Service Connector, as it requires long-lived credentials to authenticate and access AWS resources.

To use the AWS Service Connector with ZenML, you will need to use a different AWS CLI profile that does not have MFA enabled. You can do this by setting the `AWS_PROFILE` environment variable to the name of the profile you want to use before running the ZenML CLI commands.
{% endhint %}

## Prerequisites

The AWS Service Connector is part of the AWS ZenML integration. You can either install the entire integration or use a PyPI extra to install it independently of the integration:

* `pip install "zenml[connectors-aws]"` installs only prerequisites for the AWS Service Connector Type
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

This generic AWS resource type is meant to be used with Stack Components that are not represented by other, more specific resource types, like S3 buckets, Kubernetes clusters, or Docker registries. It should be accompanied by a matching set of AWS permissions that allow access to the set of remote resources required by the client(s).

The resource name represents the AWS region that the connector is authorized to access.

### S3 bucket

Allows users to connect to S3 buckets. When used by connector consumers, they are provided a pre-configured boto3 S3 client instance.

The configured credentials must have at least the following [AWS IAM permissions](https://docs.aws.amazon.com/IAM/latest/UserGuide/access\_policies.html) associated with [the ARNs of S3 buckets ](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-arn-format.html)that the connector will be allowed to access (e.g. `arn:aws:s3:::*` and `arn:aws:s3:::*/*` represent all the available S3 buckets).

* `s3:ListBucket`
* `s3:GetObject`
* `s3:PutObject`
* `s3:DeleteObject`
* `s3:ListAllMyBuckets`

{% hint style="info" %}
If you are using the [AWS IAM role](aws-service-connector.md#aws-iam-role), [Session Token](aws-service-connector.md#aws-session-token), or [Federation Token](aws-service-connector.md#aws-federation-token) authentication methods, you don't have to worry too much about restricting the permissions of the AWS credentials that you use to access the AWS cloud resources. These authentication methods already support [automatically generating temporary tokens](best-security-practices.md#generating-temporary-and-down-scoped-credentials) with permissions down-scoped to the minimum required to access the target resource.
{% endhint %}

If set, the resource name must identify an S3 bucket using one of the following formats:

* S3 bucket URI (canonical resource name): `s3://{bucket-name}`
* S3 bucket ARN: `arn:aws:s3:::{bucket-name}`
* S3 bucket name: `{bucket-name}`

### EKS Kubernetes cluster

Allows users to access an EKS cluster as a standard Kubernetes cluster resource. When used by Stack Components, they are provided a pre-authenticated Python Kubernetes client instance.

The configured credentials must have at least the following [AWS IAM permissions](https://docs.aws.amazon.com/IAM/latest/UserGuide/access\_policies.html) associated with the [ARNs of EKS clusters](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference-arns.html) that the connector will be allowed to access (e.g. `arn:aws:eks:{region_id}:{project_id}:cluster/*` represents all the EKS clusters available in the target AWS region).

* `eks:ListClusters`
* `eks:DescribeCluster`

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

* `ecr:DescribeRegistry`
* `ecr:DescribeRepositories`
* `ecr:ListRepositories`
* `ecr:BatchGetImage`
* `ecr:DescribeImages`
* `ecr:BatchCheckLayerAvailability`
* `ecr:GetDownloadUrlForLayer`
* `ecr:InitiateLayerUpload`
* `ecr:UploadLayerPart`
* `ecr:CompleteLayerUpload`
* `ecr:PutImage`
* `ecr:GetAuthorizationToken`

{% hint style="info" %}
If you are using the [AWS IAM role](aws-service-connector.md#aws-iam-role), [Session Token](aws-service-connector.md#aws-session-token), or [Federation Token](aws-service-connector.md#aws-federation-token) authentication methods, you don't have to worry too much about restricting the permissions of the AWS credentials that you use to access the AWS cloud resources. These authentication methods already support [automatically generating temporary tokens](best-security-practices.md#generating-temporary-and-down-scoped-credentials) with permissions down-scoped to the minimum required to access the target resource.
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

{% hint style="warning" %}
This method may constitute a security risk, because it can give users access to the same cloud resources and services that the ZenML Server itself is configured to access. For this reason, all implicit authentication methods are disabled by default and need to be explicitly enabled by setting the `ZENML_ENABLE_IMPLICIT_AUTH_METHODS` environment variable or the helm chart `enableImplicitAuthMethods` configuration option to `true` in the ZenML deployment.
{% endhint %}

This authentication method doesn't require any credentials to be explicitly configured. It automatically discovers and uses credentials from one of the following sources:

* environment variables (AWS\_ACCESS\_KEY\_ID, AWS\_SECRET\_ACCESS\_KEY, AWS\_SESSION\_TOKEN, AWS\_DEFAULT\_REGION)
* local configuration files [set up through the AWS CLI ](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)(\~/aws/credentials, \~/.aws/config)
* IAM roles for Amazon EC2, ECS, EKS, Lambda, etc. Only works when running the ZenML server on an AWS resource with an IAM role attached to it.

This is the quickest and easiest way to authenticate to AWS services. However, the results depend on how ZenML is deployed and the environment where it is used and is thus not fully reproducible:

* when used with the default local ZenML deployment or a local ZenML server, the credentials are the same as those used by the AWS CLI or extracted from local environment variables
* when connected to a ZenML server, this method only works if the ZenML server is deployed in AWS and will use the IAM role attached to the AWS resource where the ZenML server is running (e.g. an EKS cluster). The IAM role permissions may need to be adjusted to allow listing and accessing/describing the AWS resources that the connector is configured to access.

An IAM role may optionally be specified to be assumed by the connector on top of the implicit credentials. This is only possible when the implicit credentials have permissions to assume the target IAM role. Configuring an IAM role has all the advantages of the [AWS IAM Role](aws-service-connector.md#aws-iam-role) authentication method plus the added benefit of not requiring any explicit credentials to be configured and stored:

* the connector will [generate temporary STS tokens](best-security-practices.md#generating-temporary-and-down-scoped-credentials) upon request by [calling the AssumeRole STS API](https://docs.aws.amazon.com/IAM/latest/UserGuide/id\_credentials\_temp\_request.html#api\_assumerole).
* allows implementing [a two layer authentication scheme](best-security-practices.md#impersonating-accounts-and-assuming-roles) that keeps the set of permissions associated with implicit credentials down to the bare minimum and grants permissions to the privilege-bearing IAM role instead.
* one or more optional [IAM session policies](https://docs.aws.amazon.com/IAM/latest/UserGuide/access\_policies.html#policies\_session) may also be configured to further restrict the permissions of the generated STS tokens. If not specified, IAM session policies are automatically configured for the generated STS tokens [to restrict them to the minimum set of permissions required to access the target resource](best-security-practices.md#generating-temporary-and-down-scoped-credentials). Refer to the documentation for each supported Resource Type for the complete list of AWS permissions automatically granted to the generated STS tokens.
* the default expiration period for generated STS tokens is 1 hour with a minimum of 15 minutes up to the maximum session duration setting configured for the IAM role (default is 1 hour). If you need longer-lived tokens, you can configure the IAM role to use a higher maximum expiration value (up to 12 hours) or use the AWS Federation Token or AWS Session Token authentication methods.

Note that the discovered credentials inherit the full set of permissions of the local AWS client configuration, environment variables, or remote AWS IAM role. Depending on the extent of those permissions, this authentication instead method might not be recommended for production use, as it can lead to accidental privilege escalation. It is recommended to also configure an IAM role when using the implicit authentication method, or to use the [AWS IAM Role](aws-service-connector.md#aws-iam-role), [AWS Session Token](aws-service-connector.md#aws-session-token), or [AWS Federation Token](aws-service-connector.md#aws-federation-token) authentication methods instead to limit the validity and/or permissions of the credentials being issued to connector clients.

{% hint style="info" %}
If you need to access an EKS Kubernetes cluster with this authentication method, please be advised that the EKS cluster's `aws-auth` ConfigMap may need to be manually configured to allow authentication with the implicit IAM user or role picked up by the Service Connector. For more information, [see this documentation](https://docs.aws.amazon.com/eks/latest/userguide/add-user-role.html).
{% endhint %}

An AWS region is required and the connector may only be used to access AWS resources in the specified region.

<details>

<summary>Example configuration</summary>

The following assumes the local AWS CLI has a `connectors` AWS CLI profile already configured with credentials:

```sh
AWS_PROFILE=connectors zenml service-connector register aws-implicit --type aws --auth-method implicit --region=us-east-1
```

{% code title="Example Command Output" %}
```
⠸ Registering service connector 'aws-implicit'...
Successfully registered service connector `aws-implicit` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃     RESOURCE TYPE     │ RESOURCE NAMES                               ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃    🔶 aws-generic     │ us-east-1                                    ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃     📦 s3-bucket      │ s3://zenfiles                                ┃
┃                       │ s3://zenml-demos                             ┃
┃                       │ s3://zenml-generative-chat                   ┃
┃                       │ s3://zenml-public-datasets                   ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃ 🌀 kubernetes-cluster │ zenhacks-cluster                             ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃  🐳 docker-registry   │ 715803424590.dkr.ecr.us-east-1.amazonaws.com ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

No credentials are stored with the Service Connector:

```sh
zenml service-connector describe aws-implicit 
```

{% code title="Example Command Output" %}
```
Service connector 'aws-implicit' of type 'aws' with id 'e3853748-34a0-4d78-8006-00422ad32884' is owned by user 'default' and is 'private'.
                         'aws-implicit' aws Service Connector Details                         
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                                   ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ ID               │ 9a810521-ef41-4e45-bb48-8569c5943dc6                                    ┃
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
┃ CREATED_AT       │ 2023-06-19 18:08:37.969928                                              ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-06-19 18:08:37.969930                                              ┃
┗━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
     Configuration      
┏━━━━━━━━━━┯━━━━━━━━━━━┓
┃ PROPERTY │ VALUE     ┃
┠──────────┼───────────┨
┃ region   │ us-east-1 ┃
┗━━━━━━━━━━┷━━━━━━━━━━━┛
```
{% endcode %}

Verifying access to resources (note the `AWS_PROFILE` environment points to the same AWS CLI profile used during registration, but may yield different results with a different profile, which is why this method is not suitable for reproducible results):

```sh
AWS_PROFILE=connectors zenml service-connector verify aws-implicit --resource-type s3-bucket
```

{% code title="Example Command Output" %}
```
⠸ Verifying service connector 'aws-implicit'...
Service connector 'aws-implicit' is correctly configured with valid credentials and has access to the following resources:
┏━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ RESOURCE TYPE │ RESOURCE NAMES                        ┃
┠───────────────┼───────────────────────────────────────┨
┃ 📦 s3-bucket  │ s3://zenfiles                         ┃
┃               │ s3://zenml-demos                      ┃
┃               │ s3://zenml-generative-chat            ┃
┃               │ s3://zenml-public-datasets            ┃
┗━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

```sh
zenml service-connector verify aws-implicit --resource-type s3-bucket
```

{% code title="Example Command Output" %}
```
⠸ Verifying service connector 'aws-implicit'...
Service connector 'aws-implicit' is correctly configured with valid credentials and has access to the following resources:
┏━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ RESOURCE TYPE │ RESOURCE NAMES                                 ┃
┠───────────────┼────────────────────────────────────────────────┨
┃ 📦 s3-bucket  │ s3://sagemaker-studio-907999144431-m11qlsdyqr8 ┃
┃               │ s3://sagemaker-studio-d8a14tvjsmb              ┃
┗━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

Depending on the environment, clients are issued either temporary STS tokens or long-lived credentials, which is a reason why this method isn't well suited for production:

```sh
AWS_PROFILE=zenml zenml service-connector describe aws-implicit --resource-type s3-bucket --resource-id zenfiles --client
```

{% code title="Example Command Output" %}
```
INFO:botocore.credentials:Found credentials in shared credentials file: ~/.aws/credentials
Service connector 'aws-implicit (s3-bucket | s3://zenfiles client)' of type 'aws' with id 'e3853748-34a0-4d78-8006-00422ad32884' is owned by user 'default' and is 'private'.
    'aws-implicit (s3-bucket | s3://zenfiles client)' aws Service     
                          Connector Details                           
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                           ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ ID               │ 9a810521-ef41-4e45-bb48-8569c5943dc6            ┃
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
┃ CREATED_AT       │ 2023-06-19 18:13:34.146659                      ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-06-19 18:13:34.146664                      ┃
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
{% endcode %}

```sh
zenml service-connector describe aws-implicit --resource-type s3-bucket --resource-id s3://sagemaker-studio-d8a14tvjsmb --client
```

{% code title="Example Command Output" %}
```
INFO:botocore.credentials:Found credentials in shared credentials file: ~/.aws/credentials
Service connector 'aws-implicit (s3-bucket | s3://sagemaker-studio-d8a14tvjsmb client)' of type 'aws' with id 'e3853748-34a0-4d78-8006-00422ad32884' is owned by user 'default' and is 'private'.
    'aws-implicit (s3-bucket | s3://sagemaker-studio-d8a14tvjsmb client)' aws Service     
                                    Connector Details                                     
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                               ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ ID               │ 9a810521-ef41-4e45-bb48-8569c5943dc6                                ┃
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
┃ CREATED_AT       │ 2023-06-19 18:12:42.066053                                          ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-06-19 18:12:42.066055                                          ┃
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
{% endcode %}

</details>

### AWS Secret Key

[Long-lived AWS credentials](best-security-practices.md#long-lived-credentials-api-keys-account-keys) consisting of an AWS access key ID and secret access key associated with an AWS IAM user or AWS account root user (not recommended).

This method is preferred during development and testing due to its simplicity and ease of use. It is not recommended as a direct authentication method for production use cases because the clients have direct access to long-lived credentials and are granted the full set of permissions of the IAM user or AWS account root user associated with the credentials. For production, it is recommended to use [the AWS IAM Role](aws-service-connector.md#aws-iam-role), [AWS Session Token](aws-service-connector.md#aws-session-token), or [AWS Federation Token](aws-service-connector.md#aws-federation-token) authentication method instead.

An AWS region is required and the connector may only be used to access AWS resources in the specified region.

If you already have the local AWS CLI set up with these credentials, they will be automatically picked up when auto-configuration is used (see the example below).

<details>

<summary>Example auto-configuration</summary>

The following assumes the local AWS CLI has a `connectors` AWS CLI profile configured with an AWS Secret Key. We need to force the ZenML CLI to use the Secret Key authentication by passing the `--auth-method secret-key` option, otherwise it would automatically use [the AWS Session Token authentication method](aws-service-connector.md#aws-session-token) as an extra precaution:

```sh
AWS_PROFILE=connectors zenml service-connector register aws-secret-key --type aws --auth-method secret-key --auto-configure
```

{% code title="Example Command Output" %}
```
⠸ Registering service connector 'aws-secret-key'...
Successfully registered service connector `aws-secret-key` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃     RESOURCE TYPE     │ RESOURCE NAMES                               ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃    🔶 aws-generic     │ us-east-1                                    ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃     📦 s3-bucket      │ s3://zenfiles                                ┃
┃                       │ s3://zenml-demos                             ┃
┃                       │ s3://zenml-generative-chat                   ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃ 🌀 kubernetes-cluster │ zenhacks-cluster                             ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃  🐳 docker-registry   │ 715803424590.dkr.ecr.us-east-1.amazonaws.com ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

The AWS Secret Key was lifted up from the local host:

```sh
zenml service-connector describe aws-secret-key
```

{% code title="Example Command Output" %}
```
Service connector 'aws-secret-key' of type 'aws' with id 'a1b07c5a-13af-4571-8e63-57a809c85790' is owned by user 'default' and is 'private'.
                        'aws-secret-key' aws Service Connector Details                        
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                                   ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ ID               │ 37c97fa0-fa47-4d55-9970-e2aa6e1b50cf                                    ┃
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
┃ SECRET ID        │ b889efe1-0e23-4e2d-afc3-bdd785ee2d80                                    ┃
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
┃ CREATED_AT       │ 2023-06-19 19:23:39.982950                                              ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-06-19 19:23:39.982952                                              ┃
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
{% endcode %}

</details>

### AWS STS Token

Uses [temporary STS tokens](best-security-practices.md#short-lived-credentials) explicitly configured by the user or auto-configured from a local environment.

This method has the major limitation that the user must regularly generate new tokens and update the connector configuration as STS tokens expire. On the other hand, this method is ideal in cases where the connector only needs to be used for a short period of time, such as sharing access temporarily with someone else in your team.

Using other authentication methods like [IAM role](aws-service-connector.md#aws-iam-role), [Session Token](aws-service-connector.md#aws-session-token), or [Federation Token](aws-service-connector.md#aws-federation-token) will automatically generate and refresh STS tokens for clients upon request.

An AWS region is required and the connector may only be used to access AWS resources in the specified region.

<details>

<summary>Example auto-configuration</summary>

Fetching STS tokens from the local AWS CLI is possible if the AWS CLI is already configured with valid credentials. In our example, the `connectors` AWS CLI profile is configured with an IAM user Secret Key. We need to force the ZenML CLI to use the STS token authentication by passing the `--auth-method sts-token` option, otherwise it would automatically use [the session token authentication method](aws-service-connector.md#aws-session-token):

```sh
AWS_PROFILE=connectors zenml service-connector register aws-sts-token --type aws --auto-configure --auth-method sts-token
```

{% code title="Example Command Output" %}
```
⠸ Registering service connector 'aws-sts-token'...
Successfully registered service connector `aws-sts-token` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃     RESOURCE TYPE     │ RESOURCE NAMES                               ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃    🔶 aws-generic     │ us-east-1                                    ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃     📦 s3-bucket      │ s3://zenfiles                                ┃
┃                       │ s3://zenml-demos                             ┃
┃                       │ s3://zenml-generative-chat                   ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃ 🌀 kubernetes-cluster │ zenhacks-cluster                             ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃  🐳 docker-registry   │ 715803424590.dkr.ecr.us-east-1.amazonaws.com ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

The Service Connector configuration shows that the connector is configured with an STS token:

```sh
zenml service-connector describe aws-sts-token
```

{% code title="Example Command Output" %}
```
Service connector 'aws-sts-token' of type 'aws' with id '63e14350-6719-4255-b3f5-0539c8f7c303' is owned by user 'default' and is 'private'.
                        'aws-sts-token' aws Service Connector Details                         
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                                   ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ ID               │ a05ef4ef-92cb-46b2-8a3a-a48535adccaf                                    ┃
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
┃ SECRET ID        │ bffd79c7-6d76-483b-9001-e9dda4e865ae                                    ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ SESSION DURATION │ N/A                                                                     ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ EXPIRES IN       │ 11h58m24s                                                               ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ OWNER            │ default                                                                 ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ WORKSPACE        │ default                                                                 ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ SHARED           │ ➖                                                                      ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ CREATED_AT       │ 2023-06-19 19:25:40.278681                                              ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-06-19 19:25:40.278684                                              ┃
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
{% endcode %}

Note the temporary nature of the Service Connector. It will become unusable in 12 hours:

```sh
zenml service-connector list --name aws-sts-token
```

{% code title="Example Command Output" %}
```
┏━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━┓
┃ ACTIVE │ NAME          │ ID                                   │ TYPE   │ RESOURCE TYPES        │ RESOURCE NAME │ SHARED │ OWNER   │ EXPIRES IN │ LABELS ┃
┠────────┼───────────────┼──────────────────────────────────────┼────────┼───────────────────────┼───────────────┼────────┼─────────┼────────────┼────────┨
┃        │ aws-sts-token │ a05ef4ef-92cb-46b2-8a3a-a48535adccaf │ 🔶 aws │ 🔶 aws-generic        │ <multiple>    │ ➖     │ default │ 11h57m51s  │        ┃
┃        │               │                                      │        │ 📦 s3-bucket          │               │        │         │            │        ┃
┃        │               │                                      │        │ 🌀 kubernetes-cluster │               │        │         │            │        ┃
┃        │               │                                      │        │ 🐳 docker-registry    │               │        │         │            │        ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━┛
```
{% endcode %}

</details>

### AWS IAM Role

Generates [temporary STS credentials](best-security-practices.md#impersonating-accounts-and-assuming-roles) by assuming an AWS IAM role.

This authentication method still requires credentials to be explicitly configured. If your ZenML server is running in AWS and you're looking for an alternative that uses implicit credentials while at the same time benefits from all the security advantages of assuming an IAM role, you should [use the implicit authentication method with a configured IAM role](aws-service-connector.md#implicit-authentication) instead.

The connector needs to be configured with the IAM role to be assumed accompanied by an AWS secret key associated with an IAM user or an STS token associated with another IAM role. The IAM user or IAM role must have permission to assume the target IAM role. The connector will [generate temporary STS tokens](best-security-practices.md#generating-temporary-and-down-scoped-credentials) upon request by [calling the AssumeRole STS API](https://docs.aws.amazon.com/IAM/latest/UserGuide/id\_credentials\_temp\_request.html#api\_assumerole).

[The best practice implemented with this authentication scheme](best-security-practices.md#impersonating-accounts-and-assuming-roles) is to keep the set of permissions associated with the primary IAM user or IAM role down to the bare minimum and grant permissions to the privilege-bearing IAM role instead.

An AWS region is required and the connector may only be used to access AWS resources in the specified region.

One or more optional [IAM session policies](https://docs.aws.amazon.com/IAM/latest/UserGuide/access\_policies.html#policies\_session) may also be configured to further restrict the permissions of the generated STS tokens. If not specified, IAM session policies are automatically configured for the generated STS tokens [to restrict them to the minimum set of permissions required to access the target resource](best-security-practices.md#generating-temporary-and-down-scoped-credentials). Refer to the documentation for each supported Resource Type for the complete list of AWS permissions automatically granted to the generated STS tokens.

The default expiration period for generated STS tokens is 1 hour with a minimum of 15 minutes up to the maximum session duration setting configured for the IAM role (default is 1 hour). If you need longer-lived tokens, you can configure the IAM role to use a higher maximum expiration value (up to 12 hours) or use the AWS Federation Token or AWS Session Token authentication methods.

For more information on IAM roles and the AssumeRole AWS API, see [the official AWS documentation on the subject](https://docs.aws.amazon.com/IAM/latest/UserGuide/id\_credentials\_temp\_request.html#api\_assumerole).

For more information about the difference between this method and the AWS Federation Token authentication method, [consult this AWS documentation page](https://aws.amazon.com/blogs/security/understanding-the-api-options-for-securely-delegating-access-to-your-aws-account/).

<details>

<summary>Example auto-configuration</summary>

The following assumes the local AWS CLI has a `zenml` AWS CLI profile already configured with an AWS Secret Key and an IAM role to be assumed:

```sh
AWS_PROFILE=zenml zenml service-connector register aws-iam-role --type aws --auto-configure
```

{% code title="Example Command Output" %}
```
⠸ Registering service connector 'aws-iam-role'...
Successfully registered service connector `aws-iam-role` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃     RESOURCE TYPE     │ RESOURCE NAMES                               ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃    🔶 aws-generic     │ us-east-1                                    ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃     📦 s3-bucket      │ s3://zenfiles                                ┃
┃                       │ s3://zenml-demos                             ┃
┃                       │ s3://zenml-generative-chat                   ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃ 🌀 kubernetes-cluster │ zenhacks-cluster                             ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃  🐳 docker-registry   │ 715803424590.dkr.ecr.us-east-1.amazonaws.com ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

The Service Connector configuration shows an IAM role and long-lived credentials:

```sh
zenml service-connector describe aws-iam-role
```

{% code title="Example Command Output" %}
```
Service connector 'aws-iam-role' of type 'aws' with id '8e499202-57fd-478e-9d2f-323d76d8d211' is owned by user 'default' and is 'private'.
                         'aws-iam-role' aws Service Connector Details                         
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                                   ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ ID               │ 2b99de14-6241-4194-9608-b9d478e1bcfc                                    ┃
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
┃ SECRET ID        │ 87795fdd-b70e-4895-b0dd-8bca5fd4d10e                                    ┃
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
┃ CREATED_AT       │ 2023-06-19 19:28:31.679843                                              ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-06-19 19:28:31.679848                                              ┃
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
{% endcode %}

However, clients receive temporary STS tokens instead of the AWS Secret Key configured in the connector (note the authentication method, expiration time, and credentials):

```sh
zenml service-connector describe aws-iam-role --resource-type s3-bucket --resource-id zenfiles --client
```

{% code title="Example Command Output" %}
```
Service connector 'aws-iam-role (s3-bucket | s3://zenfiles client)' of type 'aws' with id '8e499202-57fd-478e-9d2f-323d76d8d211' is owned by user 'default' and is 'private'.
    'aws-iam-role (s3-bucket | s3://zenfiles client)' aws Service     
                          Connector Details                           
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                           ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ ID               │ 2b99de14-6241-4194-9608-b9d478e1bcfc            ┃
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
┃ EXPIRES IN       │ 59m56s                                          ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ OWNER            │ default                                         ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ WORKSPACE        │ default                                         ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ SHARED           │ ➖                                              ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ CREATED_AT       │ 2023-06-19 19:30:51.462445                      ┃
┠──────────────────┼─────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-06-19 19:30:51.462449                      ┃
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
{% endcode %}

</details>

### AWS Session Token

Generates [temporary session STS tokens](best-security-practices.md#generating-temporary-and-down-scoped-credentials) for IAM users.

The connector needs to be configured with an AWS secret key associated with an IAM user or AWS account root user (not recommended). The connector will [generate temporary STS tokens](best-security-practices.md#generating-temporary-and-down-scoped-credentials) upon request by calling [the GetSessionToken STS API](https://docs.aws.amazon.com/IAM/latest/UserGuide/id\_credentials\_temp\_request.html#api\_getsessiontoken).

The STS tokens have an expiration period longer than those issued through the [AWS IAM Role authentication method](aws-service-connector.md#aws-iam-role) and are more suitable for long-running processes that cannot automatically re-generate credentials upon expiration.

An AWS region is required and the connector may only be used to access AWS resources in the specified region.

The default expiration period for generated STS tokens is 12 hours with a minimum of 15 minutes and a maximum of 36 hours. Temporary credentials obtained by using the AWS account root user credentials (not recommended) have a maximum duration of 1 hour.

As a precaution, when long-lived credentials (i.e. AWS Secret Keys) are detected on your environment by the Service Connector during auto-configuration, this authentication method is automatically chosen instead of the AWS [Secret Key authentication method](aws-service-connector.md#aws-secret-key) alternative.

Generated STS tokens inherit the full set of permissions of the IAM user or AWS account root user that is calling the GetSessionToken API. Depending on your security needs, this may not be suitable for production use, as it can lead to accidental privilege escalation. Instead, it is recommended to use the AWS Federation Token or [AWS IAM Role authentication](aws-service-connector.md#aws-iam-role) methods to restrict the permissions of the generated STS tokens.

For more information on session tokens and the GetSessionToken AWS API, see [the official AWS documentation on the subject](https://docs.aws.amazon.com/IAM/latest/UserGuide/id\_credentials\_temp\_request.html#api\_getsessiontoken).

<details>

<summary>Example auto-configuration</summary>

The following assumes the local AWS CLI has a `connectors` AWS CLI profile already configured with an AWS Secret Key:

```sh
AWS_PROFILE=connectors zenml service-connector register aws-session-token --type aws --auth-method session-token --auto-configure
```

{% code title="Example Command Output" %}
```
⠸ Registering service connector 'aws-session-token'...
Successfully registered service connector `aws-session-token` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃     RESOURCE TYPE     │ RESOURCE NAMES                               ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃    🔶 aws-generic     │ us-east-1                                    ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃     📦 s3-bucket      │ s3://zenfiles                                ┃
┃                       │ s3://zenml-demos                             ┃
┃                       │ s3://zenml-generative-chat                   ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃ 🌀 kubernetes-cluster │ zenhacks-cluster                             ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃  🐳 docker-registry   │ 715803424590.dkr.ecr.us-east-1.amazonaws.com ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

The Service Connector configuration shows long-lived credentials were lifted from the local environment and the AWS Session Token authentication method was configured:

```sh
zenml service-connector describe aws-session-token
```

{% code title="Example Command Output" %}
```
Service connector 'aws-session-token' of type 'aws' with id '3ae3e595-5cbc-446e-be64-e54e854e0e3f' is owned by user 'default' and is 'private'.
                      'aws-session-token' aws Service Connector Details                       
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                                   ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ ID               │ c0f8e857-47f9-418b-a60f-c3b03023da54                                    ┃
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
┃ SECRET ID        │ 16f35107-87ef-4a86-bbae-caa4a918fc15                                    ┃
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
┃ CREATED_AT       │ 2023-06-19 19:31:54.971869                                              ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-06-19 19:31:54.971871                                              ┃
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
{% endcode %}

However, clients receive temporary STS tokens instead of the AWS Secret Key configured in the connector (note the authentication method, expiration time, and credentials):

```sh
zenml service-connector describe aws-session-token --resource-type s3-bucket --resource-id zenfiles --client
```

{% code title="Example Command Output" %}
```
Service connector 'aws-session-token (s3-bucket | s3://zenfiles client)' of type 'aws' with id '3ae3e595-5cbc-446e-be64-e54e854e0e3f' is owned by user 'default' and is 'private'.
    'aws-session-token (s3-bucket | s3://zenfiles client)' aws Service     
                             Connector Details                             
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                ┃
┠──────────────────┼──────────────────────────────────────────────────────┨
┃ ID               │ c0f8e857-47f9-418b-a60f-c3b03023da54                 ┃
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
┃ EXPIRES IN       │ 11h59m56s                                            ┃
┠──────────────────┼──────────────────────────────────────────────────────┨
┃ OWNER            │ default                                              ┃
┠──────────────────┼──────────────────────────────────────────────────────┨
┃ WORKSPACE        │ default                                              ┃
┠──────────────────┼──────────────────────────────────────────────────────┨
┃ SHARED           │ ➖                                                   ┃
┠──────────────────┼──────────────────────────────────────────────────────┨
┃ CREATED_AT       │ 2023-06-19 19:35:24.090861                           ┃
┠──────────────────┼──────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-06-19 19:35:24.090863                           ┃
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
{% endcode %}

</details>

### AWS Federation Token

Generates [temporary STS tokens](best-security-practices.md#generating-temporary-and-down-scoped-credentials) for federated users by [impersonating another user](best-security-practices.md#impersonating-accounts-and-assuming-roles).

The connector needs to be configured with an AWS secret key associated with an IAM user or AWS account root user (not recommended). The IAM user must have permission to call [the GetFederationToken STS API](https://docs.aws.amazon.com/IAM/latest/UserGuide/id\_credentials\_temp\_request.html#api\_getfederationtoken) (i.e. allow the `sts:GetFederationToken` action on the `*` IAM resource). The connector will generate temporary STS tokens upon request by calling the GetFederationToken STS API.

These STS tokens have an expiration period longer than those issued through [the AWS IAM Role authentication method](aws-service-connector.md#aws-iam-role) and are more suitable for long-running processes that cannot automatically re-generate credentials upon expiration.

An AWS region is required and the connector may only be used to access AWS resources in the specified region.

One or more optional [IAM session policies](https://docs.aws.amazon.com/IAM/latest/UserGuide/access\_policies.html#policies\_session) may also be configured to further restrict the permissions of the generated STS tokens. If not specified, IAM session policies are automatically configured for the generated STS tokens [to restrict them to the minimum set of permissions required to access the target resource](best-security-practices.md#generating-temporary-and-down-scoped-credentials). Refer to the documentation for each supported Resource Type for the complete list of AWS permissions automatically granted to the generated STS tokens.

{% hint style="warning" %}
If this authentication method is used with [the generic AWS resource type](aws-service-connector.md#generic-aws-resource), a session policy MUST be explicitly specified, otherwise, the generated STS tokens will not have any permissions.
{% endhint %}

The default expiration period for generated STS tokens is 12 hours with a minimum of 15 minutes and a maximum of 36 hours. Temporary credentials obtained by using the AWS account root user credentials (not recommended) have a maximum duration of 1 hour.

{% hint style="info" %}
If you need to access an EKS Kubernetes cluster with this authentication method, please be advised that the EKS cluster's `aws-auth` ConfigMap may need to be manually configured to allow authentication with the federated user. For more information, [see this documentation](https://docs.aws.amazon.com/eks/latest/userguide/add-user-role.html).
{% endhint %}

For more information on user federation tokens, session policies, and the GetFederationToken AWS API, see [the official AWS documentation on the subject](https://docs.aws.amazon.com/IAM/latest/UserGuide/id\_credentials\_temp\_request.html#api\_getfederationtoken).

For more information about the difference between this method and [the AWS IAM Role authentication method](aws-service-connector.md#aws-iam-role), [consult this AWS documentation page](https://aws.amazon.com/blogs/security/understanding-the-api-options-for-securely-delegating-access-to-your-aws-account/).

<details>

<summary>Example auto-configuration</summary>

The following assumes the local AWS CLI has a `connectors` AWS CLI profile already configured with an AWS Secret Key:

```sh
AWS_PROFILE=connectors zenml service-connector register aws-federation-token --type aws --auth-method federation-token --auto-configure
```

{% code title="Example Command Output" %}
```
⠸ Registering service connector 'aws-federation-token'...
Successfully registered service connector `aws-federation-token` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃     RESOURCE TYPE     │ RESOURCE NAMES                               ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃    🔶 aws-generic     │ us-east-1                                    ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃     📦 s3-bucket      │ s3://zenfiles                                ┃
┃                       │ s3://zenml-demos                             ┃
┃                       │ s3://zenml-generative-chat                   ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃ 🌀 kubernetes-cluster │ zenhacks-cluster                             ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃  🐳 docker-registry   │ 715803424590.dkr.ecr.us-east-1.amazonaws.com ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

The Service Connector configuration shows long-lived credentials have been picked up from the local AWS CLI configuration:

```sh
zenml service-connector describe aws-federation-token
```

{% code title="Example Command Output" %}
```
Service connector 'aws-federation-token' of type 'aws' with id '868b17d4-b950-4d89-a6c4-12e520e66610' is owned by user 'default' and is 'private'.
                     'aws-federation-token' aws Service Connector Details                     
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                                   ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ ID               │ e28c403e-8503-4cce-9226-8a7cd7934763                                    ┃
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
┃ SECRET ID        │ 958b840d-2a27-4f6b-808b-c94830babd99                                    ┃
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
┃ CREATED_AT       │ 2023-06-19 19:36:28.619751                                              ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-06-19 19:36:28.619753                                              ┃
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
{% endcode %}

However, clients receive temporary STS tokens instead of the AWS Secret Key configured in the connector (note the authentication method, expiration time, and credentials):

```sh
zenml service-connector describe aws-federation-token --resource-type s3-bucket --resource-id zenfiles --client
```

{% code title="Example Command Output" %}
```
Service connector 'aws-federation-token (s3-bucket | s3://zenfiles client)' of type 'aws' with id '868b17d4-b950-4d89-a6c4-12e520e66610' is owned by user 'default' and is 'private'.
    'aws-federation-token (s3-bucket | s3://zenfiles client)' aws Service     
                              Connector Details                               
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                   ┃
┠──────────────────┼─────────────────────────────────────────────────────────┨
┃ ID               │ e28c403e-8503-4cce-9226-8a7cd7934763                    ┃
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
┃ EXPIRES IN       │ 11h59m56s                                               ┃
┠──────────────────┼─────────────────────────────────────────────────────────┨
┃ OWNER            │ default                                                 ┃
┠──────────────────┼─────────────────────────────────────────────────────────┨
┃ WORKSPACE        │ default                                                 ┃
┠──────────────────┼─────────────────────────────────────────────────────────┨
┃ SHARED           │ ➖                                                      ┃
┠──────────────────┼─────────────────────────────────────────────────────────┨
┃ CREATED_AT       │ 2023-06-19 19:38:29.406986                              ┃
┠──────────────────┼─────────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-06-19 19:38:29.406991                              ┃
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
{% endcode %}

</details>

## Auto-configuration

The AWS Service Connector allows [auto-discovering and fetching credentials](service-connectors-guide.md#auto-configuration) and configuration set up [by the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html) during registration. The default AWS CLI profile is used unless the AWS\_PROFILE environment points to a different profile.

<details>

<summary>Auto-configuration example</summary>

The following is an example of lifting AWS credentials granting access to the same set of AWS resources and services that the local AWS CLI is allowed to access. In this case, [the IAM role authentication method](aws-service-connector.md#aws-iam-role) was automatically detected:

```sh
AWS_PROFILE=zenml zenml service-connector register aws-auto --type aws --auto-configure
```

{% code title="Example Command Output" %}
```
⠹ Registering service connector 'aws-auto'...
Successfully registered service connector `aws-auto` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃     RESOURCE TYPE     │ RESOURCE NAMES                               ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃    🔶 aws-generic     │ us-east-1                                    ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃     📦 s3-bucket      │ s3://zenbytes-bucket                         ┃
┃                       │ s3://zenfiles                                ┃
┃                       │ s3://zenml-demos                             ┃
┃                       │ s3://zenml-generative-chat                   ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃ 🌀 kubernetes-cluster │ zenhacks-cluster                             ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃  🐳 docker-registry   │ 715803424590.dkr.ecr.us-east-1.amazonaws.com ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

The Service Connector configuration shows how credentials have automatically been fetched from the local AWS CLI configuration:

```sh
zenml service-connector describe aws-auto
```

{% code title="Example Command Output" %}
```
Service connector 'aws-auto' of type 'aws' with id '9f3139fd-4726-421a-bc07-312d83f0c89e' is owned by user 'default' and is 'private'.
                           'aws-auto' aws Service Connector Details                           
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                                   ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ ID               │ 9cdc926e-55d7-49f0-838e-db5ac34bb7dc                                    ┃
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
┃ SECRET ID        │ a137151e-1778-4f50-b64b-7cf6c1f715f5                                    ┃
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
┃ CREATED_AT       │ 2023-06-19 19:39:11.958426                                              ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-06-19 19:39:11.958428                                              ┃
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
{% endcode %}

</details>

## Local client provisioning

The local AWS CLI, Kubernetes `kubectl` CLI and the Docker CLI can be [configured with credentials extracted from or generated by a compatible AWS Service Connector](service-connectors-guide.md#configure-local-clients). Please note that unlike the configuration made possible through the AWS CLI, the Kubernetes and Docker credentials issued by the AWS Service Connector have a short lifetime and will need to be regularly refreshed. This is a byproduct of implementing a high-security profile.

{% hint style="info" %}
Configuring the local AWS CLI with credentials issued by the AWS Service Connector results in a local AWS CLI configuration profile being created with the name inferred from the first digits of the Service Connector UUID in the form -\<uuid\[:8]>. For example, a Service Connector with UUID `9f3139fd-4726-421a-bc07-312d83f0c89e` will result in a local AWS CLI configuration profile named `zenml-9f3139fd`.
{% endhint %}

<details>

<summary>Local CLI configuration examples</summary>

The following shows an example of configuring the local Kubernetes CLI to access an EKS cluster reachable through an AWS Service Connector:

```sh
zenml service-connector list --name aws-session-token
```

{% code title="Example Command Output" %}
```
┏━━━━━━━━┯━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━┓
┃ ACTIVE │ NAME              │ ID                                   │ TYPE   │ RESOURCE TYPES        │ RESOURCE NAME │ SHARED │ OWNER   │ EXPIRES IN │ LABELS ┃
┠────────┼───────────────────┼──────────────────────────────────────┼────────┼───────────────────────┼───────────────┼────────┼─────────┼────────────┼────────┨
┃        │ aws-session-token │ c0f8e857-47f9-418b-a60f-c3b03023da54 │ 🔶 aws │ 🔶 aws-generic        │ <multiple>    │ ➖     │ default │            │        ┃
┃        │                   │                                      │        │ 📦 s3-bucket          │               │        │         │            │        ┃
┃        │                   │                                      │        │ 🌀 kubernetes-cluster │               │        │         │            │        ┃
┃        │                   │                                      │        │ 🐳 docker-registry    │               │        │         │            │        ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━┛
```
{% endcode %}

This checks the Kubernetes clusters that the AWS Service Connector has access to:

```sh
zenml service-connector verify aws-session-token --resource-type kubernetes-cluster
```

{% code title="Example Command Output" %}
```
Service connector 'aws-session-token' is correctly configured with valid credentials and has access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━┓
┃     RESOURCE TYPE     │ RESOURCE NAMES   ┃
┠───────────────────────┼──────────────────┨
┃ 🌀 kubernetes-cluster │ zenhacks-cluster ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

Running the login CLI command will configure the local `kubectl` CLI to access the Kubernetes cluster:

```sh
zenml service-connector login aws-session-token --resource-type kubernetes-cluster --resource-id zenhacks-cluster
```

{% code title="Example Command Output" %}
```
⠇ Attempting to configure local client using service connector 'aws-session-token'...
Cluster "arn:aws:eks:us-east-1:715803424590:cluster/zenhacks-cluster" set.
Context "arn:aws:eks:us-east-1:715803424590:cluster/zenhacks-cluster" modified.
Updated local kubeconfig with the cluster details. The current kubectl context was set to 'arn:aws:eks:us-east-1:715803424590:cluster/zenhacks-cluster'.
The 'aws-session-token' Kubernetes Service Connector connector was used to successfully configure the local Kubernetes cluster client/SDK.
```
{% endcode %}

The following can be used to check that the local `kubectl` CLI is correctly configured:

```sh
kubectl cluster-info
```

{% code title="Example Command Output" %}
```
Kubernetes control plane is running at https://A5F8F4142FB12DDCDE9F21F6E9B07A18.gr7.us-east-1.eks.amazonaws.com
CoreDNS is running at https://A5F8F4142FB12DDCDE9F21F6E9B07A18.gr7.us-east-1.eks.amazonaws.com/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy
```
{% endcode %}

A similar process is possible with ECR container registries:

```sh
zenml service-connector verify aws-session-token --resource-type docker-registry
```

{% code title="Example Command Output" %}
```
Service connector 'aws-session-token' is correctly configured with valid credentials and has access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃   RESOURCE TYPE    │ RESOURCE NAMES                               ┃
┠────────────────────┼──────────────────────────────────────────────┨
┃ 🐳 docker-registry │ 715803424590.dkr.ecr.us-east-1.amazonaws.com ┃
┗━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

```sh
zenml service-connector login aws-session-token --resource-type docker-registry 
```

{% code title="Example Command Output" %}
```
⠏ Attempting to configure local client using service connector 'aws-session-token'...
WARNING! Your password will be stored unencrypted in /home/stefan/.docker/config.json.
Configure a credential helper to remove this warning. See
https://docs.docker.com/engine/reference/commandline/login/#credentials-store

The 'aws-session-token' Docker Service Connector connector was used to successfully configure the local Docker/OCI container registry client/SDK.
```
{% endcode %}

The following can be used to check that the local Docker client is correctly configured:

```sh
docker pull 715803424590.dkr.ecr.us-east-1.amazonaws.com/zenml-server
```

{% code title="Example Command Output" %}
```
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
{% endcode %}

It is also possible to update the local AWS CLI configuration with credentials extracted from the AWS Service Connector:

```sh
zenml service-connector login aws-session-token --resource-type aws-generic
```

{% code title="Example Command Output" %}
```
Configured local AWS SDK profile 'zenml-c0f8e857'.
The 'aws-session-token' AWS Service Connector connector was used to successfully configure the local Generic AWS resource client/SDK.
```
{% endcode %}

A new profile is created in the local AWS CLI configuration holding the credentials. It can be used to access AWS resources and services, e.g.:

```sh
aws --profile zenml-c0f8e857 s3 ls
```

</details>

## Stack Components use

The [S3 Artifact Store Stack Component](../../component-guide/artifact-stores/s3.md) can be connected to a remote AWS S3 bucket through an AWS Service Connector.

The AWS Service Connector can also be used with any Orchestrator or Model Deployer stack component flavor that relies on Kubernetes clusters to manage workloads. This allows EKS Kubernetes container workloads to be managed without the need to configure and maintain explicit AWS or Kubernetes `kubectl` configuration contexts and credentials in the target environment and in the Stack Component.

Similarly, Container Registry Stack Components can be connected to an ECR Container Registry through an AWS Service Connector. This allows container images to be built and published to ECR container registries without the need to configure explicit AWS credentials in the target environment or the Stack Component.

## End-to-end examples

<details>

<summary>EKS Kubernetes Orchestrator, S3 Artifact Store and ECR Container Registry with a multi-type AWS Service Connector</summary>

This is an example of an end-to-end workflow involving Service Connectors that use a single multi-type AWS Service Connector to give access to multiple resources for multiple Stack Components. A complete ZenML Stack is registered and composed of the following Stack Components, all connected through the same Service Connector:

* a [Kubernetes Orchestrator](../../component-guide/orchestrators/kubernetes.md) connected to an EKS Kubernetes cluster
* an [S3 Artifact Store](../../component-guide/artifact-stores/s3.md) connected to an S3 bucket
* an [ECR Container Registry](../../component-guide/container-registries/aws.md) stack component connected to an ECR container registry
* a local [Image Builder](../../component-guide/image-builders/local.md)

As a last step, a simple pipeline is run on the resulting Stack.

1.  [Configure the local AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html) with valid IAM user account credentials with a wide range of permissions (i.e. by running `aws configure`) and install ZenML integration prerequisites:

    ```sh
    zenml integration install -y aws s3
    ```

    ```sh
    aws configure --profile connectors
    ```

{% code title="Example Command Output" %}
````
```text
AWS Access Key ID [None]: AKIAIOSFODNN7EXAMPLE
AWS Secret Access Key [None]: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
Default region name [None]: us-east-1
Default output format [None]: json
```
````
{% endcode %}

2.  Make sure the AWS Service Connector Type is available

    ```sh
    zenml service-connector list-types --type aws
    ```

{% code title="Example Command Output" %}
````
```text
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
````
{% endcode %}

3.  Register a multi-type AWS Service Connector using auto-configuration

    ```sh
    AWS_PROFILE=connectors zenml service-connector register aws-demo-multi --type aws --auto-configure
    ```

{% code title="Example Command Output" %}
````
```text
⠼ Registering service connector 'aws-demo-multi'...
Successfully registered service connector `aws-demo-multi` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃     RESOURCE TYPE     │ RESOURCE NAMES                               ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃    🔶 aws-generic     │ us-east-1                                    ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃     📦 s3-bucket      │ s3://zenfiles                                ┃
┃                       │ s3://zenml-demos                             ┃
┃                       │ s3://zenml-generative-chat                   ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃ 🌀 kubernetes-cluster │ zenhacks-cluster                             ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃  🐳 docker-registry   │ 715803424590.dkr.ecr.us-east-1.amazonaws.com ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
````
{% endcode %}

```
**NOTE**: from this point forward, we don't need the local AWS CLI credentials or the local AWS CLI at all. The steps that follow can be run on any machine regardless of whether it has been configured and authorized to access the AWS platform or not.
```

4\. find out which S3 buckets, ECR registries, and EKS Kubernetes clusters we can gain access to. We'll use this information to configure the Stack Components in our minimal AWS stack: an S3 Artifact Store, a Kubernetes Orchestrator, and an ECR Container Registry.

````
```sh
zenml service-connector list-resources --resource-type s3-bucket
```

````

{% code title="Example Command Output" %}
````
```text
The following 's3-bucket' resources can be accessed by service connectors configured in your workspace:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME      │ CONNECTOR TYPE │ RESOURCE TYPE │ RESOURCE NAMES                        ┃
┠──────────────────────────────────────┼─────────────────────┼────────────────┼───────────────┼───────────────────────────────────────┨
┃ bf073e06-28ce-4a4a-8100-32e7cb99dced │ aws-demo-multi      │ 🔶 aws         │ 📦 s3-bucket  │ s3://zenfiles                         ┃
┃                                      │                     │                │               │ s3://zenml-demos                      ┃
┃                                      │                     │                │               │ s3://zenml-generative-chat            ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
````
{% endcode %}

````
```sh
zenml service-connector list-resources --resource-type kubernetes-cluster
```

````

{% code title="Example Command Output" %}
````
```text
The following 'kubernetes-cluster' resources can be accessed by service connectors configured in your workspace:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME        │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES      ┃
┠──────────────────────────────────────┼───────────────────────┼────────────────┼───────────────────────┼─────────────────────┨
┃ bf073e06-28ce-4a4a-8100-32e7cb99dced │ aws-demo-multi        │ 🔶 aws         │ 🌀 kubernetes-cluster │ zenhacks-cluster    ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━┛
```
````
{% endcode %}

````
```sh
zenml service-connector list-resources --resource-type docker-registry
```

````

{% code title="Example Command Output" %}
````
```text
The following 'docker-registry' resources can be accessed by service connectors configured in your workspace:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME     │ CONNECTOR TYPE │ RESOURCE TYPE      │ RESOURCE NAMES                                  ┃
┠──────────────────────────────────────┼────────────────────┼────────────────┼────────────────────┼─────────────────────────────────────────────────┨
┃ bf073e06-28ce-4a4a-8100-32e7cb99dced │ aws-demo-multi     │ 🔶 aws         │ 🐳 docker-registry │ 715803424590.dkr.ecr.us-east-1.amazonaws.com    ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
````
{% endcode %}

5.  register and connect an S3 Artifact Store Stack Component to an S3 bucket:

    ```sh
    zenml artifact-store register s3-zenfiles --flavor s3 --path=s3://zenfiles
    ```

{% code title="Example Command Output" %}
````
```text
Running with active workspace: 'default' (repository)
Running with active stack: 'default' (repository)
Successfully registered artifact_store `s3-zenfiles`.
```
````
{% endcode %}

````
```sh
zenml artifact-store connect s3-zenfiles --connector aws-demo-multi
```

````

{% code title="Example Command Output" %}
````
```text
Running with active workspace: 'default' (repository)
Running with active stack: 'default' (repository)
Successfully connected artifact store `s3-zenfiles` to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────┼────────────────┨
┃ bf073e06-28ce-4a4a-8100-32e7cb99dced │ aws-demo-multi │ 🔶 aws         │ 📦 s3-bucket  │ s3://zenfiles  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛
```
````
{% endcode %}

6.  register and connect a Kubernetes Orchestrator Stack Component to an EKS cluster:

    ```sh
    zenml orchestrator register eks-zenml-zenhacks --flavor kubernetes --synchronous=true --kubernetes_namespace=zenml-workloads
    ```

{% code title="Example Command Output" %}
````
```text
Running with active workspace: 'default' (repository)
Running with active stack: 'default' (repository)
Successfully registered orchestrator `eks-zenml-zenhacks`.
```
````
{% endcode %}

````
```sh
zenml orchestrator connect eks-zenml-zenhacks --connector aws-demo-multi
```

````

{% code title="Example Command Output" %}
````
```text
Running with active workspace: 'default' (repository)
Running with active stack: 'default' (repository)
Successfully connected orchestrator `eks-zenml-zenhacks` to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES   ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────────────┼──────────────────┨
┃ bf073e06-28ce-4a4a-8100-32e7cb99dced │ aws-demo-multi │ 🔶 aws         │ 🌀 kubernetes-cluster │ zenhacks-cluster ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━┛
```
````
{% endcode %}

7.  Register and connect an EC GCP Container Registry Stack Component to an ECR container registry:

    ```sh
    zenml container-registry register ecr-us-east-1 --flavor aws --uri=715803424590.dkr.ecr.us-east-1.amazonaws.com
    ```

{% code title="Example Command Output" %}
````
```text
Running with active workspace: 'default' (repository)
Running with active stack: 'default' (repository)
Successfully registered container_registry `ecr-us-east-1`.
```
````
{% endcode %}

````
```sh
zenml container-registry connect ecr-us-east-1 --connector aws-demo-multi
```

````

{% code title="Example Command Output" %}
````
```text
Running with active workspace: 'default' (repository)
Running with active stack: 'default' (repository)
Successfully connected container registry `ecr-us-east-1` to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE      │ RESOURCE NAMES                               ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼────────────────────┼──────────────────────────────────────────────┨
┃ bf073e06-28ce-4a4a-8100-32e7cb99dced │ aws-demo-multi │ 🔶 aws         │ 🐳 docker-registry │ 715803424590.dkr.ecr.us-east-1.amazonaws.com ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
````
{% endcode %}

8.  Combine all Stack Components together into a Stack and set it as active (also throw in a local Image Builder for completion):

    ```sh
    zenml image-builder register local --flavor local
    ```

{% code title="Example Command Output" %}
````
```text
Running with active workspace: 'default' (global)
Running with active stack: 'default' (global)
Successfully registered image_builder `local`.
```
````
{% endcode %}

````
```sh
zenml stack register aws-demo -a s3-zenfiles -o eks-zenml-zenhacks -c ecr-us-east-1 -i local --set
```

````

{% code title="Example Command Output" %}
````
```text
Connected to the ZenML server: 'https://stefan.develaws.zenml.io'
Running with active workspace: 'default' (repository)
Stack 'aws-demo' successfully registered!
Active repository stack set to:'aws-demo'
```
````
{% endcode %}

9.  Finally, run a simple pipeline to prove that everything works as expected. We'll use the simplest pipelines possible for this example:

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

{% code title="Example Command Output" %}
````
```text
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
````
{% endcode %}

</details>

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
