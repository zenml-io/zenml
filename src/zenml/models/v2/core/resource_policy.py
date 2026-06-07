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

PRIORITY_LANE_PRIORITY = 2_147_483_647
MAX_USER_POLICY_PRIORITY = PRIORITY_LANE_PRIORITY - 1


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
    limit: Optional[NonNegativeInt] = Field(
        default=None,
        title="The hard usage limit for this grant. Omit for pool capacity.",
    )
    unit: Optional[str] = Field(
        default=None,
        title="The optional unit for reserved and limit.",
        min_length=1,
        max_length=64,
    )

    @model_validator(mode="after")
    def _validate_resource_reference(self) -> "ResourcePolicyGrant":
        """Validate that the grant references a resource.

        Returns:
            The validated policy grant.

        Raises:
            ValueError: If neither resource ID nor name is set.
        """
        if self.resource_id is None and self.resource is None:
            raise ValueError("A policy grant requires a resource ID or name.")
        return self

    @model_validator(mode="after")
    def _validate_limit(self) -> "ResourcePolicyGrant":
        """Validate that reserved capacity does not exceed the limit.

        Returns:
            The validated policy grant.

        Raises:
            ValueError: If ``reserved`` is greater than ``limit``.
        """
        if self.limit is not None and self.reserved > self.limit:
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
    component_id: Optional[UUID] = Field(
        default=None,
        title="The stack component ID targeted by this policy.",
    )
    account_id: Optional[UUID] = Field(
        default=None,
        title="The external account ID targeted by this policy.",
    )
    priority_lane: bool = Field(
        default=False,
        title="Whether this policy uses the internal maximum priority lane.",
    )
    priority: Optional[NonNegativeInt] = Field(
        default=None,
        title="The policy priority for normal policies.",
    )
    grants: list[ResourcePolicyGrant] = Field(
        default_factory=list,
        title="The policy grants. Omit all grants for a grantless policy.",
    )

    @model_validator(mode="after")
    def _validate_request(self) -> "ResourcePolicyRequest":
        """Validate pool, component or account, and priority fields.

        Returns:
            The validated policy request.

        Raises:
            ValueError: If required references or priority fields are invalid.
        """
        if self.pool_id is None and self.pool is None:
            raise ValueError("A resource policy requires a pool ID or name.")

        has_component = self.component_id is not None
        has_account = self.account_id is not None
        if has_component == has_account:
            raise ValueError(
                "Exactly one of component_id or account_id must be set."
            )

        if self.priority_lane:
            if self.priority is not None:
                raise ValueError(
                    "priority must be omitted when priority_lane is true."
                )
        elif self.priority is None:
            raise ValueError(
                "priority is required when priority_lane is false."
            )
        elif self.priority > MAX_USER_POLICY_PRIORITY:
            raise ValueError(
                f"priority must be below the priority-lane value of "
                f"{MAX_USER_POLICY_PRIORITY}."
            )

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
    account_id: Optional[UUID] = Field(
        default=None,
        title="The new external account ID.",
    )
    priority_lane: Optional[bool] = Field(
        default=None,
        title="Whether this policy uses the internal maximum priority lane.",
    )
    priority: Optional[NonNegativeInt] = Field(
        default=None,
        title="The new policy priority.",
    )
    grants: Optional[list[ResourcePolicyGrant]] = Field(
        default=None,
        title="The full replacement policy grants.",
    )

    @model_validator(mode="after")
    def _validate_component_account_and_priority(
        self,
    ) -> "ResourcePolicyUpdate":
        """Validate mutually exclusive component, account, and priority fields.

        Returns:
            The validated policy update.

        Raises:
            ValueError: If component, account, or priority fields are inconsistent.
        """
        if self.component_id is not None and self.account_id is not None:
            raise ValueError(
                "component_id and account_id cannot both be set on update."
            )

        if self.priority_lane is True and self.priority is not None:
            raise ValueError(
                "priority must be omitted when priority_lane is true."
            )
        if self.priority_lane is False and self.priority is None:
            raise ValueError(
                "priority is required when priority_lane is false."
            )
        if (
            self.priority is not None
            and self.priority > MAX_USER_POLICY_PRIORITY
        ):
            raise ValueError("priority must be below the priority-lane value.")
        return self


class ResourcePolicyResponseBody(UserScopedResponseBody):
    """Response body for resource policies."""

    pool_id: UUID = Field(title="The target resource pool ID.")
    component_id: Optional[UUID] = Field(
        default=None,
        title="The stack component ID when the policy targets a component.",
    )
    account_id: Optional[UUID] = Field(
        default=None,
        title="The external account ID when the policy targets an account.",
    )
    priority_lane: bool = Field(
        default=False,
        title="Whether this policy uses the internal maximum priority lane.",
    )
    priority: Optional[NonNegativeInt] = Field(
        default=None,
        title="The policy priority for normal policies.",
    )
    grants: list[ResourcePolicyGrant] = Field(
        default_factory=list,
        title="The policy grants.",
    )


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
    def component_id(self) -> Optional[UUID]:
        """Resource policy component ID.

        Returns:
            The stack component ID targeted by this policy, if any.
        """
        return self.get_body().component_id

    @property
    def account_id(self) -> Optional[UUID]:
        """Resource policy account ID.

        Returns:
            The external account ID targeted by this policy, if any.
        """
        return self.get_body().account_id

    @property
    def priority_lane(self) -> bool:
        """Whether this policy uses the priority lane.

        Returns:
            True when the policy has internal maximum priority.
        """
        return self.get_body().priority_lane

    @property
    def priority(self) -> Optional[int]:
        """Resource policy priority.

        Returns:
            The policy priority for normal policies.
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
    account_id: Union[UUID, str, None] = Field(
        default=None,
        description="The external account ID.",
    )
    priority: Union[int, str, None] = Field(
        default=None,
        description="The policy priority.",
    )
    priority_lane: Union[bool, str, None] = Field(
        default=None,
        description="Whether the policy uses the priority lane.",
    )
