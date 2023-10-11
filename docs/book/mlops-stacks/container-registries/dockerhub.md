---
description: How to store container images in DockerHub
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


The DockerHub container registry is a [container registry](./container-registries.md) 
flavor which comes built-in with ZenML and uses [DockerHub](https://hub.docker.com/)
to store container images.

## When to use it

You should use the DockerHub container registry if:
* one or more components of your stack need to pull or push container images.
* you have a DockerHub account. If you're not using DockerHub, take a look at the
 other [container registry flavors](./container-registries.md#container-registry-flavors).

## How to deploy it

To use the DockerHub container registry, all you need to do is create
a [DockerHub](https://hub.docker.com/) account.

When this container registry is used in a ZenML stack, the Docker images
that are built will be published in a **public** repository and everyone
will be able to pull your images. If you want to use a **private** repository
instead, you'll have to [create a private repository](https://docs.docker.com/docker-hub/repos/#creating-repositories)
on the website before running the pipeline. The repository name depends on
the remote [orchestrator](../orchestrators/orchestrators.md) or
[step operator](../step-operators/step-operators.md) that you're using in your stack.

## How to find the registry URI

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

To figure our the URI for your registry:
* Find out the account name of your [DockerHub](https://hub.docker.com/) account.
* Use the account name to fill the template `docker.io/<ACCOUNT_NAME>` and get your URI.
## How to use it

To use the Azure container registry, we need:
* [Docker](https://www.docker.com) installed and running.
* The registry URI. Check out the [previous section](#how-to-find-the-registry-uri) on the URI format and how
to get the URI for your registry.

We can then register the container registry and use it in our active stack:
```shell
zenml container-registry register <NAME> \
    --flavor=dockerhub \
    --uri=<REGISTRY_URI>

# Add the container registry to the active stack
zenml stack update -c <NAME>
```

Additionally, we'll need to login to the container registry so Docker can pull and push images.
This will require your DockerHub account name and either your password or preferably a
[personal access token](https://docs.docker.com/docker-hub/access-tokens/).

```shell
docker login
```

For more information and a full list of configurable attributes of the Azure container registry, check out the 
[API Docs](https://apidocs.zenml.io/latest/api_docs/container_registries/#zenml.container_registries.dockerhub_container_registry.DockerHubContainerRegistry).
