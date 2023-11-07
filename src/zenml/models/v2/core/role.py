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
"""Models representing roles."""

from typing import Optional, Set

from pydantic import Field

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.enums import PermissionType
from zenml.models.v2.base.base import (
    BaseRequest,
    BaseResponse,
    BaseResponseBody,
    BaseResponseMetadata,
)
from zenml.models.v2.base.filter import BaseFilter
from zenml.models.v2.base.utils import update_model

# ------------------ Request Model ------------------


class RoleRequest(BaseRequest):
    """Request model for roles."""

    name: str = Field(
        title="The unique name of the role.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    permissions: Set[PermissionType]


# ------------------ Update Model ------------------


@update_model
class RoleUpdate(RoleRequest):
    """Update model for roles."""


# ------------------ Response Model ------------------
class RoleResponseBody(BaseResponseBody):
    """Response body for roles."""

    permissions: Set[PermissionType]


class RoleResponseMetadata(BaseResponseMetadata):
    """Response metadata for roles."""


class RoleResponse(BaseResponse[RoleResponseBody, RoleResponseMetadata]):
    """Response model for roles."""

    name: str = Field(
        title="The unique name of the role.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    def get_hydrated_version(self) -> "RoleResponse":
        """Get the hydrated version of this role."""
        from zenml.client import Client

        return Client().zen_store.get_role(self.id)

    # Body and metadata properties
    @property
    def permissions(self) -> Set[PermissionType]:
        """The `permissions` property."""
        return self.get_body().permissions


# ------------------ Filter Model ------------------


class RoleFilter(BaseFilter):
    """Model to enable advanced filtering of all Users."""

    name: Optional[str] = Field(
        default=None,
        description="Name of the role",
    )
