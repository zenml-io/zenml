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
import json
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

import yaml

import zenml
from zenml.config.constants import DOCKER_CONFIGURATION_KEY
from zenml.config.schedule import Schedule
from zenml.config.settings import Settings, SettingsOrDict
from zenml.config.step_configurations import (
    Step,
    StepConfigurationUpdate,
    StepSpec,
)
from zenml.config.strict_base_model import StrictBaseModel

if TYPE_CHECKING:
    from zenml.config import DockerConfiguration

from zenml.config.settings import Settings, SettingsOrDict


class PipelineConfigurationUpdate(StrictBaseModel):
    """Class for pipeline configuration updates."""

    enable_cache: Optional[bool] = None
    settings: Dict[str, Settings] = {}
    extra: Dict[str, Any] = {}


class PipelineConfiguration(PipelineConfigurationUpdate):
    """Pipeline configuration class."""

    name: str
    enable_cache: bool


class PipelineSpec(StrictBaseModel):
    """Specification of a pipeline."""

    version: str = "0.1"
    steps: List[StepSpec]


class PipelineRunConfiguration(StrictBaseModel):
    """Class for pipeline run configurations."""

    run_name: Optional[str] = None
    enable_cache: Optional[bool] = None
    schedule: Optional[Schedule] = None
    steps: Dict[str, StepConfigurationUpdate] = {}
    settings: Dict[str, Settings] = {}
    extra: Dict[str, Any] = {}


class PipelineDeployment(StrictBaseModel):
    """Class representing the deployment of a ZenML pipeline."""

    zenml_version: str = zenml.__version__
    run_name: str
    schedule: Optional[Schedule] = None
    stack_name: str  # TODO: replace by stack ID
    pipeline: PipelineConfiguration
    proto_pipeline: str
    steps: Dict[str, Step] = {}

    def add_extra(self, key: str, value: Any) -> None:
        """Adds an extra key-value pair to the pipeline configuration.

        Args:
            key: Key for which to add the extra value.
            value: The extra value.
        """
        self.pipeline.extra[key] = value

    def yaml(self, **kwargs: Any) -> str:
        """Yaml string representation of the deployment.

        Args:
            **kwargs: Kwargs to pass to the pydantic json(...) method.

        Returns:
            Yaml string representation of the deployment.
        """
        dict_ = json.loads(self.json(**kwargs, sort_keys=False))
        return cast(str, yaml.dump(dict_, sort_keys=False))

    @property
    def docker_configuration(self) -> "DockerConfiguration":
        """Docker configuration of this pipeline deployment.

        Returns:
            The Docker configuration of this pipeline deployment.
        """
        from zenml.config import DockerConfiguration

        model_or_dict: SettingsOrDict = self.pipeline.settings.get(
            DOCKER_CONFIGURATION_KEY, {}
        )
        return DockerConfiguration.parse_obj(model_or_dict)
