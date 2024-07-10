---
description: Storing container images in Amazon ECR.
---

# Amazon Elastic Container Registry (ECR)

The AWS container registry is a [container registry](./container-registries.md) flavor provided with the ZenML `aws` integration and uses [Amazon ECR](https://aws.amazon.com/ecr/) to store container images.

### When to use it

You should use the AWS container registry if:

* one or more components of your stack need to pull or push container images.
* you have access to AWS ECR. If you're not using AWS, take a look at the other [container registry flavors](./container-registries.md#container-registry-flavors).

### How to deploy it

{% hint style="info" %}
Don't want to deploy the container registry manually? Check out the
[easy cloud deployment wizard](../../how-to/stack-deployment/deploy-a-cloud-stack.md)
or the [easy cloud registration wizard](../../how-to/stack-deployment/register-a-cloud-stack.md)
for a shortcut on how to deploy & register this stack component.
{% endhint %}

The ECR registry is automatically activated once you create an AWS account. However, you'll need to create a `Repository` in order to push container images to it:

* Go to the [ECR website](https://console.aws.amazon.com/ecr).
* Make sure the correct region is selected on the top right.
* Click on `Create repository`.
* Create a private repository. The name of the repository depends on the [orchestrator](../orchestrators/orchestrators.md) or [step operator](../step-operators/step-operators.md) you're using in your stack.

### URI format

The AWS container registry URI should have the following format:

```shell
<ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com
# Examples:
123456789.dkr.ecr.eu-west-2.amazonaws.com
987654321.dkr.ecr.ap-south-1.amazonaws.com
135792468.dkr.ecr.af-south-1.amazonaws.com
```

To figure out the URI for your registry:

* Go to the [AWS console](https://console.aws.amazon.com/) and click on your user account in the top right to see the `Account ID`.
* Go [here](https://docs.aws.amazon.com/general/latest/gr/rande.html#regional-endpoints) and choose the region in which you would like to store your container images. Make sure to choose a nearby region for faster access.
* Once you have both these values, fill in the values in this template `<ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com` to get your container registry URI.

#### Infrastructure Deployment

An AWS ECR Container Registry can be deployed directly from the ZenML CLI:

```shell
zenml container-registry deploy ecr_container_registry --flavor=aws --provider=aws ...
```

You can pass other configurations specific to the stack components as key-value arguments. If you don't provide a name, a random one is generated for you. For more information about how to work use the CLI for this, please refer to the dedicated documentation section.

### How to use it

To use the AWS container registry, we need:

*   The ZenML `aws` integration installed. If you haven't done so, run

    ```shell
    zenml integration install aws
    ```
* [Docker](https://www.docker.com) installed and running.
* The registry URI. Check out the [previous section](aws.md#how-to-deploy-it) on the URI format and how to get the URI for your registry.

We can then register the container registry and use it in our active stack:

```shell
zenml container-registry register <NAME> \
    --flavor=aws \
    --uri=<REGISTRY_URI>

# Add the container registry to the active stack
zenml stack update -c <NAME>
```

You also need to set up [authentication](aws.md#authentication-methods) required to log in to the container registry.

#### Authentication Methods

Integrating and using an AWS Container Registry in your pipelines is not possible without employing some form of authentication. If you're looking for a quick way to get started locally, you can use the _Local Authentication_ method. However, the recommended way to authenticate to the AWS cloud platform is through [an AWS Service Connector](../../how-to/auth-management/aws-service-connector.md). This is particularly useful if you are configuring ZenML stacks that combine the AWS Container Registry with other remote stack components also running in AWS.

{% tabs %}
{% tab title="Local Authentication" %}
This method uses the Docker client authentication available _in the environment where the ZenML code is running_. On your local machine, this is the quickest way to configure an AWS Container Registry. You don't need to supply credentials explicitly when you register the AWS Container Registry, as it leverages the local credentials and configuration that the AWS CLI and Docker client store on your local machine. However, you will need to install and set up the AWS CLI on your machine as a prerequisite, as covered in [the AWS CLI documentation](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html), before you register the AWS Container Registry.

With the AWS CLI installed and set up with credentials, we'll need to log in to the container registry so Docker can pull and push images:

```shell
# Fill your REGISTRY_URI and REGION in the placeholders in the following command.
# You can find the REGION as part of your REGISTRY_URI: `<ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com`
aws ecr get-login-password --region <REGION> | docker login --username AWS --password-stdin <REGISTRY_URI>
```

{% hint style="warning" %}
Stacks using the AWS Container Registry set up with local authentication are not portable across environments. To make ZenML pipelines fully portable, it is recommended to use [an AWS Service Connector](../../how-to/auth-management/aws-service-connector.md) to link your AWS Container Registry to the remote ECR registry.
{% endhint %}
{% endtab %}

{% tab title="AWS Service Connector (recommended)" %}
To set up the AWS Container Registry to authenticate to AWS and access an ECR registry, it is recommended to leverage the many features provided by [the AWS Service Connector](../../how-to/auth-management/aws-service-connector.md) such as auto-configuration, local login, best security practices regarding long-lived credentials and fine-grained access control and reusing the same credentials across multiple stack components.

If you don't already have an AWS Service Connector configured in your ZenML deployment, you can register one using the interactive CLI command. You have the option to configure an AWS Service Connector that can be used to access an ECR registry or even more than one type of AWS resource:

```sh
zenml service-connector register --type aws -i
```

A non-interactive CLI example that leverages [the AWS CLI configuration](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) on your local machine to auto-configure an AWS Service Connector targeting an ECR registry is:

```sh
zenml service-connector register <CONNECTOR_NAME> --type aws --resource-type docker-registry --auto-configure
```

{% code title="Example Command Output" %}
```
$ zenml service-connector register aws-us-east-1 --type aws --resource-type docker-registry --auto-configure
⠸ Registering service connector 'aws-us-east-1'...
Successfully registered service connector `aws-us-east-1` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃   RESOURCE TYPE    │ RESOURCE NAMES                               ┃
┠────────────────────┼──────────────────────────────────────────────┨
┃ 🐳 docker-registry │ 715803424590.dkr.ecr.us-east-1.amazonaws.com ┃
┗━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

> **Note**: Please remember to grant the entity associated with your AWS credentials permissions to read and write to one or more ECR repositories as well as to list accessible ECR repositories. For a full list of permissions required to use an AWS Service Connector to access an ECR registry, please refer to the [AWS Service Connector ECR registry resource type documentation](../../how-to/auth-management/aws-service-connector.md#ecr-container-registry) or read the documentation available in the interactive CLI commands and dashboard. The AWS Service Connector supports [many different authentication methods](../../how-to/auth-management/aws-service-connector.md#authentication-methods) with different levels of security and convenience. You should pick the one that best fits your use case.

If you already have one or more AWS Service Connectors configured in your ZenML deployment, you can check which of them can be used to access the ECR registry you want to use for your AWS Container Registry by running e.g.:

```sh
zenml service-connector list-resources --connector-type aws --resource-type docker-registry
```

{% code title="Example Command Output" %}
```
The following 'docker-registry' resources can be accessed by service connectors configured in your workspace:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME          │ CONNECTOR TYPE │ RESOURCE TYPE      │ RESOURCE NAMES                               ┃
┠──────────────────────────────────────┼─────────────────────────┼────────────────┼────────────────────┼──────────────────────────────────────────────┨
┃ 37c97fa0-fa47-4d55-9970-e2aa6e1b50cf │ aws-secret-key          │ 🔶 aws         │ 🐳 docker-registry │ 715803424590.dkr.ecr.us-east-1.amazonaws.com ┃
┠──────────────────────────────────────┼─────────────────────────┼────────────────┼────────────────────┼──────────────────────────────────────────────┨
┃ d400e0c6-a8e7-4b95-ab34-0359229c5d36 │ aws-us-east-1           │ 🔶 aws         │ 🐳 docker-registry │ 715803424590.dkr.ecr.us-east-1.amazonaws.com ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

After having set up or decided on an AWS Service Connector to use to connect to the target ECR registry, you can register the AWS Container Registry as follows:

```sh
# Register the AWS container registry and reference the target ECR registry URI
zenml container-registry register <CONTAINER_REGISTRY_NAME> -f aws \
    --uri=<REGISTRY_URL>

# Connect the AWS container registry to the target ECR registry via an AWS Service Connector
zenml container-registry connect <CONTAINER_REGISTRY_NAME> -i
```

A non-interactive version that connects the AWS Container Registry to a target ECR registry through an AWS Service Connector:

```sh
zenml container-registry connect <CONTAINER_REGISTRY_NAME> --connector <CONNECTOR_ID>
```

{% code title="Example Command Output" %}
```
$ zenml container-registry connect aws-us-east-1 --connector aws-us-east-1 
Successfully connected container registry `aws-us-east-1` to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE      │ RESOURCE NAMES                               ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼────────────────────┼──────────────────────────────────────────────┨
┃ d400e0c6-a8e7-4b95-ab34-0359229c5d36 │ aws-us-east-1  │ 🔶 aws         │ 🐳 docker-registry │ 715803424590.dkr.ecr.us-east-1.amazonaws.com ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

As a final step, you can use the AWS Container Registry in a ZenML Stack:

```sh
# Register and set a stack with the new container registry
zenml stack register <STACK_NAME> -c <CONTAINER_REGISTRY_NAME> ... --set
```

{% hint style="info" %}
Linking the AWS Container Registry to a Service Connector means that your local Docker client is no longer authenticated to access the remote registry. If you need to manually interact with the remote registry via the Docker CLI, you can use the [local login Service Connector feature](../../how-to/auth-management/service-connectors-guide.md#configure-local-clients) to temporarily authenticate your local Docker client to the remote registry:

```sh
zenml service-connector login <CONNECTOR_NAME> --resource-type docker-registry
```

{% code title="Example Command Output" %}
```
$ zenml service-connector login aws-us-east-1 --resource-type docker-registry
⠼ Attempting to configure local client using service connector 'aws-us-east-1'...
WARNING! Your password will be stored unencrypted in /home/stefan/.docker/config.json.
Configure a credential helper to remove this warning. See
https://docs.docker.com/engine/reference/commandline/login/#credentials-store

The 'aws-us-east-1' Docker Service Connector connector was used to successfully configure the local Docker/OCI container registry client/SDK.
```
{% endcode %}
{% endhint %}
{% endtab %}
{% endtabs %}

For more information and a full list of configurable attributes of the AWS container registry, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-aws/#zenml.integrations.aws.container\_registries.aws\_container\_registry.AWSContainerRegistry).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
