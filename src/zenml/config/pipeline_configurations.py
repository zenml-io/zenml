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

from typing import TYPE_CHECKING, Any, Dict, Optional

from pydantic import validator

from zenml.config.constants import DOCKER_SETTINGS_KEY
from zenml.config.source import Source, convert_source_validator
from zenml.config.strict_base_model import StrictBaseModel
from zenml.model.model import Model

if TYPE_CHECKING:
    from zenml.config import DockerSettings

from zenml.config.base_settings import BaseSettings, SettingsOrDict

DISALLOWED_PIPELINE_NAMES = ["unlisted"]


class PipelineConfigurationUpdate(StrictBaseModel):
    """Class for pipeline configuration updates."""

    enable_cache: Optional[bool] = None
    enable_artifact_metadata: Optional[bool] = None
    enable_artifact_visualization: Optional[bool] = None
    enable_step_logs: Optional[bool] = None
    settings: Dict[str, BaseSettings] = {}
    extra: Dict[str, Any] = {}
    failure_hook_source: Optional[Source] = None
    success_hook_source: Optional[Source] = None
    model: Optional[Model] = None
    parameters: Optional[Dict[str, Any]] = None

    _convert_source = convert_source_validator(
        "failure_hook_source", "success_hook_source"
    )


class PipelineConfiguration(PipelineConfigurationUpdate):
    """Pipeline configuration class."""

    name: str

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
