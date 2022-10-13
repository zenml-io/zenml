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

from pydantic import validator

from zenml.config.constants import DOCKER_SETTINGS_KEY
from zenml.config.schedule import Schedule
from zenml.config.step_configurations import StepConfigurationUpdate, StepSpec
from zenml.config.strict_base_model import StrictBaseModel

if TYPE_CHECKING:
    from zenml.config import DockerSettings

from zenml.config.base_settings import BaseSettings, SettingsOrDict

DISALLOWED_PIPELINE_NAMES = ["unlisted"]


class PipelineConfigurationUpdate(StrictBaseModel):
    """Class for pipeline configuration updates."""

    enable_cache: Optional[bool] = None
    settings: Dict[str, BaseSettings] = {}
    extra: Dict[str, Any] = {}


class PipelineConfiguration(PipelineConfigurationUpdate):
    """Pipeline configuration class."""

    name: str
    enable_cache: bool

    @validator("name")
    def ensure_pipeline_name_allowed(cls, name: str) -> str:
        """Ensures the pipeline name is allowed.

        Args:
            name: Name of the pipeline.

        Returns:
            The validated name of the pipeline.

        Raises:
            ValueError: If the name is not allowed.
        """
        if name in DISALLOWED_PIPELINE_NAMES:
            raise ValueError(
                f"Pipeline name '{name}' is not allowed since '{name}' is a "
                "reserved key word. Please choose another name."
            )
        return name

    @property
    def docker_settings(self) -> "DockerSettings":
        """Docker settings of this pipeline.

        Returns:
            The Docker settings of this pipeline.
        """
        from zenml.config import DockerSettings

        model_or_dict: SettingsOrDict = self.settings.get(
            DOCKER_SETTINGS_KEY, {}
        )
        return DockerSettings.parse_obj(model_or_dict)


class PipelineRunConfiguration(StrictBaseModel):
    """Class for pipeline run configurations."""

    run_name: Optional[str] = None
    enable_cache: Optional[bool] = None
    schedule: Optional[Schedule] = None
    steps: Dict[str, StepConfigurationUpdate] = {}
    settings: Dict[str, BaseSettings] = {}
    extra: Dict[str, Any] = {}


class PipelineSpec(StrictBaseModel):
    """Specification of a pipeline."""

    version: str = "0.1"
    steps: List[StepSpec]

    def __eq__(self, other: Any) -> bool:
        """Returns whether the other object is referring to the same pipeline.

        Args:
            other: The other object to compare to.

        Returns:
            True if the other object is referring to the same pipeline.
        """
        if isinstance(other, PipelineSpec):
            return self.steps == other.steps
        return NotImplemented
