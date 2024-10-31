#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""ZenML Pro tenant models."""

from typing import Optional
from uuid import UUID

from pydantic import Field

from zenml.login.pro.constants import ZENML_PRO_URL
from zenml.login.pro.models import BaseRestAPIModel
from zenml.login.pro.organization.models import OrganizationRead
from zenml.utils.enum_utils import StrEnum


class TenantStatus(StrEnum):
    """Enum that represents the desired state or status of a tenant.

    These values can be used in two places:

    * in the `desired_state` field of a tenant object, to indicate the desired
    state of the tenant (with the exception of `PENDING` and `FAILED` which
    are not valid values for `desired_state`)
    * in the `status` field of a tenant object, to indicate the current state
    of the tenant
    """

    # Tenant hasn't been deployed yet (i.e. newly created) or has been fully
    # deleted by the infrastructure provider
    NOT_INITIALIZED = "not_initialized"
    # Tenant is being processed by the infrastructure provider (is being
    # deployed, updated, deactivated, re-activated or deleted/cleaned up).
    PENDING = "pending"
    # Tenant is up and running
    AVAILABLE = "available"
    # Tenant is in a failure state (i.e. deployment, update or deletion failed)
    FAILED = "failed"
    # Tenant is deactivated
    DEACTIVATED = "deactivated"
    # Tenant resources have been deleted by the infrastructure provider but
    # the tenant object still exists in the database
    DELETED = "deleted"


class ZenMLServiceConfiguration(BaseRestAPIModel):
    """ZenML service configuration."""

    version: str = Field(
        description="The ZenML version.",
    )


class ZenMLServiceStatus(BaseRestAPIModel):
    """ZenML service status."""

    server_url: str = Field(
        description="The ZenML server URL.",
    )
    version: Optional[str] = Field(
        default=None,
        description="The ZenML server version.",
    )


class ZenMLServiceRead(BaseRestAPIModel):
    """Pydantic Model for viewing a ZenML service."""

    configuration: ZenMLServiceConfiguration = Field(
        description="The service configuration."
    )

    status: Optional[ZenMLServiceStatus] = Field(
        default=None,
        description="Information about the service status. Only set if the "
        "service is deployed and active.",
    )


class TenantRead(BaseRestAPIModel):
    """Pydantic Model for viewing a Tenant."""

    id: UUID

    name: str
    description: Optional[str] = Field(
        default=None, description="The description of the tenant."
    )

    organization: OrganizationRead

    desired_state: str = Field(description="The desired state of the tenant.")
    state_reason: str = Field(
        description="The reason for the current tenant state.",
    )
    status: str = Field(
        description="The current operational state of the tenant."
    )
    zenml_service: ZenMLServiceRead = Field(description="The ZenML service.")

    @property
    def organization_id(self) -> UUID:
        """Get the organization id.

        Returns:
            The organization id.
        """
        return self.organization.id

    @property
    def organization_name(self) -> str:
        """Get the organization name.

        Returns:
            The organization name.
        """
        return self.organization.name

    @property
    def version(self) -> Optional[str]:
        """Get the ZenML service version.

        Returns:
            The ZenML service version.
        """
        version = self.zenml_service.configuration.version
        if self.zenml_service.status and self.zenml_service.status.version:
            version = self.zenml_service.status.version

        return version

    @property
    def url(self) -> Optional[str]:
        """Get the ZenML server URL.

        Returns:
            The ZenML server URL, if available.
        """
        return (
            self.zenml_service.status.server_url
            if self.zenml_service.status
            else None
        )

    @property
    def dashboard_url(self) -> str:
        """Get the URL to the ZenML Pro dashboard for this tenant.

        Returns:
            The URL to the ZenML Pro dashboard for this tenant.
        """
        return (
            ZENML_PRO_URL
            + f"/organizations/{str(self.organization_id)}/tenants/{str(self.id)}"
        )

    @property
    def dashboard_organization_url(self) -> str:
        """Get the URL to the ZenML Pro dashboard for this tenant's organization.

        Returns:
            The URL to the ZenML Pro dashboard for this tenant's organization.
        """
        return ZENML_PRO_URL + f"/organizations/{str(self.organization_id)}"
