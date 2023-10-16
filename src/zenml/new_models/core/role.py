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
from zenml.new_models.base import (
    BaseRequest,
    BaseResponse,
    BaseResponseMetadata,
    update_model,
)

# ------------------ Request Model ------------------


class RoleRequest(BaseRequest):
    """Request models for roles."""

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


class RoleResponseMetadata(BaseResponseMetadata):
    """Response metadata model for roles."""


class RoleResponse(BaseResponse):
    """Response model for roles."""

    # Entity fields
    name: str = Field(
        title="The unique name of the role.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    permissions: Set[PermissionType]

    # Metadata related field, method and properties
    metadata: Optional["RoleResponseMetadata"]

    def get_hydrated_version(self) -> "RoleResponse":
        # TODO: Implement it with the parameterized calls
        from zenml.client import Client

        return Client().get_role(self.id)
