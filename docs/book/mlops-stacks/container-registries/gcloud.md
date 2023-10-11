---
description: How to store container images in GCP
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


The GCP container registry is a [container registry](./container-registries.md) flavor which comes built-in with 
ZenML and uses the [Google Artifact Registry](https://cloud.google.com/artifact-registry) or the 
[Google Container Registry](https://cloud.google.com/container-registry)
to store container images.

## When to use it

You should use the GCP container registry if:
* one or more components of your stack need to pull or push container images.
* you have access to GCP. If you're not using GCP, take a look at the
 other [container registry flavors](./container-registries.md#container-registry-flavors).

## How to deploy it

{% tabs %}
{% tab title="Google Container Registry" %}

When using the Google Container Registry, all you need to do is enabling it
[here](https://console.cloud.google.com/marketplace/product/google/containerregistry.googleapis.com).


{% endtab %}
{% tab title="Google Artifact Registry" %}

When using the Google Artifact Registry, you need to:
* enable it [here](https://console.cloud.google.com/marketplace/product/google/artifactregistry.googleapis.com)
* go [here](https://console.cloud.google.com/artifacts) and create a `Docker` repository.

{% endtab %}
{% endtabs %}

## How to find the registry URI

{% tabs %}
{% tab title="Google Container Registry" %}

When using the Google Container Registry, the GCP container 
registry URI should have one of the following formats:

```shell
gcr.io/<PROJECT_ID>
# or
us.gcr.io/<PROJECT_ID>
# or
eu.gcr.io/<PROJECT_ID>
# or
asia.gcr.io/<PROJECT_ID>

# Examples:
gcr.io/zenml
us.gcr.io/my-project
asia.gcr.io/another-project
```

To figure our the URI for your registry:
* Go to the [GCP console](https://console.cloud.google.com/).
* Click on the dropdown menu in the top left to get a list of available projects with their names and IDs.
* Use the ID of the project you want to use fill the template `gcr.io/<PROJECT_ID>` and get your URI
(You can also use the other prefixes `<us/eu/asia>.gcr.io` as explained above if you want your images stored in a different region).

{% endtab %}
{% tab title="Google Artifact Registry" %}

When using the Google Artifact Registry, the GCP container 
registry URI should have the following format:

```shell
<REGION>-docker.pkg.dev/<PROJECT_ID>/<REPOSITORY_NAME>

# Examples:
europe-west1-docker.pkg.dev/zenml/my-repo
southamerica-east1-docker.pkg.dev/zenml/zenml-test
asia-docker.pkg.dev/my-project/another-repo
```

To figure our the URI for your registry:
* Go [here](https://console.cloud.google.com/artifacts) and select the repository that
you want to uses to store Docker images. If you don't have a repository yet, take a look
at the [deployment section](#how-to-deploy-it).
* On the top, click the copy button to copy the full repository URL.

{% endtab %}
{% endtabs %}


## How to use it

To use the Azure container registry, we need:
* [Docker](https://www.docker.com) installed and running.
* The [GCP CLI](https://cloud.google.com/sdk/docs/install) installed and authenticated.
* The registry URI. Check out the [previous section](#how-to-find-the-registry-uri) on the URI format and how
to get the URI for your registry.

We can then register the container registry and use it in our active stack:
```shell
zenml container-registry register <NAME> \
    --flavor=gcp \
    --uri=<REGISTRY_URI>

# Add the container registry to the active stack
zenml stack update -c <NAME>
```

Additionally, we'll need to configure Docker so it can pull and push images:

{% tabs %}
{% tab title="Google Container Registry" %}

```shell
gcloud auth configure-docker
```

{% endtab %}
{% tab title="Google Artifact Registry" %}

```shell
gcloud auth configure-docker <REGION>-docker.pkg.dev
```

{% endtab %}
{% endtabs %}


For more information and a full list of configurable attributes of the GCP container registry, check out the 
[API Docs](https://apidocs.zenml.io/latest/api_docs/container_registries/#zenml.container_registries.gcp_container_registry.GCPContainerRegistry).
