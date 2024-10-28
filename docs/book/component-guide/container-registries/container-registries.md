---
icon: box
description: Setting up a storage for Docker images.
---

# Container Registries

The container registry is an essential part of most remote MLOps stacks. It is used to store container images that are
built to run machine learning pipelines in remote environments. Containerization of the pipeline code creates a portable
environment that allows code to run in an isolated manner.

### When to use it

The container registry is needed whenever other components of your stack need to push or pull container images.
Currently, this is the case for most of ZenML's remote [orchestrators](../orchestrators/orchestrators.md)
, [step operators](../step-operators/step-operators.md), and
some [model deployers](../model-deployers/model-deployers.md). These containerize your pipeline code and therefore
require a container registry to store the resulting [Docker](https://www.docker.com/) images. Take a look at the
documentation page of the component you want to use in your stack to see if it requires a container registry or even a
specific container registry flavor.

### Container Registry Flavors

ZenML comes with a few container registry flavors that you can use:

* Default flavor: Allows any URI without validation. Use this if you want to use a local container registry or when
  using a remote container registry that is not covered by other flavors.
* Specific flavors: Validates your container registry URI and performs additional checks to ensure you're able to push
  to the registry.

{% hint style="warning" %}
We highly suggest using the specific container registry flavors in favor of the `default` one to make use of the
additional URI validations.
{% endhint %}

| Container Registry                         | Flavor      | Integration | URI example                               |
|--------------------------------------------|-------------|-------------|-------------------------------------------|
| [DefaultContainerRegistry](default.md)     | `default`   | _built-in_  | -                                         |
| [DockerHubContainerRegistry](dockerhub.md) | `dockerhub` | _built-in_  | docker.io/zenml                           |
| [GCPContainerRegistry](gcp.md)             | `gcp`       | _built-in_  | gcr.io/zenml                              |
| [AzureContainerRegistry](azure.md)         | `azure`     | _built-in_  | zenml.azurecr.io                          |
| [GitHubContainerRegistry](github.md)       | `github`    | _built-in_  | ghcr.io/zenml                             |
| [AWSContainerRegistry](aws.md)             | `aws`       | `aws`       | 123456789.dkr.ecr.us-east-1.amazonaws.com |

If you would like to see the available flavors of container registries, you can use the command:

```shell
zenml container-registry flavor list
```

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
