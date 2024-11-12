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
"""SQL Model Implementations."""

from zenml.zen_stores.schemas.action_schemas import ActionSchema
from zenml.zen_stores.schemas.api_key_schemas import APIKeySchema
from zenml.zen_stores.schemas.artifact_schemas import (
    ArtifactSchema,
    ArtifactVersionSchema,
)
from zenml.zen_stores.schemas.artifact_visualization_schemas import (
    ArtifactVisualizationSchema,
)
from zenml.zen_stores.schemas.base_schemas import BaseSchema, NamedSchema
from zenml.zen_stores.schemas.code_repository_schemas import (
    CodeRepositorySchema,
    CodeReferenceSchema,
)
from zenml.zen_stores.schemas.device_schemas import OAuthDeviceSchema
from zenml.zen_stores.schemas.event_source_schemas import EventSourceSchema
from zenml.zen_stores.schemas.pipeline_build_schemas import PipelineBuildSchema
from zenml.zen_stores.schemas.component_schemas import StackComponentSchema
from zenml.zen_stores.schemas.flavor_schemas import FlavorSchema
from zenml.zen_stores.schemas.server_settings_schemas import ServerSettingsSchema
from zenml.zen_stores.schemas.pipeline_deployment_schemas import (
    PipelineDeploymentSchema,
)
from zenml.zen_stores.schemas.pipeline_run_schemas import PipelineRunSchema
from zenml.zen_stores.schemas.pipeline_schemas import PipelineSchema
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema
from zenml.zen_stores.schemas.run_metadata_schemas import (
    RunMetadataResourceLinkSchema,
    RunMetadataSchema,
)
from zenml.zen_stores.schemas.schedule_schema import ScheduleSchema
from zenml.zen_stores.schemas.secret_schemas import SecretSchema
from zenml.zen_stores.schemas.service_schemas import ServiceSchema
from zenml.zen_stores.schemas.service_connector_schemas import (
    ServiceConnectorSchema,
)
from zenml.zen_stores.schemas.stack_schemas import (
    StackCompositionSchema,
    StackSchema,
)
from zenml.zen_stores.schemas.step_run_schemas import (
    StepRunInputArtifactSchema,
    StepRunOutputArtifactSchema,
    StepRunParentsSchema,
    StepRunSchema,
)
from zenml.zen_stores.schemas.tag_schemas import TagSchema, TagResourceSchema
from zenml.zen_stores.schemas.trigger_schemas import (
    TriggerSchema,
    TriggerExecutionSchema
)
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.logs_schemas import LogsSchema
from zenml.zen_stores.schemas.model_schemas import (
    ModelSchema,
    ModelVersionSchema,
    ModelVersionArtifactSchema,
    ModelVersionPipelineRunSchema,
)
from zenml.zen_stores.schemas.run_template_schemas import RunTemplateSchema
from zenml.zen_stores.schemas.server_settings_schemas import ServerSettingsSchema

__all__ = [
    "ActionSchema",
    "APIKeySchema",
    "ArtifactSchema",
    "ArtifactVersionSchema",
    "ArtifactVisualizationSchema",
    "BaseSchema",
    "CodeReferenceSchema",
    "CodeRepositorySchema",
    "EventSourceSchema",
    "FlavorSchema",
    "LogsSchema",
    "NamedSchema",
    "OAuthDeviceSchema",
    "PipelineBuildSchema",
    "PipelineDeploymentSchema",
    "PipelineRunSchema",
    "PipelineSchema",
    "RunMetadataResourceLinkSchema",
    "RunMetadataSchema",
    "ScheduleSchema",
    "SecretSchema",
    "ServerSettingsSchema",
    "ServiceConnectorSchema",
    "ServiceSchema",
    "StackComponentSchema",
    "StackCompositionSchema",
    "StackSchema",
    "StepRunInputArtifactSchema",
    "StepRunOutputArtifactSchema",
    "StepRunParentsSchema",
    "StepRunSchema",
    "RunTemplateSchema",
    "TagSchema",
    "TagResourceSchema",
    "TriggerSchema",
    "TriggerExecutionSchema",
    "UserSchema",
    "LogsSchema",
    "ModelSchema",
    "ModelVersionSchema",
    "ModelVersionArtifactSchema",
    "ModelVersionPipelineRunSchema",
    "WorkspaceSchema",
]
