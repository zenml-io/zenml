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

from typing import Any, Dict, List, Optional

from zenml.enums import ExecutionStatus
from zenml.models import StepRunModel
from zenml.post_execution.artifact import ArtifactView
from zenml.repository import Repository


class StepView:
    """Post-execution step class.

    This can be used to query artifact information associated with a pipeline step.
    """

    def __init__(self, model: StepRunModel):
        """Initializes a post-execution step object.

        In most cases `StepView` objects should not be created manually
        but retrieved from a `PipelineRunView` object instead.

        Args:
            id_: The execution id of this step.
            parents_step_ids: The execution ids of the parents of this step.
            entrypoint_name: The name of this step.
            name: The name of this step within the pipeline
        """
        self._model = model
        self._inputs: Dict[str, ArtifactView] = {}
        self._outputs: Dict[str, ArtifactView] = {}

    @property
    def id(self) -> int:
        """Returns the step id.

        Returns:
            The step id.
        """
        return self._model.mlmd_id

    @property
    def parent_step_ids(self) -> List[int]:
        """Returns a list of IDs of all parents of this step.

        Returns:
            A list of IDs of all parents of this step.
        """
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
    def status(self) -> ExecutionStatus:
        """Returns the current status of the step.

        Returns:
            The current status of the step.
        """
        return Repository().zen_store.get_run_step_status(self.id)

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
        self._ensure_inputs_outputs_fetched()
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
        self._ensure_inputs_outputs_fetched()
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

    def _ensure_inputs_outputs_fetched(self) -> None:
        """Fetches all step inputs and outputs from the metadata store."""
        if self._inputs or self._outputs:
            # we already fetched inputs/outputs, no need to do anything
            return

        repo = Repository()
        inputs, outputs = repo.zen_store.get_run_step_artifacts(self._model)
        self._inputs = {
            input_name: ArtifactView(input)
            for input_name, input in inputs.items()
        }
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
