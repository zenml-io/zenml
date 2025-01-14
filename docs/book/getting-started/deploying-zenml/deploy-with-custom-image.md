---
description: Deploying ZenML with custom Docker images.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Deploy with custom images

In most cases, deploying ZenML with the default `zenmlhub/zenml-server` Docker image should work just fine. However, there are some scenarios when you might need to deploy ZenML with a custom Docker image:

* You have implemented a custom artifact store for which you want to enable [artifact visualizations](../../how-to/handle-data-artifacts/visualize-artifacts.md) or [step logs](../../how-to/setting-up-a-project-repository/best-practices.md#logging) in your dashboard.
* You have forked the ZenML repository and want to deploy a ZenML server based on your own fork because you made changes to the server / database logic.

{% hint style="warning" %}
Deploying ZenML with custom Docker images is only possible for [Docker](deploy-with-docker.md) or [Helm](deploy-with-helm.md) deployments.
{% endhint %}

### Build and Push Custom ZenML Server Docker Image

Here is how you can build a custom ZenML server Docker image:

1. Set up a container registry of your choice. E.g., as an indivial developer you could create a free [Docker Hub](https://hub.docker.com/) account and then set up a free Docker Hub repository.
2.  Clone ZenML (or your ZenML fork) and checkout the branch that you want to deploy, e.g., if you want to deploy ZenML version 0.41.0, run

    ```bash
    git checkout release/0.41.0
    ```
3.  Copy the [ZenML base.Dockerfile](https://github.com/zenml-io/zenml/blob/main/docker/base.Dockerfile), e.g.:

    ```bash
    cp docker/base.Dockerfile docker/custom.Dockerfile
    ```
4.  Modify the copied Dockerfile:

    * Add additional dependencies:

    ```bash
    RUN pip install <my_package>
    ```

    * (Forks only) install local files instead of official ZenML:

    ```bash
    RUN pip install -e .[server,secrets-aws,secrets-gcp,secrets-azure,secrets-hashicorp,s3fs,gcsfs,adlfs,connectors-aws,connectors-gcp,connectors-azure]
    ```
5.  Build and push an image based on your Dockerfile:

    ```bash
    docker build -f docker/custom.Dockerfile . -t <YOUR_CONTAINER_REGISTRY>/<IMAGE_NAME>:<IMAGE_TAG> --platform linux/amd64
    docker push <YOUR_CONTAINER_REGISTRY>/<IMAGE_NAME>:<IMAGE_TAG>
    ```

{% hint style="info" %}
If you want to verify your custom image locally, you can follow the [Deploy a custom ZenML image via Docker](deploy-with-custom-image.md#deploy-a-custom-zenml-image-via-docker) section below to deploy the ZenML server locally first.
{% endhint %}

### Deploy ZenML with your custom image

Next, adjust your preferred deployment strategy to use the custom Docker image you just built.

#### Deploy a custom ZenML image via Docker

To deploy your custom image via Docker, first familiarize yourself with the general [ZenML Docker Deployment Guide](deploy-with-docker.md).

To use your own image, follow the general guide step by step but replace all mentions of `zenmldocker/zenml-server` with your custom image reference `<YOUR_CONTAINER_REGISTRY>/<IMAGE_NAME>:<IMAGE_TAG>`. E.g.:

* To run the ZenML server with Docker based on your custom image, do

```bash
docker run -it -d -p 8080:8080 --name zenml <YOUR_CONTAINER_REGISTRY>/<IMAGE_NAME>:<IMAGE_TAG>
```

* To use `docker-compose`, adjust your `docker-compose.yml`:

```yaml
services:
  zenml:
    image: <YOUR_CONTAINER_REGISTRY>/<IMAGE_NAME>:<IMAGE_TAG>
```

#### Deploy a custom ZenML image via Helm

To deploy your custom image via Helm, first familiarize yourself with the general [ZenML Helm Deployment Guide](deploy-with-helm.md).

To use your own image, the only thing you need to do differently is to modify the `image` section of your `values.yaml` file:

```yaml
zenml:
  image:
    repository: <YOUR_CONTAINER_REGISTRY>/<IMAGE_NAME>
    tag: <IMAGE_TAG>
```

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
