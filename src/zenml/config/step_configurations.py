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
"""Pipeline configuration classes."""

from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Mapping,
    Optional,
    Tuple,
    Union,
)

from pydantic import root_validator, validator

from zenml.artifacts.external_artifact_config import (
    ExternalArtifactConfiguration,
)
from zenml.client_lazy_loader import ClientLazyLoader
from zenml.config.base_settings import BaseSettings, SettingsOrDict
from zenml.config.constants import DOCKER_SETTINGS_KEY, RESOURCE_SETTINGS_KEY
from zenml.config.source import Source, convert_source_validator
from zenml.config.strict_base_model import StrictBaseModel
from zenml.logger import get_logger
from zenml.model.lazy_load import ModelVersionDataLazyLoader
from zenml.model.model import Model
from zenml.utils import deprecation_utils

if TYPE_CHECKING:
    from zenml.config import DockerSettings, ResourceSettings

logger = get_logger(__name__)


class PartialArtifactConfiguration(StrictBaseModel):
    """Class representing a partial input/output artifact configuration."""

    materializer_source: Optional[Tuple[Source, ...]] = None
    # TODO: This could be moved to the `PipelineDeployment` as it's the same
    # for all steps/outputs
    default_materializer_source: Optional[Source] = None

    @root_validator(pre=True)
    def _remove_deprecated_attributes(
        cls, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Removes deprecated attributes from the values dict.

        Args:
            values: The values dict used to instantiate the model.

        Returns:
            The values dict without deprecated attributes.
        """
        deprecated_attributes = ["artifact_source"]
        for deprecated_attribute in deprecated_attributes:
            if deprecated_attribute in values:
                values.pop(deprecated_attribute)
        return values

    @validator("materializer_source", pre=True)
    def _convert_source(
        cls,
        value: Union[None, Source, Dict[str, Any], str, Tuple[Source, ...]],
    ) -> Optional[Tuple[Source, ...]]:
        """Converts old source strings to tuples of source objects.

        Args:
            value: Source string or object.

        Returns:
            The converted source.
        """
        if isinstance(value, str):
            value = (Source.from_import_path(value),)
        elif isinstance(value, dict):
            value = (Source.parse_obj(value),)
        elif isinstance(value, Source):
            value = (value,)

        return value


class ArtifactConfiguration(PartialArtifactConfiguration):
    """Class representing a complete input/output artifact configuration."""

    materializer_source: Tuple[Source, ...]

    @validator("materializer_source", pre=True)
    def _convert_source(
        cls, value: Union[Source, Dict[str, Any], str, Tuple[Source, ...]]
    ) -> Tuple[Source, ...]:
        """Converts old source strings to tuples of source objects.

        Args:
            value: Source string or object.

        Returns:
            The converted source.
        """
        if isinstance(value, str):
            value = (Source.from_import_path(value),)
        elif isinstance(value, dict):
            value = (Source.parse_obj(value),)
        elif isinstance(value, Source):
            value = (value,)

        return value


class StepConfigurationUpdate(StrictBaseModel):
    """Class for step configuration updates."""

    name: Optional[str] = None
    enable_cache: Optional[bool] = None
    enable_artifact_metadata: Optional[bool] = None
    enable_artifact_visualization: Optional[bool] = None
    enable_step_logs: Optional[bool] = None
    step_operator: Optional[str] = None
    experiment_tracker: Optional[str] = None
    parameters: Dict[str, Any] = {}
    settings: Dict[str, BaseSettings] = {}
    extra: Dict[str, Any] = {}
    failure_hook_source: Optional[Source] = None
    success_hook_source: Optional[Source] = None
    model: Optional[Model] = None

    outputs: Mapping[str, PartialArtifactConfiguration] = {}

    _convert_source = convert_source_validator(
        "failure_hook_source", "success_hook_source"
    )
    _deprecation_validator = deprecation_utils.deprecate_pydantic_attributes(
        "name"
    )


class PartialStepConfiguration(StepConfigurationUpdate):
    """Class representing a partial step configuration."""

    name: str
    caching_parameters: Mapping[str, Any] = {}
    external_input_artifacts: Mapping[str, ExternalArtifactConfiguration] = {}
    model_artifacts_or_metadata: Mapping[str, ModelVersionDataLazyLoader] = {}
    client_lazy_loaders: Mapping[str, ClientLazyLoader] = {}
    outputs: Mapping[str, PartialArtifactConfiguration] = {}

    # Override the deprecation validator as we do not want to deprecate the
    # `name`` attribute on this class.
    _deprecation_validator = deprecation_utils.deprecate_pydantic_attributes()

    @root_validator(pre=True)
    def _remove_deprecated_attributes(
        cls, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Removes deprecated attributes from the values dict.

        Args:
            values: The values dict used to instantiate the model.

        Returns:
            The values dict without deprecated attributes.
        """
        deprecated_attributes = ["docstring", "inputs"]
        for deprecated_attribute in deprecated_attributes:
            if deprecated_attribute in values:
                values.pop(deprecated_attribute)
        return values


class StepConfiguration(PartialStepConfiguration):
    """Step configuration class."""

    outputs: Mapping[str, ArtifactConfiguration] = {}

    @property
    def resource_settings(self) -> "ResourceSettings":
        """Resource settings of this step configuration.

        Returns:
            The resource settings of this step configuration.
        """
        from zenml.config import ResourceSettings

        model_or_dict: SettingsOrDict = self.settings.get(
            RESOURCE_SETTINGS_KEY, {}
        )
        return ResourceSettings.parse_obj(model_or_dict)

    @property
    def docker_settings(self) -> "DockerSettings":
        """Docker settings of this step configuration.

        Returns:
            The Docker settings of this step configuration.
        """
        from zenml.config import DockerSettings

        model_or_dict: SettingsOrDict = self.settings.get(
            DOCKER_SETTINGS_KEY, {}
        )
        return DockerSettings.parse_obj(model_or_dict)


class InputSpec(StrictBaseModel):
    """Step input specification."""

    step_name: str
    output_name: str


class StepSpec(StrictBaseModel):
    """Specification of a pipeline."""

    source: Source
    upstream_steps: List[str]
    inputs: Dict[str, InputSpec] = {}
    # The default value is to ensure compatibility with specs of version <0.2
    pipeline_parameter_name: str = ""

    _convert_source = convert_source_validator("source")

    def __eq__(self, other: Any) -> bool:
        """Returns whether the other object is referring to the same step.

        This is the case if the other objects is a `StepSpec` with the same
        `upstream_steps` and a `source` that meets one of the following
        conditions:
            - it is the same as the `source` of this step
            - it refers to the same absolute path as the `source` of this step

        Args:
            other: The other object to compare to.

        Returns:
            True if the other object is referring to the same step.
        """
        if isinstance(other, StepSpec):
            if self.upstream_steps != other.upstream_steps:
                return False

            if self.inputs != other.inputs:
                return False

            if self.pipeline_parameter_name != other.pipeline_parameter_name:
                return False

            return self.source.import_path == other.source.import_path

        return NotImplemented


class Step(StrictBaseModel):
    """Class representing a ZenML step."""

    spec: StepSpec
    config: StepConfiguration
