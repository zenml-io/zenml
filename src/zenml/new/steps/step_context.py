#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Step context class."""

from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Mapping,
    NamedTuple,
    Optional,
    Sequence,
    Type,
)

from zenml.exceptions import StepContextError
from zenml.logger import get_logger
from zenml.utils.singleton import SingletonMetaClass

if TYPE_CHECKING:
    from zenml.config.step_run_info import StepRunInfo
    from zenml.materializers.base_materializer import BaseMaterializer
    from zenml.models.pipeline_models import PipelineResponseModel
    from zenml.models.pipeline_run_models import PipelineRunResponseModel
    from zenml.models.step_run_models import StepRunResponseModel
    from zenml.stack.stack import Stack

logger = get_logger(__name__)


def get_step_context() -> "StepContext":
    """Get the context of the currently running step.

    Returns:
        The context of the currently running step.

    Raises:
        RuntimeError: If no step is currently running.
    """
    if StepContext._exists():
        return StepContext()  # type: ignore
    raise RuntimeError(
        "The step context is only available inside a step function."
    )


class StepContext(metaclass=SingletonMetaClass):
    """Provides additional context inside a step function.

    This singleton class is used to access information about the current run,
    step run, or its outputs inside a step function.

    Usage example:

    ```python
    from zenml.steps import get_step_context

    @step
    def my_trainer_step() -> Any:
        context = get_step_context()

        # get info about the current pipeline run
        current_pipeline_run = context.pipeline_run

        # get info about the current step run
        current_step_run = context.step_run

        # get info about the future output artifacts of this step
        output_artifact_uri = context.get_output_artifact_uri()

        ...
    ```
    """

    def __init__(
        self,
        pipeline_run: "PipelineRunResponseModel",
        step_run: "StepRunResponseModel",
        output_materializers: Mapping[str, Sequence[Type["BaseMaterializer"]]],
        output_artifact_uris: Mapping[str, str],
        step_run_info: "StepRunInfo",
        cache_enabled: bool,
    ) -> None:
        """Initialize the context of the currently running step.

        Args:
            pipeline_run: The model of the current pipeline run.
            step_run: The model of the current step run.
            output_materializers: The output materializers of the step that
                this context is used in.
            output_artifact_uris: The output artifacts of the step that this
                context is used in.
            step_run_info: (Deprecated) info about the currently running step.
            cache_enabled: (Deprecated) Whether caching is enabled for the step.

        Raises:
            StepContextError: If the keys of the output materializers and
                output artifacts do not match.
        """
        from zenml.client import Client

        self.pipeline_run = pipeline_run
        self.step_run = step_run
        self._step_run_info = step_run_info
        self._cache_enabled = cache_enabled

        # Get the stack that we are running in
        self._stack = Client().active_stack

        self.step_name = self.step_run.name

        # set outputs
        if output_materializers.keys() != output_artifact_uris.keys():
            raise StepContextError(
                f"Mismatched keys in output materializers and output artifact "
                f"URIs for step '{self.step_name}'. Output materializer "
                f"keys: {set(output_materializers)}, output artifact URI "
                f"keys: {set(output_artifact_uris)}"
            )
        self._outputs = {
            key: StepContextOutput(
                output_materializers[key], output_artifact_uris[key]
            )
            for key in output_materializers.keys()
        }

    def _get_output(
        self, output_name: Optional[str] = None
    ) -> "StepContextOutput":
        """Returns the materializer and artifact URI for a given step output.

        Args:
            output_name: Optional name of the output for which to get the
                materializer and URI.

        Returns:
            Tuple containing the materializer and artifact URI for the
                given output.

        Raises:
            StepContextError: If the step has no outputs, no output for
                the given `output_name` or if no `output_name` was given but
                the step has multiple outputs.
        """
        output_count = len(self._outputs)
        if output_count == 0:
            raise StepContextError(
                f"Unable to get step output for step '{self.step_name}': "
                f"This step does not have any outputs."
            )

        if not output_name and output_count > 1:
            raise StepContextError(
                f"Unable to get step output for step '{self.step_name}': "
                f"This step has multiple outputs ({set(self._outputs)}), "
                f"please specify which output to return."
            )

        if output_name:
            if output_name not in self._outputs:
                raise StepContextError(
                    f"Unable to get step output '{output_name}' for "
                    f"step '{self.step_name}'. This step does not have an "
                    f"output with the given name, please specify one of the "
                    f"available outputs: {set(self._outputs)}."
                )
            return self._outputs[output_name]
        else:
            return next(iter(self._outputs.values()))

    @property
    def pipeline(self) -> "PipelineResponseModel":
        """Returns the current pipeline.

        Returns:
            The current pipeline or None.

        Raises:
            StepContextError: If the pipeline run does not have a pipeline.
        """
        if self.pipeline_run.pipeline:
            return self.pipeline_run.pipeline
        raise StepContextError(
            f"Unable to get pipeline in step '{self.step_name}' of pipeline "
            f"run '{self.pipeline_run.id}': This pipeline run does not have "
            f"a pipeline associated with it."
        )

    @property
    def stack(self) -> Optional["Stack"]:
        """(Deprecated) Returns the current active stack.

        Returns:
            The current active stack or None.
        """
        logger.warning(
            "`StepContext.stack` is deprecated and will be removed in a "
            "future release. Please use `Client().active_stack` instead."
        )
        return self._stack

    @property
    def pipeline_name(self) -> str:
        """(Deprecated) Returns the current pipeline name.

        Returns:
            The current pipeline name or None.

        Raises:
            StepContextError: If the pipeline run does not have a pipeline.
        """
        logger.warning(
            "`StepContext.pipeline_name` is deprecated and will be removed in "
            "a future release. Please use `StepContext.pipeline.name` instead."
        )
        if not self.pipeline:
            raise StepContextError(
                f"Unable to get pipeline name in step '{self.step_name}' of "
                f"pipeline run '{self.pipeline_run.name}': The pipeline run "
                f"does not have a pipeline associated with it."
            )
        return self.pipeline.name

    @property
    def run_name(self) -> Optional[str]:
        """(Deprecated) Returns the current run name.

        Returns:
            The current run name or None.
        """
        logger.warning(
            "`StepContext.run_name` is deprecated and will be removed in a "
            "future release. Please use `StepContext.pipeline_run.name` "
            "instead."
        )
        return self.pipeline_run.name

    @property
    def parameters(self) -> Dict[str, Any]:
        """(Deprecated) The step parameters.

        Returns:
            The step parameters.
        """
        logger.warning(
            "`StepContext.parameters` is deprecated and will be removed in "
            "a future release. Please use "
            "`StepContext.step_run.config.parameters` instead."
        )
        return self.step_run.config.parameters

    @property
    def step_run_info(self) -> "StepRunInfo":
        """(Deprecated) Info about the currently running step.

        Returns:
            Info about the currently running step.
        """
        logger.warning(
            "`StepContext.step_run_info` is deprecated and will be removed in "
            "a future release. Please use `StepContext.step_run` or "
            "`StepContext.pipeline_run` to access information about the "
            "current run instead."
        )
        return self._step_run_info

    @property
    def cache_enabled(self) -> bool:
        """(Deprecated) Returns whether cache is enabled for the step.

        Returns:
            True if cache is enabled for the step, otherwise False.
        """
        logger.warning(
            "`StepContext.cache_enabled` is deprecated and will be removed in "
            "a future release."
        )
        return self._cache_enabled

    def get_output_materializer(
        self,
        output_name: Optional[str] = None,
        custom_materializer_class: Optional[Type["BaseMaterializer"]] = None,
        data_type: Optional[Type[Any]] = None,
    ) -> "BaseMaterializer":
        """Returns a materializer for a given step output.

        Args:
            output_name: Optional name of the output for which to get the
                materializer. If no name is given and the step only has a
                single output, the materializer of this output will be
                returned. If the step has multiple outputs, an exception
                will be raised.
            custom_materializer_class: If given, this `BaseMaterializer`
                subclass will be initialized with the output artifact instead
                of the materializer that was registered for this step output.
            data_type: If the output annotation is of type `Union` and the step
                therefore has multiple materializers configured, you can provide
                a data type for the output which will be used to select the
                correct materializer. If not provided, the first materializer
                will be used.

        Returns:
            A materializer initialized with the output artifact for
            the given output.
        """
        from zenml.utils import materializer_utils

        materializer_classes, artifact_uri = self._get_output(output_name)

        if custom_materializer_class:
            materializer_class = custom_materializer_class
        elif len(materializer_classes) == 1 or not data_type:
            materializer_class = materializer_classes[0]
        else:
            materializer_class = materializer_utils.select_materializer(
                data_type=data_type, materializer_classes=materializer_classes
            )

        return materializer_class(artifact_uri)

    def get_output_artifact_uri(
        self, output_name: Optional[str] = None
    ) -> str:
        """Returns the artifact URI for a given step output.

        Args:
            output_name: Optional name of the output for which to get the URI.
                If no name is given and the step only has a single output,
                the URI of this output will be returned. If the step has
                multiple outputs, an exception will be raised.

        Returns:
            Artifact URI for the given output.
        """
        return self._get_output(output_name).artifact_uri


class StepContextOutput(NamedTuple):
    """Tuple containing materializer class and URI for a step output."""

    materializer_classes: Sequence[Type["BaseMaterializer"]]
    artifact_uri: str
