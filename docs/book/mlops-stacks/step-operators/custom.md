---
description: How to develop a custom step operator
---

## Base Abstraction

The `BaseStepOperator` is the abstract base class that needs to be subclassed 
in order to run specific steps of your pipeline in a separate environment. As 
step operators can come in many shapes and forms, the base class exposes a 
deliberately basic and generic interface:

1. As it is the base class for a specific type of `StackComponent`,
   it inherits from the `StackComponent` class. This sets the `TYPE`
   variable to the specific `StackComponentType`.
2. The `FLAVOR` class variable needs to be set in subclasses as it
   is meant to identify the implementation flavor of the particular
   step operator.
3. Lastly, the base class features one `abstractmethod` called `launch()`. In 
   the implementation of every step operator flavor, the `launch()` method is 
   responsible for preparing the environment and executing the step.

```python
from abc import ABC, abstractmethod
from typing import List

from zenml.stack import StackComponent
from zenml.config.step_run_info import StepRunInfo

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
```

{% hint style="info" %}
This is a slimmed-down version of the base implementation which aims to 
highlight the abstraction layer. In order to see the full implementation 
and get the complete docstrings, please check the [API docs](https://apidocs.zenml.io/latest/api_docs/step_operators/#zenml.step_operators.base_step_operator.BaseStepOperator).
{% endhint %}

## Building your own custom step operator

If you want to create a custom step operator, you can follow these steps:

1. Create a class which inherits from the `BaseStepOperator`.
2. Define the `FLAVOR` class variable.
3. Implement the abstract `launch()` method. This method has two main 
   responsibilities:
      * Preparing a suitable execution environment (e.g. a Docker image): The 
   general environment is highly dependent on the concrete step operator 
   implementation, but for ZenML to be able to run the step it requires you to 
   install some `pip` dependencies. The list of requirements needed to 
   successfully execute the step can be found via the Docker settings
   `info.pipeline.docker_settings` passed to the `launch()` method.
   Additionally, you'll have to make sure that all the 
   source code of your ZenML step and pipeline are available within this 
   execution environment.
      * Running the entrypoint command: Actually running a single step of a 
   pipeline requires knowledge of many ZenML internals and is implemented in 
   the `zenml.step_operators.step_operator_entrypoint_configuration` module.
   As long as your environment  was set up correctly (see the previous bullet point),
   you can run the step using the command provided via the `entrypoint_command`
   argument of the `launch()` method.
4. If your step operator allows specification of per-step resources, make sure
   to handle the resources defined on the step (`info.config.resource_settings`) that
   was passed to the `launch()` method.

Once you are done with the implementation, you can register it through the CLI 
as:

```shell
zenml step-operator flavor register <SOURCE-PATH-OF-YOUR-STEP-OPERATOR-CLASS>
```
