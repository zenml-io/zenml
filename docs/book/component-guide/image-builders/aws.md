---
description: Building container images with AWS CodeBuild
---

# AWS Image Builder

The AWS image builder is an [image builder](./image-builders.md) flavor provided by the ZenML `aws` integration that uses [AWS CodeBuild](https://aws.amazon.com/codebuild) to build container images.

### When to use it

You should use the AWS image builder if:

* you're **unable** to install or use [Docker](https://www.docker.com) on your client machine.
* you're already using AWS.
* your stack is mainly composed of other AWS components such as the [S3 Artifact Store](../artifact-stores/s3.md) or the [Sagemaker Orchestrator](../orchestrators/sagemaker.md).

### How to deploy it

{% hint style="info" %}
Would you like to skip ahead and deploy a full ZenML cloud stack already,
including the AWS image builder? Check out the
[in-browser stack deployment wizard](../../how-to/infrastructure-deployment/stack-deployment/deploy-a-cloud-stack.md),
the [stack registration wizard](../../how-to/infrastructure-deployment/stack-deployment/register-a-cloud-stack.md),
or [the ZenML AWS Terraform module](../../how-to/infrastructure-deployment/stack-deployment/deploy-a-cloud-stack-with-terraform.md)
for a shortcut on how to deploy & register this stack component.
{% endhint %}

### How to use it

To use the AWS image builder, you need:

*   The ZenML `aws` integration installed. If you haven't done so, run:

    ```shell
    zenml integration install aws
    ```
* An [S3 Artifact Store](../artifact-stores/s3.md) where the build context will be uploaded, so AWS CodeBuild can access it.
* Recommended: an [AWS container registry](../container-registries/aws.md) where the built image will be pushed. The AWS CodeBuild service can also work with other container registries, but [explicit authentication](#authentication-methods) must be enabled in this case.
* An [AWS CodeBuild project](https://aws.amazon.com/codebuild) created in the AWS account and region where you want to build the Docker images, preferably in the same region as the ECR container registry where images will be pushed (if applicable). The CodeBuild project configuration is largely irrelevant, as ZenML will override most of the default settings for each build, but the following are some recommended default configuration values:
    *  **Source Type**: `Amazon S3`
    *  **Bucket**: The same S3 bucket used by the ZenML S3 Artifact Store.
    *  **S3 folder**: any value (e.g. `codebuild`);
    *  **Environment Type**: `Linux Container`
    *  **Environment Image**: `bentolor/docker-dind-awscli`
    *  **Privileged Mode**: `false`

The user must take care that the **Service Role** attached to the CodeBuild project also has the necessary permissions to access the S3 bucket to read objects and the ECR container registry to push images (if applicable):

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:GetObjectVersion"
            ],
            "Resource": "arn:aws:s3:::<BUCKET_NAME>/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ecr:BatchGetImage",
                "ecr:DescribeImages",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload",
                "ecr:PutImage"
            ],
            "Resource": "arn:aws:ecr:<REGION>:<ACCOUNT_ID>:repository/<REPOSITORY_NAME>"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken"
            ],
            "Resource": "*"
        },
    ]
}
```

* Recommended: grant ZenML access to trigger AWS CodeBuild builds by registering an [AWS Service Connector](../../how-to/infrastructure-deployment/auth-management/aws-service-connector.md) with the proper credentials and permissions, as covered in the [Authentication Methods](aws.md#authentication-methods) section. If not provided, then the AWS credentials will be inferred from the environment where the pipeline is triggered.

We can register the image builder and use it in our active stack:

```shell
zenml image-builder register <IMAGE_BUILDER_NAME> \
    --flavor=aws \
    --code_build_project=<CODEBUILD_PROJECT_NAME>

