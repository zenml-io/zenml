---
description: Store container images in GCR
---

The GCP container registry is a [container registry](./overview.md) flavor which comes built-in with 
ZenML and uses the [Google Container Registry](https://cloud.google.com/container-registry)
to store container images.

## When to use it

You should use the GCP container registry if:
* one or more components of your stack need to pull or push container images.
* you have access to GCP. If you're not using GCP, take a look at the
 other [container registry flavors](./overview.md#container-registry-flavors).

## How to deploy it

All you need to do to use the GCP container registry is enabling it [here](https://console.cloud.google.com/marketplace/product/google/containerregistry.googleapis.com).

## How to find the registry URI

The GCP container registry URI should have one of the following formats:
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

## How to use it

To use the Azure container registry, we need:
* [Docker](https://www.docker.com) installed and running.
* The [GCP CLI](https://cloud.google.com/sdk/docs/install) installed and authenticated.
* The registry URI. Check out the [previous section](#uri-format) on the URI format and how
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
```shell
gcloud auth configure-docker
```

For more information and a full list of configurable attributes of the GCP container registry, check out the 
[API Docs](https://apidocs.zenml.io/latest/api_docs/container_registries/#zenml.container_registries.gcp_container_registry.GCPContainerRegistry).
