---
description: Learning how to develop a custom orchestrator.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Develop a Custom Orchestrator

### Base Implementation

ZenML aims to enable orchestration with any orchestration tool. This is where the `BaseOrchestrator` comes into play. It
abstracts away many of the ZenML-specific details from the actual implementation and exposes a simplified interface:

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, Type

from zenml.models import PipelineDeploymentResponseModel
from zenml.enums import StackComponentType
from zenml.stack import StackComponent, StackComponentConfig, Stack, Flavor


class BaseOrchestratorConfig(StackComponentConfig):
    """Base class for all ZenML orchestrator configurations."""


class BaseOrchestrator(StackComponent, ABC):
    """Base class for all ZenML orchestrators"""

    @abstractmethod
    def prepare_or_run_pipeline(
        self,
        deployment: PipelineDeploymentResponseModel,
        stack: Stack,
        environment: Dict[str, str],
    ) -> Any:
        """Prepares and runs the pipeline outright or returns an intermediate
        pipeline representation that gets deployed.
        """


class BaseOrchestratorFlavor(Flavor):
    """Base orchestrator for all ZenML orchestrator flavors."""

    @property
    @abstractmethod
    def name(self):
        """Returns the name of the flavor."""

    @property
    def type(self) -> StackComponentType:
        """Returns the flavor type."""
        return StackComponentType.ORCHESTRATOR

    @property
    def config_class(self) -> Type[BaseOrchestratorConfig]:
        """Config class for the base orchestrator flavor."""
        return BaseOrchestratorConfig

    @property
    @abstractmethod
    def implementation_class(self) -> Type["BaseOrchestrator"]:
        """Implementation class for this flavor."""
```

{% hint style="info" %}
This is a slimmed-down version of the base implementation which aims to highlight the abstraction layer. In order to see
the full implementation and get the complete docstrings, please
check [the source code on GitHub](https://github.com/zenml-io/zenml/blob/main/src/zenml/orchestrators/base\_orchestrator.py)
.
{% endhint %}

### Build your own custom orchestrator

If you want to create your own custom flavor for an orchestrator, you can follow the following steps:

1. Create a class that inherits from the `BaseOrchestrator` class and implement the abstract `prepare_or_run_pipeline`
   method.
2. If you need to provide any configuration, create a class that inherits from the `BaseOrchestratorConfig` class and
   add your configuration parameters.
3. Bring both the implementation and the configuration together by inheriting from the `BaseOrchestratorFlavor` class.
   Make sure that you give a `name` to the flavor through its abstract property.

Once you are done with the implementation, you can register it through the CLI. Please ensure you **point to the flavor
class via dot notation**:

```shell
zenml orchestrator flavor register <path.to.MyOrchestratorFlavor>
```

For example, if your flavor class `MyOrchestratorFlavor` is defined in `flavors/my_flavor.py`, you'd register it by
doing:

```shell
zenml orchestrator flavor register flavors.my_flavor.MyOrchestratorFlavor
```

{% hint style="warning" %}
ZenML resolves the flavor class by taking the path where you initialized zenml (via `zenml init`) as the starting point
of resolution. Therefore, please ensure you follow 
[the best practice](/docs/book/user-guide/starter-guide/follow-best-practices.md) of initializing zenml at the
root of your repository.

If ZenML does not find an initialized ZenML repository in any parent directory, it will default to the current working
directory, but usually, it's better to not have to rely on this mechanism and initialize zenml at the root.
{% endhint %}

Afterward, you should see the new flavor in the list of available flavors:

```shell
zenml orchestrator flavor list
```

{% hint style="warning" %}
It is important to draw attention to when and how these base abstractions are coming into play in a ZenML workflow.

* The **CustomOrchestratorFlavor** class is imported and utilized upon the creation of the custom flavor through the
  CLI.
* The **CustomOrchestratorConfig** class is imported when someone tries to register/update a stack component with this
  custom flavor. Especially, during the registration process of the stack component, the config will be used to validate
  the values given by the user. As `Config` object are inherently `pydantic` objects, you can also add your own custom
  validators here.
* The **CustomOrchestrator** only comes into play when the component is ultimately in use.

The design behind this interaction lets us separate the configuration of the flavor from its implementation. This way we
can register flavors and components even when the major dependencies behind their implementation are not installed in
our local setting (assuming the `CustomOrchestratorFlavor` and the `CustomOrchestratorConfig` are implemented in a
different module/path than the actual `CustomOrchestrator`).
{% endhint %}

## Some additional implementation details

Not all orchestrators are created equal. Here are a few basic categories that differentiate them.

### Direct Orchestration

The implementation of a `local` orchestrator can be summarized as follows: code:

```python
for step in deployment.steps.values():
    self.run_step(step)
