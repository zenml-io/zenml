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
"""ZenML Pro workspace client."""

from typing import List, Optional
from uuid import UUID

from zenml.logger import get_logger
from zenml.login.pro.client import ZenMLProClient
from zenml.login.pro.workspace.models import WorkspaceRead, WorkspaceStatus

logger = get_logger(__name__)

WORKSPACES_ROUTE = "/workspaces"


class WorkspaceClient:
    """Workspace management client."""

    def __init__(
        self,
        client: ZenMLProClient,
    ):
        """Initialize the workspace client.

        Args:
            client: ZenML Pro client.
        """
        self.client = client

    def get(self, id: UUID) -> WorkspaceRead:
        """Get a workspace by id.

        Args:
            id: Id. of the workspace to retrieve.

        Returns:
            A workspace.
        """
        return self.client._get_resource(
            resource_id=id,
            route=WORKSPACES_ROUTE,
            response_model=WorkspaceRead,
        )

    def list(
        self,
        offset: int = 0,
        limit: int = 20,
        workspace_name: Optional[str] = None,
        url: Optional[str] = None,
        organization_id: Optional[UUID] = None,
        status: Optional[WorkspaceStatus] = None,
        member_only: bool = False,
    ) -> List[WorkspaceRead]:
        """List workspaces.

        Args:
            offset: Offset to use for filtering.
            limit: Limit used for filtering.
            workspace_name: Workspace name to filter by.
            url: Workspace service URL to filter by.
            organization_id: Organization ID to filter by.
            status: Filter for only workspaces with this status.
            member_only: If True, only list workspaces where the user is a member
                (i.e. users that can connect to the workspace).

        Returns:
            List of workspaces.
        """
        return self.client._list_resources(
            route=WORKSPACES_ROUTE,
            response_model=WorkspaceRead,
            offset=offset,
            limit=limit,
            workspace_name=workspace_name,
            url=url,
            organization_id=organization_id,
            status=status,
            member_only=member_only,
        )
