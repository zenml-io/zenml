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
"""Step environment class."""

from typing import TYPE_CHECKING

from zenml.environment import BaseEnvironmentComponent
from zenml.runtime_configuration import RuntimeConfiguration

STEP_ENVIRONMENT_NAME = "step_environment"
if TYPE_CHECKING:
    from zenml.config.docker_configuration import DockerConfiguration


class StepEnvironment(BaseEnvironmentComponent):
    """Added information about a step runtime inside a step function.

    This takes the form of an Environment component. This class can be used from
    within a pipeline step implementation to access additional information about
    the runtime parameters of a pipeline step, such as the pipeline name,
    pipeline run ID and other pipeline runtime information. To use it, access it
    inside your step function like this:

    ```python
    from zenml.environment import Environment

    @step
    def my_step(...)
        env = Environment().step_environment
        do_something_with(env.pipeline_name, env.pipeline_run_id, env.step_name)
    ```
    """

    NAME = STEP_ENVIRONMENT_NAME

    def __init__(
        self,
        pipeline_name: str,
        pipeline_run_id: str,
        step_name: str,
        cache_enabled: bool,
        docker_configuration: "DockerConfiguration",
        runtime_configuration: "RuntimeConfiguration",
    ):
        """Initialize the environment of the currently running step.

        Args:
            pipeline_name: the name of the currently running pipeline
            pipeline_run_id: the ID of the currently running pipeline
            step_name: the name of the currently running step
            cache_enabled: whether cache is enabled for this step
            docker_configuration: The Docker configuration of the currently
                running pipeline.
            runtime_configuration: The runtime configuration of the currently
                running pipeline.
        """
        super().__init__()
        self._pipeline_name = pipeline_name
        self._pipeline_run_id = pipeline_run_id
        self._step_name = step_name
        self._cache_enabled = cache_enabled
        self._docker_configuration = docker_configuration
        self._runtime_configuration = runtime_configuration

    @property
    def pipeline_name(self) -> str:
        """The name of the currently running pipeline.

        Returns:
            The name of the currently running pipeline.
        """
        return self._pipeline_name

    @property
    def pipeline_run_id(self) -> str:
        """The ID of the current pipeline run.

        Returns:
            The ID of the current pipeline run.
        """
        return self._pipeline_run_id

    @property
    def step_name(self) -> str:
        """The name of the currently running step.

        Returns:
            The name of the currently running step.
        """
        return self._step_name

    @property
    def cache_enabled(self) -> bool:
        """Returns whether cache is enabled for the step.

        Returns:
            True if cache is enabled for the step, otherwise False.
        """
        return self._cache_enabled

    @property
    def docker_configuration(self) -> "DockerConfiguration":
        """The Docker configuration of the currently running pipeline.

        Returns:
            A Docker configuration object.
        """
        return self._docker_configuration

    @property
    def runtime_configuration(self) -> "RuntimeConfiguration":
        """The Runtime configuration of the currently running pipeline.

        Returns:
            A Runtime configuration object.
        """
        return self._runtime_configuration
