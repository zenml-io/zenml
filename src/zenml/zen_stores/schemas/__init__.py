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

from zenml.zen_stores.schemas.api_key_schemas import APIKeySchema
from zenml.zen_stores.schemas.api_transaction_schemas import (
    ApiTransactionResultSchema,
    ApiTransactionSchema,
)
from zenml.zen_stores.schemas.artifact_schemas import (
    ArtifactSchema,
    ArtifactVersionSchema,
)
from zenml.zen_stores.schemas.artifact_visualization_schemas import (
    ArtifactVisualizationSchema,
)
from zenml.zen_stores.schemas.base_schemas import BaseSchema, NamedSchema
from zenml.zen_stores.schemas.code_repository_schemas import (
    CodeReferenceSchema,
    CodeRepositorySchema,
)
from zenml.zen_stores.schemas.component_schemas import StackComponentSchema
from zenml.zen_stores.schemas.curated_visualization_schemas import (
    CuratedVisualizationSchema,
)
from zenml.zen_stores.schemas.deployment_schemas import DeploymentSchema
from zenml.zen_stores.schemas.device_schemas import OAuthDeviceSchema
from zenml.zen_stores.schemas.flavor_schemas import FlavorSchema
from zenml.zen_stores.schemas.hook_invocation_schemas import (
    HookInvocationOutputArtifactSchema,
    HookInvocationSchema,
)
from zenml.zen_stores.schemas.logs_schemas import LogsSchema
from zenml.zen_stores.schemas.model_schemas import (
    ModelSchema,
    ModelVersionArtifactSchema,
    ModelVersionPipelineRunSchema,
    ModelVersionSchema,
)
from zenml.zen_stores.schemas.pipeline_build_schemas import PipelineBuildSchema
from zenml.zen_stores.schemas.pipeline_run_schemas import (
    PipelineRunOutputSchema,
    PipelineRunSchema,
)
from zenml.zen_stores.schemas.pipeline_schemas import PipelineSchema
from zenml.zen_stores.schemas.pipeline_snapshot_schemas import (
    PipelineSnapshotSchema,
    StepConfigurationSchema,
)
from zenml.zen_stores.schemas.project_schemas import ProjectSchema
from zenml.zen_stores.schemas.resource_pool_policy_schemas import (
    ResourcePoolSubjectPolicyResourceSchema,
    ResourcePoolSubjectPolicySchema,
)
from zenml.zen_stores.schemas.resource_pool_schemas import (
    ResourcePoolAllocationSchema,
    ResourcePoolQueueSchema,
    ResourcePoolResourceSchema,
    ResourcePoolSchema,
)
from zenml.zen_stores.schemas.resource_request_schemas import (
    ResourceRequestResourceSchema,
    ResourceRequestSchema,
)
from zenml.zen_stores.schemas.run_metadata_schemas import (
    RunMetadataResourceSchema,
    RunMetadataSchema,
)
from zenml.zen_stores.schemas.run_template_schemas import RunTemplateSchema
from zenml.zen_stores.schemas.run_wait_condition_schemas import (
    RunWaitConditionSchema,
)
from zenml.zen_stores.schemas.schedule_schema import ScheduleSchema
from zenml.zen_stores.schemas.secret_schemas import (
    SecretResourceSchema,
    SecretSchema,
)
from zenml.zen_stores.schemas.server_settings_schemas import (
    ServerSettingsSchema,
)
from zenml.zen_stores.schemas.service_connector_schemas import (
    ServiceConnectorSchema,
)
from zenml.zen_stores.schemas.service_schemas import ServiceSchema
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
from zenml.zen_stores.schemas.tag_schemas import TagResourceSchema, TagSchema
from zenml.zen_stores.schemas.trigger_assoc import (
    TriggerExecutionSchema,
    TriggerSnapshotSchema,
)
from zenml.zen_stores.schemas.trigger_schemas import TriggerSchema
from zenml.zen_stores.schemas.user_schemas import UserSchema

__all__ = [
    "APIKeySchema",
    "ArtifactSchema",
    "ArtifactVersionSchema",
    "ArtifactVisualizationSchema",
    "BaseSchema",
    "CodeReferenceSchema",
    "CodeRepositorySchema",
    "DeploymentSchema",
    "CuratedVisualizationSchema",
    "FlavorSchema",
    "HookInvocationSchema",
    "HookInvocationOutputArtifactSchema",
    "LogsSchema",
    "NamedSchema",
    "OAuthDeviceSchema",
    "PipelineBuildSchema",
    "PipelineSnapshotSchema",
    "StepConfigurationSchema",
    "PipelineRunSchema",
    "PipelineRunOutputSchema",
    "PipelineSchema",
    "RunMetadataResourceSchema",
    "RunMetadataSchema",
    "ScheduleSchema",
    "SecretSchema",
    "SecretResourceSchema",
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
    "RunWaitConditionSchema",
    "TagSchema",
    "TagResourceSchema",
    "UserSchema",
    "LogsSchema",
    "ModelSchema",
    "ModelVersionSchema",
    "ModelVersionArtifactSchema",
    "ModelVersionPipelineRunSchema",
    "ProjectSchema",
    "ApiTransactionResultSchema",
    "ApiTransactionSchema",
    "ResourcePoolQueueSchema",
    "ResourcePoolAllocationSchema",
    "ResourcePoolSubjectPolicySchema",
    "ResourcePoolSubjectPolicyResourceSchema",
    "ResourcePoolSchema",
    "ResourcePoolResourceSchema",
    "ResourceRequestSchema",
    "ResourceRequestResourceSchema",
    "TriggerSchema",
    "TriggerSnapshotSchema",
    "TriggerExecutionSchema",
]
