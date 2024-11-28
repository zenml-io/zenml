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
"""Pipeline run configuration class."""

from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import Field, SerializeAsAny

from zenml.config.base_settings import BaseSettings
from zenml.config.retry_config import StepRetryConfig
from zenml.config.schedule import Schedule
from zenml.config.source import SourceWithValidator
from zenml.config.step_configurations import StepConfigurationUpdate
from zenml.config.strict_base_model import StrictBaseModel
from zenml.model.model import Model
from zenml.models import PipelineBuildBase
from zenml.utils import pydantic_utils


class PipelineRunConfiguration(
    StrictBaseModel, pydantic_utils.YAMLSerializationMixin
):
    """Class for pipeline run configurations."""

    run_name: Optional[str] = None
    enable_cache: Optional[bool] = None
    enable_artifact_metadata: Optional[bool] = None
    enable_artifact_visualization: Optional[bool] = None
    enable_step_logs: Optional[bool] = None
    schedule: Optional[Schedule] = None
    build: Union[PipelineBuildBase, UUID, None] = Field(
        default=None, union_mode="left_to_right"
    )
    steps: Dict[str, StepConfigurationUpdate] = {}
    settings: Dict[str, SerializeAsAny[BaseSettings]] = {}
    tags: Optional[List[str]] = None
    extra: Dict[str, Any] = {}
    model: Optional[Model] = None
    parameters: Optional[Dict[str, Any]] = None
    retry: Optional[StepRetryConfig] = None
    failure_hook_source: Optional[SourceWithValidator] = None
    success_hook_source: Optional[SourceWithValidator] = None
    substitutions: Dict[str, str] = {}
