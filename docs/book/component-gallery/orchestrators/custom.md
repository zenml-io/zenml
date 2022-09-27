---
description: How to develop a custom orchestrator
---

## Base Implementation

ZenML aims to enable orchestration with any orchestration tool. This is where
the `BaseOrchestrator` comes into play. It abstracts away many of the ZenML 
specific details from the actual implementation and exposes a simplified 
interface:

1. As it is the base class for a specific type of `StackComponent`,
   it inherits from the `StackComponent` class. This sets the `TYPE`
   variable to the specific `StackComponentType`.
2. The `FLAVOR` class variable needs to be set in the particular sub-class as it
   is meant to identify the implementation flavor of the particular
   orchestrator.
3. Lastly, the base class features one `abstractmethod`:
   `prepare_or_run_pipeline`. In the implementation of every
   `Orchestrator` flavor, it is required to define this method with respect
   to the flavor at hand.

Putting all these considerations together, we end up with the following
(simplified) implementation:

```python
from abc import ABC, abstractmethod
from typing import Any
from zenml.config.pipeline_deployment import PipelineDeployment

from zenml.stack import StackComponent, Stack


class BaseOrchestrator(StackComponent, ABC):
    """Base class for all ZenML orchestrators"""

    @abstractmethod
    def prepare_or_run_pipeline(
        self,
        deployment: PipelineDeployment,
        stack: Stack,
    ) -> Any:
        """Prepares and runs the pipeline outright or returns an intermediate
        pipeline representation that gets deployed.
        """
```

{% hint style="info" %}
This is a slimmed-down version of the base implementation which aims to 
highlight the abstraction layer. In order to see the full implementation 
and get the complete docstrings, please check [the source code on GitHub](https://github.com/zenml-io/zenml/blob/main/src/zenml/orchestrators/base_orchestrator.py).
{% endhint %}

## Build your own custom orchestrator

If you want to create your own custom flavor for an artifact store, you can
follow the following steps:

1. Create a class which inherits from the `BaseOrchestrator`.
2. Define the `FLAVOR` class variable.
3. Implement the `prepare_or_run_pipeline()` based on your desired orchestrator.

Once you are done with the implementation, you can register it through the CLI
as:

```shell
zenml orchestrator flavor register <THE-SOURCE-PATH-OF-YOUR-ORCHESTRATOR>
```

# Some additional implementation details

Not all orchestrators are created equal. Here is a few basic categories that
differentiate them.

## Direct Orchestration

The implementation of a `local` orchestrator can be summarized as follows:
code:

```python
for step in deployment.steps.values():
    self.run_step(step)
```

The orchestrator basically iterates through each step and directly executes
the step within the same Python process. Obviously all kind of additional
configuration could be added around this.

## Python Operator based Orchestration

The `airflow` orchestrator has a slightly more complex implementation of the
`prepare_or_run_pipeline()` method. Instead of immediately
executing a step, a `PythonOperator` is created which contains a
`_step_callable`. This `_step_callable` will ultimately execute the
`self.run_step(...)` method of the orchestrator. The PythonOperators are
assembled into an AirflowDag which is returned. Through some Airflow magic,
this DAG is loaded by the connected instance of Airflow and orchestration of
this DAG is performed either directly or on a set schedule.

## Container-based Orchestration

The `kubeflow` orchestrator is a great example of container-based orchestration.
In an implementation-specific method called `prepare_pipeline_deployment()`
a Docker image containing the complete project context is built.

Within `prepare_or_run_pipeline()` a yaml file is created as an intermediate
representation of the pipeline and uploaded to the Kubeflow instance.
To create this yaml file a callable is defined within which a `dsl.ContainerOp`
is created for each step. This ContainerOp contains the container entrypoint
command and arguments that will make the image run just the one step.
The ContainerOps are assembled according to their interdependencies inside a
`dsl.Pipeline` which can then be compiled into the yaml file.

## Handling per-step resources

If your orchestrator allows specification of per-step resources, make sure
to handle the configurations defined on each step:

```python
def prepare_or_run_pipeline(...):
    for step in deployment.steps.values():
        if self.requires_resources_in_orchestration_environment(step):
            # make sure to handle the specified resources
            ...
```

## Base Implementation of the Step Entrypoint Configuration

Within the base Docker images that are used for container-based orchestration
the `src.zenml.entrypoints.entrypoint.py` is the default entrypoint to run
a specific step. It does so by loading an orchestrator specific
`StepEntrypointConfiguration` object. This object is then used to parse all
entrypoint arguments (e.g. `--step_name <STEP_NAME>`). Finally, the
`StepEntrypointConfiguration.run()` method is used to execute the step.
Under the hood this will eventually also call the orchestrators `run_step()`
method.

The `StepEntrypointConfiguration` is the base class that already implements
most of the required functionality. Let's dive right into it:

1. It defines some mandatory arguments for the step entrypoint. These are set as
   constants at the top of the file and used as the minimum required arguments.
3. The `run()` method uses the parsed arguments to set up all required
   prerequisites before ultimately executing the step.

Here is a schematic view of what the `StepEntrypointConfiguration` looks like:

```python
from tfx.orchestration.portable import data_types

from zenml.entrypoints import utils as entrypoint_utils
from zenml.entrypoints.base_entrypoint_configuration import (
    BaseEntrypointConfiguration,
)
from zenml.integrations.registry import integration_registry
from zenml.repository import Repository

if TYPE_CHECKING:
    from zenml.config.pipeline_deployment import PipelineDeployment
    from zenml.config.step_configurations import Step

STEP_NAME_OPTION = "step_name"


class StepEntrypointConfiguration(BaseEntrypointConfiguration):
    """Base class for entrypoint configurations that run a single step."""

    def post_run(
        self,
        pipeline_name: str,
        step_name: str,
        execution_info: Optional[data_types.ExecutionInfo] = None,
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
This is a slimmed-down version of the base implementation which aims to 
highlight the abstraction layer. In order to see the full implementation 
and get the complete docstrings, please check the [the source code on GitHub](https://github.com/zenml-io/zenml/blob/main/src/zenml/entrypoints/step_entrypoint_configuration.py).
{% endhint %}

## Build your own Step Entrypoint Configuration

If you need to customize what happens when a step gets executed inside the entrypoint,
you can subclass the `StepEntrypointConfiguration` class:

If you want to provide a custom run name (this **has** to be the same for all steps that are
executed as part of the same pipeline run), you can overwrite the `get_run_name(...)` method.

If you need to pass additional arguments to the entrypoint, there are
two methods that you need to implement:

* `get_entrypoint_options()`: This method should return all the
  additional options that you require in the entrypoint.

* `get_entrypoint_arguments(...)`: This method should return a list of
  arguments that should be passed to the entrypoint. The arguments need to
  provide
  values for all options defined in the `get_entrypoint_options()` method
  mentioned above.
