---
description: Building container images with Google Cloud Build
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Google Cloud Image Builder

The Google Cloud image builder is an [image builder](./image-builders.md) flavor provided by the ZenML `gcp` integration that uses [Google Cloud Build](https://cloud.google.com/build) to build container images.

### When to use it

You should use the Google Cloud image builder if:

* you're **unable** to install or use [Docker](https://www.docker.com) on your client machine.
* you're already using GCP.
* your stack is mainly composed of other Google Cloud components such as the [GCS Artifact Store](../artifact-stores/gcp.md) or the [Vertex Orchestrator](../orchestrators/vertex.md).

### How to deploy it

{% hint style="info" %}
Would you like to skip ahead and deploy a full ZenML cloud stack already,
including the Google Cloud image builder? Check out the
[in-browser stack deployment wizard](../../how-to/infrastructure-deployment/stack-deployment/deploy-a-cloud-stack.md),
the [stack registration wizard](../../how-to/infrastructure-deployment/stack-deployment/register-a-cloud-stack.md),
or [the ZenML GCP Terraform module](../../how-to/infrastructure-deployment/stack-deployment/deploy-a-cloud-stack-with-terraform.md)
for a shortcut on how to deploy & register this stack component.
{% endhint %}

In order to use the ZenML Google Cloud image builder you need to enable Google Cloud Build relevant APIs on the Google Cloud project.

### How to use it

To use the Google Cloud image builder, we need:

*   The ZenML `gcp` integration installed. If you haven't done so, run:

    ```shell
    zenml integration install gcp
    ```
* A [GCP Artifact Store](../artifact-stores/gcp.md) where the build context will be uploaded, so Google Cloud Build can access it.
* A [GCP container registry](../container-registries/gcp.md) where the built image will be pushed.
* Optionally, the GCP project ID in which you want to run the build and a service account with the needed permissions to run the build. If not provided, then the project ID and credentials will be inferred from the environment.
* Optionally, you can change:
  * the Docker image used by Google Cloud Build to execute the steps to build and push the Docker image. By default, the builder image will be `'gcr.io/cloud-builders/docker'`.
  * The network to which the container used to build the ZenML pipeline Docker image will be attached. More information: [Cloud build network](https://cloud.google.com/build/docs/build-config-file-schema#network).
  * The build timeout for the build, and for the blocking operation waiting for the build to finish. More information: [Build Timeout](https://cloud.google.com/build/docs/build-config-file-schema#timeout\_2).

We can register the image builder and use it in our active stack:

```shell
zenml image-builder register <IMAGE_BUILDER_NAME> \
    --flavor=gcp \
    --cloud_builder_image=<BUILDER_IMAGE_NAME> \
    --network=<DOCKER_NETWORK> \
    --build_timeout=<BUILD_TIMEOUT_IN_SECONDS>

# Register and activate a stack with the new image builder
zenml stack register <STACK_NAME> -i <IMAGE_BUILDER_NAME> ... --set
```

You also need to set up [authentication](gcp.md#authentication-methods) required to access the Cloud Build GCP services.

#### Authentication Methods

Integrating and using a GCP Image Builder in your pipelines is not possible without employing some form of authentication. If you're looking for a quick way to get started locally, you can use the _Local Authentication_ method. However, the recommended way to authenticate to the GCP cloud platform is through [a GCP Service Connector](../../how-to/infrastructure-deployment/auth-management/gcp-service-connector.md). This is particularly useful if you are configuring ZenML stacks that combine the GCP Image Builder with other remote stack components also running in GCP.

{% tabs %}
{% tab title="Implicit Authentication" %}
This method uses the implicit GCP authentication available _in the environment where the ZenML code is running_. On your local machine, this is the quickest way to configure a GCP Image Builder. You don't need to supply credentials explicitly when you register the GCP Image Builder, as it leverages the local credentials and configuration that the Google Cloud CLI stores on your local machine. However, you will need to install and set up the Google Cloud CLI on your machine as a prerequisite, as covered in [the Google Cloud documentation](https://cloud.google.com/sdk/docs/install-sdk) , before you register the GCP Image Builder.

{% hint style="warning" %}
Stacks using the GCP Image Builder set up with local authentication are not portable across environments. To make ZenML pipelines fully portable, it is recommended to use [a GCP Service Connector](../../how-to/infrastructure-deployment/auth-management/gcp-service-connector.md) to authenticate your GCP Image Builder to the GCP cloud platform.
{% endhint %}
{% endtab %}

{% tab title="GCP Service Connector (recommended)" %}
To set up the GCP Image Builder to authenticate to GCP and access the GCP Cloud Build services, it is recommended to leverage the many features provided by [the GCP Service Connector](../../how-to/infrastructure-deployment/auth-management/gcp-service-connector.md) such as auto-configuration, best security practices regarding long-lived credentials and reusing the same credentials across multiple stack components.

If you don't already have a GCP Service Connector configured in your ZenML deployment, you can register one using the interactive CLI command. You also have the option to configure a GCP Service Connector that can be used to access more than just the GCP Cloud Build service:

```sh
zenml service-connector register --type gcp -i
```

A non-interactive CLI example that leverages [the Google Cloud CLI configuration](https://cloud.google.com/sdk/docs/install-sdk) on your local machine to auto-configure a GCP Service Connector for the GCP Cloud Build service:

```sh
zenml service-connector register <CONNECTOR_NAME> --type gcp --resource-type gcp-generic --resource-name <GCS_BUCKET_NAME> --auto-configure
```

{% code title="Example Command Output" %}
```
$ zenml service-connector register gcp-generic --type gcp --resource-type gcp-generic --auto-configure
Successfully registered service connector `gcp-generic` with access to the following resources:
┏━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃ RESOURCE TYPE  │ RESOURCE NAMES ┃
┠────────────────┼────────────────┨
┃ 🔵 gcp-generic │ zenml-core     ┃
┗━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛
```
{% endcode %}

> **Note**: Please remember to grant the entity associated with your GCP credentials permissions to access the Cloud Build API and to run Cloud Builder jobs (e.g. the [Cloud Build Editor IAM role](https://cloud.google.com/build/docs/iam-roles-permissions#predefined\_roles)). The GCP Service Connector supports [many different authentication methods](../../how-to/infrastructure-deployment/auth-management/gcp-service-connector.md#authentication-methods) with different levels of security and convenience. You should pick the one that best fits your use case.

If you already have one or more GCP Service Connectors configured in your ZenML deployment, you can check which of them can be used to access generic GCP resources like the GCP Image Builder required for your GCP Image Builder by running e.g.:

```sh
zenml service-connector list-resources --resource-type gcp-generic
```

{% code title="Example Command Output" %}
```
The following 'gcp-generic' resources can be accessed by service connectors that you have configured:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE  │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼────────────────┼────────────────┨
┃ bfdb657d-d808-47e7-9974-9ba6e4919d83 │ gcp-generic    │ 🔵 gcp         │ 🔵 gcp-generic │ zenml-core     ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛
```
{% endcode %}

After having set up or decided on a GCP Service Connector to use to authenticate to GCP, you can register the GCP Image Builder as follows:

```sh
zenml image-builder register <IMAGE_BUILDER_NAME> \
    --flavor=gcp \
    --cloud_builder_image=<BUILDER_IMAGE_NAME> \
    --network=<DOCKER_NETWORK> \
    --build_timeout=<BUILD_TIMEOUT_IN_SECONDS>

# Connect the GCP Image Builder to GCP via a GCP Service Connector
zenml image-builder connect <IMAGE_BUILDER_NAME> -i
```

A non-interactive version that connects the GCP Image Builder to a target GCP Service Connector:

```sh
zenml image-builder connect <IMAGE_BUILDER_NAME> --connector <CONNECTOR_ID>
```

{% code title="Example Command Output" %}
```
$ zenml image-builder connect gcp-image-builder --connector gcp-generic
Successfully connected image builder `gcp-image-builder` to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE  │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼────────────────┼────────────────┨
┃ bfdb657d-d808-47e7-9974-9ba6e4919d83 │ gcp-generic    │ 🔵 gcp         │ 🔵 gcp-generic │ zenml-core     ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛
```
{% endcode %}

As a final step, you can use the GCP Image Builder in a ZenML Stack:

```sh
# Register and set a stack with the new image builder
zenml stack register <STACK_NAME> -i <IMAGE_BUILDER_NAME> ... --set
```
{% endtab %}

{% tab title="GCP Credentials" %}
When you register the GCP Image Builder, you can [generate a GCP Service Account Key](https://cloud.google.com/docs/authentication/application-default-credentials#attached-sa), save it to a local file and then reference it in the Image Builder configuration.

This method has the advantage that you don't need to install and configure the GCP CLI on your host, but it's still not as secure as using a GCP Service Connector and the stack component configuration is not portable to other hosts.

For this method, you need to [create a user-managed GCP service account](https://cloud.google.com/iam/docs/service-accounts-create), and grant it privileges to access the Cloud Build API and to run Cloud Builder jobs (e.g. the [Cloud Build Editor IAM role](https://cloud.google.com/build/docs/iam-roles-permissions#predefined\_roles).

With the service account key downloaded to a local file, you can register the GCP Image Builder as follows:

```shell
zenml image-builder register <IMAGE_BUILDER_NAME> \
    --flavor=gcp \
    --project=<GCP_PROJECT_ID> \
    --service_account_path=<PATH_TO_SERVICE_ACCOUNT_KEY> \
    --cloud_builder_image=<BUILDER_IMAGE_NAME> \
    --network=<DOCKER_NETWORK> \
    --build_timeout=<BUILD_TIMEOUT_IN_SECONDS>

# Register and set a stack with the new image builder
zenml stack register <STACK_NAME> -i <IMAGE_BUILDER_NAME> ... --set
```
{% endtab %}
{% endtabs %}

### Caveats

As described in this [Google Cloud Build documentation page](https://cloud.google.com/build/docs/build-config-file-schema#network), Google Cloud Build uses containers to execute the build steps which are automatically attached to a network called `cloudbuild` that provides some Application Default Credentials (ADC), that allow the container to be authenticated and therefore use other GCP services.

By default, the GCP Image Builder is executing the build command of the ZenML Pipeline Docker image with the option `--network=cloudbuild`, so the ADC provided by the `cloudbuild` network can also be used in the build. This is useful if you want to install a private dependency from a GCP Artifact Registry, but you will also need to use a [custom base parent image](../../how-to/infrastructure-deployment/customize-docker-builds/docker-settings-on-a-pipeline.md) with the [`keyrings.google-artifactregistry-auth`](https://pypi.org/project/keyrings.google-artifactregistry-auth/) installed, so `pip` can connect and authenticate in the private artifact registry to download the dependency.

```dockerfile
FROM zenmldocker/zenml:latest

RUN pip install keyrings.google-artifactregistry-auth
```

{% hint style="warning" %}
The above `Dockerfile` uses `zenmldocker/zenml:latest` as a base image, but is recommended to change the tag to specify the ZenML version and Python version like `0.33.0-py3.10`.
{% endhint %}

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
