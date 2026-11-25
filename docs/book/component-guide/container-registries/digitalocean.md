---
description: Storing container images in the DigitalOcean Container Registry.
---

# DigitalOcean Container Registry

The DigitalOcean container registry is a [container registry](./) flavor that comes built-in with the DigitalOcean ZenML integration and uses the [DigitalOcean Container Registry (DOCR)](https://www.digitalocean.com/products/container-registry) to store container images.

### When to use it

You should use the DigitalOcean container registry if:

* one or more components of your stack need to pull or push container images.
* your infrastructure runs on DigitalOcean — for example a DOKS cluster running the [Kubernetes orchestrator](https://docs.zenml.io/stacks/orchestrators/kubernetes) that pulls pipeline images from DOCR.

### How to deploy it

The flavor is provided by the DigitalOcean ZenML integration:

```shell
zenml integration install digitalocean -y
```

You also need a DOCR registry. In the [DigitalOcean control panel](https://cloud.digitalocean.com/), go to **Container Registry** and create one (each account has a single registry with a unique name). The registry URI has the form:

```
registry.digitalocean.com/<REGISTRY_NAME>
```

### How to use it

To use the DigitalOcean container registry, you need:

* [Docker](https://www.docker.com) installed and running.
* The registry URI (see above).

You can then register the container registry and use it in your active stack:

```shell
zenml container-registry register do_registry \
    --flavor=digitalocean \
    --uri=registry.digitalocean.com/<REGISTRY_NAME>

# Add the container registry to the active stack
zenml stack update -c do_registry
```

You also need to authenticate your local Docker client with DOCR. The simplest way is [`doctl`](https://docs.digitalocean.com/reference/doctl/):

```shell
doctl registry login
```

{% hint style="info" %}
DOCR login credentials issued by `doctl registry login` are short-lived and expire after a while, so you may need to re-run the command. When pipeline images are pulled by a DOKS cluster, you can instead [integrate the registry with the cluster](https://docs.digitalocean.com/products/container-registry/how-to/use-registry-docker-kubernetes/) so nodes authenticate automatically.
{% endhint %}

For more information and a full list of configurable attributes of the DigitalOcean container registry, check out the [source code on GitHub](https://github.com/zenml-io/zenml/tree/main/src/zenml/integrations/digitalocean).

