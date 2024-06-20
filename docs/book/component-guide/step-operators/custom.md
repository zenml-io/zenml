---
description: Learning how to develop a custom step operator.
---

# Develop a Custom Step Operator

{% hint style="info" %}
Before diving into the specifics of this component type, it is beneficial to familiarize yourself with our [general guide to writing custom component flavors in ZenML](../../how-to/stack-deployment/implement-a-custom-stack-component.md). This guide provides an essential understanding of ZenML's component flavor concepts.
{% endhint %}

### Base Abstraction

The `BaseStepOperator` is the abstract base class that needs to be subclassed in order to run specific steps of your pipeline in a separate environment. As step operators can come in many shapes and forms, the base class exposes a deliberately basic and generic interface:

```python
from abc import ABC, abstractmethod
from typing import List, Type

from zenml.enums import StackComponentType
from zenml.stack import StackComponent, StackComponentConfig, Flavor
from zenml.config.step_run_info import StepRunInfo


class BaseStepOperatorConfig(StackComponentConfig):
    """Base config for step operators."""


class BaseStepOperator(StackComponent, ABC):
    """Base class for all ZenML step operators."""

    @abstractmethod
    def launch(
            self,
            info: StepRunInfo,
            entrypoint_command: List[str],
    ) -> None:
        """Abstract method to execute a step.

        Subclasses must implement this method and launch a **synchronous**
        job that executes the `entrypoint_command`.

        Args:
            info: Information about the step run.
            entrypoint_command: Command that executes the step.
        """


class BaseStepOperatorFlavor(Flavor):
    """Base class for all ZenML step operator flavors."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Returns the name of the flavor."""

    @property
    def type(self) -> StackComponentType:
        """Returns the flavor type."""
        return StackComponentType.STEP_OPERATOR

    @property
    def config_class(self) -> Type[BaseStepOperatorConfig]:
        """Returns the config class for this flavor."""
        return BaseStepOperatorConfig

    @property
    @abstractmethod
    def implementation_class(self) -> Type[BaseStepOperator]:
        """Returns the implementation class for this flavor."""
```

{% hint style="info" %}
This is a slimmed-down version of the base implementation which aims to highlight the abstraction layer. In order to see the full implementation and get the complete docstrings, please check the [SDK docs](https://sdkdocs.zenml.io/latest/core\_code\_docs/core-step\_operators/#zenml.step\_operators.base\_step\_operator.BaseStepOperator) .
{% endhint %}

### Build your own custom step operator

If you want to create your own custom flavor for a step operator, you can follow the following steps:

1. Create a class that inherits from the `BaseStepOperator` class and implement the abstract `launch` method. This method has two main responsibilities:
   * Preparing a suitable execution environment (e.g. a Docker image): The general environment is highly dependent on the concrete step operator implementation, but for ZenML to be able to run the step it requires you to install some `pip` dependencies. The list of requirements needed to successfully execute the step can be found via the Docker settings `info.pipeline.docker_settings` passed to the `launch()` method. Additionally, you'll have to make sure that all the source code of your ZenML step and pipeline are available within this execution environment.
   * Running the entrypoint command: Actually running a single step of a pipeline requires knowledge of many ZenML internals and is implemented in the `zenml.step_operators.step_operator_entrypoint_configuration` module. As long as your environment was set up correctly (see the previous bullet point), you can run the step using the command provided via the `entrypoint_command` argument of the `launch()` method.
2. If your step operator allows the specification of per-step resources, make sure to handle the resources defined on the step (`info.config.resource_settings`) that was passed to the `launch()` method.
3. If you need to provide any configuration, create a class that inherits from the `BaseStepOperatorConfig` class adds your configuration parameters.
4. Bring both the implementation and the configuration together by inheriting from the `BaseStepOperatorFlavor` class. Make sure that you give a `name` to the flavor through its abstract property.

Once you are done with the implementation, you can register it through the CLI. Please ensure you **point to the flavor class via dot notation**:

```shell
zenml step-operator flavor register <path.to.MyStepOperatorFlavor>
```

For example, if your flavor class `MyStepOperatorFlavor` is defined in `flavors/my_flavor.py`, you'd register it by doing:

```shell
zenml step-operator flavor register flavors.my_flavor.MyStepOperatorFlavor
```

{% hint style="warning" %}
ZenML resolves the flavor class by taking the path where you initialized zenml (via `zenml init`) as the starting point of resolution. Therefore, please ensure you follow [the best practice](../../how-to/setting-up-a-project-repository/best-practices.md) of initializing zenml at the root of your repository.

If ZenML does not find an initialized ZenML repository in any parent directory, it will default to the current working directory, but usually, it's better to not have to rely on this mechanism and initialize zenml at the root.
{% endhint %}

Afterward, you should see the new flavor in the list of available flavors:

```shell
zenml step-operator flavor list
```

{% hint style="warning" %}
It is important to draw attention to when and how these base abstractions are coming into play in a ZenML workflow.

* The **CustomStepOperatorFlavor** class is imported and utilized upon the creation of the custom flavor through the CLI.
* The **CustomStepOperatorConfig** class is imported when someone tries to register/update a stack component with this custom flavor. Especially, during the registration process of the stack component, the config will be used to validate the values given by the user. As `Config` objects are inherently `pydantic` objects, you can also add your own custom validators here.
* The **CustomStepOperator** only comes into play when the component is ultimately in use.

The design behind this interaction lets us separate the configuration of the flavor from its implementation. This way we can register flavors and components even when the major dependencies behind their implementation are not installed in our local setting (assuming the `CustomStepOperatorFlavor` and the `CustomStepOperatorConfig` are implemented in a different module/path than the actual `CustomStepOperator`).
{% endhint %}

#### Enabling CUDA for GPU-backed hardware

Note that if you wish to use your custom step operator to run steps on a GPU, you will need to follow [the instructions on this page](../../how-to/training-with-gpus/training-with-gpus.md) to ensure that it works. It requires adding some extra settings customization and is essential to enable CUDA for the GPU to give its full acceleration.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