# Register and activate a stack with the new image builder
zenml stack register <STACK_NAME> -i <IMAGE_BUILDER_NAME> ... --set
```

You also need to set up [authentication](aws.md#authentication-methods) required to access the CodeBuild AWS service.

#### Authentication Methods

Integrating and using an AWS Image Builder in your pipelines is not possible without employing some form of authentication. If you're looking for a quick way to get started locally, you can use the _Local Authentication_ method. However, the recommended way to authenticate to the AWS cloud platform is through [an AWS Service Connector](../../how-to/infrastructure-deployment/auth-management/aws-service-connector.md). This is particularly useful if you are configuring ZenML stacks that combine the AWS Image Builder with other remote stack components also running in AWS.

{% tabs %}
{% tab title="Implicit Authentication" %}
This method uses the implicit AWS authentication available _in the environment where the ZenML code is running_. On your local machine, this is the quickest way to configure an AWS Image Builder. You don't need to supply credentials explicitly when you register the AWS Image Builder, as it leverages the local credentials and configuration that the AWS CLI stores on your local machine. However, you will need to install and set up the AWS CLI on your machine as a prerequisite, as covered in [the AWS CLI documentation](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html), before you register the AWS Image Builder.

{% hint style="warning" %}
Stacks using the AWS Image Builder set up with local authentication are not portable across environments. To make ZenML pipelines fully portable, it is recommended to use [an AWS Service Connector](../../how-to/infrastructure-deployment/auth-management/aws-service-connector.md) to authenticate your AWS Image Builder to the AWS cloud platform.
{% endhint %}
{% endtab %}

{% tab title="AWS Service Connector (recommended)" %}
To set up the AWS Image Builder to authenticate to AWS and access the AWS CodeBuild services, it is recommended to leverage the many features provided by [the AWS Service Connector](../../how-to/infrastructure-deployment/auth-management/aws-service-connector.md) such as auto-configuration, best security practices regarding long-lived credentials and reusing the same credentials across multiple stack components.

If you don't already have an AWS Service Connector configured in your ZenML deployment, you can register one using the interactive CLI command. You also have the option to configure an AWS Service Connector that can be used to access more than just the AWS CodeBuild service:

```sh
zenml service-connector register --type aws -i
```

A non-interactive CLI example that leverages [the AWS CLI configuration](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) on your local machine to auto-configure an AWS Service Connector for the AWS CodeBuild service:

```sh
zenml service-connector register <CONNECTOR_NAME> --type aws --resource-type aws-generic --auto-configure
```

{% code title="Example Command Output" %}
```
$ zenml service-connector register aws-generic --type aws --resource-type aws-generic --auto-configure
Successfully registered service connector `aws-generic` with access to the following resources:
┏━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃ RESOURCE TYPE  │ RESOURCE NAMES ┃
┠────────────────┼────────────────┨
┃ 🔵 aws-generic │ eu-central-1   ┃
┗━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛
```
{% endcode %}

> **Note**: Please remember to grant the entity associated with your AWS credentials permissions to access the CodeBuild API and to run CodeBuilder builds (e.g. the [CodeBuild Editor IAM role](https://cloud.google.com/build/docs/iam-roles-permissions#predefined\_roles)). The AWS Service Connector supports [many different authentication methods](../../how-to/infrastructure-deployment/auth-management/aws-service-connector.md#authentication-methods) with different levels of security and convenience. You should pick the one that best fits your use case.

If you already have one or more AWS Service Connectors configured in your ZenML deployment, you can check which of them can be used to access generic AWS resources like the one required for your AWS Image Builder by running e.g.:

```sh
zenml service-connector list-resources --resource-type aws-generic
```

{% code title="Example Command Output" %}
```
The following 'aws-generic' resources can be accessed by service connectors configured in your workspace:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE  │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼────────────────┼────────────────┨
┃ 7113ba9b-efdd-4a0a-94dc-fb67926e58a1 │ aws-generic    │ 🔶 aws         │ 🔶 aws-generic │ eu-central-1   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛
```
{% endcode %}

After having set up or decided on an AWS Service Connector to use to authenticate to AWS, you can register the AWS Image Builder as follows:

```sh
zenml image-builder register <IMAGE_BUILDER_NAME> \
    --flavor=aws \
    --code_build_project=<CODEBUILD_PROJECT_NAME> \
    --connector <CONNECTOR_ID>
```

To connect an AWS Image Builder to an AWS Service Connector at a later point, you can use the following command:

```sh
zenml image-builder connect <IMAGE_BUILDER_NAME> --connector <CONNECTOR_ID>
```

{% code title="Example Command Output" %}
```
$ zenml image-builder connect aws-image-builder --connector aws-generic
Successfully connected image builder `aws-image-builder` to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE  │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼────────────────┼────────────────┨
┃ 7113ba9b-efdd-4a0a-94dc-fb67926e58a1 │ aws-generic    │ 🔶 aws         │ 🔶 aws-generic │ eu-central-1   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛
```
{% endcode %}

As a final step, you can use the AWS Image Builder in a ZenML Stack:

```sh
# Register and set a stack with the new image builder
zenml stack register <STACK_NAME> -i <IMAGE_BUILDER_NAME> ... --set
```
{% endtab %}
{% endtabs %}

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
