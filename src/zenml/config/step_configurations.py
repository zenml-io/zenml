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

from pydantic import (
    ConfigDict,
    SerializeAsAny,
    field_validator,
    model_validator,
)

from zenml.artifacts.artifact_config import ArtifactConfig
from zenml.artifacts.external_artifact_config import (
    ExternalArtifactConfiguration,
)
from zenml.client_lazy_loader import ClientLazyLoader
from zenml.config.base_settings import BaseSettings, SettingsOrDict
from zenml.config.constants import DOCKER_SETTINGS_KEY, RESOURCE_SETTINGS_KEY
from zenml.config.retry_config import StepRetryConfig
from zenml.config.source import Source, SourceWithValidator
from zenml.config.strict_base_model import StrictBaseModel
from zenml.logger import get_logger
from zenml.model.lazy_load import ModelVersionDataLazyLoader
from zenml.model.model import Model
from zenml.utils import deprecation_utils
from zenml.utils.pydantic_utils import before_validator_handler

if TYPE_CHECKING:
    from zenml.config import DockerSettings, ResourceSettings

logger = get_logger(__name__)


class PartialArtifactConfiguration(StrictBaseModel):
    """Class representing a partial input/output artifact configuration."""

    materializer_source: Optional[Tuple[SourceWithValidator, ...]] = None
    # TODO: This could be moved to the `PipelineDeployment` as it's the same
    # for all steps/outputs
    default_materializer_source: Optional[SourceWithValidator] = None
    artifact_config: Optional[ArtifactConfig] = None

    @model_validator(mode="before")
    @classmethod
    @before_validator_handler
    def _remove_deprecated_attributes(
        cls, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Removes deprecated attributes from the values dict.

        Args:
            data: The values dict used to instantiate the model.

        Returns:
            The values dict without deprecated attributes.
        """
        deprecated_attributes = ["artifact_source"]

        for deprecated_attribute in deprecated_attributes:
            if deprecated_attribute in data:
                data.pop(deprecated_attribute)

        return data

    @field_validator("materializer_source", mode="before")
    @classmethod
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
            value = (Source.model_validate(value),)
        elif isinstance(value, Source):
            value = (value,)

        return value


class ArtifactConfiguration(PartialArtifactConfiguration):
    """Class representing a complete input/output artifact configuration."""

    materializer_source: Tuple[SourceWithValidator, ...]

    @field_validator("materializer_source", mode="before")
    @classmethod
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
            value = (Source.model_validate(value),)
        elif isinstance(value, Source):
            value = (value,)

        return value


class StepConfigurationUpdate(StrictBaseModel):
    """Class for step configuration updates."""

    enable_cache: Optional[bool] = None
    enable_artifact_metadata: Optional[bool] = None
    enable_artifact_visualization: Optional[bool] = None
    enable_step_logs: Optional[bool] = None
    step_operator: Optional[str] = None
    experiment_tracker: Optional[str] = None
    parameters: Dict[str, Any] = {}
    settings: Dict[str, SerializeAsAny[BaseSettings]] = {}
    extra: Dict[str, Any] = {}
    failure_hook_source: Optional[SourceWithValidator] = None
    success_hook_source: Optional[SourceWithValidator] = None
    model: Optional[Model] = None
    retry: Optional[StepRetryConfig] = None

    outputs: Mapping[str, PartialArtifactConfiguration] = {}


class PartialStepConfiguration(StepConfigurationUpdate):
    """Class representing a partial step configuration."""

    name: str
    caching_parameters: Mapping[str, Any] = {}
    external_input_artifacts: Mapping[str, ExternalArtifactConfiguration] = {}
    model_artifacts_or_metadata: Mapping[str, ModelVersionDataLazyLoader] = {}
    client_lazy_loaders: Mapping[str, ClientLazyLoader] = {}
    outputs: Mapping[str, PartialArtifactConfiguration] = {}

    # TODO: In Pydantic v2, the `model_` is a protected namespaces for all
    #  fields defined under base models. If not handled, this raises a warning.
    #  It is possible to suppress this warning message with the following
    #  configuration, however the ultimate solution is to rename these fields.
    #  Even though they do not cause any problems right now, if we are not
    #  careful we might overwrite some fields protected by pydantic.
    model_config = ConfigDict(protected_namespaces=())

    # Override the deprecation validator as we do not want to deprecate the
    # `name`` attribute on this class.
    _deprecation_validator = deprecation_utils.deprecate_pydantic_attributes()

    @model_validator(mode="before")
    @classmethod
    @before_validator_handler
    def _remove_deprecated_attributes(cls, data: Any) -> Any:
        """Removes deprecated attributes from the values dict.

        Args:
            data: The values dict used to instantiate the model.

        Returns:
            The values dict without deprecated attributes.
        """
        deprecated_attributes = ["docstring", "inputs"]

        for deprecated_attribute in deprecated_attributes:
            if deprecated_attribute in data:
                data.pop(deprecated_attribute)

        return data


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

        if isinstance(model_or_dict, BaseSettings):
            model_or_dict = model_or_dict.model_dump()
        return ResourceSettings.model_validate(model_or_dict)

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
        if isinstance(model_or_dict, BaseSettings):
            model_or_dict = model_or_dict.model_dump()
        return DockerSettings.model_validate(model_or_dict)


class InputSpec(StrictBaseModel):
    """Step input specification."""

    step_name: str
    output_name: str


class StepSpec(StrictBaseModel):
    """Specification of a pipeline."""

    source: SourceWithValidator
    upstream_steps: List[str]
    inputs: Dict[str, InputSpec] = {}
    # The default value is to ensure compatibility with specs of version <0.2
    pipeline_parameter_name: str = ""

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
