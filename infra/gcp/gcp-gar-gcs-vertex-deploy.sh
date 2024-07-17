#!/bin/bash

set -e
set -u

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

if [ -z "$ZENML_SERVER_URL" ] || [ -z "$ZENML_SERVER_API_TOKEN" ]; then
    echo "ERROR: The ZENML_SERVER_URL and ZENML_SERVER_API_TOKEN variables must be set."
    echo "Please set these variables in the script before running it."
    exit 1
fi

if [ -z "$ZENML_STACK_NAME" ]; then
    echo "ERROR: The ZENML_STACK_NAME variable must be set."
    echo "Please set this variable in the script before running it."
    exit 1
fi

if [ -z "$ZENML_STACK_REGION" ]; then
    echo "ERROR: The ZENML_STACK_REGION variable must be set."
    echo "Please set this variable in the script before running it."
    exit 1
fi

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
# * Cloud Build - ZenML uses the Cloud Build GCP service to build and push Docker images.
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
    "aiplatform.googleapis.com"
    "cloudresourcemanager.googleapis.com"
    "cloudbuild.googleapis.com"
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

# Create the Deployment Manager deployment
#
# The following command deploys the stack with Deployment Manager
echo
echo "##################################################"
echo "Creating the Deployment Manager deployment..."
echo "##################################################"
echo
echo "Please wait for the deployment to complete. This should not take more than 1-2 minutes."
echo "You may also monitor the deployment as it's being created at: https://console.cloud.google.com/dm/deployments/details/$ZENML_STACK_NAME?project=$PROJECT_ID"
echo

set +e
gcloud deployment-manager deployments create \
    --template gcp-gar-gcs-vertex.jinja $ZENML_STACK_NAME \
    --properties region:"$ZENML_STACK_REGION",zenmlServerURL:"$ZENML_SERVER_URL",zenmlServerAPIToken:"$ZENML_SERVER_API_TOKEN"
# Fetch the exit code of the deployment
DEPLOYMENT_EXIT_CODE=$?
set -e

if [ $DEPLOYMENT_EXIT_CODE -ne 0 ]; then
    echo "ERROR: The deployment failed. Please check the logs for more information."
    echo
    echo "This usually happens for one of the following reasons:"
    echo
    echo "1. Temporary issues related to enabling services or granting permissions in newly created projects. This is "
    echo "usually solved by deleting and retrying the deployment."
    echo "2. One of the GCP services required for the stack (S3 or GCP Artifact Registry) is not available in the "
    echo "region you selected. In this case, please configure a different region and try again."
    echo
    echo "To retry the deployment after you addressed the possible cause, you can run the following commands:"
    echo
    echo "gcloud deployment-manager deployments delete $ZENML_STACK_NAME"
    echo "./gcp-gar-gcs-vertex-deploy.sh"
    echo
    exit 1
fi

echo
echo "##################################################"
echo "Extracting the Deployment Manager deployment output..."
echo "##################################################"
echo

manifest=$(gcloud deployment-manager manifests list --deployment $ZENML_STACK_NAME --format="value(name)")
zenml_stack_json=$(
    gcloud deployment-manager manifests describe $manifest --deployment $ZENML_STACK_NAME --format="value(layout)" \
    | python -c 'import sys, yaml; print(yaml.safe_load(sys.stdin)["resources"][0]["outputs"][-1]["finalValue"])'
)

echo
echo "##################################################"
echo "Registering the ZenML stack with the ZenML server..."
echo "##################################################"
echo

set +e
# Register the ZenML stack with the ZenML server
curl -X POST "$ZENML_SERVER_URL/api/v1/workspaces/default/full-stack" \
    -H "Authorization: Bearer $ZENML_SERVER_API_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$zenml_stack_json"
# Fetch the exit code of the registration
REGISTRATION_EXIT_CODE=$?
set -e

if [ $REGISTRATION_EXIT_CODE -ne 0 ]; then
    echo "ERROR: The ZenML stack registration failed. Please check the logs for more information."
    echo
    echo "This could happen if the ZenML server URL or API token is incorrect. Please check the configuration and try again:"
    echo
    echo "gcloud deployment-manager deployments delete $ZENML_STACK_NAME"
    echo "./gcp-gar-gcs-vertex-deploy.sh"
    echo
    exit 1
fi

# Print the deployment URL
#
echo "##################################################"
echo
echo
echo "Congratulations ! The ZenML Deployment Manager stack has been deployed. You can access it at the following URL:"
echo
echo "https://console.cloud.google.com/dm/deployments/details/$ZENML_STACK_NAME?project=$PROJECT_ID"
echo