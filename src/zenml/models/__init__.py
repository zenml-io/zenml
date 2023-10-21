#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Pydantic models for the various concepts in ZenML."""
from zenml.new_models.core.user import UserResponse
from zenml.new_models.core.workspace import WorkspaceResponse
from zenml.models.auth_models import (
    OAuthDeviceAuthorizationRequest,
    OAuthDeviceAuthorizationResponse,
    OAuthDeviceTokenRequest,
    OAuthDeviceUserAgentHeader,
    OAuthDeviceVerificationRequest,
    OAuthRedirectResponse,
    OAuthTokenResponse,
)
from zenml.models.base_models import BaseRequestModel, BaseResponseModel
from zenml.models.device_models import (
    OAuthDeviceFilterModel,
    OAuthDeviceInternalRequestModel,
    OAuthDeviceInternalResponseModel,
    OAuthDeviceInternalUpdateModel,
    OAuthDeviceResponseModel,
    OAuthDeviceUpdateModel,
)
from zenml.models.page_model import Page
from zenml.models.secret_models import (
    SecretBaseModel,
    SecretFilterModel,
    SecretRequestModel,
    SecretResponseModel,
    SecretUpdateModel,
)
from zenml.models.server_models import ServerDatabaseType, ServerModel
from zenml.models.user_models import ExternalUserModel
from zenml.models.model_models import (
    ModelFilterModel,
    ModelResponseModel,
    ModelRequestModel,
    ModelUpdateModel,
    ModelVersionBaseModel,
    ModelVersionResponseModel,
    ModelVersionRequestModel,
    ModelVersionArtifactBaseModel,
    ModelVersionArtifactFilterModel,
    ModelVersionArtifactRequestModel,
    ModelVersionArtifactResponseModel,
    ModelVersionPipelineRunBaseModel,
    ModelVersionPipelineRunFilterModel,
    ModelVersionPipelineRunRequestModel,
    ModelVersionPipelineRunResponseModel,
    ModelVersionFilterModel,
    ModelVersionUpdateModel,
)

SecretResponseModel.update_forward_refs(
    UserResponseModel=UserResponse,
    WorkspaceResponseModel=WorkspaceResponse,
)
ModelRequestModel.update_forward_refs(
    UserResponseModel=UserResponse,
    WorkspaceResponseModel=WorkspaceResponse,
)
ModelResponseModel.update_forward_refs(
    UserResponseModel=UserResponse,
    WorkspaceResponseModel=WorkspaceResponse,
)
ModelVersionRequestModel.update_forward_refs(
    UserResponseModel=UserResponse,
    WorkspaceResponseModel=WorkspaceResponse,
)
ModelVersionResponseModel.update_forward_refs(
    UserResponseModel=UserResponse,
    WorkspaceResponseModel=WorkspaceResponse,
)
ModelVersionArtifactRequestModel.update_forward_refs(
    UserResponseModel=UserResponse,
    WorkspaceResponseModel=WorkspaceResponse,
)
ModelVersionArtifactResponseModel.update_forward_refs(
    UserResponseModel=UserResponse,
    WorkspaceResponseModel=WorkspaceResponse,
)
ModelVersionPipelineRunRequestModel.update_forward_refs(
    UserResponseModel=UserResponse,
    WorkspaceResponseModel=WorkspaceResponse,
)
ModelVersionPipelineRunResponseModel.update_forward_refs(
    UserResponseModel=UserResponse,
    WorkspaceResponseModel=WorkspaceResponse,
)
OAuthDeviceResponseModel.update_forward_refs(
    UserResponseModel=UserResponse,
)
OAuthDeviceInternalResponseModel.update_forward_refs(
    UserResponseModel=UserResponse,
)

__all__ = [
    "BaseRequestModel",
    "BaseResponseModel",
    "ExternalUserModel",
    "ModelFilterModel",
    "ModelRequestModel",
    "ModelResponseModel",
    "ModelUpdateModel",
    "ModelVersionBaseModel",
    "ModelVersionFilterModel",
    "ModelVersionRequestModel",
    "ModelVersionResponseModel",
    "ModelVersionUpdateModel",
    "ModelVersionArtifactBaseModel",
    "ModelVersionArtifactFilterModel",
    "ModelVersionArtifactRequestModel",
    "ModelVersionArtifactResponseModel",
    "ModelVersionPipelineRunBaseModel",
    "ModelVersionPipelineRunFilterModel",
    "ModelVersionPipelineRunRequestModel",
    "ModelVersionPipelineRunResponseModel",
    "OAuthDeviceAuthorizationRequest",
    "OAuthDeviceAuthorizationResponse",
    "OAuthDeviceFilterModel",
    "OAuthDeviceInternalRequestModel",
    "OAuthDeviceInternalResponseModel",
    "OAuthDeviceInternalUpdateModel",
    "OAuthDeviceResponseModel",
    "OAuthDeviceTokenRequest",
    "OAuthDeviceUpdateModel",
    "OAuthDeviceUserAgentHeader",
    "OAuthDeviceVerificationRequest",
    "OAuthRedirectResponse",
    "OAuthTokenResponse",
    "Page",
    "SecretBaseModel",
    "SecretFilterModel",
    "SecretRequestModel",
    "SecretResponseModel",
    "SecretUpdateModel",
    "ServerDatabaseType",
    "ServerModel",
]
