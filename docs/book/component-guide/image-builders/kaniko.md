---
description: Building container images with Kaniko.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Kaniko Image Builder

The Kaniko image builder is an [image builder](./image-builders.md) flavor provided by the ZenML `kaniko` integration that uses [Kaniko](https://github.com/GoogleContainerTools/kaniko) to build container images.

### When to use it

You should use the Kaniko image builder if:

* you're **unable** to install or use [Docker](https://www.docker.com) on your client machine.
* you're familiar with/already using Kubernetes.

### How to deploy it

In order to use the Kaniko image builder, you need a deployed Kubernetes cluster.

### How to use it

To use the Kaniko image builder, we need:

*   The ZenML `kaniko` integration installed. If you haven't done so, run

    ```shell
    zenml integration install kaniko
    ```
* [kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl) installed.
* A [remote container registry](../container-registries/container-registries.md) as part of your stack.
* By default, the Kaniko image builder transfers the build context using the Kubernetes API. If you instead want to transfer the build context by storing it in the artifact store, you need to register it with the `store_context_in_artifact_store` attribute set to `True`. In this case, you also need a [remote artifact store](../artifact-stores/artifact-stores.md) as part of your stack.
* Optionally, you can change the timeout (in seconds) until the Kaniko pod is running in the orchestrator using the `pod_running_timeout` attribute.

We can then register the image builder and use it in our active stack:

```shell
zenml image-builder register <NAME> \
    --flavor=kaniko \
    --kubernetes_context=<KUBERNETES_CONTEXT>
    [ --pod_running_timeout=<POD_RUNNING_TIMEOUT_IN_SECONDS> ]

# Register and activate a stack with the new image builder
zenml stack register <STACK_NAME> -i <NAME> ... --set
```

For more information and a full list of configurable attributes of the Kaniko image builder, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-kaniko/#zenml.integrations.kaniko.image\_builders.kaniko\_image\_builder.KanikoImageBuilder) .

#### Authentication for the container registry and artifact store

The Kaniko image builder will create a Kubernetes pod that is running the build. This build pod needs to be able to pull from/push to certain container registries, and depending on the stack component configuration also needs to be able to read from the artifact store:

* The pod needs to be authenticated to push to the container registry in your active stack.
* In case the [parent image](../../how-to/infrastructure-deployment/customize-docker-builds/docker-settings-on-a-pipeline.md#using-a-custom-parent-image) you use in your `DockerSettings` is stored in a private registry, the pod needs to be authenticated to pull from this registry.
* If you configured your image builder to store the build context in the artifact store, the pod needs to be authenticated to read files from the artifact store storage.

ZenML is not yet able to handle setting all of the credentials of the various combinations of container registries and artifact stores on the Kaniko build pod, which is you're required to set this up yourself for now. The following section outlines how to handle it in the most straightforward (and probably also most common) scenario, when the Kubernetes cluster you're using for the Kaniko build is hosted on the same cloud provider as your container registry (and potentially the artifact store). For all other cases, check out the [official Kaniko repository](https://github.com/GoogleContainerTools/kaniko) for more information.

{% tabs %}
{% tab title="AWS" %}
* Add permissions to push to ECR by attaching the `EC2InstanceProfileForImageBuilderECRContainerBuilds` policy to your [EKS node IAM role](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html).
* Configure the image builder to set some required environment variables on the Kaniko build pod:

```shell
# register a new image builder with the environment variables
zenml image-builder register <NAME> \
    --flavor=kaniko \
    --kubernetes_context=<KUBERNETES_CONTEXT> \
    --env='[{"name": "AWS_SDK_LOAD_CONFIG", "value": "true"}, {"name": "AWS_EC2_METADATA_DISABLED", "value": "true"}]'

# or update an existing one
zenml image-builder update <NAME> \
    --env='[{"name": "AWS_SDK_LOAD_CONFIG", "value": "true"}, {"name": "AWS_EC2_METADATA_DISABLED", "value": "true"}]'
```

Check out [the Kaniko docs](https://github.com/GoogleContainerTools/kaniko#pushing-to-amazon-ecr) for more information.
{% endtab %}

{% tab title="GCP" %}
* [Enable workload identity](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity#enable\_on\_cluster) for your cluster
* Follow the steps described [here](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity#authenticating\_to) to create a Google service account, a Kubernetes service account as well as an IAM policy binding between them.
* Grant the Google service account permissions to push to your GCR registry and read from your GCP bucket.
* Configure the image builder to run in the correct namespace and use the correct service account:

```shell
# register a new image builder with namespace and service account
zenml image-builder register <NAME> \
    --flavor=kaniko \
    --kubernetes_context=<KUBERNETES_CONTEXT> \
    --kubernetes_namespace=<KUBERNETES_NAMESPACE> \
    --service_account_name=<KUBERNETES_SERVICE_ACCOUNT_NAME>
    # --executor_args='["--compressed-caching=false", "--use-new-run=true"]'

# or update an existing one
zenml image-builder update <NAME> \
    --kubernetes_namespace=<KUBERNETES_NAMESPACE> \
    --service_account_name=<KUBERNETES_SERVICE_ACCOUNT_NAME>
```

Check out [the Kaniko docs](https://github.com/GoogleContainerTools/kaniko#pushing-to-google-gcr) for more information.
{% endtab %}

{% tab title="Azure" %}
* Create a Kubernetes `configmap` for a Docker config that uses the Azure credentials helper:

```shell
kubectl create configmap docker-config --from-literal='config.json={ "credHelpers": { "mycr.azurecr.io": "acr-env" } }'
```

* Follow [these steps](https://learn.microsoft.com/en-us/azure/aks/use-managed-identity) to configure your cluster to use a managed identity
* Configure the image builder to mount the `configmap` in the Kaniko build pod:

```shell
# register a new image builder with the mounted configmap
zenml image-builder register <NAME> \
    --flavor=kaniko \
    --kubernetes_context=<KUBERNETES_CONTEXT> \
    --volume_mounts='[{"name": "docker-config", "mountPath": "/kaniko/.docker/"}]' \
    --volumes='[{"name": "docker-config", "configMap": {"name": "docker-config"}}]'
    # --executor_args='["--compressed-caching=false", "--use-new-run=true"]'

# or update an existing one
zenml image-builder update <NAME> \
    --volume_mounts='[{"name": "docker-config", "mountPath": "/kaniko/.docker/"}]' \
    --volumes='[{"name": "docker-config", "configMap": {"name": "docker-config"}}]'
```

Check out [the Kaniko docs](https://github.com/GoogleContainerTools/kaniko#pushing-to-azure-container-registry) for more information.
{% endtab %}
{% endtabs %}

#### Passing additional parameters to the Kaniko build

You can pass additional parameters to the Kaniko build by setting the `executor_args` attribute of the image builder.

```shell
zenml image-builder register <NAME> \
    --flavor=kaniko \
    --kubernetes_context=<KUBERNETES_CONTEXT> \
    --executor_args='["--label", "key=value"]' # Adds a label to the final image
```

List of some possible additional flags:

* `--cache`: Set to `false` to disable caching. Defaults to `true`.
* `--cache-dir`: Set the directory where to store cached layers. Defaults to `/cache`.
* `--cache-repo`: Set the repository where to store cached layers. Defaults to `gcr.io/kaniko-project/executor`.
* `--cache-ttl`: Set the cache expiration time. Defaults to `24h`.
* `--cleanup`: Set to `false` to disable cleanup of the working directory. Defaults to `true`.
* `--compressed-caching`: Set to `false` to disable compressed caching. Defaults to `true`.

For a full list of possible flags, check out the [Kaniko additional flags](https://github.com/GoogleContainerTools/kaniko#additional-flags)

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
