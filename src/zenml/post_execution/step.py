#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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

from typing import TYPE_CHECKING, Any, Dict, Optional, cast

from zenml.client import Client
from zenml.enums import ExecutionStatus
from zenml.models import StepRunResponseModel
from zenml.post_execution.artifact import ArtifactView
from zenml.post_execution.base_view import BaseView

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings
    from zenml.config.step_configurations import StepConfiguration, StepSpec


class StepView(BaseView):
    """Post-execution step class.

    This can be used to query artifact information associated with a pipeline step.
    """

    MODEL_CLASS = StepRunResponseModel
    REPR_KEYS = ["id", "name", "entrypoint_name"]

    def __init__(self, model: StepRunResponseModel):
        """Initializes a post-execution step object.

        In most cases `StepView` objects should not be created manually
        but retrieved from a `PipelineRunView` object instead.

        Args:
            model: The model to initialize this object from.
        """
        super().__init__(model)
        self._inputs: Dict[str, ArtifactView] = {}
        self._outputs: Dict[str, ArtifactView] = {}

    @property
    def model(self) -> StepRunResponseModel:
        """Returns the underlying `StepRunResponseModel`.

        Returns:
            The underlying `StepRunResponseModel`.
        """
        return cast(StepRunResponseModel, self._model)

    @property
    def step_configuration(self) -> "StepConfiguration":
        """Returns the step configuration.

        Returns:
            The step configuration.
        """
        return self.model.step.config

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
        return self.step_configuration.name

    @property
    def parameters(self) -> Dict[str, str]:
        """The parameters used to run this step.

        Returns:
            The parameters used to run this step.
        """
        return self.step_configuration.parameters

    @property
    def settings(self) -> Dict[str, "BaseSettings"]:
        """Returns the step settings.

        These are runtime settings passed down to stack components, which
        can be set at step level.

        Returns:
            The step settings.
        """
        return self.step_configuration.settings

    @property
    def extra(self) -> Dict[str, Any]:
        """Returns the extra dictionary.

        This dict is meant to be used to pass any configuration down to the
        step that the user has use of.

        Returns:
            The extra dictionary.
        """
        return self.step_configuration.extra

    @property
    def enable_cache(self) -> Optional[bool]:
        """Returns whether caching is enabled for this step.

        Returns:
            Whether caching is enabled for this step.
        """
        return self.step_configuration.enable_cache

    @property
    def enable_artifact_metadata(self) -> Optional[bool]:
        """Returns whether artifact metadata is enabled for this step.

        Returns:
            Whether artifact metadata is enabled for this step.
        """
        return self.step_configuration.enable_artifact_metadata

    @property
    def step_operator(self) -> Optional[str]:
        """Returns the name of the step operator of the step.

        Returns:
            The name of the step operator of the step.
        """
        return self.step_configuration.step_operator

    @property
    def experiment_tracker(self) -> Optional[str]:
        """Returns the name of the experiment tracker of the step.

        Returns:
            The name of the experiment tracker of the step.
        """
        return self.step_configuration.experiment_tracker

    @property
    def spec(self) -> "StepSpec":
        """Returns the step spec.

        The step spec defines the source path and upstream steps of a step and
        is used primarily to compare whether two steps are the same.

        Returns:
            The step spec.
        """
        return self.model.step.spec

    @property
    def status(self) -> ExecutionStatus:
        """Returns the current status of the step.

        Returns:
            The current status of the step.
        """
        # Query the step again since the status might have changed since this
        # object was created.
        return Client().zen_store.get_run_step(self.model.id).status

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

        self._inputs = {
            name: ArtifactView(artifact_model)
            for name, artifact_model in self.model.input_artifacts.items()
        }

    def _ensure_outputs_fetched(self) -> None:
        """Fetches all step outputs from the ZenStore."""
        if self._outputs:
            # we already fetched outputs, no need to do anything
            return

        self._outputs = {
            name: ArtifactView(artifact_model)
            for name, artifact_model in self.model.output_artifacts.items()
        }
