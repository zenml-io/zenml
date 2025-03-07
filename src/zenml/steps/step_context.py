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
    List,
    Mapping,
    Optional,
    Sequence,
    Type,
)

from zenml.exceptions import StepContextError
from zenml.logger import get_logger
from zenml.utils.callback_registry import CallbackRegistry
from zenml.utils.singleton import SingletonMetaClass

if TYPE_CHECKING:
    from zenml.artifacts.artifact_config import ArtifactConfig
    from zenml.materializers.base_materializer import BaseMaterializer
    from zenml.metadata.metadata_types import MetadataType
    from zenml.model.model import Model
    from zenml.models import (
        PipelineResponse,
        PipelineRunResponse,
        StepRunResponse,
    )
    from zenml.models.v2.core.step_run import StepRunInputResponse


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
        pipeline_run: "PipelineRunResponse",
        step_run: "StepRunResponse",
        output_materializers: Mapping[str, Sequence[Type["BaseMaterializer"]]],
        output_artifact_uris: Mapping[str, str],
        output_artifact_configs: Mapping[str, Optional["ArtifactConfig"]],
    ) -> None:
        """Initialize the context of the currently running step.

        Args:
            pipeline_run: The model of the current pipeline run.
            step_run: The model of the current step run.
            output_materializers: The output materializers of the step that
                this context is used in.
            output_artifact_uris: The output artifacts of the step that this
                context is used in.
            output_artifact_configs: The outputs' ArtifactConfigs of the step that this
                context is used in.

        Raises:
            StepContextError: If the keys of the output materializers and
                output artifacts do not match.
        """
        from zenml.client import Client

        try:
            pipeline_run = Client().get_pipeline_run(pipeline_run.id)
        except KeyError:
            pass
        self.pipeline_run = pipeline_run
        try:
            step_run = Client().get_run_step(step_run.id)
        except KeyError:
            pass
        self.step_run = step_run
        self.model_version = (
            step_run.model_version or pipeline_run.model_version
        )

        self.step_name = self.step_run.name

        # set outputs
        if output_materializers.keys() != output_artifact_uris.keys():
            raise StepContextError(
                f"Mismatched keys in output materializers and output artifact "
                f"URIs for step `{self.step_name}`. Output materializer "
                f"keys: {set(output_materializers)}, output artifact URI "
                f"keys: {set(output_artifact_uris)}"
            )
        self._outputs = {
            key: StepContextOutput(
                materializer_classes=output_materializers[key],
                artifact_uri=output_artifact_uris[key],
                artifact_config=output_artifact_configs[key],
            )
            for key in output_materializers.keys()
        }
        self._cleanup_registry = CallbackRegistry()

    @property
    def pipeline(self) -> "PipelineResponse":
        """Returns the current pipeline.

        Returns:
            The current pipeline or None.

        Raises:
            StepContextError: If the pipeline run does not have a pipeline.
        """
        if self.pipeline_run.pipeline:
            return self.pipeline_run.pipeline
        raise StepContextError(
            f"Unable to get pipeline in step `{self.step_name}` of pipeline "
            f"run '{self.pipeline_run.id}': This pipeline run does not have "
            f"a pipeline associated with it."
        )

    @property
    def model(self) -> "Model":
        """Returns configured Model.

        Order of resolution to search for Model is:
            1. Model from the step context
            2. Model from the pipeline context

        Returns:
            The `Model` object associated with the current step.

        Raises:
            StepContextError: If no `Model` object was specified for the step
                or pipeline.
        """
        if not self.model_version:
            raise StepContextError(
                f"Unable to get Model in step `{self.step_name}` of pipeline "
                f"run '{self.pipeline_run.id}': No model has been specified "
                "the step or pipeline."
            )

        return self.model_version.to_model_class()

    @property
    def inputs(self) -> Dict[str, "StepRunInputResponse"]:
        """Returns the input artifacts of the current step.

        Returns:
            The input artifacts of the current step.
        """
        return self.step_run.inputs

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
                f"Unable to get step output for step `{self.step_name}`: "
                f"This step does not have any outputs."
            )

        if not output_name and output_count > 1:
            raise StepContextError(
                f"Unable to get step output for step `{self.step_name}`: "
                f"This step has multiple outputs ({set(self._outputs)}), "
                f"please specify which output to return."
            )

        if output_name:
            if output_name not in self._outputs:
                raise StepContextError(
                    f"Unable to get step output '{output_name}' for "
                    f"step `{self.step_name}`. This step does not have an "
                    f"output with the given name, please specify one of the "
                    f"available outputs: {set(self._outputs)}."
                )
            return self._outputs[output_name]
        else:
            return next(iter(self._outputs.values()))

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

        output = self._get_output(output_name)
        materializer_classes = output.materializer_classes
        artifact_uri = output.artifact_uri

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

    def get_output_metadata(
        self, output_name: Optional[str] = None
    ) -> Dict[str, "MetadataType"]:
        """Returns the metadata for a given step output.

        Args:
            output_name: Optional name of the output for which to get the
                metadata. If no name is given and the step only has a single
                output, the metadata of this output will be returned. If the
                step has multiple outputs, an exception will be raised.

        Returns:
            Metadata for the given output.
        """
        output = self._get_output(output_name)
        custom_metadata = output.run_metadata or {}
        if output.artifact_config:
            custom_metadata.update(
                **(output.artifact_config.run_metadata or {})
            )
        return custom_metadata

    def get_output_tags(self, output_name: Optional[str] = None) -> List[str]:
        """Returns the tags for a given step output.

        Args:
            output_name: Optional name of the output for which to get the
                metadata. If no name is given and the step only has a single
                output, the metadata of this output will be returned. If the
                step has multiple outputs, an exception will be raised.

        Returns:
            Tags for the given output.
        """
        output = self._get_output(output_name)
        custom_tags = set(output.tags or [])
        if output.artifact_config:
            return list(
                set(output.artifact_config.tags or []).union(custom_tags)
            )
        return list(custom_tags)

    def add_output_metadata(
        self,
        metadata: Dict[str, "MetadataType"],
        output_name: Optional[str] = None,
    ) -> None:
        """Adds metadata for a given step output.

        Args:
            metadata: The metadata to add.
            output_name: Optional name of the output for which to add the
                metadata. If no name is given and the step only has a single
                output, the metadata of this output will be added. If the
                step has multiple outputs, an exception will be raised.
        """
        output = self._get_output(output_name)
        if not output.run_metadata:
            output.run_metadata = {}
        output.run_metadata.update(**metadata)

    def add_output_tags(
        self,
        tags: List[str],
        output_name: Optional[str] = None,
    ) -> None:
        """Adds tags for a given step output.

        Args:
            tags: The tags to add.
            output_name: Optional name of the output for which to add the
                tags. If no name is given and the step only has a single
                output, the tags of this output will be added. If the
                step has multiple outputs, an exception will be raised.
        """
        output = self._get_output(output_name)
        if not output.tags:
            output.tags = []
        output.tags += tags

    def remove_output_tags(
        self,
        tags: List[str],
        output_name: Optional[str] = None,
    ) -> None:
        """Removes tags for a given step output.

        Args:
            tags: The tags to remove.
            output_name: Optional name of the output for which to remove the
                tags. If no name is given and the step only has a single
                output, the tags of this output will be removed. If the
                step has multiple outputs, an exception will be raised.
        """
        output = self._get_output(output_name)
        if not output.tags:
            return
        output.tags = [tag for tag in output.tags if tag not in tags]


class StepContextOutput:
    """Represents a step output in the step context."""

    materializer_classes: Sequence[Type["BaseMaterializer"]]
    artifact_uri: str
    run_metadata: Optional[Dict[str, "MetadataType"]] = None
    artifact_config: Optional["ArtifactConfig"]
    tags: Optional[List[str]] = None

    def __init__(
        self,
        materializer_classes: Sequence[Type["BaseMaterializer"]],
        artifact_uri: str,
        artifact_config: Optional["ArtifactConfig"],
    ):
        """Initialize the step output.

        Args:
            materializer_classes: The materializer classes for the output.
            artifact_uri: The artifact URI for the output.
            artifact_config: The ArtifactConfig object of the output.
        """
        self.materializer_classes = materializer_classes
        self.artifact_uri = artifact_uri
        self.artifact_config = artifact_config
