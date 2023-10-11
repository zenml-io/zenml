---
description: Storing container images locally.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Default Container Registry

The Default container registry is a [container registry](container-registries.md) flavor that comes built-in with ZenML
and allows container registry URIs of any format.

### When to use it

You should use the Default container registry if you want to use a **local** container registry or when using a remote
container registry that is not covered by
other [container registry flavors](container-registries.md#container-registry-flavors).

### Local registry URI format

To specify a URI for a local container registry, use the following format:

```shell
localhost:<PORT>

# Examples:
localhost:5000
localhost:8000
localhost:9999
```

### How to use it

To use the Default container registry, we need:

* [Docker](https://www.docker.com) installed and running.
* The registry URI. If you're using a local container registry, check out
* the [previous section](default.md#local-registry-uri-format) on the URI format.

We can then register the container registry and use it in our active stack:

```shell
zenml container-registry register <NAME> \
    --flavor=default \
    --uri=<REGISTRY_URI>

# Add the container registry to the active stack
zenml stack update -c <NAME>
```

For more information and a full list of configurable attributes of the Default container registry, check out
the [API Docs](https://apidocs.zenml.io/latest/integration\_code\_docs/integrations-aws/#zenml.integrations.aws.container\_registries.default\_container\_registry.DefaultContainerRegistry)
.
