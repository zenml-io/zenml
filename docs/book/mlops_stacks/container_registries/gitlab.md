---
description: Store container images in GitLab
---

The GitLab container registry is a [container registry](./overview.md) flavor which comes built-in with 
ZenML and uses the [GitLab Container Registry](https://docs.gitlab.com/ee/user/packages/container_registry/)
to store container images.

## When to use it

You should use the GitLab container registry if:
* one or more components of your stack need to pull or push container images.
* you have access to GitLab. If you're not using GitLab, take a look at the
 other [container registry flavors](./overview.md#container-registry-flavors).

## How to deploy it

...

## How to find the registry URI

The GitLab container registry URI should have the following format:
```shell
...
```

To figure our the URI for your registry:
* ...

## How to use it

To use the GitLab container registry, we need:
* [Docker](https://www.docker.com) installed and running.
* The registry URI. Check out the [previous section](#uri-format) on the URI format and how
to get the URI for your registry.

We can then register the container registry and use it in our active stack:
```shell
zenml container-registry register <NAME> \
    --flavor=gitlab \
    --uri=<REGISTRY_URI>

# Add the container registry to the active stack
zenml stack update -c <NAME>
```

Additionally, we'll need to configure Docker so it can pull and push images:
```shell
...
```

For more information and a full list of configurable attributes of the GitLab container registry, check out the 
[API Docs](https://apidocs.zenml.io/latest/api_docs/container_registries/#zenml.container_registries.gitlab_container_registry.GitLabContainerRegistry).
