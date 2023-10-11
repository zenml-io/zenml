---
description: Deploy a cloud stack when your Sandbox runs out.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Deploy a stack after using the Sandbox

Once your sandbox has run out or you want to work on real projects in a non-temporary environment, you'll want to deploy your own cloud stack and development environment. This guide will show you how to do it.

In order to deploy the equivalent of your own cloud stack and server as you were able to use in the Sandbox, you'll need two main things:

1. **A ZenML server** to run your pipelines on and to use as the central point-of-call for your deployment.
2. **A cloud stack** (or multiple stacks) on which to run your pipelines.

You'll have some options to consider along the way depending on whether you want to simply play around with ZenML a bit more versus getting serious for a production use-case. We'll cover these options in this guide.

## Deploy a ZenML server

Our full deployment guide is [available here](../deploy-zenml/deploy-zenml.md) and since we offer several options we recommend you read that once you've decided what path to take. If you are looking for something quick and don't mind if it is not production-grade, you can [use our Huggingface Spaces deployment](../deploy-zenml/deploy-using-huggingface-spaces.md) to get up and running in a few minutes.

If you are interested in a server deployment that is less ephemeral, you can use our `zenml deploy` CLI command as a simple but opinionated way to deploy a ZenML server. This will deploy to Kubernetes on one of the three big managed cloud platforms (i.e. AWS, GCP, Azure). You can read more about this in our [full deployment guide](../set-up-your-mlops-platform/deploy-zenml/deploy-with-zenml-cli.md).

For a bit more control over what gets deployed where, or for deploying to a pre-existing Kubernetes cluster you can [follow our Helm installation guide](../deploy-zenml/deploy-with-helm.md). You can follow this guide to deploy ZenML in any Kubernetes cluster using the Helm chart provided in our repository.

Once your server is deployed, you'll need to connect your client to it. You can connect to your deployed server using the `zenml connect` command. Read [this documentation page](../../../user-guide/starter-guide/connect-to-a-deployed-zenml.md#connect-your-client-to-the-server) for more information on how to do this.

## Deploy the relevant cloud stacks

Once your ZenML server is deployed, you may want to run your pipelines on the cloud or deployed infrastructure. This requires the deployment of cloud stacks. In the MLOps Platform Sandbox, some of these stacks were pre-deployed for you. To deploy individual stack components, [ZenML provides stack recipes](deploy-a-stack-post-sandbox.md) that can be easily deployed via the Command Line Interface (CLI) using the `zenml <stack-component> deploy ...` syntax.

### Deploying individual components

The `zenml deploy` command allows you to deploy individual components of your MLOps stack with a single command. For example, to deploy an MLflow tracking server on a GCP account, you can run:

```shell
zenml experiment-tracker deploy my_tracker --flavor=mlflow --cloud=gcp --project_id="zenml"
```

This will deploy an MLflow tracking server on your GCP account with the name `my_tracker`. You can then use this tracker to track your experiments. For more information on how to deploy individual stack components in this way, please refer to the [dedicated documentation page](deploy-a-stack-component.md).

## Where to go from here?

Once you have the server and stacks deployed, you can use them to run your pipelines. If you've done all this, now's probably also a good time to read [our 'Best Practices' guide](../../../user-guide/starter-guide/follow-best-practices.md) to get a sense of how to use ZenML in a production setting.
