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
from zenml.config.cache_policy import CachePolicyWithValidator
from zenml.config.frozen_base_model import FrozenBaseModel
from zenml.config.retry_config import StepRetryConfig
from zenml.config.schedule import Schedule
from zenml.config.source import SourceWithValidator
from zenml.config.step_configurations import StepConfigurationUpdate
from zenml.enums import ExecutionMode
from zenml.model.model import Model
from zenml.models import PipelineBuildBase
from zenml.utils import pydantic_utils
from zenml.utils.tag_utils import Tag


class PipelineRunConfiguration(
    FrozenBaseModel, pydantic_utils.YAMLSerializationMixin
):
    """Class for pipeline run configurations."""

    run_name: Optional[str] = Field(
        default=None, description="The name of the pipeline run."
    )
    enable_cache: Optional[bool] = Field(
        default=None,
        description="Whether to enable cache for all steps of the pipeline "
        "run.",
    )
    enable_artifact_metadata: Optional[bool] = Field(
        default=None,
        description="Whether to enable metadata for the output artifacts of "
        "all steps of the pipeline run.",
    )
    enable_artifact_visualization: Optional[bool] = Field(
        default=None,
        description="Whether to enable visualizations for the output "
        "artifacts of all steps of the pipeline run.",
    )
    enable_step_logs: Optional[bool] = Field(
        default=None,
        description="Whether to enable logs for all steps of the pipeline run.",
    )
    enable_pipeline_logs: Optional[bool] = Field(
        default=None,
        description="Whether to enable pipeline logs for the pipeline run.",
    )
    schedule: Optional[Schedule] = Field(
        default=None, description="The schedule on which to run the pipeline."
    )
    build: Union[PipelineBuildBase, UUID, None] = Field(
        default=None,
        union_mode="left_to_right",
        description="The build to use for the pipeline run.",
    )
    steps: Optional[Dict[str, StepConfigurationUpdate]] = Field(
        default=None,
        description="Configurations for the steps of the pipeline run.",
    )
    settings: Optional[Dict[str, SerializeAsAny[BaseSettings]]] = Field(
        default=None, description="Settings for the pipeline run."
    )
    environment: Optional[Dict[str, Any]] = Field(
        default=None,
        description="The environment for all steps of the pipeline run.",
    )
    secrets: Optional[List[Union[str, UUID]]] = Field(
        default=None,
        description="The secrets for all steps of the pipeline run.",
    )
    tags: Optional[List[Union[str, Tag]]] = Field(
        default=None, description="Tags to apply to the pipeline run."
    )
    extra: Optional[Dict[str, Any]] = Field(
        default=None, description="Extra configurations for the pipeline run."
    )
    model: Optional[Model] = Field(
        default=None, description="The model to use for the pipeline run."
    )
    parameters: Optional[Dict[str, Any]] = Field(
        default=None, description="Parameters for the pipeline function."
    )
    retry: Optional[StepRetryConfig] = Field(
        default=None,
        description="The retry configuration for all steps of the pipeline run.",
    )
    failure_hook_source: Optional[SourceWithValidator] = Field(
        default=None,
        description="The failure hook source for all steps of the pipeline run.",
    )
    init_hook_source: Optional[SourceWithValidator] = Field(
        default=None,
        description="The init hook source for the pipeline run.",
    )
    init_hook_kwargs: Optional[Dict[str, Any]] = Field(
        default=None,
        description="The init hook args for the pipeline run.",
    )
    cleanup_hook_source: Optional[SourceWithValidator] = Field(
        default=None,
        description="The cleanup hook source for the pipeline run.",
    )
    success_hook_source: Optional[SourceWithValidator] = Field(
        default=None,
        description="The success hook source for all steps of the pipeline run.",
    )
    substitutions: Optional[Dict[str, str]] = Field(
        default=None, description="The substitutions for the pipeline run."
    )
    cache_policy: Optional[CachePolicyWithValidator] = Field(
        default=None,
        description="The cache policy for all steps of the pipeline run.",
    )
    execution_mode: Optional[ExecutionMode] = Field(
        default=None,
        description="The execution mode for the pipeline run.",
    )
