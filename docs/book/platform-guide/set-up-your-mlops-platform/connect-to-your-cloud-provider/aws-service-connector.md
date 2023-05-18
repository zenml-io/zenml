---
description: >-
  Configure AWS Service Connectors to connect ZenML to AWS resources like S3
  buckets, EKS Kubernetes clusters and ECR container registries.
---

# AWS Service Connector

The ZenML AWS Service Connector facilitates the authentication and access to managed AWS services and resources. These encompass a range of resources, including S3 buckets, ECR repositories, and EKS clusters. The connector provides support for various authentication methods, including explicit long-lived AWS credentials, IAM roles, and implicit authentication.

To ensure heightened security measures, this connector also enables the generation of temporary STS security tokens that are scoped down to the minimum permissions necessary for accessing the intended resource. Furthermore, it includes automatic configuration and detection of  credentials locally configured through the AWS CLI.

This connector serves as a general means of accessing any AWS service by issuing pre-authenticated boto3 sessions. Additionally, the connector can handle specialized authentication for S3, Docker and Kubernetes Python clients. It also allows for the configuration of local Docker and Kubernetes CLIs.

```
$ zenml service-connector list-types --type aws
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━┯━━━━━━━┯━━━━━━━━┓
┃         NAME          │ TYPE   │ RESOURCE TYPES        │ AUTH METHODS     │ LOCAL │ REMOTE ┃
┠───────────────────────┼────────┼───────────────────────┼──────────────────┼───────┼────────┨
┃ AWS Service Connector │ 🔶 aws │ 🔶 aws-generic        │ implicit         │ ✅    │ ➖     ┃
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

## Resource Types

The Kubernetes Service Connector only supports authenticating to and granting access to a generic Kubernetes cluster. This type of resource is identified by the `kubernetes-cluster` Resource Type.

The resource name is a user-friendly cluster name configured during registration.

## Authentication Methods

### Implicit authentication

[Implicit authentication](best-security-practices.md#implicit-authentication) to AWS services using environment variables, local configuration files or IAM roles.

This authentication method doesn't require any credentials to be explicitly configured. It automatically discovers and uses credentials from one of the following sources:

* environment variables (AWS\_ACCESS\_KEY\_ID, AWS\_SECRET\_ACCESS\_KEY, AWS\_SESSION\_TOKEN, AWS\_DEFAULT\_REGION)
* local configuration files [set up through the AWS CLI ](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)(\~/aws/credentials, \~/.aws/config)
* IAM roles for Amazon EC2, ECS, EKS, Lambda, etc. Only works when running the ZenML server on an AWS resource with an IAM role attached to it.

This is the quickest and easiest way to authenticate to AWS services. However, the results depend on how ZenML is deployed and the environment where it is used and is thus not fully reproducible:

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

Uses [temporary STS tokens](best-security-practices.md#short-lived-credentials) explicitly configured by the user or auto-configured from a local environment (e.g. if the local AWS CLI is configured with an IAM role).

This method has the major limitation that the user must regularly generate new tokens and update the connector configuration as STS tokens expire. This method is best used in cases where the connector only needs to be used for a short period of time.

An AWS region is required and the connector may only be used to access AWS resources in the specified region.

<details>

<summary>Example auto-configuration</summary>

Fetching STS tokens from the local AWS CLI is possible if the AWS CLI configuration or profile already uses STS token or is configured with an IAM role. In our example, the `zenml` AWS CLI profile is configured with an AWS Secret Key and an IAM role. We need to force the ZenML CLI to use the STS token authentication by passing the `--auth-method sts-token` option, otherwise it would automatically use [the IAM role authentication method](aws-service-connector.md#aws-iam-role):

```
$ AWS_PROFILE=zenml zenml service-connector register aws-sts-token --type aws --auto-configure --auth-method sts-token
⠸ Registering service connector 'aws-sts-token'...
Successfully registered service connector `aws-sts-token` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────────────┼────────────────┨
┃ 3276be69-6559-4fbb-ae9e-3249bafc7a3c │ aws-sts-token  │ 🔶 aws         │ 🔶 aws-generic        │ 🤷 none listed ┃
┃                                      │                │                │ 📦 s3-bucket          │                ┃
┃                                      │                │                │ 🌀 kubernetes-cluster │                ┃
┃                                      │                │                │ 🐳 docker-registry    │                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛

$ zenml service-connector describe aws-sts-token 
Service connector 'aws-sts-token' of type 'aws' with id '3276be69-6559-4fbb-ae9e-3249bafc7a3c' is owned by user 'default' and is 'private'.
                        'aws-sts-token' aws Service Connector Details                         
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                                   ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ ID               │ 3276be69-6559-4fbb-ae9e-3249bafc7a3c                                    ┃
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
┃ SECRET ID        │ b72f8928-8285-4563-9470-d88d68930eba                                    ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ SESSION DURATION │ N/A                                                                     ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ EXPIRES IN       │ 59m53s                                                                  ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ OWNER            │ default                                                                 ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ WORKSPACE        │ default                                                                 ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ SHARED           │ ➖                                                                      ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ CREATED_AT       │ 2023-05-18 15:07:35.627344                                              ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-05-18 15:07:35.627346                                              ┃
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

