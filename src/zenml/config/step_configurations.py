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
from uuid import UUID

from pydantic import (
    ConfigDict,
    Field,
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
from zenml.config.cache_policy import CachePolicy, CachePolicyWithValidator
from zenml.config.constants import DOCKER_SETTINGS_KEY, RESOURCE_SETTINGS_KEY
from zenml.config.frozen_base_model import FrozenBaseModel
from zenml.config.retry_config import StepRetryConfig
from zenml.config.source import Source, SourceWithValidator
from zenml.enums import StepRuntime
from zenml.logger import get_logger
from zenml.model.lazy_load import ModelVersionDataLazyLoader
from zenml.model.model import Model
from zenml.utils import deprecation_utils
from zenml.utils.pydantic_utils import before_validator_handler, update_model

if TYPE_CHECKING:
    from zenml.config import DockerSettings, ResourceSettings
    from zenml.config.pipeline_configurations import PipelineConfiguration

logger = get_logger(__name__)


class PartialArtifactConfiguration(FrozenBaseModel):
    """Class representing a partial input/output artifact configuration."""

    materializer_source: Optional[Tuple[SourceWithValidator, ...]] = None
    # TODO: This could be moved to the `PipelineSnapshot` as it's the same
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


class StepConfigurationUpdate(FrozenBaseModel):
    """Class for step configuration updates."""

    enable_cache: Optional[bool] = Field(
        default=None,
        description="Whether to enable cache for the step.",
    )
    enable_artifact_metadata: Optional[bool] = Field(
        default=None,
        description="Whether to store metadata for the output artifacts of "
        "the step.",
    )
    enable_artifact_visualization: Optional[bool] = Field(
        default=None,
        description="Whether to enable visualizations for the output "
        "artifacts of the step.",
    )
    enable_step_logs: Optional[bool] = Field(
        default=None,
        description="Whether to enable logs for the step.",
    )
    step_operator: Optional[Union[bool, str]] = Field(
        default=None,
        description="The step operator to use for the step.",
    )
    experiment_tracker: Optional[Union[bool, str]] = Field(
        default=None,
        description="The experiment tracker to use for the step.",
    )
    parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Parameters for the step function.",
    )
    settings: Optional[Dict[str, SerializeAsAny[BaseSettings]]] = Field(
        default=None,
        description="Settings for the step.",
    )
    environment: Optional[Dict[str, str]] = Field(
        default=None,
        description="The environment for the step.",
    )
    secrets: Optional[List[Union[str, UUID]]] = Field(
        default=None,
        description="The secrets for the step.",
    )
    extra: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Extra configurations for the step.",
    )
    failure_hook_source: Optional[SourceWithValidator] = Field(
        default=None,
        description="The failure hook source for the step.",
    )
    success_hook_source: Optional[SourceWithValidator] = Field(
        default=None,
        description="The success hook source for the step.",
    )
    model: Optional[Model] = Field(
        default=None,
        description="The model to use for the step.",
    )
    retry: Optional[StepRetryConfig] = Field(
        default=None,
        description="The retry configuration for the step.",
    )
    substitutions: Optional[Dict[str, str]] = Field(
        default=None,
        description="The substitutions for the step.",
    )
    cache_policy: Optional[CachePolicyWithValidator] = Field(
        default=None,
        description="The cache policy for the step.",
    )
    runtime: Optional[StepRuntime] = Field(
        default=None,
        description="The step runtime. If not configured, the step will "
        "run inline unless a step operator or docker/resource settings "
        "are configured. This is only applicable for dynamic pipelines.",
    )

    outputs: Mapping[str, PartialArtifactConfiguration] = {}

    def uses_step_operator(self, name: str) -> bool:
        """Checks if the step configuration uses the given step operator.

        Args:
            name: The name of the step operator.

        Returns:
            If the step configuration uses the given step operator.
        """
        if self.step_operator is True:
            return True
        elif isinstance(self.step_operator, str):
            return self.step_operator == name
        else:
            return False

    def uses_experiment_tracker(self, name: str) -> bool:
        """Checks if the step configuration uses the given experiment tracker.

        Args:
            name: The name of the experiment tracker.

        Returns:
            If the step configuration uses the given experiment tracker.
        """
        if self.experiment_tracker is True:
            return True
        elif isinstance(self.experiment_tracker, str):
            return self.experiment_tracker == name
        else:
            return False


