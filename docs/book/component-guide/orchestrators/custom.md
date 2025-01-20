---
description: Learning how to develop a custom orchestrator.
---

# Develop a custom orchestrator

{% hint style="info" %}
Before diving into the specifics of this component type, it is beneficial to familiarize yourself with our [general guide to writing custom component flavors in ZenML](../../how-to/infrastructure-deployment/stack-deployment/implement-a-custom-stack-component.md). This guide provides an essential understanding of ZenML's component flavor concepts.
{% endhint %}

### Base Implementation

ZenML aims to enable orchestration with any orchestration tool. This is where the `BaseOrchestrator` comes into play. It abstracts away many of the ZenML-specific details from the actual implementation and exposes a simplified interface:

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

    @abstractmethod
    def get_orchestrator_run_id(self) -> str:
        """Returns the run id of the active orchestrator run.

        Important: This needs to be a unique ID and return the same value for
        all steps of a pipeline run.

        Returns:
            The orchestrator run id.
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
This is a slimmed-down version of the base implementation which aims to highlight the abstraction layer. In order to see the full implementation and get the complete docstrings, please check [the source code on GitHub](https://github.com/zenml-io/zenml/blob/main/src/zenml/orchestrators/base\_orchestrator.py) .
{% endhint %}

### Build your own custom orchestrator

If you want to create your own custom flavor for an orchestrator, you can follow the following steps:

1. Create a class that inherits from the `BaseOrchestrator` class and implement the abstract `prepare_or_run_pipeline(...)` and `get_orchestrator_run_id()` methods.
2. If you need to provide any configuration, create a class that inherits from the `BaseOrchestratorConfig` class and add your configuration parameters.
3. Bring both the implementation and the configuration together by inheriting from the `BaseOrchestratorFlavor` class. Make sure that you give a `name` to the flavor through its abstract property.

Once you are done with the implementation, you can register it through the CLI. Please ensure you **point to the flavor class via dot notation**:

```shell
zenml orchestrator flavor register <path.to.MyOrchestratorFlavor>
```

For example, if your flavor class `MyOrchestratorFlavor` is defined in `flavors/my_flavor.py`, you'd register it by doing:

```shell
zenml orchestrator flavor register flavors.my_flavor.MyOrchestratorFlavor
```

{% hint style="warning" %}
ZenML resolves the flavor class by taking the path where you initialized zenml (via `zenml init`) as the starting point of resolution. Therefore, please ensure you follow [the best practice](../../how-to/setting-up-a-project-repository/best-practices.md) of initializing zenml at the root of your repository.

If ZenML does not find an initialized ZenML repository in any parent directory, it will default to the current working directory, but usually, it's better to not have to rely on this mechanism and initialize zenml at the root.
{% endhint %}

Afterward, you should see the new flavor in the list of available flavors:

```shell
zenml orchestrator flavor list
```

{% hint style="warning" %}
It is important to draw attention to when and how these base abstractions are coming into play in a ZenML workflow.

* The **CustomOrchestratorFlavor** class is imported and utilized upon the creation of the custom flavor through the CLI.
* The **CustomOrchestratorConfig** class is imported when someone tries to register/update a stack component with this custom flavor. Especially, during the registration process of the stack component, the config will be used to validate the values given by the user. As `Config` object are inherently `pydantic` objects, you can also add your own custom validators here.
* The **CustomOrchestrator** only comes into play when the component is ultimately in use.

The design behind this interaction lets us separate the configuration of the flavor from its implementation. This way we can register flavors and components even when the major dependencies behind their implementation are not installed in our local setting (assuming the `CustomOrchestratorFlavor` and the `CustomOrchestratorConfig` are implemented in a different module/path than the actual `CustomOrchestrator`).
{% endhint %}

## Implementation guide

1. **Create your orchestrator class:** This class should either inherit from `BaseOrchestrator`, or more commonly from `ContainerizedOrchestrator`. If your orchestrator uses container images to run code, you should inherit from `ContainerizedOrchestrator` which handles building all Docker images for the pipeline to be executed. If your orchestator does not use container images, you'll be responsible that the execution environment contains all the necessary requirements and code files to run the pipeline.
2.  **Implement the `prepare_or_run_pipeline(...)` method:** This method is responsible for running or scheduling the pipeline. In most cases, this means converting the pipeline into a format that your orchestration tool understands and running it. To do so, you should:

    * Loop over all steps of the pipeline and configure your orchestration tool to run the correct command and arguments in the correct Docker image
    * Make sure the passed environment variables are set when the container is run
    * Make sure the containers are running in the correct order

    Check out the [code sample](custom.md#code-sample) below for more details on how to fetch the Docker image, command, arguments and step order.
3. **Implement the `get_orchestrator_run_id()` method:** This must return a ID that is different for each pipeline run, but identical if called from within Docker containers running different steps of the same pipeline run. If your orchestrator is based on an external tool like Kubeflow or Airflow, it is usually best to use an unique ID provided by this tool.

{% hint style="info" %}
To see a full end-to-end worked example of a custom orchestrator, [see here](https://github.com/zenml-io/zenml-plugins/tree/main/how\_to\_custom\_orchestrator).
{% endhint %}

### Optional features

There are some additional optional features that your orchestrator can implement:

* **Running pipelines on a schedule**: if your orchestrator supports running pipelines on a schedule, make sure to handle `deployment.schedule` if it exists. If your orchestrator does not support schedules, you should either log a warning and or even raise an exception in case the user tries to schedule a pipeline.
* **Specifying hardware resources**: If your orchestrator supports setting resources like CPUs, GPUs or memory for the pipeline or specific steps, make sure to handle the values defined in `step.config.resource_settings`. See the code sample below for additional helper methods to check whether any resources are required from your orchestrator.

### Code sample

```python
from typing import Dict

from zenml.entrypoints import StepEntrypointConfiguration
from zenml.models import PipelineDeploymentResponseModel
from zenml.orchestrators import ContainerizedOrchestrator
from zenml.stack import Stack


class MyOrchestrator(ContainerizedOrchestrator):

    def get_orchestrator_run_id(self) -> str:
        # Return an ID that is different each time a pipeline is run, but the
        # same for all steps being executed as part of the same pipeline run.
        # If you're using some external orchestration tool like Kubeflow, you
        # can usually use the run ID of that tool here.
        ...

    def prepare_or_run_pipeline(
        self,
        deployment: "PipelineDeploymentResponseModel",
        stack: "Stack",
        environment: Dict[str, str],
    ) -> None:
        # If your orchestrator supports scheduling, you should handle the schedule
        # configured by the user. Otherwise you might raise an exception or log a warning
        # that the orchestrator doesn't support scheduling
        if deployment.schedule:
            ...

        for step_name, step in deployment.step_configurations.items():
            image = self.get_image(deployment=deployment, step_name=step_name)
            command = StepEntrypointConfiguration.get_entrypoint_command()
            arguments = StepEntrypointConfiguration.get_entrypoint_arguments(
                step_name=step_name, deployment_id=deployment.id
            )
            # Your orchestration tool should run this command and arguments
            # in the Docker image fetched above. Additionally, the container which
            # is running the command must contain the environment variables specified
            # in the `environment` dictionary.
            
            # If your orchestrator supports parallel execution of steps, make sure
            # each step only runs after all its upstream steps finished
            upstream_steps = step.spec.upstream_steps

            # You can get the settings your orchestrator like so.
            # The settings are the "dynamic" part of your orchestrators config,
            # optionally defined when you register your orchestrator but can be
            # overridden at runtime.
            # In contrast, the "static" part of your orchestrators config is
            # always defined when you register the orchestrator and can be
            # accessed via `self.config`.
            step_settings = cast(
                MyOrchestratorSettings, self.get_settings(step)
            )

            # If your orchestrator supports setting resources like CPUs, GPUs or
            # memory for the pipeline or specific steps, you can find out whether
            # specific resources were specified for this step:
            if self.requires_resources_in_orchestration_environment(step):
                resources = step.config.resource_settings
```

{% hint style="info" %}
To see a full end-to-end worked example of a custom orchestrator, [see here](https://github.com/zenml-io/zenml-plugins/tree/main/how\_to\_custom\_orchestrator).
{% endhint %}

### Enabling CUDA for GPU-backed hardware

Note that if you wish to use your custom orchestrator to run steps on a GPU, you will need to follow [the instructions on this page](../../how-to/pipeline-development/training-with-gpus/README.md) to ensure that it works. It requires adding some extra settings customization and is essential to enable CUDA for the GPU to give its full acceleration.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
