#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Models representing resource policies."""

from typing import ClassVar, List, Optional, Union
from uuid import UUID

from pydantic import Field, NonNegativeInt, model_validator

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.models.v2.base.base import BaseUpdate, BaseZenModel
from zenml.models.v2.base.scoped import (
    UserScopedFilter,
    UserScopedRequest,
    UserScopedResponse,
    UserScopedResponseBody,
    UserScopedResponseMetadata,
    UserScopedResponseResources,
)


class ResourcePolicyGrant(BaseZenModel):
    """Grant line item in resource policy payloads."""

    resource_id: Optional[UUID] = Field(
        default=None,
        title="The resource descriptor ID.",
    )
    resource: Optional[str] = Field(
        default=None,
        title="The resource descriptor name.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    classes: list[str] = Field(
        title="The capacity classes covered by the grant.",
        min_length=1,
    )
    reserved: NonNegativeInt = Field(
        default=0,
        title="The reserved capacity for this grant.",
    )
    limit: NonNegativeInt = Field(
        title="The hard usage limit for this grant.",
    )

    @model_validator(mode="after")
    def _validate_limit(self) -> "ResourcePolicyGrant":
        """Validate that reserved capacity does not exceed the limit.

        Returns:
            The validated policy grant.

        Raises:
            ValueError: If ``reserved`` is greater than ``limit``.
        """
        if self.reserved > self.limit:
            raise ValueError(
                "Reserved capacity must be less than or equal to the limit."
            )

        return self


class ResourcePolicyRequest(UserScopedRequest):
    """Request model for resource policy creation."""

    pool_id: Optional[UUID] = Field(
        default=None,
        title="The target resource pool ID.",
    )
    pool: Optional[str] = Field(
        default=None,
        title="The target resource pool name.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    component_id: UUID = Field(title="The stack component ID.")
    priority: NonNegativeInt = Field(title="The policy priority.")
    grants: list[ResourcePolicyGrant] = Field(
        title="The policy grants.",
        min_length=1,
    )

    @model_validator(mode="after")
    def _validate_pool_reference(self) -> "ResourcePolicyRequest":
        """Validate that the policy targets a pool.

        Returns:
            The validated policy request.

        Raises:
            ValueError: If neither ``pool_id`` nor ``pool`` is set.
        """
        if self.pool_id is None and self.pool is None:
            raise ValueError("A resource policy requires a pool ID or name.")

        return self


class ResourcePolicyUpdate(BaseUpdate):
    """Update model for resource policies."""

    pool_id: Optional[UUID] = Field(
        default=None,
        title="The new target resource pool ID.",
    )
    pool: Optional[str] = Field(
        default=None,
        title="The new target resource pool name.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    component_id: Optional[UUID] = Field(
        default=None,
        title="The new stack component ID.",
    )
    priority: Optional[NonNegativeInt] = Field(
        default=None,
        title="The new policy priority.",
    )
    grants: Optional[list[ResourcePolicyGrant]] = Field(
        default=None,
        title="The full replacement policy grants.",
    )


class ResourcePolicyResponseBody(UserScopedResponseBody):
    """Response body for resource policies."""

    pool_id: UUID = Field(title="The target resource pool ID.")
    component_id: UUID = Field(title="The stack component ID.")
    priority: NonNegativeInt = Field(title="The policy priority.")
    grants: list[ResourcePolicyGrant] = Field(title="The policy grants.")


class ResourcePolicyResponseMetadata(UserScopedResponseMetadata):
    """Response metadata for resource policies."""

    pool: Optional[str] = Field(
        default=None,
        title="The target resource pool name.",
    )


class ResourcePolicyResponseResources(UserScopedResponseResources):
    """Response resources for resource policies."""


class ResourcePolicyResponse(
    UserScopedResponse[
        ResourcePolicyResponseBody,
        ResourcePolicyResponseMetadata,
        ResourcePolicyResponseResources,
    ]
):
    """Response model for resource policies."""

    @property
    def pool_id(self) -> UUID:
        """Resource policy pool ID.

        Returns:
            The ID of the resource pool targeted by this policy.
        """
        return self.get_body().pool_id

    @property
    def pool(self) -> Optional[str]:
        """Resource policy pool name.

        Returns:
            The optional name of the resource pool targeted by this policy.
        """
        return self.get_metadata().pool

    @property
    def component_id(self) -> UUID:
        """Resource policy component ID.

        Returns:
            The stack component ID targeted by this policy.
        """
        return self.get_body().component_id

    @property
    def priority(self) -> int:
        """Resource policy priority.

        Returns:
            The policy priority.
        """
        return self.get_body().priority

    @property
    def grants(self) -> list[ResourcePolicyGrant]:
        """Resource policy grants.

        Returns:
            The grant declarations attached to this policy.
        """
        return self.get_body().grants


class ResourcePolicyFilter(UserScopedFilter):
    """Resource policy filter model."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *UserScopedFilter.FILTER_EXCLUDE_FIELDS,
    ]

    id: Union[UUID, str, None] = Field(
        default=None,
        description="ID of the resource policy.",
    )
    pool_id: Union[UUID, str, None] = Field(
        default=None,
        description="The target resource pool ID.",
    )
    pool: Optional[str] = Field(
        default=None,
        description="The target resource pool name.",
    )
    component_id: Union[UUID, str, None] = Field(
        default=None,
        description="The stack component ID.",
    )
    priority: Union[int, str, None] = Field(
        default=None,
        description="The policy priority.",
    )
