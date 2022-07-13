---
description: Store container images in Amazon ECR
---

The AWS container registry is a [container registry](./overview.md) flavor provided with
the ZenML `aws` integration and uses [Amazon ECR](https://aws.amazon.com/ecr/) to store 
container images.

## When to use it

You should use the AWS container registry if:
* one or more components of your stack need to pull or push container images.
* you have access to AWS ECR. If you're not using AWS, take a look at the
 other [container registry flavors](./overview.md#container-registry-flavors).

## How to deploy it

The ECR registry is automatically activated once you create an AWS account.
However, you'll need to create a `Repository` in order to push container images to it:
* Go to the [ECR website](https://console.aws.amazon.com/ecr).
* Make sure the correct region is selected on the top right.
* Click on `Create repository`.
* Create a private repository called `zenml-kubernetes`, `zenml-kubeflow` or `zenml-sagemaker`
depending on which [orchestrator](../orchestrators/overview.md) or 
[step operator](../step_operators/overview.md) you're using in your stack.
## URI format

The AWS container registry URI should have the following format:
```shell
<ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com
# Examples:
123456789.dkr.ecr.eu-west-2.amazonaws.com
987654321.dkr.ecr.ap-south-1.amazonaws.com
135792468.dkr.ecr.af-south-1.amazonaws.com
```

To figure our the URI for your registry:
* Go to the [AWS console](https://console.aws.amazon.com/) and click on your user account in the top right to see the `Account ID`.
* Go [here](https://docs.aws.amazon.com/general/latest/gr/rande.html#regional-endpoints) and choose the region in which you would like to store your container images. Make sure to choose a nearby region for faster access.
* Once you have both these values, fill in the values in this template
`<ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com` to get your container registry URI.
## How to use it

To use the AWS container registry, we need:
* The ZenML `aws` integration installed. If you haven't done so, run 
    ```shell
    zenml integration install aws
    ```
* [Docker](https://www.docker.com) installed and running.
* The [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) installed and authenticated.
* The registry URI. Check out the [previous section](#uri-format) on the URI format and how
to get the URI for your registry.

We can then register the container registry and use it in our active stack:
```shell
zenml container-registry register <NAME> \
    --flavor=aws \
    --uri=<REGISTRY_URI>

# Add the container registry to the active stack
zenml stack update -c <NAME>
```

Additionally, we'll need to login to the container registry so Docker can pull and push images:
```shell
# Fill your REGISTRY_URI and REGION in the placeholders in the following command.
# You can find the REGION as part of your REGISTRY_URI: `<ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com`
aws ecr get-login-password --region <REGION> | docker login --username AWS --password-stdin <REGISTRY_URI>
```

For more information and a full list of configurable attributes of the AWS container registry, check out the 
[API Docs](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.aws.container_registries.aws_container_registry.AWSContainerRegistry).
