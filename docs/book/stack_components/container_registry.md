---
description: Setting up the storage for your containers 
---

A container registry is a store for (Docker) containers. A ZenML workflow 
involving a container registry would automatically containerize your code to 
be transported across stacks running remotely. As part of the deployment to the
cluster, the ZenML base image would be downloaded (from a cloud container 
registry) and used as the basis for the deployed 'run'.

For instance, when you are running a local container-based stack, you would 
therefore have a local container registry which stores the container images 
you create that bundle up your pipeline code. You could also use a remote 
container registry like the Elastic Container Registry at AWS in a 
more production setting.

{% hint style="warning" %} 
Before reading this chapter, make sure that you are familiar with the concept of 
[stacks, stack components and their flavors](./introduction.md).  
{% endhint %}

## Base Abstraction

```python
import re
from typing import ClassVar

from pydantic import validator

from zenml.enums import ContainerRegistryFlavor, StackComponentType
from zenml.stack import StackComponent
from zenml.utils import docker_utils


class BaseContainerRegistry(StackComponent):
    """Base class for all ZenML container registries.

    Attributes:
        uri: The URI of the container registry.
    """

    # Instance configuration
    uri: str

    # Class variables
    TYPE: ClassVar[StackComponentType] = StackComponentType.CONTAINER_REGISTRY
    FLAVOR: ClassVar[str] = ContainerRegistryFlavor.DEFAULT.value

    def prepare_image_push(self, image_name: str) -> None:
        """Method that subclasses can overwrite to do any necessary checks or
        preparations before an image gets pushed.

        Args:
            image_name: Name of the docker image that will be pushed.
        """

    def push_image(self, image_name: str) -> None:
        """Pushes a docker image.

        Args:
            image_name: Name of the docker image that will be pushed.

        Raises:
            ValueError: If the image name is not associated with this
                container registry.
        """
        if not image_name.startswith(self.uri):
            raise ValueError(
                f"Docker image `{image_name}` does not belong to container "
                f"registry `{self.uri}`."
            )

        self.prepare_image_push(image_name)
        docker_utils.push_docker_image(image_name)

```

## List of available container registry

|                     | Flavor | Integration |
|---------------------|--------|-------------|
| BaseContainerRegistry | default | `built-in` |
| DockerHubContainerRegistry  | dockerhub  | `built-in`  |
| GCPContainerRegistry     | gcp     | `built-in`         |
| AzureContainerRegistry    | azure    | `built-in`          |
| AWSContainerRegistry    | aws    | aws          |
| GitHubContainerRegistry  | github  | `built-in`        |
| GitLabContainerRegistry  | gitlab  | `built-in`        |

## Building your own container registry

WIP
