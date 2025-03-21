# Steps to apply the patch:
# - Checkout release branch
# - Remove local dashboard files: `rm -r src/zenml/zen_server/dashboard`
# - Copy patched dashboard files
# - Apply backend patches
# - Run this script
# - Apply/restart server pods for relevant tenants

aws ecr get-login-password --region eu-central-1 | docker login --username AWS --password-stdin 715803424590.dkr.ecr.eu-central-1.amazonaws.com

ZENML_VERSION=0.75.0

IMAGE_REPOSITORY=$(python -c "from packaging import version; repo = 'zenml-pro-server' if version.parse('${ZENML_VERSION}') >= version.parse('0.73.0') else 'zenml-cloud-server'; print(repo)")
IMAGE_NAME=715803424590.dkr.ecr.eu-central-1.amazonaws.com/${IMAGE_REPOSITORY}:${ZENML_VERSION}

docker build --platform linux/amd64 \
    -f Dockerfile.patch \
    --build-arg BASE_IMAGE=${IMAGE_NAME} \
    -t ${IMAGE_NAME}-patch \
    ./src/zenml

# Should we use the same tag for the patch image?
docker push ${IMAGE_NAME}-patch
