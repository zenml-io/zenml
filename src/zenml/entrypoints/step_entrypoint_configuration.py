#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Base class for entrypoint configurations that run a single step."""

from typing import TYPE_CHECKING, Any, List, Set

from zenml.client import Client
from zenml.entrypoints.base_entrypoint_configuration import (
    BaseEntrypointConfiguration,
)
from zenml.integrations.registry import integration_registry
from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.config.step_configurations import Step
    from zenml.models import PipelineDeploymentResponse

logger = get_logger(__name__)

STEP_NAME_OPTION = "step_name"


class StepEntrypointConfiguration(BaseEntrypointConfiguration):
    """Base class for entrypoint configurations that run a single step.

    If an orchestrator needs to run steps in a separate process or environment
    (e.g. a docker container), this class can either be used directly or
    subclassed if custom behavior is necessary.

    How to subclass:
    ----------------
    Passing additional arguments to the entrypoint:
        If you need to pass additional arguments to the entrypoint, there are
        two methods that you need to implement:
            * `get_entrypoint_options()`: This method should return all
                the options that are required in the entrypoint. Make sure to
                include the result from the superclass method so the options
                are complete.

            * `get_entrypoint_arguments(...)`: This method should return
                a list of arguments that should be passed to the entrypoint.
                Make sure to include the result from the superclass method so
                the arguments are complete.

        You'll be able to access the argument values from `self.entrypoint_args`
        inside your `StepEntrypointConfiguration` subclass.

    How to use:
    -----------
    After you created your `StepEntrypointConfiguration` subclass, you only
    have to run the entrypoint somewhere. To do this, you should execute the
    command returned by the `get_entrypoint_command()` method with the
    arguments returned by the `get_entrypoint_arguments(...)` method.

    Example:
    ```python
    class MyStepEntrypointConfiguration(StepEntrypointConfiguration):
        ...

    class MyOrchestrator(BaseOrchestrator):
        def prepare_or_run_pipeline(
            self,
            deployment: "PipelineDeployment",
            stack: "Stack",
        ) -> Any:
            ...

            cmd = MyStepEntrypointConfiguration.get_entrypoint_command()
            for step_name, step in pipeline.steps.items():
                ...

                args = MyStepEntrypointConfiguration.get_entrypoint_arguments(
                    step_name=step_name
                )
                # Run the command and pass it the arguments. Our example
                # orchestrator here executes the entrypoint in a separate
                # process, but in a real-world scenario you would probably run
                # it inside a docker container or a different environment.
                import subprocess
                subprocess.check_call(cmd + args)
    ```
    """

    def post_run(
        self,
        pipeline_name: str,
        step_name: str,
    ) -> None:
        """Does cleanup or post-processing after the step finished running.

        Subclasses should overwrite this method if they need to run any
        additional code after the step execution.

        Args:
            pipeline_name: Name of the parent pipeline of the step that was
                executed.
            step_name: Name of the step that was executed.
        """

    @classmethod
    def get_entrypoint_options(cls) -> Set[str]:
        """Gets all options required for running with this configuration.

        Returns:
            The superclass options as well as an option for the name of the
            step to run.
        """
        return super().get_entrypoint_options() | {STEP_NAME_OPTION}

    @classmethod
    def get_entrypoint_arguments(
        cls,
        **kwargs: Any,
    ) -> List[str]:
        """Gets all arguments that the entrypoint command should be called with.

        The argument list should be something that
        `argparse.ArgumentParser.parse_args(...)` can handle (e.g.
        `["--some_option", "some_value"]` or `["--some_option=some_value"]`).
        It needs to provide values for all options returned by the
        `get_entrypoint_options()` method of this class.

        Args:
            **kwargs: Kwargs, must include the step name.

        Returns:
            The superclass arguments as well as arguments for the name of the
            step to run.
        """
        return super().get_entrypoint_arguments(**kwargs) + [
            f"--{STEP_NAME_OPTION}",
            kwargs[STEP_NAME_OPTION],
        ]

    def run(self) -> None:
        """Prepares the environment and runs the configured step."""
        deployment = self.load_deployment()

        # Activate all the integrations. This makes sure that all materializers
        # and stack component flavors are registered.
        integration_registry.activate_integrations()

        step_name = self.entrypoint_args[STEP_NAME_OPTION]

        self.download_code_if_necessary(
            deployment=deployment, step_name=step_name
        )

        pipeline_name = deployment.pipeline_configuration.name

        step = deployment.step_configurations[step_name]
        self._run_step(step, deployment=deployment)

        self.post_run(
            pipeline_name=pipeline_name,
            step_name=step_name,
        )

    def _run_step(
        self,
        step: "Step",
        deployment: "PipelineDeploymentResponse",
    ) -> None:
        """Runs a single step.

        Args:
            step: The step to run.
            deployment: The deployment configuration.
        """
        orchestrator = Client().active_stack.orchestrator
        orchestrator._prepare_run(deployment=deployment)
        orchestrator.run_step(step=step)