```

The orchestrator basically iterates through each step and directly executes the step within the same Python process.
Obviously, all kinds of additional configurations could be added around this.

### Container-based Orchestration

The `KubeflowOrchestrator` is a great example of container-based orchestration. In an implementation-specific method
called `prepare_pipeline_deployment(),` a Docker image containing the complete project context is built.

Within `prepare_or_run_pipeline()` a YAML file is created as an intermediate representation of the pipeline and uploaded
to the Kubeflow instance. To create this YAML file a callable is defined within which a `dsl.ContainerOp` is created for
each step. This `ContainerOp` contains the container entrypoint command and arguments that will make the image run just
one step. The ContainerOps are assembled according to their interdependencies inside a `dsl.Pipeline` which can then be
compiled into the YAMLfile.

Additionally, the `prepare_or_run_pipeline()` method receives a dictionary of environment variables that need to be set
in the environment in which the steps will be executed. Coming back to our example of the `KubeflowOrchestrator`, we set
these environment variables on the `dsl.ContainerOp` objects that we created earlier.

### Handling per-step resources

If your orchestrator allows specification of per-step resources, make sure to handle the configurations defined on each
step:

```python
def prepare_or_run_pipeline(...):
    for step in deployment.steps.values():
        if self.requires_resources_in_orchestration_environment(step):
            # make sure to handle the specified resources
            ...
```

### Base Implementation of the Step Entrypoint Configuration

Within the base Docker images that are used for container-based orchestration, the `src.zenml.entrypoints.entrypoint.py`
is the default entrypoint to run a specific step. It does so by loading an
orchestrator-specific `StepEntrypointConfiguration` object. This object is then used to parse all entrypoint arguments (
e.g. `--step_name <STEP_NAME>`). Finally, the `StepEntrypointConfiguration.run()` method is used to execute the step.
Under the hood, this will eventually also call the orchestrators `run_step()` method.

The `StepEntrypointConfiguration` is the base class that already implements most of the required functionality. Let's
dive right into it:

1. It defines some mandatory arguments for the step entrypoint. These are set as constants at the top of the file and
   used as the minimum required arguments.
2. The `run()` method uses the parsed arguments to set up all required prerequisites before ultimately executing the
   step.

Here is a schematic view of what the `StepEntrypointConfiguration` looks like:

```python
from typing import Optional, Set, Any, List

from zenml.entrypoints.base_entrypoint_configuration import (
    BaseEntrypointConfiguration,
)

STEP_NAME_OPTION = "step_name"


class StepEntrypointConfiguration(BaseEntrypointConfiguration):
    """Base class for entrypoint configurations that run a single step."""

    def post_run(
            self,
            pipeline_name: str,
            step_name: str,
    ) -> None:
        """Does cleanup or post-processing after the step finished running."""

    @classmethod
    def get_entrypoint_options(cls) -> Set[str]:
        """Gets all options required for running with this configuration."""
        return super().get_entrypoint_options() | {STEP_NAME_OPTION}

    @classmethod
    def get_entrypoint_arguments(
            cls,
            **kwargs: Any,
    ) -> List[str]:
        """Gets all arguments that the entrypoint command should be called with."""
        return super().get_entrypoint_arguments(**kwargs) + [
            f"--{STEP_NAME_OPTION}",
            kwargs[STEP_NAME_OPTION],
        ]

    def run(self) -> None:
        """Prepares the environment and runs the configured step."""
        ...
```

{% hint style="info" %}
This is a slimmed-down version of the base implementation which aims to highlight the abstraction layer. In order to see
the full implementation and get the complete docstrings, please
check [the source code on GitHub](https://github.com/zenml-io/zenml/blob/main/src/zenml/entrypoints/step\_entrypoint\_configuration.py)
.
{% endhint %}

### Build your own Step Entrypoint Configuration

If you need to customize what happens when a step gets executed inside the entrypoint, you can subclass from
the `StepEntrypointConfiguration` class:

If you need to pass additional arguments to the entrypoint, there are two methods that you need to implement:

* `get_entrypoint_options()`: This method should return all the additional options that you require in the entrypoint.
* `get_entrypoint_arguments(...)`: This method should return a list of arguments that should be passed to the
  entrypoint. The arguments need to provide values for all options defined in the `get_entrypoint_options()` method
  mentioned above.

#### Enabling CUDA for GPU-backed hardware

Note that if you wish to use your custom orchestrator to run steps on a GPU, you will need to
follow [the instructions on this page](/docs/book/user-guide/advanced-guide/scale-compute-to-the-cloud.md) to ensure 
that it works. It requires adding some extra settings customization and is essential to enable CUDA for the GPU to 
give its full acceleration.
