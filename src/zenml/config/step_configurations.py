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
    Annotated,
    Any,
    Dict,
    List,
    Literal,
    Mapping,
    Optional,
    Set,
    Tuple,
    Union,
)
from uuid import UUID

from pydantic import (
    AliasChoices,
    ConfigDict,
    Field,
    SerializeAsAny,
    field_validator,
    model_validator,
)
from typing_extensions import Self

from zenml.artifacts.artifact_config import ArtifactConfig
from zenml.client_lazy_loader import ClientLazyLoader
from zenml.config.base_settings import BaseSettings, SettingsOrDict
from zenml.config.cache_policy import CachePolicy, CachePolicyWithValidator
from zenml.config.constants import DOCKER_SETTINGS_KEY, RESOURCE_SETTINGS_KEY
from zenml.config.frozen_base_model import FrozenBaseModel
from zenml.config.retry_config import StepRetryConfig
from zenml.config.source import (
    Source,
    SourceWithValidator,
    StringSerializableSource,
)
from zenml.enums import GroupType, StepRuntime, StepType
from zenml.logger import get_logger
from zenml.model.lazy_load import ModelVersionDataLazyLoader
from zenml.model.model import Model
from zenml.utils import deprecation_utils, dict_utils
from zenml.utils.pydantic_utils import before_validator_handler

if TYPE_CHECKING:
    from zenml.config import DockerSettings, ResourceSettings
    from zenml.config.pipeline_configurations import PipelineConfiguration

logger = get_logger(__name__)


class GroupInfo(FrozenBaseModel):
    """Class representing group information."""

    id: str
    name: Optional[str] = None
    type: GroupType = GroupType.MANUAL


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


class LiteralInputSource(FrozenBaseModel):
    """Literal value step input source."""

    type: Literal["literal"] = "literal"
    value: Any


class ArtifactVersionInputSource(FrozenBaseModel):
    """Artifact version step input source."""

    type: Literal["artifact_version"] = "artifact_version"
    id: UUID = Field(
        validation_alias=AliasChoices("id", "artifact_version_id")
    )


class ModelDataInputSource(FrozenBaseModel):
    """Model version data step input source."""

    type: Literal["model_data"] = "model_data"
    lazy_loader: ModelVersionDataLazyLoader


class ClientCallInputSource(FrozenBaseModel):
    """Client method call step input source."""

    type: Literal["client_call"] = "client_call"
    lazy_loader: ClientLazyLoader


InputSource = Annotated[
    Union[
        LiteralInputSource,
        ArtifactVersionInputSource,
        ModelDataInputSource,
        ClientCallInputSource,
    ],
    Field(discriminator="type"),
]

InputSourceOverride = Union[ArtifactVersionInputSource, LiteralInputSource]


def get_artifact_version_input_sources(
    artifact_version_ids: Mapping[str, UUID],
) -> Dict[str, InputSourceOverride]:
    """Convert artifact version IDs to input sources.

    Args:
        artifact_version_ids: The artifact version IDs, keyed by input name.

    Returns:
        The input sources.
    """
    return {
        name: ArtifactVersionInputSource(id=artifact_version_id)
        for name, artifact_version_id in artifact_version_ids.items()
    }


