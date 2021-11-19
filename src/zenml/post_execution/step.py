#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

from typing import TYPE_CHECKING, Any, Dict

from zenml.enums import ExecutionStatus
from zenml.post_execution.artifact import ArtifactView

if TYPE_CHECKING:
    from zenml.metadata.base_metadata_store import BaseMetadataStore


class StepView:
    """Post-execution step class which can be used to query
    artifact information associated with a pipeline step.
    """

    def __init__(
        self,
        id_: int,
        name: str,
        parameters: Dict[str, Any],
        metadata_store: "BaseMetadataStore",
    ):
        """Initializes a post-execution step object.

        In most cases `StepView` objects should not be created manually
        but retrieved from a `PipelineRunView` object instead.

        Args:
            id_: The execution id of this step.
            name: The name of this step.
            parameters: Parameters that were used to run this step.
            metadata_store: The metadata store which should be used to fetch
                additional information related to this step.
        """
        self._id = id_
        self._name = name
        self._parameters = parameters
        self._metadata_store = metadata_store

        self._inputs: Dict[str, ArtifactView] = {}
        self._outputs: Dict[str, ArtifactView] = {}

    @property
    def id(self) -> int:
        """Returns the step id."""
        return self._id

    @property
    def name(self) -> str:
        """Returns the step name.

        This name is equal to the name argument passed to the @step decorator
        or the actual function name if no explicit name was given.

        Examples:
            # the step name will be "my_step"
            @step(name="my_step")
            def my_step_function(...)

            # the step name will be "my_step_function"
            @step
            def my_step_function(...)
        """
        return self._name

    @property
    def parameters(self) -> Dict[str, Any]:
        """The parameters used to run this step."""
        return self._parameters

    @property
    def status(self) -> ExecutionStatus:
        """Returns the current status of the step."""
        return self._metadata_store.get_step_status(self)

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
            f"name='{self._name}', parameters={self._parameters})"
        )

    def __eq__(self, other: Any) -> bool:
        """Returns whether the other object is referring to the same step."""
        if isinstance(other, StepView):
            return (
                self._id == other._id
                and self._metadata_store.uuid == other._metadata_store.uuid
            )
        return NotImplemented
