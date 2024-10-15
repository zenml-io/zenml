---
description: Learn how to upgrade your server to a new version of ZenML for the different deployment options.
---

# Upgrade the version of the ZenML server

The way to upgrade your ZenML server depends a lot on how you deployed it. However, there are some best practices that apply in all cases. Before you upgrade, check out the [best practices for upgrading ZenML](./best-practices-upgrading-zenml.md) guide.

In general, upgrade your ZenML server as soon as you can once a new version is released. New versions come with a lot of improvements and fixes that you can benefit from.

{% tabs %}
{% tab title="Docker" %}
To upgrade to a new version with docker, you have to delete the existing container and then run the new version of
the `zenml-server` image.

{% hint style="danger" %}
Check that your data is persisted (either on persistent storage or on an external MySQL instance) before doing this.

Optionally also perform a backup before the upgrade.
{% endhint %}

* Delete the existing ZenML container, for example like this:

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
* Deploy the version of the `zenml-server` image that you want to use. Find all
  versions [here](https://hub.docker.com/r/zenmldocker/zenml-server/tags).

  ```bash
  docker run -it -d -p 8080:8080 --name <CONTAINER_NAME> zenmldocker/zenml-server:<VERSION>
  ```

{% endtab %}

{% tab title="Kubernetes with Helm" %}
To upgrade your ZenML server Helm release to a new version, follow the steps below:

* Pull the latest version of the Helm chart from the ZenML GitHub repository, or a version of your choice, e.g.:

```bash
# If you haven't cloned the ZenML repository yet
git clone https://github.com/zenml-io/zenml.git
# Optional: checkout an explicit release tag
# git checkout 0.21.1
git pull
# Switch to the directory that hosts the helm chart
cd src/zenml/zen_server/deploy/helm/
```

* Simply reuse the `custom-values.yaml` file that you used during the previous installation or upgrade. If you don't
  have it handy, you can extract the values from the ZenML Helm deployment using the following command:

  ```bash
  helm -n <namespace> get values zenml-server > custom-values.yaml
  ```
* Upgrade the release using your modified values file. Make sure you are in the directory that hosts the helm chart:

  ```bash
  helm -n <namespace> upgrade zenml-server . -f custom-values.yaml
  ```

{% hint style="info" %}
It is not recommended to change the container image tag in the Helm chart to custom values, since every Helm chart
version is tested to work only with the default image tag. However, if you know what you're doing you can change
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

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
