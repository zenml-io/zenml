---
description: Storing container images in a Docker image repository.
---

# Docker Image Remote Repository

The DockerHub [container registry](./) flavor allows ZenML to store and retrieve container images from a supported Docker remote container registry. Supported remote Docker image repositories include [DockerHub](https://hub.docker.com/), [Quay](https://www.projectquay.io/) or [Harbor](https://goharbor.io/).

Others are supported as long as the [`docker login`](https://docs.docker.com/reference/cli/docker/login/) command can be used to authenticate to the remote repository that saves the credentials in the config.json file. ZenML uses [docker-py](https://docker-py.readthedocs.io/en/stable/) which authenticates via the [Docker API](https://docs.docker.com/reference/api/engine/) using the credentials stored in the Docker `config.json` file.

## When to use it

You should use a Docker container registry if:

* one or more components of your stack need to pull or push container images, for example some [orchestrators](https://docs.zenml.io/stacks/orchestrators/) or [model deployers](https://docs.zenml.io/stacks/stack-components/model-deployers) require a remote container registry.

* you're already using DockerHub, Quay or Harbor for your projects.

Please take a look at the other [container registry flavors](./#container-registry-flavors) for alternatives.

## How to deploy it

Regardless of the remote repository used, a user account and repository accessible by the user account need to be created.

### 1. Create user/organisation 

You will need to create a user or organisation account with login credentials, please consult the documentation of the remote repository your using on how to do this.

### 2. Create repository

By default ZenML will push images to the target remote repository named "zenml", e.g. my_quay.com/repository/zenml_user/zenml. To change the default behaviour see [Controlling Image Repsitory Names](https://docs.zenml.io/concepts/containerization#controlling-image-repository-names).

Create either a "zenml" or custom repository and make it accessible to the docker repository user(s) or organisation(s) created in the previously described step.


### DockerHub

To use the DockerHub container registry, all you need to do is create a [DockerHub](https://hub.docker.com/) account.

When this container registry is used in a ZenML stack, the Docker images that are built will be published in a \*\* public\*\* repository and everyone will be able to pull your images. If you want to use a **private** repository instead, you'll have to [create a private repository](https://docs.docker.com/docker-hub/repos/#creating-repositories) on the website before running the pipeline. The repository name depends on the remote [orchestrator](https://docs.zenml.io/stacks/orchestrators/) or [step operator](https://docs.zenml.io/stacks/step-operators/) that you're using in your stack.


### Quay

To use the Quay container registry, you need to setup and configure a Quay instance. 

There are three options for deploying Quay.

1. Project Quay

[Project Quay](https://www.projectquay.io/) is free and open source software and is used by Quay.io and Red Hat Quay (see below).
It can be deployed using Podman, Kubernetes or Docker for self-hosted instances, see [Quick Local Deployment](https://github.com/quay/quay/blob/master/docs/quick-local-deployment.md) or [Deploy Quay](https://docs.projectquay.io/deploy_quay.html).

2. Red Hat Quay in OpenShift

[Red Hat Quay](https://www.redhat.com/en/technologies/cloud-computing/quay) is a self-managed platform that can be purchased from Red Hat.

3. Quay.io

[Quay.io](https://quay.io/) is a Software-as-a-Service (SaaS) providing a managed instance of Quay. 


#### Quay Setup

1. Create user/organisation

You will need to create a user or organisation account with login credentials, see [Deploy Quay](https://docs.projectquay.io/deploy_quay.html) or [Chapter 1. Creating Red Hat Quay users and organizations](https://docs.redhat.com/en/documentation/red_hat_quay/3.4/html/use_red_hat_quay/proc-use-quay-create-user-org). 

Follow [this guide](https://docs.redhat.com/en/documentation/red_hat_quay/3.4/html/use_red_hat_quay/use-quay-manage-repo) to create a personal access token for better security.

2. Create repository

By default ZenML will push images to the target remote repository named "zenml", e.g. my_quay.com/repository/zenml_user/zenml. To change the default behaviour see [Controlling Image Repsitory Names](https://docs.zenml.io/concepts/containerization#controlling-image-repository-names).

Create the repositories and make them accessible to the Quay user(s) or organisation(s) created previously as described in [Chapter 2. Creating a repository](https://docs.redhat.com/en/documentation/red_hat_quay/3.4/html/use_red_hat_quay/use-quay-create-repo). 


### Harbor

Harbor is open source registry project that stores, signs, and scans content and can be [deployed](https://goharbor.io/docs/latest/install-config) using Docker compose, Helm Chart.

To be completed. Git PR's welcome.


## How to find the registry URI

The DockerHub container registry URI should have one of the two following formats:

```shell
# ONLY for docker.io accounts
<ACCOUNT_NAME> 
# or
docker.io/<ACCOUNT_NAME>


# Examples:
zenml # for docker.io account
docker.io/zenml
docker.io/my-username
quay.io/my-username
quay.io/my-organization
selfhosted_harbor.com/my-username
selfhosted_quay.com/my-organization
192.168.1.100:9000/my-username
```

To determine the URI for your registry:

### DockerHub

Find out the account name of your [DockerHub](https://hub.docker.com/) account and use the account name to fill the template `docker.io/<ACCOUNT_NAME>` and get your URI.

## How to use it

To use the DockerHub container registry, we need:

* The [Docker](https://www.docker.com) daemon (for building the images) and client (for initialising the build and communicating the remote repository) installed on the client machine. Docker needs to be set up either for [rootless](https://docs.docker.com/engine/security/rootless/) or [isolated containers](https://docs.docker.com/engine/security/userns-remap/) as ZenML is usually run without root / administration permissions.

* The remote Docker registry URI. Check the [previous section](DockerHub.md#how-to-find-the-registry-uri) on the URI format and how to get the URI for your registry.

* The Docker image repository login credentials. This can be a username and password or an access token.

Register the remote repository with the docker client with the user credentials or access tokens.

```shell
# For docker.io accounts only, will prompt for account/password.
docker login
# or
docker login <REGISTRY_URI> -u <USERNAME> -p <PASSWORD>
```

We can then add the container registry to the ZenML stack as follows:

```shell
zenml container-registry register <CONTAINER_REGISTRY_NAME> \
    --flavor=dockerhub \
    --uri=<REGISTRY_URI>

# Add the container registry to the active stack
zenml stack update -c <CONTAINER_REGISTRY_NAME>
```

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
