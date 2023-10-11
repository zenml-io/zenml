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
* A [remote container registry](../container-registries/container-registries.md) where the built image will be pushed.
* Optionally, the GCP project ID in which you want to run the build and a service account with the needed permissions to run the build. If not provided, then the project ID and credentials will be inferred from the environment.
* Optionally, you can change the Docker image used by Google Cloud Build to execute the steps to build and push the Docker image. By default, the builder image will be `'gcr.io/cloud-builders/docker'`.

We can register the image builder and use it in our active stack:
```shell
zenml image-builder register <IMAGE_BUILDER_NAME> \
    --flavor=gcp \
    --project=<PROJECT_ID> \
    --service_account_path=<SERVICE_ACCOUNT_PATH> \
    --cloud_builder_image=<BUILDER_IMAGE_NAME>

# Register and activate a stack with the new image builder
zenml stack register <STACK_NAME> -im <IMAGE_BUILDER_NAME> ... --set
```
