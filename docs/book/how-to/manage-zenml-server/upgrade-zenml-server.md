---
description: >-
  Learn how to upgrade your server to a new version of ZenML for the different
  deployment options.
---

# Upgrade your ZenML server

The way to upgrade your ZenML server depends a lot on how you deployed it. However, there are some best practices that apply in all cases. Before you upgrade, check out the [best practices for upgrading ZenML](best-practices-upgrading-zenml.md) guide.

In general, upgrade your ZenML server as soon as you can once a new version is released. New versions come with a lot of improvements and fixes from which you can benefit.

{% tabs %}
{% tab title="Docker" %}
To upgrade to a new version with docker, you have to delete the existing container and then run the new version of\
the `zenml-server` image.

{% hint style="danger" %}
Check that your data is persisted (either on persistent storage or on an external MySQL instance) before doing this.

Optionally also perform a backup before the upgrade.
{% endhint %}

*   Delete the existing ZenML container, for example like this:

    ```bash
    # find your container ID
    docker ps
    ```

    ```bash
    # stop the container
    docker stop <CONTAINER_ID>

    # remove the container
    docker rm <CONTAINER_ID>
    ```
*   Deploy the version of the `zenml-server` image that you want to use. Find all\
    versions [here](https://hub.docker.com/r/zenmldocker/zenml-server/tags).

    ```bash
    docker run -it -d -p 8080:8080 --name <CONTAINER_NAME> zenmldocker/zenml-server:<VERSION>
    ```
{% endtab %}

{% tab title="Kubernetes with Helm" %}
To upgrade your ZenML server Helm release to a new version, follow the steps below.

### Simple in-place upgrade

If you don't need to change any configuration values, you can perform a simple in-place upgrade that reuses your existing configuration:

```bash
helm -n <namespace> upgrade zenml-server oci://public.ecr.aws/zenml/zenml --version <VERSION> --reuse-values
```

### Upgrade with configuration changes

If you need to modify your ZenML server configuration during the upgrade, follow these steps instead:

*   Extract your current configuration values to a file:

    ```bash
    helm -n <namespace> get values zenml-server > custom-values.yaml
    ```
* Make the necessary changes to your `custom-values.yaml` file (make sure they are compatible with the new version)
*   Upgrade the release using your modified values file:

    ```bash
    helm -n <namespace> upgrade zenml-server oci://public.ecr.aws/zenml/zenml --version <VERSION> -f custom-values.yaml
    ```

{% hint style="info" %}
It is not recommended to change the container image tag in the Helm chart to custom values, since every Helm chart\
version is tested to work only with the default image tag. However, if you know what you're doing you can change\
the `zenml.image.tag` value in your `custom-values.yaml` file to the desired ZenML version (e.g. `0.32.0`).
{% endhint %}
{% endtab %}
{% endtabs %}

{% hint style="warning" %}
Downgrading the server to an older version is not supported and can lead to unexpected behavior.
{% endhint %}

{% hint style="info" %}
The version of the Python client that connects to the server should be kept at the same version as the server.
{% endhint %}

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
