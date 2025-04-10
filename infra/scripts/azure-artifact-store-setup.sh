#!/usr/bin/env bash

# Exit on error
set -e

# Name used for the stack, service connector, and artifact store and as a prefix
# for all created resources
NAME="${NAME:-zenml-azure}"

# Region to create the resources in
LOCATION="${LOCATION:-westeurope}"

# Generate random suffix if not externally set
if [ -z "${RANDOM_SUFFIX}" ]; then
    RANDOM_SUFFIX=$(LC_ALL=C tr -dc 'a-z0-9' < /dev/urandom | fold -w 8 | head -n 1)
fi
PREFIX="${NAME}-${RANDOM_SUFFIX}"

# Azure resource names
RESOURCE_GROUP="${PREFIX}"
STORAGE_ACCOUNT="${PREFIX//-/}"  # Remove hyphens as storage accounts don't allow them
CONTAINER_NAME="${PREFIX}"
SERVICE_CONNECTOR_NAME="${NAME}-blob"
ARTIFACT_STORE_NAME="${NAME}-blob"
SP_NAME="${PREFIX}"

# Function to print cleanup instructions
print_cleanup_instructions() {
    echo
    echo "To cleanup the stack and resources, run the following commands in the order given:"
    echo "(some commands may fail if resources don't exist)"
    echo
    echo "zenml stack delete -y $NAME"
    echo "zenml artifact-store delete $ARTIFACT_STORE_NAME"
    echo "zenml service-connector delete $SERVICE_CONNECTOR_NAME"
    echo "az group delete --name $RESOURCE_GROUP --yes"
    echo "az ad sp delete --id $SP_ID"
}

# Set up trap to call cleanup instructions on script exit
trap print_cleanup_instructions EXIT

# Create resource group
echo "Creating Azure resource group: $RESOURCE_GROUP"
az group create --name "$RESOURCE_GROUP" --location "$LOCATION"

# Create storage account
echo "Creating Azure storage account: $STORAGE_ACCOUNT"
az storage account create \
    --name "$STORAGE_ACCOUNT" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --sku Standard_LRS \
    --encryption-services blob

# Create container
echo "Creating Azure storage container: $CONTAINER_NAME"
az storage container create \
    --name "$CONTAINER_NAME" \
    --account-name "$STORAGE_ACCOUNT"

# Create service principal
echo "Creating Azure service principal: $SP_NAME"
SP_CREATE=$(az ad sp create-for-rbac --name "$SP_NAME" --skip-assignment)
SP_ID=$(echo "$SP_CREATE" | jq -r .appId)
SP_PASSWORD=$(echo "$SP_CREATE" | jq -r .password)
SP_TENANT=$(echo "$SP_CREATE" | jq -r .tenant)

# Get storage account id
STORAGE_ID=$(az storage account show \
    --name "$STORAGE_ACCOUNT" \
    --resource-group "$RESOURCE_GROUP" \
    --query id --output tsv)

# Assign Storage Blob Data Contributor role to service principal
echo "Assigning Storage Blob Data Contributor role to service principal"
az role assignment create \
    --assignee "$SP_ID" \
    --role "Storage Blob Data Contributor" \
    --scope "$STORAGE_ID"

# Give Azure time to propagate the role assignment
sleep 30

# Create ZenML service connector
zenml service-connector register "$SERVICE_CONNECTOR_NAME" \
    --type azure \
    --auth-method service-principal \
    --resource-type blob-container \
    --resource-id "$CONTAINER_NAME" \
    --resource_group="$RESOURCE_GROUP" \
    --storage_account="$STORAGE_ACCOUNT" \
    --client_id="$SP_ID" \
    --client_secret="$SP_PASSWORD" \
    --tenant_id="$SP_TENANT"

# Create ZenML artifact store
zenml artifact-store register "$ARTIFACT_STORE_NAME" \
    --flavor azure \
    --path="az://${CONTAINER_NAME}" \
    --connector "$SERVICE_CONNECTOR_NAME"

# Create ZenML stack
zenml stack register "$NAME" \
    -a "${ARTIFACT_STORE_NAME}" \
    -o default

echo "Successfully created Azure resources and ZenML stack:"
echo "- Resource Group: $RESOURCE_GROUP"
echo "- Storage Account: $STORAGE_ACCOUNT"
echo "- Container: $CONTAINER_NAME"
echo "- Service Principal: $SP_NAME"
echo "- ZenML service connector: $SERVICE_CONNECTOR_NAME"
echo "- ZenML artifact store: $ARTIFACT_STORE_NAME"
echo "- ZenML stack: $NAME"
echo
