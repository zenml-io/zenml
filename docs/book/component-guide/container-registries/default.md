---
description: Storing container images locally.
---

# Default Container Registry

The Default container registry is a [container registry](./container-registries.md) flavor that comes built-in with ZenML and allows container registry URIs of any format.

### When to use it

You should use the Default container registry if you want to use a **local** container registry or when using a remote container registry that is not covered by other [container registry flavors](./container-registries.md#container-registry-flavors).

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

You may also need to set up [authentication](default.md#authentication-methods) required to log in to the container registry.

#### Authentication Methods

If you are using a private container registry, you will need to configure some form of authentication to login to the registry. If you're looking for a quick way to get started locally, you can use the _Local Authentication_ method. However, the recommended way to authenticate to a remote private container registry is through [a Docker Service Connector](../../how-to/infrastructure-deployment/auth-management/docker-service-connector.md).

If your target private container registry comes from a cloud provider like AWS, GCP or Azure, you should use the [container registry flavor](./container-registries.md#container-registry-flavors) targeted at that cloud provider. For example, if you're using AWS, you should use the [AWS Container Registry](aws.md) flavor. These cloud provider flavors also use specialized cloud provider Service Connectors to authenticate to the container registry.

{% tabs %}
{% tab title="Local Authentication" %}
This method uses the Docker client authentication available _in the environment where the ZenML code is running_. On your local machine, this is the quickest way to configure a Default Container Registry. You don't need to supply credentials explicitly when you register the Default Container Registry, as it leverages the local credentials and configuration that the Docker client stores on your local machine.

To log in to the container registry so Docker can pull and push images, you'll need to run the `docker login` command and supply your credentials, e.g.:

```shell
docker login --username <USERNAME> --password-stdin <REGISTRY_URI>
```

{% hint style="warning" %}
Stacks using the Default Container Registry set up with local authentication are not portable across environments. To make ZenML pipelines fully portable, it is recommended to use [a Docker Service Connector](../../how-to/infrastructure-deployment/auth-management/docker-service-connector.md) to link your Default Container Registry to the remote private container registry.
{% endhint %}
{% endtab %}

{% tab title="Docker Service Connector (recommended)" %}
To set up the Default Container Registry to authenticate to and access a private container registry, it is recommended to leverage the features provided by [the Docker Service Connector](../../how-to/infrastructure-deployment/auth-management/docker-service-connector.md) such as local login and reusing the same credentials across multiple stack components.

If you don't already have a Docker Service Connector configured in your ZenML deployment, you can register one using the interactive CLI command:

```sh
zenml service-connector register --type docker -i
```

A non-interactive CLI example is:

```sh
zenml service-connector register <CONNECTOR_NAME> --type docker --username=<USERNAME> --password=<PASSWORD_OR_TOKEN>
```

{% code title="Example Command Output" %}
```
$ zenml service-connector register dockerhub --type docker --username=username --password=password
Successfully registered service connector `dockerhub` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃   RESOURCE TYPE    │ RESOURCE NAMES ┃
┠────────────────────┼────────────────┨
┃ 🐳 docker-registry │ docker.io      ┃
┗━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛
```
{% endcode %}

If you already have one or more Docker Service Connectors configured in your ZenML deployment, you can check which of them can be used to access the container registry you want to use for your Default Container Registry by running e.g.:

```sh
zenml service-connector list-resources --connector-type docker --resource-id <REGISTRY_URI>
```

{% code title="Example Command Output" %}
```
$ zenml service-connector list-resources --connector-type docker --resource-id docker.io
The  resource with name 'docker.io' can be accessed by 'docker' service connectors that you have configured:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE      │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼────────────────────┼────────────────┨
┃ cf55339f-dbc8-4ee6-862e-c25aff411292 │ dockerhub      │ 🐳 docker      │ 🐳 docker-registry │ docker.io      ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛
```
{% endcode %}

After having set up or decided on a Docker Service Connector to use to connect to the target container registry, you can register the Docker Container Registry as follows:

```sh
# Register the container registry and reference the target registry URI
zenml container-registry register <CONTAINER_REGISTRY_NAME> -f default \
    --uri=<REGISTRY_URL>

# Connect the container registry to the target registry via a Docker Service Connector
zenml container-registry connect <CONTAINER_REGISTRY_NAME> -i
```

A non-interactive version that connects the Default Container Registry to a target registry through a Docker Service Connector:

```sh
zenml container-registry connect <CONTAINER_REGISTRY_NAME> --connector <CONNECTOR_ID>
```

{% code title="Example Command Output" %}
```
$ zenml container-registry connect dockerhub --connector dockerhub
Successfully connected container registry `dockerhub` to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE      │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼────────────────────┼────────────────┨
┃ cf55339f-dbc8-4ee6-862e-c25aff411292 │ dockerhub      │ 🐳 docker      │ 🐳 docker-registry │ docker.io      ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛
```
{% endcode %}

As a final step, you can use the Default Container Registry in a ZenML Stack:

```sh
# Register and set a stack with the new container registry
zenml stack register <STACK_NAME> -c <CONTAINER_REGISTRY_NAME> ... --set
```

{% hint style="info" %}
Linking the Default Container Registry to a Service Connector means that your local Docker client is no longer authenticated to access the remote registry. If you need to manually interact with the remote registry via the Docker CLI, you can use the [local login Service Connector feature](../../how-to/infrastructure-deployment/auth-management/service-connectors-guide.md#configure-local-clients) to temporarily authenticate your local Docker client to the remote registry:

```sh
zenml service-connector login <CONNECTOR_NAME>
```

{% code title="Example Command Output" %}
```
$ zenml service-connector login dockerhub
⠹ Attempting to configure local client using service connector 'dockerhub'...
WARNING! Your password will be stored unencrypted in /home/stefan/.docker/config.json.
Configure a credential helper to remove this warning. See
https://docs.docker.com/engine/reference/commandline/login/#credentials-store

The 'dockerhub' Docker Service Connector connector was used to successfully configure the local Docker/OCI container registry client/SDK.
```
{% endcode %}
{% endhint %}
{% endtab %}
{% endtabs %}

For more information and a full list of configurable attributes of the Default container registry, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-aws/#zenml.integrations.aws.container\_registries.default\_container\_registry.DefaultContainerRegistry) .

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
