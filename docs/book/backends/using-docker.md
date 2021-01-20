# Using Docker

Not all ZenML Pipelines (and Steps) are executed in a host-native environment (e.g. your local development machine). Some Backends rather rely on [Docker](https://www.docker.com/) images.

## When users need to think about Docker Images

Whenever a pipeline is executing non-locally, i.e., when a non-local [Backend](https://docs.zenml.io/backends/what-is-a-backend.html) is specified, there is usually an `image` parameter exposed that takes a Docker image as input.

Because ML practitioners may not be familiar with the Docker paradigm, ZenML ensures that there is a series of sane defaults that kick-in for users who do not want (or need) to build their own images. If no image is used a default **Base Image** is used instead. This Base Image contains [all dependencies that come bundled with ZenML](https://docs.zenml.io/getting-started/creating-custom-logic.html).

Some examples of when a Docker image is required:

- When orchestrating a pipeline on a [GCP VM instance](https://docs.zenml.io/backends/orchestrator-backends.html) or on Kubernetes.
- While specifying a GPU [training backend](https://docs.zenml.io/backends/training-backends.html) on the cloud.
- Configuring a [distributed processing backend](https://docs.zenml.io/backends/processing-backends.html) like Google Cloud Dataflow.

## Creating custom images

In cases where the dependencies specified in the base images are not enough, you can easily create a custom image based on the corresponding base image. The base images are hosted on a public Container Registry, namely `[eu.gcr.io/maiot-zenml](http://eu.gcr.io/maiot-zenml)`. The Dockerfiles of all base images can be found in the `zenml/docker` directory of the [source code](https://github.com/maiot-io/zenml).

The easiest way to create your own, custom ZenML Docker Image, is by starting a new Dockerfile, using the ZenML Base Image as `FROM` :

```docker
FROM eu.gcr.io/maiot-zenml/zenml:base-0.1.5  # The ZenML Base Image

ADD . .  # adds your working directory to the resulting Docker Image
RUN pip install -r requirements.txt  # install your custom requirements
```

More seasoned readers might notice, that there is no definition of an `ENTRYPOINT` anywhere. The ZenML Docker Images are deliberately designed without an `ENTRYPOINT` , as every backend can ship with a generic or specialised pipeline entrypoint. Routing is therefore handled via container invocation, not through defaults.