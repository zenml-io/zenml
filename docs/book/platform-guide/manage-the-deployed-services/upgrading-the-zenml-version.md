# Upgrade the ZenML Version of your server

The way to upgrade your ZenML server depends a lot on how you deployed it.

{% tabs %}
{% tab title="ZenML CLI" %}
To upgrade your ZenML server that was deployed with the `zenml deploy` command to a newer version, you can follow the steps below.

* In the config file, set `zenmlserver_image_tag` to the version that you want your ZenML server to be running.
*   Run the deploy command again with this config file:

    ```bash
    zenml deploy --config=/PATH/TO/FILE
    ```

Any database schema updates are automatically handled by ZenML and unless mentioned otherwise, all of your data is migrated to the new version, intact.
{% endtab %}

{% tab title="Docker" %}
To upgrade to a new version with docker, you have to delete the existing container and then run the new version of the `zenml-server` image.

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
*   Deploy the version of the `zenml-server` image that you want to use. Find all versions [here](https://hub.docker.com/r/zenmldocker/zenml-server/tags).

    ```bash
    docker run -it -d -p 8080:8080 --name <CONTAINER_NAME> zenmldocker/zenml-server:<VERSION>
    ```

Alternatively, if you&#x20;
{% endtab %}

{% tab title="Helm" %}
To upgrade your ZenML server Helm release to a new version, follow the steps below:

* Pull the latest version of the Helm chart from the ZenML github repository, or a version of your choice, e.g.:

```bash
# If you haven't cloned the ZenML repository yet
git clone https://github.com/zenml-io/zenml.git
# Optional: checkout an explicit release tag
# git checkout 0.21.1
git pull
# Switch to the directory that hosts the helm chart
cd src/zenml/zen_server/deploy/helm/
```

*   Simply reuse the `custom-values.yaml` file that you used during the previous installation or upgrade. If you don't have it handy, you can extract the values from the ZenML Helm deployment using the following command:

    ```bash
    helm -n <namespace> get values zenml-server > custom-values.yaml
    ```
*   Upgrade the release using your modified values file. Make sure you are in the directory that hosts the helm chart:

    ```bash
    helm -n <namespace> upgrade zenml-server . -f custom-values.yaml
    ```

> **Info** It is not recommended to change the container image tag in the Helm chart to custom values, since every Helm chart version is tested to work only with the default image tag, but if you really want to do it, you can do so by setting the `zenml.image.tag` value in your `custom-values.yaml` file to the desired ZenML version (e.g. `0.32.0`).

> **Warning** If you wish to downgrade a server, make sure that the version of ZenML that you’re moving to has the same database schema. This is because reverse migration of the schema is not supported.
{% endtab %}
{% endtabs %}

{% hint style="warning" %}
Downgrading the server to an older version is not supported and can lead to unexpected behavior.
{% endhint %}

{% hint style="info" %}
The version of the python client that connects to the server should be kept at the same version as the server.
{% endhint %}
