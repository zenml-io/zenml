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
"""ZenML Pro tenant client."""

from typing import List, Optional
from uuid import UUID

from zenml.logger import get_logger
from zenml.login.pro.client import ZenMLProClient
from zenml.login.pro.tenant.models import TenantRead, TenantStatus

logger = get_logger(__name__)

TENANTS_ROUTE = "/tenants"


class TenantClient:
    """Tenant management client."""

    def __init__(
        self,
        client: ZenMLProClient,
    ):
        """Initialize the tenant client.

        Args:
            client: ZenML Pro client.
        """
        self.client = client

    def get(self, id: UUID) -> TenantRead:
        """Get a tenant by id.

        Args:
            id: Id. of the tenant to retrieve.

        Returns:
            A tenant.
        """
        return self.client._get_resource(
            resource_id=id,
            route=TENANTS_ROUTE,
            response_model=TenantRead,
        )

    def list(
        self,
        offset: int = 0,
        limit: int = 20,
        tenant_name: Optional[str] = None,
        url: Optional[str] = None,
        organization_id: Optional[UUID] = None,
        status: Optional[TenantStatus] = None,
        member_only: bool = False,
    ) -> List[TenantRead]:
        """List tenants.

        Args:
            offset: Offset to use for filtering.
            limit: Limit used for filtering.
            tenant_name: Tenant name to filter by.
            url: Tenant service URL to filter by.
            organization_id: Organization ID to filter by.
            status: Filter for only tenants with this status.
            member_only: If True, only list tenants where the user is a member
                (i.e. users that can connect to the tenant).

        Returns:
            List of tenants.
        """
        return self.client._list_resources(
            route=TENANTS_ROUTE,
            response_model=TenantRead,
            offset=offset,
            limit=limit,
            tenant_name=tenant_name,
            url=url,
            organization_id=organization_id,
            status=status,
            member_only=member_only,
        )
