---
description: Deploy a cloud stack when your Sandbox runs out.
---



# Deploying and set up a cloud stack of your own

For once your sandbox has run out or you want to work on real projects in a
non-temporary environment, you'll want to deploy your own cloud stack and
development environment. This guide will show you how to do this.

To deploy the equivalent of your own cloud stack and server as you were able to
use in the Sandbox, you'll need two main things:

1. A server to run your pipelines on and to use as the central point of call for your
   ZenML deployment.
2. A cloud stack (or multiple stacks) on which to run your pipelines.

You'll have some options to consider along the way depending on whether you want
to simply play around with ZenML a bit more versus getting serious for a
production use-case. We'll cover these options in this guide.

## Deploy a server

Our full deployment guide is [available
here](../../../platform-guide/set-up-your-mlops-platform/deploy-zenml/deploy-zenml.md)
and since we offer several options we recommend you read that once you've
decided what path to take. If you are looking for something quick and don't mind
if it is not production-grade, you can [use our Huggingface Spaces
deployment](../../../platform-guide/set-up-your-mlops-platform/deploy-zenml/deploy-using-huggingface-spaces.md)
to get up and running in a few minutes.

If you are interested in a server deployment that is less ephemeral, you can use
our `zenml deploy` CLI command as a simple but opinionated way to deploy a ZenML
server. This will deploy to Kubernetes on one of the three big managed cloud
platforms (i.e. AWS, GCP, Azure). You can read more about this in our [full
deployment
guide](../../../platform-guide/set-up-your-mlops-platform/deploy-zenml/deploy-with-zenml-cli.md).

For a bit more control over what gets deployed where, or for deploying to a
pre-existing Kubernetes cluster you can [follow our Helm installation
guide](../deploy-zenml/deploy-with-helm.md). You can follow this guide to deploy
ZenML in any Kubernetes cluster using the Helm chart provided in our repository.

Once your server is deployed, you'll need to connect your client to it. You can connect to your deployed server using the `zenml connect` command. Read
[this documentation
page](../../../user-guide/starter-guide/connect-to-a-deployed-zenml.md#connect-your-client-to-the-server)
for more information on how to do this.

## Deploy relevant cloud stacks

## Use those stacks / where go from here

