---
description: >-
  Understand the workflow of using Service Connectors to access external
  resources with ZenML.
---

# Connecting ZenML to resources

Everything around Service Connectors is expressed in terms of resources. A Kubernetes cluster is a resource. An S3 bucket is another resource. Service Connectors simplify the configuration of ZenML to enable authentication and access to these resources. Once Service Connectors are set up, Stacks and Stack Components can easily access and utilize these resources in your ML pipelines without worrying about the specifics of authentication and access.

In this section, we walk through a typical workflow to explain conceptually the role that Service Connectors play in connecting ZenML to external resources.

## The typical Service Connectors workflow

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
