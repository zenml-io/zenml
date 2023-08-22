---
description: How to extend ZenML with plug-in flavor components.
---

# Develop a Custom Component Flavor in ZenML

ZenML is built on the philosophy of composability and reusability. It allows users to develop custom component flavors for each type of pipeline component. This guide will help you understand what a flavor is, and how you can develop and register your own custom flavor in ZenML.

## Understanding Component Flavors

In ZenML, a component type is a broad category that defines the functionality of a pipeline component. Each type can have multiple flavors, which are specific implementations of the component type. For instance, the type `orchestrator` can have flavors like `local`, `kubernetes`, etc. Each flavor is a unique implementation of the orchestrator functionality.

In order to create a custom component, one must create:

1. A custom flavor class (inheriting from `zenml.stack.Flavor` or any of its child classes)
2. An implementation class (inheriting from `zenml.stack.StackComponent` or any of its child classes)

## Writing a Custom Flavor Class

To develop a custom flavor, you need to create a class that inherits from the `BaseFlavor` class and implement the abstract properties. Here is a simplified version of the `BaseFlavor` class. Read the docstring of each function to understand its use:

```python
from abc import ABC, abstractmethod
from typing import Type

from zenml.enums import StackComponentType
from zenml.stack import StackComponent, StackComponentConfig, Flavor


class BaseFlavorConfig(StackComponentConfig):
    """Base class for all ZenML flavor configurations.
    
    This is a pydantic class, so pydantic supported items can be
    defined here.
    """

class BaseFlavor(Flavor, ABC):
    """Base class for all ZenML flavors."""

    @property
    def name(self) -> str:
        """The flavor name.

        Returns:
            The flavor name.
        """

    @property
    def docs_url(self) -> Optional[str]:
        """A url to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return None

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A url to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return None

    @property
    def logo_url(self) -> Optional[str]:
        """A url to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return None

    @property
    @abstractmethod
    def type(self) -> StackComponentType:
        """The stack component type.

        Returns:
            The stack component type.
        """

    # IMPORTANT: This point to the implementation class
    @property
    def implementation_class(self) -> Type[StackComponent]:
        """Implementation class for this flavor.

        Returns:
            The implementation class for this flavor.
        """

    @property
    def config_class(self) -> Type[StackComponentConfig]:
        """Returns `StackComponentConfig` config class.

        Returns:
            The config class.
        """
```

See the full code [here](https://github.com/zenml-io/zenml/blob/main/src/zenml/stack/flavor.py#L29).

## Writing the implementation class

While the flavor defines the properties of a component, it also points to a concrete implementation class (defined in the `implementation_class` method above).

When you register a flavor, ZenML tries to load this implementation class using `importlib`.

For each component type, the abstraction is slightly different (for example the [orchestrator](orchestrators/custom.md) is different from [data validators](data-validators/custom.md)). However, they all inherit from one base class with the following functions:

```python
class StackComponent:
    """Abstract StackComponent class for all components of a ZenML stack."""
  
    def get_connector(self) -> Optional["ServiceConnector"]:
      """Define a connector to handle authentication."""
      pass 

    @property
    def log_file(self) -> Optional[str]:
      """Optional path to a log file if this component produces logs."""
      pass 

    def prepare_pipeline_deployment(
        self,
        deployment: "PipelineDeploymentResponseModel",
        stack: "Stack",
    ) -> None:
        """Prepares deploying the pipeline.

        This method gets called immediately before a pipeline is deployed.
        Subclasses should override it if they require runtime configuration
        options or if they need to run code before the pipeline deployment.

        Args:
            deployment: The pipeline deployment configuration.
            stack: The stack on which the pipeline will be deployed.
        """

    def get_pipeline_run_metadata(
        self, run_id: UUID
    ) -> Dict[str, "MetadataType"]:
        """Get general component-specific metadata for a pipeline run.

        Args:
            run_id: The ID of the pipeline run.

        Returns:
            A dictionary of metadata.
        """
        return {}

    def prepare_step_run(self, info: "StepRunInfo") -> None:
        """Prepares running a step.

        Args:
            info: Info about the step that will be executed.
        """

    def get_step_run_metadata(
        self, info: "StepRunInfo"
    ) -> Dict[str, "MetadataType"]:
        """Get component- and step-specific metadata after a step ran.

        Args:
            info: Info about the step that was executed.

        Returns:
            A dictionary of metadata.
        """
        return {}

    def cleanup_step_run(self, info: "StepRunInfo", step_failed: bool) -> None:
        """Cleans up resources after the step run is finished.

        Args:
            info: Info about the step that was executed.
            step_failed: Whether the step failed.
        """
```

See the full code [here](https://github.com/zenml-io/zenml/blob/main/src/zenml/stack/stack_component.py).

{% hint style="info" %}

In ZenML, a flavor's `config` and `settings` are two separate, yet related entities. The `config` is the static part of your flavor's configuration, defined when you register your flavor. The `settings` are the dynamic part of your flavor's configuration, optionally defined when you register your flavor but can be overridden at runtime. You can read more about the differences [here](../../user-guide/advanced-guide/pipelining-features/configure-steps-pipelines.md).

{% endhint %}

As each component might define a different interface, please take a look at each component type to read further details on how to define a custom component of that type. For example, read the [step operator](step-operators/custom.md) guide to learn how to create a custom step operator.

## Registering a Flavor

Once you have implemented your custom flavor and implementation class, you can register your component using the ZenML CLI. Use the `flavor register` command and provide the path to your flavor class (see further below for a concrete example):

```shell
# This points to the flavor class, not the implementation class
zenml <component_type> flavor register <path.to.MyFlavor>
```

Replace `<component_type>` with the type of component you're developing the flavor for, and `<path.to.MyFlavor>` with the path to your flavor class.

For example, if your custom orchestrator flavor class `MyOrchestratorFlavor` is defined in `flavors/my_flavor.py`, you'd register it by doing:

```shell
zenml orchestrator flavor register flavors.my_flavor.MyOrchestratorFlavor
```

### Listing Flavors

You can list all registered flavors for a component type using the `flavor list` command:

```shell
zenml <component_type> flavor list
```

Replace `<component_type>` with the type of component you're interested in, e.g. `orchestrator`.

### Understanding Flavor Registration

When you register a flavor, ZenML imports the flavor class and stores its configuration in the ZenML repository. This allows ZenML to use your flavor when running pipelines, even if the dependencies required by the flavor are not installed in the current environment.

In ZenML, the config is defined in flavor class in the `def config_class(self) -> Type[StackComponentConfig]` method, while in the settings are defined in the implementation class in the `def settings_class(self) -> Type[StackComponentSettings]` function.

## Tips for Developing Flavors

* You can keep changing the `Config` and `Settings` of your flavor after registration. ZenML will pick up these "live" changes when running pipelines.

* Always test your flavor thoroughly before using it in production. Make sure it works as expected and handles errors gracefully.

* Keep your flavor code clean and well-documented. This will make it easier for others to use and contribute to your flavor.

* Follow best practices for the language and libraries you're using. This will help ensure your flavor is efficient, reliable, and easy to maintain.

Probably the best way to learn about developing flavors is to see the code for the [officially supported flavors of ZenML](https://github.com/zenml-io/zenml/tree/main/src/zenml/integrations).

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>