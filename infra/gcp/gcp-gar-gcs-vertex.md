# Welcome to the ZenML GCP Stack Deployment Tutorial

This tutorial will assist you in deploying a full ZenML GCP stack in your
GCP project using Deployment Manager. After the Deployment Manager deployment is
complete, you can return to the CLI or dashboard to view details about the
associated ZenML stack that is automatically registered with ZenML.

## Let's get started!

**Duration**: <walkthrough-tutorial-duration duration=5></walkthrough-tutorial-duration>

**Prerequisites**:

* A GCP Cloud Billing account
* ZenML Server URL and API token

Click on 'Start' to begin.

## Make sure you are authenticated with GCP

<walkthrough-project-setup>Select the GCP Project in which to deploy the stack.</walkthrough-project-setup>

## Configure your deployment

Now, let's configure the ZenML stack deployment.

You were provided with a set of configuration values when you triggered this
flow through the ZenML dashboard or CLI that looks like the following:

```
### BEGIN CONFIGURATION ###
ZENML_STACK_NAME=zenml-gcp-stack
ZENML_STACK_REGION=europe-west3
ZENML_SERVER_URL=
ZENML_SERVER_API_TOKEN=
### END CONFIGURATION ###
```

To configure your deployment, you need to simply copy these values and paste
them <walkthrough-editor-select-regex filePath="gcp-gar-gcs-vertex-deploy.sh" regex="### BEGIN CONFIGURATION.*">into the stack deployment script</walkthrough-editor-select-regex>.

## Deploy the ZenML stack

Run the deployment script to deploy the stack with Deployment Manager:

```sh
./gcp-gar-gcs-vertex-deploy.sh
```

💡 Click the 'Copy to Cloud Shell' button to copy and run the command in your
terminal

## Congratulations

<walkthrough-conclusion-trophy></walkthrough-conclusion-trophy>

If the previous command completed successfully, then you're all set!

The ZenML stack resources have been provisioned in your GCP project. You can
view and manage the resources created in the GCP Deployment Manager Console by
following the URL provided in the output.

The ZenML stack has also been automatically registered with your ZenML server
and you may now close the Cloud Shell session and switch back to the ZenML
dashboard or the ZenML CLI to continue your workflow.

**Don't forget to clean up**: When you're done using the ZenML GCP stack, be
sure to delete the GCP Deployment Manager deployment to avoid unnecessary
charges. You will need to delete the data in your GCS bucket manually before
the deployment can be deleted.
