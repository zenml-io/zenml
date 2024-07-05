# Welcome to Google Cloud Shell!

This tutorial will walk you through deploying a full ZenML stack to your GCP
project.

## 1. Make sure you are authenticated with GCP

```sh
gcloud config set project <YOUR_PROJECT_ID>
```

**IMPORTANT**: Billing account for the project must be enabled for activation of
service APIs.

## 2. Enable the necessary services

ZenML uses the Deployment Manager GCP service to deploy the stack. The following
services must be enabled in your GCP project:

```sh
gcloud services enable deploymentmanager.googleapis.com
gcloud services enable serviceusage.googleapis.com
```

## 3. Grant Deployment Manager the necessary permissions

To create custom roles using Deployment Manager, you must first grant the
appropriate permissions to the Google APIs service account. This account is
created by default for each organization and project.

```sh
PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$PROJECT_NUMBER@cloudservices.gserviceaccount.com" \
    --role="roles/iam.roleAdmin" \
    --role="roles/resourcemanager.projectIamAdmin" \
    --condition=None
```

## 4. Run the following command to deploy the stack with Deployment Manager

```sh
gcloud deployment-manager deployments create zenml-gcp-stack --config gcp-gar-gcs-vertex-config.yaml
```