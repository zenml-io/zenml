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
"""Models representing resource pool subject policies."""

from typing import (
    TYPE_CHECKING,
    Dict,
    Optional,
    Union,
)
from uuid import UUID

from pydantic import Field, NonNegativeInt, model_validator

from zenml.models.v2.base.base import BaseUpdate
from zenml.models.v2.base.scoped import (
    UserScopedFilter,
    UserScopedRequest,
    UserScopedResponse,
    UserScopedResponseBody,
    UserScopedResponseMetadata,
    UserScopedResponseResources,
)

if TYPE_CHECKING:
    from zenml.models import ComponentResponse
    from zenml.models.v2.core.resource_pool import ResourcePoolResponse


# ------------------ Request Model ------------------


class ResourcePoolSubjectPolicyRequest(UserScopedRequest):
    """Resource pool subject policy request."""

    component_id: UUID = Field(
        title="The ID of the component that is the subject of the policy.",
    )
    pool_id: UUID = Field(
        title="The ID of the resource pool that the policy is attached to.",
    )
    priority: NonNegativeInt = Field(
        title="The priority of the policy in the resource pool. Higher "
        "means preferred.",
    )
    reserved: Optional[Dict[str, NonNegativeInt]] = Field(
        title="The resources that are reserved for the policy.",
        default=None,
    )
    limit: Optional[Dict[str, NonNegativeInt]] = Field(
        title="The maximum resources that the policy can use.",
        default=None,
    )

    @model_validator(mode="after")
    def _validate_resources(self) -> "ResourcePoolSubjectPolicyRequest":
        if not self.reserved or not self.limit:
            return self

        for key, reserved_value in self.reserved.items():
            limit_value = self.limit.get(key)

            if limit_value is not None and reserved_value > limit_value:
                raise ValueError(
                    f"Reserved value for resource `{key}` ({reserved_value}) "
                    f"must be less than limit `{limit_value}`."
                )

        return self


# ------------------ Update Model ------------------


class ResourcePoolSubjectPolicyUpdate(BaseUpdate):
    """Update model for resource pool subject policies."""

    priority: NonNegativeInt = Field(
        title="The priority of the policy in the resource pool. Higher "
        "means preferred.",
    )
    reserved: Optional[Dict[str, NonNegativeInt]] = Field(
        title="The resources that are reserved for the policy.",
        default=None,
    )
    limit: Optional[Dict[str, NonNegativeInt]] = Field(
        title="The maximum resources that the policy can use.",
        default=None,
    )

    @model_validator(mode="after")
    def _validate_resources(self) -> "ResourcePoolSubjectPolicyUpdate":
        if not self.reserved or not self.limit:
            return self

        for key, reserved_value in self.reserved.items():
            limit_value = self.limit.get(key)

            if limit_value is not None and reserved_value > limit_value:
                raise ValueError(
                    f"Reserved value for resource `{key}` ({reserved_value}) "
                    f"must be less than limit `{limit_value}`."
                )

        return self


# ------------------ Response Model ------------------


class ResourcePoolSubjectPolicyResponseBody(UserScopedResponseBody):
    """Response body for resource pool subject policies."""

    priority: NonNegativeInt = Field(
        title="The priority of the policy in the resource pool. Higher "
        "means preferred.",
    )


class ResourcePoolSubjectPolicyResponseMetadata(UserScopedResponseMetadata):
    """Response metadata for resource pool subject policies."""

    reserved: Dict[str, NonNegativeInt] = Field(
        title="The resources that are reserved for the policy.",
    )
    limit: Dict[str, NonNegativeInt] = Field(
        title="The maximum resources that the policy can use.",
    )


class ResourcePoolSubjectPolicyResponseResources(UserScopedResponseResources):
    """Response resources for resource pool subject policies."""

    component: "ComponentResponse" = Field(
        title="The component that is requesting the resources."
    )
    pool: "ResourcePoolResponse" = Field(
        title="The resource pool that the policy is attached to.",
    )


class ResourcePoolSubjectPolicyResponse(
    UserScopedResponse[
        ResourcePoolSubjectPolicyResponseBody,
        ResourcePoolSubjectPolicyResponseMetadata,
        ResourcePoolSubjectPolicyResponseResources,
    ]
):
    """Response model for resource pool subject policies."""

    def get_hydrated_version(self) -> "ResourcePoolSubjectPolicyResponse":
        """Get the hydrated version of this resource pool subject policy.

        Returns:
            The hydrated version of this resource pool subject policy.
        """
        from zenml.client import Client

        return Client().zen_store.get_resource_pool_subject_policy(self.id)

    @property
    def priority(self) -> int:
        """The `priority` property.

        Returns:
            the value of the property.
        """
        return self.get_body().priority

    @property
    def reserved(self) -> Dict[str, int]:
        """The `reserved` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().reserved

    @property
    def limit(self) -> Dict[str, int]:
        """The `limit` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().limit

    @property
    def component(self) -> "ComponentResponse":
        """The `component` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().component

    @property
    def pool(self) -> "ResourcePoolResponse":
        """The `pool` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().pool


# ------------------ Filter Model ------------------


class ResourcePoolSubjectPolicyFilter(UserScopedFilter):
    """Resource pool subject policy filter model."""

    pool_id: Union[UUID, str, None] = Field(
        default=None,
        description="The ID of the resource pool that the policy is attached to.",
    )
    component_id: Union[UUID, str, None] = Field(
        default=None,
        description="The ID of the component that is the subject of the policy.",
    )
    priority: Union[int, str, None] = Field(
        default=None,
        description="The priority of the policy in the resource pool.",
    )
