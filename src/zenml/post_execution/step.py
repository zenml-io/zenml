#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""Implementation of a post-execution step class."""

from typing import Any, Dict, List, Optional, cast
from uuid import UUID

from zenml.client import Client
from zenml.enums import ExecutionStatus
from zenml.models import StepRunModel
from zenml.post_execution.artifact import ArtifactView


class StepView:
    """Post-execution step class.

    This can be used to query artifact information associated with a pipeline step.
    """

    def __init__(self, model: StepRunModel):
        """Initializes a post-execution step object.

        In most cases `StepView` objects should not be created manually
        but retrieved from a `PipelineRunView` object instead.

        Args:
            model: The model to initialize this object from.
        """
        self._model = model
        self._inputs: Dict[str, ArtifactView] = {}
        self._outputs: Dict[str, ArtifactView] = {}

    @property
    def id(self) -> UUID:
        """Returns the step id.

        Returns:
            The step id.
        """
        assert self._model.id
        return self._model.id

    @property
    def parent_step_ids(self) -> List[UUID]:
        """Returns a list of IDs of all parents of this step.

        Returns:
            A list of IDs of all parents of this step.
        """
        assert self._model.parent_step_ids
        return self._model.parent_step_ids

    @property
    def entrypoint_name(self) -> str:
        """Returns the step entrypoint_name.

        This name is equal to the name argument passed to the @step decorator
        or the actual function name if no explicit name was given.

        Examples:
            # the step entrypoint_name will be "my_step"
            @step(step="my_step")
            def my_step_function(...)

            # the step entrypoint_name will be "my_step_function"
            @step
            def my_step_function(...)

        Returns:
            The step entrypoint_name.
        """
        return self._model.entrypoint_name

    @property
    def name(self) -> str:
        """Returns the name as it is defined in the pipeline.

        This name is equal to the name given to the step within the pipeline
        context

        Examples:
            @step()
            def my_step_function(...)

            @pipeline
            def my_pipeline_function(step_a)

            p = my_pipeline_function(
                    step_a = my_step_function()
                )

            The name will be `step_a`

        Returns:
            The name of this step.
        """
        return self._model.name

    @property
    def docstring(self) -> Optional[str]:
        """Docstring of the step function or class.

        Returns:
            The docstring of the step function or class.
        """
        return self._model.docstring

    @property
    def parameters(self) -> Dict[str, str]:
        """The parameters used to run this step.

        Returns:
            The parameters used to run this step.
        """
        return self._model.parameters

    @property
    def step_configuration(self) -> Dict[str, Any]:
        """Returns the step configuration.

        Returns:
            The step configuration.
        """
        return self._model.step_configuration

    @property
    def settings(self) -> Dict[str, Any]:
        """Returns the step settings.

        These are runtime settings passed down to stack components, which
        can be set at step level.

        Returns:
            The step settings.
        """
        settings = self.step_configuration["config"]["settings"]
        return cast(Dict[str, Any], settings)

    @property
    def extra(self) -> Dict[str, Any]:
        """Returns the extra dictionary.

        This dict is meant to be used to pass any configuration down to the
        step that the user has use of.

        Returns:
            The extra dictionary.
        """
        extra = self.step_configuration["config"]["extra"]
        return cast(Dict[str, Any], extra)

    @property
    def enable_cache(self) -> bool:
        """Returns whether caching is enabled for this step.

        Returns:
            Whether caching is enabled for this step.
        """
        enable_cache = self.step_configuration["config"]["enable_cache"]
        return cast(bool, enable_cache)

    @property
    def step_operator(self) -> Optional[str]:
        """Returns the name of the step operator of the step.

        Returns:
            The name of the step operator of the step.
        """
        step_operator = self.step_configuration["config"]["step_operator"]
        return cast(Optional[str], step_operator)

    @property
    def experiment_tracker(self) -> Optional[str]:
        """Returns the name of the experiment tracker of the step.

        Returns:
            The name of the experiment tracker of the step.
        """
        experiment_tracker = self.step_configuration["config"][
            "experiment_tracker"
        ]
        return cast(Optional[str], experiment_tracker)

    @property
    def spec(self) -> Dict[str, Any]:
        """Returns the step spec.

        The step spec defines the source path and upstream steps of a step and
        is used primarily to compare whether two steps are the same.

        Returns:
            The step spec.
        """
        spec = self.step_configuration["spec"]
        return cast(Dict[str, Any], spec)

    @property
    def status(self) -> ExecutionStatus:
        """Returns the current status of the step.

        Returns:
            The current status of the step.
        """
        return Client().zen_store.get_run_step_status(self.id)

    @property
    def is_cached(self) -> bool:
        """Returns whether the step is cached or not.

        Returns:
            True if the step is cached, False otherwise.
        """
        return self.status == ExecutionStatus.CACHED

    @property
    def is_completed(self) -> bool:
        """Returns whether the step is cached or not.

        Returns:
            True if the step is completed, False otherwise.
        """
        return self.status == ExecutionStatus.COMPLETED

    @property
    def inputs(self) -> Dict[str, ArtifactView]:
        """Returns all input artifacts that were used to run this step.

        Returns:
            A dictionary of artifact names to artifact views.
        """
        self._ensure_inputs_fetched()
        return self._inputs

    @property
    def input(self) -> ArtifactView:
        """Returns the input artifact that was used to run this step.

        Returns:
            The input artifact.

        Raises:
            ValueError: If there were zero or multiple inputs to this step.
        """
        if len(self.inputs) != 1:
            raise ValueError(
                "Can't use the `StepView.input` property for steps with zero "
                "or multiple inputs, use `StepView.inputs` instead."
            )
        return next(iter(self.inputs.values()))

    @property
    def outputs(self) -> Dict[str, ArtifactView]:
        """Returns all output artifacts that were written by this step.

        Returns:
            A dictionary of artifact names to artifact views.
        """
        self._ensure_outputs_fetched()
        return self._outputs

    @property
    def output(self) -> ArtifactView:
        """Returns the output artifact that was written by this step.

        Returns:
            The output artifact.

        Raises:
            ValueError: If there were zero or multiple step outputs.
        """
        if len(self.outputs) != 1:
            raise ValueError(
                "Can't use the `StepView.output` property for steps with zero "
                "or multiple outputs, use `StepView.outputs` instead."
            )
        return next(iter(self.outputs.values()))

    def _ensure_inputs_fetched(self) -> None:
        """Fetches all step inputs from the ZenStore."""
        if self._inputs:
            # we already fetched inputs, no need to do anything
            return

        inputs = Client().zen_store.get_run_step_inputs(self.id)
        self._inputs = {
            input_name: ArtifactView(input)
            for input_name, input in inputs.items()
        }

    def _ensure_outputs_fetched(self) -> None:
        """Fetches all step outputs from the ZenStore."""
        if self._outputs:
            # we already fetched outputs, no need to do anything
            return

        outputs = Client().zen_store.get_run_step_outputs(self.id)
        self._outputs = {
            output_name: ArtifactView(output)
            for output_name, output in outputs.items()
        }

    def __repr__(self) -> str:
        """Returns a string representation of this step.

        Returns:
            A string representation of this step.
        """
        return (
            f"{self.__class__.__qualname__}(id={self.id}, "
            f"name='{self.name}', entrypoint_name='{self.entrypoint_name}'"
        )

    def __eq__(self, other: Any) -> bool:
        """Returns whether the other object is referring to the same step.

        Args:
            other: The other object to compare to.

        Returns:
            True if the other object is referring to the same step, False
            otherwise.
        """
        if isinstance(other, StepView):
            return self.id == other.id
        return NotImplemented
