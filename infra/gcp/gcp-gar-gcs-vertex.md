# Welcome to the ZenML GCP Stack Deployment Tutorial

This tutorial will assist you in deploying a full ZenML GCP stack in your
GCP project using Deployment Manager. After the Deployment Manager deployment is
complete, you can return to the CLI or dashboard to view details about the
associated ZenML stack that is automatically registered with ZenML.

## Let's get started!

**Time to complete**: About 5 minutes

**Prerequisites**: A GCP Cloud Billing account

Click on 'Start' to begin.

## Deployment Overview

**Tip:** Click the **Continue** button to proceed to the actual deployment if
you are already familiar with the deployment process or if you are eager to get
started.

The Deployment Manager deployment will create the following new resources in
your GCP project. Please ensure you have the necessary permissions and are aware
of any potential costs:

- A GCS bucket registered as a [ZenML artifact store](https://docs.zenml.io/stack-components/artifact-stores/gcp).
- A Google Artifact Registry registered as a [ZenML container registry](https://docs.zenml.io/stack-components/container-registries/gcp).
- Vertex AI registered as a [ZenML orchestrator](https://docs.zenml.io/stack-components/orchestrators/vertex).
- A GCP Service Account with the minimum necessary permissions to access the
above resources.
- An GCP Service Account access key used to give access to ZenML to connect to
the above resources through a [ZenML service connector](https://docs.zenml.io/how-to/auth-management/gcp-service-connector).

The Deployment Manager deployment will automatically create a GCP Service
Account secret key and will share it with ZenML to give it permission to access
the resources created by the stack. You can revoke these permissions at any time
by deleting the Deployment Manager deployment in the GCP Cloud Console.

## 1. Make sure you are authenticated with GCP

```sh
gcloud config set project <YOUR_PROJECT_ID>
```

💡 Click the 'Copy to Cloud Shell' button to copy the command to your
terminal then replace `<YOUR_PROJECT_ID>` with your GCP project ID.

❗ Billing account for the project must be enabled for activation of
service APIs.

## 2. Enable the necessary services

ZenML uses the Deployment Manager GCP service to deploy the stack. The following
services must be enabled in your GCP project:

```sh
gcloud services enable deploymentmanager.googleapis.com
gcloud services enable serviceusage.googleapis.com
```

💡 Click the 'Copy to Cloud Shell' button to copy and run the commands in your terminal.

## 3. Grant Deployment Manager the necessary permissions

This tutorial uses GCP Deployment Manager to create a GCP Service Account and
use its credentials to connect ZenML to the GCP resources that are about to be
provisioned in your project. For this reason you must first grant the
appropriate permissions to the Google APIs service account that Deployment
Manager uses to create resources in your project.

```sh
PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$PROJECT_NUMBER@cloudservices.gserviceaccount.com" \
    --role="roles/iam.roleAdmin" \
    --role="roles/resourcemanager.projectIamAdmin" \
    --condition=None
```

💡 Click the 'Copy to Cloud Shell' button to copy and run the commands in your terminal.

## 4. Configure your deployment

Now, let's configure the ZenML stack deployment. You'll need to provide the
following information:

* a unique name for the ZenML stack and deployment: <walkthrough-editor-select-regex filePath="gcp-gar-gcs-vertex-config.yaml" regex="name: .*"><walkthrough-editor-select-regex>
* a unique string value to use to name all created GCP resources. Can include lowercase alphanumeric characters and hyphens and must be between 6-32 characters in length: <walkthrough-editor-select-regex filePath="gcp-gar-gcs-vertex-config.yaml" regex="resourceNameSuffix: .*"><walkthrough-editor-select-regex>
* the GCP region to deploy the resources to: <walkthrough-editor-select-regex filePath="gcp-gar-gcs-vertex-config.yaml" regex="region: .*"><walkthrough-editor-select-regex>
* the URL where your ZenML server is running: <walkthrough-editor-select-regex filePath="gcp-gar-gcs-vertex-config.yaml" regex="zenmlServerUrl: .*"><walkthrough-editor-select-regex>
* an API token to authenticate with your ZenML server: <walkthrough-editor-select-regex filePath="gcp-gar-gcs-vertex-config.yaml" regex="zenmlServerAPIToken: .*"><walkthrough-editor-select-regex> 

## 5. Run the following command to deploy the stack with Deployment Manager

```sh
gcloud deployment-manager deployments create zenml-gcp-stack --config gcp-gar-gcs-vertex-config.yaml
```

💡 Click the 'Copy to Cloud Shell' button to copy and run the commands in your terminal.

## Congratulations

<walkthrough-conclusion-trophy></walkthrough-conclusion-trophy>

If the previous command completed successfully, then you're all set!

The ZenML stack has been deployed in your GCP project. You can view and manage
the resources created in [the GCP Deployment Manager Console](https://console.cloud.google.com/deployments).

If you triggered this tutorial from the ZenML dashboard or the ZenML CLI, the
ZenML stack has already been registered with your ZenML deployment and you
should now switch back to the ZenML dashboard or the ZenML CLI to continue your
workflow.

**Don't forget to clean up**: When you're done using the ZenML GCP stack, be
sure to delete [the GCP Deployment Manager deployment](https://console.cloud.google.com/deployments)
to avoid unnecessary charges.
