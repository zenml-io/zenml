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

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import SerializeAsAny, field_validator

from zenml.config.cache_policy import CachePolicyWithValidator
from zenml.config.constants import (
    DEPLOYMENT_SETTINGS_KEY,
    DOCKER_SETTINGS_KEY,
    RESOURCE_SETTINGS_KEY,
)
from zenml.config.frozen_base_model import FrozenBaseModel
from zenml.config.retry_config import StepRetryConfig
from zenml.config.source import SourceWithValidator
from zenml.enums import ExecutionMode
from zenml.model.model import Model
from zenml.utils.tag_utils import Tag
from zenml.utils.time_utils import utc_now

if TYPE_CHECKING:
    from zenml.config import (
        DeploymentSettings,
        DockerSettings,
        ResourceSettings,
    )

from zenml.config.base_settings import BaseSettings, SettingsOrDict

DISALLOWED_PIPELINE_NAMES = ["unlisted"]


class PipelineConfigurationUpdate(FrozenBaseModel):
    """Class for pipeline configuration updates."""

    enable_cache: Optional[bool] = None
    enable_artifact_metadata: Optional[bool] = None
    enable_artifact_visualization: Optional[bool] = None
    enable_step_logs: Optional[bool] = None
    environment: Dict[str, Any] = {}
    secrets: List[Union[str, UUID]] = []
    enable_pipeline_logs: Optional[bool] = None
    execution_mode: Optional[ExecutionMode] = None
    settings: Dict[str, SerializeAsAny[BaseSettings]] = {}
    tags: Optional[List[Union[str, "Tag"]]] = None
    extra: Dict[str, Any] = {}
    failure_hook_source: Optional[SourceWithValidator] = None
    success_hook_source: Optional[SourceWithValidator] = None
    init_hook_source: Optional[SourceWithValidator] = None
    init_hook_kwargs: Optional[Dict[str, Any]] = None
    cleanup_hook_source: Optional[SourceWithValidator] = None
    model: Optional[Model] = None
    parameters: Optional[Dict[str, Any]] = None
    retry: Optional[StepRetryConfig] = None
    substitutions: Dict[str, str] = {}
    cache_policy: Optional[CachePolicyWithValidator] = None

    def finalize_substitutions(
        self, start_time: Optional[datetime] = None, inplace: bool = False
    ) -> Dict[str, str]:
        """Returns the full substitutions dict.

        Args:
            start_time: Start time of the pipeline run.
            inplace: Whether to update the substitutions in place.

        Returns:
            The full substitutions dict including date and time.
        """
        if start_time is None:
            start_time = utc_now()

        if inplace:
            dict_ = self.substitutions
        else:
            dict_ = self.substitutions.copy()

        dict_.setdefault("date", start_time.strftime("%Y_%m_%d"))
        dict_.setdefault("time", start_time.strftime("%H_%M_%S_%f"))

        return dict_


class PipelineConfiguration(PipelineConfigurationUpdate):
    """Pipeline configuration class."""

    name: str
    execution_mode: ExecutionMode = ExecutionMode.CONTINUE_ON_FAILURE

    @field_validator("name")
    @classmethod
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
        return DockerSettings.model_validate(model_or_dict)

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
    def deployment_settings(self) -> "DeploymentSettings":
        """Deployment settings of this pipeline configuration.

        Returns:
            The deployment settings of this pipeline configuration.
        """
        from zenml.config import DeploymentSettings

        model_or_dict: SettingsOrDict = self.settings.get(
            DEPLOYMENT_SETTINGS_KEY, {}
        )

        if isinstance(model_or_dict, BaseSettings):
            model_or_dict = model_or_dict.model_dump()
        return DeploymentSettings.model_validate(model_or_dict)