class PartialStepConfiguration(StepConfigurationUpdate):
    """Class representing a partial step configuration."""

    name: str
    # TODO: maybe move to spec?
    template: Optional[str] = None
    parameters: Dict[str, Any] = {}
    settings: Dict[str, SerializeAsAny[BaseSettings]] = {}
    environment: Dict[str, str] = {}
    secrets: List[Union[str, UUID]] = []
    extra: Dict[str, Any] = {}
    substitutions: Dict[str, str] = {}
    caching_parameters: Mapping[str, Any] = {}
    external_input_artifacts: Mapping[str, ExternalArtifactConfiguration] = {}
    model_artifacts_or_metadata: Mapping[str, ModelVersionDataLazyLoader] = {}
    client_lazy_loaders: Mapping[str, ClientLazyLoader] = {}
    outputs: Mapping[str, PartialArtifactConfiguration] = {}
    cache_policy: CachePolicyWithValidator = CachePolicy.default()

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

    def apply_pipeline_configuration(
        self, pipeline_configuration: "PipelineConfiguration"
    ) -> "StepConfiguration":
        """Apply the pipeline configuration to this step configuration.

        Args:
            pipeline_configuration: The pipeline configuration to apply.

        Returns:
            The updated step configuration.
        """
        pipeline_values = pipeline_configuration.model_dump(
            include={
                "settings",
                "extra",
                "failure_hook_source",
                "success_hook_source",
                "retry",
                "substitutions",
                "environment",
                "secrets",
                "cache_policy",
            },
            exclude_none=True,
        )
        if pipeline_values:
            original_values = self.model_dump(
                include={
                    "settings",
                    "extra",
                    "failure_hook_source",
                    "success_hook_source",
                    "retry",
                    "substitutions",
                    "environment",
                    "secrets",
                    "cache_policy",
                },
                exclude_none=True,
            )

            original_values["secrets"] = pipeline_values.get(
                "secrets", []
            ) + original_values.get("secrets", [])

            updated_config_dict = {
                **self.model_dump(),
                **pipeline_values,
            }
            updated_config = self.model_validate(updated_config_dict)
            return update_model(updated_config, original_values)
        else:
            return self.model_copy(deep=True)


class InputSpec(FrozenBaseModel):
    """Step input specification."""

    step_name: str
    output_name: str
    chunk_index: Optional[int] = None
    chunk_size: Optional[int] = None


class StepSpec(FrozenBaseModel):
    """Specification of a pipeline."""

    source: SourceWithValidator
    upstream_steps: List[str]
    # TODO: This should be `Dict[str, List[InputSpec]]`, but that would break
    # client-server compatibility. In the next major release, change this and
    # uncomment the code that migrates legacy specs.
    inputs: Dict[str, Union[List[InputSpec], InputSpec]] = {}
    invocation_id: str
    enable_heartbeat: bool = False

    @model_validator(mode="before")
    @classmethod
    @before_validator_handler
    def _migrate_legacy_fields(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        if "invocation_id" not in data:
            data["invocation_id"] = data.pop("pipeline_parameter_name", "")

        # converted_inputs = {}
        # for key, value in data.get("inputs", {}).items():
        #     if isinstance(value, (InputSpec, dict)):
        #         converted_inputs[key] = [value]
        #     else:
        #         converted_inputs[key] = value
        # data["inputs"] = converted_inputs

        return data

    # TODO: Remove this and use the `inputs` property once we change the type
    # of the `inputs` field.
    @property
    def inputs_v2(self) -> Dict[str, List[InputSpec]]:
        """Inputs of the step spec in v2 format.

        Returns:
            The inputs of the step spec in v2 format.
        """
        return {
            key: [value] if isinstance(value, InputSpec) else value
            for key, value in self.inputs.items()
        }

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

            if self.inputs_v2 != other.inputs_v2:
                return False

            if self.invocation_id != other.invocation_id:
                return False

            return self.source.import_path == other.source.import_path

        return NotImplemented


class Step(FrozenBaseModel):
    """Class representing a ZenML step."""

    spec: StepSpec
    config: StepConfiguration
    step_config_overrides: StepConfiguration

    @model_validator(mode="before")
    @classmethod
    @before_validator_handler
    def _add_step_config_overrides_if_missing(cls, data: Any) -> Any:
        """Add step config overrides if missing.

        This is to ensure backwards compatibility with data stored in the DB
        before the `step_config_overrides` field was added. In that case, only
        the `config` field, which contains the merged pipeline and step configs,
        existed. We have no way to figure out which of those values were defined
        on the step vs the pipeline level, so we just use the entire `config`
        object as the `step_config_overrides`.

        Args:
            data: The values dict used to instantiate the model.

        Returns:
            The values dict with the step config overrides added if missing.
        """
        if "step_config_overrides" not in data:
            data["step_config_overrides"] = data["config"]

        return data

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        pipeline_configuration: "PipelineConfiguration",
    ) -> "Step":
        """Create a step from a dictionary.

        This method can create a step from data stored without the merged
        `config` attribute, by merging the `step_config_overrides` with the
        pipeline configuration.

        Args:
            data: The dictionary to create the `Step` object from.
            pipeline_configuration: The pipeline configuration to apply to the
                step configuration.

        Returns:
            The instantiated object.
        """
        if "config" not in data:
            config = StepConfiguration.model_validate(
                data["step_config_overrides"]
            )
            data["config"] = config.apply_pipeline_configuration(
                pipeline_configuration
            )
        else:
            # We still need to apply the pipeline substitutions for legacy step
            # objects which include the full config object.
            from zenml.config.pipeline_configurations import (
                PipelineConfiguration,
            )

            config = StepConfiguration.model_validate(data["config"])
            data["config"] = config.apply_pipeline_configuration(
                PipelineConfiguration(
                    name=pipeline_configuration.name,
                    substitutions=pipeline_configuration.substitutions,
                )
            )

        return cls.model_validate(data)
