#!/usr/bin/env bash

# Steps to apply the patch:
# - Checkout release branch
# - Remove local dashboard files: `rm -r src/zenml/zen_server/dashboard`
# - Copy patched dashboard files
# - Apply backend patches
# - Run this script
# - Apply/restart server pods for relevant tenants

set -e

# Default to staging environment and disable both build and push by default
STAGING_AWS_ACCOUNT_ID=339712793861
PROD_AWS_ACCOUNT_ID=715803424590
AWS_ACCOUNT_ID=$STAGING_AWS_ACCOUNT_ID
DO_BUILD=false
DO_PUSH=false
DO_LOGIN=false
ZENML_VERSION=""
COOKIE_NAME="zenml_cloud_staging_cloudapi_zenml_io_access_token"
# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --staging)
            AWS_ACCOUNT_ID=$STAGING_AWS_ACCOUNT_ID
            shift
            ;;
        --prod)
            AWS_ACCOUNT_ID=$PROD_AWS_ACCOUNT_ID
            COOKIE_NAME="zenml_cloud_cloudapi_zenml_io_access_token"
            shift
            ;;
        --build)
            DO_BUILD=true
            shift
            ;;
        --push)
            DO_PUSH=true
            shift
            ;;
        --login)
            DO_LOGIN=true
            shift
            ;;
        --version)
            ZENML_VERSION="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--version VERSION] [--staging|--prod] [--build] [--push] [--login]"
            echo "At least one of --build or --push must be specified"
            exit 1
            ;;
    esac
done

# If version not provided, try to read from VERSION file
if [ -z "$ZENML_VERSION" ]; then
    if [ -f "src/zenml/VERSION" ]; then
        ZENML_VERSION=$(cat src/zenml/VERSION)
    fi
    if [ -z "$ZENML_VERSION" ]; then
        echo "Error: Could not determine ZenML version. Either provide --version argument or ensure src/zenml/VERSION file exists"
        echo "Usage: $0 [--version VERSION] [--staging|--prod] [--build] [--push] [--login]"
        echo "At least one of --build or --push must be specified"
        exit 1
    fi
fi

# Ensure at least one operation is selected
if [ "$DO_BUILD" = false ] && [ "$DO_PUSH" = false ]; then
    echo "Error: At least one of --build or --push must be specified"
    echo "Usage: $0 [--version VERSION] [--staging|--prod] [--build] [--push] [--login]"
    exit 1
fi

# Perform ECR login if requested
if [ "$DO_LOGIN" = true ]; then
    aws ecr get-login-password --region eu-central-1 | docker login --username AWS --password-stdin 715803424590.dkr.ecr.eu-central-1.amazonaws.com
    aws ecr get-login-password --region eu-central-1 | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.eu-central-1.amazonaws.com
fi

DASHBOARD_BRANCH=patch-legacy-tenants/${ZENML_VERSION}

IMAGE_REPOSITORY=$(python -c "from packaging import version; repo = 'zenml-pro-server' if version.parse('${ZENML_VERSION}') >= version.parse('0.73.0') else 'zenml-cloud-server'; print(repo)")
BASE_IMAGE_NAME=715803424590.dkr.ecr.eu-central-1.amazonaws.com/${IMAGE_REPOSITORY}:${ZENML_VERSION}-backup
IMAGE_NAME=${AWS_ACCOUNT_ID}.dkr.ecr.eu-central-1.amazonaws.com/${IMAGE_REPOSITORY}:${ZENML_VERSION}

# Conditionally execute build
if [ "$DO_BUILD" = true ]; then
    docker build --platform linux/amd64 \
        -f Dockerfile.patch \
        --build-arg BASE_IMAGE=${BASE_IMAGE_NAME} \
        --build-arg ZENML_VERSION=${ZENML_VERSION} \
        --build-arg DASHBOARD_BRANCH=${DASHBOARD_BRANCH} \
        --build-arg COOKIE_NAME=${COOKIE_NAME} \
        -t ${IMAGE_NAME} \
        ./
fi

# Conditionally execute push
if [ "$DO_PUSH" = true ]; then
    docker push ${IMAGE_NAME}
fi
