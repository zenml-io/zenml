---
description: Building container images locally.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Local Image Builder

The local image builder is an [image builder](./) flavor that comes built-in with ZenML and uses the [container engine](../../how-to/containerization/containerization.md#choosing-the-container-engine) available on your client machine (**Docker** or **Podman**) to build and push images.

### Container engine selection

The local image builder uses [the container engine as the global setting of your ZenML client](../../how-to/containerization/containerization.md#choosing-the-container-engine):

* If you do nothing: ZenML auto-detects the container engine available on your machine: it prefers **Docker** when the Docker CLI and daemon are available; otherwise it uses **Podman** if that CLI is installed. Most users with Docker installed therefore get **Docker** by default.
* To force an engine: set the environment variable **`ZENML_CONTAINER_ENGINE`** to `docker` or `podman`.

{% hint style="info" %}
**Docker engine:** builds use the Docker API by default (or the `docker build` CLI if you enable subprocess mode below). Registry credentials for push often come from `$HOME/.docker/config.json`. If your config lives elsewhere, set `DOCKER_CONFIG` to the directory that contains `config.json`.

**Podman engine:** builds and pushes use the Podman CLI only; configure registry login with `podman login` (or your stack’s container registry credentials, which ZenML applies per operation).
{% endhint %}

### When to use it

You should use the local image builder if:

* you can run **Docker** or **Podman** on the machine where you execute pipelines
* you want to use remote components that require containerization without the additional hassle of configuring 
infrastructure for an additional component.

### How to deploy it

The local image builder comes with ZenML and works without any additional setup.

### How to use it

To use the local image builder, you need:

* [Docker](https://www.docker.com/) or [Podman](https://podman.io/) installed and working (see [Choosing the Container Engine](../../how-to/containerization/containerization.md#choosing-the-container-engine)), and
* Your user authenticated to the container registry in that stack (for example `docker login` or `podman login`, or credentials supplied via your [container registry](../../component-guide/container-registries/README.md) stack component / service connector).

We can then register the image builder and use it to create a new stack:

```shell
zenml image-builder register <NAME> --flavor=local

# Register and activate a stack with the new image builder
zenml stack register <STACK_NAME> -i <NAME> ... --set
```

#### Use the Docker CLI for builds (subprocess mode)

When the active container engine is **Docker**, builds normally go through the Docker API. You can configure the local image builder to call **`docker build`** via a subprocess instead. That helps when you need **Docker BuildKit** options that are not exposed through the Python SDK.

When the active engine is **Podman**, builds **always** use the Podman CLI; this setting has no effect.

Enable subprocess mode when registering or updating the component:

```shell
# Register with subprocess mode enabled
zenml image-builder register <NAME> --flavor=local --use_subprocess_call=true

# Or update an existing local image builder
zenml image-builder update <NAME> --use_subprocess_call=true
```

In subprocess mode, the build options passed via `DockerSettings` are handled in the following way:
- The `buildargs`, `labels` dictionaries are passed as `--build-arg KEY=VALUE` and `--label KEY=VALUE` respectively
- Lists will pass multiple command line arguments with the same name for all values
- `True` boolean values means the argument will be passed without any value (`--KEY`)
- All other values are converted to a string and passed as `--KEY VALUE`

For more information and a full list of configurable attributes of the local image builder, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/core_code_docs/core-image_builders.html#zenml.image_builders.local_image_builder) .

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
