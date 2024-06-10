---
description: Learning how to develop a custom container registry.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Develop a custom container registry

{% hint style="info" %}
Before diving into the specifics of this component type, it is beneficial to familiarize yourself with our [general guide to writing custom component flavors in ZenML](../../how-to/stack-deployment/implement-a-custom-stack-component.md). This guide provides an essential understanding of ZenML's component flavor concepts.
{% endhint %}

### Base Abstraction

In the current version of ZenML, container registries have a rather basic base abstraction. In essence, their base configuration only features a `uri` and their implementation features a non-abstract `prepare_image_push` method for validation.

```python
from abc import abstractmethod
from typing import Type

from zenml.enums import StackComponentType
from zenml.stack import Flavor
from zenml.stack.authentication_mixin import (
    AuthenticationConfigMixin,
    AuthenticationMixin,
)
from zenml.utils import docker_utils


class BaseContainerRegistryConfig(AuthenticationConfigMixin):
    """Base config for a container registry."""

    uri: str


class BaseContainerRegistry(AuthenticationMixin):
    """Base class for all ZenML container registries."""

    def prepare_image_push(self, image_name: str) -> None:
        """Conduct necessary checks/preparations before an image gets pushed."""

    def push_image(self, image_name: str) -> str:
        """Pushes a Docker image."""
        if not image_name.startswith(self.config.uri):
            raise ValueError(
                f"Docker image `{image_name}` does not belong to container "
                f"registry `{self.config.uri}`."
            )

        self.prepare_image_push(image_name)
        return docker_utils.push_image(image_name)


class BaseContainerRegistryFlavor(Flavor):
    """Base flavor for container registries."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Returns the name of the flavor."""

    @property
    def type(self) -> StackComponentType:
        """Returns the flavor type."""
        return StackComponentType.CONTAINER_REGISTRY

    @property
    def config_class(self) -> Type[BaseContainerRegistryConfig]:
        """Config class for this flavor."""
        return BaseContainerRegistryConfig

    @property
    def implementation_class(self) -> Type[BaseContainerRegistry]:
        """Implementation class."""
        return BaseContainerRegistry
```

{% hint style="info" %}
This is a slimmed-down version of the base implementation which aims to highlight the abstraction layer. In order to see the full implementation and get the complete docstrings, please check the [SDK docs](https://sdkdocs.zenml.io/latest/core\_code\_docs/core-container\_registries/#zenml.container\_registries.base\_container\_registry.BaseContainerRegistry) .
{% endhint %}

### Building your own container registry

If you want to create your own custom flavor for a container registry, you can follow the following steps:

1. Create a class that inherits from the `BaseContainerRegistry` class and if you need to execute any checks/validation before the image gets pushed, you can define these operations in the `prepare_image_push` method. As an example, you can check the `AWSContainerRegistry`.
2. If you need further configuration, you can create a class which inherits from the `BaseContainerRegistryConfig` class.
3. Bring both the implementation and the configuration together by inheriting from the `BaseContainerRegistryFlavor` class.

Once you are done with the implementation, you can register it through the CLI. Please ensure you **point to the flavor class via dot notation**:

```shell
zenml container-registry flavor register <path.to.MyContainerRegistryFlavor>
```

For example, your flavor class `MyContainerRegistryFlavor` is defined in `flavors/my_flavor.py`, you'd register it by doing:

```shell
zenml container-registry flavor register flavors.my_flavor.MyContainerRegistryFlavor
```

{% hint style="warning" %}
ZenML resolves the flavor class by taking the path where you initialized zenml (via `zenml init`) as the starting point of resolution. Therefore, please ensure you follow [the best practice](../../how-to/setting-up-a-project-repository/best-practices.md) of initializing zenml at the root of your repository.

If ZenML does not find an initialized ZenML repository in any parent directory, it will default to the current working directory, but usually it's better to not have to rely on this mechanism, and initialize zenml at the root.
{% endhint %}

Afterward, you should see the new flavor in the list of available flavors:

```shell
zenml container-registry flavor list
```

{% hint style="warning" %}
It is important to draw attention to when and how these base abstractions are coming into play in a ZenML workflow.

* The **CustomContainerRegistryFlavor** class is imported and utilized upon the creation of the custom flavor through the CLI.
* The **CustomContainerRegistryConfig** class is imported when someone tries to register/update a stack component with this custom flavor. Especially, during the registration process of the stack component, the config will be used to validate the values given by the user. As `Config` object are inherently `pydantic` objects, you can also add your own custom validators here.
* The **CustomContainerRegistry** only comes into play when the component is ultimately in use.

The design behind this interaction lets us separate the configuration of the flavor from its implementation. This way we can register flavors and components even when the major dependencies behind their implementation are not installed in our local setting (assuming the `CustomContainerRegistryFlavor` and the `CustomContainerRegistryConfig` are implemented in a different module/path than the actual `CustomContainerRegistry`).
{% endhint %}

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
