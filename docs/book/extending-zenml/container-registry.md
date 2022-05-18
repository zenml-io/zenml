---
description: Setting up the storage for your containers.
---

A container registry is a store for (Docker) containers. A ZenML workflow 
involving a container registry would automatically containerize your code to 
be transported across stacks running remotely. As part of the deployment to the
cluster, the ZenML base image would be downloaded (from a cloud container 
registry) and used as the basis for the deployed 'run'.

For instance, when you are running a local container-based stack, you would 
therefore have a local container registry which stores the container images 
you create that bundle up your pipeline code. You could also use a remote 
container registry like the Elastic Container Registry at AWS in a  production 
setting.

{% hint style="warning" %}
Before reading this chapter, make sure that you are familiar with the concept of 
[stacks, stack components and their flavors](./stacks-components-flavors.md).  
{% endhint %}

## Base Abstraction

In the current version of ZenML, container registries have a rather simple base 
abstraction. In essence, each container registry features a `uri` as an 
instance configuration and a non-abstract `prepare_image_push` method for 
validation.

```python
from typing import ClassVar

from zenml.enums import StackComponentType
from zenml.stack import StackComponent
from zenml.utils import docker_utils


class BaseContainerRegistry(StackComponent):
    """Base class for all ZenML container registries."""
    
    # Instance configuration
    uri: str

    # Class variables
    TYPE: ClassVar[StackComponentType] = StackComponentType.CONTAINER_REGISTRY

    def prepare_image_push(self, image_name: str) -> None:
        """Conduct necessary checks/preparations before an image gets pushed."""

    def push_image(self, image_name: str) -> None:
        """Pushes a docker image."""
        if not image_name.startswith(self.uri):
            raise ValueError(
                f"Docker image `{image_name}` does not belong to container "
                f"registry `{self.uri}`."
            )

        self.prepare_image_push(image_name)
        docker_utils.push_docker_image(image_name)
```

{% hint style="info" %}
This is a slimmed-down version of the base implementation which aims to 
highlight the abstraction layer. In order to see the full implementation 
and get the complete docstrings, please check the [API docs](https://apidocs.zenml.io/latest/api_docs/container_registries/#zenml.container_registries.base_container_registry.BaseContainerRegistry).
{% endhint %}

## List of available container registry

ZenML comes built-in with several flavors for container registries:

|                            | Flavor    | Integration    |
|----------------------------|-----------|----------------|
| DefaultContainerRegistry   | default   | `built-in`     |
| DockerHubContainerRegistry | dockerhub | `built-in`     |
| GCPContainerRegistry       | gcp       | `built-in`     |
| AzureContainerRegistry     | azure     | `built-in`     |
| AWSContainerRegistry       | aws       | aws            |

If you would like to see the available flavors for container registries, you can 
use the command:

```shell
zenml container-registry flavor list
```

## Building your own container registry

If you want to create your own custom flavor for a container registry, you can 
follow the following steps:

1. Create a class which inherits from the `BaseContainerRegistry`.
2. Define the `FLAVOR` class variable.
3. If you need to execute any checks/validation before the image gets pushed, 
you can define these operations in the `prepare_image_push` method. As an 
example, you can check the `AWSContainerRegistry`.
4. Once the `prepare_image_push` gets completed, the `push_image` method will 
come into play and utilize a `DockerClient` object to push the image.

Once you are done with the implementation, you can register it through the CLI 
as:

```shell
zenml container-registry flavor register <THE-SOURCE-PATH-OF-YOUR-REGISTRY>
```