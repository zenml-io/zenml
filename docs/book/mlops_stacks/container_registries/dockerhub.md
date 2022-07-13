---
description: Store container images in Dockerhub
---

The DockerHub container registry is a [container registry](./overview.md) 
flavor which comes built-in with ZenML and uses [DockerHub](https://hub.docker.com/)
to store container images.

## When to use it

You should use the DockerHub container registry if:
* one or more components of your stack need to pull or push container images.
* you have a DockerHub account. If you're not using DockerHub, take a look at the
 other [container registry flavors](./overview.md#container-registry-flavors).

## How to deploy it

...

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
* Find out the account name of your [DockerHub](https://portal.azure.com/#home) account.
* Use the account name to fill the template `docker.io/<ACCOUNT_NAME>` and get your URI.
## How to use it

To use the Azure container registry, we need:
* [Docker](https://www.docker.com) installed and running.
* The registry URI. Check out the [previous section](#uri-format) on the URI format and how
to get the URI for your registry.

We can then register the container registry and use it in our active stack:
```shell
zenml container-registry register <NAME> \
    --flavor=dockerhub \
    --uri=<REGISTRY_URI>

# Add the container registry to the active stack
zenml stack update -c <NAME>
```

Additionally, we'll need to login to the container registry so Docker can pull and push images:
```shell
...
```

For more information and a full list of configurable attributes of the Azure container registry, check out the 
[API Docs](https://apidocs.zenml.io/latest/api_docs/container_registries/#zenml.container_registries.dockerhub_container_registry.DockerHubContainerRegistry).
