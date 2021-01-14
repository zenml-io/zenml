# Using Docker
If not executing in a local environment, ZenML Pipelines (and Steps) execute in an environment specified in 
[Docker](https://www.docker.com/) images. 

## When users need to think about Docker Images
Whenever a pipeline is executing non-locally, i.e., when a non-local [Backend](what-is-a-backend.md) is 
specified, there is usually an `image` parameter exposed that takes as input the path to a Docker image.

Because ML practitioners may not be familiar with the Docker paradigm, ZenML 
ensures that there is a series of sane defaults that kick-in for users who do not want to build their own images. If 
no image is used a default **Base Image** is  used instead. The Base Image contains [all dependencies that come bundled 
with ZenML](../getting-started/creating-custom-logic.md).

Some examples of when a Docker image is required:
* When orchestrating a pipeline on a [GCP VM instance](orchestrator-backends.md).
* While pecifying a GPU [training backend](training-backends.md) on the cloud.
* Configuring a [distributed processing backend](processing-backends.md) like Google Cloud Dataflow.

## Creating custom images
In cases where the normal dependencies specified in the base images are not enough, then a user can create a custom 
image based on the corresponding base image. The base images are hosted on a public Google Container Registry, namely:

```bash
eu.gcr.io/maiot-zenml
``` 

The Dockerfiles of all base images can be found in the `zenml/docker` directory of the [source code](https://github.com/maiot-io/zenml).

### Example
Coming soon.