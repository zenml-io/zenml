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
"""ZenML Pro organization client."""

from typing import List, Union
from uuid import UUID

from zenml.logger import get_logger
from zenml.login.pro.client import ZenMLProClient
from zenml.login.pro.organization.models import OrganizationRead

logger = get_logger(__name__)

ORGANIZATIONS_ROUTE = "/organizations"


class OrganizationClient:
    """Organization management client."""

    def __init__(
        self,
        client: ZenMLProClient,
    ):
        """Initialize the organization client.

        Args:
            client: ZenML Pro client.
        """
        self.client = client

    def get(
        self,
        id_or_name: Union[UUID, str],
    ) -> OrganizationRead:
        """Get an organization by id or name.

        Args:
            id_or_name: Id or name of the organization to retrieve.

        Returns:
            An organization.
        """
        return self.client._get_resource(
            resource_id=id_or_name,
            route=ORGANIZATIONS_ROUTE,
            response_model=OrganizationRead,
        )

    async def list(
        self,
        offset: int = 0,
        limit: int = 20,
    ) -> List[OrganizationRead]:
        """List organizations.

        Args:
            offset: Query offset.
            limit: Query limit.

        Returns:
            List of organizations.
        """
        return self.client._list_resources(
            route=ORGANIZATIONS_ROUTE,
            response_model=OrganizationRead,
            offset=offset,
            limit=limit,
        )
