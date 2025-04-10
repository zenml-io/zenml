#!/usr/bin/env bash

# Exit on error
set -e

# Name used for the stack, service connector, and artifact store and as a prefix
# for all created resources
NAME="${NAME:-zenml-gcp}"

# Region to create the bucket in
REGION="${REGION:-europe-west3}"

# Project ID is required for GCP
if [ -z "${PROJECT_ID}" ]; then
    # Try to get the default project from gcloud configuration
    DEFAULT_PROJECT=$(gcloud config get-value project 2>/dev/null)
    if [ -n "${DEFAULT_PROJECT}" ] && [ "${DEFAULT_PROJECT}" != "(unset)" ]; then
        echo "Using default GCP project: ${DEFAULT_PROJECT}"
        PROJECT_ID="${DEFAULT_PROJECT}"
    else
        echo "ERROR: PROJECT_ID environment variable must be set and no default project is configured in gcloud"
        echo "You can either:"
        echo "  1. Set the PROJECT_ID environment variable"
        echo "  2. Set a default project: gcloud config set project YOUR_PROJECT_ID"
        exit 1
    fi
fi

# Generate random suffix if not externally set
if [ -z "${RANDOM_SUFFIX}" ]; then
    RANDOM_SUFFIX=$(LC_ALL=C tr -dc 'a-z0-9' < /dev/urandom | fold -w 8 | head -n 1)
fi
PREFIX="${NAME}-${RANDOM_SUFFIX}"

BUCKET_NAME="${PREFIX}"
SERVICE_ACCOUNT_NAME="${PREFIX}"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
KEY_FILE="key-${SERVICE_ACCOUNT_EMAIL}.json"
SERVICE_CONNECTOR_NAME="${NAME}-gcs"
ARTIFACT_STORE_NAME="${NAME}-gcs"

# Function to print cleanup instructions
print_cleanup_instructions() {
    echo
    echo "To cleanup the stack and resources, run the following commands in the order given:"
    echo "(some commands may fail if resources don't exist)"
    echo
    echo "zenml stack delete -y $NAME"
    echo "zenml artifact-store delete $ARTIFACT_STORE_NAME"
    echo "zenml service-connector delete $SERVICE_CONNECTOR_NAME"
    echo "rm $KEY_FILE"
    echo "gcloud iam service-accounts delete $SERVICE_ACCOUNT_EMAIL --quiet"
    echo "gcloud storage rm --recursive gs://$BUCKET_NAME"
}

# Set up trap to call cleanup instructions on script exit
trap print_cleanup_instructions EXIT

# Create GCS bucket
echo "Creating GCS bucket: $BUCKET_NAME"
gsutil mb -l "$REGION" "gs://$BUCKET_NAME"

# Create service account
echo "Creating service account: $SERVICE_ACCOUNT_NAME"
gcloud iam service-accounts create "$SERVICE_ACCOUNT_NAME" \
    --display-name "ZenML Artifact Store Service Account"

# Grant the service account permissions to access the bucket
echo "Granting bucket permissions to service account"
gsutil iam ch \
    "serviceAccount:$SERVICE_ACCOUNT_EMAIL:roles/storage.objectViewer" \
    "gs://$BUCKET_NAME"
gsutil iam ch \
    "serviceAccount:$SERVICE_ACCOUNT_EMAIL:roles/storage.objectCreator" \
    "gs://$BUCKET_NAME"
gsutil iam ch \
    "serviceAccount:$SERVICE_ACCOUNT_EMAIL:roles/storage.bucketViewer" \
    "gs://$BUCKET_NAME"

# Create and download service account key
echo "Creating service account key"
gcloud iam service-accounts keys create "$KEY_FILE" \
    --iam-account="$SERVICE_ACCOUNT_EMAIL"

# Create ZenML service connector
zenml service-connector register "$SERVICE_CONNECTOR_NAME" \
    --type gcp \
    --auth-method service-account \
    --resource-type gcs-bucket \
    --resource-id "$BUCKET_NAME" \
    --project_id="$PROJECT_ID" \
    --service_account_json="@$KEY_FILE"

# Create ZenML artifact store
zenml artifact-store register "$ARTIFACT_STORE_NAME" \
    --flavor gcp \
    --path="gs://${BUCKET_NAME}" \
    --connector "$SERVICE_CONNECTOR_NAME"

# Create ZenML stack
zenml stack register "$NAME" \
    -a "${ARTIFACT_STORE_NAME}" \
    -o default

rm "$KEY_FILE"

echo "Successfully created GCP resources and ZenML stack:"
echo "- GCS bucket: $BUCKET_NAME"
echo "- Service Account: $SERVICE_ACCOUNT_EMAIL"
echo "- ZenML service connector: $SERVICE_CONNECTOR_NAME"
echo "- ZenML artifact store: $ARTIFACT_STORE_NAME"
echo "- ZenML stack: $NAME"
echo
