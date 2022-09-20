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
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from zenml.config.constants import RESOURCE_CONFIGURATION_KEY
from zenml.config.settings import Settings, SettingsOrDict
from zenml.config.strict_base_model import StrictBaseModel

if TYPE_CHECKING:
    from zenml.config import ResourceConfiguration


class PartialArtifactConfiguration(StrictBaseModel):
    """Class representing a partial input/output artifact configuration."""

    artifact_source: Optional[str] = None
    materializer_source: Optional[str] = None


class ArtifactConfiguration(PartialArtifactConfiguration):
    """Class representing a complete input/output artifact configuration."""

    artifact_source: str
    materializer_source: str


class StepConfigurationUpdate(StrictBaseModel):
    """Class for step configuration updates."""

    enable_cache: Optional[bool] = None
    step_operator: Optional[str] = None
    experiment_tracker: Optional[str] = None
    function_parameters: Dict[str, Any] = {}
    settings: Dict[str, Settings] = {}
    extra: Dict[str, Any] = {}

    outputs: Dict[str, PartialArtifactConfiguration] = {}


class PartialStepConfiguration(StepConfigurationUpdate):
    """Class representing a partial step configuration."""

    name: str
    enable_cache: bool
    inputs: Dict[str, PartialArtifactConfiguration] = {}
    outputs: Dict[str, PartialArtifactConfiguration] = {}


class StepConfiguration(PartialStepConfiguration):
    """Step configuration class."""

    inputs: Dict[str, ArtifactConfiguration] = {}
    outputs: Dict[str, ArtifactConfiguration] = {}

    @property
    def resource_configuration(self) -> "ResourceConfiguration":
        """Docker configuration of this step configuration.

        Returns:
            The resource configuration of this step configuration.
        """
        from zenml.config import ResourceConfiguration

        model_or_dict: SettingsOrDict = self.settings.get(
            RESOURCE_CONFIGURATION_KEY, {}
        )
        return ResourceConfiguration.parse_obj(model_or_dict)


class StepSpec(StrictBaseModel):
    """Specification of a pipeline."""

    source: str
    upstream_steps: List[str]

    @property
    def module_name(self) -> str:
        """The step module name.

        Returns:
            The step module name.
        """
        module_name, _ = self.source.rsplit(".", maxsplit=1)
        return module_name

    @property
    def class_name(self) -> str:
        """The step class name.

        Returns:
            The step class name.
        """
        _, class_name = self.source.rsplit(".", maxsplit=1)
        return class_name


class Step(StrictBaseModel):
    """Class representing a ZenML step."""

    spec: StepSpec
    config: StepConfiguration
