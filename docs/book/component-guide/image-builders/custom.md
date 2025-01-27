---
description: Learning how to develop a custom image builder.
---

# Develop a Custom Image Builder

{% hint style="info" %}
Before diving into the specifics of this component type, it is beneficial to familiarize yourself with our [general guide to writing custom component flavors in ZenML](../../how-to/infrastructure-deployment/stack-deployment/implement-a-custom-stack-component.md). This guide provides an essential understanding of ZenML's component flavor concepts.
{% endhint %}

### Base Abstraction

The `BaseImageBuilder` is the abstract base class that needs to be subclassed in order to create a custom component that can be used to build Docker images. As image builders can come in many shapes and forms, the base class exposes a deliberately basic and generic interface:

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, cast

from zenml.container_registries import BaseContainerRegistry
from zenml.enums import StackComponentType
from zenml.image_builders import BuildContext
from zenml.stack import Flavor, StackComponent
from zenml.stack.stack_component import StackComponentConfig


class BaseImageBuilder(StackComponent, ABC):
    """Base class for all ZenML image builders."""

    @property
    def build_context_class(self) -> Type["BuildContext"]:
        """Build context class to use.

        The default build context class creates a build context that works
        for the Docker daemon. Override this method if your image builder
        requires a custom context.

        Returns:
            The build context class.
        """
        return BuildContext

    @abstractmethod
    def build(
            self,
            image_name: str,
            build_context: "BuildContext",
            docker_build_options: Dict[str, Any],
            container_registry: Optional["BaseContainerRegistry"] = None,
    ) -> str:
        """Builds a Docker image.

        If a container registry is passed, the image will be pushed to that
        registry.

        Args:
            image_name: Name of the image to build.
            build_context: The build context to use for the image.
            docker_build_options: Docker build options.
            container_registry: Optional container registry to push to.

        Returns:
            The Docker image repo digest or name.
        """
```

{% hint style="info" %}
This is a slimmed-down version of the base implementation which aims to highlight the abstraction layer. In order to see the full implementation and get the complete docstrings, please check [the source code on GitHub](https://github.com/zenml-io/zenml/blob/main/src/zenml/image\_builders/base\_image\_builder.py) .
{% endhint %}

### Build your own custom image builder

If you want to create your own custom flavor for an image builder, you can follow the following steps:

1. Create a class that inherits from the `BaseImageBuilder` class and implement the abstract `build` method. This method should use the given build context and build a Docker image with it. If additionally a container registry is passed to the `build` method, the image builder is also responsible for pushing the image there.
2. If you need to provide any configuration, create a class that inherits from the `BaseImageBuilderConfig` class and adds your configuration parameters.
3. Bring both the implementation and the configuration together by inheriting from the `BaseImageBuilderFlavor` class. Make sure that you give a `name` to the flavor through its abstract property.

Once you are done with the implementation, you can register it through the CLI. Please ensure you **point to the flavor class via dot notation**:

```shell
zenml image-builder flavor register <path.to.MyImageBuilderFlavor>
```

For example, if your flavor class `MyImageBuilderFlavor` is defined in `flavors/my_flavor.py`, you'd register it by doing:

```shell
zenml image-builder flavor register flavors.my_flavor.MyImageBuilderFlavor
```

{% hint style="warning" %}
ZenML resolves the flavor class by taking the path where you initialized zenml (via `zenml init`) as the starting point of resolution. Therefore, please ensure you follow [the best practice](../../how-to/infrastructure-deployment/infrastructure-as-code/best-practices.md) of initializing zenml at the root of your repository.

If ZenML does not find an initialized ZenML repository in any parent directory, it will default to the current working directory, but usually it's better to not have to rely on this mechanism, and initialize zenml at the root.
{% endhint %}

Afterward, you should see the new flavor in the list of available flavors:

```shell
zenml image-builder flavor list
```

{% hint style="warning" %}
It is important to draw attention to when and how these base abstractions are coming into play in a ZenML workflow.

* The **CustomImageBuilderFlavor** class is imported and utilized upon the creation of the custom flavor through the CLI.
* The **CustomImageBuilderConfig** class is imported when someone tries to register/update a stack component with this custom flavor. Especially, during the registration process of the stack component, the config will be used to validate the values given by the user. As `Config` objects are inherently `pydantic` objects, you can also add your own custom validators here.
* The **CustomImageBuilder** only comes into play when the component is ultimately in use.

The design behind this interaction lets us separate the configuration of the flavor from its implementation. This way we can register flavors and components even when the major dependencies behind their implementation are not installed in our local setting (assuming the `CustomImageBuilderFlavor` and the `CustomImageBuilderConfig` are implemented in a different module/path than the actual `CustomImageBuilder`).
{% endhint %}

#### Using a custom-build context

The `BaseImageBuilder` abstraction uses the `build_context_class` to provide a class that should be used as the build context. In case your custom image builder requires a different build context than the default Docker build context, you can subclass the `BuildContext` class to customize the structure of your build context. In your image builder implementation, you can then overwrite the `build_context_class` property to specify your build context subclass.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
