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

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from zenml.enums import ExecutionStatus
from zenml.post_execution.artifact import ArtifactView
from zenml.zen_stores.models.pipeline_models import StepWrapper

if TYPE_CHECKING:
    from zenml.metadata_stores import BaseMetadataStore


class StepView:
    """Post-execution step class which can be used to query
    artifact information associated with a pipeline step.
    """

    def __init__(
        self,
        id_: int,
        parents_step_ids: List[int],
        entrypoint_name: str,
        name: str,
        parameters: Dict[str, Any],
        metadata_store: "BaseMetadataStore",
    ):
        """Initializes a post-execution step object.

        In most cases `StepView` objects should not be created manually
        but retrieved from a `PipelineRunView` object instead.

        Args:
            id_: The execution id of this step.
            parents_step_ids: The execution ids of the parents of this step.
            entrypoint_name: The name of this step.
            name: The name of this step within the pipeline
            parameters: Parameters that were used to run this step.
            metadata_store: The metadata store which should be used to fetch
                additional information related to this step.
        """
        self._id = id_
        self._parents_step_ids = parents_step_ids
        self._entrypoint_name = entrypoint_name
        self._name = name
        self._parameters = parameters
        self._metadata_store = metadata_store

        self._inputs: Dict[str, ArtifactView] = {}
        self._outputs: Dict[str, ArtifactView] = {}

        # This might be set from the parent pipeline run view in case the run
        # is also tracked in the ZenStore
        self._step_wrapper: Optional[StepWrapper] = None

    @property
    def id(self) -> int:
        """Returns the step id."""
        return self._id

    @property
    def parents_step_ids(self) -> List[int]:
        """Returns a list of ID's of all parents of this step."""
        return self._parents_step_ids

    @property
    def parent_steps(self) -> List["StepView"]:
        """Returns a list of all parent steps of this step."""
        steps = [
            self._metadata_store.get_step_by_id(s)
            for s in self.parents_step_ids
        ]
        return steps

    @property
    def entrypoint_name(self) -> str:
        """Returns the step entrypoint_name.

        This name is equal to the name argument passed to the @step decorator
        or the actual function name if no explicit name was given.

        Examples:
            # the step entrypoint_name will be "my_step"
            @step(name="my_step")
            def my_step_function(...)

            # the step entrypoint_name will be "my_step_function"
            @step
            def my_step_function(...)
        """
        return self._entrypoint_name

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
        """
        return self._name

    @property
    def docstring(self) -> Optional[str]:
        """Docstring of the step function or class."""
        if self._step_wrapper:
            return self._step_wrapper.docstring
        return None

    @property
    def parameters(self) -> Dict[str, Any]:
        """The parameters used to run this step."""
        return self._parameters

    @property
    def status(self) -> ExecutionStatus:
        """Returns the current status of the step."""
        return self._metadata_store.get_step_status(self)

    @property
    def is_cached(self) -> bool:
        """Returns whether the step is cached or not."""
        return self.status == ExecutionStatus.CACHED

    @property
    def is_completed(self) -> bool:
        """Returns whether the step is cached or not."""
        return self.status == ExecutionStatus.COMPLETED

    @property
    def inputs(self) -> Dict[str, ArtifactView]:
        """Returns all input artifacts that were used to run this step."""
        self._ensure_inputs_outputs_fetched()
        return self._inputs

    @property
    def input(self) -> ArtifactView:
        """Returns the input artifact that was used to run this step.

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
        """Returns all output artifacts that were written by this step."""
        self._ensure_inputs_outputs_fetched()
        return self._outputs

    @property
    def output(self) -> ArtifactView:
        """Returns the output artifact that was written by this step.

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

        self._inputs, self._outputs = self._metadata_store.get_step_artifacts(
            self
        )

    def __repr__(self) -> str:
        """Returns a string representation of this step."""
        return (
            f"{self.__class__.__qualname__}(id={self._id}, "
            f"name='{self.name}', entrypoint_name='{self.entrypoint_name}'"
            f"parameters={self._parameters})"
        )

    def __eq__(self, other: Any) -> bool:
        """Returns whether the other object is referring to the same step."""
        if isinstance(other, StepView):
            return (
                self._id == other._id
                and self._metadata_store.uuid == other._metadata_store.uuid
            )
        return NotImplemented