def _typed_input_sources(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Filter out legacy untyped entries from an inputs dict.

    Very old configs stored a deprecated `inputs` field containing artifact
    configurations. Those entries have no `type` key and are removed.

    Args:
        inputs: The inputs dict to filter.

    Returns:
        The inputs dict without legacy untyped entries.
    """
    return {
        key: value
        for key, value in inputs.items()
        if not isinstance(value, dict) or "type" in value
    }


def _convert_legacy_input_channels(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert legacy step input config fields to input sources.

    Args:
        data: The values dict used to instantiate the model.

    Returns:
        The values dict with legacy input fields converted to entries in
        the `inputs` field.
    """
    inputs = data.get("inputs") or {}
    if not isinstance(inputs, dict):
        return data

    inputs = _typed_input_sources(inputs)

    for key, value in (
        data.pop("external_input_artifacts", None) or {}
    ).items():
        if key in inputs:
            continue

        if artifact_version_id := value.get("id"):
            inputs[key] = {
                "type": "artifact_version",
                "id": artifact_version_id,
            }

    for key, value in (
        data.pop("model_artifacts_or_metadata", None) or {}
    ).items():
        if key not in inputs:
            inputs[key] = {"type": "model_data", "lazy_loader": value}

    for key, value in (data.pop("client_lazy_loaders", None) or {}).items():
        if key not in inputs:
            inputs[key] = {"type": "client_call", "lazy_loader": value}

    data["inputs"] = inputs
    return data


def _convert_legacy_parameters(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert legacy step config parameters to literal input sources.

    Args:
        data: The step config values dict.

    Returns:
        The values dict with parameters converted to literal input sources.
    """
    parameters = data.get("parameters") or {}
    if not isinstance(parameters, dict):
        return data

    inputs = data.get("inputs") or {}
    if isinstance(inputs, dict):
        inputs = _typed_input_sources(inputs)
    if inputs:
        # The config already stores input sources, which means the
        # parameters only mirror the literal input values for display
        # purposes.
        data["parameters"] = {}
        return data

    # Some legacy dynamic step configs stored lazily resolved values in the
    # parameters. Those inputs are already covered by their lazy loader
    # config and are not converted.
    lazy_keys: Set[str] = set()
    for legacy_field in (
        "external_input_artifacts",
        "model_artifacts_or_metadata",
        "client_lazy_loaders",
    ):
        lazy_keys.update((data.get(legacy_field) or {}).keys())

    data["inputs"] = {
        key: {"type": "literal", "value": value}
        for key, value in parameters.items()
        if key not in lazy_keys
    }
    data["parameters"] = {}
    return data


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
    failure_hook_source: Optional[StringSerializableSource] = Field(
        default=None,
        description="The failure hook source for the step.",
    )
    success_hook_source: Optional[StringSerializableSource] = Field(
        default=None,
        description="The success hook source for the step.",
    )
    start_hook_source: Optional[StringSerializableSource] = Field(
        default=None,
        description="The start hook source for the step.",
    )
    end_hook_source: Optional[StringSerializableSource] = Field(
        default=None,
        description="The end hook source for the step.",
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
    heartbeat_healthy_threshold: int = Field(
        default=30,
        description="The amount of time (in minutes) that a running step "
        "has not received heartbeat and is considered healthy. By default, "
        "set to 30 minutes.",
        ge=10,
        le=60,
    )
    group: Optional[GroupInfo] = Field(
        default=None,
        description="The group information for the step.",
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
    step_type: Optional[StepType] = None
    # TODO: maybe move to spec?
    template: Optional[str] = None
    parameters: Dict[str, Any] = {}
    settings: Dict[str, SerializeAsAny[BaseSettings]] = {}
    environment: Dict[str, str] = {}
    secrets: List[Union[str, UUID]] = []
    extra: Dict[str, Any] = {}
    substitutions: Dict[str, str] = {}
    caching_parameters: Mapping[str, Any] = {}
    inputs: Mapping[str, InputSource] = {}
    outputs: Mapping[str, PartialArtifactConfiguration] = {}
    cache_policy: CachePolicyWithValidator = CachePolicy.default()
    command: Optional[List[str]] = None

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
        deprecated_attributes = ["docstring"]

        for deprecated_attribute in deprecated_attributes:
            if deprecated_attribute in data:
                data.pop(deprecated_attribute)

        return _convert_legacy_input_channels(data)

    @property
    def literal_input_values(self) -> Dict[str, Any]:
        """Literal input values of this step configuration.

        Returns:
            The literal input values of this step configuration.
        """
        return {
            name: source.value
            for name, source in self.inputs.items()
            if isinstance(source, LiteralInputSource)
        }

    def with_literal_inputs(self, values: Mapping[str, Any]) -> Self:
        """Copy of the step configuration with updated literal inputs.

        The parameters are reset as they only mirror the literal input values
        for display purposes.

        Args:
            values: The literal input values to set, keyed by input name.

        Returns:
            The updated step configuration.
        """
        return self.model_copy(
            update={
                "inputs": {
                    **self.inputs,
                    **{
                        name: LiteralInputSource(value=value)
                        for name, value in values.items()
                    },
                },
                "parameters": {},
            }
        )


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
        self,
        pipeline_configuration: "PipelineConfiguration",
        exclude_hook_sources: bool,
    ) -> "StepConfiguration":
        """Apply the pipeline configuration to this step configuration.

        Args:
            pipeline_configuration: The pipeline configuration to apply.
            exclude_hook_sources: If True, the pipeline-level lifecycle hook
                sources are not propagated as step defaults.

        Returns:
            The updated step configuration.
        """
        pipeline_dict = _get_pipeline_values_to_propagate(
            pipeline_configuration=pipeline_configuration,
            exclude_hook_sources=exclude_hook_sources,
        )
        merged_config_dict = _apply_pipeline_configuration(
            self.model_dump(), pipeline_dict
        )
        return self.model_validate(merged_config_dict)


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
    inputs: Dict[str, Union[InputSpec, List[InputSpec]]] = {}
    invocation_id: str
    enable_heartbeat: bool = False
    parameter_spec: Optional[Dict[str, Any]] = None
    # JSON schema for all step function inputs. Superset of the
    # `parameter_spec`, which is the JSON schema only for step parameters.
    input_schema: Optional[Dict[str, Any]] = None

    @model_validator(mode="before")
    @classmethod
    @before_validator_handler
    def _migrate_legacy_fields(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        if "invocation_id" not in data:
            data["invocation_id"] = data.pop("pipeline_parameter_name", "")

        return data

    @property
    def normalized_inputs(self) -> Dict[str, List[InputSpec]]:
        """Inputs of the step spec normalized to a list of input specs.

        Returns:
            The inputs of the step spec normalized to a list of input specs.
        """
        return {
            key: [value] if isinstance(value, InputSpec) else value
            for key, value in self.inputs.items()
        }

    def is_scalar_input(self, name: str) -> bool:
        """Returns whether an input is a scalar artifact.

        Args:
            name: The input name.

        Returns:
            `True` if the input is a scalar artifact.
        """
        return isinstance(self.inputs[name], InputSpec)

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

            if self.normalized_inputs != other.normalized_inputs:
                return False

            if self.parameter_spec != other.parameter_spec:
                return False

            if self.input_schema != other.input_schema:
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

        for key in ("config", "step_config_overrides"):
            config_dict = data.get(key)
            if isinstance(config_dict, dict):
                data[key] = _convert_legacy_parameters(config_dict)

        return data

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        pipeline_configuration: "PipelineConfiguration",
        exclude_hook_sources: bool,
    ) -> "Step":
        """Create a step from a dictionary.

        This method can create a step from data stored without the merged
        `config` attribute, by merging the `step_config_overrides` with the
        pipeline configuration.

        Args:
            data: The dictionary to create the `Step` object from.
            pipeline_configuration: The pipeline configuration to apply to the
                step configuration.
            exclude_hook_sources: If True, the pipeline-level lifecycle hook
                sources are not propagated as step defaults.

        Returns:
            The instantiated object.
        """
        if "config" not in data:
            pipeline_dict = _get_pipeline_values_to_propagate(
                pipeline_configuration=pipeline_configuration,
                exclude_hook_sources=exclude_hook_sources,
            )

            merged_config_dict = _apply_pipeline_configuration(
                data["step_config_overrides"], pipeline_dict
            )
            data["config"] = merged_config_dict
        else:
            # We still need to apply the pipeline substitutions for legacy step
            # objects which include the full config object.
            merged_config_dict = _apply_pipeline_configuration(
                data["config"],
                {"substitutions": pipeline_configuration.substitutions},
            )
            data["config"] = merged_config_dict

        return cls.model_validate(data).with_display_parameters()

    def with_display_parameters(self) -> "Step":
        """Copy of the step with parameters mirroring the literal inputs.

        Returns:
            The step with populated parameters.
        """
        config_parameters = self.config.literal_input_values
        override_parameters = self.step_config_overrides.literal_input_values

        if not config_parameters and not override_parameters:
            return self

        return self.model_copy(
            update={
                "config": self.config.model_copy(
                    update={"parameters": config_parameters}
                ),
                "step_config_overrides": self.step_config_overrides.model_copy(
                    update={"parameters": override_parameters}
                ),
            }
        )

    @property
    def available_input_keys(self) -> Set[str]:
        """Available input keys for the step.

        Returns:
            The available input keys for the step.
        """
        return set(self.spec.normalized_inputs) | set(self.config.inputs)


def _apply_pipeline_configuration(
    config_dict: Dict[str, Any], pipeline_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Apply the pipeline configuration to the step config dictionary.

    Args:
        config_dict: The config dictionary to apply the pipeline configuration to.
        pipeline_dict: The pipeline configuration dictionary.

    Returns:
        The merged config dictionary.
    """
    if not pipeline_dict:
        return config_dict

    combined_dict = {
        **config_dict,
        **pipeline_dict,
    }
    step_overrides = {
        key: value
        for key, value in config_dict.items()
        if key in pipeline_dict and value is not None
    }
    step_overrides["secrets"] = pipeline_dict.get(
        "secrets", []
    ) + step_overrides.get("secrets", [])
    merged_config_dict = dict_utils.recursive_update(
        combined_dict, update=step_overrides, ignore_none=True
    )
    return merged_config_dict


def _get_pipeline_values_to_propagate(
    pipeline_configuration: "PipelineConfiguration",
    exclude_hook_sources: bool,
) -> Dict[str, Any]:
    """Get the pipeline configuration fields propagated to a step.

    Args:
        pipeline_configuration: The pipeline configuration to get the values
            from.
        exclude_hook_sources: If True, omit the lifecycle hook sources.

    Returns:
        The pipeline configuration values to propagate to the step.
    """
    include = {
        "settings",
        "extra",
        "retry",
        "substitutions",
        "environment",
        "secrets",
        "cache_policy",
    }
    if not exclude_hook_sources:
        include |= {
            "failure_hook_source",
            "success_hook_source",
            "start_hook_source",
            "end_hook_source",
        }

    return pipeline_configuration.model_dump(
        include=include, exclude_none=True
    )
