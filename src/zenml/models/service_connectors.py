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
"""Model definitions for ZenML service connectors."""

import re
from typing import Any, ClassVar, Dict, List, Optional, Type, Union
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    validator,
)

from zenml.models.base_models import (
    ShareableRequestModel,
    ShareableResponseModel,
    update_model,
)
from zenml.models.constants import STR_FIELD_MAX_LENGTH
from zenml.models.filter_models import ShareableWorkspaceScopedFilterModel

# ---- #
# BASE #
# ---- #


class ServiceConnectorBaseModel(BaseModel):
    """Base model for service connectors."""

    type: str = Field(
        title="The type of service connector.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    name: str = Field(
        title="The service connector name.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    auth_method: str = Field(
        title="The authentication method that the connector instance uses to "
        "access the resources.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    resource_type: Optional[str] = Field(
        default=None,
        title="The type of resource that the connector instance can be used "
        "to gain access to. Only applicable if the connector's specification "
        "indicates that resource types are supported. If the connector's "
        "specification doesn't allow arbitrary resource types, then this "
        "value must one of those enumerated in the specification. If "
        "omitted in the connector configuration, a resource type must be "
        "provided by the connector consumer at runtime.",
    )
    resource_id: Optional[str] = Field(
        default=None,
        title="Uniquely identifies a specific resource instance that the "
        "connector instance can be used to access. Only applicable if the "
        "connector's specification indicates that resource IDs are supported "
        "for the configured authentication method and resource type. If "
        "omitted in the connector configuration, a resource ID must be "
        "provided by the connector consumer at runtime.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    configuration: Optional[Dict[str, Any]] = Field(
        title="The service connector configuration.",
    )
    secret_reference: Optional[UUID] = Field(
        default=None,
        title="The ID of the secret that contains the service connector "
        "credentials.",
    )


# -------- #
# RESPONSE #
# -------- #


class ServiceConnectorResponseModel(
    ServiceConnectorBaseModel, ShareableResponseModel
):
    """Response model for service connectors."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = [
        "connector_type",
        "auth_method",
        "resource_type",
    ]


# ------ #
# FILTER #
# ------ #


class ServiceConnectorFilterModel(ShareableWorkspaceScopedFilterModel):
    """Model to enable advanced filtering of service connectors."""

    is_shared: Optional[Union[bool, str]] = Field(
        default=None,
        description="If the service connector is shared or private",
    )
    name: Optional[str] = Field(
        default=None,
        description="The name to filter by",
    )
    type: Optional[str] = Field(
        default=None,
        description="The type of service connector to filter by",
    )
    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Workspace to filter by"
    )
    user_id: Optional[Union[UUID, str]] = Field(
        default=None, description="User to filter by"
    )
    auth_method: Optional[str] = Field(
        default=None,
        title="Filter by the authentication method configured for the "
        "connector",
    )
    resource_type: Optional[str] = Field(
        default=None,
        title="Filter by the type of resource that the connector is "
        "configured to access",
    )
    resource_id: Optional[str] = Field(
        default=None,
        title="Filter by the ID of the resource instance that the connector "
        "is configured to access",
    )
    secret_reference: Optional[UUID] = Field(
        default=None,
        title="Filter by the ID of the secret that contains the service "
        "connector's credentials",
    )


# ------- #
# REQUEST #
# ------- #


class ServiceConnectorRequestModel(
    ServiceConnectorBaseModel, ShareableRequestModel
):
    """Request model for service connectors."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = [
        "connector_type",
        "auth_method",
        "resource_type",
    ]


# ------ #
# UPDATE #
# ------ #


@update_model
class ServiceConnectorUpdateModel(ServiceConnectorRequestModel):
    """Update model for service connectors."""
