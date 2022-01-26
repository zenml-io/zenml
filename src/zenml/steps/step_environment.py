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

from typing import Any

from zenml.utils.singleton import SingletonMetaClass


class StepEnvironment(metaclass=SingletonMetaClass):
    """Provides additional information about a step runtime inside a step
    function.

    This singleton can be used from within a pipeline step implementation to
    access additional information about the runtime parameters of a pipeline
    step inside a step function, such as the pipeline name, pipeine run ID
    and other pipeline runtime information. To use it, instantiate it and
    access it inside your step function, like this:

    ```python
    @step
    def my_step(...)
        env = StepEnvironment()
        do_something_with(env.pipeline_name, env.pipeline_run_id, env.step_name)
    ```
    """

    def __init__(
        self,
        pipeline_name: str,
        pipeline_run_id: str,
        step_name: str,
    ):
        """Initialize or retrieve the environment of the currently running
        step.

        NOTE: the StepEnvironment class is a singleton. A single
        StepEnvironment instance exists at any given time and should only
        be accessed from within a pipeline step function.

        Args:
            pipeline_name: the name of the currently running pipeline
            pipeline_run_id: the ID of the currently running pipeline
            step_name: the name of the currently running step
        """
        self._pipeline_name = pipeline_name
        self._pipeline_run_id = pipeline_run_id
        self._step_name = step_name

    def __enter__(self) -> "StepEnvironment":
        """Environment context manager entry point.

        Returns:
            The StepEnvironment instance.
        """
        return self

    def __exit__(self, *args: Any) -> None:
        """Environment context manager exit point."""
        # Delete the environment singleton instance on context exit
        StepEnvironment._clear()

    @property
    def pipeline_name(self) -> str:
        """The name of the currently running pipeline."""
        return self._pipeline_name

    @property
    def pipeline_run_id(self) -> str:
        """The ID of the current pipeline run."""
        return self._pipeline_run_id

    @property
    def step_name(self) -> str:
        """The name of the currently running step."""
        return self._step_name
