---
description: How to build container images with Kaniko
---

The Kaniko image builder is an [image builder](./image-builders.md) flavor provided
with the ZenML `kaniko` integration that uses [Kaniko](https://github.com/GoogleContainerTools/kaniko)
to build container images.

## When to use it

You should use the Kaniko image builder if:
* you're **unable** to install or use [Docker](https://www.docker.com) on your client machine.
* you're familiar with/already using Kubernetes.

## How to deploy it

In order to use the Kaniko image builder, you need a deployed Kubernetes cluster.

## How to use it

To use the Kaniko image builder, we need:

* The ZenML `kaniko` integration installed. If you haven't done so, run 
    ```shell
    zenml integration install kaniko
    ```
* [kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl) installed.
* A [remote container registry](../container-registries/container-registries.md) 
as part of your stack.
* By default, the Kaniko image builder transfers the build context using the
Kubernetes API. If you instead want to transer the build context by storing it in the artifact
store, you need to register it with the `store_context_in_artifact_store` attribute set to `True`.
In this case, you also need a [remote artifact store](../artifact-stores/artifact-stores.md)
as part of your stack.

We can then register the image builder and use it in our active stack:
```shell
zenml image-builder register <NAME> \
    --flavor=kaniko \
    --kubernetes_context=<KUBERNETES_CONTEXT>

# Register and activate a stack with the new image builder
zenml stack register <STACK_NAME> -i <NAME> ... --set
```

For more information and a full list of configurable attributes of the Kaniko image builder,
check out the [API Docs](https://apidocs.zenml.io/latest/integration_code_docs/integrations-kaniko/#zenml.integrations.kaniko.image_builders.kaniko_image_builder.KanikoImageBuilder).

### Authentication for the container registry and artifact store

The Kaniko image builder will create a Kubernetes pod which is running the build. This build
pod needs to be able to pull from/push to certain container registries, and depending on the
stack component configuration also needs to be able to read from the artifact store:
* In case the parent image you use in your `DockerSettings` is stored in a private registry,
the pod needs to be authenticated to pull from this registry.
* The pod needs to be authenticated to push to the container registry in your active stack.
* If you configured your image builder to store the build context in the artifact store, the
pod needs to be authenticated to read files from the artifact store storage.

ZenML is not yet able to handle setting all of the credentials of the various combinations of
container registries and artifact stores on the Kaniko build pod, which is you're required to set
this up yourself for now. The following section outlines how to handle it in the most straightforward
(and probably also most common) scenario, when the Kubernetes cluster you're using for the
Kaniko build is hosted on the same cloud provider as your container registry (and potentially
the artifact store). For all other cases, check out the
[official Kaniko repository](https://github.com/GoogleContainerTools/kaniko) for more information.

{% tabs %}
{% tab title="AWS" %}

https://github.com/GoogleContainerTools/kaniko#pushing-to-amazon-ecr

* env: `AWS_SDK_LOAD_CONFIG=true`, `AWS_EC2_METADATA_DISABLED=true`

```shell
zenml image-builder register <NAME> \
    --flavor=kaniko \
    --kubernetes_context=<KUBERNETES_CONTEXT> \
    --env='[{"name": "AWS_SDK_LOAD_CONFIG", "value": "true"}, {"name": "AWS_EC2_METADATA_DISABLED", "value": "true"}]'
```

{% endtab %}

{% tab title="GCP" %}

https://github.com/GoogleContainerTools/kaniko#pushing-to-google-gcr

* Enable workload identity for your cluster
* Grant the Google service account permissions to push to your GCR registry and read from your
GCP bucket.

{% endtab %}

{% tab title="Azure" %}

https://github.com/GoogleContainerTools/kaniko#pushing-to-azure-container-registry

* config.json: `{ "credHelpers": { "mycr.azurecr.io": "acr-env" } }`

* `kubectl create configmap docker-config --from-file=<path to config.json>`

* configure managed service identity

```shell
zenml image-builder register <NAME> \
    --flavor=kaniko \
    --kubernetes_context=<KUBERNETES_CONTEXT> \
    --volume_mounts='[{"name": "docker-config", "mountPath": "/kaniko/.docker/"}]' \
    --volumes='[{"name": "docker-config", "configMap": {"name": "docker-config"}}]'
```

{% endtab %}
{% endtabs %}


### Passing additional parameters to the Kaniko build

If you want to pass [additional flags](https://github.com/GoogleContainerTools/kaniko#additional-flags)
to the Kaniko build, pass them as a json string when registering your image builder in the stack:
```shell
zenml image-builder register <NAME> \
    --flavor=kaniko \
    --kubernetes_context=<KUBERNETES_CONTEXT> \
    --executor_args='["--label", "key=value"]' # Adds a label to the final image
```