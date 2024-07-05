# Welcome to the ZenML GCP Stack Deployment Tutorial

This tutorial will assist you in deploying a full ZenML GCP stack in your
GCP project using Deployment Manager. After the Deployment Manager deployment is
complete, you can register the ZenML stack with the ZenML server using an
auto-generated JSON stack representation.

## Let's get started!

**Duration**: <walkthrough-tutorial-duration duration=5></walkthrough-tutorial-duration>

**Prerequisites**: A GCP Cloud Billing account

Click on 'Start' to begin.

## Overview

To deploy the GCP infrastructure resources necessary for the ZenML stack, you be
asked to log in to your GCP project and then create a Deployment Manager
deployment.

After the Deployment Manager deployment is complete, you have to navigate to the
deployment outputs and fetch the `ZenMLStack` JSON output value which you will
use to register the ZenML stack with the ZenML server.

**NOTE**: The Deployment Manager deployment will create the following new
resources in your GCP project. Please ensure you have the necessary permissions
and are aware of any potential costs:

- A GCS bucket registered as a [ZenML artifact store](https://docs.zenml.io/stack-components/artifact-stores/gcp).
- A Google Artifact Registry registered as a [ZenML container registry](https://docs.zenml.io/stack-components/container-registries/gcp).
- Vertex AI registered as a [ZenML orchestrator](https://docs.zenml.io/stack-components/orchestrators/vertex).
- A GCP Service Account with the minimum necessary permissions to access the
above resources.
- An GCP Service Account access key used to give access to ZenML to connect to
the above resources through a [ZenML service connector](https://docs.zenml.io/how-to/auth-management/gcp-service-connector).

The Deployment Manager deployment will automatically create a GCP Service
Account secret key that will be shared with ZenML to give it permission to
access the resources created by the stack. You can revoke these permissions at
any time by deleting the Deployment Manager deployment in the GCP Cloud Console.

## Make sure you are authenticated with GCP

<walkthrough-project-setup>Select the GCP Project in which to deploy the stack.</walkthrough-project-setup>

```sh
gcloud config set project <YOUR_PROJECT_ID>
```

💡 Click the 'Copy to Cloud Shell' button to copy the command to your
terminal then replace `<YOUR_PROJECT_ID>` with your GCP project ID.

## Configure your deployment

Now, let's configure the ZenML stack deployment. You'll need to provide the
following information:

* <walkthrough-editor-select-regex filePath="gcp-gar-gcs-vertex-deploy.sh" regex="ZENML_STACK_NAME=.*">the name of the ZenML stack to deploy</walkthrough-editor-select-regex>
* <walkthrough-editor-select-regex filePath="gcp-gar-gcs-vertex-config.sh" regex="ZENML_STACK_REGION=.*">the GCP region to deploy the resources to</walkthrough-editor-select-regex>. Pick one from the [list of available regions](https://cloud.google.com/compute/docs/regions-zones) (e.g., `europe-west3`).

## Deploy the ZenML stack

Run the deployment script to deploy the stack with Deployment Manager:

```sh
./gcp-gar-gcs-vertex-deploy.sh
```

💡 Click the 'Copy to Cloud Shell' button to copy and run the command in your
terminal

## Register the ZenML stack with your ZenML server

If you reached this point, the ZenML stack resources have been provisioned in
your GCP project and you can view and manage the resources created in the GCP
Deployment Manager Console by following the URL provided in the output.

However, the ZenML Stack has not yet been registered with the ZenML server. You
have to do that manually by fetching the JSON representation of the ZenML stack
from the deployment outputs.

You can start by accessing the deployment outputs in the GCP Deployment Manager
Console by following the URL provided in the output in the previous step,
navigating to the `Layout` tab, and copying the `ZenMLStack` final output value.
This is a JSON object that contains the details of the ZenML stack that was
deployed.

Finally, you can use this JSON to manually register the stack by calling the
`zenml stack import` CLI command.

## Congratulations

<walkthrough-conclusion-trophy></walkthrough-conclusion-trophy>

If you've completed the tutorial steps successfully, then you're all set!

The ZenML stack has been deployed in your GCP project and you manually
registered the stack with the ZenML server. You can view and manage
the resources created in [the GCP Deployment Manager Console](https://console.cloud.google.com/deployments).

**Don't forget to clean up**: When you're done using the ZenML GCP stack, be
sure to delete [the GCP Deployment Manager deployment](https://console.cloud.google.com/deployments)
to avoid unnecessary charges.
