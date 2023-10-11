---
description: How to build container images with Google Cloud Build
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


The Google Cloud image builder is an [image builder](./image-builders.md) flavor provided
with the ZenML `gcp` integration that uses [Google Cloud Build](https://cloud.google.com/build)
to build container images.

## When to use it

You should use the Google Cloud image builder if:

* you're **unable** to install or use [Docker](https://www.docker.com) on your client machine.
* you're already using GCP.
* your stack is mainly composed of other Google Cloud components such as the [GCS Artifact Store](../artifact-stores/gcloud-gcs.md) or the [Vertex Orchestrator](../orchestrators/gcloud-vertexai.md).

## How to deploy it

In order to use the ZenML Google Cloud image builder you need to enable Google Cloud Build relevant APIs on the Google Cloud project.

## How to use it

To use the Google Cloud image builder, we need:

* The ZenML `gcp` integration installed. If you haven't done so, run:

    ```shell
    zenml integration install gcp
    ```

* A [GCP Artifact Store](../artifact-stores/gcloud-gcs.md) where the build context will be uploaded, so Google Cloud Build can access it.
* A [GCP container registry](../container-registries/gcp.md) where the built image will be pushed.
* Optionally, the GCP project ID in which you want to run the build and a service account with the needed permissions to run the build. If not provided, then the project ID and credentials will be inferred from the environment.
* Optionally, you can change:
  * the Docker image used by Google Cloud Build to execute the steps to build and push the Docker image. By default, the builder image will be `'gcr.io/cloud-builders/docker'`.
  * The network to which the container used to build the ZenML pipeline docker image will be attached. More information: [Cloud build network](https://cloud.google.com/build/docs/build-config-file-schema#network).
  * The build timeout for the build, and for the blocking operation waiting for the build to finish. More information: [Build Timeout](https://cloud.google.com/build/docs/build-config-file-schema#timeout_2).

We can register the image builder and use it in our active stack:

```shell
zenml image-builder register <IMAGE_BUILDER_NAME> \
    --flavor=gcp \
    --project=<PROJECT_ID> \
    --service_account_path=<SERVICE_ACCOUNT_PATH> \
    --cloud_builder_image=<BUILDER_IMAGE_NAME> \
    --network=<DOCKER_NETWORK> \
    --build_timeout=<BUILD_TIMEOUT_IN_SECONDS>

# Register and activate a stack with the new image builder
zenml stack register <STACK_NAME> -i <IMAGE_BUILDER_NAME> ... --set
```

## Caveats

As described in this [Google Cloud Build documentation page](https://cloud.google.com/build/docs/build-config-file-schema#network), Google Cloud Build uses containers to execute the build steps which are automatically attached to a network called `cloudbuild` that provides some Application Default Credentials (ADC), that allows the container to be authenticated and therefore use other GCP services.

By default, the GCP Image Builder is executing the build command of the ZenML Pipeline Docker image with the option `--network=cloudbuild`, so the ADC provided by the `cloudbuild` network can also be used in the build. This is useful if you want to install a private dependency from a GCP Artifact Registry, but you will also need to use a [custom base parent image](../../starter-guide/production-fundamentals/containerization.md#using-a-custom-parent-image) with the [`keyrings.google-artifactregistry-auth`](https://pypi.org/project/keyrings.google-artifactregistry-auth/) installed, so `pip` can connect and authenticate in the private artifact registry to download the dependency.

```dockerfile
FROM zenmldocker/zenml:latest

RUN pip install keyrings.google-artifactregistry-auth
```

{% hint style="warning" %}
The above `Dockerfile` uses `zenmldocker/zenml:latest` as base image, but is recommended to change the tag to specify the ZenML version and Python version like `0.33.0-py3.10`.
{% endhint %}
