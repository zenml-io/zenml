---
description: Storing container images in GCP.
---

# Google Cloud Container Registry

The GCP container registry is a [container registry](./container-registries.md) flavor that comes built-in with ZenML and uses the [Google Artifact Registry](https://cloud.google.com/artifact-registry).

{% hint style="warning" %}
**Important Notice: Google Container Registry** [**is being replaced by Artifact Registry**](https://cloud.google.com/artifact-registry/docs/transition/transition-from-gcr)**. Please start using Artifact Registry for your containers. As per Google's documentation, "after May 15, 2024, Artifact Registry will host images for the gcr.io domain in Google Cloud projects without previous Container Registry usage. After March 18, 2025, Container Registry will be shut down."** The terms `container registry` and `artifact registry` will be used interchangeably throughout this document.
{% endhint %}

### When to use it

You should use the GCP container registry if:

* one or more components of your stack need to pull or push container images.
* you have access to GCP. If you're not using GCP, take a look at the other [container registry flavors](./container-registries.md#container-registry-flavors).

### How to deploy it

{% hint style="warning" %}
The GCP container registry (and GCP integration in general) currently only works for Python versions <3.11. The ZenML team is aware of this dependency clash/issue and is working on a fix. For now, please use Python <3.11 together with the GCP integration.
{% endhint %}

When using the Google Artifact Registry, you need to:

* enable it [here](https://console.cloud.google.com/marketplace/product/google/artifactregistry.googleapis.com)
* go [here](https://console.cloud.google.com/artifacts) and create a `Docker` repository.

### Infrastructure Deployment

A GCP Container Registry can be deployed directly from the ZenML CLI:

```shell
zenml container-registry deploy gcp_container_registry --flavor=gcp --provider=gcp ...
```

You can pass other configurations specific to the stack components as key-value arguments. If you don't provide a name, a random one is generated for you. For more information about how to work use the CLI for this, please refer to the [dedicated documentation section](../../how-to/stack-deployment/deploy-a-stack-component.md).

## How to find the registry URI

When using the Google Artifact Registry, the GCP container registry URI should have the following format:

```shell
<REGION>-docker.pkg.dev/<PROJECT_ID>/<REPOSITORY_NAME>

# Examples:
europe-west1-docker.pkg.dev/zenml/my-repo
southamerica-east1-docker.pkg.dev/zenml/zenml-test
asia-docker.pkg.dev/my-project/another-repo
```

To figure out the URI for your registry:

* Go [here](https://console.cloud.google.com/artifacts) and select the repository that you want to use to store Docker images. If you don't have a repository yet, take a look at the [deployment section](gcp.md#how-to-deploy-it).
* On the top, click the copy button to copy the full repository URL.

#### Infrastructure Deployment

A GCP Container Registry can be deployed directly from the ZenML CLI:

```shell
zenml container-registry deploy gcp_container_registry --flavor=gcp --provider=gcp ...
```

You can pass other configurations specific to the stack components as key-value arguments. If you don't provide a name, a random one is generated for you. For more information about how to work use the CLI for this, please refer to the dedicated documentation section.

### How to use it

To use the GCP container registry, we need:

* [Docker](https://www.docker.com) installed and running.
* The registry URI. Check out the [previous section](gcp.md#how-to-find-the-registry-uri) on the URI format and how to get the URI for your registry.

We can then register the container registry and use it in our active stack:

```shell
zenml container-registry register <NAME> \
    --flavor=gcp \
    --uri=<REGISTRY_URI>

# Add the container registry to the active stack
zenml stack update -c <NAME>
```

You also need to set up [authentication](gcp.md#authentication-methods) required to log in to the container registry.

#### Authentication Methods

Integrating and using a GCP Container Registry in your pipelines is not possible without employing some form of authentication. If you're looking for a quick way to get started locally, you can use the _Local Authentication_ method. However, the recommended way to authenticate to the GCP cloud platform is through [a GCP Service Connector](../../how-to/auth-management/gcp-service-connector.md). This is particularly useful if you are configuring ZenML stacks that combine the GCP Container Registry with other remote stack components also running in GCP.

{% tabs %}
{% tab title="Local Authentication" %}
This method uses the Docker client authentication available _in the environment where the ZenML code is running_. On your local machine, this is the quickest way to configure a GCP Container Registry. You don't need to supply credentials explicitly when you register the GCP Container Registry, as it leverages the local credentials and configuration that the GCP CLI and Docker client store on your local machine. However, you will need to install and set up the GCP CLI on your machine as a prerequisite, as covered in [the GCP CLI documentation](https://cloud.google.com/sdk/docs/install-sdk), before you register the GCP Container Registry.

With the GCP CLI installed and set up with credentials, we'll need to configure Docker, so it can pull and push images:

*   for a Google Container Registry:

    ```shell
    gcloud auth configure-docker
    ```
*   for a Google Artifact Registry:

    ```shell
    gcloud auth configure-docker <REGION>-docker.pkg.dev
    ```

{% hint style="warning" %}
Stacks using the GCP Container Registry set up with local authentication are not portable across environments. To make ZenML pipelines fully portable, it is recommended to use [a GCP Service Connector](../../how-to/auth-management/gcp-service-connector.md) to link your GCP Container Registry to the remote GCR registry.
{% endhint %}
{% endtab %}

{% tab title="GCP Service Connector (recommended)" %}
To set up the GCP Container Registry to authenticate to GCP and access a GCR registry, it is recommended to leverage the many features provided by [the GCP Service Connector](../../how-to/auth-management/gcp-service-connector.md) such as auto-configuration, local login, best security practices regarding long-lived credentials and reusing the same credentials across multiple stack components.

{% hint style="warning" %}
The GCP Service Connector does not support the Google Artifact Registry yet. If you need to connect your GCP Container Registry to a Google Artifact Registry, you can use the _Local Authentication_ method instead.
{% endhint %}

If you don't already have a GCP Service Connector configured in your ZenML deployment, you can register one using the interactive CLI command. You have the option to configure a GCP Service Connector that can be used to access a GCR registry or even more than one type of GCP resource:

```sh
zenml service-connector register --type gcp -i
```

A non-interactive CLI example that leverages [the GCP CLI configuration](https://docs.gcp.amazon.com/cli/latest/userguide/getting-started-install.html) on your local machine to auto-configure a GCP Service Connector targeting a GCR registry is:

```sh
zenml service-connector register <CONNECTOR_NAME> --type gcp --resource-type docker-registry --auto-configure
```

{% code title="Example Command Output" %}
```
$ zenml service-connector register gcp-zenml-core --type gcp --resource-type docker-registry --auto-configure
⠸ Registering service connector 'gcp-zenml-core'...
Successfully registered service connector `gcp-zenml-core` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃   RESOURCE TYPE    │ RESOURCE NAMES                                  ┃
┠────────────────────┼─────────────────────────────────────────────────┨
┃ 🐳 docker-registry │ gcr.io/zenml-core                               ┃
┃                    │ us.gcr.io/zenml-core                            ┃
┃                    │ eu.gcr.io/zenml-core                            ┃
┃                    │ asia.gcr.io/zenml-core                          ┃
┃                    │ asia-docker.pkg.dev/zenml-core/asia.gcr.io      ┃
┃                    │ europe-docker.pkg.dev/zenml-core/eu.gcr.io      ┃
┃                    │ europe-west1-docker.pkg.dev/zenml-core/test     ┃
┃                    │ us-docker.pkg.dev/zenml-core/gcr.io             ┃
┃                    │ us-docker.pkg.dev/zenml-core/us.gcr.io          ┃
┗━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

> **Note**: Please remember to grant the entity associated with your GCP credentials permissions to read and write to your GCR registry. For a full list of permissions required to use a GCP Service Connector to access a GCR registry, please refer to the [GCP Service Connector GCR registry resource type documentation](../../how-to/auth-management/gcp-service-connector.md#gcr-container-registry) or read the documentation available in the interactive CLI commands and dashboard. The GCP Service Connector supports [many different authentication methods](../../how-to/auth-management/gcp-service-connector.md#authentication-methods) with different levels of security and convenience. You should pick the one that best fits your use-case.

If you already have one or more GCP Service Connectors configured in your ZenML deployment, you can check which of them can be used to access the GCR registry you want to use for your GCP Container Registry by running e.g.:

```sh
zenml service-connector list-resources --connector-type gcp --resource-type docker-registry
``` 

{% code title="Example Command Output" %}
```text
The following 'docker-registry' resources can be accessed by 'gcp' service connectors configured in your workspace:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME   │ CONNECTOR TYPE │ RESOURCE TYPE      │ RESOURCE NAMES                                  ┃
┠──────────────────────────────────────┼──────────────────┼────────────────┼────────────────────┼─────────────────────────────────────────────────┨
┃ ffc01795-0c0a-4f1d-af80-b84aceabcfcf │ gcp-implicit     │ 🔵 gcp         │ 🐳 docker-registry │ gcr.io/zenml-core                               ┃
┃                                      │                  │                │                    │ us.gcr.io/zenml-core                            ┃
┃                                      │                  │                │                    │ eu.gcr.io/zenml-core                            ┃
┃                                      │                  │                │                    │ asia.gcr.io/zenml-core                          ┃
┃                                      │                  │                │                    │ asia-docker.pkg.dev/zenml-core/asia.gcr.io      ┃
┃                                      │                  │                │                    │ europe-docker.pkg.dev/zenml-core/eu.gcr.io      ┃
┃                                      │                  │                │                    │ europe-west1-docker.pkg.dev/zenml-core/test     ┃
┃                                      │                  │                │                    │ us-docker.pkg.dev/zenml-core/gcr.io             ┃
┃                                      │                  │                │                    │ us-docker.pkg.dev/zenml-core/us.gcr.io          ┃
┠──────────────────────────────────────┼──────────────────┼────────────────┼────────────────────┼─────────────────────────────────────────────────┨
┃ 561b776a-af8b-491c-a4ed-14349b440f30 │ gcp-zenml-core   │ 🔵 gcp         │ 🐳 docker-registry │ gcr.io/zenml-core                               ┃
┃                                      │                  │                │                    │ us.gcr.io/zenml-core                            ┃
┃                                      │                  │                │                    │ eu.gcr.io/zenml-core                            ┃
┃                                      │                  │                │                    │ asia.gcr.io/zenml-core                          ┃
┃                                      │                  │                │                    │ asia-docker.pkg.dev/zenml-core/asia.gcr.io      ┃
┃                                      │                  │                │                    │ europe-docker.pkg.dev/zenml-core/eu.gcr.io      ┃
┃                                      │                  │                │                    │ europe-west1-docker.pkg.dev/zenml-core/test     ┃
┃                                      │                  │                │                    │ us-docker.pkg.dev/zenml-core/gcr.io             ┃
┃                                      │                  │                │                    │ us-docker.pkg.dev/zenml-core/us.gcr.io          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

After having set up or decided on a GCP Service Connector to use to connect to the target GCR registry, you can register the GCP Container Registry as follows:

```sh
# Register the GCP container registry and reference the target GCR registry URI
zenml container-registry register <CONTAINER_REGISTRY_NAME> -f gcp \
    --uri=<REGISTRY_URL>

# Connect the GCP container registry to the target GCR registry via a GCP Service Connector
zenml container-registry connect <CONTAINER_REGISTRY_NAME> -i
```

A non-interactive version that connects the GCP Container Registry to a target GCR registry through a GCP Service Connector:

```sh
zenml container-registry connect <CONTAINER_REGISTRY_NAME> --connector <CONNECTOR_ID>
```

{% hint style="info" %}
Linking the GCP Container Registry to a Service Connector means that your local Docker client is no longer authenticated to access the remote registry. If you need to manually interact with the remote registry via the Docker CLI, you can use the [local login Service Connector feature](../../how-to/auth-management/service-connectors-guide.md#configure-local-clients) to temporarily authenticate your local Docker client to the remote registry:

```sh
zenml service-connector login <CONNECTOR_NAME> --resource-type docker-registry
```

{% code title="Example Command Output" %}
```text
$ zenml service-connector login gcp-zenml-core --resource-type docker-registry
⠋ Attempting to configure local client using service connector 'gcp-zenml-core'...
WARNING! Your password will be stored unencrypted in /home/stefan/.docker/config.json.
Configure a credential helper to remove this warning. See
https://docs.docker.com/engine/reference/commandline/login/#credentials-store

The 'gcp-zenml-core' Docker Service Connector connector was used to successfully configure the local Docker/OCI container registry client/SDK.
```
{% endcode %}
{% endhint %}

{% code title="Example Command Output" %}
```text
$ zenml container-registry connect gcp-zenml-core --connector gcp-zenml-core 
Successfully connected container registry `gcp-zenml-core` to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE      │ RESOURCE NAMES                              ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼────────────────────┼─────────────────────────────────────────────┨
┃ 561b776a-af8b-491c-a4ed-14349b440f30 │ gcp-zenml-core │ 🔵 gcp         │ 🐳 docker-registry │ europe-west1-docker.pkg.dev/zenml-core/test ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

As a final step, you can use the GCP Container Registry in a ZenML Stack:

```sh
# Register and set a stack with the new container registry
zenml stack register <STACK_NAME> -c <CONTAINER_REGISTRY_NAME> ... --set
```
{% endtab %}
{% endtabs %}

For more information and a full list of configurable attributes of the GCP container registry, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/core\_code\_docs/core-container\_registries/#zenml.container\_registries.gcp\_container\_registry.GCPContainerRegistry) .

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
