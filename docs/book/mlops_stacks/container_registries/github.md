---
description: Store container images in GitHub
---

The GitHub container registry is a [container registry](./overview.md) flavor which comes built-in with 
ZenML and uses the [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
to store container images.

## When to use it

You should use the GitHub container registry if:
* one or more components of your stack need to pull or push container images.
* you're using GitHub for your projects. If you're not using GitHub, take a look at the
 other [container registry flavors](./overview.md#container-registry-flavors).

## How to deploy it

The GitHub container registry is enabled by default when you create a GitHub account.

## How to find the registry URI

The GitHub container registry URI should have the following format:
```shell
ghcr.io/<USER_OR_ORGANIZATION_NAME>

# Examples:
ghcr.io/zenml
ghcr.io/my-username
ghcr.io/my-organization
```

To figure our the URI for your registry:
* Use the GitHub user or organization name to fill the template 
`ghcr.io/<USER_OR_ORGANIZATION_NAME>` and get your URI.

## How to use it

To use the GitHub container registry, we need:
* [Docker](https://www.docker.com) installed and running.
* The registry URI. Check out the [previous section](#uri-format) on the URI format and how
to get the URI for your registry.
* Our Docker client configured so it can pull and push images. Follow
[this guide](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry#authenticating-to-the-container-registry) to create a
personal access token and login to the container registry.

We can then register the container registry and use it in our active stack:
```shell
zenml container-registry register <NAME> \
    --flavor=github \
    --uri=<REGISTRY_URI>

# Add the container registry to the active stack
zenml stack update -c <NAME>
```

For more information and a full list of configurable attributes of the GitHub container registry, check out the 
[API Docs](https://apidocs.zenml.io/latest/api_docs/container_registries/#zenml.container_registries.github_container_registry.GitHubContainerRegistry).




