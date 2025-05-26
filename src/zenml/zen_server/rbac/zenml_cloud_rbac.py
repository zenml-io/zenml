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
"""Cloud RBAC implementation."""

from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple

from zenml.zen_server.cloud_utils import cloud_connection
from zenml.zen_server.rbac.models import Action, Resource
from zenml.zen_server.rbac.rbac_interface import RBACInterface

if TYPE_CHECKING:
    from zenml.models import UserResponse


PERMISSIONS_ENDPOINT = "/rbac/check_permissions"
ALLOWED_RESOURCE_IDS_ENDPOINT = "/rbac/allowed_resource_ids"
RESOURCE_MEMBERSHIP_ENDPOINT = "/rbac/resource_members"
RESOURCES_ENDPOINT = "/rbac/resources"


class ZenMLCloudRBAC(RBACInterface):
    """RBAC implementation that uses the ZenML Pro Management Plane as a backend."""

    def __init__(self) -> None:
        """Initialize the object."""
        self._connection = cloud_connection()

    def check_permissions(
        self, user: "UserResponse", resources: Set[Resource], action: Action
    ) -> Dict[Resource, bool]:
        """Checks if a user has permissions to perform an action on resources.

        Args:
            user: User which wants to access a resource.
            resources: The resources the user wants to access.
            action: The action that the user wants to perform on the resources.

        Returns:
            A dictionary mapping resources to a boolean which indicates whether
            the user has permissions to perform the action on that resource.
        """
        if not resources:
            # No need to send a request if there are no resources
            return {}

        if user.is_service_account:
            # Service accounts have full permissions for now
            return {resource: True for resource in resources}

        # At this point it's a regular user, which in a ZenML Pro with RBAC
        # enabled is always authenticated using external authentication
        assert user.external_user_id

        params = {
            "user_id": str(user.external_user_id),
            "action": str(action),
        }
        response = self._connection.post(
            endpoint=PERMISSIONS_ENDPOINT,
            params=params,
            data=[str(resource) for resource in resources],
        )
        value = response.json()

        assert isinstance(value, dict)
        return {Resource.parse(k): v for k, v in value.items()}

    def list_allowed_resource_ids(
        self, user: "UserResponse", resource: Resource, action: Action
    ) -> Tuple[bool, List[str]]:
        """Lists all resource IDs of a resource type that a user can access.

        Args:
            user: User which wants to access a resource.
            resource: The resource the user wants to access.
            action: The action that the user wants to perform on the resource.

        Returns:
            A tuple (full_resource_access, resource_ids).
            `full_resource_access` will be `True` if the user can perform the
            given action on any instance of the given resource type, `False`
            otherwise. If `full_resource_access` is `False`, `resource_ids`
            will contain the list of instance IDs that the user can perform
            the action on.
        """
        assert not resource.id
        if user.is_service_account:
            # Service accounts have full permissions for now
            return True, []

        # At this point it's a regular user, which in the ZenML Pro with RBAC
        # enabled is always authenticated using external authentication
        assert user.external_user_id
        params = {
            "user_id": str(user.external_user_id),
            "resource": str(resource),
            "action": str(action),
        }
        response = self._connection.get(
            endpoint=ALLOWED_RESOURCE_IDS_ENDPOINT, params=params
        )
        response_json = response.json()

        full_resource_access: bool = response_json["full_access"]
        allowed_ids: List[str] = response_json["ids"]

        return full_resource_access, allowed_ids

    def update_resource_membership(
        self,
        sharing_user: "UserResponse",
        resource: Resource,
        actions: List[Action],
        user_id: Optional[str] = None,
        team_id: Optional[str] = None,
    ) -> None:
        """Update the resource membership of a user.

        Args:
            sharing_user: User that is sharing the resource.
            resource: The resource.
            actions: The actions that the user should be able to perform on the
                resource.
            user_id: ID of the user for which to update the membership.
            team_id: ID of the team for which to update the membership.
        """
        assert sharing_user.external_user_id
        data = {
            "user_id": user_id,
            "team_id": team_id,
            "sharing_user_id": str(sharing_user.external_user_id),
            "resource": str(resource),
            "actions": [str(action) for action in actions],
        }
        self._connection.post(endpoint=RESOURCE_MEMBERSHIP_ENDPOINT, data=data)

    def delete_resources(self, resources: List[Resource]) -> None:
        """Delete resource membership information for a list of resources.

        Args:
            resources: The resources for which to delete the resource membership
                information.
        """
        params = {
            "resources": [str(resource) for resource in resources],
        }
        self._connection.delete(endpoint=RESOURCES_ENDPOINT, params=params)
