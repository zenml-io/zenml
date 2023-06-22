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
from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.config.step_run_info import StepRunInfo

logger = get_logger(__name__)

STEP_ENVIRONMENT_NAME = "step_environment"


class StepEnvironment(BaseEnvironmentComponent):
    """(Deprecated) Added information about a run inside a step function.

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
        do_something_with(env.pipeline_name, env.run_name, env.step_name)
    ```
    """

    NAME = STEP_ENVIRONMENT_NAME

    def __init__(
        self,
        step_run_info: "StepRunInfo",
        cache_enabled: bool,
    ):
        """Initialize the environment of the currently running step.

        Args:
            step_run_info: Info about the currently running step.
            cache_enabled: Whether caching is enabled for the current step run.
        """
        super().__init__()
        self._step_run_info = step_run_info
        self._cache_enabled = cache_enabled

    @property
    def pipeline_name(self) -> str:
        """The name of the currently running pipeline.

        Returns:
            The name of the currently running pipeline.
        """
        return self._step_run_info.pipeline.name

    @property
    def run_name(self) -> str:
        """The name of the current pipeline run.

        Returns:
            The name of the current pipeline run.
        """
        return self._step_run_info.run_name

    @property
    def step_name(self) -> str:
        """The name of the currently running step.

        Returns:
            The name of the currently running step.
        """
        return self._step_run_info.pipeline_step_name

    @property
    def step_run_info(self) -> "StepRunInfo":
        """Info about the currently running step.

        Returns:
            Info about the currently running step.
        """
        return self._step_run_info

    @property
    def cache_enabled(self) -> bool:
        """Returns whether cache is enabled for the step.

        Returns:
            True if cache is enabled for the step, otherwise False.
        """
        return self._cache_enabled
