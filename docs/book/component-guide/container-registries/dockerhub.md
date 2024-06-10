---
description: Storing container images in DockerHub.
---

# DockerHub

The DockerHub container registry is a [container registry](./container-registries.md) flavor that comes built-in with ZenML and uses [DockerHub](https://hub.docker.com/) to store container images.

### When to use it

You should use the DockerHub container registry if:

* one or more components of your stack need to pull or push container images.
* you have a DockerHub account. If you're not using DockerHub, take a look at the other [container registry flavors](./container-registries.md#container-registry-flavors).

### How to deploy it

To use the DockerHub container registry, all you need to do is create a [DockerHub](https://hub.docker.com/) account.

When this container registry is used in a ZenML stack, the Docker images that are built will be published in a \*\* public\*\* repository and everyone will be able to pull your images. If you want to use a **private** repository instead, you'll have to [create a private repository](https://docs.docker.com/docker-hub/repos/#creating-repositories) on the website before running the pipeline. The repository name depends on the remote [orchestrator](../orchestrators/orchestrators.md) or [step operator](../step-operators/step-operators.md) that you're using in your stack.

### How to find the registry URI

The DockerHub container registry URI should have one of the two following formats:

```shell
<ACCOUNT_NAME>
# or
docker.io/<ACCOUNT_NAME>

# Examples:
zenml
my-username
docker.io/zenml
docker.io/my-username
```

To figure out the URI for your registry:

* Find out the account name of your [DockerHub](https://hub.docker.com/) account.
* Use the account name to fill the template `docker.io/<ACCOUNT_NAME>` and get your URI.

### How to use it

To use the Azure container registry, we need:

* [Docker](https://www.docker.com) installed and running.
* The registry URI. Check out the [previous section](dockerhub.md#how-to-find-the-registry-uri) on the URI format and how to get the URI for your registry.

We can then register the container registry and use it in our active stack:

```shell
zenml container-registry register <NAME> \
    --flavor=dockerhub \
    --uri=<REGISTRY_URI>

# Add the container registry to the active stack
zenml stack update -c <NAME>
```

Additionally, we'll need to log in to the container registry so Docker can pull and push images. This will require your DockerHub account name and either your password or preferably a [personal access token](https://docs.docker.com/docker-hub/access-tokens/).

```shell
docker login
```

For more information and a full list of configurable attributes of the `dockerhub` container registry, check out the [SDK Docs](https://apidocs.zenml.io/latest/core\_code\_docs/core-container\_registries/#zenml.container\_registries.dockerhub\_container\_registry.DockerHubContainerRegistry) .

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
