#!/bin/bash

set -e

# Configure your deployment
#
# The following variables must be configured before running the deployment
# script:
#
# * ZENML_STACK_NAME - The name of the ZenML stack to deploy. This name will be
# used to identify the stack in the ZenML server and the GCP Deployment Manager.
# * ZENML_STACK_REGION - The GCP region to deploy the resources to. Pick one
# from the list of available regions documented at: https://cloud.google.com/about/locations
# * ZENML_SERVER_URL: The URL where your ZenML server is running
# * ZENML_SERVER_API_TOKEN: The API token used to authenticate with your ZenML
# server. This would have been provided to you in the ZenML CLI or the ZenML
# dashboard when you triggered this tutorial.

### BEGIN CONFIGURATION ###
ZENML_STACK_NAME=zenml-gcp-stack
ZENML_STACK_REGION=europe-west3
ZENML_SERVER_URL=
ZENML_SERVER_API_TOKEN=
### END CONFIGURATION ###

# Extract the project ID and project number from the gcloud configuration
PROJECT_ID=$(gcloud config get-value project)

if [ -z "$PROJECT_ID" ]; then
    echo "ERROR: No project is set in the gcloud configuration. Please set a "
    echo "project using 'gcloud config set project PROJECT_ID' before running this script."
    exit 1
fi

PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

# Enable the necessary services
#
# The following services must be enabled in your GCP project:
#
# * Deployment Manager - used to provision infrastructure resources.
# * IAM API - used to manage permissions.
# * Artifact Registry API - ZenML uses the Artifact Registry GCP service to store and manage Docker images.
# * Cloud Storage API - ZenML uses the Cloud Storage GCP service to store and manage data.
# * Vertex AI API - ZenML uses the Vertex AI GCP service to manage machine learning resources.
# * Cloud Functions and Cloud Build API - used to automatically register the ZenML stack in the ZenML server.
echo
echo "##################################################"
echo "Enabling necessary GCP services..."
echo "##################################################"
echo
# Array of services to enable
services=(
    "deploymentmanager.googleapis.com"
    "iam.googleapis.com"
    "artifactregistry.googleapis.com"
    "storage-api.googleapis.com"
    "ml.googleapis.com"
    "cloudfunctions.googleapis.com"
    "cloudbuild.googleapis.com"
    "cloudresourcemanager.googleapis.com"
)

# Enable the services
gcloud services enable "${services[@]}"

# Grant Deployment Manager the necessary permissions
#
# The GCP Deployment Manager uses the Google APIs Service Agent
# (https://cloud.google.com/compute/docs/access/service-accounts#google_apis_service_agent)
# to create deployment resources. You must first grant this service the
# appropriate permissions to assign roles to the GCP service account that will be
# created for the ZenML stack.
echo
echo "##################################################"
echo "Granting Deployment Manager the necessary permissions..."
echo "##################################################"
echo
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$PROJECT_NUMBER@cloudservices.gserviceaccount.com" \
    --role="roles/resourcemanager.projectIamAdmin" \
    --condition=None

# Grant the Compute Engine default service account the necessary permissions
#
# The GCP Cloud Functions uses the default compute service account
# (https://cloud.google.com/functions/docs/securing/function-identity#runtime-sa)
# to run. You must first grant this service the appropriate permissions to
# create and manage Artifact Registry resources.
echo
echo "##################################################"
echo "Granting Deployment Manager the necessary permissions..."
echo "##################################################"
echo
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$PROJECT_NUMBER-compute@cloudservices.gserviceaccount.com" \
    --role="roles/artifactregistry.admin" \
    --condition=None


# Create the Deployment Manager deployment
#
# The following command deploys the stack with Deployment Manager
echo
echo "##################################################"
echo "Creating the Deployment Manager deployment..."
echo "##################################################"
echo
echo echo "Deployment will be created at: https://console.cloud.google.com/dm/deployments/details/$ZENML_STACK_NAME?project=$PROJECT_ID"
echo
gcloud deployment-manager deployments create \
    --template gcp-gar-gcs-vertex.jinja $ZENML_STACK_NAME \
    --properties region:"$ZENML_STACK_REGION",zenmlServerURL:"$ZENML_SERVER_URL",zenmlServerAPIToken:"$ZENML_SERVER_API_TOKEN"

# Print the deployment URL
#
echo "##################################################"
echo
echo
echo "Congratulations ! The ZenML stack has been deployed. You can access it at the following URL:"
echo
echo "https://console.cloud.google.com/dm/deployments/details/$ZENML_STACK_NAME?project=$PROJECT_ID"