Note the temporary nature of the Service Connector. It will become unusable in 1 hour:

```
$ zenml service-connector list 
┏━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ ACTIVE │ NAME                         │ ID                                  │ TYPE          │ RESOURCE TYPES        │ RESOURCE NAME                  │ SHARED │ OWNER   │ EXPIRES IN │ LABELS                   ┃
┠────────┼──────────────────────────────┼─────────────────────────────────────┼───────────────┼───────────────────────┼────────────────────────────────┼────────┼─────────┼────────────┼──────────────────────────┨
┃        │ aws-sts-token                │ 3276be69-6559-4fbb-ae9e-3249bafc7a3 │ 🔶 aws        │ 🔶 aws-generic        │ <multiple>                     │ ➖     │ default │ 59m25s     │                          ┃
┃        │                              │ c                                   │               │ 📦 s3-bucket          │                                │        │         │            │                          ┃
┃        │                              │                                     │               │ 🌀 kubernetes-cluster │                                │        │         │            │                          ┃
┃        │                              │                                     │               │ 🐳 docker-registry    │                                │        │         │            │                          ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━┛

```

</details>

### AWS IAM Role

Generates [temporary STS credentials](best-security-practices.md#impersonating-accounts-and-assuming-roles) by assuming an AWS IAM role.

The connector needs to be configured with the IAM role to be assumed accompanied by an AWS secret key associated with an IAM user or an STS token associated with another IAM role. The IAM user or IAM role must have permissions to assume the target IAM role. The connector will [generate temporary STS tokens](best-security-practices.md#generating-temporary-and-down-scoped-credentials) upon request by [calling the AssumeRole STS API](https://docs.aws.amazon.com/IAM/latest/UserGuide/id\_credentials\_temp\_request.html#api\_assumerole).

An AWS region is required and the connector may only be used to access AWS resources in the specified region.

One or more optional [IAM session policies](https://docs.aws.amazon.com/IAM/latest/UserGuide/access\_policies.html#policies\_session) may also be configured to further restrict the permissions of the generated STS tokens. If not specified, IAM session policies are automatically configured for the generated STS tokens [to restrict them to the minimum set of permissions required to access the target resource](best-security-practices.md#aws-down-scoped-credentials-example). Refer to the documentation for each supported Resource Type for the complete list of AWS permissions automatically granted to the generated STS tokens.

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



</details>

### AWS Federation Token

Generates [temporary STS tokens](best-security-practices.md#generating-temporary-and-down-scoped-credentials) for federated users by [impersonating another user](best-security-practices.md#impersonating-accounts-and-assuming-roles).

The connector needs to be configured with an AWS secret key associated with an IAM user or AWS account root user (not recommended). The IAM user must have permissions to call [the GetFederationToken STS API](https://docs.aws.amazon.com/IAM/latest/UserGuide/id\_credentials\_temp\_request.html#api\_getfederationtoken) (i.e. allow the `sts:GetFederationToken` action on the `*` IAM resource). The connector will generate temporary STS tokens upon request by calling the GetFederationToken STS API.

These STS tokens have an expiration period longer that those issued through [the AWS IAM Role authentication method](aws-service-connector.md#aws-iam-role) and are more suitable for long-running processes that cannot automatically re-generate credentials upon expiration.

An AWS region is required and the connector may only be used to access AWS resources in the specified region.

One or more optional [IAM session policies](https://docs.aws.amazon.com/IAM/latest/UserGuide/access\_policies.html#policies\_session) may also be configured to further restrict the permissions of the generated STS tokens. If not specified, IAM session policies are automatically configured for the generated STS tokens [to restrict them to the minimum set of permissions required to access the target resource](best-security-practices.md#aws-down-scoped-credentials-example). Refer to the documentation for each supported Resource Type for the complete list of AWS permissions automatically granted to the generated STS tokens.

{% hint style="warning" %}
If this authentication method is used with the generic AWS resource type, a session policy MUST be explicitly specified, otherwise the generated STS tokens will not have any permissions.
{% endhint %}

The default expiration period for generated STS tokens is 12 hours with a minimum of 15 minutes and a maximum of 36 hours. Temporary credentials obtained by using the AWS account root user credentials (not recommended) have a maximum duration of 1 hour.

{% hint style="info" %}
If you need to access an EKS kubernetes cluster with this authentication method, please be advised that the EKS cluster's `aws-auth` ConfigMap may need to be manually configured to allow authentication with the federated user. For more information, [see this documentation](https://docs.aws.amazon.com/eks/latest/userguide/add-user-role.html).
{% endhint %}

For more information on user federation tokens, session policies and the GetFederationToken AWS API, see [the official AWS documentation on the subject](https://docs.aws.amazon.com/IAM/latest/UserGuide/id\_credentials\_temp\_request.html#api\_getfederationtoken).

For more information about the difference between this method and [the AWS IAM Role authentication method](aws-service-connector.md#aws-iam-role), [consult this AWS documentation page](https://aws.amazon.com/blogs/security/understanding-the-api-options-for-securely-delegating-access-to-your-aws-account/).

## Auto-configuration

The Kubernetes Service Connector allows fetching credentials from the local Kubernetes client (i.e. `kubectl`) during registration. The current Kubernetes kubectl configuration context is used for this purpose. The following is an example of lifting Kubernetes credentials granting access to a GKE cluster:

```
$ zenml service-connector register kube-auto --type kubernetes --auto-configure
Successfully registered service connector `kube-auto` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────────────┼────────────────┨
┃ 4315e8eb-fcbd-4938-a4d7-a9218ab372a1 │ kube-auto      │ 🌀 kubernetes  │ 🌀 kubernetes-cluster │ 35.175.95.223  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛

$ zenml service-connector describe kube-auto 
Service connector 'kube-auto' of type 'kubernetes' with id '4315e8eb-fcbd-4938-a4d7-a9218ab372a1' is owned by user 'default' and is 'private'.
     'kube-auto' kubernetes Service Connector Details      
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                ┃
┠──────────────────┼──────────────────────────────────────┨
┃ ID               │ 4315e8eb-fcbd-4938-a4d7-a9218ab372a1 ┃
┠──────────────────┼──────────────────────────────────────┨
┃ NAME             │ kube-auto                            ┃
┠──────────────────┼──────────────────────────────────────┨
┃ TYPE             │ 🌀 kubernetes                        ┃
┠──────────────────┼──────────────────────────────────────┨
┃ AUTH METHOD      │ token                                ┃
┠──────────────────┼──────────────────────────────────────┨
┃ RESOURCE TYPES   │ 🌀 kubernetes-cluster                ┃
┠──────────────────┼──────────────────────────────────────┨
┃ RESOURCE NAME    │ 35.175.95.223                        ┃
┠──────────────────┼──────────────────────────────────────┨
┃ SECRET ID        │ a833e86d-b845-4584-9656-4b041335e299 ┃
┠──────────────────┼──────────────────────────────────────┨
┃ SESSION DURATION │ N/A                                  ┃
┠──────────────────┼──────────────────────────────────────┨
┃ EXPIRES IN       │ N/A                                  ┃
┠──────────────────┼──────────────────────────────────────┨
┃ OWNER            │ default                              ┃
┠──────────────────┼──────────────────────────────────────┨
┃ WORKSPACE        │ default                              ┃
┠──────────────────┼──────────────────────────────────────┨
┃ SHARED           │ ➖                                   ┃
┠──────────────────┼──────────────────────────────────────┨
┃ CREATED_AT       │ 2023-05-16 21:45:33.224740           ┃
┠──────────────────┼──────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-05-16 21:45:33.224743           ┃
┗━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                  Configuration                  
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY              │ VALUE                 ┃
┠───────────────────────┼───────────────────────┨
┃ server                │ https://35.175.95.223 ┃
┠───────────────────────┼───────────────────────┨
┃ insecure              │ False                 ┃
┠───────────────────────┼───────────────────────┨
┃ cluster_name          │ 35.175.95.223         ┃
┠───────────────────────┼───────────────────────┨
┃ token                 │ [HIDDEN]              ┃
┠───────────────────────┼───────────────────────┨
┃ certificate_authority │ [HIDDEN]              ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┛
```

{% hint style="info" %}
Credentials auto-discovered and lifted through the Kubernetes Service Connector might have a limited lifetime, especially if the target Kubernetes cluster is managed through a 3rd party authentication provider such a GCP or AWS. Using short-lived credentials with your Service Connectors could lead to loss of connectivity and other unexpected errors in your pipeline.
{% endhint %}

## Local client provisioning

This Service Connector allows configuring the local Kubernetes client (i.e. `kubectl`) with credentials:

```
$ zenml service-connector login kube-auto 
⠦ Attempting to configure local client using service connector 'kube-auto'...
Cluster "35.185.95.223" set.
⠇ Attempting to configure local client using service connector 'kube-auto'...
⠏ Attempting to configure local client using service connector 'kube-auto'...
Updated local kubeconfig with the cluster details. The current kubectl context was set to '35.185.95.223'.
The 'kube-auto' Kubernetes Service Connector connector was used to successfully configure the local Kubernetes cluster client/SDK.
```

## Stack Components use

The Kubernetes Service Connector can be used in Orchestrator and Model Deployer stack component flavors that rely on Kubernetes clusters to manage their workloads. This allows Kubernetes container workloads to be managed without the need to configure and maintain explicit Kubernetes `kubectl` configuration contexts and credentials in the target environment and in the Stack Component.
